# Remaining work: completion report

**Date:** 2026-11-25 · **Branch:** `ui/redesign-2026-10-25` (changes uncommitted, not pushed)
**Follows:** `reports/FINAL_END_TO_END_VALIDATION_AND_REMAINING_WORK.md` (§4). That report and its evidence are unchanged.
**Evidence:** `reports/e2e-evidence/remaining-work/`:
- the screenshots and `state.json` of journey run `FV83449`;
- `FV94672/`: the final run after all changes, 22 of 22 pass;
- `18-discharge-ui-reproduction.png`.

**Scope (the user's instruction):** finish everything in §4 except OTP/SMS (Twilio) and the LLM/Whisper work, which stay ON HOLD until the user provides those APIs.

**Rules kept:**
- synthetic data only; the development database was not touched;
- no SMS, email or OTP was sent;
- Twilio, Whisper and LLM were not configured or called;
- `.env` credentials were not used (the Twilio variables were blank in every test run);
- nothing was committed or pushed.

---

## 1. Summary

| Item | Status | How it was checked |
|---|---|---|
| P1-1 Inpatient discharge from the browser | **Done.** Works in the UI; the earlier failure was the test script | Journey step 18 PASS; manual reproduction screenshot |
| P1-2 Nurse profile on invite; author shown on vitals | **Done**, plus a command for old records (policy 5) | Backend tests; journey step 17 shows the nurse name |
| P1-3 India/UTC date boundary (00:00–05:30 IST) | **Done** | Frozen-clock tests at 02:30 IST and late evening |
| P1-4 SMS/OTP delivery | **ON HOLD.** Needs the user's Twilio credentials | — |
| P2-1 Lab Staff link walk-in orders to the visit | **Done** (policy 4: read-only) | Backend tests |
| P2-2 Medicine GST | **No change needed.** The earlier finding was wrong | Journey step 06 stocks a medicine at 12 % GST |
| P2-3 Move the repo off iCloud | **User action** (see §4) | — |
| P2-4 Discount, GST and refunds in the journey | **Done.** Refund screen added | Journey step 15 |
| P2-5 BUG-011 queue/visit status | **Done** | Backend and Vitest tests |
| P2-5 BUG-012 portal probes | **Done** | Vitest |
| P2-5 MF-006 structured lab results | **Already present** | Code review (see §2) |
| P2-5 MF-007 catalogue lookups | **Done** | Backend and Vitest tests |
| P2-5 MF-010 real-time updates (patient portal) | **Done** (quiet refresh) | Vitest |
| P2-5 MF-012 OPD nurse triage | **Done** | Vitest; backend scope already allowed it |
| P3-1 Setup wizard does not advance | **Done** | Vitest |
| P3-2 OTP-start 503 noise at staff sign-in | **ON HOLD** (Twilio) | — |
| P3-3 Lint errors | **No change needed.** HEAD already had `/* global Buffer */` | ESLint: 0 errors |
| P3-4 BUG-009 nurse billing banner | **Done** | Journey step 17 |
| P3-4 BUG-010 billing modal accessibility | **Done** | Lint, build, e2e |
| P3-4 BUG-013 default doctor | **Done** | Vitest |
| P3-4 Appointment reference shown to patients | **Done** | Vitest |
| P3-5 Bill read as "Unpaid" right after a payment | **Explained.** Read skew between two queries; monitor only | Server reproduction |
| New: booking slots from the wrong day | **Found and fixed** | Vitest (RED, then GREEN) |

## 2. What changed, item by item

### P1-1 Discharge from the browser
A manual Playwright reproduction (a copy of the e2e database, the same doctor account) showed the UI completes the discharge on a fresh page and on the tick-then-click path. The earlier hang was in the test step: it clicked before readiness had refreshed. The step now:
1. ticks the four checklist items;
2. waits for "Ready to complete";
3. confirms the dialog;
4. waits for the toast "Discharge completed and bed released".

No application change was needed. Evidence: `18-discharge-ui-reproduction.png`, journey step 18 and 18b PASS.

### P1-2 Nurse profile and authorship
- **New nurses:** `backend/users/staff_invite.py` → `_ensure_nurse_profile` links an unlinked Nurse record with the same email, or creates one, when a Nurse invite is accepted, as was already done for doctors.
- **Old records (policy 5, "Audit log se naam jodo"):** new command `python manage.py attribute_nursing_records` in `backend/nurses/management/commands/`.
  - It is a dry run by default; `--apply` saves; `--hospital <id>` limits it to one hospital.
  - It attributes an assessment or note only when the audit log names its creator and that user holds the Nurse role at the record's hospital. Anything else is reported and left alone.
  - Every change is audited.
  - **It was not run on any real database.** Run it as a dry run first and read the report.
- **Tests:** `users/test_staff_invite.py` (two new tests), `nurses/test_attribute_records.py` (four tests).

### P1-3 Hospital day (IST) vs UTC
- `backend/config/hospital_time.py` gained `day_bounds`, `on_hospital_day` and `hospital_date_range`. They compare against the hospital day's start and end in UTC instead of `__date` (the UTC date).
- **Replaced in:**
  - home stats (today's patients, emergencies and revenue);
  - token issue (visit reuse);
  - nurse shifts and today's tasks;
  - audit, pharmacy and unbilled-work date filters;
  - the per-day report series (`TruncDate` in IST);
  - forecasting.
- **Tests:** `backend/config/test_hospital_day.py` re-runs the visit-reuse and today's-stats tests with the clock frozen at 02:30 IST and late evening.

### P2-1 Lab Staff and visits (policy 4: "Haan, read-only")
- Lab Staff may list **one patient's** visits (`?patient=` required) to link a walk-in order to its visit.
- They cannot browse all visits, open a visit, or create or change one.
- The rows they get carry no clinical text: id, patient, hospital, doctor, doctor name, visit type, date and status only.
- **Files:** `backend/encounters/views.py` (`LabStaffVisitLookup`, `LAB_LOOKUP_FIELDS`).
- **Tests:** `backend/encounters/test_lab_visit_lookup.py` (5 tests, including that the order saves with the visit). `VisitSelect` already showed the field when the list could be read, so no UI change was needed.

### P2-2 Medicine GST: earlier finding corrected
"Add Medicine" does have a "GST %" field. The validation run missed it. The journey now stocks a medicine at 12 % GST, and the bill shows the tax.

### P2-4 Discount, GST and refunds in the journey
- **New refund screen:** a "Refund" button on bills with money paid (Admin, Hospital Manager, Billing Staff) opens `src/components/billing/RefundDialog.jsx`.
  - It asks for the amount, reason (required) and method.
  - It caps the amount at the amount paid, works in paise, and sends one idempotency key per dialog.
  - Before this, refunds existed only in the API.
- **Journey step 15 now covers:**
  - a discount on the visit bill;
  - GST on the medicine bill;
  - a ₹20.25 refund on the lab bill, which becomes "Partially Paid";
  - settling that refund with a discount;
  - reconciliation of subtotal + tax − discount against every bill.
- **Tests:** `src/__tests__/refundDialog.test.jsx` (4).

### BUG-011 Queue and visit status
- **One called patient per doctor and day.** Calling another patient (Call, or Call Next on a waiting token) while one is Called, Acknowledged or Ready is refused with 409. The message names the token and says to start, skip or mark no-show first. Re-calling the same patient still works.
- **Consultation shows the queue state.** Visits now carry `queue_status` (from the latest token, annotated on the list). Consultation shows "Called", "Acknowledged" or "Ready" for a waiting visit, so both screens agree.
- **Files:**
  - `backend/encounters/views.py` (`_already_called`);
  - `backend/encounters/serializers.py`;
  - `src/utils/visitQueueStatus.js`;
  - `src/pages/Consultation.jsx`.
- **Tests:** `backend/encounters/test_one_called_token.py` (7), `src/__tests__/visitQueueStatus.test.js` (2).

### BUG-012 Patient portal probes
- The browser remembers whether the session is staff or patient (`hms_account`; no name, id or token), and start-up asks the matching "who am I" endpoint first.
- A patient session lists hospitals from the public directory instead of the staff endpoint.
- **Files:**
  - `src/services/api.js`;
  - `src/assets/context/AuthProvider.jsx`;
  - `src/assets/context/HospitalsContext.jsx`.
- **Tests:** `src/__tests__/authStartup.test.jsx` (3).

### MF-006 Structured lab results: already present
- **Backend:** `LabResult.result_data` and `abnormal_flags`, and per-hospital `LabReferenceRange` (parameter, unit, sex, low/high, critical low/high).
- **Lab page:** asks for each configured parameter's value, so the server can flag it.
- **Not changed.** A full result-entry form (instead of one prompt per parameter) would be a UI improvement, not a missing capability.

### MF-007 Catalogue lookups when ordering
- **New read-only endpoints:**
  - `GET /api/billing/price-list/catalogue/?hospital=` gives the services in force today that a doctor orders by name (consultation and bed excluded). It returns names and categories, not prices.
  - `GET /api/pharmacy/formulary/?hospital=` gives medicine names once each, with the generic name and whether any is in stock. It returns no prices, batches or counts.
- **Who can read them:** doctors, besides the roles that already read those lists. Doctors still cannot read the price list or the stock list themselves.
- **In the UI:** the Consultation "Service" field and the Prescription medicine "Name" field suggest from these lists. Typing anything else still works.
- **Files:**
  - `backend/billing/views.py`;
  - `backend/pharmacy/views.py`;
  - `src/hooks/useOrderingCatalogue.js`;
  - `src/pages/Consultation.jsx`;
  - `src/pages/Prescription.jsx`.
- **Tests:** `backend/billing/test_ordering_catalogue.py` (5), `src/__tests__/orderingCatalogue.test.jsx` (3).

### MF-010 Updates without reloading (patient portal)
- Patient dashboard, appointments, lab results, prescriptions and bills re-read their data every 60 s while the tab is visible, and as soon as the patient returns to the tab. The refresh is quiet: no loading spinner.
- The queue page already refreshed every 30 s.
- Push updates (SSE or WebSocket) were not added. Polling meets the need without new infrastructure.
- **Files:** `src/hooks/useRefreshTick.js` and the five patient pages.
- **Tests:** `src/__tests__/refreshTick.test.jsx` (2).

### MF-012 OPD nursing triage
- The server already let a nurse record for patients in today's queue (care scope `_nurse_care`, the `opd` part).
- The nurse's "Record Vitals" form now offers today's OPD patients who have not yet gone in to the doctor (Waiting, Called, Acknowledged or Ready), labelled with their token, after the ward patients.
- Saved without an admission, as a nursing assessment. The doctor's Consultation already reads these by patient ("Nursing observations").
- **Files:** `src/utils/opdTriage.js`, `src/pages/Nurses.jsx`.
- **Tests:** `src/__tests__/opdTriage.test.js` (2).

### P3-1 Setup wizard
After "Create hospital", `HospitalSetup.jsx` selects the new hospital, moves to the next step and refreshes the signed-in user, so later steps are enabled without a reload. Test: `src/__tests__/hospitalSetup.test.jsx` (2).

### BUG-009 Nurse billing banner
The Nurses page reads bills, and shows the billing tab, only for roles that may view Billing. A nurse no longer sees the "bills could not be loaded" error.

### BUG-010 Billing modal accessibility
The Create/Edit Bill and Payment form is now announced as a dialog (`role="dialog"`, `aria-modal`, titled by its heading), and Escape closes it.

**Fields now named:**
- the close button;
- the four service amounts;
- Discount, Amount Paid and Payment Method, tied to their labels.

The "Payment" action already opened a payment-only form.

### BUG-013 Default doctor
A signed-in doctor is the default referring doctor on new lab orders and prescriptions (`src/utils/ownDoctor.js`). Test: `src/__tests__/ownDoctor.test.js`.

### Appointment reference for patients
Patients see the same reference staff search by ("A007") on each appointment and in the booking confirmation (`src/utils/appointmentRef.js`, used by both the staff and patient pages). Test: `src/__tests__/appointmentRef.test.js` (2). Hindi strings added.

### New finding, fixed: booking slots from the wrong day
- **Bug:** in `BookAppointmentModal.jsx`, a slow answer for the previously chosen day could overwrite the new day's slots, so a patient could pick a time from the wrong day.
- **Fix:** the effect now ignores stale answers and clears the chosen time on each change.
- **Test:** `src/__tests__/bookingSlots.test.jsx`. It was RED before the fix and GREEN after.

### P3-5 "Unpaid" read right after a payment
Reproduced on a copy of the run's database. The invoice detail reads its status row and its payments in separate queries, so one read can mix the two moments. The stored data is always consistent. It is low impact; leave it as monitor-only, or read both in one transaction later.

## 3. Test results

| Suite | Result |
|---|---|
| Backend, full (`manage.py test`, Twilio variables blank) | 1562 run, 38 skipped, **2 failures, both from local `.env` settings**: `OTP_PROVIDER=twilio` without Twilio credentials, and an LLM model name. Both are ON HOLD areas. No code failure |
| Vitest (clean copy of the working tree) | **55 files, 278 tests, all pass** |
| ESLint `src e2e` | **0 errors**, 16 warnings (unchanged) |
| Production build | **Pass** |
| Journey `e2e/final-validation.spec.js`, run `FV83449` | **21 of 22 pass.** Every step's result is PASS except 11-laboratory PARTIAL (see below). The one failing test was step 15's final page reload, after all its billing checks had passed, while the machine was overloaded (load average above 140). The reload wait was changed to `domcontentloaded` |
| Regression specs and journey after the BUG-011, MF-007 and MF-012 changes | See §3a |

**Step 11 PARTIAL in `FV83449`:** that run came before P2-1, so the Lab Staff order was saved without a visit. It is PASS in `FV94672` (§3a).

### 3a. Final e2e re-run (after every change above)
- **Regression specs, 33 of 33 pass:**
  - `opd-to-bill`, `billing-decimal`, `appointments-nursing-pharmacy`;
  - `laboratory`, `patient-registration`, `nurse-mar`;
  - `ipd-bed`, `remaining-workflows`, `pharmacy`.
- **Journey run `FV94672`, 22 of 22 pass; every step PASS**, including 11-laboratory. The Lab Staff order is now linked to the visit (P2-1).
  - Evidence: `reports/e2e-evidence/remaining-work/FV94672/`.
- **Test-script change:** since P2-1, the lab charge lands on the visit bill, not on a separate bill. That is the intended behaviour. Step 15 now:
  - works out the expected discount from the visit bill's own lines;
  - adds the refund settlement to the existing discount (the discount field holds the bill's whole discount).
  - The first re-run (`FV94379`) failed steps 15 and 16 only because the script still assumed a separate lab bill.

## 4. Still open: needs the user

**ON HOLD (awaiting your APIs):**
- **Twilio (SMS/OTP), P1-4 and P3-2:**
  - Create a Twilio Verify service.
  - Put `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` (or the API key and secret) and `TWILIO_VERIFY_SERVICE_SID` in `backend/.env` yourself.
  - Register the sender for India (DLT) if required.
  - Then decide whether staff sign-in requires OTP.
- **Whisper and LLM (AI scribe):** waiting for your API choice and keys.

**Your decisions on 2026-11-25, and what was done:**

| Policy | Decision | Done |
|---|---|---|
| 1. Admin as the lab's second checker | Allowed (as now) | No change |
| 2. Compounders record vitals | No | No change |
| 3. One booking per doctor/day (BUG-008) | No limit | No change |
| 4. Lab Staff see visits | Yes, read-only | P2-1 above |
| 5. Old nursing records without a nurse | Attribute from the audit log | `attribute_nursing_records` (dry run first) |

**Your action:**
- **P2-3:** move the project folder out of iCloud Desktop (for example `~/Projects/hospital-automate`). In place, Vitest workers fail to start and Vite starts slowly. The tests above were run in a clean copy.
- **Old nursing records:** run `python manage.py attribute_nursing_records` (dry run) on the real database, read the report, then decide on `--apply`.
- **Review and commit:** nothing is committed or pushed. Another session shares this checkout, so stage only these files.
