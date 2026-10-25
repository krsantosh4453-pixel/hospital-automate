# Hospital Automate — Technical Audit Report

- **Date:** 2026-10-25
- **Branch audited:** `ui/redesign-2026-10-25` at `e2900f2` (working tree clean)
- **Type:** Read-only audit. No application code, configuration, database, dependencies or README were changed.
- **Auditor's environment:** macOS, Python 3.12.15 (`backend_env`), Node 26.7.0, npm 11.19.0

> **Most important limitation.** The project folder is on an iCloud-synced Desktop. Most files in `backend_env/` (11 MB on disk) and `node_modules/` (26 MB on disk) have been evicted to iCloud. Every Python and Node command stalled while those files downloaded on demand. The Django check, migration check, backend test suite, frontend build and lint were all started, but **none finished during the audit**. They are recorded as **BLOCKED**, not passed. **Update:** after a long stall, several of these did complete: backend suite 229 OK (1 skipped), migrations clean, lint 0 errors, npm audit clean. Only the frontend build is still unverified. See section H. Section H has the details. Every runtime claim in this report therefore rests on (a) code review done in this audit, or (b) earlier test evidence in `docs/TEST_REPORT.md`, which is labelled as such wherever it is used.

---

## A. Executive summary

| Measure | Result | Basis |
|---|---|---|
| **Implementation estimate** (code exists; partial rows count half) | **64.3%** | 116-row requirement checklist, re-assessed in this audit (section F) |
| **Verified completion** (behaviour backed by test evidence) | **31.3%** | Rows backed by automated tests documented on 2026-10-25 that this audit's code review did not contradict |
| Backend tests executed in this audit | **229 run, all pass (1 skipped)** | Completed late after an iCloud stall (section H). Lint passes (0 errors); the frontend build is still blocked |
| Frontend completion (provisional) | ~60% | Rows whose UI exists and calls the real API |
| Backend completion (provisional) | ~69% | Rows whose API and model exist |
| API integration (provisional) | ~80% of UI workflows reach real endpoints; ~70% work end to end | Page-by-page trace (section E) |
| Database readiness | Partial | Good tenancy columns, locks and constraints; unsafe cascade deletes; no UHID generation |
| Testing | 226 backend test methods found; **0 executed here**; no frontend tests | Section H |
| Security readiness | **Not ready** | 3 High findings confirmed by code review (section G) |
| Production readiness | **Not ready for real patient data** | Section I |
| Confidence | **Medium** for code-level findings; **low** for runtime behaviour | Runtime checks blocked |

**In one paragraph:** A large, genuinely wired system exists. 26 Django apps are registered, roughly 232 API endpoints are called from a single service layer, tenant isolation is designed to fail closed, and billing and stock use Decimal arithmetic, row locks and an append-only ledger. It is not ready for real patients. This audit found three serious problems that the earlier readiness report did not list:

- Staff can sign in through Google with **no password and no OTP**.
- **Deleting a patient in one hospital cascades into another hospital's clinical records.**
- **Email, SMS and WhatsApp notification "providers" are stubs that record a successful send but send nothing.**

On top of these, appointments and patients can be saved only in the browser, and the queue page only sees appointments booked from that same browser.

---

## B. README vs actual implementation

The requirement sources the project cites (`HMS_UI_Structure.md` and `Hospital_Management_FINAL_MultiHospital_AI.pdf`) are **not in the repository**. This audit used `docs/REQUIREMENTS_TRACEABILITY.md` (116 rows, derived from them) as the requirement list, and re-checked rows against the code.

| README claim | Finding | Status |
|---|---|---|
| React 19, Vite 8, Django 6.0, DRF, SimpleJWT | Installed versions match: Django 6.0.9, Vite 8.3.5 | Accurate |
| "Staff: password + SMS OTP" | Production settings enforce OTP on the password path. **`/api/auth/google/` issues staff tokens with neither** (G-01) | **Misleading** |
| "Hospital isolation is enforced server-side … tested across 67 models" | Detail views and writes check the role per hospital. **List calls without `X-Hospital-ID` use the union of roles across all hospitals** (G-04, suspected) | Partly accurate |
| "Notifications … SMS/WhatsApp need credentials" | Adding credentials would not make them work: the providers are TODO stubs that return `success=True` (G-03) | **Misleading** |
| "AI scribe … needs a real STT/LLM provider" | True. In addition, the `openai` and `anthropic` SDKs are **not in any requirements file**, so a real provider cannot run without a dependency change | Incomplete |
| "FHIR, HL7, ABDM code present, not mounted" | Confirmed: commented out in `backend/config/urls.py`. `interoperability/` (3,878 lines) and `ai_advanced/` are also unmounted | Accurate |
| "`python manage.py test` — 217 tests" | 226 test methods now exist; the redesign commits added suites. Not executed in this audit | Outdated |
| "Book appointment … Implemented" (traceability B7) | No booking UI in `src/pages/patient/PatientAppointments.jsx`; the API is read-only for patients (`backend/appointments/views.py:14`, `IsPatientReadOnly`) | **Unsupported** |
| "UHID per hospital — Implemented" (B2) | `PatientHospital.uhid` exists (`backend/patients/models.py:65`). No non-test code ever creates a membership or UHID; it is not unique per hospital | **Partial** |
| "Notifications bell not wired" (A21) | `src/components/Navbar.jsx:318,338` now lists notifications and marks them read | Outdated (now better) |
| Project structure lists `nginx.prod.conf`, `docs/API.md`, `pyproject.toml` | None of these files exist. The real files are `nginx.conf.template` and `docs/API_DOCUMENTATION.md` | Outdated |
| "CSP … nginx CSP" | nginx sends a CSP that allows `'unsafe-inline'` scripts. Django's `CSP_*` settings are dead: django-csp 4.0 ignores the legacy format (G-08) | Partly accurate |
| CI pipeline exists | It triggers on `main`/`develop`, but the default branch is `master`. Deploy jobs only `echo`. `pytest` has no config, so it would skip every `tests.py` (G-10) | **Misleading** |
| Footer "Documentation updated by audit: 2026-10-10" | The header says 2026-10-25 | Inconsistent |

