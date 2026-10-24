# Hospital Management System — Evidence-Based Audit

**Audit date:** 2026-10-17  
**Scope:** Current checkout and available local runtime. This report distinguishes source inspection from runtime verification.

## 1. Executive Summary

| Area | Status | Evidence |
|---|---|---|
| Overall verified status | **PARTIALLY WORKING** | The frontend production build succeeds. No complete clinical or administrative workflow was verified end to end. |
| Frontend | **PARTIALLY WORKING** | Vite build succeeds; several pages use demo records and local-only mutations. Lint did not complete. |
| Backend | **BLOCKED** | Django checks and tests stalled during imports in the local Python 3.14 environment. |
| API integration | **BLOCKED** | Anonymous access was rejected by the pre-existing local API process, but CRUD and persistence were not exercised. |
| Database | **BLOCKED** | No migration or persistence verification completed. The tracked SQLite database was not inspected or modified. |
| Authentication/security | **PARTIALLY WORKING** | Anonymous API access returned 401 on the pre-existing process; source contains JWT/RBAC/hospital-scoping logic. Production frontend dev-bypass behavior was fixed and build-verified. Login, role, and cross-hospital flows remain unverified. |
| Testing | **BLOCKED** | Frontend build passed. Lint, Django checks, migration check, and backend tests did not complete. |
| Production readiness | **Not Ready** | Production configuration and data-integrity blockers remain; critical workflows, deployment startup, and recovery have not been verified. |

No completion percentage is assigned: the full set of workflow acceptance criteria could not be tested.

## 2. Technology and Architecture

- **Frontend:** React 19.2.8, Vite 8.2.2, React Router 7.18.3, Tailwind CSS 4.3.3, Axios 1.20.0.
- **Backend:** Django 5.2.17, Django REST Framework (requirements allow 3.15+), SimpleJWT.
- **Runtime observed:** Node 26.7.0, npm 11.19.0, Python 3.14.6. The repository virtual environment imports Django 5.2.17.
- **Development database setting:** SQLite at `backend/db.sqlite3`. `development.py` does not use `DATABASE_URL`.
- **Production database setting:** PostgreSQL parsed from `DATABASE_URL`.
- **Cache/workers:** Redis and Celery are configured; Compose files describe PostgreSQL, Redis, workers, and beat.
- **Authentication:** JWT is used by the API client. The client stores access and refresh tokens in `localStorage`; staff and patient login flows are implemented in source but were not exercised.
- **API shape:** DRF routers and app URL includes under `/api/`; the frontend API base is `VITE_API_BASE_URL` or `/api`.
- **Frontend routes:** Staff modules, admin pages, login/registration, and patient portal routes are registered in `src/App.jsx`.
- **Applications registered in base settings:** users, patients, home, doctors, appointments, nurses, compounder, pharmacy, laboratory, hospital, encounters, clinical, ipd, emergency, billing, bloodbank, notifications, audit, procurement, ai_scribe, and reports.
- **Route gaps:** FHIR, HL7, and ABDM includes are commented out in `backend/config/urls.py`. Documents and consent includes are present in source, but consent operations are stubs.
- **Environment limitations:** Docker was unavailable. A pre-existing local backend process was already running and was not restarted or modified. The repository already had extensive unrelated uncommitted changes, including settings, migrations, reports, and `backend/db.sqlite3`; these were preserved.

## 3. Module-by-Module Audit

`CODE PRESENT, UNVERIFIED` means code exists but runtime behavior was not established. `PARTIALLY WORKING` is used where source inspection confirms mock data, local-only operations, or stubs prevent a complete workflow.

