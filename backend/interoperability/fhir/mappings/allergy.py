"""
FHIR AllergyIntolerance Mapper

Maps internal Allergy model to FHIR R4 AllergyIntolerance resource.
"""

from typing import List, Dict, Any
from datetime import datetime
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class AllergyIntoleranceResourceBuilder(FHIRResourceBuilder):
    """FHIR AllergyIntolerance resource builder."""
    resource_type = "AllergyIntolerance"


# Map internal severity to FHIR AllergyIntolerance.severity
SEVERITY_MAP = {
    "Mild": "mild",
    "Moderate": "moderate",
    "Severe": "severe",
    "Critical": "severe",
    "Life-threatening": "severe",
}


@register_fhir_mapper("AllergyIntolerance")
class AllergyIntoleranceMapper(FHIRMapper):
    """Maps internal Allergy to FHIR AllergyIntolerance."""
    
    source_model = "clinical.Allergy"
    target_resource_type = "AllergyIntolerance"
    required_source_fields = ["patient", "name", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = AllergyIntoleranceResourceBuilder()
    
    def map(self, allergy) -> Dict[str, Any]:
        """Map Allergy model to FHIR AllergyIntolerance resource."""
        patient = allergy.patient
        hospital = patient.hospital
        if not hospital and hasattr(patient, "hospital_memberships"):
            membership = patient.hospital_memberships.filter(is_active=True).first()
            if membership:
                hospital = membership.hospital
        
        if not hospital:
            raise ValueError("Patient must be associated with a hospital for FHIR export")
        
        resource_id = self._get_stable_id(allergy, "AllergyIntolerance")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/allergy/{hospital.id}",
            "value": f"ALL-{allergy.id}",
            "use": "official"
        }]
        
        # Clinical Status - active by default for recorded allergies
        resource["clinicalStatus"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                code="active",
                display="Active"
            )]
        )
        
        # Verification Status - unconfirmed by default (patient-reported)
        resource["verificationStatus"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                code="unconfirmed",
                display="Unconfirmed"
            )]
        )
        
        # Type - allergy vs intolerance (default to allergy)
        resource["type"] = "allergy"
        
        # Category - could be food, medication, environment, biologic
        # Try to infer from name
        category = self._infer_category(allergy.name)
        resource["category"] = [category]
        
        # Criticality (severity)
        severity = allergy.severity or "Mild"
        resource["criticality"] = SEVERITY_MAP.get(severity, "mild")
        
        # Code (substance)
        resource["code"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://hospital-automate.local/codes/allergen",
                code=allergy.name.lower().replace(" ", "-"),
                display=allergy.name
            )],
            text=allergy.name
        )
        
        # Patient
        resource["patient"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Onset DateTime
        resource["onsetDateTime"] = allergy.created_at.isoformat() if allergy.created_at else None
        
        # Recorded Date
        resource["recordedDate"] = allergy.created_at.isoformat() if allergy.created_at else None
        
        # Recorder (who recorded it - could be patient or clinician)
        # Not stored in current model, skip
        
        # Reaction
        if allergy.reaction:
            resource["reaction"] = [{
                "manifestation": [self.builder._codeable_concept(text=allergy.reaction)],
                "severity": SEVERITY_MAP.get(severity, "mild"),
            }]
        
        # Note
        if allergy.reaction:
            resource["note"] = [{"text": f"Reaction: {allergy.reaction}"}]
        
        return resource
    
    def _infer_category(self, name: str) -> str:
        """Infer allergy category from name."""
        name_lower = name.lower()
        if any(term in name_lower for term in ["drug", "medicine", "medication", "antibiotic", "penicillin", "aspirin", "ibuprofen"]):
            return "medication"
        if any(term in name_lower for term in ["food", "peanut", "shellfish", "milk", "egg", "wheat", "soy", "nut"]):
            return "food"
        if any(term in name_lower for term in ["pollen", "dust", "mold", "pet", "animal", "latex", "bee", "wasp"]):
            return "environment"
        if any(term in name_lower for term in ["blood", "serum", "vaccine", "immunoglobulin"]):
            return "biologic"
        return "environment"  # Default


def map_allergy_to_fhir(allergy, context: MappingContext) -> Dict[str, Any]:
    """Map Allergy to FHIR AllergyIntolerance."""
    mapper = AllergyIntoleranceMapper(context)
    return mapper.map(allergy)