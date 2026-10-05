"""
FHIR Practitioner Mapper

Maps internal Doctor/Nurse models to FHIR R4 Practitioner resource.
"""

from typing import List, Dict, Any
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class PractitionerResourceBuilder(FHIRResourceBuilder):
    """FHIR Practitioner resource builder."""
    resource_type = "Practitioner"


@register_fhir_mapper("Practitioner")
class PractitionerMapper(FHIRMapper):
    """Maps internal Doctor to FHIR Practitioner."""
    
    source_model = "doctors.Doctor"
    target_resource_type = "Practitioner"
    required_source_fields = ["name", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = PractitionerResourceBuilder()
    
    def map(self, doctor) -> Dict[str, Any]:
        """Map Doctor model to FHIR Practitioner resource."""
        hospital = doctor.hospital
        if not hospital:
            raise ValueError("Doctor must be associated with a hospital for FHIR export")
        
        resource_id = self._get_stable_id(doctor, "Practitioner")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = self._get_practitioner_identifier(doctor, hospital)
        
        # Active status
        resource["active"] = doctor.status == "Available"
        
        # Name
        name_parts = doctor.name.split(" ", 1) if doctor.name else ["Unknown", ""]
        family = name_parts[1] if len(name_parts) > 1 else name_parts[0]
        given = [name_parts[0]] if len(name_parts) > 1 else []
        resource["name"] = [self.builder._human_name(
            family=family, 
            given=given,
            prefix=["Dr."]
        )]
        
        # Telecom
        telecom = []
        if doctor.phone:
            telecom.append(self.builder._contact_point("phone", doctor.phone, "work"))
        resource["telecom"] = telecom
        
        # Qualifications (specialization)
        if doctor.specialization:
            resource["qualification"] = [{
                "code": self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/v2-0203",
                        code=doctor.specialization,
                        display=doctor.specialization
                    )],
                    text=doctor.specialization
                ),
                "period": self.builder._period(start=doctor.created_at) if doctor.created_at else None
            }]
        
        # Communication - languages (could be extended)
        resource["communication"] = [
            self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="urn:ietf:bcp:47",
                    code="en",
                    display="English"
                )],
                text="English"
            )
        ]
        
        return resource


@register_fhir_mapper("Practitioner")
class NursePractitionerMapper(FHIRMapper):
    """Maps internal Nurse to FHIR Practitioner (role=nurse)."""
    
    source_model = "nurses.Nurse"
    target_resource_type = "Practitioner"
    required_source_fields = ["name", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = PractitionerResourceBuilder()
    
    def map(self, nurse) -> Dict[str, Any]:
        """Map Nurse model to FHIR Practitioner resource."""
        hospital = nurse.hospital
        if not hospital:
            raise ValueError("Nurse must be associated with a hospital for FHIR export")
        
        resource_id = self._get_stable_id(nurse, "Practitioner")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": "http://hospital-automate.local/identifiers/practitioner",
            "value": f"NUR-{nurse.id}",
            "use": "usual"
        }, {
            "system": f"http://hospital-automate.local/identifiers/practitioner/{hospital.id}",
            "value": f"NUR-{nurse.id}",
            "use": "official"
        }]
        
        # Active status
        resource["active"] = nurse.is_active
        
        # Name
        name_parts = nurse.name.split(" ", 1) if nurse.name else ["Unknown", ""]
        family = name_parts[1] if len(name_parts) > 1 else name_parts[0]
        given = [name_parts[0]] if len(name_parts) > 1 else []
        resource["name"] = [self.builder._human_name(family=family, given=given)]
        
        # Telecom
        telecom = []
        if nurse.phone:
            telecom.append(self.builder._contact_point("phone", nurse.phone, "work"))
        if nurse.email:
            telecom.append(self.builder._contact_point("email", nurse.email, "work"))
        resource["telecom"] = telecom
        
        # Qualification - nurse qualification
        if nurse.qualification:
            resource["qualification"] = [{
                "code": self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/v2-0360",
                        code=nurse.qualification,
                        display=nurse.qualification
                    )],
                    text=nurse.qualification
                )
            }]
        
        return resource


def map_doctor_to_fhir(doctor, context: MappingContext) -> Dict[str, Any]:
    """Convenience function to map a doctor to FHIR Practitioner."""
    mapper = PractitionerMapper(context)
    return mapper.map(doctor)


def map_nurse_to_fhir(nurse, context: MappingContext) -> Dict[str, Any]:
    """Convenience function to map a nurse to FHIR Practitioner."""
    mapper = NursePractitionerMapper(context)
    return mapper.map(nurse)