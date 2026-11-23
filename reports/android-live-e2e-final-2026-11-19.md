# Android live E2E — final integration and readiness audit

Run 20 Nov 2026 (follows the 19 Nov report [android-live-e2e-2026-11-19.md](android-live-e2e-2026-11-19.md) and Prompts 1–4). Everything is uncommitted, as instructed.

**Setup**
- Real Android app: `hms_mobile` debug build on emulator `hms_pixel_api36`.
- Backend: a throwaway Django server, `config.settings.e2e`, SQLite, fresh `seed_demo` data, port 8191 (127.0.0.1 only).
- Test patient: **Meera Finaltest**, self-registered in the app, UHID **DCH-2026-000001**, Demo City Hospital.
- All data is synthetic.
- No SMS, calls, email or payment gateway were used. The test settings are console-only, and every payment was a desk record.

Every step below was checked three ways:
1. what the app showed;
2. the database row (ORM query on the e2e database);
3. where it mattered, a second probe through the API (repeat, wrong role, wrong data).

A 200 response alone was never counted as a pass.

## 1. Executive summary

- **The full patient-to-exit journey ran on the Android app**, from self-registration to the patient's final history view. Every record was confirmed in the database with correct patient, visit, admission and hospital links.
- **Steps that still needed the API:**
  - the Admin price list;
  - adding a bed (seed beds were full);
  - reading the e-mailed OTP (the test mailbox is in memory).

  The app has no screens for the first two (see §13).
- **All 11 original bugs now pass.** Five of them (BUG-05, 08, 09, 10, 11) had not been fixed by Prompts 1–4. They were fixed in this round.
- **Five more defects were found and fixed:**
  - medication orders stayed active after discharge;
  - queue, visit, bed and discharge-start changes were not audited;
  - an N+1 query on the IPD admissions list;
  - a misleading lab message;
  - a stale billing list.
- **Tests:**
  - Backend: 1,382 tests on SQLite and on PostgreSQL 17, 0 failures (the PostgreSQL run skips nothing).
  - Flutter: 474 tests pass and analyze is clean.
  - Web ESLint is clean on the changed pages.
- **Follow-up (20 Nov, same day):** first-dose scheduling of ward medication orders is fixed and verified live (§16). A once-daily order no longer starts at midnight and shows as Overdue at once.
- **Verdict: Ready for Controlled Pilot, not Production Ready.** Reasons are in §15.

## 2. The 11 original bugs

| Bug | Original severity | Fix implemented | Regression test | Result (live + DB) |
|---|---|---|---|---|
| BUG-01 self-registered patient can't join a hospital | Critical | Prompt 2: hospital chosen at sign-up, join from booking, reception link by mobile + DOB | `patients/test_registration_linking.py` | **PASS.** Registered in the app with a hospital. The DB shows UHID DCH-2026-000001 issued at once, with no fixture. |
| BUG-02 token/appointment stay Waiting after consultation | High | Prompt 1: `visit_lifecycle.change_visit_status` moves visit, token and appointment together | `encounters/test_visit_lifecycle.py` | **PASS.** After Complete, the DB has token, visit and appointment all `Completed`. The patient app says "No active token". |
| BUG-03 "Now serving" shows the highest token | Medium | Prompt 1 | `encounters`, `home` tests | **PASS.** "No token being served" before the consultation, "Now serving token 3" during it. |
| BUG-04 age stored as 1 | High (clinical) | Prompt 2: DOB required, age derived, placeholder 1s cleared (migration 0015) | `patients` tests | **PASS.** DB has DOB 1982-03-15 and age 44. Profile, nurse header and dispense screen show "44 y". |
| BUG-05 "Current prescriptions 0" for a partly dispensed RX; no issued quantity | Medium | **This round.** "Partially Dispensed" counts as current (mobile `record_models.dart`, web `PatientDashboard.jsx`, `PatientPrescriptions.jsx`). Patient card shows "Prescribed 5 · Issued 5 · Left 0". | `patient_repository_test.dart` (BUG-05 group) | **PASS.** Home shows "Current prescriptions 1", and the prescription card shows issued and left quantities. |
| BUG-06 same user entered and verified a lab result | Medium | Prompt 4: maker-checker on `verify_result`. **This round:** the app now explains the refusal. | `laboratory/test_result_verification.py`, `lab_screens_test.dart` | **PASS.** Result entered by demo.lab and verified by demo.admin (`self_verified=False`). demo.lab's own attempt got 403 `same_user` in the app and the API, and the app now says "a different authorised person must verify it". |
| BUG-07 no charge capture or price list; ₹0 final bill possible | Medium | Prompt 4: price list, charge capture, final bill from bed prices, ₹0 needs a waiver | `billing/test_price_list.py`, `test_charge_capture.py` | **PASS.** Consultation ₹500 was captured at completion and lab ₹650 at verification. The bed day (₹1,000) came from the list with no rate field. A repeat final bill returned 400. |
| BUG-08 ward vitals "Something went wrong" on first open | Low | **This round.** Root cause: `_history()` read `context.l10n` synchronously from `initState`, which throws in debug builds and was caught as a load error. Labels are now read after the fetch. | `nursing_screens_test.dart` "earlier vitals show on first open". It **fails on the old code** and passes now. | **PASS.** The panel loaded on first open, and vitals saved and showed. |
| BUG-09 sign-out from a deep page shows "session ended"; footer says "Not signed in" for patients | Low | **This round.** Sign-out goes to the start page (`app_shell.dart`). The footer uses `isSignedIn` (`sidebar.dart`). | `nursing_screens_test.dart` sign-out test, `auth_screens_test.dart` | **PASS.** 8 sign-outs from deep pages all ended on the start page. The drawer shows "Signed in as Patient". |
| BUG-10 discharged stay shows "Waiting for a bed"; checklist ticks invisible | Low | **This round.** `IpdAdmission.releasedBed` and `bedLabel()` show "Bed … · released <day>". Checklist icons use on-card colours. | `ops_logic_test.dart` (BUG-10 group) | **PASS.** Checklist icons are clearly visible (screenshot). The released-bed label is checked in unit tests; the discharged list row was not screenshotted. |
| BUG-11 profile shows DB id instead of UHID | Low | **This round.** `patient/me` returns `hospitals[{id,name,uhid}]`, and the profile shows the selected hospital's UHID. | `patients/test_registration_linking.py::PatientProfileUhidTests`, `auth_models_test.dart` | **PASS.** Profile shows "Patient ID DCH-2026-000001". |

