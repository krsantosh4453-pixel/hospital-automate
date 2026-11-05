"""
Queue and place voice-call fallbacks for failed SMS/WhatsApp notifications.

A call is queued when an SMS/WhatsApp message of a notification finally
failed (after its retries) for a reason other than the patient opting out,
voice was not already one of its channels, and the patient consented to voice
calls. One call at most per patient and event within DEDUPE_WINDOW, so SMS and
WhatsApp both failing ring once. The Celery task
``notifications.tasks.place_voice_call`` dials after FIRST_CALL_DELAY_SECONDS
and with retries; if a text message or call reached the patient meanwhile, the
call is skipped.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .providers import NotificationChannel
from .voice import NOT_CONFIGURED, get_voice_call_provider, to_e164

logger = logging.getLogger(__name__)

TEXT_CHANNELS = (NotificationChannel.SMS, NotificationChannel.WHATSAPP)
OPTED_OUT = "Consent not granted"
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 300
# Time for another text channel still retrying to get through before dialling.
FIRST_CALL_DELAY_SECONDS = 600
DEDUPE_WINDOW = timedelta(minutes=30)
DELIVERED_BY_TEXT = "Reached the patient by text or call in the meantime"


def spoken_message(hospital_name, title):
    """What the call says: the notification title only, never its clinical body."""
    who = f"This is {hospital_name}." if hospital_name else "This is your hospital."
    return (f"Hello. {who} We could not reach you by text message. {title}. "
            "Please check the patient portal or call the hospital.")[:500]


def _failure_reason(results):
    text = [r for r in results if r.channel in TEXT_CHANNELS]
    if not text or any(r.success for r in text) or all(r.error == OPTED_OUT for r in text):
        return None
    return "; ".join(f"{r.channel.value}: {r.error or 'failed'}" for r in text)[:255]


def queue_voice_fallback(engine, payload, results):
    """Create a VoiceCallFallback for ``payload`` if its text delivery failed; never raises."""
    from notifications.models import VoiceCallFallback
    from patients.models import Patient

    try:
        reason = _failure_reason(results)
        if reason is None or NotificationChannel.VOICE in payload.channels:
            return None
        patient = Patient.objects.select_related("hospital").filter(pk=payload.patient_id).first()
        if patient is None:
            return None
        recent = timezone.now() - DEDUPE_WINDOW
        if VoiceCallFallback.objects.filter(patient=patient, event=payload.event.value, created_at__gte=recent).exists():
            return None
        hospital = patient.hospital if patient.hospital_id == payload.hospital_id else None
        row = VoiceCallFallback(
            hospital_id=payload.hospital_id, patient=patient, event=payload.event.value, reason=reason,
            message=spoken_message(getattr(hospital, "name", ""), payload.title),
        )
        if not engine.check_consent(payload.patient_id, payload.event, NotificationChannel.VOICE, payload.hospital_id):
            row.status, row.error = VoiceCallFallback.Status.SKIPPED, "No consent for voice calls"
        elif not to_e164(patient.phone):
            row.status, row.error = VoiceCallFallback.Status.SKIPPED, "Patient has no usable phone number"
        row.save()
        if row.status == VoiceCallFallback.Status.QUEUED:
            from notifications.tasks import place_voice_call

            transaction.on_commit(lambda: place_voice_call.apply_async(args=[row.pk], countdown=FIRST_CALL_DELAY_SECONDS))
        return row
    except Exception:
        logger.exception("Could not queue a voice-call fallback")
        return None


def _record_delivery(row, status, error="", call_id=""):
    from notifications.models import NotificationDelivery

    NotificationDelivery.objects.create(
        hospital_id=row.hospital_id, patient_id=row.patient_id, event=row.event,
        channel=NotificationChannel.VOICE.value, status=status, error=error[:255], provider_message_id=call_id[:100],
    )


def _reached_meanwhile(row):
    """True if a text message or call for the same event reached the patient around this fallback."""
    from notifications.models import NotificationDelivery

    channels = [c.value for c in TEXT_CHANNELS] + [NotificationChannel.VOICE.value]
    return NotificationDelivery.objects.filter(
        patient_id=row.patient_id, event=row.event, channel__in=channels,
        status=NotificationDelivery.Status.SENT, attempted_at__gte=row.created_at - DEDUPE_WINDOW,
    ).exists()


def place_queued_call(row_id, provider=None):
    """
    Dial one queued fallback. Returns True when the task should retry
    (a transient failure with attempts left).
    """
    from notifications.models import NotificationDelivery, VoiceCallFallback

    provider = provider or get_voice_call_provider()
    with transaction.atomic():
        row = VoiceCallFallback.objects.select_for_update().select_related("patient").filter(
            pk=row_id, status=VoiceCallFallback.Status.QUEUED
        ).first()
        if row is None:
            return False
        row.provider = provider.name
        if _reached_meanwhile(row):
            row.status, row.error = VoiceCallFallback.Status.SKIPPED, DELIVERED_BY_TEXT
            row.save(update_fields=["provider", "status", "error"])
            return False
        if not provider.is_configured():
            row.status, row.error = VoiceCallFallback.Status.SKIPPED, NOT_CONFIGURED
            row.save(update_fields=["provider", "status", "error"])
            _record_delivery(row, NotificationDelivery.Status.SKIPPED, NOT_CONFIGURED)
            return False
        result = provider.place_call(to_e164(row.patient.phone), row.message)
        row.attempts += 1
        if result.success:
            row.status, row.provider_call_id, row.error = VoiceCallFallback.Status.PLACED, result.call_id, ""
            row.placed_at = timezone.now()
            _record_delivery(row, NotificationDelivery.Status.SENT, call_id=result.call_id)
        else:
            row.error = result.error[:255]
            if row.attempts >= MAX_ATTEMPTS:
                row.status = VoiceCallFallback.Status.FAILED
                _record_delivery(row, NotificationDelivery.Status.FAILED, result.error)
        row.save()
        return row.status == VoiceCallFallback.Status.QUEUED
