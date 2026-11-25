# Final end-to-end validation and remaining work

**Date:** 2026-11-25 · **Branch:** `ui/redesign-2026-10-25` at `7495be3` (Prompts 1–5 committed; Prompts 4–5 not pushed)
**Execution ID:** `FV55750` (final full run; earlier iterations FV51479–FV55226 only fixed the test script, never the app)
**Evidence:** `reports/e2e-evidence/final-validation/`:
- 29 screenshots;
- `state.json` (each step's result and facts);
- `db-verification.txt`;
- `discharge-replay.txt`.

**Test script:** `e2e/final-validation.spec.js` (new, untracked).

## How this was tested

- **Isolated backend:** the Playwright e2e backend (`config.settings.e2e`), which builds a fresh throwaway SQLite database on every run. Its seeded "Demo City Hospital" served only as the *other* hospital for isolation checks.
- **Fresh hospital:** the primary hospital, its staff, its patient and every record were created from scratch through the real browser UI.
- **Synthetic data only.** The development database was not touched.
- **Admin sign-up:** a synthetic `ADMIN_INVITE_CODE` was given to the e2e backend only, so a brand-new Hospital Admin could sign up.
- **Passwords:** generated per run and not recorded.
- **Nothing real was sent.** OTP codes came from the e2e console OTP log (no SMS). Payments are cash entries in the app.
- **Not called or configured:** Whisper, Twilio or any LLM.
- **No application code was changed.**

---

## 1. Executive summary

**The complete outpatient journey works end to end on a brand-new hospital.**

- **Setup:** Hospital Admin sign-up; hospital, department, ward and beds; price list; nine staff roles invited and onboarded.
- **Patient:** registration with UHID, then booking (with day-off, clash, reschedule and cancel rules).
- **Front desk and doctor:** reception token, then the doctor's consultation (allergy status, diagnosis, note, vitals).
- **Investigations:** lab with second-person verification; X-ray with image upload, validation and a signed report.
- **Pharmacy:** dispensing with stock and ledger.
- **Money:** billing that reconciles to the paisa with no duplicate charges; partial and full payments with receipts.
- **Portal:** the patient sees all of it after signing in again.
- **Security:** role access and hospital isolation held on every probe.

**What did not pass:**

| # | Item | Status |
|---|---|---|
| 1 | Completing an inpatient discharge from the browser | **Not achieved in the test.** Everything up to "Ready to complete" worked (checklist 4/4, summary signed, final bill ₹1,200.00 paid), but the final click sent no request. The same server call completes correctly when replayed. **Needs a manual check (P1).** |
| 2 | Nurse authorship | **Defect (P1).** Inviting a Nurse creates no Nurse profile, so ward observations are saved without a nurse: the doctor sees value, unit and time, but no name. |
| 3 | Date boundary, 00:00–05:30 India time | **Defect (P1).** Two backend tests fail only in this window, because some code compares the UTC date with the hospital's India date. This can create a second visit for a waiting patient and shows wrong "today" figures. |
| 4 | Lab Staff orders | **Limitation (P2).** Orders placed by Lab Staff can't be linked to the visit (Lab Staff can't list visits), so the lab charge goes on a separate bill. Doctor-placed orders link correctly. |

**Integrations on hold:** Whisper, Twilio (SMS/OTP) and the LLM are, as instructed. That leaves no real SMS delivery for OTP sign-in.

**Verdict: NOT READY FOR CONTROLLED PILOT** (see §8).

## 2. Complete workflow results