---

## C. Frontend audit

There are 33 routes in `src/App.jsx` (25 staff, 8 patient), plus login and registration. One API layer: `src/services/api.js` (2,022 lines, about 232 endpoint URLs). There are no mock or demo markers in the pages; `src/utils/demoData.js` only *removes* old demo rows. Pages are loaded statically, with no code-splitting.

| Status | Pages / workflows | Evidence |
|---|---|---|
| **Implemented, wired to API (unverified at runtime here)** | Home, Patients, Doctors, Consultation, Prescriptions, Pharmacy, Laboratory, Nurses (notes, assessments, MAR), IPD (admit, bed, discharge summary, finalize, discharge), Emergency (triage, vitals, orders, meds, refer, discharge), Blood bank (requests), Billing (invoices, payments), Inventory (medicines, stock adjust), AI Scribe, Reports, Admin Users / Departments / Hospitals, all 8 patient pages, Navbar notifications | Page → `api.*` map built in this audit |
| **Partial** | Billing: no refund action. Inventory: suppliers, POs and GRNs are list-only. Blood bank: no transactions UI. Patient consent: the share access log is never shown (`api.consent.shares.accessLog` unused). Queue: waiting-time `estimates`, `acknowledge` and `noShow` unused | Unused API methods |
| **Broken / unsafe integration** | **Queue token generation** only considers appointments stored in this browser's `localStorage` (`src/pages/Queue.jsx:104-111`). An appointment booked on another computer cannot get a token from this screen, and local "T-00x" numbers are mixed with server tokens (`Queue.jsx:145-178`) | G-05 |
| **Local-only fallback (data integrity risk)** | Appointments and Patients save to `localStorage` when a request fails **or times out** (8 s default, `src/services/api.js:121`): "Saved on this device only" (`src/pages/Appointments.jsx:430-441`, `src/pages/Patients.jsx:282-297`). These records never sync, and a timed-out request that actually succeeded creates a duplicate | G-06 |
| **Static by design** | Settings (browser-only preferences), Permissions (read-only matrix), Roles | Code review |
| **Missing** | Patient self-booking; audit log viewer; invoice and lab-result print/PDF; breadcrumbs; patient context strip | Code review |
| **Dead code** | `BedStatus.jsx`, `EmergencyStatus.jsx`, `RecentPatients.jsx`, `AppointmentList.jsx` are never imported | grep |
| **Dev-only bypass** | "Development access (OTP bypassed)" exists only when `import.meta.env.DEV` is true (`src/assets/context/AuthContext.jsx:7-18`). It holds no tokens, and the server still requires auth. Acceptable | Code review |
| Hindi / English | Navigation and the patient menu only; page bodies are English | Traceability A17; not re-run |
| Build / lint | **BLOCKED** (section H) | — |

---

## D. Backend audit

**Registered and mounted:** users, patients, home, doctors, appointments, nurses, compounder, pharmacy, laboratory, hospital, encounters, clinical, ipd, emergency, billing, bloodbank, notifications, audit, procurement, ai_scribe, reports, consent. `documents` is mounted as views only; its model lives in `patients`.

**Present but not mounted or installed:** fhir, hl7, abdm, interoperability, ai_advanced.

Strengths confirmed by code review:

- Default `IsAuthenticated` permission, JSON-only renderer and throttling: `backend/config/settings/base.py:194-230`.
- `HospitalScopedViewSet` fails closed when no owning-hospital path exists, checks every related object on write, and audits old → new values on update: `backend/users/viewsets.py:86-263`.
- Per-hospital role resolution: `backend/users/permissions.py:119-140`. Object-level role check: `permissions.py:249-258`.
- Billing and pharmacy integrity: `select_for_update` and `transaction.atomic` in `backend/billing/services.py:85-124` and `backend/pharmacy/views.py:59-166`. Payments and sales are append-only (`http_method_names` restricted).
- Queue tokens are unique on `(hospital, token_date, token_number)` (`backend/encounters/models.py:178`).
- OTPs use `secrets`, are stored hashed, have an attempt limit and are compared with `hmac.compare_digest` (`backend/users/patient_auth.py:180-243`).
- Production settings refuse to start without secrets, and set HSTS, secure cookies and RS256 JWT (`backend/config/settings/production.py`).

Problems:

| Area | Finding | Evidence |
|---|---|---|
| Auth | Google login gives staff full tokens without password or OTP | G-01 |
| Deletion | Hard deletes everywhere. Patient delete cascades into every hospital's clinical rows | G-02 |
| Notifications | SMS, WhatsApp, Voice and Email providers are stubs that report success; message bodies are logged at INFO | G-03 |
| RBAC on lists | Roles are unioned across hospitals when no hospital header is sent | G-04 (suspected) |
| UHID | Never generated; not unique per hospital | `backend/patients/models.py:65-70`; no creator outside tests |
| Patient booking | Patients cannot create appointments | `backend/appointments/views.py:14` |
| AI providers | Real OpenAI/Anthropic/Google classes exist, but their SDKs are not in the requirements | `backend/ai_scribe/services/llm.py:222`, `stt.py:245` |
| Async work | Notifications are sent synchronously (`backend/notifications/services/engine.py:230`, TODO) | Code review |
| Dead config | Django CSP settings ignored; `STATICFILES_STORAGE` removed in Django 5.1+, so WhiteNoise compression is inactive; no WhiteNoise middleware | G-08 |

