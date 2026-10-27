# Defect Register

Audit date 2026-10-25 (evening). Branch `ui/redesign-2026-10-25`, base commit `e2900f2`, plus uncommitted changes. Nothing in this audit was committed.

**Sources.** Findings G-01 to G-14 come from the read-only report `reports/HMS_TECHNICAL_AUDIT_REPORT.md` (same day). This audit re-checked every one of them in code or at runtime. "New" means first found in this audit.

**Evidence.**

- "Reproduced" means a test failed against the unfixed code and passes after the fix.
- Test names refer to `backend/security_tests/` unless a path is given.

## Fixed

| ID | Sev. | Module / files | Defect and evidence | Root cause | Fix | Regression test | Result |
|---|---|---|---|---|---|---|---|
| D-01 (G-02) | Critical | `backend/patients/views.py` | A Hospital A receptionist's `DELETE /api/patients/{id}/` returned 204 and deleted Hospital B's visits. Reproduced. | A patient is shared across hospitals, and every clinical FK to `Patient` cascades | `destroy` returns **409** when the patient is registered at, or has any record in, another hospital | `test_rbac_and_writes.PatientDeleteTests` (4) | Pass |
| D-02 (G-04) | High | `backend/users/viewsets.py` | A user who is Doctor in A and Receptionist in B listed B's vital signs by omitting `X-Hospital-ID`. Reproduced (row 2 returned). | Without an acting hospital, list scoping used every member hospital, while role checks used the union of roles | Without an acting hospital, a list covers only the hospitals where the view's own permission classes pass for the role held there | `RolePerHospitalTests.test_list_without_hospital_*`, `test_detail_without_hospital_*` | Pass |
| D-03 (G-14) | High | `backend/reports/views.py` | Reproduced: a patient account read report templates; any hospital admin deleted shared templates; a schedule could be moved to a foreign hospital; recipients from another hospital were accepted; a missing `hospital` gave a 500. | Plain `ModelViewSet` with `IsAuthenticated` only; hospital checked only on create; `int(None)` | Templates: staff read, superuser write. Saved/scheduled reports: active staff, hospital validated on create **and** update, recipients must be staff of that hospital, 400 instead of 500 | `test_reports_access` (7) | Pass |
| D-04 (G-03) | High | `backend/notifications/services/providers.py` | With credentials set, SMS/WhatsApp/Voice and every email were recorded as **sent** although nothing was sent, and message bodies were logged at INFO. Reproduced. | TODO stubs returned `success=True` | Email is really sent through Django's mail backend to the patient's account email. SMS/WhatsApp/Voice report `success=False` ("not implemented"). Logs carry ids only | `test_notifications.ProviderHonestyTests` (3) | Pass |
| D-05 (G-13) | High | `backend/users/views.py` | A staff member with a linked patient record received tokens from `/api/auth/patient/login/` and `/api/auth/patient/token/` with no OTP. Those tokens act as staff. Reproduced. | Patient routes issued tokens without checking for a staff profile | The three patient token routes (`otp/verify`, `login`, `token`) refuse users with a staff profile (403) | `test_auth.StaffAuthTests.test_patient_*_refused_for_staff_account` | Pass |
| D-06 (G-01) | High | `backend/users/views.py` | Staff could sign in through Google with no password and no OTP | Google login linked by email and issued staff tokens | **Fixed by the owner's uncommitted change** (present before this audit). This audit only verified it | `test_auth.*google_login_refused*` (3) | Pass |
| D-07 (new) | High | `backend/config/settings/__init__.py` | Without a `.env`, the test settings (and therefore CI or a fresh clone) failed to load: "DJANGO_SECRET_KEY environment variable is required". Production settings also ran `development.py` first. Reproduced. | The package `__init__` star-imports an environment module even when `DJANGO_SETTINGS_MODULE` names a submodule | It now selects an environment only when the settings module is the package itself | `test_settings_loading` (3) | Pass |
| D-08 (G-09) | Medium | `config/client_ip.py` (new), `config/middleware/ratelimit.py`, `audit/services.py`, `users/permissions.py`, settings | Rate-limit keys, the audit IP, the admin and HL7 IP allow-lists, and DRF throttles (`NUM_PROXIES` unset) all trusted the client-supplied leftmost `X-Forwarded-For` | The leftmost entry is attacker-controlled; nginx appends the real address on the right | One `client_ip()` helper using `TRUSTED_PROXY_COUNT` (0 in development, 1 in production); DRF `NUM_PROXIES` set to match | `test_client_ip` (3) | Pass |
| D-09 (G-08) | Medium | `config/settings/production.py` | Under production settings Django sent **no** CSP header. Reproduced at runtime. | django-csp 4.0 ignores the legacy `CSP_*` names | Converted to `CONTENT_SECURITY_POLICY` with the same directives; `CSP_REPORT_ONLY` env supported | `test_settings_loading.test_production_settings_send_a_content_security_policy` | Pass |
| D-10 (G-05) | High (functional) | `src/pages/Queue.jsx` | The queue could only issue tokens for appointments booked in the same browser, and it mixed in local rows with made-up token numbers | Issuable appointments came from the `localStorage` context | Booked appointments now load from `/api/appointments/?hospital=`; the queue shows server tokens only | Browser: an appointment seeded server-side was issued real token #1 | Pass (manual) |
| D-11 (G-06) | Medium | `src/services/api.js`, `PatientContext.jsx`, `AppointmentContext.jsx`, `AuthContext.jsx`, `Appointments.jsx`, `Patients.jsx` | (a) Patient and appointment rows in `localStorage` survived logout on shared PCs. (b) A request **timeout** triggered the "saved on this device only" fallback although the server may already have saved, causing duplicates. | No cleanup on logout or session expiry; timeouts were treated as offline | `clearCachedPatientData()` on logout and on session expiry; contexts drop in-memory rows on `auth:logout`; timeouts surface as errors | `src/__tests__/apiSession.test.js` (3) | Pass |
| D-12 (new) | Medium | `src/pages/AIScribe.jsx` | Reopening a visit with an existing AI scribe session showed "consultation session with this visit already exists", and the transcript and drafts never loaded | `s.visit === selectedVisitId` compared a number with a string | String comparison | Browser: revisit made a GET only, no failing POST | Pass (manual) |
| D-13 (G-10) | Medium | `.github/workflows/ci.yml` | CI never ran: it triggers on `main`/`develop` but the branch is `master`. The lint job could never pass (1,469 Ruff findings), and `pytest` with no config would skip `tests.py` | Stale workflow | Triggers include `master`. Ruff runs correctness rules (E9, F63, F7, F82). Backend runs `manage.py test` on SQLite **and** PostgreSQL 16 from the lock file, with a missing-migration check. Adds `npm test`, `pip-audit`, and a gating `npm audit`. Node 24 | Workflow parsed; each command run locally | Pass (not run on GitHub) |
| D-14 (new) | Low | `backend/hospital/permissions.py` | `IsHospitalMember` referenced an undefined `view` (NameError; Ruff F821). The class is not imported anywhere | Missing parameter | Parameter passed through | `ruff --select F82` clean | Pass |
| D-15 (new) | Low | `config/settings/production.py` | The startup warning said the AI scribe "will run in development mode (mock responses)"; the code actually disables it | Stale message | Message corrected | — | Done |
| D-16 (new) | Low | frontend | No frontend test runner, and nothing caught calls to API methods that do not exist | — | Vitest 5 + jsdom; `npm test`. A test asserts every `api.<group>.<method>()` used in `src` exists. The backend contract test now also checks **HTTP methods** (291 calls) | `src/__tests__/apiUsage.test.js`, `test_frontend_contract.FrontendMethodContractTests` | Pass; both mutation-checked |

