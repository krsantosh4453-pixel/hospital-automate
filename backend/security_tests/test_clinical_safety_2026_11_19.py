"""
Clinical safety review, 2026-11-19: defects found while preparing the
clinical safety pack, each with the test that proves the fix. Hazard ids
(H-xx) refer to docs/CLINICAL_HAZARD_REGISTER.md. Synthetic data only.
"""

import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from ai_scribe.models import AIConsultationDraft, ConsultationSession, ConversationTranscript
from audit.models import AuditLog
from clinical.medication_safety import check_items
from clinical.models import Allergy, Prescription, PrescriptionItem
from config.hospital_time import hospital_today
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from ipd.models import Admission
from nurses.frequency import INTERVAL, ONCE, PRN, FrequencyError, parse_frequency
from nurses.models import MAR, MARAdministration
from patients.models import Patient, PatientHospital
from pharmacy.models import Medicine
from users.models import StaffRole

from .test_tenant_isolation import make_staff, put_in_care

RX_URL = "/api/clinical/prescriptions/"


def api(user, hospital):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
    return client


class FrequencyParsingTests(SimpleTestCase):
    """H-01: every frequency is either understood exactly or refused."""

    def test_indian_and_latin_abbreviations_give_the_right_interval(self):
        cases = {
            "OD": 24, "od": 24, "Daily": 24, "HS": 24, "BD": 12, "BID": 12, "TDS": 8, "TID": 8,
            "QDS": 6, "QID": 6, "Q8H": 8, "q 6 h": 6, "Every 4 hours": 4, "EOD": 48, "Alternate day": 48,
            "WEEKLY": 168, "Once weekly": 168,
            "1-0-1": 12, "1-1-1": 8, "0-0-1": 24, "1-1-1-1": 6, "½-0-½": 12, "1 - 0 - 1": 12,
        }
        for text, hours in cases.items():
            with self.subTest(text=text):
                parsed = parse_frequency(text)
                self.assertEqual((parsed.kind, parsed.interval_hours), (INTERVAL, hours))

    def test_as_needed_and_single_doses_are_not_scheduled_repeatedly(self):
        for text in ("PRN", "SOS", "prn for pain", "As needed"):
            with self.subTest(text=text):
                self.assertEqual(parse_frequency(text).kind, PRN)
        for text in ("STAT", "Once", "single dose"):
            with self.subTest(text=text):
                self.assertEqual(parse_frequency(text).kind, ONCE)

    def test_unknown_or_impossible_frequencies_are_refused(self):
        # Before the fix all of these became "once daily", and Q0H never finished.
        for text in ("", "  ", "Q0H", "Q200H", "0-0-0", "1-0-1 after food", "as directed", "twice", "Q4-6H"):
            with self.subTest(text=text):
                with self.assertRaises(FrequencyError):
                    parse_frequency(text)


class MARSchedulingTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic MAR Review", is_active=True)
        self.nurse, _ = make_staff("rv_nurse", self.hospital, role=StaffRole.NURSE)
        self.doctor, _ = make_staff("rv_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.patient = Patient.objects.create(name="Synthetic Review Patient", age=64, gender="Female",
                                              phone="9000001901", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="RV-1")
        self.admission = Admission.objects.create(patient=self.patient, hospital=self.hospital, status="Admitted")
        put_in_care(self.doctor, self.hospital, self.patient)
        self.rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient)
        self.item = PrescriptionItem.objects.create(prescription=self.rx, name="Synthetic Methotrexate",
                                                    dosage="7.5 mg", frequency="WEEKLY")
        self.doctor_api = api(self.doctor, self.hospital)
        self.nurse_api = api(self.nurse, self.hospital)

    def order(self, frequency, days=14):
        return MAR.objects.create(
            patient=self.patient, admission=self.admission, hospital=self.hospital, prescription=self.rx,
            prescription_item=self.item, medicine_name="Synthetic Methotrexate", dose="7.5 mg", route="Oral",
            frequency=frequency, start_date=hospital_today(), end_date=hospital_today() + timedelta(days=days),
        )

    def schedule(self, mar, **body):
        return self.doctor_api.post(f"/api/nurses/mar/{mar.id}/generate_schedule/", body, format="json")

    def doses(self, mar):
        return MARAdministration.objects.filter(mar=mar).order_by("scheduled_time")

    def test_weekly_order_is_not_scheduled_daily(self):
        mar = self.order("WEEKLY")
        # No rounds configured here, so a weekly order needs an explicit first dose.
        self.assertEqual(self.schedule(mar, first_dose="now").status_code, 200)
        times = list(self.doses(mar).values_list("scheduled_time", flat=True))
        self.assertEqual(len(times), 3)  # day 0, 7 and 14; daily scheduling gave 15
        self.assertEqual(times[1] - times[0], timedelta(days=7))

    def test_indian_twice_daily_notation_is_scheduled_twice_a_day(self):
        mar = self.order("1-0-1", days=1)
        self.assertEqual(self.schedule(mar).status_code, 200)
        times = list(self.doses(mar).values_list("scheduled_time", flat=True))
        self.assertEqual(times[1] - times[0], timedelta(hours=12))

    def test_stat_order_gets_one_dose_and_regenerating_never_adds_another(self):
        mar = self.order("STAT")
        self.schedule(mar)
        self.assertEqual(self.doses(mar).count(), 1)
        dose = self.doses(mar).first()
        self.assertEqual(self.nurse_api.post(f"/api/nurses/mar-administrations/{dose.id}/administer/", {},
                                             format="json").status_code, 200)
        self.schedule(mar)
        self.assertEqual(self.doses(mar).count(), 1)

    def test_unrecognised_frequency_is_refused_not_guessed(self):
        mar = self.order("Q0H")  # an older row typed before validation existed
        resp = self.schedule(mar)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(self.doses(mar).exists())

    def test_doctor_cannot_save_an_order_with_an_unknown_frequency(self):
        body = {"patient": self.patient.id, "admission": self.admission.id, "hospital": self.hospital.id,
                "prescription": self.rx.id, "prescription_item": self.item.id, "medicine_name": "Synthetic",
                "dose": "1 tab", "route": "Oral", "frequency": "as directed",
                "start_date": hospital_today().isoformat()}
        resp = self.doctor_api.post("/api/nurses/mar/", body, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("frequency", str(resp.content))
        body["frequency"] = "TDS"
        self.assertEqual(self.doctor_api.post("/api/nurses/mar/", body, format="json").status_code, 201)

    def test_sos_order_records_prn_doses_and_is_not_auto_scheduled(self):
        mar = self.order("SOS")
        self.schedule(mar)
        self.assertFalse(self.doses(mar).exists())
        resp = self.nurse_api.post(f"/api/nurses/mar/{mar.id}/prn/", {"notes": "Pain 7/10"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_start_time_without_a_zone_is_the_hospital_clock(self):
        """A doctor's 08:00 means 08:00 at the hospital (Asia/Kolkata), not 08:00 UTC (13:30 IST)."""
        mar = self.order("OD", days=2)
        # Tomorrow: a first dose in the past is refused (first-dose scheduling fix).
        start = f"{(hospital_today() + timedelta(days=1)).isoformat()}T08:00"
        resp = self.doctor_api.post(f"/api/nurses/mar/{mar.id}/generate_schedule/", {"start_date": start},
                                    format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        first = self.doses(mar).first().scheduled_time.astimezone(ZoneInfo("Asia/Kolkata"))
        self.assertEqual((first.hour, first.minute), (8, 0))

    def test_stopped_order_cannot_be_scheduled(self):
        mar = self.order("BD")
        mar.is_active = False
        mar.save(update_fields=["is_active"])
        self.assertEqual(self.schedule(mar).status_code, 400)
        self.assertFalse(self.doses(mar).exists())

    def test_a_future_dose_cannot_be_recorded_as_given_or_missed_early(self):
        """H-02: recording tomorrow's dose now would lead to a second dose being given."""
        mar = self.order("BD", days=2)
        early = MARAdministration.objects.create(mar=mar, scheduled_time=timezone.now() + timedelta(hours=5))
        soon = MARAdministration.objects.create(mar=mar, scheduled_time=timezone.now() + timedelta(minutes=30))
        base = "/api/nurses/mar-administrations"
        resp = self.nurse_api.post(f"{base}/{early.id}/administer/", {}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(self.nurse_api.post(f"{base}/{early.id}/mark_missed/", {}, format="json").status_code, 400)
        early.refresh_from_db()
        self.assertEqual(early.status, MARAdministration.SCHEDULED)
        self.assertEqual(self.nurse_api.post(f"{base}/{soon.id}/administer/", {}, format="json").status_code, 200)


class PrescriptionChangeTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Rx Review", is_active=True)
        self.doctor_user, _ = make_staff("rv_rx_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.nurse, _ = make_staff("rv_rx_nurse", self.hospital, role=StaffRole.NURSE)
        self.patient = Patient.objects.create(name="Synthetic Rx Patient", age=58, gender="Male",
                                              phone="9000001902", hospital=self.hospital)
        self.doctor = put_in_care(self.doctor_user, self.hospital, self.patient)
        self.doctor_api = api(self.doctor_user, self.hospital)

    def write(self, *names):
        resp = self.doctor_api.post(RX_URL, {
            "hospital": self.hospital.id, "patient": self.patient.id,
            "items": [{"name": name, "dosage": "1 tab", "frequency": "BD", "quantity": 10} for name in names],
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        return Prescription.objects.get(pk=resp.json()["id"])

    def test_editing_a_prescription_never_erases_the_medication_administration_record(self):
        """H-03: replacing the lines used to cascade-delete MAR orders and every recorded dose."""
        rx = self.write("Synthetic Ceftriaxone")
        item = rx.items.get()
        admission = Admission.objects.create(patient=self.patient, hospital=self.hospital, status="Admitted")
        mar = MAR.objects.create(patient=self.patient, admission=admission, hospital=self.hospital, prescription=rx,
                                 prescription_item=item, medicine_name=item.name, dose="1 g", route="IV",
                                 frequency="BD", start_date=hospital_today())
        dose = MARAdministration.objects.create(mar=mar, scheduled_time=timezone.now(), status="Administered",
                                                administered_time=timezone.now(), recorded_by=self.nurse)

        resp = self.doctor_api.patch(f"{RX_URL}{rx.pk}/", {"items": [{"name": "Synthetic Other", "quantity": 1}]},
                                     format="json")

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("medication order", str(resp.content).lower())
        self.assertTrue(MAR.objects.filter(pk=mar.pk).exists())
        self.assertTrue(MARAdministration.objects.filter(pk=dose.pk, status="Administered").exists())
        self.assertEqual(rx.items.get().name, "Synthetic Ceftriaxone")

    def test_editing_without_mar_orders_still_works(self):
        rx = self.write("Synthetic Paracetamol")
        resp = self.doctor_api.patch(f"{RX_URL}{rx.pk}/", {"items": [{"name": "Synthetic Cetirizine", "quantity": 5}]},
                                     format="json")
        self.assertEqual(resp.status_code, 200, resp.content)


class PaperReverificationTests(TestCase):
    """H-04: a verified paper prescription changed afterwards needs a second check again."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Paper Review", is_active=True)
        self.first, _ = make_staff("rv_pharm_a", self.hospital, role=StaffRole.PHARMACIST)
        self.second, _ = make_staff("rv_pharm_b", self.hospital, role=StaffRole.PHARMACIST)
        self.patient = Patient.objects.create(name="Synthetic Paper Review Patient", age=40, gender="Female",
                                              phone="9000001903", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="RV-P1")

    def test_changing_medicines_after_verification_sends_it_back_for_verification(self):
        resp = api(self.first, self.hospital).post(f"{RX_URL}transcribe/", {
            "hospital": self.hospital.id, "patient": self.patient.id,
            "original_prescriber_name": "Dr Outside Synthetic", "original_prescriber_registration": "REG-1",
            "original_prescription_date": str(hospital_today()),
            "items": [{"name": "Paracetamol", "dosage": "500 mg", "frequency": "1-0-1", "quantity": 6}],
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        rx_id = resp.json()["id"]
        self.assertEqual(api(self.second, self.hospital).post(f"{RX_URL}{rx_id}/verify/", {}, format="json")
                         .status_code, 200)

        changed = api(self.first, self.hospital).patch(f"{RX_URL}{rx_id}/", {
            "items": [{"name": "Paracetamol", "dosage": "650 mg", "frequency": "1-1-1", "quantity": 30}],
        }, format="json")

        self.assertEqual(changed.status_code, 200, changed.content)
        rx = Prescription.objects.get(pk=rx_id)
        self.assertEqual(rx.status, Prescription.PENDING_VERIFICATION)
        self.assertIsNone(rx.verified_by_id)
        self.assertEqual(rx.transcribed_by_id, self.first.pk)  # so the editor cannot verify their own change
        self.assertEqual(api(self.first, self.hospital).post(f"{RX_URL}{rx_id}/verify/", {}, format="json")
                         .status_code, 403)
        self.assertEqual(api(self.second, self.hospital).post(f"{RX_URL}{rx_id}/verify/", {}, format="json")
                         .status_code, 200)


class AllergyMatchingTests(TestCase):
    """H-05: an allergy written as a brand name, or one the checker cannot read."""

    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Allergy Review", is_active=True)
        cls.patient = Patient.objects.create(name="Synthetic Allergy Patient", age=33, gender="Female",
                                             phone="9000001904", hospital=cls.hospital)
        Medicine.objects.create(name="Augmentin 625", generic_name="amoxicillin + clavulanic acid",
                                hospital=cls.hospital, quantity=10, price=Decimal("20"))
        Medicine.objects.create(name="Mox 500", generic_name="amoxicillin", hospital=cls.hospital,
                                quantity=10, price=Decimal("5"))

    def test_brand_name_allergy_is_resolved_through_the_catalogue(self):
        Allergy.objects.create(patient=self.patient, hospital=self.hospital, name="Augmentin", reaction="Rash")
        alerts = check_items(self.hospital, self.patient, ["Mox 500"])
        self.assertIn(("allergy", "high"), {(a["type"], a["severity"]) for a in alerts})

    def test_allergy_the_checker_cannot_match_is_shown_as_not_checked(self):
        Allergy.objects.create(patient=self.patient, hospital=self.hospital, name="Synthetic Unknown Drug X")
        alerts = check_items(self.hospital, self.patient, ["Mox 500"])
        unchecked = [a for a in alerts if a["type"] == "allergy_unchecked"]
        self.assertEqual(len(unchecked), 1)
        self.assertEqual(unchecked[0]["severity"], "info")
        self.assertIn("Synthetic Unknown Drug X", unchecked[0]["message"])

    def test_matched_allergy_is_not_also_reported_as_unchecked(self):
        Allergy.objects.create(patient=self.patient, hospital=self.hospital, name="Penicillin")
        alerts = check_items(self.hospital, self.patient, ["Paracetamol 500"])
        self.assertFalse([a for a in alerts if a["type"] == "allergy_unchecked"])


MEDIA = tempfile.mkdtemp(prefix="hms-ai-review-")


@override_settings(MEDIA_ROOT=MEDIA)
class ScribeConsentTests(TestCase):
    """H-06: patient audio reaches the speech-to-text provider only with recorded consent."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Scribe Review", is_active=True)
        self.user, _ = make_staff("rv_ai_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.doctor = Doctor.objects.create(hospital=self.hospital, user=self.user, name="Dr Synthetic Review",
                                            specialization="General", phone="9000001905")
        self.patient = Patient.objects.create(name="Synthetic Scribe Patient", age=50, gender="Male",
                                              phone="9000001906", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="RV-AI1")
        self.visit = Visit.objects.create(patient=self.patient, hospital=self.hospital, doctor=self.doctor)
        self.client = api(self.user, self.hospital)
        resp = self.client.post("/api/ai/consultation-sessions/", {
            "visit": self.visit.id, "hospital": self.hospital.id, "patient": self.patient.id,
            "doctor": self.doctor.id, "language": "en",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.session_id = resp.json()["id"]
        self.base = f"/api/ai/consultation-sessions/{self.session_id}"

    @staticmethod
    def audio():
        return SimpleUploadedFile("c.webm", b"\x1aE\xdf\xa3synthetic", content_type="audio/webm;codecs=opus")

    def test_audio_cannot_be_uploaded_or_transcribed_without_consent(self):
        resp = self.client.post(f"{self.base}/upload_audio/", {"audio_file": self.audio()}, format="multipart")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("consent", str(resp.content).lower())
        session = ConsultationSession.objects.get(pk=self.session_id)
        self.assertFalse(session.audio_file)

        # Even with audio already on the session (an older row), transcription is refused.
        session.audio_file.save("old.webm", self.audio(), save=True)
        resp = self.client.post(f"{self.base}/transcribe/", {}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(ConversationTranscript.objects.filter(consultation_id=self.session_id).exists())

    def test_consented_upload_still_works_and_rejection_is_audited(self):
        self.assertEqual(self.client.post(f"{self.base}/start_recording/", {"patient_consent": True},
                                          format="json").status_code, 200)
        resp = self.client.post(f"{self.base}/upload_audio/", {"audio_file": self.audio()}, format="multipart")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self.client.post(f"{self.base}/transcribe/", {}, format="json").status_code, 200)

        draft = AIConsultationDraft.objects.get(consultation_id=self.session_id)
        resp = self.client.post(f"/api/ai/drafts/{draft.id}/reject/", {"notes": "Wrong patient history"},
                                format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        entry = AuditLog.objects.get(action="ai.draft.rejected", object_id=str(draft.id))
        self.assertIn("Wrong patient history", entry.details)
