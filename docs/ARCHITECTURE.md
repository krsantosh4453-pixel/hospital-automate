# Hospital Management System — Architecture Documentation

This document describes the actual architecture of the Hospital Management System as implemented in the repository.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND (React)                                 │
│  ┌──────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
│  │  Pages   │  │ Components  │  │ Contexts │  │ API Svc   │  │ Router   │  │
│  └──────────┘  └─────────────┘  └──────────┘  └───────────┘  └──────────┘  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ HTTPS / REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACKEND (Django + DRF)                             │
│  ┌────────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │  ViewSets  │  │Serializers│  │Permissions│  │ Auth     │  │  Models  │  │
│  └────────────┘  └──────────┘  └───────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ ORM
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE (PostgreSQL/SQLite)                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Technology Stack
- **React 19** — UI library
- **Vite** — Build tool and dev server
- **React Router v7** — Client-side routing
- **Tailwind CSS 4** — Utility-first styling
- **Context API** — State management (no Redux/Zustand)

### Key Directories
```
src/
├── pages/              # Page-level components (one per route)
├── components/         # Reusable UI components
├── services/           # API service layer (api.js)
├── assets/context/     # React Context providers
├── layouts/            # Layout wrappers (Layout, PatientLayout)
└── utils/              # Utility functions
```

### React Context Providers (in `src/assets/context/`)
| Context | Purpose |
|---------|---------|
| `AuthContext` | JWT token management, login/logout, token refresh |
| `RoleContext` | Role definitions, permissions, active role switching |
| `PatientContext` | Current patient data for patient portal |
| `PrescriptionContext` | Prescription state during consultation |
| `PharmacyContext` | Pharmacy/cart state |
| `HospitalsContext` | Hospital selection and list |
| `SidebarContext` | Sidebar open/close state |
| `RoleAuthBridge` | Syncs backend roles to frontend |

### Routing Structure (`src/App.jsx`)
- **Staff routes** (`/`) — Protected by `ProtectedRoute audience="staff"`
  - Dashboard, Patients, Appointments, Queue, Consultation, Prescription
  - Doctors, Nurses, Compounder, Pharmacy, Laboratory, Billing
  - Inventory, Reports, Emergency, Blood Bank, IPD, AI Scribe
  - Admin: Dashboard, Users, Roles, Hospitals, Departments, Permissions
  - Settings, Hospital Selection
- **Patient routes** (`/patient/*`) — Protected by `ProtectedRoute audience="patient"`
  - Dashboard, Appointments, Queue, Prescriptions, Lab Results, Bills, Documents, Consent

### API Service Layer (`src/services/api.js`)
- Base URL: `import.meta.env.VITE_API_BASE_URL || '/api'`
- Automatic JWT attachment via `Authorization: Bearer <access_token>`
- Automatic token refresh on 401 (except for auth endpoints)
- Timeout: 8 seconds
- Error parsing with `parseErrorDetail()`

---

## Backend Architecture

### Technology Stack
- **Django 5.2** — Web framework
- **Django REST Framework 3.15** — API framework
- **djangorestframework-simplejwt** — JWT authentication
- **django-cors-headers** — CORS handling
- **PostgreSQL** (production) / **SQLite** (development)

### Project Structure
```
backend/
├── config/             # Project settings, URLs, health, schema
├── users/              # Authentication, authorization, staff/patient
├── patients/           # Patient management
├── doctors/            # Doctor management
├── appointments/       # Appointment scheduling
├── nurses/             # Nursing: assessments, notes, MAR, care tasks
├── pharmacy/           # Medicine inventory, sales
├── laboratory/         # Lab tests, samples, results, dispatch
├── clinical/           # Clinical notes, prescriptions, diagnoses, procedures
├── encounters/         # Visits, queue tokens, doctor schedules
├── hospital/           # Hospital, department, ward, room, bed
├── billing/            # Invoices, payments, insurance claims
├── bloodbank/          # Blood inventory, requests, transactions
├── ipd/                # Admissions, bed allocations, discharge
├── emergency/          # Emergency visits, triage, orders, medications
├── procurement/        # Suppliers, purchase orders, GRN, stock transactions
├── ai_scribe/          # AI Medical Scribe (STT + LLM)
├── audit/              # Audit logging
├── notifications/      # Notification system
├── reports/            # Reports (stubbed)
├── fhir/               # FHIR (UNMOUNTED)
├── hl7/                # HL7 (UNMOUNTED)
├── abdm/               # ABDM/ABHA (UNMOUNTED)
├── consent/            # Consent (UNMOUNTED)
├── documents/          # Documents (UNMOUNTED)
└── interoperability/   # Interoperability utilities
```

