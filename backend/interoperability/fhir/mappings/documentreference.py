"""
FHIR DocumentReference Mapper

Maps internal ClinicalNote, DischargeSummary, and other clinical documents
to FHIR R4 DocumentReference resource.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import FHIRMapper, register_fhir_mapper, MappingContext
from ..resources.base import FHIRResourceBuilder


class DocumentReferenceResourceBuilder(FHIRResourceBuilder):
    """FHIR DocumentReference resource builder."""
    resource_type = "DocumentReference"


# Document type mapping
DOCUMENT_TYPE_MAP = {
    "clinical_note": {
        "code": "34133-9",
        "display": "Summarization of episode note",
        "system": "http://loinc.org"
    },
    "discharge_summary": {
        "code": "18842-5",
        "display": "Discharge summary",
        "system": "http://loinc.org"
    },
    "prescription": {
        "code": "57833-6",
        "display": "Prescription",
        "system": "http://loinc.org"
    },
    "referral": {
        "code": "57133-1",
        "display": "Referral note",
        "system": "http://loinc.org"
    },
    "consent": {
        "code": "57016-8",
        "display": "Consent form",
        "system": "http://loinc.org"
    },
}


@register_fhir_mapper("DocumentReference")
class ClinicalNoteDocumentReferenceMapper(FHIRMapper):
    """Maps internal ClinicalNote to FHIR DocumentReference."""
    
    source_model = "clinical.ClinicalNote"
    target_resource_type = "DocumentReference"
    required_source_fields = ["visit", "note", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = DocumentReferenceResourceBuilder()
    
    def map(self, clinical_note) -> Dict[str, Any]:
        """Map ClinicalNote to FHIR DocumentReference."""
        visit = clinical_note.visit
        patient = visit.patient
        hospital = visit.hospital
        doctor = clinical_note.doctor
        
        resource_id = self._get_stable_id(clinical_note, "DocumentReference")
        
        resource = self.builder._base_resource(resource_id)
        
        # Master Identifier
        resource["masterIdentifier"] = {
            "system": f"http://hospital-automate.local/identifiers/document/{hospital.id}",
            "value": f"CN-{clinical_note.id}",
            "use": "official"
        }
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/document/{hospital.id}",
            "value": f"CN-{clinical_note.id}",
            "use": "usual"
        }]
        
        # Status
        resource["status"] = "current"
        
        # Type
        doc_type = DOCUMENT_TYPE_MAP["clinical_note"]
        resource["type"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system=doc_type["system"],
                code=doc_type["code"],
                display=doc_type["display"]
            )],
            text="Clinical Note"
        )
        
        # Category
        resource["category"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                code="clinical-note",
                display="Clinical Note"
            )]
        )]
        
        # Subject (Patient)
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Date (creation)
        resource["date"] = clinical_note.created_at.isoformat() if clinical_note.created_at else None
        
        # Author (Doctor)
        if doctor:
            resource["author"] = [self.builder._reference(
                "Practitioner", f"Practitioner-{doctor.id}", doctor.name
            )]
        
        # Authenticator (same as author for clinical notes)
        resource["authenticator"] = resource["author"][0] if resource.get("author") else None
        
        # Custodian (Hospital)
        resource["custodian"] = self.builder._reference(
            "Organization", f"Organization-{hospital.id}", hospital.name
        )
        
        # Content
        resource["content"] = [{
            "attachment": self.builder._attachment(
                content_type="text/plain",
                data=clinical_note.note,
                title=f"Clinical Note for {patient.name}",
                creation=clinical_note.created_at
            ),
            "format": {
                "system": "http://ihe.net/fhir/ValueSet/IHE.FormatCode.codesystem",
                "code": "urn:ihe:iti:xds-sd:pdf:2008",
                "display": "PDF Document"
            }
        }]
        
        # Context
        resource["context"] = self._build_context(visit, clinical_note)
        
        return resource
    
    def _build_context(self, visit, clinical_note) -> Dict[str, Any]:
        """Build DocumentReference.context."""
        context = {
            "encounter": [self.builder._reference(
                "Encounter", f"Encounter-{visit.id}", f"Visit {visit.visit_type}"
            )],
            "period": self.builder._period(start=visit.visit_date),
            "facilityType": self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    code="HOSP",
                    display="Hospital"
                )]
            ),
            "practiceSetting": self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/practice-setting",
                    code="394802001",
                    display="General Medicine"
                )]
            )
        }
        return context


@register_fhir_mapper("DocumentReference")
class DischargeSummaryDocumentReferenceMapper(FHIRMapper):
    """Maps internal DischargeSummary to FHIR DocumentReference."""
    
    source_model = "ipd.DischargeSummary"
    target_resource_type = "DocumentReference"
    required_source_fields = ["admission", "summary", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = DocumentReferenceResourceBuilder()
    
    def map(self, discharge_summary) -> Dict[str, Any]:
        """Map DischargeSummary to FHIR DocumentReference."""
        admission = discharge_summary.admission
        patient = admission.patient
        hospital = admission.hospital
        doctor = discharge_summary.authorized_doctor
        
        resource_id = self._get_stable_id(discharge_summary, "DocumentReference")
        
        resource = self.builder._base_resource(resource_id)
        
        # Master Identifier
        resource["masterIdentifier"] = {
            "system": f"http://hospital-automate.local/identifiers/document/{hospital.id}",
            "value": f"DS-{discharge_summary.id}",
            "use": "official"
        }
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/document/{hospital.id}",
            "value": f"DS-{discharge_summary.id}",
            "use": "usual"
        }]
        
        # Status - only finalized summaries should be shared
        resource["status"] = "current" if discharge_summary.finalized else "superseded"
        
        # Type
        doc_type = DOCUMENT_TYPE_MAP["discharge_summary"]
        resource["type"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system=doc_type["system"],
                code=doc_type["code"],
                display=doc_type["display"]
            )],
            text="Discharge Summary"
        )
        
        # Category
        resource["category"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                code="discharge-summary",
                display="Discharge Summary"
            )]
        )]
        
        # Subject (Patient)
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Date (finalized or created)
        date_field = discharge_summary.finalized_at or discharge_summary.created_at
        resource["date"] = date_field.isoformat() if date_field else None
        
        # Author
        if doctor:
            resource["author"] = [self.builder._reference(
                "Practitioner", f"Practitioner-{doctor.id}", doctor.name
            )]
        
        # Authenticator
        resource["authenticator"] = resource["author"][0] if resource.get("author") else None
        
        # Custodian
        resource["custodian"] = self.builder._reference(
            "Organization", f"Organization-{hospital.id}", hospital.name
        )
        
        # Content
        resource["content"] = [{
            "attachment": self.builder._attachment(
                content_type="text/plain",
                data=discharge_summary.summary,
                title=f"Discharge Summary for {patient.name}",
                creation=date_field
            ),
            "format": {
                "system": "http://ihe.net/fhir/ValueSet/IHE.FormatCode.codesystem",
                "code": "urn:ihe:iti:xds-sd:pdf:2008",
                "display": "PDF Document"
            }
        }]
        
        # Context
        resource["context"] = {
            "encounter": [self.builder._reference(
                "Encounter", f"Encounter-{admission.id}", "Inpatient Admission"
            )],
            "period": self.builder._period(
                start=admission.admission_date,
                end=admission.discharge_date
            ),
            "facilityType": self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    code="HOSP",
                    display="Hospital"
                )]
            ),
            "practiceSetting": self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/practice-setting",
                    code="394802001",
                    display="General Medicine"
                )]
            )
        }
        
        return resource


@register_fhir_mapper("DocumentReference")
class PatientDocumentDocumentReferenceMapper(FHIRMapper):
    """Maps internal PatientDocument to FHIR DocumentReference."""
    
    source_model = "patients.PatientDocument"
    target_resource_type = "DocumentReference"
    required_source_fields = ["patient", "title", "file", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = DocumentReferenceResourceBuilder()
    
    def map(self, doc) -> Dict[str, Any]:
        """Map PatientDocument to FHIR DocumentReference."""
        patient = doc.patient
        hospital = patient.hospital
        if not hospital and hasattr(patient, "hospital_memberships"):
            membership = patient.hospital_memberships.filter(is_active=True).first()
            if membership:
                hospital = membership.hospital
        
        if not hospital:
            raise ValueError("Patient must be associated with a hospital for FHIR export")
        
        resource_id = self._get_stable_id(doc, "DocumentReference")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/document/{hospital.id}",
            "value": f"DOC-{doc.id}",
            "use": "official"
        }]
        
        # Status
        resource["status"] = "current"
        
        # Type - generic document
        resource["type"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://loinc.org",
                code="11488-4",
                display="Consultation note"
            )],
            text=doc.title
        )
        
        # Category
        if doc.folder:
            resource["category"] = [self.builder._codeable_concept(text=doc.folder)]
        
        # Subject
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Date
        resource["date"] = doc.uploaded_at.isoformat() if doc.uploaded_at else None
        
        # Custodian
        resource["custodian"] = self.builder._reference(
            "Organization", f"Organization-{hospital.id}", hospital.name
        )
        
        # Content - reference to file
        resource["content"] = [{
            "attachment": self.builder._attachment(
                content_type="application/octet-stream",
                url=self.context.get_resource_url("Binary", f"Binary-{doc.id}"),
                title=doc.title,
                creation=doc.uploaded_at
            ),
            "format": {
                "system": "http://ihe.net/fhir/ValueSet/IHE.FormatCode.codesystem",
                "code": "urn:ihe:iti:xds-sd:pdf:2008",
                "display": "PDF Document"
            }
        }]
        
        # Context
        resource["context"] = {
            "facilityType": self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    code="HOSP",
                    display="Hospital"
                )]
            )
        }
        
        return resource


@register_fhir_mapper("DocumentReference")
class AIConsultationDraftDocumentReferenceMapper(FHIRMapper):
    """Maps approved AI Consultation Draft to FHIR DocumentReference."""
    
    source_model = "ai_scribe.AIConsultationDraft"
    target_resource_type = "DocumentReference"
    required_source_fields = ["consultation", "structured_extraction", "id"]
    
    def __init__(self, context: MappingContext):
        super().__init__(context)
        self.builder = DocumentReferenceResourceBuilder()
    
    def map(self, ai_draft) -> Optional[Dict[str, Any]]:
        """Map approved AI Consultation Draft to FHIR DocumentReference.
        
        Only maps drafts with status 'approved' - drafts must not be shared.
        """
        if ai_draft.status != "approved":
            return None
        
        consultation = ai_draft.consultation
        visit = consultation.visit
        patient = consultation.patient
        hospital = consultation.hospital
        doctor = ai_draft.approved_by or consultation.doctor
        
        resource_id = self._get_stable_id(ai_draft, "DocumentReference")
        
        resource = self.builder._base_resource(resource_id)
        
        # Identifier
        resource["identifier"] = [{
            "system": f"http://hospital-automate.local/identifiers/document/{hospital.id}",
            "value": f"AI-{ai_draft.id}",
            "use": "official"
        }]
        
        # Status
        resource["status"] = "current"
        
        # Type - AI-generated clinical note
        resource["type"] = self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://loinc.org",
                code="34133-9",
                display="Summarization of episode note"
            )],
            text="AI-Generated Clinical Note (Doctor Approved)"
        )
        
        # Category
        resource["category"] = [self.builder._codeable_concept(
            coding=[self.builder._coding(
                system="http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                code="clinical-note",
                display="Clinical Note"
            )]
        )]
        
        # Subject
        resource["subject"] = self.builder._reference(
            "Patient", f"Patient-{patient.id}", patient.name
        )
        
        # Date
        resource["date"] = ai_draft.approved_at.isoformat() if ai_draft.approved_at else ai_draft.updated_at.isoformat()
        
        # Author (AI system)
        resource["author"] = [{
            "display": f"AI Medical Scribe ({ai_draft.provider or 'Unknown'} - {ai_draft.provider_model or 'Unknown'})"
        }]
        
        # Authenticator (Doctor who approved)
        if doctor:
            resource["authenticator"] = self.builder._reference(
                "Practitioner", f"Practitioner-{doctor.id}", doctor.name
            )
        
        # Custodian
        resource["custodian"] = self.builder._reference(
            "Organization", f"Organization-{hospital.id}", hospital.name
        )
        
        # Content - structured extraction as JSON
        import json
        content_text = json.dumps(ai_draft.structured_extraction, indent=2)
        if ai_draft.summary:
            content_text = ai_draft.summary + "\n\n---\n\nStructured Extraction:\n" + content_text
        
        resource["content"] = [{
            "attachment": self.builder._attachment(
                content_type="application/json",
                data=content_text,
                title=f"AI-Generated Clinical Note for {patient.name}",
                creation=ai_draft.approved_at
            ),
            "format": {
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-format",
                "code": "application/json",
                "display": "JSON Document"
            }
        }]
        
        # Context
        resource["context"] = {
            "encounter": [self.builder._reference(
                "Encounter", f"Encounter-{visit.id}", f"Visit {visit.visit_type}"
            )],
            "period": self.builder._period(start=visit.visit_date),
            "facilityType": self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    code="HOSP",
                    display="Hospital"
                )]
            ),
            "practiceSetting": self.builder._codeable_concept(
                coding=[self.builder._coding(
                    system="http://terminology.hl7.org/CodeSystem/practice-setting",
                    code="394802001",
                    display="General Medicine"
                )]
            ),
            "related": [{
                "identifier": {
                    "system": "http://hospital-automate.local/identifiers/ai-draft",
                    "value": f"AI-DRAFT-{ai_draft.id}"
                },
                "ref": self.builder._reference(
                    "DocumentReference", f"DocumentReference-{ai_draft.final_clinical_note_id}" if ai_draft.final_clinical_note_id else "unknown",
                    "Final Clinical Note"
                )
            }]
        }
        
        return resource


def map_clinical_note_to_fhir(clinical_note, context: MappingContext) -> Dict[str, Any]:
    """Map ClinicalNote to FHIR DocumentReference."""
    mapper = ClinicalNoteDocumentReferenceMapper(context)
    return mapper.map(clinical_note)


def map_discharge_summary_to_fhir(discharge_summary, context: MappingContext) -> Dict[str, Any]:
    """Map DischargeSummary to FHIR DocumentReference."""
    mapper = DischargeSummaryDocumentReferenceMapper(context)
    return mapper.map(discharge_summary)


def map_patient_document_to_fhir(doc, context: MappingContext) -> Dict[str, Any]:
    """Map PatientDocument to FHIR DocumentReference."""
    mapper = PatientDocumentDocumentReferenceMapper(context)
    return mapper.map(doc)


def map_ai_draft_to_fhir(ai_draft, context: MappingContext) -> Optional[Dict[str, Any]]:
    """Map approved AI Consultation Draft to FHIR DocumentReference."""
    mapper = AIConsultationDraftDocumentReferenceMapper(context)
    return mapper.map(ai_draft)