## 3. More defects found in this round

| # | Severity | Problem | Fix | Test | Status |
|---|---|---|---|---|---|
| A1 | **Medium (clinical safety)** | Completing a discharge left the stay's ward medication orders active. The nurses' due list (`mar__is_active=True`, Scheduled) would show the discharged patient's doses as due or overdue from midnight. Seen live: admission 3 order still `is_active=True` after discharge. | `ipd/views.py complete_discharge` stops the stay's active orders (end date = discharge day) in the same transaction. Recorded doses are kept, and the audit row records how many orders were stopped. | `ipd/test_discharge_readiness.py::test_discharge_stops_the_stay_medication_orders` (fails on old code) | Fixed |
| A2 | Medium | Audit gaps. None of these left an audit row: queue token issue and status changes (call, start, complete, skip, no-show, cancel, requeue, Call Next), visit status changes, bed allocate/transfer/release, discharge start. | `record_audit` added in `encounters/views.py` and `ipd/views.py`, with `from` and `to` | `encounters/test_visit_lifecycle.py::QueueAuditTests` | Fixed. Live: `ipd.admission.discharge_initiated` recorded. |
| A3 | Medium (performance) | N+1 on `GET /ipd/admissions/`. `current_bed` ran `.filter().first()` per row and ignored the prefetch: 25 → 72 queries when the list grew from 2 to 14 stays. | `AdmissionSerializer.get_current_bed` reads the prefetched rows | `security_tests/test_query_budget.py::AdmissionListScalingTests` (fails on old code) | Fixed: query count stays flat |
| A4 | Low | A lab self-verify refusal read "Your role does not have access", which is wrong and confusing | `labErrorMessage` maps the `same_user` flag to a clear sentence (en + hi) | `lab_screens_test.dart` | Fixed, confirmed live |
| A5 | Low | After "Create final bill", the invoice list and totals stayed stale until Refresh was pressed (live: 2 invoices / ₹1,183.60 instead of 3 / ₹2,183.60) | `FinalBillSection(onBilled:)` reloads invoices and stats | `clinical_work_test.dart` | Fixed, confirmed live (4 invoices, ₹2,183.60 at once) |

Found but not fixed in the first pass. **All are now resolved or classified: see §16 for the first dose and §17 for the other seven.**

