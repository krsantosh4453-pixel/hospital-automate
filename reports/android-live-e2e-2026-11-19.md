# Android live end-to-end patient journey — 19 Nov 2026

Run on the real Android app (`hms_mobile` debug build, emulator `hms_pixel_api36`) against a throwaway Django backend: committed HEAD `a0d93a3`, `config.settings.e2e`, SQLite, `seed_demo` data, port 8171. All patient data is synthetic. No SMS, calls, e-mail or online payments were sent; providers are console-only in these settings. Nothing was committed and no app code was changed.

Test patient: **Ravi Testpatient E2E** (patient id 6, UHID **DCH-2026-000001**), Demo City Hospital, Dr Asha Mehta (Cardiology).

## A. Summary

| | Count |
|---|---|
| Workflows tested | 14 |
| Pass | 6 |
| Partial (works, with defects or needed a non-app step) | 6 |
| Fail | 1 |
| Blocked in the app | 1 (patient → hospital registration) |

- **Android app:** most screens work against the live API. Reception has no mobile screens. Admission creation, discharge plan/summary and final bill are web-only.
- **Backend integration:** every in-app save was confirmed in the database with correct patient, doctor, visit, admission and hospital links.
- **Persistence:** no duplicates. Idempotency keys were present on the appointment and the prescription. Stock fell by exactly the dispensed quantity.
- **Not production-ready:** see section F.

## B. Results by role

| Role | Workflow | Result | Evidence |
|---|---|---|---|
| Patient | Registration + email OTP + login | PARTIAL | Account created (patient 6, email verified). Form has no age, address or hospital fields, and `age` is stored as **1**. |
| Patient | Join hospital / get UHID | **BLOCKED** | No API or screen links a self-registered patient to a hospital (BUG-01). Done with a labelled fixture calling `ensure_uhid()`. |
| Patient | Book appointment | PASS | Appointment #3, 19 Nov 14:00, Dr Mehta. Past slots hidden. 1 DB row with idempotency key. Visible to the doctor. |
| Reception | Check-in / issue token | PARTIAL | No mobile screen. Done via `POST /encounters/queue-tokens/issue/` as demo.desk.main: token #3, 201. A repeat call returned 200 with the same token (no duplicate). |
| Patient | Queue / waiting time | PASS, then FAIL | Token 3, position #2, ~15 min, matches the API and DB. The 30 s auto-refresh works. After the visit was completed, the token stays "Waiting" forever (BUG-02). |
| Doctor | Appointments, queue, consultation | PARTIAL | Patient, UHID, token and reason are correct. Vitals, note, ICD-10 diagnosis I20.9 and completion are all saved. Token/appointment not updated (BUG-02). Dashboard says "Now serving token 3" (BUG-03). No allergies field. |
| Doctor | Prescription | PASS | RX #1, Confirmed, 2 items (Pantoprazole 40mg ×5, Aspirin 75mg ×30), linked to visit 3. |
| Doctor | Lab order | PASS | Lipid Profile, LabTest #1, linked to visit 3. |
| Pharmacist | Dispensing | PASS | Aspirin "Not in stock" correctly blocked. Pantoprazole ×5 from DEMO-PAN-01: stock 80 → 75, Sale #1 ₹30. RX → Partially Dispensed. Auto-billed to INV/26-27/000001 ₹33.60 incl. 12% GST. |
| Lab staff | Sample → result → release | PARTIAL | All 8 stages done in the app with timestamps. Result is free text only. The same user entered and verified the result (BUG-06). |
| Doctor | Admission + bed | PARTIAL | No create-admission screen: admission #3 was created via API as the doctor. No free bed in seed data: bed E2E-2 was added via the admin API. Bed allocation done in the app. |
| Nurse | Vitals, notes, observations | PARTIAL | 2 assessments + 1 progress note saved, linked to admission 3, newest first. Vitals panel failed on first load (BUG-08). Header shows "1 y" (BUG-04). MAR is empty because no medication orders can be written from mobile. |
| Billing | Invoice + payment | PARTIAL | Pharmacy is auto-billed. Consultation, lab and bed were not auto-billed: entered by hand as INV-2 ₹2,800 (no price list). Cash receipt RCPT-638E4C9377A3, INV-2 Paid. No online gateway. |
| Doctor | Discharge | PARTIAL | Start discharge in the app. "Complete" correctly stays disabled until plan, summary and final bill exist, and those are web-only (done via API). Completed in the app: Discharged, bed released → Available. |
| Patient | Final journey view | PARTIAL | Correct: prescriptions, lab report, 3 bills (₹33.60 due), profile. Wrong or missing: token still "Waiting #2, expected 2:09 PM"; appointment "Checked in"; 0 past visits; "Current prescriptions 0"; no diagnosis, visit history, admission or discharge summary; Patient ID shows "6", not the UHID. |
| Security | RBAC / isolation | PASS | Other doctor: 404 on the record, empty vitals/diagnoses. Pharmacist and lab: 403 on the full record. Patient API: only own rows, 404 on another patient, 403 on nursing and IPD. |