| Module | Frontend | Backend | API | Database | Tests | Final Status |
|---|---|---|---|---|---|---|
| Hospital and department administration | Pages/routes present | Models, serializers, views present | Mounted | Not exercised | Present, not run | **CODE PRESENT, UNVERIFIED** |
| Patient registration, UHID, portal | Pages/routes present; patient page has demo fallback | Patient viewsets and auth code present | Mounted | Not exercised | Present, not run | **PARTIALLY WORKING** — fallback can substitute demo patients |
| Reception and appointments | Pages present with offline/demo seed behavior | Appointment viewset present | Mounted | Not exercised | Present, not run | **PARTIALLY WORKING** |
| Queue and encounters | Queue page has demo seed behavior | Encounter routes/views present | Mounted | Not exercised | Present, not run | **PARTIALLY WORKING** |
| Doctors | Page has offline/demo fallback | Doctor APIs present | Mounted | Not exercised | Present, not run | **PARTIALLY WORKING** |
| Clinical consultation, vitals, notes, diagnosis, prescription | Pages and API client methods present | Clinical models/views/serializers present | Mounted | Not exercised | Present, not run | **CODE PRESENT, UNVERIFIED** |
| Nursing, assessment, MAR, care tasks | Page has numerous mock datasets; failed API calls are replaced with empty results, then fallback mocks | Nurse and clinical APIs present | Mounted | Not exercised | Present, not run | **PARTIALLY WORKING** |
| IPD, beds, discharge | Page/routes and APIs present | Models and viewsets present | Mounted | Not exercised | Present, not run | **CODE PRESENT, UNVERIFIED** |
| Emergency/ER | Page and API code present | Models/views present | Mounted | Not exercised | Present, not run | **CODE PRESENT, UNVERIFIED** |
| Pharmacy, inventory, procurement | Pages, API client, and backend routes present | Models/services/views present | Mounted | Not exercised | Present, not run | **CODE PRESENT, UNVERIFIED** |
| Laboratory and results | API list is loaded; create/edit/delete/process/complete handlers update local React state; mock tests appear when API data is empty | Lab tests, collection, dispatch, results, and verification APIs present | Mounted | UI mutations not persisted by the inspected handlers | Present, not run | **PARTIALLY WORKING** |
| Billing, payments, insurance | Pages/API methods present | Invoice, payment, and claim APIs present | Mounted | Not exercised | Present, not run | **CODE PRESENT, UNVERIFIED** |
| Blood bank | Page/API code present | Models and routes present | Mounted | Not exercised | Present, not run | **CODE PRESENT, UNVERIFIED** |
| Documents | Patient document UI/API references present | Document routes and access checks present | Mounted in source | Not exercised | Not run | **CODE PRESENT, UNVERIFIED** |
| Consent | Patient UI present | Static templates; create, sign, revoke, verify, and signature operations return HTTP 501; record list is hard-coded empty | Mounted in source | No persistence path observed | Not run | **PARTIALLY WORKING** |
| Notifications and OTP | Auth client methods present | Notification/OTP code present | Mounted | Not exercised | Present, not run | **CODE PRESENT, UNVERIFIED** |
| Audit logging | No complete user workflow verified | Audit models/API present | Mounted | Not exercised | Present, not run | **CODE PRESENT, UNVERIFIED** |
| Reports and dashboards | Reports page uses hard-coded demo datasets; Home has demo fallbacks | Report services, models, and APIs exist | Mounted | UI report data not shown to come from API | Not run | **PARTIALLY WORKING** |
| AI medical scribe | Recording/review page and API calls present | Provider abstractions include development mocks and real-provider adapters | Mounted | No generated result was persisted in this audit | Not run; no provider test | **PARTIALLY WORKING** — provider/configuration behavior is unverified |
| FHIR | No frontend workflow found | Source app exists | URL include disabled | Not exercised | Not run | **NOT IMPLEMENTED** as a reachable API |
| HL7 | No frontend workflow found | Source app exists | URL include disabled | Not exercised | Not run | **NOT IMPLEMENTED** as a reachable API |
| ABDM/ABHA | No frontend workflow found | Source app exists | URL include disabled | Not exercised | Not run | **NOT IMPLEMENTED** as a reachable API |

## 4. API Audit

| Method and route | Purpose | Auth/permission evidence | Runtime result | CRUD/persistence |
|---|---|---|---|---|
| `GET /api/patients/` | Patient list | Anonymous request rejected | HTTP 401 from a pre-existing server process | No CRUD or persistence test |
| `GET /api/documents/` | Document list | Anonymous request rejected | HTTP 401 from the pre-existing process | No CRUD or persistence test |
| `GET /api/consent/` | Consent routes | Expected current source include exists | HTTP 404 from the pre-existing process; process predates this audit by several days, so this does not establish the current checkout's route behavior | No CRUD; source operations are stubs |
| `GET /health/ready/` | Readiness check | Public health route in source | Timed out with no response from the pre-existing process | Database readiness not established |

The source wires patient, doctor, appointment, pharmacy, laboratory, nurse, encounter, clinical, IPD, emergency, billing, blood-bank, notification, audit, procurement, AI, reports, documents, and consent routes. The current request/response contracts, authenticated permissions, persistence, and mutation refresh behavior were not validated by live CRUD tests.

## 5. Runtime and Build Results

