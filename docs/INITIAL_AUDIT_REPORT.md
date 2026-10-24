# Initial Audit Report (baseline)

**Baseline:** commit `e58280c` on 2026-10-24, tagged `baseline-before-readiness-audit-2026-10-24`. All work since is on branch `audit/production-readiness-2026-10-24`.

This report records the system as found, before any changes. For the current state, see `FINAL_PRODUCTION_READINESS_REPORT.md`.

## Method

1. Read both requirement documents in full: `HMS_UI_Structure.md` and the 43-page PDF. The PDF has no embedded images (checked page by page).
2. Ran the available checks: Django system check, migration check, backend tests, frontend build and lint.
3. Enumerated every URL route (about 320) and every model (90+) programmatically, with each route's permission classes and each model's link to a hospital.
4. Wrote probe tests that try to read Hospital B's data as a Hospital A admin.
5. Ran end-to-end workflow tests through the real API.
6. Checked every frontend API call against the backend resolver.
7. Browsed every staff and patient route of the production build against a seeded test backend.

Earlier reports in the repository root were treated as claims to verify, not as evidence. Several were wrong; for example, AI scribe draft generation was described as working, but its module could not even be imported.

## Environment finding

The project is on an iCloud-synced Desktop. Many `__pycache__`, log and virtualenv files were "dataless" (evicted to iCloud), so Python blocked while reading them. This caused the "Django check hangs" and "tests could not run" results in earlier audits.

Workarounds: run Python with `PYTHONPYCACHEPREFIX` pointing outside the project, and use a virtualenv outside iCloud.

## Baseline check results

| Check | Result |
|---|---|
| `manage.py check` | Passed (once the iCloud stall was avoided) |
| `makemigrations --check` | No changes |
| Backend tests | 155 run, all passed, 1 skipped |
| Frontend build | Passed |
| ESLint | 0 errors, 135 warnings. `no-undef` was switched off, which hid real crashes. |

## Critical findings (P0)

| # | Area | Finding |
|---|---|---|
| 1 | Tenant isolation | A Hospital A admin could list or read Hospital B rows through 25 endpoints, including AI transcripts and drafts, audit logs, allergies, medical records, prescription items, payments, invoice items, insurance claims, discharge summaries, plans and notes, wards, rooms and beds, lab results, MAR doses and consents. Causes: scoping fell back to "unscoped" when a model had no direct hospital field, and scoped some records through the patient's membership of any hospital. |
| 2 | Tenant isolation | Any staff user could create, edit or delete any hospital, department, ward, room or bed (permission was just "is staff"). |
| 3 | Tenant isolation | Writes did not check related objects, so a Hospital A user could attach records to a Hospital B visit. Issuing a queue token looked up the appointment without any scope. |
| 4 | RBAC | A role held in one hospital applied in every hospital; the staff profile's role also granted access. |
| 5 | Authentication | Staff OTP verify and resend accepted a bare `user_id`, so the SMS code alone signed a user in, without the password. `/api/auth/token/` issued tokens without any staff checks. There was no account lockout and no password reset. |
| 6 | Clinical safety (AI) | With no provider configured (the production default), speech-to-text and the LLM fell back to mock providers that return a fabricated transcript and findings (e.g. "probable migraine", BP 130/85). A doctor could approve these into the record. |
| 7 | Clinical safety (AI) | A draft's status, approver and final note could be set with a PATCH request, bypassing clinician approval. |
| 8 | Clinical safety (MAR) | Every scheduled dose was created with status "Administered", so the chart showed doses as given that no nurse had given. |
| 9 | Clinical safety (lab UI) | "Complete" set every test result to "Normal". The lab page also showed hard-coded patients. |
| 10 | Financial integrity | Totals were computed in float. Total, tax and status were writable by the client. Payments had no overpayment check, no idempotency, and could be edited or deleted. There were no refunds. |
| 11 | Privacy | nginx served `/media/` publicly, exposing patient documents and consultation audio to anyone with the link. `backend/db.sqlite3` was tracked in git. |
| 12 | Deployment | Production compose could not start: there was no Celery app, the JWT secret names didn't match, HL7/ABDM were enabled without their secrets, workers lacked required variables, and every container ran migrations. |
| 13 | Deployment | Nested nginx locations had no `proxy_pass`, so token refresh, password reset and every AI endpoint would 404 in production. nginx also reflected any CORS origin with credentials. |

## Broken functionality (P1)

| Area | Finding |
|---|---|
| AI scribe | `stt.py` ended with a stray "(End of file)" line and never imported. The STT result was read with `.get()` on a dataclass. Approve, review and reject queried a nonexistent `Doctor.user` field (500). The JSON stop-recording request returned 415, the UI uploaded a stale empty recording, and no first draft was ever created. |
| Queue | Issuing a token returned 500 after saving: it called a missing `NotificationEngine.send_notification`. |
| Lab | Create returned no id; `collect_sample` 500'd without a sample id; lab sub-resources were unreachable (shadowed by the root router). |
| Consent | Every write returned 501, and there were no models. |
| Documents | Download, preview and search never authenticated via JWT; `categories/` and `search/` routes were shadowed. |
| Audit | Nothing wrote `AuditLog`. Three of the four scheduled Celery tasks did not exist. |
| Frontend contract | 31 calls in `api.js` went to routes that do not exist (including the nurses list and all notification calls). |
| Frontend crashes | Home (undefined variables), Pharmacy (variable used before declaration), Permissions (missing import), and Reports (once connected). |
| Fake data / fake success | Nurses, Laboratory, Home, Queue, Appointments, Doctors, Patients, Reports, Compounder, the admin pages, the hospital lists and the prescription context used demo data or saved only in the browser. |
| Prescriptions | `dispensePrescription` always returned null. Rejected prescriptions were kept locally and cached with patient data in localStorage. |

## Missing at baseline

Proxy and delegated access, medical certificates, referrals, vaccination, ICD-10 terminology, drug interaction checking, OPD/IPD returns, purchase requisitions and approval, CSSD/laundry, ambulance, mortuary, phlebotomy, HR, feedback, invoice PDF export, voice-call workflow, and internationalisation (the language toggle did nothing).

The implementation history is in `IMPLEMENTATION_CHANGELOG.md`.