## C. Patient journey

Registration **PARTIAL** → Login **PASS** → Join hospital **BLOCKED** → Appointment **PASS** → Queue token **PARTIAL (no mobile reception)** → Waiting time **PASS** → Consultation **PARTIAL** → Prescription **PASS** → Lab investigation **PARTIAL** → Pharmacy **PASS** → Admission **PARTIAL (web-only create)** → Nursing **PARTIAL** → Billing **PARTIAL** → Discharge **PARTIAL (web-only steps)** → Patient exit view **PARTIAL / queue FAIL**

Patient calling was not tested by design: Call was never pressed and no calling integration is configured.

## D. Bugs

| ID | Severity | Module | Problem | Root cause | Fix |
|---|---|---|---|---|---|
| BUG-01 | Critical | Backend / Reception | A self-registered portal patient can never join a hospital, so they can never book. | `PatientHospitalViewSet` → `_check_tenancy` (`users/viewsets.py:250`) rejects patients with no membership. `lookup` and `list` can't see them. Only `POST /patients/` (creates a *new* record) or seed scripts create memberships. | Add a reception "register existing portal patient" action (find by verified phone or email, then `ensure_uhid`), or let a patient request to join a hospital. |
| BUG-02 | High | Doctor app / Queue | After Start → Complete consultation, the queue token stays **Waiting** and the appointment **Checked In**. Patient sees "position #2, stay nearby"; doctor and nurse queues list the patient as waiting. | The consultation screen PATCHes `visit.status` (`doctor_repository.dart:188` `setVisitStatus`) instead of the token actions `start-consultation`/`complete` (`encounters/views.py:348/357`), and the Visit update does not sync token or appointment. | Call the token actions when the visit has a token, or sync token and appointment from the Visit status change on the server. |
| BUG-03 | Medium | Dashboard API | Doctor and nurse dashboards say "Now serving token 3" while nobody is in consultation. | `home/views.py:152` picks the highest token number issued today, whatever its status. | Use the token whose status is In Consultation (or Called). Show "No token served" otherwise. |
| BUG-04 | High (clinical) | Registration | Age is stored as 1 for every self-registered patient. Nurse header shows "1 y · Male", billing search shows "1". | The registration form has no age/DOB field and the model default is used. | Collect date of birth at registration. Make age nullable and show "Age not recorded". |
| BUG-05 | Medium | Patient app | Patient home "Current prescriptions: 0" while RX-1 is Partly dispensed. Prescription card doesn't show which items were issued. | Tile counting excludes the partly dispensed status (to confirm in the dashboard counter). Item dispensed quantities aren't rendered for patients. | Count partly dispensed prescriptions as current. Show "Issued x of y" per item. |
| BUG-06 | Medium | Laboratory | The same lab user entered *and* verified a result. | No maker-checker on `verify`. | Require a different user (or a supervisor role) to verify. |
| BUG-07 | Medium | Billing / IPD | Consultation, lab and bed-day charges are not auto-billed. Manual lines take free-text prices. Final IPD bill accepts `daily_rate` 0, and a separate manual bed charge isn't linked, so double or zero billing is possible. | No tariff and no charge capture from visits, lab or IPD. | Add a service price list and auto-capture charges. Require `daily_rate` > 0 or a justification. |
| BUG-08 | Low | Nursing app | Ward patient vitals panel shows "Something went wrong" on first open, then works on Try again. No server error was logged. | Client-side first-load race in `ward_vitals_section.dart` (no Flutter error was printed). | Reproduce with logging around `_history()`. Load after the ward context is ready. |
| BUG-09 | Low | Navigation | Logging out from a deep staff page (IPD) leaves the page showing "Your session has ended" instead of going to sign-in. Drawer footer says "Not signed in · Sign in" while a patient is signed in. | Router redirect on sign-out and the footer read session state wrongly. | Redirect to sign-in on sign-out. Bind the footer to `SessionController`. |
| BUG-10 | Low | IPD UI | A discharged stay shows "Bed: Waiting for a bed". Discharge checklist ticks are almost invisible (dark icon on teal). | Display logic and colour contrast. | Show "Released on …". Raise the icon contrast. |
| BUG-11 | Low | Patient profile | "Patient ID: 6" (internal DB id). Staff screens show UHID DCH-2026-000001. | Profile shows the DB id. | Show the UHID for the selected hospital. |

### Fix status

