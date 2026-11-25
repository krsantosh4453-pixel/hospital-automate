# Prompt 5: remaining workflows, patient tracking, billing, radiology and security

**Date:** 2026-11-24/25 · **Branch:** `ui/redesign-2026-10-25`

All testing used isolated environments with synthetic data only:

- the Django test database (SQLite);
- a throwaway PostgreSQL 17 cluster on 127.0.0.1:55433, stopped after each use;
- the Playwright e2e backend (`config.settings.e2e`, fresh `seed_demo` database each run).

The development database was not used. No SMS, email, OTP or payment was sent; Twilio variables were blanked for test runs. Authentication, RBAC, hospital isolation and audit logging were not weakened anywhere.

## Phase 0: what was already done

- **Prompt 4 report:** the `PLAYWRIGHT_FULL_RESULT` placeholder now holds the real result: 46 passed, and 1 failure (`nurse-mar`, known flaky) that passed twice when re-run alone.
- **Diagnoses and IPD discharge:** these were already visible to patients before this prompt, through the patient timeline (`patients/timeline.py`, "My health record" on the patient dashboard, since commit `972c886`, 2026-10-28). The audit's "not visible" note did not match the code. I verified this with new tests and in the browser rather than rebuilding it.
- **Consultation and lab billing:** these already existed (`billing/charges.py`: consultation when the visit is Completed, lab when the result is verified, keyed lines so each is charged once). The audit saw them unbilled because the demo price list is empty. That is configuration, not code. No price is hard-coded.

## Finding-to-file map

| # | Finding | Main files |
|---|---|---|
| 1 | Patient diagnosis visibility (MF-008) | `backend/patients/timeline.py` (existing), `src/components/clinical/PatientTimeline.jsx` |
| 2 | Nursing status for the patient (MF-009) | `backend/patients/timeline.py` (`_ward_vitals`, new) |
| 3 | Discharge visibility (MF-009) | `backend/patients/timeline.py` (`_admissions`, existing) |
| 4 | Portal data accuracy (BUG-004) | `src/pages/patient/PatientDashboard.jsx`, `PatientBills.jsx` (Prompt 2) |
| 5–8 | Consultation, lab, X-ray billing; reconciliation (INT-004, MF-011) | `backend/billing/models.py`, `charges.py`, `unbilled.py`, `views.py`, `laboratory/views.py`, `src/components/billing/*`, `src/utils/billingLines.js` |
| 9 | Radiology role (MF-004) | `backend/users/models.py`, `permissions.py`, `role_permissions.py`, `seed_demo.py`, `laboratory/views.py`; web `RoleContext.jsx`, `navigation.js`, `roleHomes.js`, `staffRoles.js`, `roleRouting.js`, `Radiology.jsx`, `admin/Roles.jsx`, `LanguageProvider.jsx`, `Sidebar.jsx`, `Navbar.jsx` |
| 10 | Radiology image upload (MF-005) | `backend/laboratory/imaging_files.py` (new), `patients/models.py`, `documents/views.py`, `patients/views.py`, `src/components/radiology/StudyImages.jsx` (new) |
| 11 | Order and visit association (INT-002) | `backend/laboratory/serializers.py`, `src/components/clinical/VisitSelect.jsx` (new), `Radiology.jsx`, `laboratory.jsx` |
| 12–13 | Patient cancel and reschedule (MF-003, INT-003) | `backend/appointments/views.py`, `src/components/patient/ManageAppointmentDialog.jsx` (new), `PatientAppointments.jsx`, `src/services/api.js` |
| 14 | Staff profile in browser storage (SEC-001) | `src/services/api.js` |
| 15 | Lab second-person verification (SEC-002) | `backend/laboratory/views.py` (unchanged), tests only |
| 16 | Mobile nursing temperature unit | `hospital-automate-mobile/lib/features/nursing/*`, `lib/l10n/*` |
| 17 | Compounder vitals | `src/pages/Compounter.jsx` |

