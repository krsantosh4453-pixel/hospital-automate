# Hospital Management System — Architecture

This describes the system as implemented on branch `audit/production-readiness-2026-10-24` (2026-10-25). For module status see `REQUIREMENTS_TRACEABILITY.md`; for the API see `API_DOCUMENTATION.md`.

## Overview

```
Browser (React SPA) ──HTTPS──> nginx ──┬─ /           static build (frontend container)
                                       ├─ /api/       Django + DRF (gunicorn)
                                       ├─ /health/    Django health checks
                                       └─ /media/     404: files only via the audited API
Django ── PostgreSQL 16 (data) ── Redis (cache, Celery broker) ── Celery worker + beat
Django ── external (optional): Twilio Verify/SMS, email, STT/LLM providers, Google sign-in
```

Every staff request acts in **one hospital** (see "Tenancy"). Patients authenticate separately and see only their own records.

## Frontend (`src/`)

- **Stack:** React 19, Vite 8, React Router 7, Tailwind 4, Context API.
- **Directories:**
  - `pages/` — one component per route
  - `components/` — Navbar, Sidebar, …
  - `layouts/` — staff Layout, PatientLayout
  - `assets/context/` — providers
  - `services/api.js` — the only HTTP client
  - `utils/roleRouting.js`

### Context providers

| Context | Purpose |
|---|---|
| `LanguageContext` | English/Hindi interface text (`t()`), stored in `localStorage` as `hms_language`; sets `<html lang>` |
| `AuthContext` | Staff/patient session, token storage, login flows; dev bypass only in development builds |
| `HospitalsContext` | Hospitals from the API only (staff: memberships; patients: `/api/hospital/directory/`) |
| `PatientContext` | Selected hospital (`localStorage.selectedHospital`) and patient state |
| `RoleContext` / `RoleAuthBridge` | Which menu items a role sees. UI only; the server enforces access. |
| `PrescriptionContext`, `PharmacyContext` | API-backed lists; writes succeed only when the server accepts them |
| `SidebarContext` | Sidebar open or closed |

### API client (`services/api.js`)

- Base URL `VITE_API_BASE_URL || '/api'`.
- Attaches `Authorization: Bearer …` and `X-Hospital-ID` (the selected hospital).
- Refreshes the token once on 401.
- 8-second timeout.
- Errors show the server's `message`.
- `backend/security_tests/test_frontend_contract.py` fails if any client URL has no backend route.

### Routing

- **Staff routes:** `ProtectedRoute audience="staff"` plus a backend-role check.
- **Patient routes:** under `/patient/*`.
- **Production builds:** always require login.

## Backend (`backend/`)

- **Stack:** Django 6.0, DRF 3.18, SimpleJWT, django-cors-headers, drf-spectacular, Celery 5 with django-celery-beat. Exact versions are in `requirements-lock.txt`.
- **Apps:**
  - `users` — auth, permissions, staff admin, scoped base viewsets
  - `patients`, `doctors`, `appointments`
  - `encounters` — visits, queue tokens, schedules
  - `clinical` — vitals, allergies, notes, diagnoses, orders, procedures, prescriptions
  - `laboratory`, `pharmacy`, `procurement`
  - `nurses` — assessments, notes, care tasks, MAR
  - `ipd`, `emergency`, `billing`, `bloodbank`
  - `notifications` — engine, consent, delivery log
  - `consent` — forms, record sharing
  - `documents` — file API
  - `ai_scribe`
  - `audit`
  - `reports` — KPIs, forecasts
  - `hospital` — hospital, department, ward, room, bed
- **Not mounted:** `fhir`, `hl7`, `abdm` (code present; no URLs).

### Tenancy (`users/viewsets.py`)

