"""
FHIR Organization Mapper

Maps internal Hospital model to FHIR R4 Organization resource.
"""

from typing import List, Dict, Any
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class OrganizationResourceBuilder(FHIRResourceBuilder):
    """FHIR Organization resource builder."""
    resource_type = "Organization"


@register_fhir_mapper("Organization")
class OrganizationMapper(FHIRMapper):
    """Maps internal Hospital to FHIR Organization."""
    
    source_model = "hospital.Hospital"
    target_resource_type = "Organization"
    required_source_fields = ["name", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = OrganizationResourceBuilder()
    
    def map(self, hospital) -> Dict[str, Any]:
        """Map Hospital model to FHIR Organization resource."""
        resource_id = self._get_stable_id(hospital, "Organization")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": "http://hospital-automate.local/identifiers/organization",
            "value": f"HOSP-{hospital.id}",
            "use": "official"
        }]
        
        # Active status
        resource["active"] = hospital.is_active
        
        # Type - hospital
        resource["type"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/organization-type",
                code="prov",
                display="Healthcare Provider"
            )],
            text="Hospital"
        )]
        
        # Name
        resource["name"] = hospital.name
        
        # Telecom
        telecom = []
        if hospital.phone:
            telecom.append(self.builder._contact_point("phone", hospital.phone, "work"))
        if hospital.email:
            telecom.append(self.builder._contact_point("email", hospital.email, "work"))
        resource["telecom"] = telecom
        
        # Address
        address = []
        if hospital.address or hospital.city or hospital.state:
            address.append(self.builder._address(
                line=[hospital.address] if hospital.address else [],
                city=hospital.city,
                state=hospital.state,
                use="work"
            ))
        resource["address"] = address
        
        # PartOf - could link to parent organization if applicable
        # resource["partOf"] = ...
        
        return resource


def map_hospital_to_fhir(hospital, context: MappingContext) -> Dict[str, Any]:
    """Convenience function to map a hospital to FHIR Organization."""
    mapper = OrganizationMapper(context)
    return mapper.map(hospital)