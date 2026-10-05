"""
FHIR Provenance Mapper

Maps internal AuditLog to FHIR R4 Provenance resource for audit trail interoperability.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class ProvenanceResourceBuilder(FHIRResourceBuilder):
    """FHIR Provenance resource builder."""
    resource_type = "Provenance"


@register_fhir_mapper("Provenance")
class AuditLogProvenanceMapper(FHIRMapper):
    """Maps internal AuditLog to FHIR Provenance."""
    
    source_model = "audit.AuditLog"
    target_resource_type = "Provenance"
    required_source_fields = ["action", "model_name", "object_id", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = ProvenanceResourceBuilder()
    
    def map(self, audit_log) -> Dict[str, Any]:
        """Map AuditLog to FHIR Provenance resource."""
        resource_id = self._get_stable_id(audit_log, "Provenance")
        
        resource = self.builder._base_resource(resource_id)
        
        # Target - the resource that was affected
        target_ref = self._get_target_reference(audit_log)
        if target_ref:
            resource["target"] = [target_ref]
        
        # Recorded time
        resource["recorded"] = audit_log.created_at.isoformat() if audit_log.created_at else datetime.utcnow().isoformat()
        
        # Agent (who performed the action)
        agent = self._build_agent(audit_log)
        if agent:
            resource["agent"] = [agent]
        
        # Entity (what was affected)
        entity = self._build_entity(audit_log)
        if entity:
            resource["entity"] = [entity]
        
        # Activity (what action was performed)
        resource["activity"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/audit-event-action",
                code=self._map_action_to_fhir(audit_log.action),
                display=audit_log.action
            )],
            text=audit_log.action
        )
        
        return resource
    
    def _get_target_reference(self, audit_log) -> Optional[Dict[str, Any]]:
        """Get FHIR reference to the target resource."""
        model_name = audit_log.model_name
        object_id = audit_log.object_id
        
        # Map internal model names to FHIR resource types
        model_to_fhir = {
            "Patient": "Patient",
            "Doctor": "Practitioner",
            "Hospital": "Organization",
            "Visit": "Encounter",
            "Admission": "Encounter",
            "EmergencyVisit": "Encounter",
            "VitalSign": "Observation",
            "Allergy": "AllergyIntolerance",
            "Diagnosis": "Condition",
            "Prescription": "MedicationRequest",
            "PrescriptionItem": "Medication",
            "LabTest": "DiagnosticReport",
            "LabResult": "Observation",
            "ClinicalNote": "DocumentReference",
            "DischargeSummary": "DocumentReference",
            "Consent": "Consent",
        }
        
        fhir_type = model_to_fhir.get(model_name)
        if fhir_type:
            return self.builder._reference(fhir_type, f"{fhir_type}-{object_id}")
        return None
    
    def _build_agent(self, audit_log) -> Optional[Dict[str, Any]]:
        """Build Provenance.agent from audit log user."""
        if not audit_log.user:
            return None
        
        user = audit_log.user
        
        # Try to get practitioner reference
        try:
            from doctors.models import Doctor
            doctor = Doctor.objects.filter(user=user).first()
            if doctor:
                return {
                    "who": self.builder._reference(
                        "Practitioner", f"Practitioner-{doctor.id}",
                        f"Dr. {doctor.name}"
                    ),
                    "onBehalfOf": self.builder._reference(
                        "Organization", f"Organization-{doctor.hospital_id}",
                        doctor.hospital.name if doctor.hospital else "Unknown"
                    ) if doctor.hospital_id else None,
                    "type": self.builder._codeable_concept(
                        coding=[self.builder._coding(
                            system="http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                            code="author",
                            display="Author"
                        )]
                    )
                }
        except Exception:
            pass
        
        try:
            from nurses.models import Nurse
            nurse = Nurse.objects.filter(user=user).first()
            if nurse:
                return {
                    "who": self.builder._reference(
                        "Practitioner", f"Practitioner-{nurse.id}",
                        nurse.name
                    ),
                    "type": self.builder._codeable_concept(
                        coding=[self.builder._coding(
                            system="http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                            code="author",
                            display="Author"
                        )]
                    )
                }
        except Exception:
            pass
        
        # Fallback to generic user
        return {
            "who": {
                "display": user.get_full_name() or user.username
            },
            "type": self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                    code="author",
                    display="Author"
                )]
            )
        }
    
    def _build_entity(self, audit_log) -> Optional[Dict[str, Any]]:
        """Build Provenance.entity from audit log details."""
        entity = {
            "what": self._get_target_reference(audit_log),
            "role": "revision"
        }
        
        # Add details from audit_log.details if available
        if audit_log.details:
            try:
                import json
                details = json.loads(audit_log.details) if isinstance(audit_log.details, str) else audit_log.details
                if isinstance(details, dict):
                    entity["what"] = entity["what"] or {"display": f"{audit_log.model_name} #{audit_log.object_id}"}
            except Exception:
                pass
        
        return entity
    
    def _map_action_to_fhir(self, action: str) -> str:
        """Map internal action to FHIR audit event action codes."""
        action_map = {
            "CREATE": "C",
            "READ": "R",
            "UPDATE": "U",
            "DELETE": "D",
            "EXECUTE": "E",
            "LOGIN": "L",
            "LOGOUT": "O",
        }
        # Try exact match first
        if action.upper() in action_map:
            return action_map[action.upper()]
        
        # Try partial match
        action_lower = action.lower()
        if "create" in action_lower or "add" in action_lower:
            return "C"
        if "read" in action_lower or "view" in action_lower or "get" in action_lower:
            return "R"
        if "update" in action_lower or "edit" in action_lower or "change" in action_lower or "modify" in action_lower:
            return "U"
        if "delete" in action_lower or "remove" in action_lower:
            return "D"
        if "login" in action_lower:
            return "L"
        if "logout" in action_lower:
            return "O"
        
        return "E"  # Execute/default


def map_audit_log_to_fhir(audit_log, context: MappingContext) -> Dict[str, Any]:
    """Map AuditLog to FHIR Provenance."""
    mapper = AuditLogProvenanceMapper(context)
    return mapper.map(audit_log)