"""
Base FHIR Resource Builder

Provides common functionality for building FHIR R4 resources from internal models.
All resource builders should inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, date
import json


class FHIRResourceBuilder(ABC):
    """
    Abstract base class for FHIR resource builders.
    
    Each builder converts internal Django models to FHIR R4 resource dictionaries.
    Builders do NOT expose Django models directly - they create clean FHIR representations.
    """
    
    # FHIR resource type (e.g., "Patient", "Observation", "Encounter")
    resource_type: str = ""
    
    # FHIR version
    fhir_version: str = "4.0.1"
    
    def __init__(self, hospital_id: Optional[int] = None):
        self.hospital_id = hospital_id
        self._extensions: Dict[str, Any] = {}
    
    @abstractmethod
    def build(self, source_obj: Any) -> Dict[str, Any]:
        """
        Build a FHIR resource from the source internal model object.
        
        Args:
            source_obj: The internal Django model instance
            
        Returns:
            Dictionary representing the FHIR resource
        """
        pass
    
    def _base_resource(self, id_value: str, meta: Optional[Dict] = None) -> Dict[str, Any]:
        """Create base FHIR resource structure with id, meta, and resourceType."""
        resource = {
            "resourceType": self.resource_type,
            "id": id_value,
            "meta": meta or self._default_meta(),
        }
        return resource
    
    def _default_meta(self) -> Dict[str, Any]:
        """Default meta element for FHIR resources."""
        return {
            "versionId": "1",
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "profile": [f"http://hl7.org/fhir/StructureDefinition/{self.resource_type}"],
            "tag": [
                {
                    "system": "http://hospital-automate.local/fhir/tags",
                    "code": "hospital-automate",
                    "display": "Hospital Automate FHIR Export"
                }
            ]
        }
    
    def _identifier(self, system: str, value: str, use: str = "official", 
                    type_code: Optional[str] = None, period: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a FHIR Identifier element."""
        identifier = {
            "use": use,
            "system": system,
            "value": value
        }
        if type_code:
            identifier["type"] = {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                    "code": type_code
                }]
            }
        if period:
            identifier["period"] = period
        return identifier
    
    def _human_name(self, family: str, given: List[str], prefix: Optional[List[str]] = None,
                    suffix: Optional[List[str]] = None, use: str = "official") -> Dict[str, Any]:
        """Create a FHIR HumanName element."""
        name = {
            "use": use,
            "family": family,
            "given": given
        }
        if prefix:
            name["prefix"] = prefix
        if suffix:
            name["suffix"] = suffix
        return name
    
    def _contact_point(self, system: str, value: str, use: str = "home",
                       rank: Optional[int] = None, period: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a FHIR ContactPoint element."""
        contact = {
            "system": system,
            "value": value,
            "use": use
        }
        if rank is not None:
            contact["rank"] = rank
        if period:
            contact["period"] = period
        return contact
    
    def _address(self, line: Optional[List[str]] = None, city: Optional[str] = None,
                 state: Optional[str] = None, postal_code: Optional[str] = None,
                 country: Optional[str] = None, use: str = "home",
                 type_: str = "physical") -> Dict[str, Any]:
        """Create a FHIR Address element."""
        address = {"use": use, "type": type_}
        if line:
            address["line"] = line
        if city:
            address["city"] = city
        if state:
            address["state"] = state
        if postal_code:
            address["postalCode"] = postal_code
        if country:
            address["country"] = country
        return address
    
    def _reference(self, resource_type: str, id_value: str, 
                   display: Optional[str] = None, identifier: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a FHIR Reference element."""
        ref = {"reference": f"{resource_type}/{id_value}"}
        if display:
            ref["display"] = display
        if identifier:
            ref["identifier"] = identifier
        return ref
    
    def _codeable_concept(self, coding: List[Dict], text: Optional[str] = None) -> Dict[str, Any]:
        """Create a FHIR CodeableConcept element."""
        concept = {"coding": coding}
        if text:
            concept["text"] = text
        return concept
    
    def _coding(self, system: str, code: str, display: Optional[str] = None,
                version: Optional[str] = None, user_selected: bool = False) -> Dict[str, Any]:
        """Create a FHIR Coding element."""
        coding = {"system": system, "code": code}
        if display:
            coding["display"] = display
        if version:
            coding["version"] = version
        if user_selected:
            coding["userSelected"] = user_selected
        return coding
    
    def _period(self, start: Optional[datetime] = None, 
                end: Optional[datetime] = None) -> Dict[str, Any]:
        """Create a FHIR Period element."""
        period = {}
        if start:
            period["start"] = start.isoformat() if isinstance(start, datetime) else str(start)
        if end:
            period["end"] = end.isoformat() if isinstance(end, datetime) else str(end)
        return period if period else None
    
    def _quantity(self, value: float, unit: str, system: str = "http://unitsofmeasure.org",
                  code: Optional[str] = None) -> Dict[str, Any]:
        """Create a FHIR Quantity element."""
        qty = {"value": value, "unit": unit, "system": system}
        if code:
            qty["code"] = code
        return qty
    
    def _attachment(self, content_type: str, data: Optional[str] = None,
                    url: Optional[str] = None, title: Optional[str] = None,
                    creation: Optional[datetime] = None) -> Dict[str, Any]:
        """Create a FHIR Attachment element."""
        attachment = {"contentType": content_type}
        if data:
            attachment["data"] = data
        if url:
            attachment["url"] = url
        if title:
            attachment["title"] = title
        if creation:
            attachment["creation"] = creation.isoformat() if isinstance(creation, datetime) else str(creation)
        return attachment
    
    def _annotation(self, text: str, author_string: Optional[str] = None,
                    time: Optional[datetime] = None) -> Dict[str, Any]:
        """Create a FHIR Annotation element."""
        annotation = {"text": text}
        if author_string:
            annotation["authorString"] = author_string
        if time:
            annotation["time"] = time.isoformat() if isinstance(time, datetime) else str(time)
        return annotation
    
    def to_json(self, resource: Dict[str, Any], pretty: bool = False) -> str:
        """Serialize resource to JSON string."""
        if pretty:
            return json.dumps(resource, indent=2, default=str)
        return json.dumps(resource, default=str, separators=(",", ":"))
    
    def validate_required_fields(self, resource: Dict[str, Any], 
                                  required: List[str]) -> List[str]:
        """Validate required fields are present. Returns list of missing fields."""
        missing = []
        for field in required:
            if field not in resource or resource[field] in (None, "", [], {}):
                missing.append(field)
        return missing


class FHIRBundleBuilder:
    """
    Builder for FHIR Bundle resources.
    
    Supports: collection, document, message, transaction, transaction-response,
    batch, batch-response, history, searchset
    """
    
    BUNDLE_TYPES = [
        "collection", "document", "message", "transaction", 
        "transaction-response", "batch", "batch-response", 
        "history", "searchset"
    ]
    
    def __init__(self, bundle_type: str = "collection", total: Optional[int] = None):
        if bundle_type not in self.BUNDLE_TYPES:
            raise ValueError(f"Invalid bundle type: {bundle_type}. Must be one of {self.BUNDLE_TYPES}")
        self.bundle_type = bundle_type
        self.total = total
        self.entries: List[Dict] = []
        self.links: List[Dict] = []
    
    def add_entry(self, resource: Dict[str, Any], 
                  full_url: Optional[str] = None,
                  search_mode: Optional[str] = None,
                  request: Optional[Dict] = None,
                  response: Optional[Dict] = None) -> "FHIRBundleBuilder":
        """Add a resource entry to the bundle."""
        entry = {"resource": resource}
        if full_url:
            entry["fullUrl"] = full_url
        if search_mode:
            entry["search"] = {"mode": search_mode}
        if request:
            entry["request"] = request
        if response:
            entry["response"] = response
        self.entries.append(entry)
        return self
    
    def add_link(self, relation: str, url: str) -> "FHIRBundleBuilder":
        """Add a pagination/link relation."""
        self.links.append({"relation": relation, "url": url})
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the complete Bundle resource."""
        bundle = {
            "resourceType": "Bundle",
            "id": f"bundle-{datetime.utcnow().timestamp()}",
            "meta": {
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            },
            "type": self.bundle_type,
            "entry": self.entries
        }
        if self.total is not None:
            bundle["total"] = self.total
        if self.links:
            bundle["link"] = self.links
        return bundle