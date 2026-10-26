import logging
from collections import deque
from functools import lru_cache

from django.db import models
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from hospital.models import Hospital
from users.doctor_scope import limit_to_patients_in_care, may_write_for_patients
from users.permissions import (
    IsStaffUser,
    IsHospitalMember,
    get_request_hospital_id,
    get_user_hospital_ids,
    get_user_active_hospital_memberships,
    get_linked_patient,
    is_active_staff,
)

logger = logging.getLogger(__name__)

HOSPITAL_LABEL = "hospital.Hospital"
# Relations that never decide which hospital owns a row. A patient is a
# shared identity across hospitals and a user/staff profile can belong to
# several, so following them would let Hospital A see Hospital B's rows.
_NON_OWNING_TARGETS = {"patients.Patient", "auth.User", "users.StaffProfile"}


@lru_cache(maxsize=None)
def resolve_hospital_lookup(model):
    """
    ORM path from ``model`` to the id of the hospital that owns a row, e.g.
    ``"hospital_id"``, ``"prescription__hospital_id"`` or
    ``"room__ward__hospital_id"``. Returns None when no owning path exists.
    """
    if model._meta.label == HOSPITAL_LABEL:
        return "id"
    queue = deque([(model, "")])
    seen = {model}
    while queue:
        current, prefix = queue.popleft()
        if prefix.count("__") >= 3:
            continue
        relations = [
            f for f in current._meta.concrete_fields
            if isinstance(f, (models.ForeignKey, models.OneToOneField))
        ]
        for field in relations:
            if field.related_model._meta.label == HOSPITAL_LABEL:
                return f"{prefix}{field.name}_id"
        for field in relations:
            target = field.related_model
            if target in seen or target._meta.label in _NON_OWNING_TARGETS:
                continue
            seen.add(target)
            queue.append((target, f"{prefix}{field.name}__"))
    return None


def hospital_id_of(obj, lookup):
    """Follow ``lookup`` on an instance and return the owning hospital id."""
    if obj is None or not lookup:
        return None
    parts = lookup.split("__")
    current = obj
    for part in parts[:-1]:
        current = getattr(current, part, None)
        if current is None:
            return None
    return getattr(current, parts[-1], None)


def _with_scoped_hospital(view, context):
    # Serializers that need the acting hospital get it only after the
    # membership check, so a foreign hospital id is never trusted here.
    try:
        hospital_id = get_request_hospital_id(view.request, view)
    except ValidationError:
        hospital_id = None
    if hospital_id and hospital_id in get_user_hospital_ids(view.request.user):
        context["scoped_hospital"] = Hospital.objects.filter(pk=hospital_id).first()
    return context


class HospitalScopedViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that scopes every query and write to the hospitals the user
    is an active member of. It fails closed: a model with no resolvable
    owning hospital returns no rows unless the view marks it ``tenant_global``.

    The acting hospital comes from ``?hospital=``, a ``hospital`` body field,
    or the ``X-Hospital-ID`` header (see ``get_request_hospital_id``). When it
    is present, results are limited to that one hospital.
    """

    permission_classes = [IsAuthenticated, IsStaffUser, IsHospitalMember]
    # Explicit ORM path to the owning hospital id; resolved automatically if None.
    hospital_lookup = None
    # Platform reference data (templates, schemas) that no hospital owns.
    tenant_global = False

    def _base_queryset(self):
        if getattr(self, "queryset", None) is not None:
            return self.queryset.all()
        return self.get_serializer_class().Meta.model.objects.all()

    def get_hospital_lookup(self, model=None):
        if self.hospital_lookup:
            return self.hospital_lookup
        if model is None:
            model = self._base_queryset().model
        return resolve_hospital_lookup(model)

    def get_object_hospital_id(self, obj):
        if self.tenant_global:
            return None
        return hospital_id_of(obj, self.get_hospital_lookup(type(obj)))

    def get_acting_hospital_ids(self):
        """
        Hospital ids this request may touch, narrowed by the acting hospital.
        Without one, only hospitals where this view's permissions pass for the
        role held there: a Doctor in A who is a Receptionist in B must not
        list B's clinical rows just by leaving out the hospital.
        """
        hospital_ids = get_user_hospital_ids(self.request.user)
        acting = get_request_hospital_id(self.request, self)
        if acting is not None:
            return [acting] if acting in hospital_ids else []
        return [h for h in hospital_ids if self._permitted_in_hospital(h)]

    def _permitted_in_hospital(self, hospital_id):
        # Permission classes read the acting hospital through
        # get_request_hospital_id, which caches it on the request; evaluate
        # them as if this hospital had been sent, then restore the cache.
        request = self.request
        saved = getattr(request, "_hms_hospital_id", None)
        request._hms_hospital_id = hospital_id
        try:
            return all(p.has_permission(request, self) for p in self.get_permissions())
        finally:
            request._hms_hospital_id = saved

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
        queryset = self._base_queryset()

        linked_patient = get_linked_patient(self.request.user)
        if linked_patient and not is_active_staff(self.request.user):
            queryset = self._queryset_for_linked_patient(queryset, linked_patient)
            acting = get_request_hospital_id(self.request, self)
            lookup = self.get_hospital_lookup(queryset.model)
            if acting is not None and lookup and not self.tenant_global:
                queryset = queryset.filter(**{lookup: acting})
            return queryset

        if self.tenant_global:
            return queryset if get_user_hospital_ids(self.request.user) else queryset.none()

        hospital_ids = self.get_acting_hospital_ids()
        if not hospital_ids:
            return queryset.none()

        lookup = self.get_hospital_lookup(queryset.model)
        if not lookup:
            logger.error(
                "No owning-hospital path for %s in %s; returning no rows.",
                queryset.model._meta.label, type(self).__name__,
            )
            return queryset.none()
        queryset = queryset.filter(**{f"{lookup}__in": hospital_ids})
        return limit_to_patients_in_care(
            queryset, self.request.user, hospital_ids,
            lambda ids: models.Q(**{f"{lookup}__in": list(ids)}),
        )

    # ------------------------------------------------------------------
    # Writes: every related row and the row's own hospital must be in scope
    # ------------------------------------------------------------------

    def _default_hospital(self):
        acting = get_request_hospital_id(self.request, self)
        allowed = get_user_hospital_ids(self.request.user)
        if acting is not None:
            if acting not in allowed:
                raise PermissionDenied("You are not a member of that hospital.")
            return Hospital.objects.get(pk=acting)
        if len(allowed) == 1:
            return Hospital.objects.get(pk=allowed[0])
        return None

    def _check_tenancy(self, validated_data, instance=None):
        if self.tenant_global:
            return {}
        allowed = set(get_user_hospital_ids(self.request.user))
        model = self._base_queryset().model
        extra = {}

        own_hospital = validated_data.get("hospital")
        if own_hospital is None and instance is not None:
            own_hospital = getattr(instance, "hospital", None)
        has_hospital_field = any(f.name == "hospital" for f in model._meta.concrete_fields)
        if has_hospital_field and own_hospital is None and instance is None:
            own_hospital = self._default_hospital()
            if own_hospital is not None:
                extra["hospital"] = own_hospital
        own_id = getattr(own_hospital, "pk", own_hospital)
        if own_id is not None and own_id not in allowed:
            raise PermissionDenied("You are not a member of that hospital.")

        owners = set() if own_id is None else {own_id}
        for name, value in validated_data.items():
            if not isinstance(value, models.Model) or isinstance(value, Hospital):
                continue
            label = value._meta.label
            if label == "patients.Patient":
                target = own_id or get_request_hospital_id(self.request, self)
                memberships = value.hospital_memberships.filter(is_active=True)
                if target is not None:
                    ok = memberships.filter(hospital_id=target).exists() or value.hospital_id == target
                else:
                    ok = memberships.filter(hospital_id__in=allowed).exists() or value.hospital_id in allowed
                if not ok:
                    raise ValidationError({name: "Patient is not registered at this hospital."})
                continue
            if label in _NON_OWNING_TARGETS:
                continue
            related_hospital = hospital_id_of(value, resolve_hospital_lookup(type(value)))
            if related_hospital is None:
                continue
            if related_hospital not in allowed:
                raise ValidationError({name: "Object not found."})
            owners.add(related_hospital)
        if len(owners) > 1:
            raise ValidationError("Related records belong to different hospitals.")
        acting = get_request_hospital_id(self.request, self)
        scope = list(owners) or ([acting] if acting is not None else list(allowed))
        if not may_write_for_patients(self.request.user, model, validated_data, scope):
            raise PermissionDenied("This patient is not in your care.")
        return extra

    def _audit(self, verb, obj, details=None):
        from audit.services import record_audit

        record_audit(self.request, f"{obj._meta.label_lower}.{verb}", obj,
                     hospital=self.get_object_hospital_id(obj), details=details)

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        instance = serializer.save(**extra)
        self._audit("create", instance)

    def perform_update(self, serializer):
        self._check_tenancy(serializer.validated_data, instance=serializer.instance)
        before = {
            name: getattr(serializer.instance, name, None)
            for name in serializer.validated_data
            if not isinstance(getattr(serializer.instance, name, None), models.Manager)
        }
        instance = serializer.save()
        # Previous values are kept so corrections to records stay traceable.
        changes = {
            name: {"from": getattr(old, "pk", old), "to": getattr(getattr(instance, name, None), "pk", getattr(instance, name, None))}
            for name, old in before.items()
            if getattr(old, "pk", old) != getattr(getattr(instance, name, None), "pk", getattr(instance, name, None))
        }
        self._audit("update", instance, details={"changes": changes})

    def perform_destroy(self, instance):
        self._audit("delete", instance)
        instance.delete()

    def get_serializer_context(self):
        return _with_scoped_hospital(self, super().get_serializer_context())


class ReadOnlyHospitalScopedViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only version of HospitalScopedViewSet, with the same fail-closed
    scoping rules.
    """

    permission_classes = [IsAuthenticated, IsStaffUser, IsHospitalMember]
    hospital_lookup = None
    tenant_global = False

    _base_queryset = HospitalScopedViewSet._base_queryset
    get_hospital_lookup = HospitalScopedViewSet.get_hospital_lookup
    get_object_hospital_id = HospitalScopedViewSet.get_object_hospital_id
    get_acting_hospital_ids = HospitalScopedViewSet.get_acting_hospital_ids
    _permitted_in_hospital = HospitalScopedViewSet._permitted_in_hospital

    def get_queryset(self):
        queryset = self._base_queryset()
        if self.tenant_global:
            return queryset if get_user_hospital_ids(self.request.user) else queryset.none()
        hospital_ids = self.get_acting_hospital_ids()
        if not hospital_ids:
            return queryset.none()
        lookup = self.get_hospital_lookup(queryset.model)
        if not lookup:
            logger.error("No owning-hospital path for %s; returning no rows.", queryset.model._meta.label)
            return queryset.none()
        return queryset.filter(**{f"{lookup}__in": hospital_ids})

    def get_serializer_context(self):
        return _with_scoped_hospital(self, super().get_serializer_context())
