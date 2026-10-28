"""
Which internal rows back each FHIR resource type served by the read API.

Each resource type lists one or more ``Source``s: a hospital-scoped queryset,
the path from a row to its patient (for ``?patient=`` searches) and the mapper
that turns a row into FHIR. Mappers live in ``interoperability.fhir.mappings``.

Only data that is final enough to share is exported: lab values only once the
test is released.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Type

from django.db.models import Q, QuerySet

from clinical.models import Allergy, ClinicalNote, Diagnosis, Prescription, VitalSign
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from interoperability.fhir.mappings.allergy import AllergyIntoleranceMapper
from interoperability.fhir.mappings.base import FHIRMapper
from interoperability.fhir.mappings.condition import DiagnosisConditionMapper
from interoperability.fhir.mappings.diagnosticreport import LabTestDiagnosticReportMapper
from interoperability.fhir.mappings.documentreference import ClinicalNoteDocumentReferenceMapper
from interoperability.fhir.mappings.encounter import VisitEncounterMapper
from interoperability.fhir.mappings.medication import PrescriptionMedicationRequestMapper
from interoperability.fhir.mappings.observation import LabResultObservationMapper, VitalSignObservationMapper
from interoperability.fhir.mappings.organization import OrganizationMapper
from interoperability.fhir.mappings.patient import PatientMapper
from interoperability.fhir.mappings.practitioner import PractitionerMapper
from laboratory.models import LabResult, LabTest
from patients.models import Patient

RELEASED_LAB_STATUS = "Released"


@dataclass(frozen=True)
class Source:
    # hospital id -> rows of this hospital
    queryset: Callable[[int], QuerySet]
    # ORM path from a row to its patient's id; None when rows are not about a patient
    patient_field: Optional[str]
    mapper: Type[FHIRMapper]
    # ORM lookup that the numeric part of a FHIR id refers to
    id_lookup: str = "pk"


def _patients(hospital_id):
    in_hospital = Q(hospital_id=hospital_id) | Q(
        hospital_memberships__hospital_id=hospital_id, hospital_memberships__is_active=True
    )
    return Patient.objects.filter(in_hospital).distinct()


RESOURCES: Dict[str, List[Source]] = {
    "Patient": [Source(_patients, "pk", PatientMapper)],
    "Encounter": [Source(
        lambda h: Visit.objects.filter(hospital_id=h).select_related("patient", "doctor", "hospital"),
        "patient_id", VisitEncounterMapper,
    )],
    "Observation": [
        Source(
            lambda h: VitalSign.objects.filter(visit__hospital_id=h).select_related("visit__patient"),
            "visit__patient_id", VitalSignObservationMapper,
        ),
        Source(
            lambda h: LabResult.objects.filter(
                lab_test__hospital_id=h, lab_test__status=RELEASED_LAB_STATUS, is_released=True,
            ).select_related("lab_test__patient"),
            "lab_test__patient_id", LabResultObservationMapper,
        ),
    ],
    "Condition": [Source(
        lambda h: Diagnosis.objects.filter(visit__hospital_id=h).select_related("visit__patient"),
        "visit__patient_id", DiagnosisConditionMapper,
    )],
    "MedicationRequest": [Source(
        lambda h: Prescription.objects.filter(hospital_id=h).select_related("patient", "doctor")
        .prefetch_related("items"),
        "patient_id", PrescriptionMedicationRequestMapper, id_lookup="items__pk",
    )],
    "AllergyIntolerance": [Source(
        lambda h: Allergy.objects.filter(hospital_id=h).select_related("patient"),
        "patient_id", AllergyIntoleranceMapper,
    )],
    "DiagnosticReport": [Source(
        lambda h: LabTest.objects.filter(hospital_id=h, status=RELEASED_LAB_STATUS)
        .select_related("patient", "doctor"),
        "patient_id", LabTestDiagnosticReportMapper,
    )],
    "DocumentReference": [Source(
        lambda h: ClinicalNote.objects.filter(visit__hospital_id=h).select_related("visit__patient", "doctor"),
        "visit__patient_id", ClinicalNoteDocumentReferenceMapper,
    )],
    "Organization": [Source(lambda h: Hospital.objects.filter(pk=h), None, OrganizationMapper)],
    "Practitioner": [Source(lambda h: Doctor.objects.filter(hospital_id=h), None, PractitionerMapper)],
}

# Resource types gathered by Patient/$everything (all patient-linked ones).
PATIENT_COMPARTMENT = [name for name, sources in RESOURCES.items()
                       if name != "Patient" and all(s.patient_field for s in sources)]