## Remaining (not fixed)

| ID | Sev. | Module | Problem | Evidence | Next action |
|---|---|---|---|---|---|
| R-01 (G-07) | ~~High~~ **Fixed 2026-10-26 (D-17)** | `src/services/api.js`, `nginx.conf.template` | Access and refresh tokens were in `localStorage`, and the nginx CSP allowed `'unsafe-inline'` scripts | Code | Done: httpOnly cookies + CSRF; inline scripts removed from the CSP |
| R-02 (G-11) | ~~High~~ **Fixed 2026-10-26** | git history | `backend/db.sqlite3` was in 4 historical commits on GitHub | After: 0 commits on `master`, `audit/…`, `cursor/…`, `ui/redesign-…` | Done: `git filter-repo` + force-push (owner approved). Backup: `~/hms-backups/hms-github-before-purge-2026-10-26.bundle`. GitHub's read-only `refs/pull/1/*` still reference old commits; ask GitHub Support to purge them. Commit ids quoted in these reports from before the rewrite (e.g. `e2900f2`, `582ef1c`) changed |
| R-03 (G-12) | Medium | `clinical/views.py`, `patients/views.py` | Vitals, diagnoses, notes and orders can be hard-deleted by Doctor/Nurse. A Receptionist, Doctor or Nurse can delete a patient known only to their own hospital, cascading that hospital's records | Code; existing test `patients.tests.test_delete_patient` expects a Doctor delete to succeed | Policy decision: soft delete / "entered in error", and/or admin-only patient deletion |
| R-04 | ~~Medium~~ **Fixed 2026-10-28** | `users/staff_admin.py`, `users/views.py`, `users/staff_invite.py` | Pending staff applicants (name, email, phone) were visible to every hospital's admins; Admin self-registration works with a shared invite code | `security_tests/test_staff_admin.py` (8 tests) | Done: staff join only by a hospital's invitation. Public sign-up refuses Doctor/Nurse/Compounder/Receptionist (403); the open applicant list and `/api/users/<id>/approve/` are removed; inviting an earlier applicant by email admits them. **Accepted (owner, 2026-10-28):** Admin sign-up with the secret `ADMIN_INVITE_CODE` stays as the onboarding path for a new hospital's owner; that Admin belongs to no hospital and can only create one |
| R-05 | Medium | audit | No read-auditing of list or detail views of clinical data; no break-glass access | Code | Define the policy, then implement it |
| R-06 | Medium | notifications | SMS, WhatsApp and Voice delivery is not implemented, and sending is synchronous | D-04 now reports it honestly | Implement with Twilio Messaging behind consent; move to Celery |
| R-07 | ~~Medium~~ **Fixed 2026-10-28 (D-29, D-30)** | non-viewset endpoints | The D-02 fix covered `HospitalScopedViewSet` only. Function, `APIView` and custom-permission endpoints were not re-checked for the role-union pattern | Every non-viewset endpoint reviewed; one live leak (procurement) and one count leak (home stats) reproduced | Done: see the 2026-10-28 update |
| R-08 | Low | `patients/models.py`, `users/patient_auth.py` | UHID is not unique per hospital but is used as a login identifier; email OTP hash is unsalted SHA-256 (short TTL) | Code | Unique constraint `(hospital, uhid)`; HMAC the OTP |
| R-09 | Low | production settings | `STATICFILES_STORAGE` is ignored by Django 6 and WhiteNoise is not installed, so static files depend on nginx | Runtime check | Switch to `STORAGES` after a Docker `collectstatic` rehearsal |
| R-10 | Low | CI | Trivy action is on `@master` (unpinned); Bandit is report-only; deploy jobs only `echo`; `Dockerfile.frontend` uses Node 20 | Workflow | Pin Trivy to a reviewed SHA; triage Bandit; write real deploy steps |
| R-11 | Low | API docs | Swagger/ReDoc are public. With the D-09 CSP, CDN-loaded Swagger assets may be blocked in production (not tested) | Code | Disable or protect docs in production |
| R-12 | Low | quality | Ruff 1,469 style findings; ESLint 68 warnings; main JS bundle 818 kB (no code splitting) | Command output | Reformat in a dedicated change; route-level `lazy()` |
| R-13 | Low | frontend | Network-failure fallback still writes patient/appointment rows to `localStorage` until logout; the Queue page reads only the first page (50) of appointments | Code | Real offline queue, or remove the fallback; filter appointments by date |
| R-14 | Low | `src/assets/context/AuthContext.jsx` | Development auth bypass defaults **on** under `vite dev` (never in a production build) | Code | Default it off |