- **BUG-02 — fixed (Prompt 1/5, 19 Nov, uncommitted).** Visit status changes now go through `encounters/services/visit_lifecycle.py`, which moves the token and appointment in one locked transaction. Discharge and appointment cancel close open tokens. `close_stale_queue_tokens` repairs old rows. Found while verifying: token issuing reused a Completed same-day visit (fixed in `token_issue.py`), and a token could overwrite a closed visit (fixed in `appointment_status.py`). Re-verified live on the emulator.
- **BUG-03 — fixed** as part of the same change: "Now serving" is the token In Consultation.
- **BUG-01 — fixed (Prompt 2/5, 19 Nov, uncommitted).**
  - Patients choose a hospital at sign-up, or join one later from booking (`auth/patient/hospitals/` and `…/join/`).
  - Reception links an existing account by mobile number + date of birth (`patients/link/`), and is stopped from registering a patient-app account twice.
  - New Android reception screens: patient search/register/link, appointments with check-in (issues the token), and a read-only queue.
  - Re-verified live on the emulator with no fixture.
- **BUG-04 — fixed.** Date of birth is required at sign-up and is the source of truth for age. Migration 0015 clears only the placeholder 1s. Ages that aren't recorded are no longer shown.

- **BUG-06 and BUG-07 — fixed (Prompt 4/5, 20 Nov, uncommitted).** Details, calculations and database evidence: [billing-pharmacy-lab-2026-11-20.md](billing-pharmacy-lab-2026-11-20.md).
  - A hospital price list (INR, effective dates, never edited) prices consultation, laboratory and bed days. Charges are captured when a consultation completes and a lab result is verified, once per service.
  - The final stay bill takes bed days from the price list. ₹0 bills are refused unless an Admin or Manager records a waiver. Discharge waits for every bill of the stay.
  - A lab result is verified by a different user from the one who entered it, unless an Admin turns on the audited exception policy. Results can no longer be edited through the API.

- **Final verification (Prompt 5/5, 20 Nov, uncommitted):** all 11 bugs re-checked live on the emulator. BUG-05, 08, 09, 10 and 11 were still open and are now fixed, along with 5 more defects. Details: [android-live-e2e-final-2026-11-19.md](android-live-e2e-final-2026-11-19.md).

- **Prompt 3/5 (19 Nov, uncommitted)** added these to Android: allergies with Unknown vs No-known-allergies status, admit + bed, ward medication orders, discharge plan/summary/finalize, the billing final bill, and patient health history (with the finalized discharge summary).
  - Admission status can no longer be written by clients.
  - The emulator UI run stalled (host out of memory); the workflow was verified live through the API and in 463 widget tests.

## E. Missing in the Android app

- Reception: patient registration at a hospital, check-in, issuing tokens (API exists, no screens).
- Doctor: create admission, write MAR medication orders, discharge plan/checklist, discharge summary (all "completed on the web app").
- Billing: IPD final bill, service price list.
- Patient: visit/consultation history, diagnoses, admission and discharge summary, nursing records, opening documents ("not available yet"), online payment, cancelling or rescheduling appointments.
- Clinical: allergies field in consultation; structured lab results (only free text).
- Calling: no calling integration configured. Not tested, as instructed.

## F. Production readiness

| Area | Assessment |
|---|---|
| Android UI | Good visual quality, clear confirmations and error states. Several stale or misleading states (BUG-02/03/05/10). |
| Flutter architecture | Clean feature-first structure, server re-checks every action. Consultation bypasses the queue state machine (BUG-02). |
| API integration | Correct for every in-app action tested. Idempotency keys used. |
| Backend | Solid scoping and audit. Missing the portal-patient → hospital link (BUG-01) and charge capture (BUG-07). |
| Database | Consistent links, no duplicates, exact stock arithmetic. |
| Authentication | Email OTP verification and password login work. Staff login always calls `otp/start` first and gets a 400 (harmless, noisy). |
| RBAC / isolation | Pass in every probe. |
| Patient privacy | Patient sees only own data. Lab result entered and verified by one person (BUG-06). |
| Workflow correctness | Not ready: queue never closes (BUG-02), age default (BUG-04), self-registered patients stuck (BUG-01). |
| Error handling | Good: stock shortage, discharge blockers and invalid dispense are all blocked clearly. |
| Performance | Not measured (single user, emulator). |
| **Overall** | **Not production-ready.** The happy path works end to end only with non-app steps, and the patient is left with a false "waiting" state. |

## Steps done outside the Android app (all on the throwaway server)

1. Fixture: `ensure_uhid(patient 6, hospital 1)` → DCH-2026-000001 (no API exists, BUG-01).
2. API as demo.desk.main: `queue-tokens/issue` for appointment 3 (no reception screen).
3. API as demo.admin: added bed "E2E-2" in Ward A (seed beds were all occupied).
4. API as demo.doctor1: create admission 3; discharge plan; discharge summary + finalize.
5. API as demo.billing: IPD final bill (₹0, bed-day already on INV-2).
6. Email OTP read from the test DB's hashed code with the test server's key (the e2e mailbox is in-memory).