| Severity | Finding |
|---|---|
| ~~Medium~~ **Fixed (§16)** | An OD ward order written at 07:32 got its first dose at 00:00 that day, so it showed **Overdue** immediately. |
| ~~Low~~ **Fixed (§17-1)** | MAR card showed "Ordered by: demo.doctor1" (username) instead of the doctor's name. |
| ~~Low~~ **Fixed (§17-2)** | Discharge-plan checkboxes and the dispensing "At most N" hint were dark on teal. |
| ~~Low~~ **Fixed (§17-3)** | "Record: no known allergies" stayed enabled while an allergy was recorded. The server correctly refuses it (`patients/views.py allergy_status`). |
| ~~Low~~ **Fixed (§17-4)** | "Create final bill" had no confirmation dialog. |
| ~~Low~~ **Fixed (§17-5)** | Staff login always called `staff/login/otp/start/` first and got 400. |
| ~~Low~~ **Fixed (§17-6)** | On sign-out, the open page sent 1–3 requests without a token (401). |
| **Not reproduced (§17-7)** | Ward temperature typed "37.1" was stored as "37". The doctor's "36.9" was stored correctly, so this is most likely adb input lag under memory pressure, not an app defect. |

## 4. Files modified in this round

Backend:
- `backend/users/views.py`: `patient/me` returns `hospitals`.
- `backend/ipd/views.py`: stops orders on discharge; adds audit records.
- `backend/ipd/serializers.py`: fixes the N+1.
- `backend/encounters/views.py`: adds audit records.

Backend tests:
- `backend/patients/test_registration_linking.py`
- `backend/ipd/test_discharge_readiness.py`
- `backend/encounters/test_visit_lifecycle.py`
- `backend/security_tests/test_query_budget.py`

Web:
- `src/pages/patient/PatientDashboard.jsx`
- `src/pages/patient/PatientPrescriptions.jsx`

Mobile:
- `lib/core/security/session_controller.dart`
- `lib/features/auth/auth_models.dart`
- `lib/features/patient/data/record_models.dart`
- `lib/features/patient/ui/clinical_records_screens.dart`
- `lib/features/patient/ui/account_screens.dart`
- `lib/features/nursing/ui/ward_vitals_section.dart`
- `lib/features/navigation/app_shell.dart`
- `lib/features/navigation/sidebar.dart`
- `lib/features/ipd/data/ipd_models.dart`
- `lib/features/ipd/ui/ipd_ui.dart`
- `lib/features/ipd/ui/admission_screen.dart`
- `lib/features/ipd/ui/clinical_work_sections.dart`
- `lib/features/billing/ui/billing_screen.dart`
- `lib/features/laboratory/ui/lab_ui.dart`
- `lib/l10n/app_en.arb`, `lib/l10n/app_hi.arb`, and the generated l10n files

Mobile tests:
- `test/features/nursing/nursing_screens_test.dart`
- `test/features/operations/ops_logic_test.dart`
- `test/features/operations/clinical_work_test.dart`
- `test/features/auth/auth_models_test.dart`
- `test/features/patient/patient_repository_test.dart`
- `test/features/laboratory/lab_screens_test.dart`

Across Prompts 1–5 there are 110 uncommitted paths (`git status`).

## 5. Database migrations

Two were added by the first-dose follow-up (§16):
- `nurses/0012_medication_rounds`: `MedicationRound`, plus a unique (order, scheduled time) constraint on scheduled doses. It first removes only duplicate still-Scheduled copies and stops if two recorded doses collide.
- `nurses/0013_stop_orders_of_discharged_stays`: data only. It stops orders left active by discharges before fix A1, ending them on the discharge day. Nothing is deleted.

The 8 migrations from Prompts 1–4 are all uncommitted:
- `billing/0012_price_list_and_charge_capture`
- `clinical/0016_allergy_category`
- `hospital/0011_hospital_allow_patient_self_registration`
- `laboratory/0007_lab_verification_policy`
- `nurses/0011_mar_instructions`
- `patients/0014_alter_patient_age`
- `patients/0015_clear_placeholder_age`
- `patients/0016_patient_allergy_status`

`makemigrations --check` reports no changes. All migrations applied cleanly to a fresh SQLite database and to the PostgreSQL 17 test database.

## 6. API changes in this round

These are all additive, and no field was removed:
- `GET /api/auth/patient/me/` adds `hospitals: [{id, name, uhid}]`.
- `POST /ipd/admissions/{id}/complete_discharge/` also ends the stay's active medication orders.
- New audit actions:
  - `encounters.queue_token.issued`
  - `encounters.queue_token.status_changed`
  - `encounters.visit.status_changed`
  - `ipd.bed.allocated`, `ipd.bed.transferred`, `ipd.bed.released`
  - `ipd.admission.discharge_initiated`
