# PHASE 2 STARTING STATE REPORT

## Executive Summary

**Phase 1 Status: PARTIALLY COMPLETE**

Phase 1 security & multi-hospital foundation has significant gaps that must be addressed before/during Phase 2.

---

## Phase 1 Verification Results

### ✅ What IS Working

| Area | Status | Details |
|------|--------|---------|
| JWT Authentication | ✅ | SimpleJWT configured in settings, `JWTAuthentication` used in some views |
| Hospital Model | ✅ | `Hospital` model exists with `is_active` flag |
| Patient-Hospital Membership | ✅ | `PatientHospital` model with `unique_together` on (patient, hospital) |
| Hospital FK on Core Models | ✅ | `Doctor`, `Department`, `Ward`, `Room`, `Bed`, `Nurse`, `Visit`, `QueueToken`, `VitalSign`, `ClinicalNote`, `Diagnosis`, `ServiceOrder`, `Prescription`, `Invoice` all have `hospital` FK |
| API Filtering by Hospital | ✅ | Most ViewSets filter via `?hospital=` query param |
| CORS | ✅ | Configured for frontend origins |

### ❌ What IS BROKEN / MISSING

| Area | Issue | Severity |
|------|-------|----------|
| **BloodInventory** | **NO hospital FK** - completely unscoped | **CRITICAL** |
| **BloodRequest** | **NO hospital FK** - completely unscoped | **CRITICAL** |
| **BloodTransaction** | **NO hospital FK** - completely unscoped | **CRITICAL** |
| **LabTest model** | No hospital FK (only filtered in view via patient) | HIGH |
| **EmergencyVisit** | Has hospital FK but no hospital filtering in ViewSet | HIGH |
| **IPD Models** | Admission has hospital FK but BedAllocation/Discharge* rely on Admission only | MEDIUM |
| **Object-level permissions** | None implemented - any authenticated user can access any object | **CRITICAL** |
| **RBAC** | Only `IsAuthenticated` - no role-based access control | **CRITICAL** |
| **Hospital isolation enforcement** | Relies on `?hospital=` param - can be bypassed | **CRITICAL** |
| **Auto hospital context** | No middleware/permission to auto-scope to user's hospital | HIGH |
| **Audit logging** | Audit app exists but models not integrated | MEDIUM |

### 🔴 Critical Security Gaps

1. **Blood Bank completely unscoped** - Hospital A can see/edit Hospital B's blood inventory
2. **No object permissions** - User from Hospital A can PATCH/DELETE Hospital B's patients, admissions, etc.
3. **No RBAC** - Nurse can access Doctor/Admin endpoints, no role checks
4. **Query param trust** - Frontend sends `?hospital=`; backend trusts it without verifying user membership

---

## Existing Backend Models (Summary)

### IPD (`backend/ipd/models.py`)
- `Admission` - patient, hospital, status, dates, reason
- `BedAllocation` - admission, bed, allocated_at, released_at
- `DischargePlan` - admission, instructions, pending_tasks
- `DischargeSummary` - admission, summary, authorized_doctor, finalized
- `DischargeNote` - admission, note

### Emergency (`backend/emergency/models.py`)
- `EmergencyVisit` - patient, hospital, visit_number, triage_level, status, arrival/discharge times

### Laboratory (`backend/laboratory/models.py`)
- `LabTest` - name, patient, doctor (CharField), priority, result, status, test_date
  - **Missing**: hospital FK, sample workflow models (SampleCollection, SampleDispatch, LabResult, ResultVerification)

### Blood Bank (`backend/bloodbank/models.py`)
- `BloodInventory` - blood_group, component, units, expiry_date → **NO hospital FK**
- `BloodRequest` - patient, blood_group, component, units, status → **NO hospital FK**
- `BloodTransaction` - request, transaction_type, units, remarks → **NO hospital FK**

### Nurses (`backend/nurses/models.py`)
- `Nurse` - hospital (nullable), name, phone, email, department, shift, qualification, joining_date, status
  - **Missing**: NursingAssessment, VitalSign (clinical has but not nurse-specific), MAR, CareTask, NursingNote

### Hospital (`backend/hospital/models.py`)
- `Hospital`, `Department`, `Ward`, `Room`, `Bed` - all properly scoped

### Clinical/Encounters (`backend/clinical/models.py`, `backend/encounters/models.py`)
- `Visit`, `QueueToken`, `VitalSign`, `ClinicalNote`, `Diagnosis`, `ServiceOrder`, `Procedure`, `Prescription`, `PrescriptionItem`, `MedicalRecord`, `Allergy`

### Billing (`backend/billing/models.py`)
- `Invoice`, `InvoiceItem`, `Payment`, `InsuranceClaim` - all have hospital FK

---

## Existing APIs (ViewSets)

