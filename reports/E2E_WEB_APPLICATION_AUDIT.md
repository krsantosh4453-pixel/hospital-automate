# Hospital Automate — End-to-End Web Application Audit

- **Date:** 2026-11-24 (IST)
- **Branch / commit tested:** `ui/redesign-2026-10-25` @ `e71bb63`
- **Scope:** testing and audit only. No application code, schema, settings or Git history was changed.
- **Machine-readable copy:** [`E2E_WEB_APPLICATION_AUDIT.json`](E2E_WEB_APPLICATION_AUDIT.json)
- **Evidence:** [`e2e-evidence/`](e2e-evidence/) (screenshots, captured request/response bodies, suite log). No tokens, passwords or real patient data.

## How the testing was done

| Item | Detail |
|---|---|
| Frontend | React 19 + Vite 7 + React Router 7, Tailwind. One API client (`src/services/api.js`), cookie (httpOnly JWT) sessions, CSRF on writes |
| Backend | Django 6 + DRF, SQLite in dev/e2e (PostgreSQL in production), role permissions per hospital |
| Isolation | A **throwaway database** (`config.settings.e2e`: every external service off, console OTP, in-memory email, Twilio blanked) seeded by `seed_demo` with synthetic "Demo City Hospital" accounts. Own Django on `127.0.0.1:8147` and Vite on `:5187` (proxy to 8147). The developer's dev DB was **not modified** (24 users / 4 appointments before and after). |
| Browser | Chrome via DevTools automation: real clicks and form entry in the running UI, network capture, console capture. Each role in its own isolated browser context. |
| Existing automation | Ran the project's Playwright suite (`npx playwright test`, 32 specs) against its own isolated backend: **31 passed, 1 failed; the failing spec passed 2/2 on rerun (flaky)**. See `e2e-evidence/00-playwright-suite.txt`. |
| Backend unit tests | 44 health/registration/auth tests passed earlier the same day (`config.test_health`, `users.test_stage1a_patient_registration`, `users.test_stage1_auth`, `users.test_twilio_verify_failures`). |
| Test identities | Synthetic only: patient "Audit Synthetic Patient", mobile 9000031101, `audit.patient.1@example.test`; staff `demo.*` seed accounts; every clinical entry is prefixed `AUDIT-SYNTHETIC`. |

---

## A. Executive summary

| Measure | Result |
|---|---|
| Overall status | **Core OPD journey works end to end** (register → book → token → consult → lab → X-ray → pharmacy → bill → patient view), with real backend data at every step. Several defects and integration gaps block a *self-registered* patient and complete billing. |
| Journey workflows tested | 11 |
| Passed | 6 (Appointment, Queue, Doctor consultation, Radiology, Laboratory, Pharmacy) |
| Partially working | 4 (Registration, Nursing, Billing, Patient tracking) |
| Failed | 0 outright (billing full-payment fails, recorded under Billing = Partial) |
| Not tested / blocked | 1 (Discharge for this OPD patient; IPD discharge covered only by the passing Playwright `ipd-bed` spec) |
| Bugs | 13 (2 High, 6 Medium, 5 Low) |
| Missing features | 12 |
| Security findings | 2 (Low/Medium); every permission and isolation probe passed |
| Readiness | **Not ready for real patients** until P1/P2 items below are fixed (allergy display, billing in paise, self-registered patients cannot book, nurse vitals not visible to doctors). |

---

## B. Complete patient journey results

