"""
Sensitive-read auditing: which staff member looked at which patients' data.

Every successful list or detail read of a patient-related model through the
hospital-scoped viewsets writes one AuditLog row (``<model>.list`` or
``<model>.read``) holding the ids of the patients on the returned page.
Patients reading their own records and models that are not about a patient
(beds, stock, schedules) are not logged. Rows reached only through a
break-glass grant are listed separately so they can be reviewed.
"""

import logging

from audit.services import record_audit
from users.care_scope import resolve_patient_lookup
from users.permissions import get_request_hospital_id, is_active_staff

logger = logging.getLogger(__name__)

# Upper bound on the rows and patient ids copied into one audit row.
MAX_AUDITED_PATIENTS = 200


def audit_patient_read(view, verb, pks, obj=None):
    """Record that ``view.request.user`` read the rows with these primary keys. Never raises."""
    try:
        _record(view, verb, pks, obj)
    except Exception:  # pragma: no cover - logged, never propagated
        logger.exception("Failed to audit %s read in %s", verb, type(view).__name__)


def _record(view, verb, pks, obj):
    request = view.request
    if not is_active_staff(request.user):
        return
    model = view._base_queryset().model
    lookup = resolve_patient_lookup(model)
    if lookup is None:
        return
    patient_ids = sorted(set(
        model._default_manager.filter(pk__in=pks).exclude(**{f"{lookup}__isnull": True})
        .values_list(lookup, flat=True)
    ))
    if not patient_ids:
        return
    details = {"patient_ids": patient_ids, "patient_count": len(patient_ids)}
    break_glass = _break_glass_patients(request.user, patient_ids)
    if break_glass:
        details["break_glass_patient_ids"] = break_glass
    if obj is not None:
        hospital = view.get_object_hospital_id(obj)
    else:
        hospital = get_request_hospital_id(request, view)
    record_audit(request, f"{model._meta.label_lower}.{verb}", obj, hospital=hospital, details=details)


def _break_glass_patients(user, patient_ids):
    from audit.models import BreakGlassAccess

    return sorted(set(
        BreakGlassAccess.objects.active().filter(user=user, patient_id__in=patient_ids)
        .values_list("patient_id", flat=True)
    ))


class SensitiveReadAuditMixin:
    """Adds read auditing to list and retrieve of a hospital-scoped viewset."""

    def paginate_queryset(self, queryset):
        page = super().paginate_queryset(queryset)
        self._audited_rows = page if page is not None else queryset
        return page

    def list(self, request, *args, **kwargs):
        self._audited_rows = None
        response = super().list(request, *args, **kwargs)
        rows = self._audited_rows
        if response.status_code == 200 and rows is not None:
            if isinstance(rows, list):
                pks = [row.pk for row in rows]
            else:
                pks = rows.values_list("pk", flat=True)[:MAX_AUDITED_PATIENTS]
            audit_patient_read(self, "list", pks)
        return response

    def retrieve(self, request, *args, **kwargs):
        self._retrieved_object = None
        response = super().retrieve(request, *args, **kwargs)
        obj = self._retrieved_object
        if response.status_code == 200 and obj is not None:
            audit_patient_read(self, "read", [obj.pk], obj=obj)
        return response

    def get_object(self):
        obj = super().get_object()
        self._retrieved_object = obj
        return obj