## Counting

16 fixed defects (D-01 to D-16; D-06 was fixed by the owner and only verified here) and 14 remaining (R-01 to R-14).

Remaining by severity: **2 High** (R-01, R-02), **5 Medium** (R-03 to R-07), **7 Low** (R-08 to R-14).

## Update 2026-10-26: cookie sessions and production rehearsal

The owner asked for production points 1–7. The production Compose stack was started for the first time, using Docker via Colima on the audit Mac, with synthetic secrets and a self-signed certificate. Running it exposed defects that code review and unit tests could not.

| ID | Sev. | Files | Defect and evidence | Fix | Verification | Result |
|---|---|---|---|---|---|---|
| D-17 (R-01) | High | `config/auth_cookies.py`, `config/auth_cookie_views.py` (new), settings, `users/urls.py`, `users/views.py`, `src/services/api.js`, `AuthContext.jsx`, `PatientLogin.jsx` | JWTs were stored in `localStorage`, so one XSS exposed the session | The browser sends `X-Auth-Mode: cookie`; tokens go in httpOnly cookies (`Secure` + `SameSite=Strict` in production), never in the JSON body. Cookie-authenticated writes need a CSRF token (`/api/auth/csrf/`). Refresh and logout use the cookie. Bearer clients are unchanged | `test_auth_cookies` (8); `apiSession.test.js` (+4); HTTPS run through nginx; real browser: no JWT in storage, auth cookies invisible to JS, write 201, logout clears the session | Pass |
| D-18 | High | `nginx.conf.template` | The CSP blocked Google's sign-in script (`accounts.google.com/gsi/client`), so Google sign-in could not work in production. It also allowed `'unsafe-inline'` scripts | Allows only the GSI script, frame and style; no inline scripts (the build has none); adds `object-src`, `base-uri`, `frame-ancestors` | Header checked on the running stack | Pass |
| D-19 | Critical (deploy) | `.dockerignore` | `*.sh` excluded `backend/entrypoint.sh`, which the Dockerfile copies, so the backend image could not build | Re-include the entrypoint | Image built | Pass |
| D-20 | Critical (deploy) | `backend/Dockerfile` | `requirements-production.txt` includes `-r requirements.txt`, which was never copied, so `pip install` failed | Install the pinned, audited `requirements-lock.txt` (the set CI tests) | Image built | Pass |
| D-21 | Critical (deploy) | `backend/Dockerfile` | `python-magic` needs `libmagic1`, which was missing, so Django crashed while loading URLs | Install `libmagic1` | Backend healthy | Pass |
| D-22 | Critical (deploy) | `docker-compose.prod.yml` | `./logs` bind mount: Docker creates a missing folder as root, the non-root `django` user cannot write its log, and backend, worker and beat crash-loop | Named volume `app_logs`, which takes the image's ownership | All containers up | Pass |
| D-23 | High | `config/settings/base.py` | Beat uses `django_celery_beat`'s DatabaseScheduler, but the app was not in `INSTALLED_APPS`, so beat crashed and no scheduled task ever ran | App registered (its own migrations add the tables) | Beat logs "Starting…" | Pass |
| D-24 | Medium | `docker-compose.prod.yml` | Worker and beat inherited the image's HTTP health check, so they would be permanently "unhealthy" | Worker: `celery inspect ping`; beat: check disabled (restart policy covers crashes) | Worker healthy | Pass |
| D-25 | High (deploy) | `nginx-entrypoint.sh` | `#!/bin/bash` (the nginx:alpine image has no bash), and Compose overrides the entrypoint without a command, so `exec "$@"` had nothing to run | POSIX `sh`; starts `nginx -g 'daemon off;'` when no command is given | nginx serves 80/443 | Pass |
| D-26 | High | `nginx.conf.template` | nginx resolved `backend` once. After the backend was recreated (the documented upgrade step) it proxied to a dead IP. Missing `/50x.html` turned every outage into a "404 Not Found" | Upstreams re-resolve via Docker DNS (`resolve`); bogus error pages removed | Backend recreated without restarting nginx → 200; backend stopped → honest 504 | Pass |
| D-27 | High | `config/settings/production.py` | The HTTPS redirect answered the container health check with a 301, which `curl -f` treats as success, so "healthy" never tested the database | `SECURE_REDIRECT_EXEMPT` for `health/` | `/health/ready/` → 200 with database, cache, Redis and Celery checks | Pass |
| D-28 | Low | `nginx.conf` | The header was misspelled `X-Content-Type-Nosniff`, so no-sniff was never sent by the frontend container | `X-Content-Type-Options` | Header present | Pass |