| Step | Workflow | Result | Evidence | Remaining issue |
|---|---|---|---|---|
| 1 | Hospital creation | **PASS** | `01-admin-signup.png`, `02-hospital-created.png`, `02-ward-created.png`; hospital id 2, code `SF5750`, active, accepts online registration | The setup wizard sometimes stays on "1. Hospital" with later steps disabled until reload (P3-1) |
| 2 | Staff account creation | **PASS** | `04-staff-invited.png`, `04-invite-accepted.png`. Admin, Doctor, Receptionist, Nurse, Compounder, Lab Staff ×2, Radiology Staff, Pharmacist and Billing Staff were invited by the Admin; each accepted the link, set a password, and signed in with the right role and hospital | Invited Nurse gets no Nurse profile (P1-2) |
| — | Price configuration | **PASS** | `03-price-list.png`: consultation ₹450.50, lab "Complete Blood Count" ₹320.25, X-ray "X-ray Chest PA" ₹610.75 and bed ₹1,200.00, entered in Billing → Price list; medicine ₹2.50 entered in Pharmacy | The Add Medicine form has no GST field, so stock is saved at 0% GST (P2-2, to confirm) |
| — | Role access | **PASS** | `state.json` → `accessMatrix`: every forbidden probe for 8 roles answered 403; another hospital's doctor got 403 | — |
| 3 | Patient registration | **PASS** | `07-patient-registered.png`. The form will not submit without a hospital or with mismatched passwords; duplicate account → 400; unknown hospital → 400 | Email/password sign-in needs a verified email (by design); otherwise patients rely on mobile OTP |
| 4 | UHID generation | **PASS** | `SF5750-2026-000001` on the dashboard (`07-patient-dashboard-uhid.png`), unchanged after signing in again; another patient's record → 404 | — |
| 5 | Appointment booking | **PASS** | `08-booked.png`, `08-history.png`; today 09:00 with the new doctor. Same slot again → 409. A second booking was moved 15:00→15:30 by the patient, then cancelled with a reason. With working days "Mon-Sat", Sunday offers 0 slots with the reason, and booking it → 400. The other hospital's doctor → 400 | Per-day limit is a policy question (BUG-008) |
| 6 | Reception and queue | **PASS** | `09-reception-patient.png`, `09-token-issued.png`. The patient was found with the UHID, the token issued and the patient Waiting; the receptionist got 403 on vitals, users and lab | — |
| 7 | Doctor consultation | **PASS** | `10-consultation-open.png`, `10-consultation-saved.png`. Called → In Consultation; allergy shown as **unknown** (never "No known allergies"); diagnosis J02.9, note and vitals (37.8 °C) persisted after reload; visit Completed | — |
| 8 | Nursing | **PARTIAL** | `17-nurse-vitals.png`, `17-doctor-sees-nurse-vitals.png`. The nurse recorded BP, pulse, SpO₂, respiratory rate and **100.4 °F**, stored with `temperature_unit: F`; the doctor's Consultation shows "100.4 °F" | **No nurse name** (P1-2). Nurses cannot record OPD vitals (MF-012, unchanged) |
| 9 | Laboratory | **PARTIAL** | `11-lab-released.png`. Lab Staff ordered CBC, then Collected → Dispatched → Received → Processing → Result Entered; self-verification → 403; a second Lab Staff verified and released; the doctor sees it; a pharmacist gets 403; charged once at ₹320.25 | A Lab Staff order has **no visit link**, so the charge is on its own bill (P2-1) |
| 10 | Radiology | **PASS** | `12-image-attached.png`, `12-report-signed.png`. The doctor ordered (only doctors may) and the order linked to the visit; Radiology Staff performed it; `.exe` refused, >50 MB refused, PNG attached; pharmacist → 403 on the image, doctor 200; report signed, re-sign → 400; charged once at the hospital's ₹610.75 | — |
| 11 | Pharmacy | **PASS** | `13-dispensed.png`. Search while typing had no page errors; RX-0001 dispensed; stock 20 → 17; ledger IN 20 / OUT 3; second dispense → 409; quantity −1 → "Line 1, quantity: Ensure this value is greater than or equal to 1." (no raw error) | Insufficient stock was not exercised here (covered by the existing `pharmacy.spec.js`) |
| 12 | Billing | **PASS** | `15-partially-paid.png`, `15-all-paid.png`, `db-verification.txt`. 4 bills; every total equals its lines to the paisa; no duplicate charge keys; the hospital's own prices were used | Discount and GST were not exercised (prices at 0% GST; GST covered by Prompt 2) |
| 13 | Payment | **PASS** | Partial payments ₹7.49 then ₹0.01 (paise), plus full payments; 5 receipts (RCPT-…); every bill finished **Paid** with ₹0.00 due | Refunds were not exercised in this run (covered by backend tests) |
| 14 | Patient portal | **PASS** | `16-patient-dashboard.png`, `16-patient-bills.png`. After a fresh sign-in: UHID, diagnosis, signed X-ray impression and its image (200), lab result, prescription, all bills paid, 0 dues | Ward observations in the portal were verified by API tests only |
| 15 | Discharge / exit | **PARTIAL** | OPD: the visit completed. IPD: admitted, bed allocated, discharge started, checklist 4/4, summary signed, final bill created and paid (`18-final-bill.png`); the page showed "Ready to complete" | The browser "Complete discharge" sent no request; the **server replay completes it** (`discharge-replay.txt`). Manual UI check needed (P1-1) |

