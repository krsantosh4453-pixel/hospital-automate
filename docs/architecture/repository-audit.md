# Repository audit (2026-11-09)

Scope: discovery for the multi-tenant SaaS and Flutter mobile programme. Nothing was changed in code.
Each statement is marked **[V]** verified by reading the code or config, or **[A]** an assumption or a figure taken from an earlier report and not re-run today.

Related: [current-system.md](current-system.md) · [target-system.md](target-system.md) · [implementation-roadmap.md](implementation-roadmap.md) · [risks-and-dependencies.md](risks-and-dependencies.md)

## 1. Repository map

| Location | What it is | Relevant? |
|---|---|---|
| `~/Desktop/hospital automate` (`krsantosh4453-pixel/hospital-automate`, branch `ui/redesign-2026-10-25`, 156 commits, 871 tracked files) | The product: Django API + React web app in one repository | **Yes, the only active repository** [V] |
| `~/Desktop/hospital automate 2`, `hospital automate 3` | Old clones of the same GitHub repository (last commits 2026-09-19 and 2026-10-05) | No, stale copies [V] |
| `~/Desktop/hospital automate.worktrees/*` | Git worktrees of the same repository used by agent sessions | No, branches of the same code [V] |
| `~/Desktop/hospital_managment` | An earlier, separate frontend/backend attempt (not a git repository) | No [V] |
| `~/Desktop/ai_healthcare_bot` | A small separate Django project | No: not imported or called by the product [V] |

There is no mobile repository and no Flutter code anywhere. Flutter and Dart are **not installed** on this Mac (`which flutter` finds nothing); Xcode is present [V].

## 2. Components inside the active repository

### 2.1 Backend API (`backend/`)

| | |
|---|---|
| Purpose | All business rules and data for every role |
| Framework | Django 6.0.9, Django REST Framework 3.18.3, SimpleJWT 5.5.1, drf-spectacular 0.30 (OpenAPI), Celery 5.6 + django-celery-beat, django-redis, gunicorn 26 [V, `requirements-lock.txt`] |
| Database | PostgreSQL 16 in production (`config/settings/production.py`, `CONN_MAX_AGE=60`); SQLite in development (`backend/db.sqlite3`) [V] |
| Primary keys | `BigAutoField` integers everywhere except two report models (UUID) [V] |
| Size | About 150 models across 30 Django apps; 114 backend test files [V]. The last documented run passed 217+ backend tests [A] |
| Entry points | `manage.py`, `config/wsgi.py` (gunicorn), `config/asgi.py`, `config/celery.py`, `entrypoint.sh` [V] |
| API ownership | Owns every endpoint under `/api/` (no versioning yet), `/health/*`, `/api/schema/`, `/api/docs/` [V] |
| DB ownership | Sole owner of the schema; migrations are version-controlled per app [V] |

Important directories:

| App | Holds | Reuse for mobile |
|---|---|---|
| `users/` | Staff roles, `StaffProfile`, `StaffHospitalMembership` (staff × hospital × role × department), patient OTP and email OTP sign-in, proxy/family access, staff invites, `HospitalScopedViewSet`, permission classes, care scope | **Core**: tenancy and RBAC already live here |
| `hospital/` | `Hospital`, `Department`, `Ward`, `Room`, `Bed`, `RoleModuleRestriction`, public hospital directory | Hospital discovery, departments |
| `patients/` | `Patient` (optional `user` link), `PatientHospital` (per-hospital UHID), `UhidSequence`, documents, timeline | Patient profile, registration |
| `doctors/` | `Doctor` (per hospital, optional user, department) | Doctor discovery |
| `appointments/` | `Appointment`, patient self-booking with 30-day window and upcoming-booking cap | Booking |
| `encounters/` | `Visit`, `QueueToken` (idempotent token issue), `DoctorSchedule` (weekly day/start/end) | Check-in, queue, schedules |
| `clinical/` | Vitals, allergies, notes, diagnoses, orders, procedures, medical records, prescriptions + items, certificates, referrals, immunisations | Doctor workflow, patient records |
| `billing/` | Invoices, items, payments (with `idempotency_key`), advances, insurance claims, per-hospital invoice sequence, GST | Bills, payments |
| `pharmacy/`, `procurement/` | Medicines, sales, returns; suppliers, POs, GRNs, requisitions | Pharmacy (staff) |
| `notifications/` | In-app notifications, delivery log, channel consents, OTP verification log, voice-call fallback; Celery retry task | Notifications (push missing) |
| `ai_scribe/`, `ai_advanced/` | Consultation session, transcript, AI draft, doctor review, prompt templates, STT + LLM provider abstraction (OpenAI or development stub); AI discharge draft | Doctor voice-to-text draft |
| `audit/` | Audit log, AI-interaction log, break-glass access; retention task | Audit trail |
| `consent/`, `documents/` | Consent forms/records, record shares, DPDP rights requests, patient documents | Consent, medical reports |
| `laboratory/`, `ipd/`, `emergency/`, `nurses/`, `bloodbank/`, `hospital_services/`, `reports/`, `home/` | Remaining hospital modules and dashboards | Admin dashboards and reports |
| `abdm/`, `fhir/`, `interoperability/`, `terminology/` | ABHA link (off by default), FHIR R4 read API (off by default), mappings, ICD-10 search | Later |
| `config/` | Settings (base/development/testing/e2e/production), cookie JWT auth, correlation-id and rate-limit middleware, health, exception handler, OpenAPI schema | Shared |
| `security_tests/` | 36 files of tenancy, permission and PostgreSQL row-lock tests | Regression net |