- `GET /ipd/admissions/`: same response, fewer queries.
- First-dose follow-up (§16):
  - `POST /nurses/mar/` accepts `first_dose` (`now` | `at` | `next_round`) and `first_dose_at`, and schedules the doses in the same transaction.
  - `POST /nurses/mar/{id}/generate_schedule/` takes the same fields. A bare `start_date` no longer means midnight.
  - New `POST /nurses/mar/schedule-preview/` (doctor only).
  - New `GET/POST/PATCH /nurses/medication-rounds/` (Admin/Manager write, ward staff read).
  - New setting `MAR_OVERDUE_GRACE_MINUTES` (default 30).

## 7. Flutter screen changes

- Patient profile: UHID.
- Patient prescriptions: issued and left quantities; partly dispensed prescriptions count as current.
- Ward vitals: first load fixed.
- Shell: sign-out goes to the start page; drawer footer fixed.
- IPD: released-bed label; visible checklist icons.
- Lab: clear message on self-verify.
- Billing: list reloads after a final bill.
- Ward medication order (§16): first-dose choice (Next medication round / Start now / Specific time), and a review of the first and next doses before saving.

## 8. Role-wise results (live, app + DB)

| Role | Covered in the app | Result |
|---|---|---|
| Patient | Registration (DOB, hospital) → email OTP → login; profile (UHID, age 44); booking (past slots hidden, 1 row + idempotency key); queue (position 2 / ~15 min, then "No active token"); prescriptions; lab report; bills (2 due, ₹1,183.60); history with visit, vitals, diagnosis, prescription, lab, admission and finalised discharge summary | PASS |
| Receptionist | Dashboard, appointments, check-in → token #3 (repeat → same token, 200). Patient registration and linking screens exist and are covered by tests; they were not driven live. | PASS |
| Doctor | Queue (call → start), consultation: allergy (Penicillin, Moderate), 8 vitals, note, ICD-10 I20.9, prescription (2 lines), lab order, complete; admit + bed; ward medication order; discharge start, plan, summary, finalise, complete | PASS |
| Nurse | Ward list (own ward), record header, vitals saved on the stay, dose recorded as Administered, nursing note. A mis-tap on "Missed" was caught by the confirmation dialog. | PASS |
| Pharmacist | RX-1 queue with UHID; Aspirin blocked "Not in stock"; Pantoprazole ×5: stock 80 → 75, Sale ₹30, bill ₹33.60, RX Partially Dispensed. API: repeat → 400, wrong medicine → 400, doctor dispensing → 403. | PASS |
| Lab technician | Collect, dispatch, receive, process, enter result; self-verify refused; release | PASS |
| Admin / Billing | Admin: price list (API only, no app screen); verified lab result in the app. Billing: final bill from price list, cash payment RCPT-C9D1E78A9902 (idempotency key), no gateway notice shown. Bed management: API only. | PARTIAL (price list and beds have no Android screens) |

## 9. Patient-to-exit workflow

| Step | Result | Evidence |
|---|---|---|
| Registration | PASS | patient 6, DOB 1982-03-15, age 44, email_verified |
| Hospital linking | PASS | UHID DCH-2026-000001 at sign-up |
| Patient login | PASS | email + password |
| Appointment booking | PASS | Appointment #3, 20 Nov 09:00, Dr Asha Mehta, Scheduled |
| Reception check-in / token | PASS | Token #3, Visit 3 Waiting, appointment Checked In |
| Waiting time | PASS | position 2, ~15 min |
| Doctor login / consultation | PASS | Visit 3 In Consultation → Completed |
| Allergies / diagnosis | PASS | Allergy Penicillin (Drug, Moderate); I20.9 Provisional |
| Prescription | PASS | RX #1 Confirmed, 2 items |
| Lab order → testing → independent verification | PASS | LabTest 1: entered demo.lab, verified demo.admin, released |
| Pharmacy dispensing | PASS | stock 80 → 75, INV/26-27/000002 ₹33.60 |
| Admission / bed | PASS (bed added via API) | Admission 3, bed E2E-F1 Occupied |
| Nurse assessment, vitals, notes | PASS | NursingAssessment 1, NursingNote 1 |
| Ward medication | PASS | MAR 1, dose 1 Administered by Nurse Priya |
| Billing | PASS | INV-1 ₹1,150 (consult 500 + lab 650), INV-2 ₹33.60, INV-3 ₹1,000 final (bed), INV-3 paid |
| Doctor review / discharge plan / summary | PASS | DischargePlan (4 ticks), DischargeSummary finalised |
| Final discharge / exit | PASS | Admission Discharged, bed released → Available, 0 open tokens |