---

## E. API integration matrix (major workflows)

Request chain: page → `api.js` → Vite proxy / nginx `/api/` → DRF router or app `urls.py` → viewset → serializer/service → DB. Auth is a Bearer JWT from `localStorage`, with a single-flight refresh on 401 (`src/services/api.js:63-147`) and the `X-Hospital-ID` header taken from the selected hospital. No endpoint mismatches were found by inspection. `security_tests/test_frontend_contract.py` asserts every URL resolves, but it was **not executed here**.

| Frontend action | API function | Method / endpoint | Backend handler | Persistence | Test evidence | Status |
|---|---|---|---|---|---|---|
| Staff sign-in + OTP | `auth.staffLoginStartOtp`, `staffOtpVerify` | POST `/api/auth/staff/login/otp/start/`, `/verify/` | `users/views.py` | User / blacklist | `security_tests/test_auth.py` (prior) | Implemented; bypassable via Google (G-01) |
| Register patient | `patients.create` | POST `/api/patients/` | `PatientViewSet` | Patient (no UHID) | `test_e2e_workflows` (prior) | Partial (local fallback, no UHID) |
| Book appointment (staff) | `appointments.create` | POST `/api/appointments/` | `AppointmentViewSet` | Appointment + localStorage copy | appointments tests (prior) | Partial (G-06) |
| Book appointment (patient) | — | — | read-only for patients | — | — | **Missing** |
| Issue queue token | `queue.issue` | POST `/api/encounters/queue-tokens/issue/` | encounters views | Visit + QueueToken | `test_e2e_workflows` (prior) | **Broken in UI** (G-05) |
| Call / skip / complete | `queue.call/skip/complete/callNext` | POST actions | encounters | QueueToken | encounters tests (prior) | Implemented |
| Consultation | `clinical.vitals/diagnoses/notes/serviceOrders` CRUD | `/api/clinical/*` | clinical viewsets | Rows (hard delete) | prior tests | Implemented |
| Prescription → dispense | `prescriptions.*`, `pharmacy.sales` | `/api/clinical/prescriptions/`, `/api/pharmacy-sales/` | `PrescriptionViewSet`, `SaleViewSet` | Sale + StockTransaction (atomic) | `test_financial_integrity` (prior) | Implemented |
| Lab workflow | `laboratory.tests[action]` | POST `/api/laboratory/{id}/collect/ … release/` | `LabTestViewSet` actions | LabTest status | `test_e2e_workflows` (prior) | Implemented |
| IPD admit → discharge | `ipd.admissions.*`, `dischargeSummaries.finalize` | `/api/ipd/*` | ipd viewsets | Admission, BedAllocation | `test_e2e_workflows` (prior) | Implemented |
| MAR administer | `nurses.marAdministrations.administer` | POST `/api/nurses/mar-administrations/{id}/administer/` | nurses | MAR row | `test_mar_safety` (prior) | Implemented |
| Invoice / payment | `billing.invoices.*`, `billing.payments.create` | `/api/billing/*` | billing services | Decimal, locked | `test_financial_integrity` (prior) | Implemented |
| Refund | — (not in UI) | POST `/api/billing/invoices/{id}/refund/` | `InvoiceViewSet` | Payment row | prior | API only |
| Procurement PO / GRN create | — (list only in UI) | `/api/procurement/*` | procurement | — | 36 procurement tests (prior) | API only |
| AI scribe draft → approve | `aiScribe.drafts.generate/approve` | `/api/ai/*` | ai_scribe | Draft → ClinicalNote | `test_ai_scribe_safety` (prior) | Implemented; no real provider |
| Consent share / revoke | `consent.shares.*` | `/api/consent/*` | consent | Share + access log | `test_consent_sharing` (prior) | Implemented |
| Documents | `patients.documents` | `/api/patients/{id}/documents/`, `/api/documents/{id}/download/` | patients, documents | Private file, audited | `test_documents` (prior) | Implemented |
| Notifications bell | `notifications.list/markRead` | `/api/notifications/notifications/` | `NotificationViewSet` | In-app | `test_notifications` (prior) | Implemented (in-app only) |
| Reports | `reports.dashboard` | `/api/reports/…` | reports services | Read | prior | Implemented |

"(prior)" = the test exists and `docs/TEST_REPORT.md` records it passing on 2026-10-25 before the UI-redesign commits. Not re-run in this audit.

---

## F. Module completion matrix

**Method.** Denominator: the 116 rows of `docs/REQUIREMENTS_TRACEABILITY.md`, minus 1 N/A = **115**. Each row is scored once:

| Row status | Implementation score | Verified score |
|---|---|---|
| VERIFIED | 1 | 1 |
| IMPLEMENTED | 1 | 0 |
| PARTIAL | 0.5 | 0 |
| MISSING / BROKEN / PLACEHOLDER | 0 | 0 |
| BLOCKED | 0 | 0 |

**Changes this audit made to the prior statuses, with reasons:**

