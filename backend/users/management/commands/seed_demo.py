"""
Build (or remove) a synthetic "Demo City Hospital" for checking the app by
hand: one login per role, patients, today's OPD queue, admissions, nurse
duty, pharmacy stock (batches marked DEMO-, one near expiry, one expired)
and the bundled list of common ICD-10 codes. Development databases only;
the password is chosen by the person running it and is never printed.
Running it again adds nothing twice.

    python manage.py seed_demo --password <your-choice>
    python manage.py seed_demo --remove
"""

from datetime import time, timedelta
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from appointments.models import Appointment
from billing.models import AdvanceAccount, AdvanceTransaction, Payment
from config.hospital_time import hospital_today
from doctors.models import Doctor
from encounters.models import QueueToken, Visit
from encounters.services.appointment_status import sync_appointment_status
from hospital.models import Bed, Department, Hospital, Room, Ward
from ipd.models import Admission, BedAllocation
from nurses.models import Nurse, NurseWardAssignment
from patients.models import Patient, PatientHospital
from pharmacy.models import Medicine, Sale, SaleReturn
from procurement.models import StockTransaction
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

HOSPITAL_NAME = "Demo City Hospital"
USERNAME_PREFIX = "demo."
EMAIL_DOMAIN = "example.test"
MIN_PASSWORD_LENGTH = 10
# New registrations at the demo hospital get UHIDs like DCH-2026-000001.
DEMO_UHID_PREFIX = "DCH"
DEMO_BATCH_PREFIX = "DEMO-"

# name, generic (salt), category, batch suffix, units, price, GST %, days until expiry.
# Names match what the demo doctors prescribe, so batches are picked automatically.
DEMO_STOCK = (
    ("Paracetamol 500mg", "Paracetamol", "Analgesic", "PCM-01", 200, "2.00", "12", 540),
    ("Paracetamol 500mg", "Paracetamol", "Analgesic", "PCM-02", 30, "2.00", "12", 90),
    ("Cetirizine 10mg", "Cetirizine", "Antihistamine", "CTZ-01", 100, "3.00", "12", 365),
    ("Amoxicillin 500mg", "Amoxicillin", "Antibiotic", "AMX-01", 60, "8.50", "12", 300),
    ("Pantoprazole 40mg", "Pantoprazole", "Antacid", "PAN-01", 80, "6.00", "12", 420),
    ("Metformin 500mg", "Metformin", "Antidiabetic", "MET-01", 120, "1.50", "5", 600),
    ("ORS Sachet", "Oral rehydration salts", "Electrolyte", "ORS-01", 40, "20.00", "0", 240),
    # Shows the expiry warnings: one batch about to expire, one already expired.
    ("Azithromycin 500mg", "Azithromycin", "Antibiotic", "AZI-01", 5, "25.00", "12", 20),
    ("Ibuprofen 400mg", "Ibuprofen", "Analgesic", "IBU-OLD", 25, "2.50", "12", -60),
)

# username, role, department name (or None)
STAFF = (
    ("demo.admin", StaffRole.ADMIN, None),
    ("demo.doctor1", StaffRole.DOCTOR, "Cardiology"),
    ("demo.doctor2", StaffRole.DOCTOR, "Orthopaedics"),
    ("demo.nurse", StaffRole.NURSE, None),
    ("demo.desk", StaffRole.RECEPTIONIST, "Cardiology"),
    ("demo.desk.main", StaffRole.RECEPTIONIST, None),
    ("demo.manager", StaffRole.HOSPITAL_MANAGER, None),
    ("demo.pharmacist", StaffRole.PHARMACIST, None),
    ("demo.compounder", StaffRole.COMPOUNDER, None),
    ("demo.lab", StaffRole.LAB_STAFF, None),
    ("demo.bloodbank", StaffRole.BLOOD_BANK_STAFF, None),
    ("demo.billing", StaffRole.BILLING_STAFF, None),
    ("demo.inventory", StaffRole.INVENTORY_STAFF, None),
)