| Step | Module | Test case | Result | Evidence |
|---|---|---|---|---|
| 1 | Registration | Patient account creation via dashboard → Patient sign in → Create Account modal | **PARTIAL** | `POST /api/auth/register/` 201; 6 required fields block empty submit; row stored (MD5 hasher under e2e settings; pbkdf2_sha256 verified on the dev server earlier). Mobile-OTP sign-in → dashboard PASS (`01-new-patient-dashboard.png`). **No hospital selector** → no UHID → cannot book (MF-001). Email verification BLOCKED in e2e mode (in-memory mailbox); PASS on dev server earlier today. Duplicate account rejected (generic anti-enumeration message, verified on dev server). |
| 2 | Appointment | Hospital → doctor (department in label) → date → real free slots → book | **PASS** (with BUG-003, BUG-009) | `POST /api/appointments/book/` 201, appointment #3 "Scheduled", toast "Booked with Dr Asha Mehta…", listed on patient page. Same slot → 409; past time, off-hours, >60 days, missing doctor → 400; cap of 3 upcoming enforced. Sunday slot accepted for a "Mon–Sat" doctor. Appointment ID not shown to the patient. |
| 3 | Queue | Reception issues token, patient position/wait, sync | **PASS** | Reception "Issue token" → "Token #3 generated". Patient page: token 3, position #2, est. 15 min, expected 12:55, from backend. Patient page refreshes by **30-second polling** (not push); a change appeared 14 s after a staff action without reload. Doctor queue scoped to own patients. |
| 4 | Doctor | Call → start consultation → diagnosis, notes, vitals, Rx, orders → complete | **PASS** (BUG-001) | Starting before calling is refused ("Token #3 has not been called yet"). Diagnosis, clinical note, vitals (°C) saved; RX-0001 linked to visit #3; visit → Completed. Banner wrongly shows "No known allergies" for `allergy_status: "Unknown"`. |
| 5 | Nursing | Vitals, notes, visibility to doctor | **PARTIAL** | Ward vitals for an admitted patient saved (`POST /api/nurses/assessments/` 201, `05-nurse-vitals-*`). Nurse cannot record OPD vitals (form lists ward patients only). Nurse vitals are not in `clinical/vitals` (0 rows) → **doctor's Vitals tab never shows them**; temperature stored as `"98.6"` without unit while doctors record °C. Nurse page shows a permission error banner for bills. MAR covered by Playwright `nurse-mar` (flaky, passes on rerun). |
| 6 | Radiology | Order → schedule → perform → signed report → doctor/patient view | **PASS** (no radiology role, no image upload) | Imaging #1 `RAD-…` Ordered → Scheduled → Performed → Reported. Lab staff schedule/perform; lab staff cannot sign (403); doctor signs; empty findings/impression blocked; report locked (PATCH 405). Patient sees "Impression: …". Order not linked to visit (`visit: null`). Not billed. |
| 7 | Laboratory | Order → collect → dispatch → receive → process → result → verify → release | **PASS** | LAB-1 walked all 8 steps in the UI. Self-verification refused ("a different authorised user must verify it"); verified/released by a second user (Admin). Patient sees the released result. Result entry is free text only. Order `visit: null`. |
| 8 | Pharmacy | Rx reaches pharmacy → dispense → stock → ledger → bill | **PASS** (BUG-006, BUG-007) | RX-0001 in "To dispense", "In stock". Qty > prescribed blocked; dispensed 10 → stock 100 → 90; ledger IN 100 / OUT 10 (`SALE-1`) reconciles; duplicate dispense 409; invoice INV/26-27/000001 ₹33.60 created (10 × ₹3 + 12% GST). `08-dispense-*`. Short-stock and returns covered by Playwright (pass). |
| 9 | Billing | Charges, invoice, payment, outstanding | **PARTIAL** | Pharmacy charge billed correctly. Consultation and CBC appear as "Unbilled work — Add a price first" (seed price list empty). **X-ray never appears anywhere in billing.** Payment of ₹33.60 impossible (field accepts whole rupees, `09-billing-paise-payment-blocked.png`); ₹33 recorded → "Partially Paid", receipt + idempotency key, balance ₹0.60. |
| 10 | Patient tracking | Patient sees each stage | **PARTIAL** | Visible: appointments, queue/token, prescription + dispensed date, lab result, imaging impression, bill & balance (`10-patient-results-mobile.png`). Not visible: diagnosis/consultation summary, nursing status, radiology/lab order progress before release, discharge. Dashboard tile "Bills with balance due: 0" while ₹0.60 is due (BUG-004). Only the queue page auto-refreshes (polling); other pages need manual refresh. Data correct after refresh. |
| 11 | Discharge | Discharge summary and final history | **NOT TESTED (this patient)** | Patient was OPD (no admission). IPD discharge is covered by Playwright `ipd-bed.spec.js` (pass). The patient portal has no discharge-summary page (MF-009). |

---

## C. Bug list

### BUG-001 — Consultation banner shows "No known allergies" when allergies were never recorded
- **Module:** Doctor consultation (clinical safety) · **Severity: High**
- **Steps:** Register a patient (allergy status defaults to Unknown) → doctor opens the visit in Consultation.
- **Expected:** "Allergies not recorded — ask the patient" (or similar).
- **Actual:** "No known allergies". `GET /api/patients/6/` returns `"allergy_status": "Unknown"`.
- **Root cause (code):** `src/components/clinical/PatientContextStrip.jsx:77` renders "No known allergies" whenever the allergy list is empty and never reads `allergy_status`.
- **Database impact:** none; display only. **Risk:** a prescriber can read "unknown" as "none".