| Row | Prior → now | Reason |
|---|---|---|
| A3 Tenancy / isolation | V → P | List role union (G-04) and cross-hospital cascade delete (G-02) |
| A5 Staff SMS OTP | I → P | Google login bypass (G-01) |
| A8, B6, E1 | V → I | Evidence was a browser pass only; not re-run, and the UI has been redesigned since |
| A21 Notification bell | P → I | Now wired (`Navbar.jsx:318`) |
| B2 UHID | I → P | Never generated; not unique |
| B7 Patient booking | I → M | No UI; API read-only for patients |
| C3 Appointment → token | V → P | Backend tested; UI broken (G-05) |
| H3 Refunds | V → P | No UI |
| I1 Procurement | I → P | UI list-only |

**Resulting totals:** 36 VERIFIED, 24 IMPLEMENTED, 28 PARTIAL, 24 MISSING, 3 BLOCKED, 1 N/A (116 rows).

- **Implementation estimate** = (36 + 24 + 0.5 × 28) / 115 = 74 / 115 = **64.3%**
- **Verified completion** = 36 / 115 = **31.3%**. This relies on prior test runs; **0%** was executed in this audit.

| Module (area) | Rows | V | I | P | M | Blocked / NA | Impl. % | Verified % | Main missing work | Priority |
|---|---|---|---|---|---|---|---|---|---|---|
| A. Platform, auth, tenancy | 21 | 7 | 5 | 6 | 3 | – | 71% | 33% | Google OTP bypass, list RBAC, audit viewer, breadcrumbs, context strip, UHID search | P0 |
| B. Registration and portal | 15 | 4 | 2 | 6 | 3 | – | 60% | 27% | UHID generation, demographics, emergency contact, patient booking, proxy access | P1 |
| C. Appointments / OPD | 8 | 2 | 4 | 2 | 0 | – | 88% | 25% | Queue UI using server appointments; nurse-seen state | P1 |
| D. Consultation / EMR | 15 | 4 | 3 | 3 | 5 | – | 57% | 27% | ICD-10 search, structured EMR, certificate, referral, vaccination | P2 |
| E. Nursing / IPD | 12 | 4 | 5 | 3 | 0 | – | 88% | 33% | Discharge checklist, discharge-to-billing link | P1 |
| F. Pharmacy | 8 | 4 | 0 | 1 | 3 | – | 56% | 50% | **Drug-interaction alerts**, returns, substitutes | P1 |
| G. Lab / radiology | 5 | 2 | 0 | 2 | 1 | – | 60% | 40% | Result print/export, radiology | P2 |
| H. Billing | 8 | 3 | 1 | 2 | 2 | – | 63% | 38% | Refund UI, advance payments, invoice PDF, IPD billing | P1 |
| I. Supply chain | 6 | 1 | 1 | 1 | 3 | – | 42% | 17% | PO/GRN UI, requisition, returns, CSSD | P2 |
| J. Emergency / other | 7 | 1 | 3 | 1 | 2 | – | 64% | 14% | Remaining ER actions, ambulance, OT, HR | P2 |
| K. AI / notifications / ML | 11 | 4 | 0 | 1 | 2 | 3 B, 1 NA | 45% | 40% | Real notification providers, AI SDKs, voice, ABDM / FHIR | P1 |
| **Total** | **116** | **36** | **24** | **28** | **24** | **3 B, 1 NA** | **64.3%** | **31.3%** | | |

Module percentages use the module's own rows (N/A excluded). The overall figure is computed from all rows, not by averaging modules. Row-level detail is in `docs/REQUIREMENTS_TRACEABILITY.md`, with the changes above.

**Frontend / backend split (provisional, low confidence).** About 6 rows have a backend but no UI (A15, B14, B15, C6, H3, I1); a few others are partial on the UI side.

- Backend ≈ (74 + 5) / 115 ≈ **69%**
- Frontend ≈ (74 − 5) / 115 ≈ **60%**

These are estimates, not row-by-row measurements.

---

## G. Critical bugs and security findings

"Confirmed (code)" means the defect is visible directly in the source. "Suspected" means it is strongly indicated by code but was not executed.

Probe tests for G-01, G-02 and G-04 were written in the audit's scratchpad copy (`audit_probes/test_probes.py`, not in the project) but could not run because of the iCloud block. They are listed under "Verification needed".

### G-01 — High — Staff Google sign-in bypasses password and SMS OTP

- **Status:** Confirmed (code). **FIXED after the audit (P0-1, uncommitted):** `google_login` now returns 403 for any account with a staff profile. Three tests in `security_tests/test_auth.py` cover it, and the full suite passes.
- **Where:** `backend/users/views.py:79-133` (`google_login`). It links any verified Google identity to an existing `User` whose email matches (`User.objects.filter(email__iexact=email)`, ~line 109). If that user is active staff, it returns `_auth_response(user)` with staff tokens (lines 130-134). `STAFF_LOGIN_REQUIRE_OTP` is never consulted.
- **Impact:** Anyone who controls a Google account with a staff member's email address gets full staff access with no password or OTP. Production requires `GOOGLE_CLIENT_ID`, so the route is live.
- **Fix:** Refuse staff accounts on `/api/auth/google/`. Alternatively, return an OTP challenge like the password path. Do not auto-link by email to staff users.
- **Verify:** Run the probe `StaffGoogleLoginProbe`; add it to `security_tests/test_auth.py`.

### G-02 — High — Deleting a patient in Hospital A deletes Hospital B's clinical records

