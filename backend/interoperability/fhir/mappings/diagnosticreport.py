"""
FHIR DiagnosticReport Mapper

Maps internal LabTest model to FHIR R4 DiagnosticReport resource.
"""

from typing import List, Dict, Any
from datetime import datetime
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class DiagnosticReportResourceBuilder(FHIRResourceBuilder):
    """FHIR DiagnosticReport resource builder."""
    resource_type = "DiagnosticReport"


# Map internal LabTest status to FHIR DiagnosticReport.status
DIAGNOSTIC_REPORT_STATUS_MAP = {
    "Ordered": "registered",
    "Sample Pending": "partial",
    "Collected": "partial",
    "Dispatched": "partial",
    "Received": "partial",
    "Processing": "partial",
    "Result Entered": "partial",
    "Verified": "final",
    "Released": "final",
    "Cancelled": "cancelled",
}


# Map priority to FHIR DiagnosticReport.priority
PRIORITY_MAP = {
    "Normal": "routine",
    "Urgent": "stat",
}


@register_fhir_mapper("DiagnosticReport")
class LabTestDiagnosticReportMapper(FHIRMapper):
    """Maps internal LabTest to FHIR DiagnosticReport."""
    
    source_model = "laboratory.LabTest"
    target_resource_type = "DiagnosticReport"
    required_source_fields = ["patient", "name", "hospital", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = DiagnosticReportResourceBuilder()
    
    def map(self, lab_test) -> Dict[str, Any]:
        """Map LabTest model to FHIR DiagnosticReport resource."""
        patient = lab_test.patient
        hospital = lab_test.hospital
        doctor = lab_test.doctor
        visit = lab_test.visit
        
        resource_id = self._get_stable_id(lab_test, "DiagnosticReport")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/diagnostic-report/{hospital.id}",
            "value": f"LAB-{lab_test.id}",
            "use": "official"
        }]
        
        # Status
        resource["status"] = DIAGNOSTIC_REPORT_STATUS_MAP.get(lab_test.status, "registered")
        
        # Category - laboratory
        resource["category"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/v2-0074",
                code="LAB",
                display="Laboratory"
            )]
        )]
        
        # Code (test name)
        resource["code"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://hospital-automate.local/codes/lab-test",
                code=lab_test.name.lower().replace(" ", "-"),
                display=lab_test.name
            )],
            text=lab_test.name
        )
        
        # Subject (Patient)
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Encounter
        if visit:
            resource["encounter"] = self.builder._reference(
                "Encounter", f"Encounter-{visit.id}", f"Visit {visit.visit_type}"
            )
        
        # Effective DateTime (test date)
        resource["effectiveDateTime"] = lab_test.test_date.isoformat() if lab_test.test_date else None
        
        # Issued DateTime
        issued_time = lab_test.verified_at or lab_test.released_at or lab_test.processed_at or datetime.utcnow()
        resource["issued"] = issued_time.isoformat()
        
        # Performer (lab staff who processed)
        performers = []
        lab_result = getattr(lab_test, "lab_result", None)
        if lab_result:
            if lab_result.entered_by:
                performers.append({
                    "actor": self.builder._reference(
                        "Practitioner", f"Practitioner-{lab_result.entered_by.id}",
                        lab_result.entered_by.get_full_name()
                    )
                })
            if lab_result.verified_by:
                performers.append({
                    "actor": self.builder._reference(
                        "Practitioner", f"Practitioner-{lab_result.verified_by.id}",
                        lab_result.verified_by.get_full_name()
                    )
                })
        resource["performer"] = performers
        
        # Requester (Doctor who ordered)
        if doctor:
            resource["requester"] = self.builder._reference(
                "Practitioner", f"Practitioner-{doctor.id}", doctor.name
            )
        
        # Specimen
        specimen = getattr(lab_test, "sample_collection", None)
        if specimen:
            resource["specimen"] = [self.builder._reference(
                "Specimen", f"Specimen-{specimen.id}", f"Sample {specimen.sample_id}"
            )]
        
        # Results (references to Observation resources)
        observations = []
        if lab_result and lab_result.result_data:
            for test_name in lab_result.result_data.keys():
                obs_id = f"Observation-{test_name.replace(' ', '-')}"
                observations.append(self.builder._reference(
                    "Observation", f"{obs_id}-{lab_result.id}", test_name
                ))
        resource["result"] = observations
        
        # Conclusion (result text)
        if lab_result and lab_result.result_text:
            resource["conclusion"] = lab_result.result_text
        
        # Conclusion Code (abnormal flags summary)
        if lab_result and lab_result.abnormal_flags:
            codes = []
            for flag in lab_result.abnormal_flags:
                codes.append(self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                    code=flag,
                    display={"H": "High", "L": "Low", "A": "Abnormal", "N": "Normal"}.get(flag, "Abnormal")
                ))
            if codes:
                resource["conclusionCode"] = [self.builder._codeable_concept(coding=codes)]
        
        # Presented Form (PDF/Document reference - if available)
        # resource["presentedForm"] = [...]
        
        return resource


def map_lab_test_to_fhir(lab_test, context: MappingContext) -> Dict[str, Any]:
    """Map LabTest to FHIR DiagnosticReport."""
    mapper = LabTestDiagnosticReportMapper(context)
    return mapper.map(lab_test)