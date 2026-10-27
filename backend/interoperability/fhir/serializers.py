"""
FHIR Serializers

Serializers for outputting FHIR resources as JSON via DRF.
These are separate from internal model serializers - they output pure FHIR JSON.
"""

from rest_framework import serializers
from typing import Dict, Any, List, Optional


class FHIRResourceSerializer(serializers.Serializer):
    """Base serializer for FHIR resources."""
    
    resourceType = serializers.CharField()
    id = serializers.CharField()
    meta = serializers.DictField(required=False)
    identifier = serializers.ListField(child=serializers.DictField(), required=False)
    
    def to_representation(self, instance):
        """Pass through the FHIR resource dict as-is."""
        if isinstance(instance, dict):
            return instance
        return super().to_representation(instance)


class FHIRPatientSerializer(FHIRResourceSerializer):
    """FHIR Patient serializer."""
    
    resourceType = serializers.CharField(default="Patient")
    name = serializers.ListField(child=serializers.DictField(), required=False)
    telecom = serializers.ListField(child=serializers.DictField(), required=False)
    gender = serializers.CharField(required=False)
    birthDate = serializers.DateField(required=False)
    address = serializers.ListField(child=serializers.DictField(), required=False)
    managingOrganization = serializers.DictField(required=False)
    active = serializers.BooleanField(required=False)


class FHIRPractitionerSerializer(FHIRResourceSerializer):
    """FHIR Practitioner serializer."""
    
    resourceType = serializers.CharField(default="Practitioner")
    name = serializers.ListField(child=serializers.DictField(), required=False)
    telecom = serializers.ListField(child=serializers.DictField(), required=False)
    qualification = serializers.ListField(child=serializers.DictField(), required=False)
    communication = serializers.ListField(child=serializers.DictField(), required=False)
    active = serializers.BooleanField(required=False)


class FHIROrganizationSerializer(FHIRResourceSerializer):
    """FHIR Organization serializer."""
    
    resourceType = serializers.CharField(default="Organization")
    name = serializers.CharField(required=False)
    telecom = serializers.ListField(child=serializers.DictField(), required=False)
    address = serializers.ListField(child=serializers.DictField(), required=False)
    type = serializers.ListField(child=serializers.DictField(), required=False)
    active = serializers.BooleanField(required=False)
    partOf = serializers.DictField(required=False)


class FHIREncounterSerializer(FHIRResourceSerializer):
    """FHIR Encounter serializer."""
    
    resourceType = serializers.CharField(default="Encounter")
    status = serializers.CharField(required=False)
    class_field = serializers.DictField(source="class", required=False)
    type = serializers.ListField(child=serializers.DictField(), required=False)
    subject = serializers.DictField(required=False)
    participant = serializers.ListField(child=serializers.DictField(), required=False)
    period = serializers.DictField(required=False)
    serviceProvider = serializers.DictField(required=False)
    reasonCode = serializers.ListField(child=serializers.DictField(), required=False)
    diagnosis = serializers.ListField(child=serializers.DictField(), required=False)
    hospitalization = serializers.DictField(required=False)
    priority = serializers.DictField(required=False)


class FHIRObservationSerializer(FHIRResourceSerializer):
    """FHIR Observation serializer."""
    
    resourceType = serializers.CharField(default="Observation")
    status = serializers.CharField(required=False)
    category = serializers.ListField(child=serializers.DictField(), required=False)
    code = serializers.DictField(required=False)
    subject = serializers.DictField(required=False)
    encounter = serializers.DictField(required=False)
    effectiveDateTime = serializers.DateTimeField(required=False)
    issued = serializers.DateTimeField(required=False)
    valueQuantity = serializers.DictField(required=False)
    valueString = serializers.CharField(required=False)
    dataAbsentReason = serializers.DictField(required=False)
    interpretation = serializers.ListField(child=serializers.DictField(), required=False)
    referenceRange = serializers.ListField(child=serializers.DictField(), required=False)
    performer = serializers.ListField(child=serializers.DictField(), required=False)
    note = serializers.ListField(child=serializers.DictField(), required=False)


class FHIRConditionSerializer(FHIRResourceSerializer):
    """FHIR Condition serializer."""
    
    resourceType = serializers.CharField(default="Condition")
    clinicalStatus = serializers.DictField(required=False)
    verificationStatus = serializers.DictField(required=False)
    category = serializers.ListField(child=serializers.DictField(), required=False)
    code = serializers.DictField(required=False)
    subject = serializers.DictField(required=False)
    encounter = serializers.DictField(required=False)
    onsetDateTime = serializers.DateTimeField(required=False)
    recordedDate = serializers.DateTimeField(required=False)
    recorder = serializers.DictField(required=False)
    asserter = serializers.DictField(required=False)
    note = serializers.ListField(child=serializers.DictField(), required=False)


class FHIRAllergyIntoleranceSerializer(FHIRResourceSerializer):
    """FHIR AllergyIntolerance serializer."""
    
    resourceType = serializers.CharField(default="AllergyIntolerance")
    clinicalStatus = serializers.DictField(required=False)
    verificationStatus = serializers.DictField(required=False)
    type = serializers.CharField(required=False)
    category = serializers.ListField(child=serializers.CharField(), required=False)
    criticality = serializers.CharField(required=False)
    code = serializers.DictField(required=False)
    patient = serializers.DictField(required=False)
    onsetDateTime = serializers.DateTimeField(required=False)
    recordedDate = serializers.DateTimeField(required=False)
    reaction = serializers.ListField(child=serializers.DictField(), required=False)
    note = serializers.ListField(child=serializers.DictField(), required=False)


