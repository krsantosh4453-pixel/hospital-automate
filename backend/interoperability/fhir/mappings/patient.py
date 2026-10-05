"""
FHIR Patient Mapper

Maps internal Patient model to FHIR R4 Patient resource.
"""

from typing import List, Dict, Any, Optional
from datetime import date

from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class PatientResourceBuilder(FHIRResourceBuilder):
    """FHIR Patient resource builder."""
    resource_type = "Patient"
    
    def build(self, source_obj) -> Dict[str, Any]:
        # This is called via the mapper, which prepares the data
        return source_obj


@register_fhir_mapper("Patient")
class PatientMapper(FHIRMapper):
    """Maps internal Patient to FHIR Patient."""
    
    source_model = "patients.Patient"  # String reference to avoid circular imports
    target_resource_type = "Patient"
    required_source_fields = ["name", "gender", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = PatientResourceBuilder()
    
    def map(self, patient) -> Dict[str, Any]:
        """Map Patient model to FHIR Patient resource."""
        hospital = patient.hospital
        if not hospital and hasattr(patient, "hospital_memberships"):
            membership = patient.hospital_memberships.filter(is_active=True).first()
            if membership:
                hospital = membership.hospital
        
        if not hospital:
            raise ValueError("Patient must be associated with a hospital for FHIR export")
        
        resource_id = self._get_stable_id(patient, "Patient")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = self._get_patient_identifier(patient, hospital)
        
        # Name
        name_parts = patient.name.split(" ", 1) if patient.name else ["Unknown", ""]
        family = name_parts[1] if len(name_parts) > 1 else name_parts[0]
        given = [name_parts[0]] if len(name_parts) > 1 else []
        resource["name"] = [self.builder._human_name(family=family, given=given)]
        
        # Telecom
        telecom = []
        if patient.phone:
            telecom.append(self.builder._contact_point("phone", patient.phone, "mobile"))
        resource["telecom"] = telecom
        
        # Gender - map internal gender to FHIR administrative gender
        gender_map = {
            "Male": "male",
            "Female": "female",
            "Other": "other",
            "Unknown": "unknown"
        }
        resource["gender"] = gender_map.get(patient.gender, "unknown")
        
        # Birth Date - calculate from age if birth_date not stored
        # Note: Internal model only has age, not birthDate
        # We calculate approximate birth date from age
        if patient.age:
            current_year = date.today().year
            birth_year = current_year - patient.age
            resource["birthDate"] = f"{birth_year}-01-01"  # Approximate
        
        # Address - from hospital address as proxy if patient address not stored
        address = []
        if hospital.address:
            address.append(self.builder._address(
                line=[hospital.address],
                city=hospital.city,
                state=hospital.state,
                use="home"
            ))
        resource["address"] = address
        
        # Managing Organization (the hospital)
        resource["managingOrganization"] = self.builder._reference(
            "Organization", f"Organization-{hospital.id}", hospital.name
        )
        
        # Active status
        resource["active"] = patient.status == "Active"
        
        return resource


def map_patient_to_fhir(patient, context: MappingContext) -> Dict[str, Any]:
    """Convenience function to map a patient to FHIR."""
    mapper = PatientMapper(context)
    return mapper.map(patient)