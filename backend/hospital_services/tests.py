"""Hospital services (J5, J6, I6) on synthetic data: rules, roles and tenancy."""

from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditLog
from doctors.models import Doctor
from hospital.models import Department, Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

from .models import Ambulance, LeaveRequest, MortuaryRecord, OperatingTheatre, SterileSet, SterilizationCycle

API = "/api/services"


class ServicesCase(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Services", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Elsewhere", is_active=True)
        self.manager, _ = make_staff("sv_manager", self.hospital, role=StaffRole.HOSPITAL_MANAGER)
        self.doctor_user, _ = make_staff("sv_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.nurse, _ = make_staff("sv_nurse", self.hospital, role=StaffRole.NURSE)
        self.desk, _ = make_staff("sv_desk", self.hospital, role=StaffRole.RECEPTIONIST)
        self.store, _ = make_staff("sv_store", self.hospital, role=StaffRole.INVENTORY_STAFF)
        self.outsider, _ = make_staff("sv_outsider", self.other, role=StaffRole.HOSPITAL_MANAGER)
        self.doctor = Doctor.objects.create(hospital=self.hospital, user=self.doctor_user, name="Dr Synthetic",
                                            specialization="Surgery", phone="9000001001")
        self.patient = Patient.objects.create(name="Synthetic Service Patient", age=50, gender="Male",
                                              phone="9000001002", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="SV-1")
        # Clinical roles write only for patients in their care (users/care_scope.py).
        put_in_care(self.doctor_user, self.hospital, self.patient)
        self.ward = Department.objects.create(hospital=self.hospital, name="Ward S")

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).id))
        return client

    def post(self, user, path, body=None):
        return self.client_for(user).post(f"{API}/{path}", body or {}, format="json")