### 2.2 Web frontend (`src/`, root `package.json`)

| | |
|---|---|
| Purpose | The staff application and the patient portal |
| Framework | React 19.2, React Router 7, Vite 8, Tailwind CSS 4, lucide-react; plain `fetch` client in `src/services/api.js` [V] |
| State | React contexts in `src/assets/context/` (Auth, Role, Hospitals, Patient, Pharmacy, Prescription, Language) [V] |
| Auth | httpOnly cookies (`X-Auth-Mode: cookie`), CSRF token, acting hospital sent as `X-Hospital-ID` [V] |
| Tests | 65 Vitest unit tests, 23 Playwright E2E tests (`e2e/`) [A, from `KNOWN_LIMITATIONS.md`] |
| API ownership | None; consumes the backend only |
| DB ownership | None |

### 2.3 Deployment and tooling

- `docker-compose.prod.yml`: postgres 16, redis 7 (password, AOF, LRU), backend (gunicorn), celery-worker, celery-beat, frontend build, nginx (TLS, `nginx.conf.template`) [V].
- `docker-compose.dev.yml`, `backend/Dockerfile`, `Dockerfile.frontend` [V].
- CI: `.github/workflows/ci.yml` runs ruff, ESLint, Vitest, the Vite build, Django checks, a missing-migration check, and backend tests on PostgreSQL 16 with row-lock tests required [V].
- Observability: Sentry SDK, django-prometheus, health checks, correlation ids [V].
- Env: `.env.example`, `.env.production.example`; production refuses to start without CORS origins and RS256 JWT keys [V].

## 3. Integrations

| Integration | State |
|---|---|
| Twilio Verify (patient + staff SMS OTP) | Code present; never run with real credentials [V code; A untested, per `KNOWN_LIMITATIONS.md` L2] |
| Twilio SMS/WhatsApp/Voice | Providers stubbed; voice default `noop` [V] |
| Email (SMTP) | Configured in production settings; email OTPs stored as keyed HMAC [V] |
| Google sign-in | Present for patients [V] |
| OpenAI (LLM), STT | Behind a provider interface; 503 without a key [V] |
| Firebase push | Only two settings (`PUSH_NOTIFICATION_PROVIDER`, `FIREBASE_CREDENTIALS_PATH`); **no implementation, no device table** [V] |
| Payment gateway | **None.** Payments are recorded manually with a free-text `payment_method` [V] |
| ABDM / FHIR | Mounted, off unless enabled [V] |

## 4. Duplicates, dead code and incomplete work

| Finding | Evidence | Suggested action |
|---|---|---|
| Unmounted URL modules | `appointments/urls.py`, `pharmacy/urls.py`, `compounder/urls.py`, `patients/urls.py`, `doctors/urls.py` exist but are not included in `config/urls.py`; the root router registers those viewsets directly. `doctors/urls.py` holds separate function views (`doctor_list`, `doctor_detail`) [V] | Remove or mount deliberately during the API-v1 work, not before |
| iCloud conflict copy | Untracked `backend/patients/tests 2.py` differs from `tests.py` [V] | Owner to diff and delete |
| Two FHIR layers | `fhir/` (views) uses `interoperability/fhir/mappings` [V] | Fine as is; keep one entry point |
| No patient AI chatbot | `ai_scribe` is a doctor-side scribe; nothing patient-facing [V] | New module in Phase 9 |
| Many top-level status reports | 20+ `*_REPORT.md` / `PHASE_*.md` at the root, some superseded [V] | Archive into `docs/history/` later |
| Sessions with no device metadata | SimpleJWT blacklist tables exist; there is no per-device session list [V] | Phase 3 |

## 5. Skills and agents relevant to this programme

- **Backend:** `ecc:django-patterns`, `ecc:django-security`, `ecc:django-tdd`, `ecc:postgres-patterns`, `ecc:database-migrations`, `ecc:api-design`, `ecc:healthcare-phi-compliance`. Reviewers: `ecc:django-reviewer`, `ecc:database-reviewer`, `ecc:security-reviewer`, `ecc:healthcare-reviewer`.
- **Mobile:** `ecc:dart-flutter-patterns`, `ecc:flutter-dart-code-review`, `ecc:flutter-build`, `ecc:flutter-test`. Reviewer: `ecc:flutter-reviewer`. Build fixer: `ecc:dart-build-resolver`.
- **Integrations:** `twilio-developer-kit:twilio-verify-send-otp`, `twilio-developer-kit:twilio-webhook-architecture`.
- **Load testing:** `ecc:benchmark-methodology` (k6 or Locust scripts).
