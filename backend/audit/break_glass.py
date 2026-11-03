"""
Break-glass emergency access API.

A Doctor or Nurse may open time-limited access to a patient of the acting
hospital who is not in their care, with a written reason. The grant widens
their care scope (users.care_scope.patients_in_care) until it lapses or is
ended; every read made under it is marked in the sensitive-read audit. An
Admin or Hospital Manager of that hospital reviews each grant.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.models import BreakGlassAccess
from audit.services import record_audit
from patients.models import Patient
from users.models import StaffRole
from users.permissions import IsStaffUser, get_request_hospital_id, get_user_active_hospital_memberships

MIN_REASON_LENGTH = 20
CLINICAL_ROLES = (StaffRole.DOCTOR, StaffRole.NURSE)
REVIEWER_ROLES = (StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER)


class BreakGlassAccessSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True, default="")
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = BreakGlassAccess
        fields = [
            "id", "user", "username", "hospital", "patient", "patient_name", "reason",
            "created_at", "expires_at", "ended_at", "is_active",
            "reviewed_by", "reviewed_by_username", "reviewed_at", "review_note",
        ]
        read_only_fields = fields

    def get_is_active(self, obj):
        return obj.ended_at is None and obj.expires_at > timezone.now()


def _hospitals_with_role(user, roles):
    return set(
        get_user_active_hospital_memberships(user).filter(role__in=roles).values_list("hospital_id", flat=True)
    )


class BreakGlassAccessViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    GET    /api/audit/break-glass/              own grants; reviewers also see their hospitals' grants
                                                (?pending_review=true for unreviewed ones)
    POST   /api/audit/break-glass/              {patient, reason}, acting hospital required
    POST   /api/audit/break-glass/{id}/end/     the clinician ends their grant early
    POST   /api/audit/break-glass/{id}/review/  {note}: an Admin or Hospital Manager signs it off
    """

    serializer_class = BreakGlassAccessSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]

    def get_queryset(self):
        user = self.request.user
        reviewer_hospitals = _hospitals_with_role(user, REVIEWER_ROLES)
        queryset = BreakGlassAccess.objects.select_related("user", "patient", "reviewed_by").filter(
            Q(user=user) | Q(hospital_id__in=reviewer_hospitals)
        )
        acting = get_request_hospital_id(self.request, self)
        if acting is not None:
            queryset = queryset.filter(hospital_id=acting)
        if self.request.query_params.get("pending_review") == "true":
            queryset = queryset.filter(reviewed_at__isnull=True)
        return queryset.order_by("-created_at", "-id")

    def create(self, request):
        hospital_id = get_request_hospital_id(request, self)
        if hospital_id is None:
            raise ValidationError({"hospital": "Choose the hospital you are working in."})
        if hospital_id not in _hospitals_with_role(request.user, CLINICAL_ROLES):
            raise PermissionDenied("Only a Doctor or Nurse of this hospital can use emergency access.")

        reason = str(request.data.get("reason") or "").strip()
        if len(reason) < MIN_REASON_LENGTH:
            raise ValidationError({"reason": f"Describe the emergency in at least {MIN_REASON_LENGTH} characters."})
        patient = self._patient_of_hospital(request.data.get("patient"), hospital_id)

        existing = BreakGlassAccess.objects.active().filter(
            user=request.user, hospital_id=hospital_id, patient=patient,
        ).first()
        if existing is not None:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)

        grant = BreakGlassAccess.objects.create(
            user=request.user, hospital_id=hospital_id, patient=patient, reason=reason,
            expires_at=timezone.now() + timedelta(minutes=settings.BREAK_GLASS_DURATION_MINUTES),
        )
        record_audit(request, "break_glass.open", grant, hospital=hospital_id,
                     details={"patient_id": patient.pk, "reason": reason,
                              "expires_at": grant.expires_at.isoformat()})
        return Response(self.get_serializer(grant).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        grant = self.get_object()
        if grant.user_id != request.user.pk:
            raise PermissionDenied("Only the clinician who opened this access can end it.")
        if grant.ended_at is None:
            grant.ended_at = timezone.now()
            grant.save(update_fields=["ended_at"])
            record_audit(request, "break_glass.end", grant, hospital=grant.hospital_id)
        return Response(self.get_serializer(grant).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        grant = self.get_object()
        if grant.hospital_id not in _hospitals_with_role(request.user, REVIEWER_ROLES):
            raise PermissionDenied("Only an Admin or Hospital Manager of this hospital can review access.")
        if grant.user_id == request.user.pk:
            raise PermissionDenied("You cannot review your own emergency access.")
        if grant.reviewed_at is not None:
            raise ValidationError("This access has already been reviewed.")
        grant.reviewed_by = request.user
        grant.reviewed_at = timezone.now()
        grant.review_note = str(request.data.get("note") or "").strip()
        grant.save(update_fields=["reviewed_by", "reviewed_at", "review_note"])
        record_audit(request, "break_glass.review", grant, hospital=grant.hospital_id,
                     details={"note": grant.review_note})
        return Response(self.get_serializer(grant).data)

    @staticmethod
    def _patient_of_hospital(patient_id, hospital_id):
        try:
            patient_id = int(patient_id)
        except (TypeError, ValueError):
            raise ValidationError({"patient": "Choose a patient."})
        patient = Patient.objects.filter(
            Q(hospital_id=hospital_id)
            | Q(hospital_memberships__hospital_id=hospital_id, hospital_memberships__is_active=True),
            pk=patient_id,
        ).distinct().first()
        if patient is None:
            raise ValidationError({"patient": "Patient is not registered at this hospital."})
        return patient
