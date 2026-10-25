"""Write audit events. Never raises: an audit failure must not break care."""

import json
import logging

logger = logging.getLogger(__name__)

# Field names whose values are never copied into audit details.
_REDACT = {"password", "otp", "otp_code", "code", "token", "access", "refresh", "secret", "api_key"}


def _client_ip(request):
    if request is None:
        return None
    from config.client_ip import client_ip

    return client_ip(request)


def _resolve_hospital(obj, hospital):
    if hospital is not None or obj is None:
        return hospital
    from users.viewsets import hospital_id_of, resolve_hospital_lookup

    return hospital_id_of(obj, resolve_hospital_lookup(type(obj)))


def record_audit(request, action, obj=None, hospital=None, details=None, user=None):
    """
    Store who did ``action`` to ``obj`` and when. ``hospital`` may be a
    Hospital or an id; it is derived from ``obj`` when omitted.
    """
    from audit.models import AuditLog

    try:
        actor = user or getattr(request, "user", None)
        if actor is not None and not getattr(actor, "is_authenticated", False):
            actor = None
        hospital = _resolve_hospital(obj, hospital)
        hospital_id = getattr(hospital, "pk", hospital)
        if isinstance(details, dict):
            details = json.dumps(
                {k: ("[redacted]" if k.lower() in _REDACT else v) for k, v in details.items()},
                default=str,
            )
        AuditLog.objects.create(
            user=actor,
            hospital_id=hospital_id,
            action=action[:100],
            model_name=obj._meta.label if obj is not None else "",
            object_id=str(getattr(obj, "pk", "") or ""),
            details=details or "",
            ip_address=_client_ip(request),
        )
    except Exception:  # pragma: no cover - logged, never propagated
        logger.exception("Failed to write audit event %s", action)
