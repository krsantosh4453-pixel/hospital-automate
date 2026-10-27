"""
FHIR Observation Mapper

Maps internal VitalSign and LabResult models to FHIR R4 Observation resource.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class ObservationResourceBuilder(FHIRResourceBuilder):
    """FHIR Observation resource builder."""
    resource_type = "Observation"


# LOINC codes for vital signs
VITAL_SIGN_LOINC = {
    "weight": {"code": "29463-7", "display": "Body weight", "unit": "kg", "ucum": "kg"},
    "height": {"code": "8302-2", "display": "Body height", "unit": "cm", "ucum": "cm"},
    "systolic_bp": {"code": "8480-6", "display": "Systolic blood pressure", "unit": "mmHg", "ucum": "mm[Hg]"},
    "diastolic_bp": {"code": "8462-4", "display": "Diastolic blood pressure", "unit": "mmHg", "ucum": "mm[Hg]"},
    "temperature": {"code": "8310-5", "display": "Body temperature", "unit": "°C", "ucum": "Cel"},
    "heart_rate": {"code": "8867-4", "display": "Heart rate", "unit": "/min", "ucum": "/min"},
    "respiratory_rate": {"code": "9279-1", "display": "Respiratory rate", "unit": "/min", "ucum": "/min"},
    "spo2": {"code": "2708-6", "display": "Oxygen saturation", "unit": "%", "ucum": "%"},
    "blood_sugar": {"code": "2345-7", "display": "Glucose [Mass/volume] in Blood", "unit": "mg/dL", "ucum": "mg/dL"},
}


@register_fhir_mapper("Observation")
class VitalSignObservationMapper(FHIRMapper):
    """Maps internal VitalSign to FHIR Observation resources (one per vital sign)."""
    
    source_model = "clinical.VitalSign"
    target_resource_type = "Observation"
    required_source_fields = ["visit", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = ObservationResourceBuilder()
    
    def map(self, vital_sign) -> List[Dict[str, Any]]:
        """
        Map VitalSign model to multiple FHIR Observation resources.
        
        Each vital sign measurement becomes a separate Observation resource
        following FHIR best practices for vital signs.
        """
        observations = []
        visit = vital_sign.visit
        patient = visit.patient
        hospital = visit.hospital
        recorded_at = vital_sign.recorded_at or datetime.utcnow()
        
        # Map each vital sign field
        vital_fields = [
            ("weight", vital_sign.weight),
            ("height", vital_sign.height),
            ("systolic_bp", vital_sign.systolic_bp),
            ("diastolic_bp", vital_sign.diastolic_bp),
            ("temperature", vital_sign.temperature),
            ("heart_rate", vital_sign.heart_rate),
            ("respiratory_rate", vital_sign.respiratory_rate),
            ("spo2", vital_sign.spo2),
            ("blood_sugar", vital_sign.blood_sugar),
        ]
        
        for field_name, value in vital_fields:
            if value is not None:
                loinc = VITAL_SIGN_LOINC.get(field_name)
                if not loinc:
                    continue
                
                resource_id = self._get_stable_id(vital_sign, f"Observation-{field_name}")
                
                obs = self.builder._base_resource(resource_id)
                
                # Status
                obs["status"] = "final"
                
                # Category - vital signs
                obs["category"] = [self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/observation-category",
                        code="vital-signs",
                        display="Vital Signs"
                    )]
                )]
                
                # Code (LOINC)
                obs["code"] = self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://loinc.org",
                        code=loinc["code"],
                        display=loinc["display"]
                    )],
                    text=loinc["display"]
                )
                
                # Subject (Patient)
                obs["subject"] = self.builder._reference(
                    "Patient", f"Patient-{patient.id}", patient.name
                )
                
                # Encounter (Visit)
                obs["encounter"] = self.builder._reference(
                    "Encounter", f"Encounter-{visit.id}", f"Visit {visit.visit_type}"
                )
                
                # Effective time
                obs["effectiveDateTime"] = recorded_at.isoformat()
                
                # Value
                if field_name in ["systolic_bp", "diastolic_bp", "heart_rate", "respiratory_rate", "spo2"]:
                    # Integer values
                    obs["valueQuantity"] = self.builder._quantity(
                        value=float(value),
                        unit=loinc["unit"],
                        code=loinc["ucum"]
                    )
                else:
                    # Decimal values
                    obs["valueQuantity"] = self.builder._quantity(
                        value=float(value),
                        unit=loinc["unit"],
                        code=loinc["ucum"]
                    )
                
                # Performer (could be nurse/doctor who recorded)
                obs["performer"] = [{
                    "actor": self.builder._reference(
                        "Practitioner", f"Practitioner-{visit.doctor_id}" if visit.doctor_id else "Practitioner-unknown",
                        visit.doctor.name if visit.doctor else "Unknown"
                    )
                }]
                
                # Device (if applicable - could be extended)
                # obs["device"] = ...
                
                # Note
                if vital_sign.comments:
                    obs["note"] = [{"text": vital_sign.comments}]
                
                observations.append(obs)
        
        return observations


@register_fhir_mapper("Observation")
class LabResultObservationMapper(FHIRMapper):
    """Maps internal LabResult to FHIR Observation resources."""
    
    source_model = "laboratory.LabResult"
    target_resource_type = "Observation"
    required_source_fields = ["lab_test", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = ObservationResourceBuilder()
    
    def map(self, lab_result) -> List[Dict[str, Any]]:
        """Map LabResult to FHIR Observation resources."""
        observations = []
        lab_test = lab_result.lab_test
        patient = lab_test.patient
        hospital = lab_test.hospital
        
        # Get result data from JSON field
        result_data = lab_result.result_data or {}
        reference_ranges = lab_result.reference_ranges or {}
        abnormal_flags = lab_result.abnormal_flags or []
        
        # Each key in result_data becomes a separate observation
        for test_name, test_value in result_data.items():
            resource_id = self._get_stable_id(lab_result, f"Observation-{test_name.replace(' ', '-')}")
            
            obs = self.builder._base_resource(resource_id)
            
            # Status
            obs["status"] = "final" if lab_result.is_verified else "preliminary"
            
            # Category - laboratory
            obs["category"] = [self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/observation-category",
                    code="laboratory",
                    display="Laboratory"
                )]
            )]
            
            # Code - use test name as text, could map to LOINC
            obs["code"] = self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://hospital-automate.local/codes/lab",
                    code=test_name.lower().replace(" ", "-"),
                    display=test_name
                )],
                text=test_name
            )
            
            # Subject
            obs["subject"] = self.builder._reference(
                "Patient", f"Patient-{patient.id}", patient.name
            )
            
            # Encounter (from lab_test.visit)
            if lab_test.visit:
                obs["encounter"] = self.builder._reference(
                    "Encounter", f"Encounter-{lab_test.visit.id}", f"Visit {lab_test.visit.visit_type}"
                )
            
            # Specimen (from sample collection)
            sample = getattr(lab_test, "sample_collection", None)
            if sample:
                obs["specimen"] = [self.builder._reference(
                    "Specimen", f"Specimen-{sample.id}", f"Sample {sample.sample_id}"
                )]
            
            # Effective time
            effective_time = lab_result.entered_at or lab_result.verified_at or datetime.utcnow()
            obs["effectiveDateTime"] = effective_time.isoformat()
            
            # Issued time
            obs["issued"] = effective_time.isoformat()
            
            # Value
            if isinstance(test_value, (int, float)):
                # Try to get unit from reference_ranges
                unit = ""
                if test_name in reference_ranges:
                    ref = reference_ranges[test_name]
                    if isinstance(ref, dict):
                        unit = ref.get("unit", "")
                
                obs["valueQuantity"] = self.builder._quantity(
                    value=float(test_value),
                    unit=unit,
                    code=unit
                )
            elif isinstance(test_value, str):
                obs["valueString"] = test_value
            else:
                obs["valueString"] = str(test_value)
            
            # Reference Range
            if test_name in reference_ranges:
                ref = reference_ranges[test_name]
                if isinstance(ref, dict):
                    ref_range = {}
                    if "low" in ref:
                        ref_range["low"] = self.builder._quantity(
                            value=float(ref["low"]), unit=ref.get("unit", ""), code=ref.get("unit", "")
                        )
                    if "high" in ref:
                        ref_range["high"] = self.builder._quantity(
                            value=float(ref["high"]), unit=ref.get("unit", ""), code=ref.get("unit", "")
                        )
                    if ref_range:
                        ref_range["text"] = f"{ref.get('low', '')}-{ref.get('high', '')} {ref.get('unit', '')}"
                        obs["referenceRange"] = [ref_range]
            
            # Interpretation (abnormal flags)
            if test_name in abnormal_flags:
                flag = abnormal_flags[test_name] if isinstance(abnormal_flags, dict) else "A"
                interpretation_map = {
                    "H": "H",
                    "L": "L",
                    "A": "A",
                    "HH": "HH",
                    "LL": "LL",
                    "N": "N"
                }
                obs["interpretation"] = [self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        code=interpretation_map.get(flag, "A"),
                        display={"H": "High", "L": "Low", "A": "Abnormal", "HH": "Critical High", "LL": "Critical Low", "N": "Normal"}.get(flag, "Abnormal")
                    )]
                )]
            
            # Performer
            if lab_result.entered_by:
                obs["performer"] = [{
                    "actor": self.builder._reference(
                        "Practitioner", f"Practitioner-{lab_result.entered_by.id}",
                        lab_result.entered_by.get_full_name()
                    )
                }]
            
            # Note
            if lab_result.result_text:
                obs["note"] = [{"text": lab_result.result_text}]
            
            observations.append(obs)
        
        return observations


@register_fhir_mapper("Observation")
class EmergencyVitalsObservationMapper(FHIRMapper):
    """Maps internal EmergencyVitals to FHIR Observation resources."""
    
    source_model = "emergency.EmergencyVitals"
    target_resource_type = "Observation"
    required_source_fields = ["visit", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = ObservationResourceBuilder()
    
    def map(self, er_vitals) -> List[Dict[str, Any]]:
        """Map EmergencyVitals to FHIR Observations."""
        observations = []
        visit = er_vitals.visit
        patient = visit.patient
        recorded_at = er_vitals.recorded_at
        
        vital_fields = [
            ("temperature", er_vitals.temperature, "8310-5", "Body temperature", "°C", "Cel"),
            ("systolic_bp", er_vitals.systolic_bp, "8480-6", "Systolic blood pressure", "mmHg", "mm[Hg]"),
            ("diastolic_bp", er_vitals.diastolic_bp, "8462-4", "Diastolic blood pressure", "mmHg", "mm[Hg]"),
            ("heart_rate", er_vitals.heart_rate, "8867-4", "Heart rate", "/min", "/min"),
            ("respiratory_rate", er_vitals.respiratory_rate, "9279-1", "Respiratory rate", "/min", "/min"),
            ("spo2", er_vitals.spo2, "2708-6", "Oxygen saturation", "%", "%"),
            ("blood_sugar", er_vitals.blood_sugar, "2345-7", "Glucose in Blood", "mg/dL", "mg/dL"),
        ]
        
        for field_name, value, loinc_code, display, unit, ucum in vital_fields:
            if value is not None:
                resource_id = self._get_stable_id(er_vitals, f"Observation-{field_name}")
                
                obs = self.builder._base_resource(resource_id)
                obs["status"] = "final"
                obs["category"] = [self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://terminology.hl7.org/CodeSystem/observation-category",
                        code="vital-signs",
                        display="Vital Signs"
                    )]
                )]
                obs["code"] = self.builder._codeable_concept(
                    coding=[self.builder._coding(
                        system="http://loinc.org",
                        code=loinc_code,
                        display=display
                    )],
                    text=display
                )
                obs["subject"] = self.builder._reference("Patient", f"Patient-{patient.id}", patient.name)
                obs["encounter"] = self.builder._reference("Encounter", f"Encounter-{visit.id}", "Emergency Visit")
                obs["effectiveDateTime"] = recorded_at.isoformat()
                
                obs["valueQuantity"] = self.builder._quantity(
                    value=float(value), unit=unit, code=ucum
                )
                
                if er_vitals.recorded_by:
                    obs["performer"] = [{
                        "actor": self.builder._reference(
                            "Practitioner", f"Practitioner-{er_vitals.recorded_by.id}",
                            er_vitals.recorded_by.name
                        )
                    }]
                
                observations.append(obs)
        
        return observations


def map_vitals_to_fhir(vital_sign, context: MappingContext) -> List[Dict[str, Any]]:
    """Map VitalSign to FHIR Observations."""
    mapper = VitalSignObservationMapper(context)
    return mapper.map(vital_sign)


def map_lab_result_to_fhir(lab_result, context: MappingContext) -> List[Dict[str, Any]]:
    """Map LabResult to FHIR Observations."""
    mapper = LabResultObservationMapper(context)
    return mapper.map(lab_result)


def map_er_vitals_to_fhir(er_vitals, context: MappingContext) -> List[Dict[str, Any]]:
    """Map EmergencyVitals to FHIR Observations."""
    mapper = EmergencyVitalsObservationMapper(context)
    return mapper.map(er_vitals)