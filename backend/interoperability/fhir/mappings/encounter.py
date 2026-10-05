"""
FHIR Encounter Mapper

Maps internal Visit, Admission, and EmergencyVisit models to FHIR R4 Encounter resource.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class EncounterResourceBuilder(FHIRResourceBuilder):
    """FHIR Encounter resource builder."""
    resource_type = "Encounter"


def _map_encounter_class(visit_type: str) -> Dict[str, Any]:
    """Map internal visit_type to FHIR Encounter.class."""
    class_map = {
        "OPD": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB", "display": "Ambulatory"},
        "IPD": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "Inpatient"},
        "Emergency": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "EMER", "display": "Emergency"},
        "Admission": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "Inpatient"},
        "Discharge": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "Inpatient"},
    }
    coding = class_map.get(visit_type, class_map["OPD"])
    return {"coding": [coding]}


def _map_encounter_status(status: str, visit_type: str) -> str:
    """Map internal status to FHIR Encounter.status."""
    # FHIR Encounter status: planned, arrived, triaged, in-progress, onleave, finished, cancelled, entered-in-error, unknown
    status_map = {
        "Waiting": "arrived",
        "Called": "arrived",
        "Acknowledged": "arrived",
        "Ready": "arrived",
        "In Consultation": "in-progress",
        "Completed": "finished",
        "Skipped": "cancelled",
        "Cancelled": "cancelled",
        "No Show": "cancelled",
        "Registered": "planned",
        "Triage": "triaged",
        "Under Consultation": "in-progress",
        "Investigations": "in-progress",
        "Treatment": "in-progress",
        "Observation": "in-progress",
        "Admitted": "in-progress",
        "Discharged": "finished",
        "Referred": "finished",
        "Left Against Advice": "finished",
        "Expired": "finished",
        "Admitted": "in-progress",
        "Discharge Initiated": "in-progress",
        "Transferred": "finished",
    }
    return status_map.get(status, "unknown")


@register_fhir_mapper("Encounter")
class VisitEncounterMapper(FHIRMapper):
    """Maps internal Visit (OPD) to FHIR Encounter."""
    
    source_model = "encounters.Visit"
    target_resource_type = "Encounter"
    required_source_fields = ["patient", "hospital", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = EncounterResourceBuilder()
    
    def map(self, visit) -> Dict[str, Any]:
        """Map Visit model to FHIR Encounter resource."""
        hospital = visit.hospital
        patient = visit.patient
        doctor = visit.doctor
        
        resource_id = self._get_stable_id(visit, "Encounter")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/encounter/{hospital.id}",
            "value": f"VIS-{visit.id}",
            "use": "official"
        }]
        
        # Status
        resource["status"] = _map_encounter_status(visit.status, visit.visit_type)
        
        # Class
        resource["class"] = _map_encounter_class(visit.visit_type)
        
        # Type
        resource["type"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/v2-0004",
                code=visit.visit_type,
                display=visit.visit_type
            )],
            text=visit.visit_type
        )]
        
        # Subject (Patient)
        patient_mapper = self._get_patient_mapper()
        patient_resource = patient_mapper.map(patient) if patient_mapper else None
        patient_ref = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        resource["subject"] = patient_ref
        
        # Participant (Doctor)
        participants = []
        if doctor:
            participants.append({
                "type": [self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                        code="ATND",
                        display="Attender"
                    )]
                )],
                "period": self.builder._period(start=visit.visit_date),
                "individual": self.builder._reference(
                    "Practitioner", f"Practitioner-{doctor.id}", doctor.name
                )
            })
        resource["participant"] = participants
        
        # Period
        period_start = visit.visit_date
        period_end = None
        if visit.status in ["Completed", "Cancelled", "No Show"]:
            # Estimate end time or use completed_at if available
            pass
        resource["period"] = self.builder._period(start=period_start, end=period_end)
        
        # Service Provider (Hospital)
        resource["serviceProvider"] = self.builder._reference(
            "Organization", f"Organization-{hospital.id}", hospital.name
        )
        
        # Reason (Chief Complaint)
        if visit.chief_complaint:
            resource["reasonCode"] = [self.builder._codeable_concept(
                text=visit.chief_complaint
            )]
        
        # Diagnosis (from clinical diagnoses)
        diagnoses = getattr(visit, "diagnoses", None)
        if diagnoses:
            diag_list = []
            for dx in diagnoses.all():
                diag_list.append({
                    "condition": self.builder._reference(
                        "Condition", f"Condition-{dx.id}", dx.name
                    ),
                    "use": self.builder._codeable_concept(
                        coding=[self.builder._coding(
                            system="http://terminology.hl7.org/CodeSystem/diagnosis-role",
                            code="DD",
                            display="Discharge Diagnosis"
                        )]
                    ),
                    "rank": 1
                })
            resource["diagnosis"] = diag_list
        
        # Hospitalization (for IPD) - not applicable for OPD visits
        if visit.visit_type in ["IPD", "Admission"]:
            resource["hospitalization"] = self._build_hospitalization(visit)
        
        return resource
    
    def _build_hospitalization(self, visit) -> Dict[str, Any]:
        """Build hospitalization details for inpatient encounters."""
        hospitalization = {}
        
        # Admit source
        hospitalization["admitSource"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/admit-source",
                code="outpatient",
                display="Outpatient"
            )]
        )
        
        return hospitalization
    
    def _get_patient_mapper(self):
        """Lazy import to avoid circular dependency."""
        from .patient import PatientMapper
        return PatientMapper(self.context)


@register_fhir_mapper("Encounter")
class AdmissionEncounterMapper(FHIRMapper):
    """Maps internal Admission (IPD) to FHIR Encounter."""
    
    source_model = "ipd.Admission"
    target_resource_type = "Encounter"
    required_source_fields = ["patient", "hospital", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = EncounterResourceBuilder()
    
    def map(self, admission) -> Dict[str, Any]:
        """Map Admission model to FHIR Encounter resource."""
        hospital = admission.hospital
        patient = admission.patient
        doctor = admission.admitting_doctor
        
        resource_id = self._get_stable_id(admission, "Encounter")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/admission/{hospital.id}",
            "value": f"ADM-{admission.id}",
            "use": "official"
        }]
        
        # Status
        status_map = {
            "Admitted": "in-progress",
            "Discharge Initiated": "in-progress",
            "Discharged": "finished",
            "Transferred": "finished",
            "Cancelled": "cancelled"
        }
        resource["status"] = status_map.get(admission.status, "unknown")
        
        # Class - Inpatient
        resource["class"] = _map_encounter_class("IPD")
        
        # Type
        resource["type"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/v2-0004",
                code="IPD",
                display="Inpatient Admission"
            )],
            text="Inpatient Admission"
        )]
        
        # Subject (Patient)
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Participant (Admitting Doctor)
        participants = []
        if doctor:
            participants.append({
                "type": [self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                        code="ADM",
                        display="Admitting"
                    )]
                )],
                "period": self.builder._period(start=admission.admission_date),
                "individual": self.builder._reference(
                    "Practitioner", f"Practitioner-{doctor.id}", doctor.name
                )
            })
        resource["participant"] = participants
        
        # Period
        resource["period"] = self.builder._period(
            start=admission.admission_date,
            end=admission.discharge_date
        )
        
        # Service Provider (Hospital)
        resource["serviceProvider"] = self.builder._reference(
            "Organization", f"Organization-{hospital.id}", hospital.name
        )
        
        # Reason
        if admission.reason:
            resource["reasonCode"] = [self.builder._codeable_concept(text=admission.reason)]
        
        # Hospitalization details
        resource["hospitalization"] = self._build_hospitalization(admission)
        
        return resource
    
    def _build_hospitalization(self, admission) -> Dict[str, Any]:
        """Build detailed hospitalization information."""
        hospitalization = {
            "admitSource": self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/admit-source",
                    code="outpatient",
                    display="Outpatient"
                )]
            )
        }
        
        # Bed allocation
        bed_allocation = getattr(admission, "bed_allocations", None)
        if bed_allocation:
            active_bed = bed_allocation.filter(is_active=True).first()
            if active_bed and active_bed.bed:
                hospitalization["location"] = [{
                    "location": self.builder._reference(
                        "Location", f"Location-{active_bed.bed.id}",
                        f"Bed {active_bed.bed.bed_number} in {active_bed.bed.room.ward.name}"
                    ),
                    "period": self.builder._period(start=active_bed.allocated_at)
                }]
        
        # Discharge disposition
        if admission.status == "Discharged":
            discharge_summary = getattr(admission, "discharge_summary", None)
            if discharge_summary:
                hospitalization["dischargeDisposition"] = self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/discharge-disposition",
                        code="home",
                        display="Home"
                    )],
                    text="Discharged to home"
                )
        
        return hospitalization


@register_fhir_mapper("Encounter")
class EmergencyEncounterMapper(FHIRMapper):
    """Maps internal EmergencyVisit to FHIR Encounter."""
    
    source_model = "emergency.EmergencyVisit"
    target_resource_type = "Encounter"
    required_source_fields = ["patient", "hospital", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = EncounterResourceBuilder()
    
    def map(self, visit) -> Dict[str, Any]:
        """Map EmergencyVisit model to FHIR Encounter resource."""
        hospital = visit.hospital
        patient = visit.patient
        doctor = visit.attending_doctor
        
        resource_id = self._get_stable_id(visit, "Encounter")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/emergency/{hospital.id}",
            "value": visit.visit_number,
            "use": "official"
        }]
        
        # Status
        status_map = {
            "Registered": "planned",
            "Triage": "triaged",
            "Waiting": "arrived",
            "Under Consultation": "in-progress",
            "Investigations": "in-progress",
            "Treatment": "in-progress",
            "Observation": "in-progress",
            "Admitted": "in-progress",
            "Discharged": "finished",
            "Referred": "finished",
            "Left Against Advice": "finished",
            "Expired": "finished"
        }
        resource["status"] = status_map.get(visit.status, "unknown")
        
        # Class - Emergency
        resource["class"] = _map_encounter_class("Emergency")
        
        # Type
        resource["type"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://terminology.hl7.org/CodeSystem/v2-0004",
                code="EMER",
                display="Emergency"
            )],
            text="Emergency"
        )]
        
        # Priority (from triage level)
        if visit.triage_level:
            priority_map = {
                "Critical": "emergency",
                "Emergency": "urgent",
                "Urgent": "urgent",
                "Semi-Urgent": "routine",
                "Non-Urgent": "routine"
            }
            resource["priority"] = self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-ActPriority",
                    code=priority_map.get(visit.triage_level, "routine"),
                    display=visit.triage_level
                )]
            )
        
        # Subject (Patient)
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Participant (Attending Doctor)
        participants = []
        if doctor:
            participants.append({
                "type": [self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                        code="ATND",
                        display="Attender"
                    )]
                )],
                "period": self.builder._period(start=visit.arrival_time),
                "individual": self.builder._reference(
                    "Practitioner", f"Practitioner-{doctor.id}", doctor.name
                )
            })
        resource["participant"] = participants
        
        # Period
        resource["period"] = self.builder._period(
            start=visit.arrival_time,
            end=visit.discharge_time
        )
        
        # Service Provider
        resource["serviceProvider"] = self.builder._reference(
            "Organization", f"Organization-{hospital.id}", hospital.name
        )
        
        # Reason (from triage chief complaint)
        triage = getattr(visit, "triage", None)
        if triage and triage.chief_complaint:
            resource["reasonCode"] = [self.builder._codeable_concept(text=triage.chief_complaint)]
        
        # Diagnosis (from discharge diagnosis)
        if visit.discharge_diagnosis:
            resource["diagnosis"] = [{
                "condition": self.builder._reference(
                    "Condition", f"Condition-er-{visit.id}", visit.discharge_diagnosis
                ),
                "use": self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/diagnosis-role",
                        code="DD",
                        display="Discharge Diagnosis"
                    )]
                ),
                "rank": 1
            }]
        
        return resource


def map_visit_to_fhir(visit, context: MappingContext) -> Dict[str, Any]:
    """Map Visit (OPD) to FHIR Encounter."""
    mapper = VisitEncounterMapper(context)
    return mapper.map(visit)


def map_admission_to_fhir(admission, context: MappingContext) -> Dict[str, Any]:
    """Map Admission (IPD) to FHIR Encounter."""
    mapper = AdmissionEncounterMapper(context)
    return mapper.map(admission)


def map_emergency_to_fhir(emergency_visit, context: MappingContext) -> Dict[str, Any]:
    """Map EmergencyVisit to FHIR Encounter."""
    mapper = EmergencyEncounterMapper(context)
    return mapper.map(emergency_visit)