**Rehearsal results** (`https://localhost`):

- All 7 containers healthy; all migrations applied on an empty PostgreSQL 16 database; 157 static files served.
- HTTP→HTTPS redirect works; `/media/` returns 404; anonymous API calls get 401.
- HSTS, CSP, `X-Frame-Options` and nosniff are present on SPA and API responses.
- `check --deploy` in the container reports no issues.
- 40 bad logins with rotating spoofed `X-Forwarded-For` were limited: Django 429 after 3, nginx 503 after its burst.
- Staff OTP with fake Twilio credentials fails cleanly (503).

**Not covered by this local rehearsal:**

- a real domain and CA certificate
- a real server's firewall and DNS
- backup/restore on the containers
- real Twilio/SMTP/Google/AI credentials. The local `.env` has every Twilio key blank and no SMTP settings, so point 2 is **blocked on credentials**.

**Counting after this update:** 28 defects fixed (D-01 to D-28).

Remaining:

- **1 High:** R-02 (approved, being applied).
- **5 Medium:** R-03 to R-07.
- **7 Low:** R-08 to R-14. R-09 (static storage) is mitigated: nginx served the collected static files in the rehearsal.

## Update 2026-10-28: R-07 (role union outside the viewset base)

Every function view, `APIView`, `viewsets.ViewSet` and custom permission class was reviewed for a role taken from the union of all hospitals instead of the acting hospital.

