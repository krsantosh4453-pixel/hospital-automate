from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from hospital.models import Hospital
from users.permissions import (
    IsStaffUser,
    IsHospitalMember,
    get_user_hospital_ids,
    get_user_active_hospital_memberships,
    get_linked_patient,
    is_active_staff,
)


class HospitalScopedViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that automatically scopes querysets to the user's authorized hospitals.
    """

    permission_classes = [IsAuthenticated, IsStaffUser, IsHospitalMember]

    def _base_queryset(self):
        if hasattr(self, "queryset") and self.queryset is not None:
            return self.queryset.all()
        return self.get_serializer().Meta.model.objects.all()

    def _queryset_for_linked_patient(self, queryset, patient):
        model = queryset.model
        if model._meta.label == "patients.Patient":
            return queryset.filter(pk=patient.pk)
        if hasattr(model, "patient"):
            return queryset.filter(patient_id=patient.pk)
        if hasattr(model, "visit"):
            return queryset.filter(visit__patient_id=patient.pk)
        if hasattr(model, "invoice"):
            return queryset.filter(invoice__patient_id=patient.pk)
        if hasattr(model, "prescription"):
            return queryset.filter(prescription__patient_id=patient.pk)
        return queryset.none()

    def get_queryset(self):
        if getattr(self, "queryset", None) is not None:
            queryset = self.queryset.all()
        else:
            queryset = self.get_serializer().Meta.model.objects.all()

        linked_patient = get_linked_patient(self.request.user)
        if linked_patient and not is_active_staff(self.request.user):
            return self._queryset_for_linked_patient(queryset, linked_patient)

        # Get the user's authorized hospital IDs
        hospital_ids = get_user_hospital_ids(self.request.user)

        if not hospital_ids:
            return queryset.none()

        # Filter queryset by hospital
        if hasattr(queryset.model, "hospital"):
            return queryset.filter(hospital_id__in=hospital_ids)

        # For models with patient -> hospital relationship
        if hasattr(queryset.model, "patient"):
            return queryset.filter(
                patient__hospital_memberships__hospital_id__in=hospital_ids,
                patient__hospital_memberships__is_active=True
            ).distinct()

        # For models with visit -> hospital relationship
        if hasattr(queryset.model, "visit"):
            return queryset.filter(
                visit__hospital_id__in=hospital_ids
            )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Add scoped_hospital to context for serializers that need it
        # Handle both DRF Request (query_params) and Django WSGIRequest (GET)
        # Also check request.data for POST/PUT/PATCH requests
        hospital_id = None
        if hasattr(self.request, 'query_params'):
            hospital_id = self.request.query_params.get("hospital")
        elif hasattr(self.request, 'GET'):
            hospital_id = self.request.GET.get("hospital")
        
        # Also check request.data for POST/PUT/PATCH
        if not hospital_id and hasattr(self.request, 'data'):
            hospital_id = self.request.data.get("hospital")
        
        if hospital_id:
            try:
                context["scoped_hospital"] = Hospital.objects.get(pk=hospital_id)
            except Hospital.DoesNotExist:
                pass
        return context
        # Get the requested hospital from context or query params
        hospital_id = self._get_requested_hospital_id()
        if hospital_id:
            hospital_ids = get_user_hospital_ids(self.request.user)
            if hospital_id not in hospital_ids:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have access to this hospital.")
            serializer.save(hospital_id=hospital_id)
        else:
            # Use the user's first hospital as default
            hospital_ids = get_user_hospital_ids(self.request.user)
            if hospital_ids:
                serializer.save(hospital_id=hospital_ids[0])
            else:
                serializer.save()

    def _get_requested_hospital_id(self):
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            return int(hospital_id)
        hospital_id = self.request.data.get("hospital")
        if hospital_id:
            return int(hospital_id)
        return None


class ReadOnlyHospitalScopedViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only version of HospitalScopedViewSet.
    """

    permission_classes = [IsAuthenticated, IsStaffUser, IsHospitalMember]

    def get_queryset(self):
        if hasattr(self, "queryset") and self.queryset is not None:
            queryset = self.queryset
        elif hasattr(self, "get_queryset") and self.get_queryset != ReadOnlyHospitalScopedViewSet.get_queryset:
            queryset = super(viewsets.ReadOnlyModelViewSet, self).get_queryset()
        else:
            queryset = self.get_serializer().Meta.model.objects.all()

        hospital_ids = get_user_hospital_ids(self.request.user)

        if not hospital_ids:
            return queryset.none()

        if hasattr(queryset.model, "hospital"):
            return queryset.filter(hospital_id__in=hospital_ids)

        if hasattr(queryset.model, "patient"):
            return queryset.filter(
                patient__hospital_memberships__hospital_id__in=hospital_ids,
                patient__hospital_memberships__is_active=True
            ).distinct()

        if hasattr(queryset.model, "visit"):
            return queryset.filter(
                visit__hospital_id__in=hospital_ids
            )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Add scoped_hospital to context for serializers that need it
        # Handle both DRF Request (query_params) and Django WSGIRequest (GET)
        # Also check request.data for POST/PUT/PATCH requests
        hospital_id = None
        if hasattr(self.request, 'query_params'):
            hospital_id = self.request.query_params.get("hospital")
        elif hasattr(self.request, 'GET'):
            hospital_id = self.request.GET.get("hospital")
        
        # Also check request.data for POST/PUT/PATCH
        if not hospital_id and hasattr(self.request, 'data'):
            hospital_id = self.request.data.get("hospital")
        
        if hospital_id:
            try:
                context["scoped_hospital"] = Hospital.objects.get(pk=hospital_id)
            except Hospital.DoesNotExist:
                pass
        return context