- **Status:** **Confirmed at runtime.** In probe `PatientDeleteCascadeProbe` (scratchpad copy, in-memory DB, synthetic data), a Hospital A receptionist's `DELETE /api/patients/{id}/` returned **204** and Hospital B's `Visit` row was gone.
- **Where:** `backend/patients/views.py:30`. `DELETE` is allowed to Receptionist, Doctor, Nurse and Admin of the patient's primary hospital. Clinical FKs to Patient are `on_delete=CASCADE`: `clinical/models.py:30-32,144-146,183-185`; encounters (4), ipd (2), laboratory (2), billing (4), nurses (11). A patient is a shared identity across hospitals (`users/viewsets.py:24-27`).
- **Impact:** Irreversible loss of another hospital's visits, prescriptions, lab results and invoices. Medico-legal records can be destroyed by a front-desk role. The deletion is audited only as "patient.delete".
- **Fix:** Disallow patient hard delete (use an inactive status), or restrict it to the platform admin with a PROTECT check. Switch clinical FKs to `PROTECT`. Add soft delete for clinical rows.
- **Verify:** Run the probe `PatientDeleteCascadeProbe`.

### G-03 — High — Email / SMS / WhatsApp / Voice notifications report success but send nothing

- **Status:** Confirmed (code).
- **Where:** `backend/notifications/services/providers.py:176-203` (SMS), WhatsApp, Voice, and Email (~lines 285-310). Each has `# TODO: Implement actual … sending`, logs "Would send …", and returns `success=True`.
- **Email:** `EmailProvider.is_configured()` is true whenever `EMAIL_HOST` is set, and production defaults it to `smtp.gmail.com` (`config/settings/production.py`). So every consented email notification is logged as delivered and never sent.
- **Also:** The message body is logged at INFO, and production logs INFO to a file. This puts patient message content in logs.
- **Impact:** Patients miss queue calls and results; delivery logs are false; PHI ends up in logs.
- **Fix:** Implement the providers (the Twilio SDK is already a dependency) or make them return `success=False`. Log ids, not content.
- **Verify:** Unit test that an unimplemented provider never reports success.

### G-04 — High — List endpoints use roles from all hospitals when no hospital is sent

- **Status:** **Confirmed at runtime.** In probe `ListWithoutHospitalHeaderProbe`, a user who is Doctor in A and Receptionist in B called `GET /api/clinical/vitals/` with no `X-Hospital-ID`. The response was **200** and included Hospital B's vital-sign row. A receptionist role should not see clinical data.
- **Where:** `backend/users/permissions.py:232-247`. When `hospital_id` is None, `get_user_roles(user, None)` returns the roles of every membership. `users/viewsets.py:120-126,157-168` then lists rows from all of the user's hospitals.
- **Example:** A Doctor in A who is a Receptionist in B calls `GET /api/clinical/vitals/` without `X-Hospital-ID` and receives B's clinical rows. Object-level checks protect detail and update, not list. Existing tests only cover writes and detail views (`security_tests/test_rbac_and_writes.py:39-75`).
- **Fix:** Require an acting hospital on scoped list endpoints, or filter the list per hospital by the role held there.
- **Verify:** Run the probe `ListWithoutHospitalHeaderProbe`.

### G-05 — High (functional) — Queue page cannot issue tokens for appointments booked elsewhere

- **Status:** Confirmed (code).
- **Where:** `src/pages/Queue.jsx:104-111`. `issueableAppointments` comes from `useAppointment()`, which is `localStorage` "hospitalAppointments" (`src/assets/context/AppointmentContext.jsx:7-27`). The server appointment list is never loaded into it. `Queue.jsx:145-178` merges local "T-00x" numbers with server tokens.
- **Impact:** At reception desk B, "Generate token" reports "No booked appointment is waiting" for appointments booked at desk A. Token numbers can be confusing.
- **Fix:** Load appointments from `api.appointments.list` on the queue page and drop the local context.
- **Verify:** Browser test with two browser profiles.

### G-06 — Medium — Local-only saves and PHI kept in `localStorage`

- **Status:** Confirmed (code).
- **Where:** `src/pages/Appointments.jsx:430-441` and `src/pages/Patients.jsx:282-297` save to `localStorage` on network error **or timeout**. The default timeout is 8 s (`src/services/api.js:121`, `isNetworkError` is also set for timeouts).
- **What is kept:** "hospitalAppointments", "hospitalPatients" and "patientData" hold names, phones, village and reason.
- **Not cleared on logout:** `failAuthSession` (`api.js:104-112`) and `clearSessionState` (`AuthContext.jsx:50-58`) do not remove them.
- **Impact:** Duplicate or never-synced bookings; PHI left on shared reception PCs for the next user.
- **Fix:** Remove the offline fallback (or build a real sync queue), and clear all PHI keys on logout.

### G-07 — High (open, known) — Tokens in `localStorage` with `'unsafe-inline'` scripts allowed in CSP

- **Where:** `src/services/api.js:3-22`; `nginx.conf.template:121`.
- **Status:** Already recorded in `docs/SECURITY_AUDIT.md`; still open.

### G-08 — Medium — Django security config silently inactive

- **Where:** `backend/config/settings/production.py:53-69` uses the pre-4.0 `CSP_*` settings, but django-csp **4.0** is installed (`requirements-lock.txt:27`).
- **Effect:** With no `CONTENT_SECURITY_POLICY` setting, django-csp 4.0 emits **no** CSP header. Because `csp` is not in `INSTALLED_APPS`, its `csp.E001` warning never fires either. The only CSP is nginx's weaker one.
- **Also:** `STATICFILES_STORAGE` (removed in Django 5.1) is ignored, and WhiteNoise middleware is not installed.
- **Fix:** Convert to `CONTENT_SECURITY_POLICY = {...}`; use `STORAGES`.