All modules have basic `ModelViewSet` CRUD:
- `/api/ipd/admissions/`, `/api/ipd/bed-allocations/`, `/api/ipd/discharge-plans/`, `/api/ipd/discharge-summaries/`, `/api/ipd/discharge-notes/`
- `/api/emergency/emergency-visits/`
- `/api/laboratory/` (LabTest only)
- `/api/bloodbank/inventory/`, `/api/bloodbank/requests/`, `/api/bloodbank/transactions/`
- `/api/nurses/nurses/`
- `/api/clinical/vitals/`, `/api/clinical/clinical-notes/`, `/api/clinical/diagnoses/`, `/api/clinical/service-orders/`, `/api/clinical/prescriptions/`
- `/api/encounters/visits/`, `/api/encounters/queue-tokens/`
- `/api/billing/` (invoices, payments, claims)
- `/api/hospital/` (hospitals, departments, wards, rooms, beds)

**Missing Custom Actions:**
- Bed allocation with availability check + atomic transaction
- Discharge workflow (plan → summary → bed release)
- Emergency triage → registration → vitals → orders → admission/discharge/referral
- Lab sample workflow (collect → dispatch → process → verify → release)
- Blood request → approval → issue → inventory update
- MAR administration workflow

---

## Existing Frontend Pages

| Page | File | Status |
|------|------|--------|
| Laboratory | `src/pages/laboratory.jsx` | ✅ Basic CRUD, uses real API |
| Nurses | `src/pages/Nurses.jsx` | ⚠️ Mixed - uses API for nurses/patients/blood/ipd but **mock data** for vitals, assessments, MAR, orders, notes, billing |
| Patients | `src/pages/Patients.jsx` | ✅ Basic CRUD |
| Appointments | `src/pages/Appointments.jsx` | ✅ |
| Queue | `src/pages/Queue.jsx` | ✅ |
| Consultation | `src/pages/Consultation.jsx` | ✅ |
| Pharmacy | `src/pages/pharmacy.jsx` | ✅ |
| Billing | `src/pages/billing.jsx` | ✅ |
| Inventory | `src/pages/inventory.jsx` | ✅ |
| Dashboard | `src/pages/Dashboard.jsx` | ✅ |
| **IPD** | — | ❌ **MISSING** |
| **Emergency/ER** | — | ❌ **MISSING** |
| **Blood Bank** | — | ❌ **MISSING** (API exists in api.js) |

---

## Existing Migrations

All apps have initial migrations applied. Recent additions:
- `laboratory/migrations/0002_labtest_doctor_labtest_priority_alter_labtest_status.py`
- `nurses/migrations/0002_nurse_email_nurse_hospital_nurse_joining_date_and_more.py`
- `procurement/migrations/0001_initial.py`

---

## Existing Tests

| App | Test Coverage |
|-----|---------------|
| pharmacy | ✅ 9 tests (CRUD, hospital filtering, stock deduction, cross-hospital rejection) |
| procurement | ✅ Extensive tests |
| **All other apps** | ❌ Empty `TestCase` stubs only |

---

## Phase 2 Implementation Plan

### Priority Order (P1 = Must Complete)

| Priority | Module | Key Work |
|----------|--------|----------|
| **P1** | **IPD** | Bed allocation (atomic), discharge workflow, hospital isolation, RBAC |
| **P1** | **Emergency** | Complete ER workflow, hospital isolation, status transitions |
| **P1** | **Laboratory** | Sample workflow models + APIs, status flow, hospital isolation |
| **P1** | **Blood Bank** | **Add hospital FK to all models**, workflow (request→approve→issue→update), audit |
| **P1** | **Nursing + MAR** | Nursing workflow models, MAR (Medication Administration Record), safety validations |

### Cross-Cutting Concerns (Apply to ALL modules)

1. **Add hospital FK** where missing (BloodInventory, BloodRequest, BloodTransaction, LabTest)
2. **Implement HospitalIsolationPermission** - deny access to objects not in user's hospital(s)
3. **Implement RBAC** - role-based permissions (Admin, Doctor, Nurse, LabTech, BloodBankStaff, etc.)
4. **Auto-hospital context** - middleware/permission to inject hospital from user membership
5. **Atomic transactions** - bed allocation, blood issue, discharge
6. **Audit logging** - sensitive operations (discharge, blood issue, MAR administration)
7. **Status transition validation** - prevent invalid state changes
8. **Frontend integration** - replace mock data with real API calls, error/loading states

---

## Next Steps

1. **Immediate**: Fix Blood Bank models (add hospital FK + migrations)
2. **Immediate**: Add hospital FK to LabTest model
3. **Immediate**: Create base permission classes for hospital isolation + RBAC
4. **Then**: Implement each P1 module backend → API → frontend → tests
5. **Finally**: Cross-module integration testing (Workflows A-G)