# Hospital Management System - Interoperability Audit (Phase 0)

**Date:** 2026-10-03
**Auditor:** Senior Healthcare Interoperability Architect

---

## Executive Summary

This audit documents the current state of the Hospital Management System (HMS) before implementing Stage 6 - Healthcare Interoperability (FHIR R4, HL7 v2, ABDM/ABHA).

**Verdict:** No existing FHIR, HL7, ABDM, or ABHA interoperability implementation found. Clean slate for implementation.

---

## Current Architecture Overview

### Backend (Django REST Framework)
- **Framework:** Django 6.1 + DRF + SimpleJWT
- **Database:** SQLite (development) - ready for PostgreSQL
- **Authentication:** JWT with role-based access control (RBAC)
- **Multi-tenancy:** Hospital isolation via `Hospital` model + `StaffHospitalMembership`
- **Permissions:** Custom permission classes (`HospitalIsolationPermission`, `RoleBasedPermission`, `IsHospitalMember`)

### Frontend (React + Vite)
- **Framework:** React 18 + Vite
- **API Client:** Custom `api.js` service with token refresh
- **State:** Component-level state + React Context

---

## Data Model Inventory (FHIR Mapping Candidates)

| Internal Model | App | FHIR Resource Target | Status |
|---|---|---|---|
| `Patient` | patients | **Patient** | ✅ Ready |
| `PatientHospital` (membership) | patients | Patient.identifier + Patient.link | ✅ Ready |
| `Doctor` | doctors | **Practitioner** | ✅ Ready |
| `Hospital` | hospital | **Organization** | ✅ Ready |
| `Department` | hospital | Organization.partOf | ✅ Ready |
| `Visit` (OPD) | encounters | **Encounter** (class=AMB) | ✅ Ready |
| `Admission` (IPD) | ipd | **Encounter** (class=IMP) | ✅ Ready |
| `EmergencyVisit` | emergency | **Encounter** (class=EMER) | ✅ Ready |
| `VitalSign` | clinical | **Observation** (vital signs) | ✅ Ready |
| `Allergy` | clinical | **AllergyIntolerance** | ✅ Ready |
| `Diagnosis` | clinical | **Condition** | ✅ Ready |
| `Prescription` + `PrescriptionItem` | clinical | **MedicationRequest** + **Medication** | ✅ Ready |
| `LabTest` + `LabResult` | laboratory | **DiagnosticReport** + **Observation** | ✅ Ready |
| `ClinicalNote` | clinical | **DocumentReference** (type=clinical-note) | ✅ Ready |
| `DischargeSummary` | ipd | **DocumentReference** (type=discharge-summary) | ✅ Ready |
| `Consent` | notifications | **Consent** | ✅ Ready |
| `AuditLog` | audit | **Provenance** | ✅ Ready |
| `Medicine` | pharmacy | **Medication** (catalog) | ✅ Ready |
| `Nurse` | nurses | **Practitioner** (role=nurse) | ✅ Ready |

### Models NOT directly mappable to standard FHIR resources:
- `QueueToken` → Queue management (custom)
- `BedAllocation` → Location/Encounter extension
- `ServiceOrder` / `Procedure` → ServiceRequest / Procedure
- `EmergencyTriage` / `EmergencyVitals` / `EmergencyOrder` / `EmergencyMedication` → Extensions on Encounter
- `BloodInventory` / `BloodRequest` / `BloodTransaction` → SupplyRequest / custom
- `Invoice` / `Payment` / `InsuranceClaim` → Account / Coverage / Claim
- `AI Scribe models` → DocumentReference (AI-generated, draft status)

---

## Existing Security & Isolation (Reusable for Interoperability)

### Hospital Isolation
- **Mechanism:** `HospitalScopedViewSet` base class auto-filters by user's hospital memberships
- **Enforcement:** `HospitalIsolationPermission` object-level checks
- **Coverage:** All models with `hospital` FK or patient/visit relationships

### RBAC
- **Roles:** Admin, Doctor, Nurse, Lab Staff, Blood Bank Staff, Pharmacist, Receptionist, Billing Staff, Inventory Staff, Hospital Manager
- **Permission Matrix:** Defined in `RoleBasedPermission.ROLE_PERMISSIONS`
- **Object-level:** `IsOwnerOrHospitalAdmin`, `ReadOnlyOrHospitalAdmin`

### Audit Logging
- **Model:** `AuditLog` (action, model_name, object_id, details, user, timestamp)
- **AI Interactions:** Separate `AIInteraction` model with review tracking

### Consent
- **Model:** `Consent` in notifications app (patient, purpose, granted, timestamp)
- **Status:** Basic implementation, needs enhancement for interoperability consent directives

---

## API Surface Analysis

### Current API Endpoints (via router)
```
/api/patients/
/api/patient-hospitals/
/api/doctors/
/api/appointments/
/api/nurses/
/api/compounder/
/api/pharmacy/
/api/pharmacy-sales/
/api/laboratory/
/api/home/
/api/hospital/
/api/encounters/
/api/clinical/
/api/ipd/
/api/emergency/
/api/billing/
/api/bloodbank/
/api/notifications/
/api/audit/
/api/procurement/
/api/auth/
```