## Verdicts

| # | Finding | Verdict |
|---|---|---|
| 1 | Patient sees diagnoses | **NOT APPLICABLE**: already implemented. Verified by a new test and in the browser |
| 2 | Patient sees nursing status | **FIXED BUT NOT FULLY VERIFIED**: API-tested; the browser seed has no admitted portal patient |
| 3 | Discharge shown only when real | **NOT APPLICABLE**: already correct. Verified by a new test |
| 4 | Portal totals and bill statuses | **FIXED AND VERIFIED** (Prompt 2 fix held; re-checked in the browser) |
| 5 | Consultation charged once | **NOT APPLICABLE** in code (already implemented); the blocker was **price configuration**. Verified end to end |
| 6 | Lab charged once | **NOT APPLICABLE** in code (already implemented); same price-list dependency. Verified end to end |
| 7 | X-ray charged once | **FIXED AND VERIFIED** |
| 8 | Reconciliation | **FIXED AND VERIFIED** for charges, partial payment and paise. Refunds are covered by existing backend tests only, not re-run in the browser |
| 9 | Radiology role and permissions | **FIXED AND VERIFIED** |
| 10 | Radiology image upload | **FIXED AND VERIFIED** |
| 11 | Orders linked to their visit | **FIXED AND VERIFIED** |
| 12 | Patient cancellation | **FIXED AND VERIFIED** |
| 13 | Patient rescheduling | **FIXED AND VERIFIED** (including a PostgreSQL race) |
| 14 | Staff data in browser storage | **FIXED AND VERIFIED** |
| 15 | Admin as lab second checker | **POLICY DECISION REQUIRED** (every other role, and the same person, is refused: verified) |
| 16 | Mobile nursing temperature unit | **FIXED BUT NOT FULLY VERIFIED**: unit and widget tests only; not run on a device against a live server |
| 17 | Compounder vitals persistence | **POLICY DECISION REQUIRED**: the role has no clinical-record permission; the form that only pretended to save was removed |

---

## Phase 1: patient tracking

**1. Diagnoses.**

- The timeline lists each diagnosis with its type, ICD-10 code, date and hospital, across all the patient's hospitals.
- Doctors' notes and unreleased results stay hidden (existing rules).
- **Test:** `patients.test_timeline.test_patient_sees_the_diagnoses_recorded_for_them`.
- **Browser:** "My health record" shows "Acute bronchitis (J20.9)" (`5-patient-health-record.png`).

**2. Nursing status.**

- **Root cause:** the timeline had no source for ward vitals (`NursingAssessment.vitals`), and nursing notes are hidden from patients (kept).
- **Fix:** a `_ward_vitals` source emits only the measured values (BP, pulse, SpO₂, respiratory rate, and temperature with its unit, or "(unit not recorded)" for older readings). The nurse's free-text assessment and nursing notes are never included. It reads the existing records, so there is no second source of truth.
- **Test:** `test_patient_sees_ward_observations_with_units_but_no_nursing_notes`.

**3. Discharge.**

- An outpatient visit never produces a "Discharge" event: completing a visit is a "Visit".
- An admission shows "Discharged" only when `discharge_date` is set, with the finalized summary and the follow-up instructions; a draft summary is never shown.
- **Test:** `test_discharge_appears_only_for_a_real_inpatient_discharge`.
- The IPD discharge flow is unchanged (`ipd-bed.spec.js` passes).

**4. Portal accuracy.**

- After a partial payment, the patient's bills page shows the bill with ₹1,000.25 due (`6-patient-bill-due.png`). The dashboard's "Bills with balance due" uses `hasBalanceDue` (Prompt 2).
- Not addressed (out of scope): BUG-012, the staff-endpoint probes on patient page load.

## Phase 2: billing integration

**5–6. Consultation and laboratory.**