**Financial check:**
- INV-1: 500 + 650 = 1,150.00, GST 0.
- INV-2: 5 × 6.00 = 30.00 + 12% GST 3.60 = 33.60.
- INV-3: 1 day × 1,000.00 = 1,000.00, paid in full.
- Outstanding: 1,150.00 + 33.60 = 1,183.60, which matches the app and the patient view.

## 10. Security and data integrity (live probes + test suite)

| # | Check | Result |
|---|---|---|
| 1 | Patient to patient | PASS. Own record 200; other patient record and timeline 404; invoice list contains only patient 6. |
| 2 | Hospital to hospital | PASS (tests only). The live seed has one hospital. A foreign `X-Hospital-ID` header got 403. Covered by `security_tests/test_tenant_isolation` and related suites. |
| 3–8 | Role checks | PASS. Doctor dispensing 403; nurse price write 403; pharmacist and lab reading a full patient record 403; receptionist writing a diagnosis 403; billing verifying a lab result 403; patient reading nursing or IPD APIs 403; the other doctor sees no vitals on visit 3. |
| 9 | Unauthenticated requests | PASS. No token or a garbage token → 401. |
| 10 | JWT / session | PASS. Sign-out revokes the access token (old token → 401). The session survives an app cold restart and an APK reinstall. |
| 11 | Duplicate operations | PASS. DB checks found no duplicate charge keys, tokens per visit, booked slots, final bills per stay or payment keys. Repeat check-in returns the same token; repeat dispense and repeat final bill are refused. |
| 12 | Concurrent updates | PASS on PostgreSQL 17. All parallel row-lock tests ran (0 skipped). |
| 13 | Financial integrity | PASS. Every invoice equals its lines plus GST. One sale for RX-1. Lab results cannot be edited (PATCH/PUT/DELETE → 405). |
| 14 | Audit logging | PASS after fix A2. Before it, queue, visit, bed and discharge-start changes were not audited. |
| 15 | Sensitive data | PASS. The email OTP is stored only as an HMAC (plain column empty). Payment form warns never to type card/CVV/PIN. No secrets were added; `.env` was not touched or copied. |

## 11. Database verification (fresh e2e DB, after the run)

```
Patient 6       Meera Finaltest, DOB 1982-03-15, age 44, Female, email_verified
PatientHospital Demo City Hospital → DCH-2026-000001
Appointment 3   2026-11-20 09:00 Dr Asha Mehta → Completed
QueueToken 3    visit 3, appointment 3 → Completed
Visit 3         → Completed; VitalSign 138/88, HR 92, RR 18, 36.9 °C, SpO2 97, 68 kg, 160 cm
Allergy         Penicillin / Drug / Skin rash / Moderate
Diagnosis       I20.9 Angina pectoris, unspecified (Provisional)
Prescription 1  Partially Dispensed: Pantoprazole 40mg ×5 (issued 5), Aspirin 75mg ×30 (issued 0)
LabTest 1       Lipid Profile → Released; entered demo.lab, verified demo.admin, self_verified False
Medicine 5      Pantoprazole stock 80 → 75; Sale 1: 5 × 6.00 = 30.00
Admission 3     Discharged; BedAllocation E2E-F1 released; Bed E2E-F1 Available
MAR 1           Pantoprazole 40 mg 1 tab OD; administration 1 Administered (Nurse Priya)
Discharge       Plan: 4 items ticked; Summary finalised by Dr Asha Mehta
Invoices        INV/26-27/000001 ₹1,150.00 Unpaid (visit 3)
                INV/26-27/000002 ₹33.60 Unpaid (pharmacy)
                INV/26-27/000003 ₹1,000.00 Paid, final, admission 3, charge key admission:3:bed:3
Notifications   in_app sent 3; sms skipped 2; whatsapp skipped 2; voice skipped 1
```

## 12. Failed tests

None in the final runs:
- Backend on SQLite: 1,382 tests, OK (35 PostgreSQL-only tests skipped).
- Backend on PostgreSQL 17: 1,382 tests, OK, 0 skipped.
- Flutter: 474 tests pass; 51 live-API tests skipped (they need a live server and environment variables, and were not re-run this round).
- `flutter analyze` and ESLint (the 2 changed web pages) are clean.

The two date-window failures noted in Prompt 4 (`test_revenue_is_net_of_refunds`, a token-reuse test) did not recur. They depend on running near IST midnight.