### G-09 — Medium — Rate limits keyed on a client-supplied `X-Forwarded-For`

- **Where:** `backend/config/middleware/ratelimit.py:144-149` takes the first XFF value. Clients can rotate it to defeat the per-IP login/OTP limits.
- **Mitigation already present:** nginx `limit_req` on `$binary_remote_addr` and account lockout.
- **Fix:** Trust only the proxy-appended address, or use `REMOTE_ADDR` behind nginx.

### G-10 — Medium — CI does not protect the main branch

- **Where:** `.github/workflows/ci.yml` triggers on `main` and `develop`, but the repository uses `master`. `python -m pytest` runs with no `pytest.ini` / `python_files`, so all 18 app `tests.py` files (about 160 tests) would be skipped. Deploy jobs only `echo`. Bandit and npm audit end with `|| true`.
- **Fix:** Trigger on `master`; run `manage.py test` or configure pytest; remove `|| true`.

### G-11 — High (open, known) — `backend/db.sqlite3` in git history

- **Where:** Present in commits `1299a51`, `e58280c`, `c131b6e`, `835cfde`, `2a753d1` (`git log --all -- backend/db.sqlite3`). `.env` was never committed; only the example env files are tracked.
- **Fix:** Purge with `git filter-repo` before sharing the repository; rotate anything it contained.

### G-12 — Medium — Hard deletes on clinical records

- **Where:** Vitals, diagnoses, notes and orders can be deleted by Doctor or Nurse roles (`backend/clinical/views.py:49-130`; the Consultation page calls `.delete`). The deletion is audited, but the data is gone.
- **Fix:** Soft delete or "entered in error" status.

### G-14 — Medium — Report templates writable by any signed-in user, across hospitals

- **Status:** Confirmed (code).
- **Where:** `backend/reports/views.py:614-625`. `ReportTemplateViewSet` is a plain `ModelViewSet` with `IsAuthenticated` only and `queryset = ReportTemplate.objects.all()`. Mounted at `/api/reports/templates/`.
- **Impact:** Any authenticated account, including a patient login, can list, edit and delete every template platform-wide.
- **Related problems:**
  - `SavedReportViewSet` and `ScheduledReportViewSet` (`reports/views.py:628-663`) check the hospital only on create. A PATCH can change `hospital` to one the user does not belong to.
  - A request without `hospital` raises `int(None)`, which returns a 500.
  - None of these views check roles.
- **Fix:** Admin/Manager write permission; tenant-check on update; validate `hospital` in the serializer. Alternatively, move these views to `HospitalScopedViewSet`.

### G-13 — Low — Other observations

- UHID not unique per hospital, yet used as a login identifier (`backend/users/patient_auth.py:295`).
- Email OTP hash is unsalted SHA-256 (short TTL limits the risk).
- Admin role is included in every clinical permission class, so an Admin can diagnose or verify lab results.
- Patient email/password login for a user who is also staff issues a token that the API treats as staff (`users/views.py:926-955` with `viewsets.py:145-147`). Suspected; OTP bypass for dual-role users.
- Dev logging prints SQL parameters (known).

- The OpenAPI schema, Swagger UI and ReDoc are public (`backend/config/schema.py:21,30,45`). This exposes the full API surface; consider restricting them in production.

**Not found:** raw SQL injection paths, `eval`/pickle deserialization, or tracked secrets. `AllowAny` appears only on the auth views (`users/views.py`), the schema views, and the unmounted `hl7` app. Plain (non-scoped) viewsets are `HospitalViewSet` (custom permissions, tested), `OTPVerificationViewSet` (superuser only) and the `reports` viewsets (G-14).

---

## H. Testing results

| Command (actually executed) | Result |
|---|---|
| `backend_env/bin/python manage.py check --settings=config.settings.testing` (in the project) | Stalled for 6 minutes at 0% CPU on iCloud reads; stopped. **BLOCKED** |
| Same, on a scratchpad copy of the code, using `backend_env` | Still importing site-packages from iCloud after ~45 minutes. **BLOCKED** |
| `manage.py makemigrations --check --dry-run` (project folder) | **No changes detected** (exit 0) ✅ — finished after the report was first written |
| `manage.py test --settings=config.settings.testing --noinput` (project folder) | **Ran 229 tests in 161 s — OK (skipped=1)**, exit 0 ✅. Wall time 47 min, almost all of it iCloud download. The run included the P0-1 fix (3 new tests) and some uncommitted edits by another author in the working tree, so it is not a pure run of `e2900f2` |
| `npx vite build --outDir <scratchpad>` (first run) | Bundling started; stalled; stopped (exit 143). **BLOCKED** |
| `npx vite build` (second run) | Reached "transforming…" after 17 s of plugin time; not finished. **BLOCKED** |
| `npx eslint -c eslint.config.cjs .` (second run) | **0 errors, 68 warnings** (exit 0) ✅. Mostly unused variables; the earlier report said 124 warnings |
| `npm audit` (including dev dependencies) | **found 0 vulnerabilities** ✅ |
| `npm audit --omit=dev` | **found 0 vulnerabilities** (exit 0) ✅ |
| `git log --all -- backend/db.sqlite3` | 5 commits contain it (G-11) |
| Static grep / code review | Basis of sections C–G |