- Unchanged code. A completed visit and a verified lab result charge from the price list, once, keyed `visit:{id}:consultation` and `labtest:{id}`.
- Without a price, the work is not billed: an audit row (`billing.charge.unpriced`) is written and the work waits in "Unbilled work".
- **Each hospital must add its prices** (Billing → Price list). The demo seed ships none, and no default price was invented.

**7. X-ray and radiology (new).**

- New price category `imaging`.
- New `billing.charges.capture_imaging_study`. It runs in the same transaction as **signing the report** (the study row is locked), keyed `imaging:{id}`, on the visit's bill when the study has a visit.
- **Price lookup:** "<modality> <body part>" (for example "X-ray Chest PA"), then the modality alone ("X-ray"). Never a default.
- Ordered, performed-but-unsigned and cancelled studies are never charged.
- Unpriced studies are audited and listed in Unbilled work. They can be charged in bulk or by picking them (`kind: "imaging"`), still only once.
- The price-list and Unbilled-work screens label the new category.

**8. Reconciliation (browser, isolated e2e database).** The patient "Demo Portal Patient" went through one OPD visit, with prices added through the real price-list API:

| Line | Key | Amount |
|---|---|---|
| Consultation (OPD, Dr Asha Mehta) | `visit:{visit}:consultation` | ₹500.50 |
| Laboratory: CBC | `labtest:{id}` | ₹250.25 |
| Imaging: X-ray Chest PA | `imaging:{id}` | ₹350.75 |
| **Visit bill INV/26-27/000001** | | **₹1,101.50** (equal to the sum of its lines, to the paisa) |
| Pharmacy bill (Paracetamol 500mg × 2 + 12% GST) | prescription | ₹4.48 |

- Each service appears exactly once.
- A second report signature is refused (400), and no second charge appears.
- A partial payment of ₹101.25 set the bill to **Partially Paid**, with paid ₹101.25 and **due ₹1,000.25**, the same in the API, the billing page and the patient's bills page.
- Facts are in `reports/e2e-evidence/prompt-5/run-facts.json`; screenshots `4-visit-bill-partially-paid.png` and `6-patient-bill-due.png`.

## Phase 3: radiology

**9. Role.**

- New `StaffRole.RADIOLOGY_STAFF` ("Radiology Staff", radiographer) and `IsRadiologyStaff`.
- It may schedule and perform studies, and attach images. Lab Staff keep doing the same.
- Only doctors order and sign, unchanged.
- The role catalogue (`role_permissions.py`) matches the web `RoleContext` (checked by `security_tests.test_tenant_context`). Imaging belongs to the Laboratory module, as the backend's module map already had it.
- The web menu shows Radiology Staff the Radiology page, not Laboratory, Billing or Patients (a new `hideFor` on navigation items).
- **Verified refusals:** Radiology Staff get 403 on lab tests, invoices, patients, pharmacy sales, clinical vitals and nursing assessments. Another hospital's radiographer sees an empty list, and 403 when forcing this hospital.
- `demo.radiology` was added to `seed_demo` (synthetic).
- Every step is audited with who did it.

**10. Image upload.**

- **Endpoints:** `POST /api/laboratory/imaging/{id}/images/` (multipart), `GET` the same URL to list, and `GET …/images/{doc}/` for the file.
- **Who may upload:** Radiology Staff, Lab Staff and doctors. Nurses and pharmacists get 403.
- **When:** only before the report is signed. A signed or cancelled study takes no more images.
- **Validation** (`laboratory/imaging_files.py`): allowed extensions are PNG, JPEG, DICOM and PDF, and the content (libmagic) must match the extension. Files over 50 MB (the existing documents limit) and empty files are refused. Verified refusals: an `.exe`, a shell script renamed `.png`, a `.txt` and an empty file.
- **Storage:** the existing private `PatientDocument` storage, with a new nullable `imaging_study` link.
- **Serving:** only through the study endpoint (`Cache-Control: private, no-store`, `nosniff`, audited `image_read`). Never a `/media/` URL.
- **Access:** unauthenticated 401, pharmacist 403, another hospital's doctor 404.
- **Patients** see a study's images only once its report is signed, through the study endpoint, `/api/documents/` and the patient documents action alike.

