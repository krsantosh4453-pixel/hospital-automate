"""
Base FHIR Mapper

Provides the mapping infrastructure to convert internal Django models to FHIR resources.
Each mapper encapsulates the logic for one internal model -> one FHIR resource type.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from dataclasses import dataclass

from ..resources.base import FHIRResourceBuilder, FHIRBundleBuilder


@dataclass
class MappingContext:
    """
    Context passed to mappers during FHIR resource generation.
    
    Contains hospital-scoped information and references needed for proper
    FHIR resource construction (e.g., base URLs, hospital identifiers).
    """
    hospital_id: int
    base_url: str = "http://localhost:8000/fhir"
    include_narrative: bool = False
    user_id: Optional[int] = None
    
    def get_resource_url(self, resource_type: str, resource_id: str) -> str:
        """Generate the full URL for a FHIR resource."""
        return f"{self.base_url}/{resource_type}/{resource_id}"


class FHIRMapper(ABC):
    """
    Abstract base class for FHIR mappers.
    
    Each mapper handles one internal model type and produces one FHIR resource type.
    Mappers are stateless and receive a MappingContext for hospital-scoped operations.
    """
    
    # The internal Django model class this mapper handles
    source_model: Type = None
    
    # The FHIR resource type this mapper produces
    target_resource_type: str = ""
    
    # Required fields that must be present in source for valid mapping
    required_source_fields: List[str] = []
    
    def __init__(self, context: MappingContext):
        self.context = context
        self.builder: FHIRResourceBuilder = None
    
    @abstractmethod
    def map(self, source_obj: Any) -> Dict[str, Any]:
        """
        Map a single source object to a FHIR resource.
        
        Args:
            source_obj: Instance of source_model
            
        Returns:
            FHIR resource dictionary
        """
        pass
    
    def map_multiple(self, source_objects: List[Any]) -> List[Dict[str, Any]]:
        """Map multiple source objects to FHIR resources."""
        return [self.map(obj) for obj in source_objects]
    
    def build_bundle(self, source_objects: List[Any], 
                     bundle_type: str = "collection",
                     total: Optional[int] = None) -> Dict[str, Any]:
        """Map multiple objects and wrap in a FHIR Bundle."""
        bundle_builder = FHIRBundleBuilder(bundle_type=bundle_type, total=total)
        
        for obj in source_objects:
            resource = self.map(obj)
            resource_id = resource.get("id", "")
            full_url = self.context.get_resource_url(self.target_resource_type, resource_id)
            bundle_builder.add_entry(resource, full_url=full_url, search_mode="match")
        
        return bundle_builder.build()
    
    def validate_source(self, source_obj: Any) -> List[str]:
        """
        Validate source object has required fields for mapping.
        Returns list of missing/invalid fields.
        """
        missing = []
        for field in self.required_source_fields:
            if not hasattr(source_obj, field) or getattr(source_obj, field) in (None, ""):
                missing.append(field)
        return missing
    
    def _get_stable_id(self, source_obj: Any, prefix: str = "") -> str:
        """
        Generate a stable FHIR ID from internal model.
        
        Uses internal PK but prefixes with resource type for clarity.
        This ensures stable IDs across exports while avoiding collisions.
        """
        pk = getattr(source_obj, "pk", None) or getattr(source_obj, "id", None)
        if pk is None:
            raise ValueError("Source object must have a primary key")
        if prefix:
            return f"{prefix}-{pk}"
        return f"{self.target_resource_type.lower()}-{pk}"
    
    def _get_hospital_identifier(self, hospital) -> Dict[str, Any]:
        """Create a stable identifier for a hospital."""
        return {
            "system": "http://hospital-automate.local/identifiers/hospital",
            "value": f"HOSP-{hospital.id}",
            "use": "official"
        }
    
    def _get_patient_identifier(self, patient, hospital) -> List[Dict[str, Any]]:
        """
        Get all identifiers for a patient in a hospital context.
        
        Includes:
        - Internal PatientHospital UHID (if exists)
        - Direct patient-hospital link
        - ABHA ID (if implemented)
        """
        identifiers = []
        
        # Internal system identifier
        identifiers.append({
            "system": "http://hospital-automate.local/identifiers/patient",
            "value": f"PAT-{patient.id}",
            "use": "usual"
        })
        
        # Hospital-specific UHID from PatientHospital membership
        try:
            membership = patient.hospital_memberships.filter(
                hospital=hospital, is_active=True
            ).first()
            if membership and membership.uhid:
                identifiers.append({
                    "system": f"http://hospital-automate.local/identifiers/uhid/{hospital.id}",
                    "value": membership.uhid,
                    "use": "official",
                    "type": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical Record Number"
                        }]
                    }
                })
        except Exception:
            pass
        
        # Direct hospital link UHID fallback
        if hasattr(patient, "hospital_id") and patient.hospital_id == hospital.id:
            if not any(i["system"].endswith(f"uhid/{hospital.id}") for i in identifiers):
                identifiers.append({
                    "system": f"http://hospital-automate.local/identifiers/uhid/{hospital.id}",
                    "value": f"PAT-{patient.id}",
                    "use": "secondary"
                })
        
        return identifiers
    
    def _get_practitioner_identifier(self, doctor, hospital) -> List[Dict[str, Any]]:
        """Get identifiers for a doctor/practitioner."""
        identifiers = [{
            "system": "http://hospital-automate.local/identifiers/practitioner",
            "value": f"DOC-{doctor.id}",
            "use": "usual"
        }]
        
        # Hospital-specific identifier
        identifiers.append({
            "system": f"http://hospital-automate.local/identifiers/practitioner/{hospital.id}",
            "value": f"DOC-{doctor.id}",
            "use": "official"
        })
        
        return identifiers


class FHIRMappingRegistry:
    """
    Registry of all FHIR mappers.
    
    Provides centralized access to mappers and supports dynamic discovery.
    """
    
    _mappers: Dict[str, Type[FHIRMapper]] = {}
    
    @classmethod
    def register(cls, resource_type: str, mapper_class: Type[FHIRMapper]):
        """Register a mapper for a FHIR resource type."""
        cls._mappers[resource_type] = mapper_class
    
    @classmethod
    def get_mapper(cls, resource_type: str) -> Optional[Type[FHIRMapper]]:
        """Get mapper class for a FHIR resource type."""
        return cls._mappers.get(resource_type)
    
    @classmethod
    def get_all_mappers(cls) -> Dict[str, Type[FHIRMapper]]:
        """Get all registered mappers."""
        return cls._mappers.copy()
    
    @classmethod
    def create_mapper(cls, resource_type: str, context: MappingContext) -> Optional[FHIRMapper]:
        """Instantiate a mapper for the given resource type."""
        mapper_class = cls.get_mapper(resource_type)
        if mapper_class:
            return mapper_class(context)
        return None


def register_fhir_mapper(resource_type: str):
    """Decorator to register a FHIR mapper class."""
    def decorator(mapper_class: Type[FHIRMapper]):
        FHIRMappingRegistry.register(resource_type, mapper_class)
        return mapper_class
    return decorator