## 3. Prompt 1–5 verification

| Prompt | Implemented | Re-tested now | Passed | Failed / incomplete |
|---|---|---|---|---|
| 1 Allergy safety | "No known allergies" only when recorded | Fresh patient shows "unknown"; `allergy-status.spec.js` 3/3 | Yes | — |
| 2 Billing paise | Exact paise payments and dues | ₹7.49 + ₹0.01 settled a ₹7.50 bill; dues exact; `billing-decimal.spec.js` 5/5 | Yes | — |
| 3 Registration / UHID | Hospital at sign-up, UHID, desk enrolment | Fresh patient at a fresh hospital, UHID stable after re-login; `patient-registration.spec.js` 4/4 | Yes | — |
| 4 Appointments / nursing / pharmacy | Working days, vitals with units, search, safe errors | Sunday refused, °F stored and shown, search while typing, readable quantity error; `appointments-nursing-pharmacy.spec.js` 3/3 | Yes | Nurse name missing for invited nurses (new, P1-2) |
| 5 Radiology, billing, self-service, storage | Radiology role/images/billing, cancel/reschedule, portal tracking, storage | All of it on the fresh hospital; `remaining-workflows.spec.js` 9/9 | Yes | Lab Staff orders unlinked to visits (P2-1); mobile not device-tested; the Prompt 5 report's "0 lint errors" predates its spec (P3-3) |

## 4. Remaining work: prioritized

### P0: critical safety, security or data-integrity blockers

None found that bypasses security, exposes data, or corrupts committed financial records. The closest is P1-3 (an extra visit record in the early-morning window).

### P1: required functional workflows

**P1-1. Inpatient "Complete discharge" from the browser is not verified.**

- **Observed:** every precondition was met ("Ready to complete"), but the click produced no `POST /api/ipd/admissions/{id}/complete_discharge/` (Playwright trace of the step). The test's next API call then hung. A server replay on a copy of the run's database returns 200 in 0.01 s and discharges.
- **Root cause:** not established. Possibly the confirmation-dialog interaction or a page stall.
- **Files:**
  - `src/pages/IPD.jsx` (`handleCompleteDischarge`; button `disabled={!readiness[id]?.ready}`);
  - `src/components/ipd/DischargeReadiness.jsx`;
  - `src/components/ui/useConfirm.jsx`;
  - `backend/ipd/views.py` (`complete_discharge`).
- **Dependencies:** none.
- **Steps:**
  1. Reproduce manually and with the trace viewer.
  2. Confirm the dialog opens and its button fires.
  3. Fix only if a defect is found.
- **Tests:** a Playwright discharge spec: admit → final bill paid → complete → bed released → patient sees "Discharged".

**P1-2. An invited Nurse has no Nurse profile, so nursing records have no author.**

- **Root cause (verified):** `backend/users/staff_invite.py` creates the Doctor profile for Doctor invites (`_ensure_doctor_profile`) but nothing equivalent for Nurse. `NursingAssessment.nurse` is empty, so doctor and patient see readings without a nurse name. The audit log still holds the user.
- **Files:**
  - `backend/users/staff_invite.py`;
  - `backend/nurses/models.py` (`Nurse`), `backend/nurses/serializers.py` (`nurse_name`), `backend/nurses/views.py`;
  - `src/pages/Nurses.jsx`.