class TheatreTests(ServicesCase):
    def setUp(self):
        super().setUp()
        self.theatre = OperatingTheatre.objects.create(hospital=self.hospital, name="OT 1")
        self.start = timezone.now() + timedelta(days=1)

    def book(self, offset_hours=0, hours=2, user=None):
        start = self.start + timedelta(hours=offset_hours)
        return self.post(user or self.doctor_user, "ot-bookings/", {
            "theatre": self.theatre.id, "patient": self.patient.id, "surgeon": self.doctor.id,
            "procedure_name": "Appendicectomy", "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=hours)).isoformat()})

    def test_no_double_booking_and_the_case_moves_in_order(self):
        first = self.book()
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(self.book(offset_hours=1).status_code, 400)
        self.assertEqual(self.book(offset_hours=2).status_code, 201)  # back to back is fine
        booking = first.json()["id"]
        self.assertEqual(self.post(self.nurse, f"ot-bookings/{booking}/complete/").status_code, 400)
        self.assertEqual(self.post(self.nurse, f"ot-bookings/{booking}/start/").json()["status"], "In progress")
        self.assertEqual(self.post(self.nurse, f"ot-bookings/{booking}/complete/").json()["status"], "Completed")

    def test_cancel_needs_a_reason_and_frees_the_slot_and_nurses_cannot_book(self):
        booking = self.book().json()["id"]
        self.assertEqual(self.post(self.doctor_user, f"ot-bookings/{booking}/cancel/").status_code, 400)
        self.assertEqual(self.post(self.doctor_user, f"ot-bookings/{booking}/cancel/", {"reason": "Unfit"}).status_code, 200)
        self.assertEqual(self.book().status_code, 201)
        self.assertEqual(self.book(offset_hours=5, user=self.nurse).status_code, 403)


class AmbulanceTests(ServicesCase):
    def test_one_trip_per_ambulance_and_it_comes_back_available(self):
        ambulance = Ambulance.objects.create(hospital=self.hospital, vehicle_number="MH01AB1234")
        trips = [self.post(self.desk, "ambulance-trips/", {"caller_name": "Synthetic Caller", "caller_phone": "9000001003",
                                                           "pickup": "Sector 5", "destination": "Hospital"}).json()["id"]
                 for _ in range(2)]
        self.assertEqual(self.post(self.desk, f"ambulance-trips/{trips[0]}/dispatch_trip/",
                                   {"ambulance": ambulance.id, "crew": "Driver A"}).status_code, 200)
        self.assertEqual(self.post(self.desk, f"ambulance-trips/{trips[1]}/dispatch_trip/",
                                   {"ambulance": ambulance.id}).status_code, 400)
        self.assertEqual(self.post(self.desk, f"ambulance-trips/{trips[0]}/complete/").status_code, 200)
        ambulance.refresh_from_db()
        self.assertEqual(ambulance.status, "Available")
        self.assertEqual(self.post(self.desk, f"ambulance-trips/{trips[1]}/dispatch_trip/",
                                   {"ambulance": ambulance.id}).status_code, 200)

    def test_status_on_trip_cannot_be_set_by_hand(self):
        ambulance = Ambulance.objects.create(hospital=self.hospital, vehicle_number="MH01AB9999")
        resp = self.client_for(self.manager).patch(f"{API}/ambulances/{ambulance.id}/", {"status": "On trip"}, format="json")
        self.assertEqual(resp.status_code, 400)


class MortuaryTests(ServicesCase):
    def record(self, police_case=False):
        resp = self.post(self.doctor_user, "mortuary/", {"patient": self.patient.id, "deceased_name": self.patient.name,
                                                   "time_of_death": timezone.now().isoformat(), "storage_unit": "C-2",
                                                   "certified_cause": "As certified", "police_case": police_case})
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()["id"]

    def test_release_needs_a_doctor_or_manager_the_receiver_and_happens_once(self):
        record = self.record()
        body = {"released_to_name": "Synthetic Relative", "released_to_relation": "Son", "released_to_id_last4": "1234"}
        self.assertEqual(self.post(self.nurse, f"mortuary/{record}/release/", body).status_code, 403)
        self.assertEqual(self.post(self.doctor_user, f"mortuary/{record}/release/", {**body, "released_to_id_last4": "12"}).status_code, 400)
        released = self.post(self.doctor_user, f"mortuary/{record}/release/", body)
        self.assertEqual(released.status_code, 200, released.content)
        self.assertEqual(released.json()["release_authorised_by_name"], "sv_doctor")
        self.assertEqual(self.post(self.doctor_user, f"mortuary/{record}/release/", body).status_code, 400)
        entry = AuditLog.objects.get(action="hospital_services.mortuaryrecord.released")
        self.assertNotIn("1234", entry.details)

    def test_medico_legal_case_needs_police_clearance(self):
        record = self.record(police_case=True)
        body = {"released_to_name": "Synthetic Relative", "released_to_relation": "Wife", "released_to_id_last4": "5678"}
        self.assertEqual(self.post(self.doctor_user, f"mortuary/{record}/release/", body).status_code, 400)
        self.assertEqual(self.post(self.doctor_user, f"mortuary/{record}/release/", {**body, "police_reference": "FIR 12/2026"}).status_code, 200)
        self.assertEqual(MortuaryRecord.objects.get().status, "Released")


class CssdLaundryTests(ServicesCase):
    def cycle(self, sterile_set, expires_in=timedelta(days=30), indicator=True):
        now = timezone.now()
        return self.post(self.nurse, "sterilization-cycles/", {
            "sterile_set": sterile_set.id, "method": "Autoclave", "load_number": "L-1", "indicator_passed": indicator,
            "sterilized_at": (now - timedelta(hours=1)).isoformat(), "expires_at": (now + expires_in).isoformat()})

    def test_only_sterile_unexpired_sets_with_a_passed_indicator_are_issued(self):
        kit = SterileSet.objects.create(hospital=self.hospital, name="Major set", code="MS-1")
        cycle = self.cycle(kit).json()["id"]
        self.assertEqual(self.cycle(kit).status_code, 400)  # one live cycle per set
        issued = self.post(self.nurse, f"sterilization-cycles/{cycle}/issue/", {"issued_to": self.ward.id})
        self.assertEqual(issued.json()["status"], "Issued")
        self.assertEqual(self.post(self.nurse, f"sterilization-cycles/{cycle}/issue/", {"issued_to": self.ward.id}).status_code, 400)
        self.assertEqual(self.post(self.nurse, f"sterilization-cycles/{cycle}/return/").json()["status"], "Returned")
        failed = self.cycle(kit, indicator=False).json()["id"]
        self.assertEqual(self.post(self.nurse, f"sterilization-cycles/{failed}/issue/", {"issued_to": self.ward.id}).status_code, 400)
        SterilizationCycle.objects.filter(pk=failed).update(status="Returned")
        stale = self.cycle(kit).json()["id"]
        SterilizationCycle.objects.filter(pk=stale).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.post(self.nurse, f"sterilization-cycles/{stale}/issue/", {"issued_to": self.ward.id}).status_code, 400)

    def test_laundry_return_never_exceeds_what_was_sent_and_shows_the_shortfall(self):
        batch = self.post(self.store, "laundry/", {"department": self.ward.id, "item_type": "Bedsheets", "quantity_sent": 40}).json()["id"]
        self.assertEqual(self.post(self.store, f"laundry/{batch}/returned/", {"quantity_returned": 41}).status_code, 400)
        back = self.post(self.store, f"laundry/{batch}/returned/", {"quantity_returned": 38})
        self.assertEqual(back.json()["shortfall"], 2)
        self.assertEqual(self.post(self.store, f"laundry/{batch}/returned/", {"quantity_returned": 2}).status_code, 400)


class LeaveFeedbackTemplateTests(ServicesCase):
    def test_leave_is_decided_by_someone_else_and_overlaps_are_refused(self):
        start = date.today() + timedelta(days=10)
        body = {"kind": "Casual", "start_date": str(start), "end_date": str(start + timedelta(days=2))}
        mine = self.post(self.nurse, "leave/", body)
        self.assertEqual(mine.status_code, 201, mine.content)
        self.assertEqual(self.post(self.nurse, "leave/", body).status_code, 400)
        own = self.post(self.manager, "leave/", body).json()["id"]
        self.assertEqual(self.post(self.manager, f"leave/{own}/approve/").status_code, 400)
        self.assertEqual(self.post(self.nurse, f"leave/{mine.json()['id']}/approve/").status_code, 403)
        self.assertEqual(self.post(self.manager, f"leave/{mine.json()['id']}/approve/").json()["status"], "Approved")
        # A nurse sees only her own requests; the manager sees everyone's.
        self.assertEqual(len(self.client_for(self.desk).get(f"{API}/leave/").json().get("results", [])), 0)
        self.assertEqual(LeaveRequest.objects.count(), 2)

    def test_feedback_is_recorded_by_staff_and_answered_by_a_manager(self):
        fb = self.post(self.desk, "feedback/", {"patient": self.patient.id, "rating": 2, "category": "Waiting time",
                                                "comments": "Waited 2 hours"})
        self.assertEqual(fb.status_code, 201, fb.content)
        self.assertEqual(self.post(self.desk, "feedback/", {"rating": 6, "category": "Care"}).status_code, 400)
        self.assertEqual(self.post(self.desk, f"feedback/{fb.json()['id']}/respond/", {"response": "x"}).status_code, 403)
        closed = self.post(self.manager, f"feedback/{fb.json()['id']}/respond/", {"response": "Added a counter", "close": True})
        self.assertEqual(closed.json()["status"], "Closed")

    def test_templates_written_by_doctors_read_by_nurses_and_never_across_hospitals(self):
        made = self.post(self.doctor_user, "templates/", {"name": "Post-op advice", "kind": "Discharge advice",
                                                          "body": "Keep the wound dry for {days} days."})
        self.assertEqual(made.status_code, 201, made.content)
        self.assertEqual(self.post(self.nurse, "templates/", {"name": "x", "kind": "Message", "body": "y"}).status_code, 403)
        listed = self.client_for(self.nurse).get(f"{API}/templates/?kind=Discharge advice").json()
        self.assertEqual([t["name"] for t in listed.get("results", listed)], ["Post-op advice"])
        outsider = self.client_for(self.outsider, self.other).get(f"{API}/templates/").json()
        self.assertEqual(outsider.get("results", outsider), [])


class CreateFromScreenTests(ServicesCase):
    def test_theatre_ambulance_and_set_are_created_for_the_acting_hospital_once(self):
        for path, body in (("theatres/", {"name": "OT 9"}), ("ambulances/", {"vehicle_number": "MH09", "kind": "ALS"}),
                           ("sterile-sets/", {"code": "S-9", "name": "Minor set"})):
            with self.subTest(path=path):
                first = self.post(self.manager, path, body)
                self.assertEqual(first.status_code, 201, first.content)
                self.assertEqual(first.json()["hospital"], self.hospital.id)
                self.assertEqual(self.post(self.manager, path, body).status_code, 400)