**Tests discovered:** 226 backend test methods.

- App `tests.py` and `users/test_stage*.py`: 158.
- `backend/security_tests/` (17 files): 68, including new `test_home_stats`, `test_bloodbank_flow`, `test_emergency_flow`.

**Update (same day, after the first version of this report):**

- The full backend suite completed: **229 run, 228 passed, 1 skipped, 0 failed**. This is the pre-existing 226 plus 3 new P0-1 tests.
- A separate run of the auth suites (49 tests) also passed.
- The skipped test is the known `nurses` MAR test.
- Lint passes: 0 errors, 68 warnings.
- Still blocked: the frontend production build (stopped after 24 min stalled in "transforming…") and `manage.py check --deploy`.
- A run on the scratchpad copy that also included the audit probes ran 232 tests: **2 failed, both audit probes**, which confirms G-02 and G-04 at runtime. Every project test passed.

**Prior evidence (not re-verified):** `docs/TEST_REPORT.md` reports 217 run, 216 pass, 1 skipped on SQLite and PostgreSQL 16 on 2026-10-25. That was before five UI-redesign commits, which also changed backend code ("fix broken discharge and ER workflows", "fix lab edit").

**Missing tests:**

- Google login for staff
- Patient delete cascade
- List RBAC without a hospital header
- Notification provider truthfulness
- Any frontend unit or E2E test (none exists)
- Concurrency under real parallel load
- Docker / nginx runtime

**To unblock:** move the project out of iCloud (or turn off "Optimize Mac Storage" for Desktop), then run:

```bash
cd backend && ../backend_env/bin/python manage.py test --settings=config.settings.testing
```

```bash
npm run build && npm run lint
```

---

## I. Production readiness checklist

| Requirement | Status | Note |
|---|---|---|
| DEBUG off, secrets from env, fail closed | PASS (code) | `production.py` |
| HTTPS, HSTS, secure cookies | PARTIAL | Configured; never run behind nginx |
| Staff MFA enforced | PASS (fixed) | G-01 fixed by P0-1 with 3 tests, uncommitted |
| Tenant isolation | **FAIL** | G-02 and G-04 confirmed at runtime |
| Token storage | FAIL (open) | G-07 |
| CSP | PARTIAL | G-08 |
| Rate limiting / brute force | PARTIAL | G-09; lockout present |
| Data integrity of clinical records | **FAIL** | G-02, G-12 |
| Frontend data consistency | FAIL | G-05, G-06 |
| Notifications deliver what they log | **FAIL** | G-03 |
| AI scribe with real provider | NOT VERIFIED | SDKs missing |
| Migrations consistent with models | PASS | `makemigrations --check`: no changes |
| Backend tests pass | PASS | 229 run, OK, 1 skipped (working tree incl. P0-1 fix) |
| Frontend lint | PASS | 0 errors, 68 warnings |
| Frontend build | NOT VERIFIED | Blocked by iCloud |
| Dependency vulnerabilities | PASS (npm) / NOT VERIFIED (pip) | `npm audit` clean; `pip-audit` not run |
| CI gating on `master` | FAIL | G-10 |
| Automated deployment / rollback | FAIL | Deploy jobs are `echo` stubs; rollback is documented only |
| Docker Compose / nginx runtime | NOT VERIFIED | Never started |
| Health checks | PARTIAL | `/health/`, `/live/`, `/ready/` exist; not run here |
| Backups and restore | PARTIAL | `backend/scripts/backup.py` exists; prior PostgreSQL test claimed; not re-run |
| Monitoring / error reporting | PARTIAL | `sentry-sdk` in production requirements; `MONITORING_ENABLED` defaults off; `/metrics` commented out |
| Logging without PHI | FAIL | G-03 message bodies at INFO |
| Performance | PARTIAL | Query-budget test exists; no code-splitting (single bundle); no load test |
| Repo hygiene | FAIL | G-11 |
| Clinical safety sign-off, pen test, DPDP assessment | FAIL (not done) | Organisational |

---

## J. Remaining work and roadmap

Effort assumes one developer who knows the codebase, and excludes review and clinical sign-off time.

### P0 — release blockers

| ID | Problem | Files | Change | Depends on | Acceptance / how to test | Effort |
|---|---|---|---|---|---|---|
| P0-1 | Staff Google login skips password and OTP (G-01) | `backend/users/views.py` | Reject staff on `/auth/google/`, or issue an OTP challenge; stop auto-linking staff by email | — | New test: verified Google identity for a staff email returns no tokens | 0.5 d |
| P0-2 | Cross-hospital cascade delete (G-02, G-12) | `patients/views.py`, clinical / encounters / ipd / lab / billing / nurses `models.py` + migrations | Block patient delete (inactive status); FKs to `PROTECT`; soft delete for clinical rows | Migration plan | Probe test passes; delete of a patient with records returns 409 | 2–3 d |
| P0-3 | Fake notification success, PHI in logs (G-03) | `notifications/services/providers.py` | Return failure until implemented, then implement Twilio SMS/WhatsApp and SMTP email; log ids only | Credentials for real sends | Unit test: unconfigured or unimplemented → `success=False`; staging send | 1 d stub fix; 3–4 d real providers |
| P0-4 | Unblock and re-run all checks | Environment | Move repo out of iCloud; run check, makemigrations, tests, build, lint, `pip-audit` | — | All green on the current branch | 0.5 d |
| P0-5 | Purge `db.sqlite3` from history (G-11) | git | `git filter-repo`; force-push with team coordination | Team agreement | `git log --all -- backend/db.sqlite3` is empty | 0.5 d |