| ID | Sev. | Files | Defect and evidence | Fix | Regression test | Result |
|---|---|---|---|---|---|---|
| D-29 (R-07) | High | `backend/procurement/views.py` | `RequiresHospitalScope` checked `get_user_roles(user)` (all hospitals) and then only membership of `?hospital=`. A user who is Inventory Staff in A and Receptionist in B listed, created and edited B's suppliers (the same class guards purchase orders, goods receipt and stock). Reproduced: 200 / 201 / 200 | The role must be held in the acting hospital (`?hospital=`, body `hospital`, or `X-Hospital-ID`). A write with no hospital is refused unless the user belongs to exactly one hospital | `test_rbac_and_writes.ProcurementRolePerHospitalTests` (5) | Pass |
| D-30 (R-07) | Low | `backend/home/views.py` | The dashboard counted lab tests by the **patient's registration** hospital, so Hospital A's count included tests a shared patient had at Hospital B. Reproduced: 2 instead of 1 | Count by `LabTest.hospital` | `test_home_stats.HomeStatsTests.test_lab_count_uses_the_test_hospital_not_the_patient_registration` | Pass |
| D-31 | Low | `backend/users/permissions.py` | `IsOwnerOrHospitalAdmin` (not used by any view) accepted an Admin role held in any hospital for an object in another | Role read in the object's hospital | Not exercised (class unused) | Done |

**Reviewed and clean** (role checked in one named hospital, or no data): home stats (hospital required), report analytics and KPI views, consent writes and shared-record reads, documents upload/delete, staff list, membership and invites, hospital and org-structure writes, stock `adjust`. HL7 uses its own API-key/IP check. FHIR and ABDM views are stubs that return no data.

**Not fixed (policy decisions, new):**

| ID | Sev. | Module | Problem | Next action |
|---|---|---|---|---|
| R-15 | Medium | `consent/views.py`, `documents/views.py`, `reports/views.py`, `home/views.py` | Reads have **no role check**: any active staff role at a hospital (e.g. Pharmacist, Lab Staff) can list that hospital's consent records, shares, patient documents, analytics and revenue. Documents and consents also skip the Doctor/Nurse care scope. Not a role-union bug: it is the same with or without `X-Hospital-ID` | Decide which roles read each, then gate them per hospital |
| R-16 | Low | `home/views.py` | Lab "pending"/"completed"/"urgent" counts filter on `Pending`/`Completed`, which are not `LabTest` statuses, so they are always 0 | Map to the real status set |

Verification: full backend suite in a clean copy, `manage.py test` with `config.settings.testing`: **388 tests, OK (3 skipped)**. Both reproduced defects failed before the fix.

**Counting after this update:** 31 defects fixed (D-01 to D-31). Remaining: R-02 (High, see its row), R-03 to R-06 and R-15 (Medium), R-08 to R-14 and R-16 (Low).