class FHIRMedicationSerializer(FHIRResourceSerializer):
    """FHIR Medication serializer."""
    
    resourceType = serializers.CharField(default="Medication")
    code = serializers.DictField(required=False)
    status = serializers.CharField(required=False)
    form = serializers.DictField(required=False)


class FHIRMedicationRequestSerializer(FHIRResourceSerializer):
    """FHIR MedicationRequest serializer."""
    
    resourceType = serializers.CharField(default="MedicationRequest")
    status = serializers.CharField(required=False)
    intent = serializers.CharField(required=False)
    category = serializers.ListField(child=serializers.DictField(), required=False)
    priority = serializers.CharField(required=False)
    medicationReference = serializers.DictField(required=False)
    medicationCodeableConcept = serializers.DictField(required=False)
    subject = serializers.DictField(required=False)
    encounter = serializers.DictField(required=False)
    authoredOn = serializers.DateTimeField(required=False)
    requester = serializers.DictField(required=False)
    performer = serializers.DictField(required=False)
    dosageInstruction = serializers.ListField(child=serializers.DictField(), required=False)
    dispenseRequest = serializers.DictField(required=False)
    substitution = serializers.DictField(required=False)
    note = serializers.ListField(child=serializers.DictField(), required=False)


class FHIRDiagnosticReportSerializer(FHIRResourceSerializer):
    """FHIR DiagnosticReport serializer."""
    
    resourceType = serializers.CharField(default="DiagnosticReport")
    status = serializers.CharField(required=False)
    category = serializers.ListField(child=serializers.DictField(), required=False)
    code = serializers.DictField(required=False)
    subject = serializers.DictField(required=False)
    encounter = serializers.DictField(required=False)
    effectiveDateTime = serializers.DateTimeField(required=False)
    issued = serializers.DateTimeField(required=False)
    performer = serializers.ListField(child=serializers.DictField(), required=False)
    requester = serializers.DictField(required=False)
    specimen = serializers.ListField(child=serializers.DictField(), required=False)
    result = serializers.ListField(child=serializers.DictField(), required=False)
    conclusion = serializers.CharField(required=False)
    conclusionCode = serializers.ListField(child=serializers.DictField(), required=False)


class FHIRDocumentReferenceSerializer(FHIRResourceSerializer):
    """FHIR DocumentReference serializer."""
    
    resourceType = serializers.CharField(default="DocumentReference")
    masterIdentifier = serializers.DictField(required=False)
    identifier = serializers.ListField(child=serializers.DictField(), required=False)
    status = serializers.CharField(required=False)
    type = serializers.DictField(required=False)
    category = serializers.ListField(child=serializers.DictField(), required=False)
    subject = serializers.DictField(required=False)
    date = serializers.DateTimeField(required=False)
    author = serializers.ListField(child=serializers.DictField(), required=False)
    authenticator = serializers.DictField(required=False)
    custodian = serializers.DictField(required=False)
    content = serializers.ListField(child=serializers.DictField(), required=False)
    context = serializers.DictField(required=False)


class FHIRConsentSerializer(FHIRResourceSerializer):
    """FHIR Consent serializer."""
    
    resourceType = serializers.CharField(default="Consent")
    status = serializers.CharField(required=False)
    scope = serializers.DictField(required=False)
    category = serializers.ListField(child=serializers.DictField(), required=False)
    patient = serializers.DictField(required=False)
    dateTime = serializers.DateTimeField(required=False)
    performer = serializers.ListField(child=serializers.DictField(), required=False)
    organization = serializers.ListField(child=serializers.DictField(), required=False)
    purpose = serializers.ListField(child=serializers.DictField(), required=False)
    policyRule = serializers.DictField(required=False)
    provision = serializers.DictField(required=False)


class FHIRProvenanceSerializer(FHIRResourceSerializer):
    """FHIR Provenance serializer."""
    
    resourceType = serializers.CharField(default="Provenance")
    target = serializers.ListField(child=serializers.DictField(), required=False)
    recorded = serializers.DateTimeField(required=False)
    agent = serializers.ListField(child=serializers.DictField(), required=False)
    entity = serializers.ListField(child=serializers.DictField(), required=False)
    activity = serializers.DictField(required=False)


class FHIRBundleSerializer(serializers.Serializer):
    """FHIR Bundle serializer."""
    
    resourceType = serializers.CharField(default="Bundle")
    id = serializers.CharField(required=False)
    meta = serializers.DictField(required=False)
    type = serializers.CharField(required=False)
    total = serializers.IntegerField(required=False)
    link = serializers.ListField(child=serializers.DictField(), required=False)
    entry = serializers.ListField(child=serializers.DictField(), required=False)
    
    def to_representation(self, instance):
        """Pass through the bundle dict as-is."""
        if isinstance(instance, dict):
            return instance
        return super().to_representation(instance)


class FHIRCapabilityStatementSerializer(serializers.Serializer):
    """FHIR CapabilityStatement serializer for /metadata endpoint."""
    
    resourceType = serializers.CharField(default="CapabilityStatement")
    status = serializers.CharField(default="active")
    date = serializers.DateTimeField()
    kind = serializers.CharField(default="instance")
    fhirVersion = serializers.CharField(default="4.0.1")
    format = serializers.ListField(child=serializers.CharField(), default=["json"])
    rest = serializers.ListField(child=serializers.DictField(), required=False)