class Command(BaseCommand):
    help = "Create or remove the synthetic Demo City Hospital (development only)."

    def add_arguments(self, parser):
        parser.add_argument("--password", help=f"Password for every demo login (at least {MIN_PASSWORD_LENGTH} characters).")
        parser.add_argument("--remove", action="store_true", help="Delete the demo hospital and demo logins.")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo runs only on a development server (DEBUG=True).")
        if options["remove"]:
            self._remove()
            return
        password = options.get("password") or ""
        if len(password) < MIN_PASSWORD_LENGTH:
            raise CommandError(f"Give --password with at least {MIN_PASSWORD_LENGTH} characters.")
        with transaction.atomic():
            self._seed(password)
        self._report()

    # ------------------------------------------------------------------

    def _remove(self):
        with transaction.atomic():
            hospital = Hospital.objects.filter(name=HOSPITAL_NAME).first()
            if hospital is not None:
                # Money and stock records are protected from cascades; remove them first, in order.
                AdvanceTransaction.objects.filter(account__hospital=hospital).delete()
                AdvanceAccount.objects.filter(hospital=hospital).delete()
                Payment.objects.filter(invoice__hospital=hospital).delete()
                SaleReturn.objects.filter(hospital=hospital).delete()
                Patient.all_objects.filter(hospital=hospital).delete()
                Sale.objects.filter(hospital=hospital).delete()
                StockTransaction.objects.filter(hospital=hospital).delete()
                Medicine.objects.filter(hospital=hospital).delete()
                hospital.delete()
            get_user_model().objects.filter(username__startswith=USERNAME_PREFIX).delete()
        self.stdout.write(self.style.SUCCESS("Demo hospital and demo logins removed."))

    def _seed(self, password):
        hospital, _ = Hospital.objects.get_or_create(name=HOSPITAL_NAME, defaults={"is_active": True})
        prefix_free = not Hospital.objects.exclude(pk=hospital.pk).filter(uhid_prefix=DEMO_UHID_PREFIX).exists()
        if not hospital.uhid_prefix and prefix_free:
            hospital.uhid_prefix = DEMO_UHID_PREFIX
            hospital.save(update_fields=["uhid_prefix"])
        departments = {
            name: Department.objects.get_or_create(hospital=hospital, name=name)[0]
            for name in ("Cardiology", "Orthopaedics")
        }
        logins = {
            username: self._staff(hospital, username, role, departments.get(dept), password)
            for username, role, dept in STAFF
        }
        doctor1 = self._doctor(hospital, logins["demo.doctor1"], "Dr Asha Mehta", departments["Cardiology"], "9000003001")
        doctor2 = self._doctor(hospital, logins["demo.doctor2"], "Dr Rohan Verma", departments["Orthopaedics"], "9000003002")
        nurse, _ = Nurse.objects.get_or_create(
            hospital=hospital, user=logins["demo.nurse"],
            defaults={"name": "Nurse Priya", "phone": "9000003003", "email": logins["demo.nurse"].email},
        )
        ward_a = self._bed_ward(hospital, "Ward A")
        ward_b = self._bed_ward(hospital, "Ward B")

        self._opd(hospital, self._patient(hospital, "Demo Ravi (Cardiology OPD)", "9000003011"), doctor1, 1)
        self._opd(hospital, self._patient(hospital, "Demo Sunil (Ortho OPD)", "9000003012"), doctor2, 2)
        self._admit(hospital, self._patient(hospital, "Demo Kiran (Ward A)", "9000003013"), doctor1, ward_a)
        self._admit(hospital, self._patient(hospital, "Demo Meena (Ward B)", "9000003014"), doctor2, ward_b)
        NurseWardAssignment.objects.get_or_create(
            nurse=nurse, ward=ward_a, shift="Morning", shift_date=hospital_today(),
            defaults={"hospital": hospital},
        )
        self._portal_patient(hospital, password)
        self._pharmacy_stock(hospital)
        # Reference codes, the same for every hospital: loaded only into an empty table,
        # so a full CMS load is never touched. --remove leaves them in place.
        call_command("load_icd10", "--if-empty", stdout=StringIO())

    def _staff(self, hospital, username, role, department, password):
        user = self._login(username, password)
        profile, _ = StaffProfile.objects.get_or_create(
            user=user, defaults={"role": role, "employee_id": f"EMP-{username}", "is_active_staff": True},
        )
        # No mobile number: these logins sign in with the password alone.
        StaffHospitalMembership.objects.update_or_create(
            staff=profile, hospital=hospital, defaults={"role": role, "department": department, "is_active": True},
        )
        return user

    def _login(self, username, password):
        user, _ = get_user_model().objects.get_or_create(
            username=username, defaults={"email": f"{username}@{EMAIL_DOMAIN}"},
        )
        user.set_password(password)
        user.is_active = True
        user.save()
        return user

    def _doctor(self, hospital, user, name, department, phone):
        doctor, _ = Doctor.objects.get_or_create(
            hospital=hospital, user=user,
            defaults={"name": name, "specialization": department.name, "department": department,
                      "phone": phone, "email": user.email, "availability": "Mon-Sat 09:00-17:00"},
        )
        return doctor

    def _bed_ward(self, hospital, name):
        ward, _ = Ward.objects.get_or_create(hospital=hospital, name=name)
        room, _ = Room.objects.get_or_create(ward=ward, room_number=f"{name[-1]}-101")
        Bed.objects.get_or_create(room=room, bed_number="1", defaults={"status": "Available"})
        return ward

    def _patient(self, hospital, name, phone):
        patient, _ = Patient.objects.get_or_create(
            hospital=hospital, name=name, defaults={"age": 45, "gender": "Female", "phone": phone},
        )
        PatientHospital.objects.get_or_create(patient=patient, hospital=hospital, defaults={"uhid": f"DEMO-{phone}"})
        return patient

    def _opd(self, hospital, patient, doctor, number):
        today = hospital_today()
        appointment, _ = Appointment.objects.get_or_create(
            hospital=hospital, patient=patient, doctor=doctor, appointment_date=today,
            defaults={"appointment_time": time(10, number * 15 % 60), "status": "Scheduled"},
        )
        if not QueueToken.objects.filter(hospital=hospital, patient=patient, token_date=today).exists():
            visit = Visit.objects.create(hospital=hospital, patient=patient, doctor=doctor)
            # Linked to its appointment, or the queue offers that appointment a second token.
            token = QueueToken.objects.create(hospital=hospital, visit=visit, patient=patient, doctor=doctor,
                                              appointment=appointment, token_date=today, token_number=number)
            sync_appointment_status(token)

    def _admit(self, hospital, patient, doctor, ward):
        admission, _ = Admission.objects.get_or_create(
            hospital=hospital, patient=patient,
            defaults={"admitting_doctor": doctor, "status": "Admitted", "reason": "Demo observation"},
        )
        bed = Bed.objects.get(room__ward=ward, bed_number="1")
        if not BedAllocation.objects.filter(admission=admission, is_active=True).exists():
            BedAllocation.objects.create(admission=admission, bed=bed)
            Bed.objects.filter(pk=bed.pk).update(status="Occupied")

    def _portal_patient(self, hospital, password):
        user = self._login("demo.patient", password)
        patient, _ = Patient.objects.get_or_create(
            user=user,
            defaults={"hospital": hospital, "name": "Demo Portal Patient", "age": 30, "gender": "Male",
                      "phone": "9000003020", "email_verified": True},
        )
        PatientHospital.objects.get_or_create(patient=patient, hospital=hospital, defaults={"uhid": "DEMO-PORTAL"})

    def _pharmacy_stock(self, hospital):
        today = hospital_today()
        for name, generic, category, batch, units, price, gst, days in DEMO_STOCK:
            medicine, created = Medicine.objects.get_or_create(
                hospital=hospital, name=name, batch=f"{DEMO_BATCH_PREFIX}{batch}",
                defaults={"generic_name": generic, "category": category, "quantity": units,
                          "price": Decimal(price), "tax_rate": Decimal(gst),
                          "expiry_date": today + timedelta(days=days)},
            )
            if created:
                # Same ledger entry the pharmacy page writes for new stock.
                StockTransaction.objects.create(
                    medicine=medicine, hospital=hospital, transaction_type=StockTransaction.TYPE_IN,
                    quantity=units, reason="Opening stock (demo)", reference=f"MED-{medicine.pk}",
                )

    def _report(self):
        self.stdout.write(self.style.SUCCESS(f"{HOSPITAL_NAME} is ready. Every login uses the password you gave."))
        for username, role, dept in STAFF:
            self.stdout.write(f"  Staff login  {username:<16} {role}{f' ({dept})' if dept else ''}")
        self.stdout.write(f"  Patient login  demo.patient@{EMAIL_DOMAIN} (patient portal, Email tab)")
        self.stdout.write(f"  Pharmacy stock {len(DEMO_STOCK)} demo batches ({DEMO_BATCH_PREFIX}...); "
                          f"new patients get {DEMO_UHID_PREFIX}-<year>-<number> UHIDs")
