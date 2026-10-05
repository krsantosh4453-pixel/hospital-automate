"""
FHIR Medication and MedicationRequest Mappers

Maps internal Prescription and PrescriptionItem models to FHIR R4
Medication and MedicationRequest resources.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class MedicationResourceBuilder(FHIRResourceBuilder):
    """FHIR Medication resource builder."""
    resource_type = "Medication"


class MedicationRequestResourceBuilder(FHIRResourceBuilder):
    """FHIR MedicationRequest resource builder."""
    resource_type = "MedicationRequest"


@register_fhir_mapper("Medication")
class PrescriptionMedicationMapper(FHIRMapper):
    """Maps internal PrescriptionItem to FHIR Medication (catalog entries)."""
    
    source_model = "clinical.PrescriptionItem"
    target_resource_type = "Medication"
    required_source_fields = ["name", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = MedicationResourceBuilder()
    
    def map(self, item) -> Dict[str, Any]:
        """Map PrescriptionItem to FHIR Medication resource."""
        resource_id = self._get_stable_id(item, "Medication")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": "http://hospital-automate.local/identifiers/medication",
            "value": f"MED-{item.id}",
            "use": "official"
        }]
        
        # Code
        resource["code"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://hospital-automate.local/codes/medication",
                code=item.name.lower().replace(" ", "-"),
                display=item.name
            )],
            text=item.name
        )
        
        # Status
        resource["status"] = "active"
        
        # Form (could be inferred from dosage)
        if item.dosage:
            resource["form"] = self.builder._codeable_concept(text=item.dosage)
        
        # Ingredient (not available in current model)
        # resource["ingredient"] = [...]
        
        # Batch (not available in current model)
        # resource["batch"] = ...
        
        return resource


@register_fhir_mapper("MedicationRequest")
class PrescriptionMedicationRequestMapper(FHIRMapper):
    """Maps internal Prescription + PrescriptionItem to FHIR MedicationRequest."""
    
    source_model = "clinical.Prescription"
    target_resource_type = "MedicationRequest"
    required_source_fields = ["patient", "doctor", "hospital", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = MedicationRequestResourceBuilder()
    
    def map(self, prescription) -> List[Dict[str, Any]]:
        """Map Prescription to FHIR MedicationRequest resources (one per item)."""
        requests = []
        patient = prescription.patient
        doctor = prescription.doctor
        hospital = prescription.hospital
        visit = prescription.visit
        
        for item in prescription.items.all():
            resource_id = self._get_stable_id(item, "MedicationRequest")
            
            resource = self.builder._base_resource(resource_id)
            
            # Identifier
            resource["identifier"] = [{
                "system": f"http://hospital-automate.local/identifiers/medication-request/{hospital.id}",
                "value": f"RX-{prescription.id}-ITEM-{item.id}",
                "use": "official"
            }]
            
            # Status
            status_map = {
                "Confirmed": "active",
                "Draft": "draft",
                "Cancelled": "cancelled",
                "Completed": "completed",
                "On Hold": "on-hold",
            }
            resource["status"] = status_map.get(prescription.status, "active")
            
            # Intent
            resource["intent"] = "order"
            
            # Category
            resource["category"] = [self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/medicationrequest-category",
                    code="outpatient" if not visit or visit.visit_type == "OPD" else "inpatient",
                    display="Outpatient" if not visit or visit.visit_type == "OPD" else "Inpatient"
                )]
            )]
            
            # Priority
            resource["priority"] = "routine"
            
            # Medication Reference
            resource["medicationReference"] = self.builder._reference(
                "Medication", f"Medication-{item.id}", item.name
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
            
            # Authored On
            resource["authoredOn"] = prescription.created_at.isoformat() if prescription.created_at else None
            
            # Requester (Doctor)
            if doctor:
                resource["requester"] = self.builder._reference(
                    "Practitioner", f"Practitioner-{doctor.id}", doctor.name
                )
            
            # Performer (Pharmacist - not tracked in current model)
            # resource["performer"] = ...
            
            # Dosage Instruction
            dosage = self._build_dosage_instruction(item)
            if dosage:
                resource["dosageInstruction"] = [dosage]
            
            # Dispense Request
            dispense = self._build_dispense_request(item, prescription)
            if dispense:
                resource["dispenseRequest"] = dispense
            
            # Substitution
            resource["substitution"] = {
                "allowedBoolean": True
            }
            
            # Note
            if item.instructions:
                resource["note"] = [{"text": item.instructions}]
            
            requests.append(resource)
        
        return requests
    
    def _build_dosage_instruction(self, item) -> Optional[Dict[str, Any]]:
        """Build FHIR Dosage from PrescriptionItem."""
        dosage = {}
        
        # Text instruction
        text_parts = []
        if item.dosage:
            text_parts.append(f"Dose: {item.dosage}")
        if item.frequency:
            text_parts.append(f"Frequency: {item.frequency}")
        if item.duration:
            text_parts.append(f"Duration: {item.duration}")
        if item.instructions:
            text_parts.append(f"Instructions: {item.instructions}")
        
        if text_parts:
            dosage["text"] = "; ".join(text_parts)
        
        # Timing
        if item.frequency:
            # Parse frequency (simplified)
            dosage["timing"] = {
                "code": self.builder._codeable_concept(text=item.frequency)
            }
        
        # Dose Quantity
        if item.dosage:
            # Try to parse dosage (e.g., "500mg" -> value=500, unit=mg)
            dosage["doseAndRate"] = [{
                "doseQuantity": self._parse_dosage(item.dosage)
            }]
        
        # Route (not in current model)
        # dosage["route"] = ...
        
        return dosage if dosage else None
    
    def _parse_dosage(self, dosage_str: str) -> Dict[str, Any]:
        """Parse dosage string into FHIR Quantity."""
        import re
        # Simple regex to extract number and unit
        match = re.match(r"([\d.]+)\s*(\w+)", dosage_str)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            return self.builder._quantity(value=value, unit=unit, code=unit)
        return self.builder._quantity(value=1, unit="tablet", code="tablet")
    
    def _build_dispense_request(self, item, prescription) -> Optional[Dict[str, Any]]:
        """Build FHIR DispenseRequest from PrescriptionItem."""
        if not item.quantity:
            return None
        
        dispense = {
            "quantity": self.builder._quantity(
                value=float(item.quantity),
                unit="tablet",  # Default unit
                code="tablet"
            ),
            "expectedSupplyDuration": self.builder._quantity(
                value=1,  # Default
                unit="days",
                code="d"
            )
        }
        
        # Parse duration if available
        if item.duration:
            import re
            match = re.match(r"(\d+)\s*(\w+)", item.duration)
            if match:
                dispense["expectedSupplyDuration"] = self.builder._quantity(
                    value=float(match.group(1)),
                    unit=match.group(2),
                    code=match.group(2)
                )
        
        # Performer (pharmacy)
        # dispense["performer"] = ...
        
        return dispense


@register_fhir_mapper("MedicationRequest")
class EmergencyMedicationRequestMapper(FHIRMapper):
    """Maps internal EmergencyMedication to FHIR MedicationRequest."""
    
    source_model = "emergency.EmergencyMedication"
    target_resource_type = "MedicationRequest"
    required_source_fields = ["visit", "name", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = MedicationRequestResourceBuilder()
    
    def map(self, er_med) -> Dict[str, Any]:
        """Map EmergencyMedication to FHIR MedicationRequest."""
        visit = er_med.visit
        patient = visit.patient
        hospital = visit.hospital
        doctor = er_med.prescribed_by
        
        resource_id = self._get_stable_id(er_med, "MedicationRequest")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/medication-request/{hospital.id}",
            "value": f"ER-RX-{er_med.id}",
            "use": "official"
        }]
        
        # Status
        if er_med.administered:
            resource["status"] = "completed"
        else:
            resource["status"] = "active"
        
        # Intent - emergency
        resource["intent"] = "order"
        resource["priority"] = "stat"
        
        # Category
        resource["category"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/medicationrequest-category",
                code="emergency",
                display="Emergency"
            )]
        )]
        
        # Medication (inline or reference)
        resource["medicationCodeableConcept"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://hospital-automate.local/codes/medication",
                code=er_med.name.lower().replace(" ", "-"),
                display=er_med.name
            )],
            text=er_med.name
        )
        
        # Subject
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Encounter
        resource["encounter"] = self.builder._reference(
            "Encounter", f"Encounter-{visit.id}", "Emergency Visit"
        )
        
        # Authored On
        resource["authoredOn"] = er_med.prescribed_at.isoformat() if er_med.prescribed_at else None
        
        # Requester
        if doctor:
            resource["requester"] = self.builder._reference(
                "Practitioner", f"Practitioner-{doctor.id}", doctor.name
            )
        
        # Performer (nurse who administered)
        if er_med.administered_by:
            resource["performer"] = self.builder._reference(
                "Practitioner", f"Practitioner-{er_med.administered_by.id}",
                er_med.administered_by.name
            )
        
        # Dosage Instruction
        dosage = {
            "text": f"Dose: {er_med.dose}; Route: {er_med.route}; Frequency: {er_med.frequency}",
            "timing": {"code": self.builder._codeable_concept(text=er_med.frequency)},
            "route": self.builder._codeable_concept(text=er_med.route),
            "doseAndRate": [{
                "doseQuantity": self.builder._quantity(value=1, unit=er_med.dose, code=er_med.dose)
            }]
        }
        if er_med.duration:
            dosage["text"] += f"; Duration: {er_med.duration}"
        resource["dosageInstruction"] = [dosage]
        
        return resource


def map_prescription_to_fhir_medications(prescription, context: MappingContext) -> List[Dict[str, Any]]:
    """Map Prescription items to FHIR Medication resources."""
    mapper = PrescriptionMedicationMapper(context)
    return [mapper.map(item) for item in prescription.items.all()]


def map_prescription_to_fhir_requests(prescription, context: MappingContext) -> List[Dict[str, Any]]:
    """Map Prescription to FHIR MedicationRequest resources."""
    mapper = PrescriptionMedicationRequestMapper(context)
    return mapper.map(prescription)


def map_er_medication_to_fhir_request(er_med, context: MappingContext) -> Dict[str, Any]:
    """Map EmergencyMedication to FHIR MedicationRequest."""
    mapper = EmergencyMedicationRequestMapper(context)
    return mapper.map(er_med)