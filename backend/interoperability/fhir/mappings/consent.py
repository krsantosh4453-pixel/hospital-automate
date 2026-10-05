"""
FHIR Consent Mapper

Maps internal Consent model to FHIR R4 Consent resource.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class ConsentResourceBuilder(FHIRResourceBuilder):
    """FHIR Consent resource builder."""
    resource_type = "Consent"


@register_fhir_mapper("Consent")
class ConsentMapper(FHIRMapper):
    """Maps internal Consent to FHIR Consent."""
    
    source_model = "notifications.Consent"
    target_resource_type = "Consent"
    required_source_fields = ["patient", "purpose", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = ConsentResourceBuilder()
    
    def map(self, consent) -> Dict[str, Any]:
        """Map Consent model to FHIR Consent resource."""
        patient = consent.patient
        hospital = patient.hospital
        if not hospital and hasattr(patient, "hospital_memberships"):
            membership = patient.hospital_memberships.filter(is_active=True).first()
            if membership:
                hospital = membership.hospital
        
        if not hospital:
            raise ValueError("Patient must be associated with a hospital for FHIR export")
        
        resource_id = self._get_stable_id(consent, "Consent")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/consent/{hospital.id}",
            "value": f"CONSENT-{consent.id}",
            "use": "official"
        }]
        
        # Status
        resource["status"] = "active" if consent.granted else "rejected"
        
        # Scope - patient-privacy
        resource["scope"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/consentscope",
                code="patient-privacy",
                display="Patient Privacy"
            )]
        )
        
        # Category
        resource["category"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/consentcategorycodes",
                code="hdirecshr",
                display="Healthcare Directive Sharing"
            )]
        )]
        
        # Patient
        resource["patient"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # DateTime
        resource["dateTime"] = consent.created_at.isoformat() if consent.created_at else None
        
        # Performer (Patient)
        resource["performer"] = [{
            "actor": self.builder._reference(
                "Patient", f"Patient-{patient.id}", patient.name
            )
        }]
        
        # Organization (Hospital)
        resource["organization"] = [self.builder._reference(
            "Organization", f"Organization-{hospital.id}", hospital.name
        )]
        
        # Purpose
        resource["purpose"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/v3-ActReason",
                code="TREAT",
                display="Treatment"
            )],
            text=consent.purpose
        )]
        
        # Policy (link to consent form/policy document)
        # resource["policy"] = [...]
        
        # Policy Rule (grant/deny)
        resource["policyRule"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/consentpolicycodes",
                code="optin" if consent.granted else "optout",
                display="Opt In" if consent.granted else "Opt Out"
            )]
        )
        
        # Provision (what data, to whom, for what purpose)
        resource["provision"] = self._build_provision(consent)
        
        return resource
    
    def _build_provision(self, consent) -> Dict[str, Any]:
        """Build Consent.provision based on consent purpose."""
        provision = {
            "type": "permit" if consent.granted else "deny",
            "period": self.builder._period(start=consent.created_at),
            "purpose": [self.builder._codeable_concept(text=consent.purpose)]
        }
        
        # Could add actor (who can access), action (what they can do),
        # data (what data), securityLabel based on purpose
        
        return provision


@register_fhir_mapper("Consent")
class ConsentRecordMapper(FHIRMapper):
    """Maps detailed consent records (if separate model exists) to FHIR Consent."""
    
    source_model = "consent.ConsentRecord"  # If exists
    target_resource_type = "Consent"
    required_source_fields = ["patient", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = ConsentResourceBuilder()
    
    def map(self, consent_record) -> Dict[str, Any]:
        """Map ConsentRecord to FHIR Consent."""
        # Placeholder for more detailed consent model if added
        # This would include: consent form version, digital signature,
        # specific data elements consented, expiration, etc.
        pass


def map_consent_to_fhir(consent, context: MappingContext) -> Dict[str, Any]:
    """Map Consent to FHIR Consent."""
    mapper = ConsentMapper(context)
    return mapper.map(consent)