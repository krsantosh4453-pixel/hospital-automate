# Production Readiness Audit

- **Date:** 2026-10-25 (evening)
- **Revision:** branch `ui/redesign-2026-10-25` at `e2900f2`, plus the owner's uncommitted changes (10 files), plus this audit's changes. Nothing is committed.
- **Companion documents:** `DEFECT_REGISTER.md` (every defect, fixed or open), `TEST_EXECUTION_REPORT.md` (every command and result), `SECURITY_AUDIT.md`, `DEPLOYMENT_CHECKLIST.md`.
- **Earlier reports:** `FINAL_PRODUCTION_READINESS_REPORT.md` (morning) and `reports/HMS_TECHNICAL_AUDIT_REPORT.md` (read-only, afternoon) are the inputs to this audit.

## Verdict: READY FOR STAGING VALIDATION

Not production-ready.

**What has been checked.** No known Critical defect remains open, and the backend suite passes on SQLite and PostgreSQL 16.

**Why not production-ready:**

- Two High items remain open and need your decision: tokens in `localStorage` (R-01) and `db.sqlite3` in git history (R-02).
- The production runtime (Docker, nginx, TLS) has never been started.
- Twilio, email, AI and Google sign-in have never run with real credentials.
- There has been no clinical safety review, penetration test or DPDP assessment.

A code audit cannot certify legal, clinical or operational readiness.

## Scope and method

**What was inspected:**

- All Django apps mounted in `backend/config/urls.py`, with deeper review of:
  - authentication (`users/`)
  - tenancy (`users/viewsets.py`, `users/permissions.py`)
  - patients, reports, notifications, middleware and settings
- The React client (`src/services/api.js`, contexts, the Queue, Appointments, Patients and AI Scribe pages) and all 26 staff routes in a browser.
- CI, Docker and nginx configuration (by reading).

**How the work was done:**

- The project folder is on iCloud with evicted files, and commands there stalled. Work therefore ran in an exact scratch copy, compared byte for byte with the project at the end (`TEST_EXECUTION_REPORT.md`).
- Each confirmed defect was fixed with a failing-then-passing regression test.

## What was wrong at the start

1. **Data destruction across hospitals.** Deleting a shared patient in one hospital erased another hospital's clinical and billing records.
2. **Tenancy gap.** Leaving out the hospital header widened a user's role to the union of their roles in every hospital.
3. **Auth bypasses.**
   - Staff could get tokens through Google sign-in (fixed by your uncommitted change).
   - They could also get tokens through the patient login routes if they had a patient record, skipping password + OTP.
4. **Open report templates.** Any authenticated account, including patients, could read and edit them. Schedules could be moved to other hospitals.
5. **False delivery records.** Notifications were recorded as "sent" when nothing was sent, and message text (PHI) was logged.
6. **Inactive or bypassable security config.**
   - Django's CSP was silently inactive.
   - Rate limits trusted a spoofable header.
   - Test and production settings depended on development variables, so a fresh clone or CI could not run the tests.
7. **CI never ran.** It triggered on the wrong branch name, and it could not have passed anyway.
8. **Front-end defects.**
   - The Queue page only saw appointments booked in the same browser.
   - Patient data stayed in `localStorage` after logout.
   - Timeouts created duplicate local records.
   - The AI scribe could never reopen an existing session.

## Final metrics

**Requirements.** The 116-row checklist in `REQUIREMENTS_TRACEABILITY.md` was **not** re-scored row by row in this audit. Its last counts were:

| Status | Rows |
|---|---:|
| Verified | 42 |
| Implemented | 24 |
| Partial | 23 |
| Missing | 23 |
| Blocked | 3 |
| N/A | 1 |

The afternoon read-only audit estimated 64.3% implementation and 31.3% verified. This audit's fixes change behaviour inside existing rows (queue issuing, notification honesty, report access) and add no new modules.