### Core Patterns

#### ViewSets
- Base: `HospitalScopedViewSet` (filters queryset by user's hospital membership)
- Permissions: Role-based permission classes from `users.permissions`
- Serializers: Separate list/detail serializers where needed

#### Hospital Scoping
All hospital-scoped models include `hospital = ForeignKey(Hospital)` and are filtered by `HospitalScopedViewSet` using the user's active `StaffHospitalMembership`.

#### Serializers
- Use `ModelSerializer` with explicit fields
- Nested serializers for relationships
- Custom validation in `validate()` methods

#### Permissions (`users/permissions.py`)
- `IsStaffUser` — Authenticated staff with active profile
- `IsHospitalMember` — Staff member of requested hospital
- `RoleBasedPermission` — Base class for role-specific permissions
  - `IsAdmin`, `IsDoctor`, `IsNurse`, `IsReceptionist`, `IsPharmacist`
  - `IsLabStaff`, `IsBillingStaff`, `IsInventoryStaff`, `IsBloodBankStaff`
  - `IsHospitalManager`, `IsClinicalStaff`, `IsAdminOrManager`
- Object-level: `IsOwnerOrHospitalAdmin`, `IsHospitalScoped`
- Patient: `IsLinkedPatient`, `IsPatientReadOnly`

---

## Database Architecture

### Development Database
- **SQLite** (`backend/db.sqlite3`) — File-based, zero-config
- Used for local development and testing
- Migrations applied via `python manage.py migrate`

### Production Database
- **PostgreSQL 15+** — Configured via `DATABASE_URL` environment variable
- Connection pooling via `psycopg2-binary`
- Migrations managed in CI/CD pipeline

### Major Entity Relationships

```
Hospital (1) ──────< (N) StaffHospitalMembership >────── (1) StaffProfile
    │
    ├─< (N) Patient (direct FK) 
    │   └─< (N) PatientHospital (membership)
    │
    ├─< (N) Doctor
    ├─< (N) Nurse
    ├─< (N) Department
    ├─< (N) Ward ──< (N) Room ──< (N) Bed
    ├─< (N) Appointment
    ├─< (N) Visit
    ├─< (N) QueueToken
    ├─< (N) Prescription
    ├─< (N) Invoice
    ├─< (N) BloodInventory
    ├─< (N) BloodRequest
    ├─< (N) EmergencyVisit
    ├─< (N) Admission
    ├─< (N) Supplier
    ├─< (N) PurchaseOrder
    └─< (N) Medicine

Patient (1) ──< (N) Appointment
Patient (1) ──< (N) Visit
Patient (1) ──< (N) Prescription
Patient (1) ──< (N) Invoice
Patient (1) ──< (N) Admission
Patient (1) ──< (N) EmergencyVisit
Patient (1) ──< (N) LabTest
Patient (1) ──< (N) BloodRequest

Visit (1) ──< (N) VitalSign
Visit (1) ──< (N) ClinicalNote
Visit (1) ──< (N) Diagnosis
Visit (1) ──< (N) ServiceOrder
Visit (1) ──< (N) Procedure
Visit (1) ──< (N) Prescription
Visit (1) ──< (N) LabTest
Visit (1) ──< (N) QueueToken

Prescription (1) ──< (N) PrescriptionItem
Prescription (1) ──< (N) MAR
Prescription (1) ──< (N) Sale (pharmacy)

Admission (1) ──< (N) BedAllocation
Admission (1) ──< (1) DischargePlan
Admission (1) ──< (1) DischargeSummary
Admission (1) ──< (N) DischargeNote
Admission (1) ──< (N) NursingAssessment
Admission (1) ──< (N) NursingNote
Admission (1) ──< (N) CareTask
Admission (1) ──< (N) MAR
Admission (1) ──< (N) PatientAssignment
```

### Key Indexes (Verified from Models)
- Most FK fields have `db_index=True`
- Composite indexes on `(hospital, status)`, `(hospital, created_at)`, `(hospital, date)`
- Unique constraints on `QueueToken(hospital, token_date, token_number)`, `Supplier(hospital, name)`, `PurchaseOrder(hospital, reference)`, `GoodsReceipt(hospital, reference)`

---

## Authentication Architecture

### Staff Authentication
1. **Login**: `POST /api/auth/staff/login/` with username/password
2. **Response**: JWT access + refresh tokens, user object, roles array, hospitals array
3. **Token Storage**: localStorage (access_token, refresh_token)
4. **Access Token**: Short-lived (configurable via SIMPLE_JWT)
5. **Refresh Token**: Long-lived, used to obtain new access token
6. **Auto-refresh**: Frontend intercepts 401, calls `/api/auth/token/refresh/`, retries request

### Patient Authentication
1. **OTP Request**: `POST /api/auth/patient/otp/request/` with phone
2. **OTP Verify**: `POST /api/auth/patient/otp/verify/` with phone + OTP
3. **Email OTP**: Alternative flow via `/api/auth/patient/email-otp/`
3. **Login**: `POST /api/auth/patient/login/` or `/api/auth/patient/token/`
4. **Session**: JWT tokens same as staff, but linked to `Patient` via `user.patient_account`

### Registration
- `POST /api/auth/register/` — Creates User + Patient (if patient registration)
- Staff accounts created via admin or Users management

### Google OAuth
- `POST /api/auth/google/` — Exchanges Google ID token for JWT

### Token Endpoints (DRF SimpleJWT)
- `POST /api/auth/token/` — Obtain pair (username/password)
- `POST /api/auth/token/refresh/` — Refresh access token
- `POST /api/auth/token/verify/` — Verify token validity

---

## Authorization Architecture

### Backend Enforcement (Source of Truth)
All authorization decisions are made in **backend permission classes** (`users/permissions.py`):

1. **Authentication** — `IsAuthenticated` (JWT valid)
2. **Staff Check** — `IsStaffUser` (has StaffProfile, is_active_staff)
3. **Hospital Membership** — `IsHospitalMember` (active membership in requested hospital)
4. **Role Check** — `RoleBasedPermission` subclasses (IsDoctor, IsNurse, etc.)
5. **Object-Level** — `IsOwnerOrHospitalAdmin`, `IsHospitalScoped`

### Frontend Role Visibility (UI Only — NOT Security)
Frontend uses `RoleContext` (`src/assets/context/RoleContext.jsx`) to control **visibility only**:

- `DEFAULT_ROLES` defines 6 roles: Admin, Doctor, Nurse, Compounder, Receptionist, Patient
- Each role has `permissions[module] = ["View", "Add", "Edit", "Delete"]`
- `canView(module)`, `canAdd(module)`, etc. used in Sidebar and page components
- **Critical**: Frontend hiding ≠ security. Backend permissions enforce actual access.

### Role Mapping (Backend ↔ Frontend)
| Backend Role (StaffRole) | Frontend Role | Notes |
|--------------------------|---------------|-------|
| ADMIN | Admin | Full access |
| DOCTOR | Doctor | Clinical workflows |
| NURSE | Nurse | Vitals, MAR, assessments |
| COMPOUNDER | Compounder | Pharmacy dispensing |
| RECEPTIONIST | Receptionist | Registration, appointments, queue |
| PHARMACIST | (mapped to Compounder) | Frontend uses "Compounder" |
| LAB_STAFF | (no dedicated frontend role) | Uses Laboratory module |
| BILLING_STAFF | (no dedicated frontend role) | Uses Billing module |
| INVENTORY_STAFF | (no dedicated frontend role) | Uses Inventory module |
| BLOOD_BANK_STAFF | (no dedicated frontend role) | Uses Blood Bank module |
| HOSPITAL_MANAGER | Admin (falls back) | No dedicated frontend role |

---

## Deployment Architecture (Stage 7 — ACTUAL)

### Container Structure
```
┌─────────────────────────────────────────────────────────────────┐
│                        DOCKER COMPOSE                           │
├──────────────┬──────────────┬──────────────┬──────────────────┤
│   nginx      │   backend    │   frontend   │   postgres       │
│  (reverse    │  (gunicorn)  │  (nginx +    │   (database)     │
│   proxy)     │  + celery    │   static)    │                  │
└──────────────┴──────────────┴──────────────┴──────────────────┘
```

### Services (from `docker-compose.prod.yml`)

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `nginx` | `nginx:alpine` | 80/443 | Reverse proxy, SSL termination, static files |
| `backend` | Built from `Dockerfile` | 8000 | Gunicorn + Django, Celery worker, Celery beat |
| `frontend` | Built from `Dockerfile.frontend` | 3000 | Nginx serving React build |
| `postgres` | `postgres:15-alpine` | 5432 | Primary database |
| `redis` | `redis:7-alpine` | 6379 | Cache, Celery broker, sessions |

### Network & Volumes
- All services on `hms-network` bridge network
- Named volumes: `postgres_data`, `redis_data`, `media_files`, `static_files`, `backend_logs`

### SSL/TLS
- Nginx terminates SSL (Let's Encrypt or self-signed)
- Certificates mounted at `/etc/nginx/certs/`
- HTTP → HTTPS redirect enforced

### Health Checks
- `GET /health/` — Liveness
- `GET /health/ready/` — Readiness (DB, Redis, migrations)
- `GET /health/live/` — Liveness probe

### Environment Configuration
- `.env.production` → `docker-compose.prod.yml` via `env_file`
- Secrets: `SECRET_KEY`, `DB_PASSWORD`, `REDIS_PASSWORD`, `JWT_SECRET`
- See [Environment](ENVIRONMENT.md) for full variable list

---

## Component Status Legend

| Status | Meaning |
|--------|---------|
| **ACTIVE** | Fully implemented, mounted, tested |
| **PARTIAL** | Partially implemented, some endpoints/models missing |
| **MOCK** | Uses mock/demo data, not production-ready |
| **UNMOUNTED** | Code exists but not included in URL routing |
| **STUB** | Minimal implementation, placeholder only |
| **PLANNED** | Designed but not implemented |
| **BROKEN** | Known non-functional |
| **NOT VERIFIED** | Status unknown, needs investigation |

---

## Module Status Summary

| Module | Frontend | Backend | API | Database | Status |
|--------|----------|---------|-----|----------|--------|
| Authentication | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Patients | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Doctors | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Appointments | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Nurses | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Compounder | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Pharmacy | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Laboratory | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Clinical | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Encounters/Visits | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Queue | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Hospital/Dept/Ward/Bed | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Billing | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Blood Bank | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| IPD/Admissions | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Emergency | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| Procurement | ✅ | ✅ | ✅ | ✅ | ACTIVE |
| AI Scribe | ✅ | ✅ | ✅ | ✅ | **MOCK** (STT/LLM use dev providers) |
| Reports | ✅ (UI) | ⚠️ | ⚠️ | ❌ | **PARTIAL / STUB** |
| Notifications | ❌ | ✅ | ✅ | ✅ | **BACKEND ONLY** |
| Audit | ❌ | ✅ | ✅ | ✅ | **BACKEND ONLY** |
| FHIR | ❌ | ❌ | ❌ | ❌ | **UNMOUNTED** |
| HL7 | ❌ | ❌ | ❌ | ❌ | **UNMOUNTED** |
| ABDM | ❌ | ❌ | ❌ | ❌ | **UNMOUNTED** |
| Consent | ✅ (UI) | ❌ | ❌ | ❌ | **UI ONLY / UNMOUNTED** |
| Documents | ✅ (UI) | ✅ (model) | ❌ | ✅ | **UNMOUNTED** |

See [Module Status](MODULE_STATUS.md) for detailed matrix.

---

## Known Architecture Limitations

1. **No API Gateway** — Direct nginx → backend routing
2. **No Service Mesh** — Monolithic Django app, not microservices
3. **Single Database** — No read replicas configured
4. **Celery + Redis** — Single Redis instance (no sentinel/cluster)
5. **Frontend Role Hiding** — Not a security boundary
6. **AI Scribe Mock Providers** — Development STT/LLM providers active by default
7. **Reports Module** — Backend stubbed, no real report generation
8. **FHIR/HL7/ABDM** — Apps exist but completely unmounted
9. **No Rate Limiting** — Not configured in DRF
10. **No WebSocket** — Real-time updates not implemented (polling only)