| Command/action | Result |
|---|---|
| `npm run build` before and after the auth guard change | **Pass**; 80 modules transformed. Main JS chunk is about 842.5 kB minified, over Vite's 500 kB warning threshold. |
| `npm run lint` | **Blocked**; process remained stalled without diagnostics for over 10 minutes and was stopped. |
| `npx eslint src/assets/context/AuthContext.jsx` | **Blocked**; process remained stalled without diagnostics and was stopped. |
| `cd backend && ../backend_env/bin/python manage.py check --settings=config.settings.testing` | **Blocked**; no result after several minutes. Process sampling showed the Python process blocked while reading a Django bytecode file. |
| `manage.py makemigrations --check --dry-run --settings=config.settings.testing` | **Blocked** by the same environment stall; no result. |
| `manage.py test --settings=config.settings.testing --verbosity 1` | **Blocked** before test discovery/output by the same import stall; no test result is claimed. |
| Retry with `PYTHONPYCACHEPREFIX=/tmp/hms-audit-pycache` | **Blocked**; no result. Temporary cache was removed. |
| Local frontend HTTP check | HTTP 200. The browser page title loaded, but the accessible snapshot exposed only the root node; no workflow was tested. The temporary dev server was stopped. |
| Existing local API checks | Patient and documents anonymous GETs returned 401; readiness timed out; consent returned 404. This server was already running for several days and is not a fresh startup of this checkout. |
| Docker/Compose startup | **Blocked**; Docker CLI was unavailable. |

An initial Django check invocation from the repository root failed because `manage.py` is under `backend/`; subsequent commands used the correct working directory.

## 6. Missing and Broken Features

| Severity | Module / affected files | Confirmed issue and evidence | Root cause / required fix / risk |
|---|---|---|---|
| High | Frontend auth — `src/assets/context/AuthContext.jsx` | Before the audit change, the dev-auth bypass was enabled by default when its flag was absent and could be restored from browser storage. | **Fixed in this checkout:** production builds now force the bypass off and ignore/clear a stale bypass marker when no tokens exist. Development can still be explicitly configured. Risk: verify with an automated auth regression test when frontend test tooling is available. |
| High | Production startup — `backend/config/settings/production.py`, `docker-compose.prod.yml`, `.env.example`, `docs/ENVIRONMENT.md` | Production settings require `JWT_PRIVATE_KEY` and `JWT_PUBLIC_KEY`; Compose passes `JWT_SECRET_KEY` instead. Settings also require HL7 allowlist/key and Twilio Verify credentials when enabled; Compose defaults HL7 on but does not pass its allowlist/key or all required Twilio Verify values. Django workers/beat also need the production settings contract. | Align the secret/config contract for every Django service and validate it without embedding real secrets. Not changed: this requires an agreed deployment secret source and broader configuration edits. Docker was unavailable to verify startup. |
| High | Laboratory — `src/pages/laboratory.jsx` | Create/edit/delete/process/complete handlers mutate React state rather than calling backend mutation endpoints; mock records are used when the API list is empty. | Wire these actions to validated API operations, refresh persisted data, and show failures instead of sample clinical records. Regression risk: API payload/status mapping. |
| High | Nursing — `src/pages/Nurses.jsx` | Multiple clinical datasets fall back to hard-coded patients, vitals, notes, assessments, medication administration, and billing examples; individual API failures are converted to empty arrays. | Remove misleading clinical fallbacks and implement/report persisted API operations. This spans multiple workflow surfaces and needs a coordinated change; not applied. |
| High | Reports/Home — `src/pages/reports.jsx`, `src/pages/Home.jsx` | Reports use fixed sample datasets; dashboard metrics fall back to demo totals. | Connect metrics and reports to authenticated, hospital-scoped report endpoints; keep explicit loading/error/empty states. |
| High | Consent — `backend/consent/views.py` | Consent creation, signing, revocation, verification, and signature endpoints return 501; records are hard-coded empty. | Implement persistence, authorization, and audit trail before relying on consent workflow. |
| High | Development database — `backend/config/settings/development.py`, `docker-compose.dev.yml` | Compose starts PostgreSQL and sets `DATABASE_URL`, but development settings select SQLite directly. | Decide and document the intended dev database before changing it; switching can change where existing local data is stored. |
| Medium | Reports, AI, interoperability | Reports UI is demo-backed; AI includes a mock provider; FHIR/HL7/ABDM routes are disabled. | Integrate and verify independently; do not represent mock or unreachable behavior as production-ready. |
| Medium | Validation evidence | Full backend checks/tests, migrations, lint, Docker, and clinical workflows were not completed. | Resolve the local file/import stall and rerun with isolated test data and the repository's supported runtime. |

## 7. Security and Data Integrity

**Verified in source or limited runtime checks**

- DRF defaults to authenticated access; one anonymous patient API request returned 401 on the pre-existing server.
- `HospitalScopedViewSet` filters records using the user's hospital memberships. Patient creation includes an explicit hospital access check.
- Source tests include cross-hospital access-denial cases for users, patients, billing, pharmacy, procurement, and other modules, but those tests did not run.
- Production settings define secure cookies, HTTPS redirect defaults, HSTS, host/origin requirements, and RS256 JWT settings.
- Production frontend bundle was inspected after the fix: the compiled development-bypass function returns false even though the local Vite flag is true.
- No secrets or patient record contents were printed. The existing SQLite database was not directly queried or altered; the readiness request to the pre-existing server timed out without returning data.

**Failed checks or unverified risks**