## 13. Remaining blockers and gaps

- **Not in the Android app:** price list admin, bed/ward/room management, lab result reject/correct, opening documents, online payment.
- **Clinical:** ~~the once-daily first dose was scheduled at midnight~~. Fixed in §16; hospitals must configure their medication rounds.
- **Not live-tested:** hospital-to-hospital isolation (covered by tests); the reception registration and linking screens (covered by tests); the released-bed label on a discharged stay (unit tests only).
- **Environment:** the Mac (8 GB) swapped about 6 GB during the run, and adb input occasionally lagged. Mis-taps were caught by the app's confirmation dialogs.
- Nothing is committed: 110 uncommitted paths across Prompts 1–5.

## 14. External integrations intentionally postponed

| Integration | Status in the app |
|---|---|
| Twilio / SMS / WhatsApp / voice calling | Not configured. Deliveries are recorded as `skipped`, never as sent. |
| External email | Console / in-memory backend only. Self-registration OTP e-mails do not leave the server in this setup. |
| External OTP provider | Not configured. The app now reads `staff/login/options/` and goes straight to password login (§17-5); if OTP is required, the code step is kept. |
| Payment gateway | None. The payment screen says "There is no online payment gateway" and records desk payments only. |
| Other keyed APIs | No keys added; `.env` not edited. |

## 15. Production readiness

| Area | Assessment |
|---|---|
| Android workflows | The full patient-to-exit journey works in the app, apart from the price list and bed setup |
| Correctness | All 11 original bugs pass; 5 more fixed; first-dose scheduling fixed (§16); the 7 remaining findings are resolved or not reproduced (§17) |
| Security / RBAC | Passed every live probe and the full suites |
| Data integrity | No duplicates; exact stock and invoice arithmetic; locks proven on PostgreSQL |
| Audit | Complete for the journey after fix A2 |
| Performance | One N+1 fixed; other polled lists stay flat with more rows (queue, prescriptions, MAR, timeline, invoices, lab, price list) |
| Operations | Code is uncommitted. No production deployment, real email or SMS delivery, or real patient load has been tested. |

**Verdict: Ready for Controlled Pilot, not Production Ready.**

**Why it is ready for a pilot:** every internal, key-independent workflow works on the Android app against the real API and database, the role checks hold, and the finances reconcile.

**Pilot conditions:**
1. Commit and review the changes.
2. Configure a real email provider before allowing patient self-registration. Until then, reception registers patients.
3. Configure each hospital's medication rounds. Until then, once-daily orders need an explicit Start now or a specific time.
4. Price list and beds are maintained on the web.

**Why it is not production ready:** these conditions, the postponed integrations, and no production deployment or load evidence.

## 16. Follow-up: first-dose scheduling of ward medication orders (20 Nov 2026)

**Defect:** the app sent only today's date when scheduling a ward order, and the server read a bare date as 00:00. A once-daily order written at 07:32 therefore had its first dose at midnight and showed as Overdue at once (seen live: admission 3, Pantoprazole OD).