**11. Visit association.**

- Lab and imaging order serializers refuse a `visit` that belongs to another patient.
- The Radiology and Laboratory order forms offer the patient's visits at this hospital and pre-select the open one (`VisitSelect`). Roles that may not list visits don't see the field.
- In the browser, the X-ray order saved the open visit (`1-order-linked-to-visit.png`).
- The ordering and reporting doctors are kept, as before.

## Phase 4: appointments

**12. Cancel.**

- `POST /api/appointments/{id}/self-cancel/` (patients only, own booking).
- Only a **Scheduled** booking whose time has not passed. Checked-in, in-consultation, completed, cancelled, no-show and past bookings are refused (400). Once checked in, the desk owns the booking; this follows the existing status flow and adds no new policy.
- The reason and time are audited (`appointments.appointment.self_cancelled`).
- A queue token, if any, is cancelled through the existing lifecycle, and the slot's place is freed.
- Another patient's booking gets 404. The staff `cancel` endpoint stays staff-only.

**13. Reschedule.**

- `POST /api/appointments/{id}/self-reschedule/`.
- It applies booking's own rules: past times, the 60-day window, working days, the slot grid, capacity (doctor row lock, `take_place`) and clashes.
- Refused moves (day off, full slot → 409, past, beyond window, off-grid time) leave the booking exactly as it was. One record is moved, and the audit records from and to.
- **PostgreSQL:** four patients moving into one remaining place at once give exactly one 200 and three 409s (`ParallelRescheduleTests`).
- **Browser:** Reschedule and Cancel appear only on upcoming Scheduled bookings. The dialog offers only the server's free slots and shows the day-off reason (`7-reschedule.png`, `8-cancelled.png`).

## Phase 5: security and clinical safety

**14. SEC-001.**

- Before: `user` (name, email, phone, employee ID), `roles` and `hospitals` were written to `localStorage` at staff sign-in, and never read back.
- Now they are never written, and copies from earlier builds are removed at startup. The profile still comes from `/auth/staff/me/`.
- Logout and an auth failure also clear `selectedHospital`. A sign-in drops a saved hospital the new user does not belong to.
- **Browser result:** after sign-in, storage holds only `hms_session` (a "1" flag), `selectedHospital` (id and name) and `sidebarOpen`. After logout, only `sidebarOpen` is left.
- No tokens, OTPs or credentials were ever stored (cookie sessions, unchanged).

**15. SEC-002.**

