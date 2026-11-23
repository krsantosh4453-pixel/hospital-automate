"""
Verify the real external providers with the credentials this server has.

    python manage.py check_providers                  # read-only checks only
    python manage.py check_providers --send-sms 98XXXXXXXX
    python manage.py check_providers --verify-sms 98XXXXXXXX 123456
    python manage.py check_providers --send-email someone@example.org
    python manage.py check_providers --llm-sample
    python manage.py check_providers --transcribe sample.wav

The default run sends nothing. Each flag performs one real delivery or
provider call, so use only numbers, addresses and audio you own; the
synthetic LLM sample holds no patient data. Exits 1 when a check fails.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from config.provider_checks import FAIL, run_all_checks
from users.twilio_verify import get_twilio_verify_service, mask_phone

SYNTHETIC_TRANSCRIPT = (
    "Doctor: What brings you in today? Patient: I have had a dry cough and mild fever for three days. "
    "Doctor: Any breathlessness? Patient: No. Doctor: Temperature is 38.1. Chest is clear. "
    "Take paracetamol 500 mg three times a day for three days and come back if the fever persists."
)


class Command(BaseCommand):
    help = "Check the real SMS, e-mail, AI scribe and Google Sign-In providers (read-only unless flags say otherwise)."

    def add_arguments(self, parser):
        parser.add_argument("--send-sms", metavar="PHONE", help="Send a real Twilio Verify OTP to this number.")
        parser.add_argument("--verify-sms", nargs=2, metavar=("PHONE", "CODE"), help="Check a received OTP.")
        parser.add_argument("--send-email", metavar="ADDRESS", help="Send one real test e-mail.")
        parser.add_argument("--llm-sample", action="store_true", help="Draft a note from a synthetic transcript.")
        parser.add_argument("--transcribe", metavar="AUDIO_FILE", help="Transcribe an audio file you own.")

    def handle(self, *args, **options):
        failed = False
        for result in run_all_checks():
            failed |= result.status == FAIL
            self._line(result.status, result.provider, result.detail)

        steps = (
            ("send_sms", self._send_sms), ("verify_sms", self._verify_sms), ("send_email", self._send_email),
            ("llm_sample", self._llm_sample), ("transcribe", self._transcribe),
        )
        for option, step in steps:
            if options.get(option):
                failed |= not step(options[option])
        if failed:
            raise SystemExit(1)

    def _line(self, status, provider, detail):
        style = {"PASS": self.style.SUCCESS, "FAIL": self.style.ERROR}.get(status, self.style.WARNING)
        self.stdout.write(f"{style(status):<8} {provider:<17} {detail}")

    def _send_sms(self, phone):
        result = get_twilio_verify_service().start_verification(phone, channel="sms")
        self._line("PASS" if result.ok else "FAIL", "sms_send",
                   f"to {mask_phone(phone)}: {result.reason} {result.sid or ''}".strip())
        return result.ok

    def _verify_sms(self, args):
        phone, code = args
        result = get_twilio_verify_service().check_verification(phone, code)
        self._line("PASS" if result.ok else "FAIL", "sms_verify", f"{mask_phone(phone)}: {result.reason}")
        return result.ok

    def _send_email(self, address):
        try:
            sent = send_mail("Hospital system e-mail check", "This is a delivery test from check_providers.",
                             settings.DEFAULT_FROM_EMAIL, [address], fail_silently=False)
        except Exception as exc:
            self._line("FAIL", "email_send", type(exc).__name__)
            return False
        backend = settings.EMAIL_BACKEND.rsplit(".", 2)[-2]
        delivered = bool(sent) and backend == "smtp"
        self._line("PASS" if delivered else "FAIL", "email_send",
                   f"accepted by the {backend} backend" + ("" if delivered else " (not a real delivery)"))
        return delivered

    def _llm_sample(self, _flag):
        from ai_scribe.services.llm import LLMClinicalService, LLMGenerationError

        service = LLMClinicalService()
        if service._default_provider in (None, "development"):
            self._line("FAIL", "llm_draft", f"no real LLM provider (default: {service._default_provider})")
            return False
        try:
            draft = service.generate_clinical_draft(SYNTHETIC_TRANSCRIPT, patient_context={"age": 40, "gender": "Other"})
        except LLMGenerationError as exc:
            self._line("FAIL", "llm_draft", str(exc))
            return False
        sections = sorted(k for k, v in (draft.get("structured_extraction") or {}).items() if v)
        self._line("PASS", "llm_draft", f"{draft.get('provider')}/{draft.get('model')}; schema-valid sections: {sections}")
        return True

    def _transcribe(self, audio_file):
        from ai_scribe.services.stt import SpeechToTextService, TranscriptionError

        service = SpeechToTextService()
        if service._default_provider in (None, "development"):
            self._line("FAIL", "stt_transcribe", f"no real STT provider (default: {service._default_provider})")
            return False
        try:
            result = service.transcribe(audio_file, language="auto")
        except TranscriptionError as exc:
            self._line("FAIL", "stt_transcribe", str(exc))
            return False
        self._line("PASS", "stt_transcribe",
                   f"{result.provider}/{result.model}: {len(result.text)} characters, language {result.detected_language}")
        return True