- Staff login, patient OTP, role permissions, hospital isolation, sensitive audit events, and patient ownership were not verified end to end.
- Frontend auth tokens are stored in `localStorage`; mitigate XSS exposure through a reviewed CSP and frontend input/output handling, or consider an approved cookie-based design.
- OTP/SMS delivery was not tested. Production settings require Twilio Verify credentials.
- Production deployment configuration has the required-variable mismatch described above.
- Database integrity, migration application, backup recovery, and data persistence were not tested.
- Development configuration explicitly enables a fake staff identity in the local `.env`; this was not changed. Keep it confined to local development and set `VITE_DEV_AUTH_BYPASS=false` when testing real login.

## 8. Production Readiness

**Not Ready.** The production container startup contract is not demonstrated and is inconsistent with required JWT/HL7/OTP settings. Core clinical mutations and reports can present local/demo data instead of persisted records. Migrations and automated tests could not be verified. Database backups/recovery, monitoring, HTTPS end-to-end behavior, OTP delivery, and privacy controls have not been exercised. Do not use this audit as production approval.

## 9. Prioritized Roadmap

| Priority | Task | Prerequisites and affected areas | Acceptance criteria |
|---|---|---|---|
| P0 | Align production settings and Compose secrets | Confirm how RSA keys and external service credentials are provisioned; update `backend/config/settings/production.py`, `docker-compose.prod.yml`, `.env.example`, deployment docs, and all Django service definitions. | Configuration validation fails clearly when required secrets are absent; Compose config validates; backend, worker, and beat start with secrets supplied securely; health/readiness passes. |
| P0 | Preserve production auth enforcement | `src/assets/context/AuthContext.jsx`; add a frontend test harness when approved/available. | Production build never grants staff access without a valid session even with `VITE_DEV_AUTH_BYPASS=true` or stale local storage; normal local-development behavior is explicit and tested. |
| P1 | Make laboratory and nursing workflows persist | Review API serializers/actions and pages `src/pages/laboratory.jsx`, `src/pages/Nurses.jsx`. | Create/update/delete/result/MAR actions persist; failed requests remain visible; empty API results show an empty state rather than sample patient data; hospital scope is tested. |
| P1 | Verify patient-to-OPD-to-clinical-to-billing path | Use isolated test data and the existing tests under patients, appointments, encounters, clinical, laboratory, pharmacy, and billing. | Execute registration through invoice/receipt with database assertions and cross-hospital denial; no real patient data is used. |
| P1 | Unblock and run backend quality checks | Investigate Python 3.14 bytecode read stall; select the repository-supported Python runtime. | Django check and migration dry-run complete; full test suite reports pass/fail counts with no silent skips. |
| P2 | Integrate reports and dashboard | `src/pages/reports.jsx`, `src/pages/Home.jsx`, `backend/reports/`. | User/hospital-scoped report API data is displayed; loading, empty, and error states are distinct; no static sample data is presented as live. |
| P2 | Implement consent records and signatures | `backend/consent/views.py`, consent UI, persistence model/migrations. | Authorized create/sign/revoke/verify operations persist, produce audit records, and reject cross-patient/hospital access. |
| P2 | Verify provider-backed AI scribe and notifications | AI provider dependencies/settings, audio storage, Twilio/email configuration. | Provider availability is reported honestly; no mock output is presented as clinical output; review/approval is auditable. |
| P3 | Enable interoperability deliberately | FHIR/HL7/ABDM apps, URL registration, auth/network policy, credentials. | Separate conformance/security tests pass before routes are enabled in a deployment. |

## 10. Evidence-Based Completion Summary

1. **Verified working functionality:** Frontend production build; Vite frontend returned HTTP 200; anonymous patient/document requests to the pre-existing API process were rejected with 401; production bundle now compiles the dev-auth bypass as disabled.
2. **Partially working functionality:** Nursing, laboratory, reports/dashboard, patient/appointment/queue demo fallback behavior; consent templates without persisted consent operations; AI scribe with a development mock path.
3. **Broken functionality:** No current-checkout runtime feature is marked broken solely from the stale API process. Consent operations are explicitly unimplemented (501) in source.
4. **Not implemented functionality:** FHIR, HL7, and ABDM are not mounted in the current root URL configuration.
5. **Could not be tested:** Django checks, migrations, backend tests, lint, live CRUD, database persistence, authenticated workflows, cross-hospital isolation, deployment startup, and readiness.

**Five highest-priority next actions**

1. Align production environment requirements with Compose for JWT, HL7, OTP, and all Django services.
2. Add regression coverage for the production auth-bypass guard.
3. Replace mock/local-only laboratory and nursing operations with persisted hospital-scoped APIs.
4. Connect report/dashboard views to backend report endpoints and remove demo totals.
5. Unblock the Python validation environment, then run Django checks, migration checks, and the complete isolated test suite.
