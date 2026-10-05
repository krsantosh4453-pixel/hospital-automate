"""
FHIR Condition Mapper

Maps internal Diagnosis model to FHIR R4 Condition resource.
"""

from typing import List, Dict, Any
from datetime import datetime
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class ConditionResourceBuilder(FHIRResourceBuilder):
    """FHIR Condition resource builder."""
    resource_type = "Condition"


# Map internal diagnosis_type to FHIR Condition.clinicalStatus
CLINICAL_STATUS_MAP = {
    "Provisional": "active",
    "Confirmed": "active",
    "Refuted": "refuted",
    "Resolved": "resolved",
    "Differential": "active",
    "Working": "active",
}

# Map internal diagnosis_type to FHIR Condition.verificationStatus
VERIFICATION_STATUS_MAP = {
    "Provisional": "unconfirmed",
    "Confirmed": "confirmed",
    "Refuted": "refuted",
    "Resolved": "confirmed",
    "Differential": "differential",
    "Working": "provisional",
}


@register_fhir_mapper("Condition")
class DiagnosisConditionMapper(FHIRMapper):
    """Maps internal Diagnosis to FHIR Condition."""
    
    source_model = "clinical.Diagnosis"
    target_resource_type = "Condition"
    required_source_fields = ["visit", "name", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = ConditionResourceBuilder()
    
    def map(self, diagnosis) -> Dict[str, Any]:
        """Map Diagnosis model to FHIR Condition resource."""
        visit = diagnosis.visit
        patient = visit.patient
        hospital = visit.hospital
        
        resource_id = self._get_stable_id(diagnosis, "Condition")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/condition/{hospital.id}",
            "value": f"DX-{diagnosis.id}",
            "use": "official"
        }]
        
        # Clinical Status
        resource["clinicalStatus"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                code=CLINICAL_STATUS_MAP.get(diagnosis.diagnosis_type, "active"),
                display=diagnosis.diagnosis_type
            )]
        )
        
        # Verification Status
        resource["verificationStatus"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                code=VERIFICATION_STATUS_MAP.get(diagnosis.diagnosis_type, "unconfirmed"),
                display=diagnosis.diagnosis_type
            )]
        )
        
        # Category - problem-list-item
        resource["category"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/condition-category",
                code="problem-list-item",
                display="Problem List Item"
            )]
        )]
        
        # Severity (if available from ICD10 or remarks)
        if diagnosis.icd10_code:
            # Could add severity based on ICD10 chapter
            pass
        
        # Code (Diagnosis name + ICD10)
        coding = []
        if diagnosis.icd10_code:
            coding.append(self.builder._coding(
                system="http://hl7.org/fhir/sid/icd-10",
                code=diagnosis.icd10_code,
                display=diagnosis.name
            ))
        coding.append(self.builder._coding(
            system="http://hospital-automate.local/codes/diagnosis",
            code=diagnosis.name.lower().replace(" ", "-"),
            display=diagnosis.name
        ))
        resource["code"] = self.builder._codeable_concept(coding=coding, text=diagnosis.name)
        
        # Subject (Patient)
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Encounter (Visit)
        resource["encounter"] = self.builder._reference(
            "Encounter", f"Encounter-{visit.id}", f"Visit {visit.visit_type}"
        )
        
        # Onset DateTime
        resource["onsetDateTime"] = diagnosis.created_at.isoformat() if diagnosis.created_at else None
        
        # Recorded Date
        resource["recordedDate"] = diagnosis.created_at.isoformat() if diagnosis.created_at else None
        
        # Recorder (Doctor who made diagnosis)
        if diagnosis.visit and diagnosis.visit.doctor:
            resource["recorder"] = self.builder._reference(
                "Practitioner", f"Practitioner-{diagnosis.visit.doctor.id}",
                diagnosis.visit.doctor.name
            )
        
        # Asserter (same as recorder for now)
        resource["asserter"] = resource.get("recorder")
        
        # Note
        if diagnosis.remarks:
            resource["note"] = [{"text": diagnosis.remarks}]
        
        # Evidence (could link to observations/lab results)
        # resource["evidence"] = [...]
        
        return resource


@register_fhir_mapper("Condition")
class EmergencyDischargeConditionMapper(FHIRMapper):
    """Maps EmergencyVisit discharge_diagnosis to FHIR Condition."""
    
    source_model = "emergency.EmergencyVisit"
    target_resource_type = "Condition"
    required_source_fields = ["id", "discharge_diagnosis"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = ConditionResourceBuilder()
    
    def map(self, visit) -> List[Dict[str, Any]]:
        """Map EmergencyVisit discharge_diagnosis to FHIR Condition resources."""
        conditions = []
        
        if not visit.discharge_diagnosis:
            return conditions
        
        patient = visit.patient
        hospital = visit.hospital
        
        # Parse discharge diagnosis - could be multiple conditions
        # For now, create one condition from the text
        diagnosis_text = visit.discharge_diagnosis
        
        resource_id = self._get_stable_id(visit, "Condition-discharge")
        
        resource = self.builder._base_resource(resource_id)
        
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/condition/{hospital.id}",
            "value": f"ER-DX-{visit.id}",
            "use": "official"
        }]
        
        resource["clinicalStatus"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                code="resolved",
                display="Resolved"
            )]
        )
        
        resource["verificationStatus"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                code="confirmed",
                display="Confirmed"
            )]
        )
        
        resource["category"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/condition-category",
                code="encounter-diagnosis",
                display="Encounter Diagnosis"
            )]
        )]
        
        resource["code"] = self.builder._codeable_concept(text=diagnosis_text)
        
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        resource["encounter"] = self.builder._reference(
            "Encounter", f"Encounter-{visit.id}", "Emergency Visit"
        )
        
        if visit.discharge_time:
            resource["onsetDateTime"] = visit.arrival_time.isoformat() if visit.arrival_time else None
            resource["abatementDateTime"] = visit.discharge_time.isoformat()
        
        resource["recordedDate"] = visit.discharge_time.isoformat() if visit.discharge_time else None
        
        if visit.attending_doctor:
            resource["recorder"] = self.builder._reference(
                "Practitioner", f"Practitioner-{visit.attending_doctor.id}",
                visit.attending_doctor.name
            )
        
        conditions.append(resource)
        
        return conditions


def map_diagnosis_to_fhir(diagnosis, context: MappingContext) -> Dict[str, Any]:
    """Map Diagnosis to FHIR Condition."""
    mapper = DiagnosisConditionMapper(context)
    return mapper.map(diagnosis)


def map_er_discharge_to_fhir(visit, context: MappingContext) -> List[Dict[str, Any]]:
    """Map EmergencyVisit discharge diagnosis to FHIR Conditions."""
    mapper = EmergencyDischargeConditionMapper(context)
    return mapper.map(visit)