| Metric | Count |
|---|---:|
| Backend tests discovered / executed (SQLite) / passed / failed / skipped | 254 / 254 / 253 / 0 / 1 |
| Same suite on PostgreSQL 16 | 254 run, 253 pass, 1 skipped |
| Frontend tests discovered / executed / passed | 4 / 4 / 4 |
| Other checks executed / passed (static, config, style, deps, secrets, 3 manual browser scenarios) | 14 / 13 (the 1 failure is informational style lint) |
| Checks blocked / not run | 2 / 4 (see `TEST_EXECUTION_REPORT.md`) |
| New regression tests this audit | 25 backend + 4 frontend |
| Defects fixed | 16 (1 Critical, 7 High, 5 Medium, 3 Low; one High, D-06, was fixed by the owner and verified here) |
| Defects remaining | 14: 2 High, 5 Medium, 7 Low |
| Security findings remediated this audit | 9 (`SECURITY_AUDIT.md` #25–33) |
| Security findings unresolved | 2 High (R-01, R-02) and 3 security-relevant Medium (R-04, R-05, R-07) |

**Counting method.**

- A test is a test method, counted once per database run. The PostgreSQL run repeats the SQLite tests and is not added to them.
- A defect is one root cause, even when it spans several files.

## Test results

| Area | Executed | Passed | Failed | Blocked | Not run |
|---|---:|---:|---:|---:|---:|
| Backend (SQLite) | 254 | 253 | 0 | 0 | 1 |
| Backend (PostgreSQL 16) | 254 | 253 | 0 | 0 | 1 |
| Frontend unit | 4 | 4 | 0 | 0 | 0 |
| Static / build / config | 7 | 7 | 0 | 0 | 0 |
| Style lint (informational) | 1 | 0 | 1 | 0 | 0 |
| Dependency / secret scans | 3 | 3 | 0 | 0 | 0 |
| Manual browser | 3 | 3 | 0 | 0 | 1 |
| Infra / integrations / ops / perf / Bandit | 0 | 0 | 0 | 2 | 3 |

## Implemented fixes

| ID | File(s) | Root cause | Fix | Regression test | Final result |
|---|---|---|---|---|---|
| D-01 | `patients/views.py` | Cascade from a shared Patient | 409 when used by another hospital | `PatientDeleteTests` | Pass |
| D-02 | `users/viewsets.py` | Role union without acting hospital | Per-hospital permission evaluation for lists | `RolePerHospitalTests` | Pass |
| D-03 | `reports/views.py` | `IsAuthenticated` only; create-only checks | Staff / superuser split; hospital and recipient validation | `test_reports_access` | Pass |
| D-04 | `notifications/services/providers.py` | Stubs returned success | Real email; honest failures; no PHI in logs | `ProviderHonestyTests` | Pass |
| D-05 | `users/views.py` | Patient routes ignored staff profile | 403 for staff accounts | `test_auth` | Pass |
| D-06 | `users/views.py` (owner) | Google linked staff by email | Owner's fix verified | `test_auth` | Pass |
| D-07 | `config/settings/__init__.py`, `testing.py` | Package init imported dev settings | Select only when the package is the settings module; optional `TEST_DATABASE_URL` | `test_settings_loading` | Pass |
| D-08 | `config/client_ip.py` + 4 call sites, settings | Leftmost XFF trusted | `TRUSTED_PROXY_COUNT`, DRF `NUM_PROXIES` | `test_client_ip` | Pass |
| D-09 | `config/settings/production.py` | django-csp 4 format | `CONTENT_SECURITY_POLICY` | `test_settings_loading` | Pass |
| D-10 | `src/pages/queue.jsx` | Local-only appointment source | Server appointments; server tokens only | Browser | Pass |
| D-11 | `api.js`, 3 contexts, Appointments, Patients | No cleanup; timeout = offline | Clear on logout/expiry; timeouts surface | `apiSession.test.js` | Pass |
| D-12 | `src/pages/AIScribe.jsx` | Number vs string id | String compare | Browser | Pass |
| D-13 | `.github/workflows/ci.yml` | Wrong branch; unpassable lint; pytest | `master`; correctness lint; Django runner on SQLite + PostgreSQL; `npm test`; audits | Local run of each step | Pass locally |
| D-14 | `hospital/permissions.py` | Undefined `view` | Pass parameter | Ruff F82 | Pass |
| D-15 | `config/settings/production.py` | Stale warning | Corrected | — | Done |
| D-16 | `package.json`, `vitest.config.js`, `src/__tests__/`, `test_frontend_contract.py` | No frontend tests; no method contract | Vitest; usage and method contract tests | Mutation-checked | Pass |

## Remaining defects

See `DEFECT_REGISTER.md` → Remaining (R-01 to R-14). Summary:

| ID | Severity | Module | Problem | Next action |
|---|---|---|---|---|
| R-01 | High | auth / frontend | Tokens in `localStorage`; nginx CSP allows inline scripts | httpOnly cookies + CSRF, or formal risk acceptance |
| R-02 | High | repository | `db.sqlite3` in git history | History rewrite (needs your approval) |
| R-03 | Medium | clinical, patients | Hard deletes of clinical rows; non-admin delete of single-hospital patients | Policy: soft delete / admin-only |
| R-04 | ~~Medium~~ Fixed 2026-10-28 | staff admin | Pending applicants visible to all hospitals; Admin via shared invite code | Done: invite-only staff; Admin code kept as accepted onboarding path |
| R-05 | Medium | audit | No read auditing; no break-glass | Policy, then build |
| R-06 | Medium | notifications | SMS/WhatsApp/Voice not implemented; synchronous | Twilio Messaging + Celery |
| R-07 | Medium | APIView endpoints | Not re-checked for role-union | Probe each endpoint |
| R-08 – R-14 | Low | various | UHID uniqueness, static storage, CI pinning, public docs, quality, offline cache, dev bypass | See register |

## Production blockers

| Blocker | Risk | Required action | Owner / dependency |
|---|---|---|---|
| Runtime never started (Docker, nginx, TLS) | Routing, `/media/` denial, headers and health unverified | Staging rehearsal (`DEPLOYMENT_CHECKLIST.md` §2–3) | DevOps; a machine with Docker |
| Real providers never exercised | Staff cannot sign in if Twilio Verify fails; email and AI unverified | Staging credentials and end-to-end runs | You (accounts, credentials) |
| R-01 tokens in `localStorage` | One XSS exposes patient-data sessions | Decide and implement, or accept formally | You + security owner |
| R-02 database in git history | Possible data exposure if the repository is shared | Purge history before sharing | You (approval for force-push) |
| No clinical safety sign-off; no drug-interaction checking | Patient harm | Clinician/pharmacist review | Clinical safety officer |
| No penetration test / DPDP assessment | Legal and regulatory exposure | Commission both | Organisation |
| CI unconfirmed on GitHub | Regressions could merge unseen | Push to `master` and confirm green | You |

## Handover

1. **What was wrong.** See "What was wrong at the start". The most serious: cross-hospital data destruction on patient delete, role widening on lists, two staff-OTP bypasses, and fake notification delivery.

2. **What was fixed.** The 16 defects above, each with a test or a browser check. Your uncommitted changes (Google staff refusal, random dev OTP, password validation, SMTP and Twilio options, request timeouts) were kept and are covered by the passing suite.

3. **Tests before and after:**

   | | Before | After |
   |---|---|---|
   | Backend, with your `.env` | 229 (1 skipped) | 254 (1 skipped) |
   | Backend, without `.env` | 0, could not load | 254 (1 skipped), on SQLite and PostgreSQL |
   | Frontend | 0 | 4 |

   Lint, build and dependency audits were clean both before and after.

4. **Still failing or not run:**
   - Style lint (1,469 Ruff findings; informational).
   - One pre-existing skipped MAR model test.
   - Patient-portal browser pass.
   - Docker/nginx and real providers: blocked.
   - Backup/restore: not re-run.
   - Load tests and Bandit: not run.

   Reasons are in `TEST_EXECUTION_REPORT.md`.

5. **Incomplete features** (`KNOWN_LIMITATIONS.md`):
   - drug-interaction alerts
   - ABDM, FHIR, HL7
   - SMS/WhatsApp/Voice notifications
   - CSSD, OT, HR, ambulance
   - invoice PDF, advance payments
   - ICD-10 search, certificates, referrals, vaccination
   - proxy access

6. **Remaining security risks:** R-01 to R-07 above.

7. **Manual configuration.** Everything in `DEPLOYMENT_CHECKLIST.md` §1, in particular:
   - Twilio Verify, SMTP, Google client id
   - JWT RSA keys
   - `TRUSTED_PROXY_COUNT`
   - the AI provider key
   - retention policy

8. **Local verification commands:**

   ```bash
   cd backend
   python manage.py check --settings=config.settings.testing
   python manage.py makemigrations --check --dry-run --settings=config.settings.testing
   python manage.py test --settings=config.settings.testing

   cd ..
   npm ci
   npm run lint
   npm test
   npm run build
   ```

   Run them from a folder outside iCloud.

9. **Before staging and production:**
   - Commit, push and confirm CI.
   - Make the decisions on R-01, R-02 and R-03.
   - Run the staging rehearsal and real-credential runs.
   - Get the clinical, penetration-test and DPDP sign-offs.
   - Then follow `DEPLOYMENT_CHECKLIST.md` §5.

**Completed work** is the "Implemented fixes" table. **Recommendations and blockers** are "Remaining defects" and "Production blockers".

## Update 2026-10-26: production points 1–7

The verdict stays **READY FOR STAGING VALIDATION**. Remaining blockers need credentials, a real server or people; none is a known code defect.

| # | Point | Status | Evidence |
|---|---|---|---|
| 1 | Docker / nginx / HTTPS run | **Done locally.** The full production Compose stack ran with self-signed TLS after 9 deployment defects were fixed (D-19 to D-27); none of them could have been found without running it. Still needed: the same on a real server with a domain and CA certificate | `DEFECT_REGISTER.md` (update), T-029, T-039 to T-042 |
| 2 | Real Twilio / email / Google / AI | **Blocked.** Your `.env` has every Twilio key blank and no SMTP settings | T-030 |
| 3 | Tokens in `localStorage` | **Done.** httpOnly cookies + CSRF; nginx CSP without inline scripts; Google sign-in no longer blocked by the CSP | D-17, D-18, T-041, T-043 |
| 4 | `db.sqlite3` in git history | **Done.** Purged with `git filter-repo` and force-pushed to all 4 GitHub branches; 0 commits now contain it. GitHub's read-only PR #1 refs need GitHub Support to purge. Backup in `~/hms-backups` | `DEFECT_REGISTER.md` R-02 |
| 5 | Clinical safety sign-off | **Pack ready:** `CLINICAL_SAFETY_REVIEW_PACK.md`. Needs a clinician and pharmacist | — |
| 6 | Penetration test / DPDP | **Pack ready:** `PRIVACY_AND_PENTEST_PACK.md`. Needs an external firm and a privacy assessor | — |
| 7 | CI green on GitHub | Waiting for your pull request into `master`. Every CI command passes locally (262 tests on SQLite and PostgreSQL 16; 8 frontend tests) | T-034 to T-038 |