- Already enforced on the server: the person who entered a result cannot verify it, unless the hospital's audited exception policy allows it.
- **New tests:** every non-laboratory role (Receptionist, Billing, Compounder, Radiology Staff, Hospital Manager, Blood Bank, Inventory) and a lab user from another hospital are refused, with nothing recorded.
- **Not changed:** an **Admin** account can be the second checker, because `IsLabStaff` includes Admin, as every role permission here does. No document says whether an Admin-only account (for example a small clinic's pathologist) may verify.
- **Decision needed (lab director):** restrict verify/release to accounts holding the Lab Staff role, or keep Admin. A test pins today's behaviour so any change is deliberate.

## Phase 6: Prompt 4 temperature gaps

**16. Mobile.**

- The ward-vitals form asks for °C (`VitalField.temperature`), and now sends `temperature_unit: "C"` with every temperature. The server validates the reading against it (the Prompt 4 rule).
- Readings show as "Temperature: 37.2 °C". An older reading without a unit shows "(unit not recorded)", in English and Hindi. Nothing is converted.
- The web doctor view (`formatTemperature`) shows the same value and unit.
- **Not verified:** a run on a device or emulator against a live server.

**17. Compounder.**

- The Compounder role holds no clinical-record permission. The catalogue gives Pharmacy, Compounders, Inventory and Prescriptions (view), and clinical vitals are Doctor/Nurse only.
- The page's vitals form kept readings in React state, and its patient list was an empty constant, so it could never save. It is replaced by a notice that nurses and doctors record vitals.
- RBAC was not bypassed. Letting compounders record vitals is a **policy decision**.

## Database and migrations

All three migrations are additive, with no data migration; historical rows are untouched.

- `users/0007`: the role choice gains "Radiology Staff".
- `billing/0013`: the price category gains "imaging".
- `patients/0017`: nullable `PatientDocument.imaging_study` FK (PROTECT).

`makemigrations --check` reports no further changes.

## Test results

| Suite | Result |
|---|---|
| Backend, full (SQLite, Twilio blanked) | 1521 run: 1482 pass, 37 skipped, **2 fail**. Both failures are the known `.env`-caused tests, failing since before Prompt 4: `ai_scribe…test_capabilities_report_providers_without_keys_and_block_cnn` and `security_tests…test_production_boots_without_twilio_when_sms_otp_is_off` |
| New / changed backend tests | `laboratory.test_radiology_workflow` 19; `appointments.test_patient_self_service` 9 (1 PostgreSQL-only); `patients.test_timeline` +3; `laboratory.test_result_verification` +2 |
| Backend on PostgreSQL 17 | appointments, laboratory, billing, timeline, concurrency: **265 OK**; parallel reschedule race OK |
| Vitest | 45 files, **252 pass** |
| Flutter (nursing) | **49 pass**; `flutter analyze` clean |
| ESLint `src/` + `e2e/` | 0 errors (13 existing warnings) |
| Vite build | OK |
| Playwright `remaining-workflows.spec.js` | **9 / 9 pass** (last run 2026-11-25, with the stronger image check) |
| Playwright full suite | See the breakdown below |

**Playwright full suite, three runs.**

1. **First run:** 46 passed, 2 failed, 8 did not run. It overlapped a stalled SQLite test run on the same machine. `laboratory.spec.js` hung for 5.5 minutes, then the e2e SQLite database answered "database is locked". Re-run alone, `laboratory.spec.js` passed 2/2.
2. **Second run (quiet machine):** **55 passed, 1 failed.** The failure was `procurement.spec.js` "store adds a supplier…", the first navigation of a cold run (`page.goto: net::ERR_ABORTED`). After a usage-limit pause, Vite took 79 s to start: the iCloud-evicted workspace, over Playwright's 60 s limit. Once warm, `procurement.spec.js` passed **3/3** and the Prompt 5 spec **9/9**.

None of these failures traces to a Prompt 5 change.

## Regression: Prompts 1–4

- Prompts 1–4 specs (`allergy-status`, `billing-decimal`, `patient-registration`, `appointments-nursing-pharmacy`) passed in the quiet full run. Their backend and Vitest tests are in the full suites above.
- The full runs re-capture earlier prompts' screenshots. The 17 committed Prompt 1–4 images were restored to their committed versions afterwards.

## Remaining gaps and decisions

- **POLICY:** may an Admin-only account be the lab's second checker (SEC-002)?
- **POLICY:** may compounders record vitals?
- **POLICY (from Prompt 4):** should a patient be limited to one booking per doctor per day (BUG-008)?
- **Configuration:** each hospital must add consultation, lab and imaging prices; until then the work waits in Unbilled work, audited.
- **Not verified:** the mobile unit change on a device; patient-portal nursing observations in the browser (the API is verified).
- **Mobile:** no radiology screens; a Radiology Staff sign-in there gets the generic home.
- **Out of scope** (still open from the audit): BUG-009, BUG-010, BUG-011, BUG-012, BUG-013; MF-006, MF-007, MF-010, MF-012.