- **Steps:**
  1. Create or link the Nurse profile on invite, as for doctors.
  2. Decide how existing records get attributed (policy 5).
- **Tests:** an invite-a-nurse backend test; an assessment shows `nurse_name`; a Playwright nurse → doctor check shows the name.

**P1-3. UTC/India date boundary, 00:00–05:30 IST.**

- **Root cause (verified for stats):** `TIME_ZONE = 'UTC'`, while "today" is the hospital's India date (`hospital_today()`). Filters like `paid_at__date=today` (`backend/home/views.py:142`) take the UTC date.
- **Same window, encounters:** `encounters.test_visit_lifecycle.TokenIssueVisitTests.test_a_waiting_visit_opened_before_the_token_is_reused` fails. A token issued then does not reuse the waiting visit, which creates a second visit for the patient.
- **Both tests pass outside the window**, which is why earlier (daytime) runs were green.
- **Files:** `backend/home/views.py`, `backend/encounters/services/visit_lifecycle.py` and token issue, `backend/config/hospital_time.py`.
- **Steps:**
  1. Compare against the hospital day's UTC bounds instead of `__date`.
  2. Audit every `__date=` filter.
- **Tests:** frozen time at 02:00 IST for token/visit reuse and today's stats.

**P1-4. No real SMS/OTP delivery: ON HOLD (§5),** but a pilot needs it. Without it, staff and patients have no OTP channel. Email sign-in needs a verified email, which needs a real email backend.

### P2: important missing features and improvements

- **P2-1. Lab Staff orders can't be linked to the visit.** The visit selector offered Lab Staff 0 visits, so the order saved without one. *Policy:* should Lab Staff see a patient's open visits (read-only)? Files: `backend/encounters/views.py` (visit permissions), `src/components/clinical/VisitSelect.jsx`. Tests: a Lab Staff order links to the open visit; the charge lands on the visit bill.
- **P2-2. Medicine GST.** "Add Medicine" has no GST field, so stocked items are 0% GST. Confirm whether GST is set elsewhere (stock edit or procurement); add it if not. Files: the pharmacy page, `backend/pharmacy/serializers.py`.
- **P2-3. Development environment.** On the iCloud Desktop, Vitest workers fail to start in place (0 of 45 files ran; 45/45 pass in a clean copy) and Vite took 79 s to start. Move the repo off iCloud.
- **P2-4. Not yet exercised end to end:** discount, GST-bearing services and refunds. Add them to the journey spec.
- **P2-5. Still open from the audit:**
  - BUG-011 (queue/visit status sync);
  - BUG-012 (portal probes);
  - MF-006 (structured lab results);
  - MF-007 (catalogue lookups);
  - MF-010 (real-time updates);
  - MF-012 (OPD nurse triage).

### P3: UI/UX and non-critical

- **P3-1:** the Hospital setup wizard sometimes doesn't advance or enable its steps after "Create hospital" until reload (`src/pages/admin/HospitalSetup.jsx`).
- **P3-2:** every staff sign-in first calls `POST /auth/staff/login/otp/start/`, which answers 503 while SMS is unconfigured (log noise; tied to Twilio, on hold).
- **P3-3:** lint shows 2 errors in `e2e/remaining-workflows.spec.js` (`Buffer` without `/* global Buffer */`).
- **P3-4:** BUG-009 (nurse banner), BUG-010 (billing modal a11y), BUG-013 (default doctor), appointment reference shown to patients.
- **P3-5:** one earlier iteration read a bill as "Unpaid" with ₹0.00 due right after a payment. It was not reproduced; the final re-read was Paid. Monitor only.

### ON HOLD: awaiting your APIs and configuration

Whisper (speech-to-text), Twilio (SMS/OTP), LLM (AI scribe). See §5.

### POLICY DECISIONS REQUIRED