### P1 — essential functionality and integration

| ID | Problem | Files | Change | Acceptance / how to test | Effort |
|---|---|---|---|---|---|
| P1-1 | Queue uses local appointments (G-05) | `src/pages/Queue.jsx`, `AppointmentContext.jsx` | Load server appointments; remove local tokens | Two browsers: book on one, issue token on the other | 1 d |
| P1-2 | Local-only saves, PHI left in browser (G-06) | `Appointments.jsx`, `Patients.jsx`, `PatientContext.jsx`, `api.js` | Remove offline save; clear keys on logout; idempotency key on create | Network off → error, nothing saved; logout clears storage | 1–1.5 d |
| P1-3 | List RBAC across hospitals (G-04) | `users/permissions.py`, `users/viewsets.py` | Require acting hospital or filter per role | Probe passes | 1 d |
| P1-4 | Tokens in `localStorage` (G-07) | `api.js`, auth views, settings | httpOnly cookie + CSRF; strict CSP | XSS cannot read the token; login, refresh and logout still work | 3–4 d |
| P1-5 | Dead CSP / static config (G-08) | `production.py` | `CONTENT_SECURITY_POLICY`, `STORAGES`, WhiteNoise middleware | Response has a CSP header; `check --deploy` clean | 0.5 d |
| P1-6 | CI not gating (G-10) | `.github/workflows/ci.yml` | `master` trigger; run all tests; fail on audit findings | CI red on a failing test | 0.5 d |
| P1-7 | UHID never generated | `patients/serializers.py`, models | Create `PatientHospital` with a unique UHID on registration; `unique_together(hospital, uhid)` | Test: two registrations → distinct UHIDs; search by UHID | 1 d |
| P1-8 | Patient self-booking missing | appointments views, `PatientAppointments.jsx` | Patient create with own-patient constraint; booking UI | Test: patient books own appointment, not another patient's | 2 d |
| P1-9 | Refund and procurement UI missing | `billing.jsx`, `inventory.jsx` | Wire existing APIs | Refund visible in balance; PO → GRN updates stock | 2–3 d |
| P1-10 | Drug-interaction alerts absent | pharmacy / clinical | Licensed drug database or explicit, documented exclusion with clinical sign-off | Clinical safety acceptance | 5–10 d (depends on data source) |
| P1-11 | Real AI provider | requirements, ai_scribe | Add the chosen SDK; staging run | Draft → approval with a real provider | 1–2 d plus provider setup |
| P1-12 | Docker / nginx staging rehearsal | compose, nginx | Run `docs/DEPLOYMENT.md` steps 1–8 | TLS, `/media/` 404, `/health/ready/` | 1–2 d |

### P2 — reliability, testing, maintainability

| ID | Task | Effort |
|---|---|---|
| P2-1 | Frontend test harness (Vitest + Playwright) for login, booking, queue, consultation, billing | 4–5 d |
| P2-2 | XFF-safe rate limiting (G-09) | 0.5 d |
| P2-3 | Async notifications via Celery with retry | 2 d |
| P2-4 | Code-splitting (`React.lazy`) for the single bundle | 1 d |
| P2-5 | Remove dead components; mount or delete `ai_advanced` / `interoperability` | 0.5 d |
| P2-6 | Update README and traceability with this audit's corrections | 0.5 d |
| P2-7 | Read auditing for clinical detail views; break-glass policy | 2–3 d |
| P2-8 | ICD-10 search, structured EMR sections, result/invoice PDF | 6–8 d |

### P3 — enhancements

ABDM, FHIR and HL7 mounting after review; voice-call workflow; CSSD, OT, ambulance, HR modules; full Hindi translation of page bodies; proxy/caregiver access. Each is several days to weeks.

**Estimated remaining effort:**

- P0 + P1, excluding the drug database: about **25–35 developer-days**.
- Adding P2: about **45–55 developer-days**.

This is a realistic range, not a schedule. It assumes the runtime checks in P0-4 pass without large surprises.

---

## K. Final recommendation

1. **Local demo?** Yes, with synthetic data only, once the environment is out of iCloud. Prior evidence says the core flows ran.
2. **Controlled staging?** Only after P0-1 to P0-4 and P1-1, P1-2 and P1-12. Use synthetic data and real provider credentials.
3. **Production with real patient data?** **No.** Blocked by the staff MFA bypass, cross-hospital deletion, false notification delivery, tokens in `localStorage`, unverified tests and build on the current commit, and the missing clinical safety sign-off and penetration test.
4. **Five most important tasks:** P0-1 (Google OTP bypass), P0-2 (cascade delete / soft delete), P0-3 (notification stubs), P0-4 (re-run all tests and the build on this commit), P1-1 + P1-2 (queue and local-only data).
5. **What to do first:** P0-4 (move the folder out of iCloud and get a real test/build result), then P0-1. P0-1 is half a day and closes the most dangerous hole.
6. **Areas needing more testing before they count as complete:** multi-hospital staff permissions; queue and appointments across devices; IPD discharge and ER flows (backend changed in the redesign commits after the last test run); AI scribe with a real provider; notifications; all frontend flows (no automated frontend tests exist); Docker / nginx production runtime.

---

### Evidence notes

- No patient data, secrets, `.env` contents or tokens were read or reproduced in this report. The local `.env` file exists but was not opened.
- Probe tests were written only to a scratchpad copy outside the project and were not executed.
- Line numbers are as of commit `e2900f2`.