### BUG-002 — A bill with paise cannot be paid in full
- **Module:** Billing · **Severity: High**
- **Steps:** Dispense RX-0001 (bill ₹33.60) → Billing → "Payment" → enter 33.60 → Save.
- **Expected:** Payment of ₹33.60 recorded, invoice Paid.
- **Actual:** Browser blocks it: "Please enter a valid value. The two nearest valid values are 33 and 34." Recording ₹33 leaves ₹0.60 that cannot be cleared through this form.
- **Root cause (code):** `src/pages/billing.jsx` (~line 1637) Amount Paid is `type="number" min="0"` without `step`; Discount has the same pattern. Any GST-bearing bill has paise.
- **Evidence:** `e2e-evidence/09-billing-paise-payment-blocked.png`.

### BUG-003 — Booking offers and accepts days the doctor does not work
- **Module:** Appointments · **Severity: Medium**
- **Steps:** Patient books Dr Asha Mehta ("Mon-Sat 09:00-17:00") on Sunday 2026-11-29.
- **Expected:** No slots on Sunday; booking refused.
- **Actual:** `GET /api/appointments/booking-options/?…&date=2026-11-29` lists slots `available: true`; `POST /api/appointments/book/` → 201 (appointment #5).
- **Probable cause:** slot generation uses working hours but not working days.

### BUG-004 — Patient dashboard does not count partially paid bills
- **Module:** Patient portal · **Severity: Medium**
- **Steps:** Partially pay a bill → patient opens Home.
- **Expected:** "Bills with balance due: 1".
- **Actual:** "0" (Bills page correctly shows ₹0.60 due).
- **Root cause (code):** `src/pages/patient/PatientDashboard.jsx:49` checks `"Partial"`; the API returns `"Partially Paid"`.

### BUG-005 — Temperature stored without unit; nurse (°F) and doctor (°C) use different units
- **Module:** Nursing / clinical data · **Severity: Medium**
- **Steps:** Nurse records 98.6 in "Temperature °F" → saved as `vitals.temperature: "98.6"` in a nursing assessment. Doctor's form records °C in a different table.
- **Expected:** One vitals record with an explicit unit, visible to both roles.
- **Actual:** Unitless string in `nurses/assessments`; see integration issue INT-001.
- **Evidence:** `e2e-evidence/05-nurse-vitals-request.network-request`.

### BUG-006 — Pharmacy "Medicine returns" search throws on typing
- **Module:** Pharmacy · **Severity: Medium**
- **Steps:** Pharmacy → Medicine returns → type in the search box.
- **Actual:** `TypeError: Cannot read properties of undefined (reading 'value')` at `SaleReturns.jsx:87` (seen in the Playwright run's Vite log); the query is not updated.
- **Root cause (code):** `onChange={(e) => setQuery(e.target.value)}`, but `SearchInput` calls `onChange(value)` with a string (`src/components/ui/Data.jsx:50`).

### BUG-007 — Raw Python error shown to the pharmacist for an invalid quantity
- **Module:** Pharmacy · **Severity: Medium**
- **Steps:** Open RX-0001 → set "Give now" to -1 → Dispense.
- **Expected:** "Quantity must be at least 1." (and the form should not submit).
- **Actual:** Request sent (`POST /api/pharmacy-sales/dispense-prescription/` 400); toast shows `lines: {0: {'quantity': [ErrorDetail(string='Ensure this value is greater than or equal to 1.', code='min_value')]}}`. The input allows 0 (`min=0`) and the click handler submits invalid values.

### BUG-008 — Same patient can book the same doctor twice on one day
- **Module:** Appointments · **Severity: Medium**
- **Steps:** Book Dr Asha Mehta 2026-11-25 09:15, then 10:00 (same patient).
- **Actual:** Both 201 (appointments #3 and #4). If the hospital intends one visit per doctor per day, this is a duplicate booking.

### BUG-009 — Nurse home shows a permission error banner
- **Module:** Nursing · **Severity: Low**
- **Actual:** "Some ward data did not load — Could not load: bills (You do not have permission…)" on every visit; the page requests `GET /api/billing/invoices/` (403) that the nurse role is not allowed to read.

### BUG-010 — Edit Bill / Payment modal is not an accessible dialog
- **Module:** Billing · **Severity: Low**
- **Actual:** The modal has no `role="dialog"`/`aria-modal`; "Amount Paid" and "Payment Method" have no programmatic labels (accessible names "₹ 0" / none). The "Payment" action opens a combined "Edit Bill" form (discount + payment), which is easy to misuse.

### BUG-011 — Queue and visit status disagree; two tokens can be "Called" at once
- **Module:** Queue / Consultation · **Severity: Low**
- **Actual:** After reception called token #1, the queue showed "Called" while Consultation listed that visit as "Waiting". The doctor could then call token #3 while #1 was still "Called". Patient position stayed "#2" until the consultation started.

### BUG-012 — Patient portal calls staff-only and dev endpoints on every load
- **Module:** Patient portal / Auth · **Severity: Low**
- **Actual:** `GET /api/hospital/hospitals/` 403, `GET /api/auth/staff/me/` 403 and `GET /api/auth/dev/login/` 404 on each page load, plus console errors; hides real errors and adds load.

### BUG-013 — Order forms default the doctor to "Not specified" for a signed-in doctor
- **Module:** Laboratory / Prescription · **Severity: Low**
- **Actual:** "New lab order → Referring doctor" and the prescription "Doctor" field default to "Not specified" when a doctor creates them; the lab order can be saved without a referring doctor.

### Test-suite finding (not an app bug)
- `e2e/nurse-mar.spec.js` "ward nurse gives a due dose from the MAR" timed out after `reload()` waiting for the MAR tab; passed 2/2 on rerun → **flaky**.

---

## D. Missing feature list

| ID | Feature | Module | Required functionality | Current status | Dependencies | Recommended approach |
|---|---|---|---|---|---|---|
| MF-001 | Hospital choice at self-registration | Registration | Patient picks a hospital; gets a UHID | Backend `register_account` accepts `hospital` and calls `ensure_uhid`; **UI has no field** | `hospital/directory` API | Add a hospital select to `Register.jsx`, send `hospital` |
| MF-002 | Reception "link existing patient" | Reception | Enrol a self-registered patient by mobile + DOB | `POST /api/patients/link/` works (201, UHID `DCH-2026-000001`), **no frontend caller** | patients viewset | Add a "Find & enrol" action on Patients/Queue |
| MF-003 | Patient cancel / reschedule | Patient portal | Patient cancels or moves own booking | Backend `cancel`/`reschedule` staff-only (patient 403); no buttons | appointment permissions | Patient-scoped cancel (and reschedule) with cut-off rules |
| MF-004 | Radiology staff role & statuses | Radiology | Radiology technician/radiologist roles; Accepted / In progress / Reviewed | Lab Staff performs imaging, any Doctor reports; statuses Ordered/Scheduled/Performed/Reported/Cancelled | `StaffRole`, permissions | Add roles; optional "In progress" and second-read "Reviewed" |
| MF-005 | Imaging attachments | Radiology | Upload images/PDF/DICOM link to a study | `ImagingStudy` has text fields only | Documents app / storage | FK to documents or file field + viewer |
| MF-006 | Structured lab results | Laboratory | Parameters, units, reference ranges, flags per test | Single free-text result | Test catalogue | Result templates per test |
| MF-007 | Catalogue lookups in ordering | Consultation / Rx | Pick services and formulary medicines | Free-text "Service" and medicine name | Price list, pharmacy stock | Typeahead from catalogue/formulary |
| MF-008 | Visit summary for the patient | Patient portal | Diagnosis and doctor's advice after consultation | Not shown anywhere | Clinical notes/diagnoses APIs | "Visit summary" page with released fields |
| MF-009 | Full journey tracker & discharge summary | Patient portal | Nursing, order progress, discharge summary | Only final results/bills; no discharge page | IPD discharge data | Timeline from `patients/{id}/timeline/` |
| MF-010 | Real-time updates | Patient portal | Push updates | Queue page polls every 30 s; others need refresh | — | Polling on more pages, or SSE/WebSocket |
| MF-011 | Radiology billing | Billing | X-ray/imaging charges | Not in price list or unbilled sweep | `billing/unbilled.py` | Add imaging kind to price list + sweep |
| MF-012 | OPD nursing triage | Nursing | Nurse records OPD vitals before consultation | Nurse vitals form lists ward patients only | care scope | OPD triage queue for nurses writing `clinical/vitals` |

---

## E. Integration issues

| ID | Issue | Evidence |
|---|---|---|
| INT-001 | Two vitals stores: nurse → `nurses/assessments` (unitless JSON), doctor → `clinical/vitals` (°C). Doctor's Vitals tab shows **0** nurse readings. | `GET /api/clinical/vitals/?patient=3` → 0 rows; `GET /api/nurses/assessments/?patient=3` → 1 row |
| INT-002 | Lab and imaging orders created from Laboratory/Radiology pages are **not linked to the visit** (`visit: null`) although the models support it. | `GET /api/laboratory/1/`, `/api/laboratory/imaging/1/` |
| INT-003 | Backend endpoints with no UI: `POST /api/patients/link/`, `hospital` on `/auth/register/`, appointment `cancel`/`reschedule` for patients. | Code search: no callers in `src/` |
| INT-004 | Consultation and lab charges depend on a price list; with none configured they stay in "Unbilled work". Radiology is outside the sweep entirely. | `GET /api/billing/price-list/unbilled/` → consultation #3, lab #1 `priced:false`; no imaging |
| INT-005 | Patient tracking is page-by-page; no single journey timeline; only queue polls. | Portal pages read at runtime |
| INT-006 | No mock or localStorage-only workflows were found in the tested journey: every step used live API calls. localStorage holds session flags and (staff) a profile cache only. | Network logs per role |

---

## F. Security findings

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| SEC-001 | Low | Staff profile (`user`, `roles`, `hospitals`, incl. email/phone/employee ID fields) is cached in `localStorage` on shared hospital PCs. No tokens are stored there. | Receptionist session: keys `user, roles, hospitals, selectedHospital, hms_session` |
| SEC-002 | Medium (governance) | The lab four-eyes rule can be satisfied by an **Admin** account, which is not a clinical/pathology role (`IsLabStaff` includes Admin). | LAB-1 verified and released by `demo.admin` |

**Permission and isolation probes — all PASSED:**
- Patient → other patient's record/timeline: 404; diagnoses 403; nursing assessments 403; list endpoints return only own rows (filters like `?patient=1` are ignored but still scoped to self).
- Pharmacist → add diagnosis / change visit / list users / enter lab result / sign imaging report: all 403.
- Nurse → create prescription / add diagnosis / list users / dispense / read invoices: all 403.
- Lab staff → list users / invite staff / prescriptions / invoices / foreign hospital (`X-Hospital-ID: 999`): all 403; lab staff cannot sign imaging reports (403).
- Anonymous → patients, prescriptions, invoices, laboratory: 401. Forged JWT (cookie or Bearer): 401.
- Signed imaging report cannot be edited (PATCH 405). Duplicate dispense 409. Same appointment slot 409.
- Responses carry `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`; session JWT is an httpOnly cookie; phone numbers masked in staff patient pickers.
- Not tested: cross-hospital data with two real hospitals (seed has one), rate limiting (disabled in e2e settings; registration limiter was observed working on the dev server: HTTP 429 after 5 attempts).

---

## G. Test evidence

| File | Content |
|---|---|
| `e2e-evidence/00-playwright-suite.txt` | Per-test results of the existing Playwright suite + rerun |
| `e2e-evidence/01-new-patient-dashboard.png` | New patient's dashboard after Mobile-OTP sign-in |
| `e2e-evidence/05-nurse-vitals-request.network-request` / `-response.network-response` | Nurse vitals payload (unitless temperature) |
| `e2e-evidence/08-dispense-request.network-request` / `-response.network-response` | Dispense request and invoice-linked response |
| `e2e-evidence/09-billing-paise-payment-blocked.png` | ₹33.60 rejected by the payment field |
| `e2e-evidence/10-patient-results-mobile.png` | Patient lab and imaging results at narrow width |

Other observations: patient pages had no horizontal scroll at narrow width; the dev server issues every request twice (React StrictMode, development only).

---

## H. Prioritized implementation backlog

### Priority 1 — Patient safety, data integrity, security
| Task | Problem | Required implementation | Frontend | Backend | Acceptance criteria | Test |
|---|---|---|---|---|---|---|
| P1-01 | BUG-001 allergy banner | Show "Allergies not recorded" when `allergy_status` ≠ known/none; "No known allergies" only for an explicit NKA | `src/components/clinical/PatientContextStrip.jsx` | — (field exists) | Unknown → warning text; NKA → "No known allergies"; list → allergies | Vitest for three states + Playwright on Consultation |
| P1-02 | BUG-005 / INT-001 vitals | One vitals source with explicit units; nurse vitals written to (or surfaced in) clinical vitals | `src/pages/Nurses*`, Consultation Vitals tab | `nurses` assessments → `clinical.Vitals` (or read-through) | Nurse reading visible in doctor's Vitals tab with unit | API test + Playwright nurse→doctor |
| P1-03 | SEC-002 lab verifier | Restrict verify/release to clinical lab roles (configurable) | — | `users/permissions.py` (`IsLabStaff`), `laboratory/views.py` verify/release | Admin-only account cannot verify | Django test |

### Priority 2 — Core patient journey failures
| Task | Problem | Required implementation | Frontend | Backend | Acceptance criteria | Test |
|---|---|---|---|---|---|---|
| P2-01 | BUG-002 paise payments | `step="0.01"` on amount/discount; validate ≤ balance | `src/pages/billing.jsx` | — | ₹33.60 pays invoice fully → Paid | Playwright billing |
| P2-02 | MF-001 hospital at sign-up | Hospital select on Create Account | `src/pages/Register.jsx` | none | New patient gets UHID and can book | Playwright register→book |
| P2-03 | MF-002 enrol existing patient | UI for `POST /api/patients/link/` | `src/pages/Patients.jsx` or Queue | none | Reception enrols by mobile + DOB | Playwright reception |
| P2-04 | BUG-003 working days | Respect doctor working days in slots and booking | — | `appointments` booking-options / book | Sunday shows no slots; POST → 400 | Django test |
| P2-05 | INT-004 / MF-011 billing coverage | Price list seed/admin flow; imaging in price list + unbilled sweep | `src/components/billing/*` | `billing/unbilled.py`, price list | Consultation, lab, X-ray charged | Django + Playwright |

### Priority 3 — Cross-module integration
| Task | Problem | Required implementation | Frontend | Backend | Acceptance criteria | Test |
|---|---|---|---|---|---|---|
| P3-01 | INT-002 order↔visit link | Pass `visit` when ordering from consultation; offer visit picker on module pages | Consultation, Laboratory, Radiology order dialogs | serializers accept `visit` | Orders show their visit | API test |
| P3-02 | BUG-004 dashboard count | Use `"Partially Paid"` (or `balance_due > 0`) | `src/pages/patient/PatientDashboard.jsx` | — | Tile = number of bills with balance | Vitest |
| P3-03 | BUG-011 queue/visit status | Keep visit status in step with token; one called token per doctor | Queue, Consultation | `encounters/services/visit_lifecycle.py` | Statuses match across screens | Django test |
| P3-04 | BUG-008 duplicate same-day booking | Decide policy; enforce if one per doctor per day | — | appointments book | Second same-day booking → 409 (if policy) | Django test |

### Priority 4 — Missing functionality
MF-003 (patient cancel/reschedule), MF-004 (radiology roles), MF-005 (imaging attachments), MF-006 (structured lab results), MF-007 (catalogue/formulary lookups), MF-008/009 (visit summary, journey tracker, discharge summary), MF-010 (real-time updates), MF-012 (OPD nurse triage). Each: frontend page + backend endpoint/permission + Playwright journey test.

### Priority 5 — UI/UX and minor
| Task | Problem | Files | Acceptance |
|---|---|---|---|
| P5-01 | BUG-006 returns search | `src/components/pharmacy/SaleReturns.jsx:87` → `onChange={setQuery}` | Typing filters, no TypeError |
| P5-02 | BUG-007 raw error + min qty | Pharmacy dispense panel (`min=1`, block invalid submit); flatten DRF errors in `parseErrorDetail` | Friendly message, no request for qty < 1 |
| P5-03 | BUG-009 nurse banner | Nurse page: don't request invoices without permission | No error banner for nurses |
| P5-04 | BUG-010 billing modal a11y | Use shared `Modal`; label inputs | Screen reader announces dialog + labels |
| P5-05 | BUG-012 noisy requests | Patient portal skips staff/dev probes | No 403/404 on patient page load |
| P5-06 | BUG-013 default doctor | Default to signed-in doctor | Doctor pre-selected |
| P5-07 | Show appointment ID to patient | Patient appointments list | ID/reference visible |
| P5-08 | Flaky `nurse-mar` spec | `e2e/nurse-mar.spec.js` wait for tablist after reload | 10 consecutive passes |

---

## Not verified

- Real SMS/email delivery and payments: not attempted by design (external services). On the dev server, Twilio rejected the configured credentials (separate configuration issue).
- Google sign-in, AI scribe, FHIR/HL7/ABDM: disabled in e2e settings.
- Multi-hospital isolation with two populated hospitals; production (PostgreSQL) behaviour; load/performance.
- IPD admission → discharge for this audit patient (covered only by the existing Playwright `ipd-bed` spec, which passed).