### Authentication
- JWT (access 15min, refresh 7d, rotation + blacklist)
- Google OAuth integration
- Staff login required for all API endpoints

---

## Interoperability Gaps (Phase 0 Findings)

| Requirement | Current Status | Gap |
|---|---|---|
| FHIR R4 Resources | Not implemented | Complete implementation needed |
| FHIR REST API | Not implemented | Need `/fhir/` endpoint namespace |
| FHIR Validation | Not implemented | Need validation layer |
| HL7 v2 Parsing/Generation | Not implemented | Need HL7 engine |
| ABDM/ABHA Integration | Not implemented | Need HIP/HIU/HIE adapters |
| ABHA ID Management | Not implemented | Need ABHA linking on Patient |
| Consent for Data Sharing | Basic model exists | Need FHIR Consent + policy enforcement |
| Provenance/Audit Trail | Basic AuditLog exists | Need FHIR Provenance mapping |
| Bundle Support | Not implemented | Need Bundle generation/parsing |
| Search/Filter (FHIR spec) | DRF filtering only | Need FHIR search parameters |
| Terminology Binding | Not implemented | Need CodeSystem/ValueSet support |
| SMART on FHIR / OAuth2 | Not implemented | Need authorization server |

---

## Implementation Strategy

### Phase 1: FHIR R4 Mapping Layer (Priority: HIGH)
Create `interoperability/fhir/` app with:
- `resources/` - FHIR resource builders (not serializers - separate from internal models)
- `mappings/` - Internal model → FHIR resource transformers
- `serializers/` - FHIR JSON output serializers
- `validators/` - FHIR structure validation
- `views/` - FHIR REST API endpoints (`/fhir/Patient`, `/fhir/Observation`, etc.)
- `urls.py` - FHIR routing

### Phase 2: FHIR Validation (Priority: HIGH)
- Integrate `fhir.resources` (Python FHIR library) for validation
- Validate on generate and on ingest

### Phase 3: HL7 v2 (Priority: MEDIUM)
- Create `interoperability/hl7/` app
- ADT, ORM, ORU message support
- MLLP transport option

### Phase 4: ABDM/ABHA (Priority: MEDIUM)
- Create `interoperability/abdm/` app
- ABHA ID linking on Patient
- HIP/HIU/HIE gateway adapters
- Consent artifact management

### Phase 5: Secure APIs (Priority: HIGH)
- Extend permission system for FHIR endpoints
- Audit all FHIR read/write operations
- Rate limiting per external system

### Phase 6: Import/Export (Priority: MEDIUM)
- FHIR Bundle import (transaction/history)
- FHIR Bundle export (document/collection)
- HL7 batch processing

### Phase 7: Tests (Priority: HIGH)
- Unit tests for each mapper
- Integration tests for FHIR endpoints
- Validation tests
- Round-trip tests

### Phase 8: Documentation (Priority: MEDIUM)
- FHIR Implementation Guide (CapabilityStatement)
- API documentation (OpenAPI/Swagger)
- Mapping documentation
- ABDM integration guide

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Breaking existing APIs | Low | High | New `/fhir/` namespace, no changes to `/api/` |
| Hospital isolation bypass | Medium | Critical | Reuse `HospitalScopedViewSet` + `HospitalIsolationPermission` |
| Data leakage via FHIR | Medium | Critical | Server-side hospital scoping, consent enforcement |
| Performance on large bundles | Medium | High | Pagination, streaming, async processing |
| FHIR validation false negatives | Medium | Medium | Use battle-tested `fhir.resources` library |

---

## Next Steps

1. ✅ **Phase 0 Complete** - Audit documented
2. **Phase 1** - Create `interoperability` app structure and implement core FHIR mappers
3. **Phase 2** - Add validation layer
4. **Phase 3-8** - Continue per roadmap

---

## Appendix: Key Files Referenced

- `backend/config/settings.py` - Django settings
- `backend/config/urls.py` - Main URL routing
- `backend/hospital/permissions.py` - Permission classes
- `backend/users/viewsets.py` - HospitalScopedViewSet
- `backend/patients/models.py` - Patient, PatientHospital
- `backend/doctors/models.py` - Doctor
- `backend/hospital/models.py` - Hospital, Department, Ward, Room, Bed
- `backend/encounters/models.py` - Visit, QueueToken
- `backend/clinical/models.py` - VitalSign, Allergy, ClinicalNote, Diagnosis, Prescription, PrescriptionItem
- `backend/ipd/models.py` - Admission, DischargeSummary
- `backend/emergency/models.py` - EmergencyVisit, EmergencyTriage
- `backend/laboratory/models.py` - LabTest, LabResult
- `backend/pharmacy/models.py` - Medicine, Sale
- `backend/billing/models.py` - Invoice, Payment, InsuranceClaim
- `backend/bloodbank/models.py` - BloodInventory, BloodRequest
- `backend/notifications/models.py` - Consent
- `backend/audit/models.py` - AuditLog, AIInteraction
- `backend/ai_scribe/models.py` - AI consultation models
- `backend/procurement/models.py` - Supply chain models