1. May an Admin-only account be the lab's second checker? (SEC-002; Admin currently can.)
2. May Compounders record vitals? (Currently not; no form is offered.)
3. Should a patient be limited to one booking per doctor (or hospital) per day? (BUG-008.)
4. Should Lab Staff see visits to link the orders they create? (P2-1.)
5. How should nursing records saved without a nurse be attributed (from the audit log user)? (P1-2.)

## 5. External integrations on hold

These are intentionally deferred until you supply APIs and configuration. Nothing was configured, called or changed.

| Integration | Current implementation | Missing | Remaining tasks | Verification needed | Status |
|---|---|---|---|---|---|
| **Whisper / speech-to-text** | `backend/ai_scribe/services/stt.py`: `WhisperSTTProvider` (API and local), `GoogleSTTProvider`, development provider; settings `AI_SCRIBE_STT_*` (default `whisper-1`); `ai_scribe/audio_validation.py`; AI Scribe page; disabled in e2e | STT API key or local model; provider and region choice; data-processing terms for patient audio | Configure the provider; key in a secret store; audio retention policy | Synthetic Hindi/English recordings; error and timeout paths; consent before audio leaves | **ON HOLD: awaiting user API/configuration** |
| **Twilio / SMS / OTP** | `backend/users/sms.py` (Twilio Verify v2; console provider in development); patient and staff OTP flows; limits of 3 codes per 10 min and a 60 s cooldown; `staff/login/otp/start` returns 503 when unconfigured | `TWILIO_ACCOUNT_SID`, auth token or API key/secret, `TWILIO_VERIFY_SERVICE_SID`; the earlier audit saw the dev `.env` credentials rejected | Valid credentials; India sender/DLT registration; set `PATIENT_OTP_DELIVERY=sms`; decide `STAFF_LOGIN_REQUIRE_OTP` | Real OTP to a test number; failure messages; rate limits; no codes in production logs | **ON HOLD: awaiting user API/configuration** |
| **LLM (AI scribe and assist)** | `backend/ai_scribe/services/llm.py`: OpenAI, Anthropic, Google and development providers; `AI_SCRIBE_PROVIDER`, `AI_SCRIBE_MODEL` (default `gpt-4o-mini`), `AI_SCRIBE_LLM_BASE_URL`; mock providers barred in production; drafts never write clinical records without review | Provider, key, model, data-processing terms | Configure; review prompts; keep human review mandatory | Drafts from synthetic transcripts; refusal and timeout handling; AI interaction audit | **ON HOLD: awaiting user API/configuration** |

Two known backend test failures depend on the local `.env` provider settings, not on code: `ai_scribe…test_capabilities_report_providers_without_keys_and_block_cnn` and `security_tests…test_production_boots_without_twilio_when_sms_otp_is_off`.

## 6. Test summary

| Check | Result |
|---|---|
| Backend, full (SQLite, Twilio blanked) | **1522 run: 1480 passed, 38 skipped, 4 failed.** 2 are known `.env`-dependent failures (above). 2 are the **date-boundary defect** (P1-3), failing only between 00:00 and 05:30 IST: `encounters…test_a_waiting_visit_opened_before_the_token_is_reused` and `security_tests.test_home_stats…test_revenue_is_net_of_refunds` |
| Backend on PostgreSQL | Not re-run here (last: Prompt 5, 265 OK) |
| Frontend unit tests (Vitest) | In the project folder, workers failed to start (iCloud, environment). In a clean `git archive HEAD` copy with `npm ci`: **45 files, 252 tests passed** |
| Lint (`src` + `e2e`) | **2 errors**, both in `e2e/remaining-workflows.spec.js` (`Buffer`); 15 warnings at run time, 2 of them in the new spec (since removed) |
| Production build | **Passed** (17.7 s) |
| Browser E2E: fresh-hospital journey (FV55750) | **22 steps: 20 passed, 1 failed** (18, discharge completion), **1 skipped** (18b depends on 18); 2 recorded as PARTIAL (lab visit link, nurse name) |
| Browser E2E: Prompt 1–5 regression | **24 / 24 passed** (allergy 3, appointments-nursing-pharmacy 3, billing-decimal 5, patient-registration 4, remaining-workflows 9) |
| Database verification | `db-verification.txt`: hospital, memberships, UHID, appointments, visit, diagnosis, lab, imaging, image, invoices, lines, payments, stock, admission, nursing and audit rows |
| Security checks | All passed (§7) |
| Known pre-existing failures | The 2 `.env`-dependent backend tests; `nurse-mar.spec.js` known flaky (not in this run) |