**Fix:**
- `backend/nurses/scheduling.py`:
  - **First dose options:** `now`, `at` (a chosen time), or `next_round` (the hospital's next configured round).
  - **Never in the past:** a past time is refused (with 5 minutes of clock tolerance).
  - **Default when the doctor chooses nothing:**
    - once-daily or less often → next round;
    - STAT → now;
    - more than once a day → now (unchanged);
    - no rounds configured, or a later start day → refused with `first_dose_required`, so the doctor must choose.
  - **Later doses:** whole-day intervals keep the local clock time, so they survive daylight-saving changes, and a round inside a DST gap moves to just after it. Shorter intervals step in real hours, crossing midnight correctly.
- `MedicationRound`: configured per hospital, with none assumed. Only Admin or Manager can add or switch off a round; a round's time can't be changed after creation, and rows are never deleted.
- **Overdue:** a dose is overdue only after its time plus `MAR_OVERDUE_GRACE_MINUTES` (server-computed `is_delayed`, default 30).
- **No duplicate doses:** unique (order, scheduled time) for scheduled doses, plus a row lock on the order while scheduling.
- **History:** recorded doses are never replaced. Each schedule is audited (`nurses.mar.schedule_generated`: mode, first dose, count).
- **Discharge:** still stops the stay's orders (A1). Migration 0013 stopped the order left active by the earlier discharge (MAR 1, stay 3).
- **App (Flutter):** the doctor picks the first dose and reviews the first dose, the next 3 and the total before saving. The order and its schedule are saved in one call, so a refusal leaves no order. There are clear messages when a choice is needed or a time is refused.
- **Web:** the order form sends the chosen first dose with the order (default: next medication round).

**Tests:**
- `nurses/test_first_dose_scheduling.py`: 32 tests. They cover next round, date boundary, rounds exactly now, no rounds, now, specific time (zone, past, tolerance, missing), order dates, PRN, STAT, daily/8-hourly series, DST step and gap, atomic refusal, old bare-date clients, regeneration without duplicates (history kept, DB constraint), preview, RBAC, rounds API, grace period, and the stale-order migration.
- Two existing tests were updated to the safe rules: a past 08:00 became 08:00 tomorrow, and a weekly order without rounds now chooses `now`.
- Flutter: `clinical_work_test.dart` covers the review before saving, refusal asking for a choice, Start now, cancelling the review, closing the time picker, and the wire format.
- **Totals:** backend 1,414 tests OK (SQLite); Flutter 479 OK; analyze and ESLint clean.
- **Not run:** the web unit test (`enteredInError.test.jsx`). The vitest worker times out starting from the iCloud-evicted `node_modules`, before any test runs. It was updated for the new request body.

**Live verification (emulator + database, 20 Nov, 12:14 IST):**

| Step | Evidence | Result |
|---|---|---|
| No rounds configured | `schedule-preview` OD → 400 "…none configured. Choose Start now or a specific time.", `first_dose_required: true` | PASS |
| Rounds configured (API: no admin screen in the app) | Admin added 08:00, 14:00, 20:00 (labelled demo). Nurse → 403; duplicate 08:00 → 400. | PASS |
| Doctor orders Pantoprazole OD in the app, default "Next medication round" | Review dialog: "First dose: Nov 20, 2026 2:00 PM (Next medication round); Then: Nov 21, 22, 23 2:00 PM; 8 doses scheduled" | PASS |
| Database | MAR 2 (stay 4): 8 doses, 20–27 Nov at 14:00 IST, first `Scheduled`, `is_delayed` false. Audit `{"first_dose_mode": "next_round", "first_dose": "2026-11-20T14:00:00+05:30", "doses": 8}`. | PASS |
| Nurse ward record | "Due Nov 20, 2026 2:00 PM" with no Overdue badge; the stopped order from the old stay is no longer listed | PASS |
| Past specific time via API | 400 "The first dose cannot be in the past…"; no extra order created | PASS |
| Regenerate twice | 8 doses, 0 duplicates | PASS |
| Dose on a stopped order | Nurse → 400 "No active doctor's order…" | PASS |

## 17. The seven remaining findings (20 Nov 2026, afternoon)

**Result:** 6 fixed and verified live (app + API + database), 1 not reproduced, 0 open. The first-dose scheduling from §16 was not changed. During live checks its 14:00 doses were unchanged.

| # | Finding | Root cause | Fix | Tests | Live result | Status |
|---|---|---|---|---|---|---|
| 1 | MAR "Ordered by: demo.doctor1" | `MARSerializer.get_ordered_by_name` used `get_full_name() or username`; demo doctors have no account name, and their real name is on the `Doctor` profile | Use the ordering user's Doctor profile name at the order's hospital (annotated in the MAR list query, no N+1), then account full name, then username. The app already shows the server value and hides an empty one. | `nurses/tests.py::MAROrderedByNameTests` (3); `nursing_screens_test.dart` | Nurse ward record: "Ordered by: Dr Asha Mehta" for account `demo.doctor1` | **PASS** |
| 2 | Dark checkboxes / "At most N" on teal | `CheckboxListTile` and the dispense `TextField` helper used the light-surface theme defaults on a teal card | Checkbox: light outline, light fill with teal tick, dimmed when disabled. Hint: `helperStyle` in `AppColors.onCard`, as `HmsTextField` hints already do. No dark theme exists. | `clinical_work_test.dart` (checkbox states), `pharmacy_screens_test.dart` (hint colour) | Screenshots: plan checkboxes and "At most 30" clearly readable | **PASS** |
| 3 | "No known allergies" enabled with an allergy | Button disabled only when status was already "none"; recorded allergies were not considered | Disabled when an allergy row is loaded or the status is "Has allergies", with the existing explanation shown. Load errors show no actions (unchanged). Server validation untouched. | `clinical_work_test.dart`: existing allergy, after adding, failed load, server refusal | Meera (Penicillin): button disabled with explanation; tap sent nothing. API still 409 `allergy_on_record`. Demo Ravi (none recorded): button enabled. | **PASS** |
| 4 | No confirmation for "Create final bill" | Button called the API directly | Confirmation naming the patient, days and price-list bed charges, explaining cancellation rules; Cancel/Create. The existing busy guard stops repeat taps; the list refresh (A5) is kept. Financial rules unchanged. | `clinical_work_test.dart`: cancel, confirm, failure then retry | Cancel → 4 invoices (none created). Confirm plus an extra tap → exactly one final bill INV/26-27/000005 ₹1,000 (`admission:4:bed:3`), list showed 5. API repeat → 400 "already has a final bill". | **PASS** |
| 5 | Staff login always called `otp/start` (400/503) | The app could not see the server's OTP policy, so it always tried OTP first | New public `GET auth/staff/login/options/` → `{otp_required, otp_available}` (no account data, tenancy exemption written). The app goes straight to password login only when codes are neither required nor available; otherwise, or if options can't be read, it keeps the code-first flow. Password login still refuses when OTP is required. | `users/test_staff_login_identifier.py::StaffLoginOptionsTests` (3), `auth_service_test.dart` (4) | 4 live staff sign-ins: **0** `otp/start` requests in the server log. Wrong password → 401, signed out. Required-OTP path covered by tests only (no SMS provider configured here). | **PASS** |
| 6 | 1–3 tokenless requests on sign-out | `SessionController.signOut()` notifies listeners and the open page reloads before navigation; the server had already revoked the session | `SessionController` has a closing flag, set before the server logout and by any sign-out, and cleared when new tokens are stored. `ApiClient` (`blockAuthenticated`) does not send signed-in requests while it is set. Anonymous auth calls, restore and refresh are unchanged; 401s are not hidden. | `api_client_test.dart`, `auth_service_test.dart` (2) | Sign-out from ward record, IPD stay, billing and the polling patient queue: **0** new 401 lines (queue watched 40 s after sign-out). Old access and refresh tokens → 401. Start page reached. | **PASS** (an in-flight request at the moment of sign-out is covered by tests only) |
| 7 | "37.1" stored as "37" | **Not reproduced.** Every layer keeps the text: decimal keyboard, no formatter, `wardVitalsJson` passes the string through, JSON stored as sent, displayed as stored. | No code change | `nursing_logic_test.dart` (37.1/36.9/38.5/37), `nursing_screens_test.dart` (typed 37.1 saved as 37.1) | App: 37.1 typed one character at a time → DB `{"temperature": "37.1"}`, shown "Temperature: 37.1". API: 36.9, 38.5 and 37 round-trip exactly. Doctor visit vitals: 36.90 (two-decimal field). The original "37" matches adb input lag dropping characters, which recurred in this session (passwords were truncated by the same lag). | **NOT REPRODUCED** |

**Follow-up on the remaining limitations (20 Nov, evening):**
- **Ward vitals are checked on the server** (`nurses/serializers.py check_ward_vitals`). The rules are the same structural ones as an OPD reading (`clinical.models.VitalSign`): whole numbers for BP, pulse, respiratory rate and SpO2; at most two decimals for temperature (≤ 999.99); nothing negative; SpO2 ≤ 100; only the five known keys. No normal range is applied, values are stored as sent, and an empty value means "not measured". Live: 37.123, −2, SpO2 101, "120/", pulse 72.5 and an unknown key were each refused with a field message and nothing was saved; a valid set with 37.1 was stored unchanged. Tests: `nurses/tests.py::WardVitalsValidationTests`.
- **The OPD vitals card shows the recorder's real name.** A shared helper, `users/staff_links.py staff_display_name`, uses the Doctor or Nurse profile at the hospital, then the account name, then the username. Live: "Nov 20, 2026 7:14 AM · Dr Asha Mehta" (was "demo.doctor1"). Tests: `clinical/test_vitals_immunizations.py::VitalsRecorderNameTests`.
- **The web unit test (`enteredInError.test.jsx`) still did not run.** vitest's worker times out on start-up because `node_modules` in the iCloud-synced folder is evicted; even copying it out stalls on iCloud downloads. ESLint passes on the changed web files.

**Tests:**
- Backend: 1,425 tests OK (SQLite), 35 PostgreSQL-only skipped; `makemigrations --check` clean.
- Flutter: 495 OK, 51 live-API tests skipped; `flutter analyze` clean.
- Web: not changed in this round. The web unit test from §16 (`enteredInError.test.jsx`) still could not run: vitest's worker times out starting from the iCloud-synced folder, even after pre-downloading `node_modules`.

**Migrations:** none in this round.