- `HospitalScopedViewSet` and `ReadOnlyHospitalScopedViewSet` resolve each model's path to its owning hospital (`resolve_hospital_lookup`). They never route through the shared Patient identity, and filter to the user's active memberships, narrowed to the acting hospital.
- Scoping **fails closed:** a model with no path returns nothing.
- Writes run `_check_tenancy`: the record's own hospital must be one of the user's, every related object must belong to the same hospital, and any patient must be registered there.
- The acting hospital comes from `?hospital=`, a body `hospital` field, or the `X-Hospital-ID` header (`users/permissions.get_request_hospital_id`). Malformed values return 400.

### Authorization (`users/permissions.py`)

- Roles come from `StaffHospitalMembership.role` in the acting hospital (`get_user_roles(user, hospital_id)`). The `StaffProfile.role` field is only a display default.
- Role classes (`IsDoctor`, `IsNurse`, …) check the role in the acting hospital and, per object, in the object's owning hospital.
- `IsPatientReadOnly` lets a linked patient read their own rows, further filtered per resource (for example, only released lab results).
- Platform superusers alone create or delete hospitals and see OTP rows. There is no cross-hospital superuser data access through the scoped APIs.

### Domain services

- `billing/services.py`: Decimal totals, locked and idempotent payments, refunds.
- `audit/services.record_audit`: never raises; redacts secrets.
- `notifications/services/engine.py`: consent check (latest answer per hospital and purpose), providers, a durable `NotificationDelivery` row per attempt.
- `ai_scribe/services/{stt,llm}.py`: provider abstraction. Mock providers load only when `AI_SCRIBE_ALLOW_MOCK_PROVIDERS` is set. Extraction is coerced to a fixed schema.
- `reports/services.KPIService`: hospital-scoped KPIs.

### Clinical safety rules (enforced server-side)

- AI drafts are labelled "AI Draft — Pending Review". Workflow fields are read-only, approval needs the signed-in user's Doctor profile at that hospital, and approving creates the clinical note. Mock-provider drafts cannot be approved where mocks are disallowed.
- Recording needs the patient's consent first.
- Discharge summaries are finalized only by a linked doctor and are immutable afterwards. Discharge can't complete without a finalized summary.
- Lab results move only through lab-staff actions; patients see Released results only.
- MAR doses start as Scheduled; every outcome records who and when.
- Every write is audited with previous values.

### Background jobs

- `config/celery.py`.
- Beat schedule: `notifications.tasks.cleanup_expired_otp` (hourly) and `audit.tasks.cleanup_old_audit_logs` (daily; only when `AUDIT_LOG_RETENTION_DAYS > 0`).
- The queue-token notification path calls the engine synchronously and never fails the request.

## Authentication

- **Staff:**
  - password sign-in, with lockout after 5 failures for 15 minutes;
  - SMS OTP via Twilio Verify, with a signed challenge from the password step (mandatory in production via `STAFF_LOGIN_REQUIRE_OTP`);
  - OTP password reset that revokes refresh tokens.
- **Patients:** mobile OTP, email OTP, verified-email password, or Google.
- **Tokens:** JWT access 15 minutes and refresh 7 days (rotated, blacklisted on logout); RS256 in production. Tokens are kept in `localStorage` (see `SECURITY_AUDIT.md`, open item).

## Deployment

`docker-compose.prod.yml` runs:

- `postgres:16-alpine` and `redis`;
- `backend` (gunicorn; migrates when `RUN_MIGRATIONS=true`), `celery-worker` and `celery-beat` — all three share the `x-django-service` anchor and `.env.production`;
- `frontend` (static build);
- `nginx` (TLS, rate limits, private media, per-location proxying).

Health checks: `/health/live/` and `/health/ready/` (database and cache). See `DEPLOYMENT.md` and `OPERATIONS_RUNBOOK.md`.

## Known architecture limitations

See `KNOWN_LIMITATIONS.md`. The main ones:

- Tokens in `localStorage`.
- The main JavaScript bundle is about 836 kB (no code-splitting).
- Notifications are sent synchronously (no Celery task yet).
- FHIR, HL7 and ABDM are not mounted.
- No structured EMR sections (complaint, history, examination).
- No frontend test harness.