## 7. Security and data integrity

| Area | Result | Evidence |
|---|---|---|
| Authentication | Unauthenticated patient read → 401 | `state.json` → `security` |
| RBAC | 8 roles × 8 endpoints: every forbidden combination 403. Receptionist 403 on vitals, users and lab; pharmacist 403 on the lab result and X-ray image; Lab Staff can't verify their own result | `accessMatrix`, `labTest`, `study` |
| Hospital isolation | Another hospital's doctor → 403 on this hospital's patients and appointments, 404 in their own scope; the patient can't book the other hospital's doctor | `security`, `bookingChecks` |
| Patient privacy | Another patient's record → 404; X-ray images withheld until signed; clinical and nursing notes not in the portal | `registrationChecks`, Prompt 5 tests |
| Browser storage | After staff sign-in only `hms_session` and `sidebarOpen`; after logout only `sidebarOpen` | `security` |
| Audit logging | 217 rows for the new hospital, including invites, payments, discharge-plan updates and summary finalization | `db-verification.txt` |
| Duplicate prevention | Same slot 409; second dispense 409; second report signature 400; no duplicate charge keys | `bookingChecks`, `pharmacy`, `study`, `billing` |
| Financial reconciliation | Each bill total equals its lines to the paisa; payments sum to totals; all Paid at ₹0.00 due | `billing`, `db-verification.txt` |
| Input validation | Unsafe/oversize files refused; negative quantity refused readably; unknown hospital and duplicate registration refused | `study`, `pharmacy`, `registrationChecks` |
| Gap | Nursing records lack a nurse link for invited nurses (P1-2); the user is still in the audit log | `db-verification.txt` |

## 8. Final project verdict

**NOT READY FOR CONTROLLED PILOT.**

The outpatient journey is functionally complete and verified end to end on a fresh hospital, with correct money handling and security controls. A controlled pilot still needs:

1. **Real OTP delivery** (Twilio on hold); email sign-in also needs a real email backend.
2. **Inpatient discharge completion** confirmed in the UI (P1-1).
3. **Nurse authorship** on nursing records (P1-2).
4. **The UTC/India date-boundary defect** fixed (P1-3), since hospitals run around the clock.

With these closed and this same spec re-run green, the evidence would support **READY FOR CONTROLLED PILOT**.

## 9. Next implementation roadmap

1. **P1-3:** hospital-day helper; replace `__date=today` filters; frozen-time tests at 02:00 IST.
2. **P1-2:** Nurse profile on invite; attribution decision for existing records; tests.
3. **P1-1:** reproduce discharge completion with the trace viewer; fix if needed; add a discharge spec.
4. **Policy decisions** 1–5 (§4).
5. **P2-1** (per decision) and **P2-2** medicine GST.
6. **Integrations, once credentials arrive:** Twilio first, then the email backend, then STT and LLM (verification steps in §5).
7. **P2-3:** move the repo off iCloud; re-run all suites in place.
8. **P2-5** audit items, then P3.
9. **Re-run `e2e/final-validation.spec.js`** and the full suites; update this verdict.

---

**Git at report time:**

- On `ui/redesign-2026-10-25`, HEAD `7495be3`. Commits `ae1023f` (Prompt 4) and `7495be3` (Prompt 5) are **not pushed** (`origin` is at `5e24012`).
- New and untracked from this task: `e2e/final-validation.spec.js`, this report, `reports/e2e-evidence/final-validation/`.
- Pre-existing untracked or deleted files are unchanged.
- **Nothing was committed or pushed in this task.**
