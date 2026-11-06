# E2E Hospital Workflow Report — Patient → Appointment → Doctor → Prescription → Pharmacy

**Date:** 2026-11-05 · **Branch:** `ui/redesign-2026-10-25` (HEAD `47b140d` + the fixes below, uncommitted)
**Method:** real browser (Claude in-app browser pane, which you watched) driving the real React UI against the real Django API and a real SQLite database. Every "PASS" below was checked in the database, not just on screen. Timings come from the browser's Resource Timing API (`performance.getEntriesByType('resource')`) and the server's own timestamps.

---

## 1. Project architecture inspected

| Layer | What it is | Modules used in this flow |
|---|---|---|
| Frontend | React 19 + Vite SPA (`src/`) | `Patients.jsx`, `Appointments.jsx`, `queue.jsx`, `Consultation.jsx`, `Prescription.jsx`, `pharmacy.jsx` |
| API | Django REST Framework (`backend/`), cookie + CSRF auth, hospital-scoped viewsets (`users/viewsets.py: HospitalScopedViewSet`) | `patients`, `appointments`, `encounters` (Visit, QueueToken), `clinical` (vitals, diagnoses, notes, Prescription/Item), `pharmacy` (Medicine, Sale, dispensing), `procurement` (stock ledger) |
| Permissions | Role per hospital membership (`users/permissions.py`), doctor care-scope, module restrictions | Receptionist, Doctor, Pharmacist |
| DB | SQLite (dev / e2e), PostgreSQL (prod) | — |

**There is no "Queries" module in this project.** The doctor's worklist is **OPD Queue → Consultation** (Visits). Appointments become queue tokens and Visits at check-in.

Actual data flow: `Patient` → `Appointment` → (check-in) `QueueToken` + `Visit` → `VitalSign` / `Diagnosis` / `ClinicalNote` on the Visit → `Prescription` + `PrescriptionItem` (linked to Visit) → `Sale` rows per item + `StockTransaction OUT` → `Prescription.status = Dispensed`.

## 2. Test environment

- Isolated copy of the repo (`git archive HEAD`) in the session scratchpad, fresh venv from `requirements-lock.txt`, `npm ci`.
- Backend: `config.settings.e2e` (all outside services off, password login), throwaway DB `e2e_workflow.sqlite3`, seeded with `manage.py seed_demo` (synthetic "Demo City Hospital").
- Frontend: Vite on `http://localhost:5185`, proxying to Django on `127.0.0.1:8095`, auth required (no dev bypass).
- Launch config: `.claude/launch.json` → `e2e-workflow`.
- **The project's real `backend/db.sqlite3` and `.env` were never touched.** No real patient, real inventory or real credential was used.

Test accounts (from `seed_demo`): `demo.desk.main` (Receptionist), `demo.doctor1` (Dr Asha Mehta, Cardiology), `demo.pharmacist` (Pharmacist). An isolation fixture added a second hospital ("Other Test Hospital", id 2) with `other.pharmacist` and `other.doctor`.

## 3. Test patient (synthetic only)

| Field | Value |
|---|---|
| Patient ID | 6 (shown as `PAT-6`) |
| UHID | **none: see Bug F1** |
| Name | TEST E2E Workflow Patient |
| Mobile | 9000009901 (fictional test number) |
| Age / Gender | 38 / Male |
| Hospital | Demo City Hospital (id 1) |
| Registration status | Active |

## 4. Appointment booking (Receptionist)

| Field | Value |
|---|---|
| Appointment ID | 3 (UI: `A003`) |
| Patient ID | 6 |
| Doctor ID | 1 (Dr Asha Mehta) |
| Department | Cardiology (taken from the doctor; the form has no separate department field) |
| Date / Time | 2026-11-05 15:30 |
| Status flow | Scheduled → Checked In (token issued) → In Consultation → Completed |

Verified in: the DB row; the Appointment list after reload; the appointment detail; the doctor's queue (token #5, later #3 in the re-run). The patient profile is a details dialog and does **not** list appointments.

Check-in: Queue → "booked appointment(s) without a token" → **Token #5 → Visit 3 → Appointment 3** (DB-verified). In the first run this also gave duplicate tokens to two seed patients: **Bug F2, fixed**.

## 5. Doctor workflow

Signed in as `demo.doctor1`. The queue showed only her own tokens (Dr Verma's patients hidden), so doctor scoping works.

1. Called token #5 → Start consultation → Consultation screen auto-selected **Visit #3**. Patient identity, age/sex, phone and "No known allergies" were correct.
2. History: no prior vitals, diagnoses or notes (new patient), shown as empty.
3. Vitals recorded (fictional): BP 118/76, pulse 88, SpO₂ 98, temp 38.2 °C, RR 16, wt 70 kg, ht 172 cm.
4. Diagnosis: *Acute pharyngitis (TEST)*, ICD-10 **J02.9**, Final. The ICD suggestion list is empty because the seeded terminology table is empty, so the code was typed by hand.
5. Clinical note: chief complaint, HPI, past history, medications, examination, assessment, plan (all marked TEST DATA).
6. Prescription (on the separate Prescription page):

| Medicine | Qty | Dosage | Frequency | Duration | Instructions |
|---|---|---|---|---|---|
| Paracetamol 500mg | 15 | 1 tablet (500 mg) | 1-1-1 | 5 days | After food; TEST DATA |
| Cetirizine 10mg | 5 | 1 tablet (10 mg) | 0-0-1 | 5 days | At bedtime; TEST DATA |

7. Finalized via Queue → Complete. Token, appointment and (after the fix) visit → Completed.

Server timestamps: consultation started 09:14:00, completed 09:17:29 UTC = **3 min 28 s** total doctor processing. This includes the automation's typing and pauses, so it is not a pure system time.

## 6. Prescription verification

DB row `Prescription 1` (`RX-0001`): hospital 1, patient 6, doctor 1 (Dr Asha Mehta), visit 3, status Confirmed, no safety alerts. Both items match the table above field by field. It appears in the doctor's prescription list and is retrievable by the pharmacy. No duplicate prescription was created. The pharmacy flow was **not** bypassed by creating a separate pharmacy prescription.

## 7. Pharmacy workflow

| Step | Result |
|---|---|
| Prescription received | PASS: `RX-0001` found by ID; patient, patient ID, doctor and every medicine with dosage, frequency, duration and required quantity shown. Instructions are **not** shown (F8). |
| Prescription verified | PASS |
| Stock checked | Initially **Not in stock**. Dispense was correctly refused ("choose a stock batch") and nothing was faked. The pharmacist then added clearly labelled TEST stock through "Add medicine": `TEST-E2E-PCM-01` (100, exp 12/2027, ₹2) and `TEST-E2E-CTZ-01` (50, exp 10/2027, ₹3). Batches auto-matched by name, batch and expiry were shown, and required ≤ stock. |
| Substitution | Not needed (exact names). The server refuses a different-salt substitute (tested). |
| Billing status | Pharmacy ledger: SALE-1 ₹30 + SALE-2 ₹15 = **₹45**, correct. **Not posted to the patient's invoice** (F9). |
| Dispensing status | PASS: `Dispensed`, `dispensed_at` set, 2 `Sale` rows linked to the exact prescription items, `dispensed_by = demo.pharmacist`, stock 100→85 and 50→45, `StockTransaction OUT 15 / OUT 5`. |

## 8. Database verification (one chain, one patient)

```
Patient 6 ─ Appointment 3 ─ QueueToken 5 ─ Visit 3 ─┬─ VitalSign (1)
   (doctor 1, hospital 1 on every row)              ├─ Diagnosis J02.9 (1)
                                                    ├─ ClinicalNote (1, doctor 1)
                                                    └─ Prescription 1 ─ Items 1,2 ─ Sales 1,2 ─ StockTxn OUT ×2
```
All rows reference patient 6, hospital 1 and doctor 1. No duplicate patient or prescription was created. Status consistency after the fixes: token, appointment and visit all **Completed**, prescription **Dispensed**.

## 9. API integration and permission results

Probes ran through the Vite proxy with each role's real login (same origin and CSRF as the browser).

| Case | Result |
|---|---|
| Anonymous read of prescription / patient | 401 ✅ |
| Receptionist create prescription / dispense / add diagnosis | 403 ✅ |
| Doctor dispense via pharmacy endpoint / add stock | 403 ✅ |
| Pharmacist add diagnosis | 403 ✅ |
| Pharmacist re-dispense a dispensed RX | 409 "already been dispensed" ✅ |
| Over-dispense (partial 4 of 3) | 400 ✅ |
| Dispense more than stock | 400 "Insufficient stock" ✅ |
| Different-salt substitute | 400 ✅ |
| Other-hospital pharmacist: read RX-1 / list hospital 1 / spoof `X-Hospital-ID` / dispense | 404 / 403 / 403 / 403 ✅ |
| Other-hospital doctor: read patient 6 / visit notes | 404 / empty list ✅ |
| **Doctor PATCH a Confirmed RX → "Dispensed"** | **was 200 (bug F11)** → now **400** ✅ |
| **Doctor creates RX in another doctor's name** | **was 201 (bug F12)** → now **400** ✅ |
| Pharmacist creates a prescription (no doctor) | 201: **open decision (F13)** |

Hospital-wise isolation held in every test.

## 10. Performance measurements (actual)

API time = server round trip measured in the browser. UI time = from the click (or navigation) to the last API response that renders the result. Local dev stack (SQLite, Vite dev server, React StrictMode).

| Operation | API response time | UI loading time | Result |
|---|---|---|---|
| Patient creation | `POST /api/patients/` 68 ms (re-run 29 ms) | ≈111 ms (CSRF 17 + POST) | PASS |
| Appointment booking | `POST /api/appointments/` 18 ms (re-run 15 ms) | ≈64 ms (patient lookup 40 + CSRF 5 + POST 18) | PASS |
| Check-in (issue token) | `POST /queue-tokens/issue/` 72 ms | ≈140 ms incl. queue refresh (37 + 32) | PASS |
| Doctor appointment loading | queue-tokens 47 ms, appointments 39 ms | ≈100 ms after shell load | PASS |
| Patient history loading | patient 141, allergies 106, vitals 108, diagnoses 94, notes 108, orders 140 ms (parallel) | ≈1.12 s from navigation (DOMContentLoaded 103 ms; history calls finished in a 174 ms window) | PASS |
| Consultation saving | visit PATCH 112, vitals 83, diagnosis 65, note 52, call 69, start 73, complete 62 ms | each < 150 ms | PASS |
| Prescription generation | safety-check 34 + create 34 ms | ≈123 ms | PASS |
| Pharmacy prescription loading | `GET /prescriptions/1/` 56 ms | ≈60 ms | PASS |
| Stock verification | add stock 37 / 45 ms; re-lookup 55 ms; batch match client-side | ≈60 ms | PASS |
| Dispensing | `POST dispense-prescription` 56 ms (re-run 42 ms) | ≈140 ms incl. inventory/sales refresh | PASS |

Notes: every list endpoint is requested twice on page load (React StrictMode, dev only). `/api/pharmacy-sales/` is requested **6 times** on one Pharmacy page load (F7).

## 11. Failed tests (first run)

F2, F3, F11, F12 (details in §13). All four were fixed and re-run green.

## 12. Blocked tests

None blocked. Everything ran locally. SMS/WhatsApp notifications are off in `e2e` settings (console provider), so patient notifications were not delivered. That is by configuration, not a failure.

## 13. Bugs discovered

| ID | Severity | Where | Finding |
|---|---|---|---|
| **F11** | **High** | API + Prescription page | A doctor (any role with prescription write access) could set a prescription to **Dispensed** with no sale and no stock movement. The doctor-side "Dispense" button did exactly this (`PATCH {status:"Dispensed"}`), so records could say medicine was given when it wasn't. |
| **F12** | Medium-High | API | A doctor could create or move a prescription **in another doctor's name** (`doctor` was a free field). |
| **F3** | Medium | `encounters/services/appointment_status.py` | Start/complete consultation updated the token and appointment but **not the Visit**, so the Consultation screen showed "Waiting" during and "In Consultation" after the consultation. |
| **F2** | Medium (dev data) | `seed_demo` | Seeded tokens weren't linked to their appointments, so the Queue issued **duplicate tokens** to seeded patients. Also: "Issue token" is one click with no choice of patient (earliest first). |
| F1 | Medium | Patients | Registering a patient in the UI never creates a UHID / `PatientHospital` row, and no screen assigns one. The UHID strip and UHID search are empty for new patients. |
| F9 | Medium | Billing ↔ Pharmacy | Dispensed medicines never reach the patient's invoice. Billing has no reference to pharmacy sales; pharmacy keeps its own ₹ ledger. |
| F13 | Decision | API | Pharmacists can create prescriptions with no doctor. This may be intentional (transcribing paper prescriptions). |
| F6 | Low-Med (UX) | Pharmacy | No list of pending prescriptions. The pharmacist must type the RX ID, and the placeholder `RX-2026-001` doesn't match the real format `RX-0001`. |
| F8 | Low-Med | Pharmacy | Prescription **instructions** ("After food", "At bedtime") are not shown to the pharmacist. |
| F4 | Low (UX) | Consultation → Prescription | The prescription page doesn't carry the visit/patient over from the consultation. The doctor re-selects them (Doctor defaults to "Not specified"; now auto-signed server-side). |
| F7 | Low (perf) | Pharmacy | `/api/pharmacy-sales/` fetched 6× per page load. |
| — | Low (a11y) | Queue | Row buttons are all named just "Call" / "Skip" (no patient in the accessible name). |
| — | Info | Seed data | No pharmacy stock and no ICD-10 terminology in `seed_demo`. |

A finding I first logged as "over-dispense accepted" was **retracted**. Without `partial: true` the server always issues exactly the outstanding quantity and ignores the requested number (sale was 3 of 3, stock 85→82). This is documented behaviour.

## 14. Bugs fixed

| ID | Fix | Files |
|---|---|---|
| F11 | `PrescriptionSerializer.validate` refuses `Dispensed` / `Partially Dispensed` on API create/update (only the pharmacy dispense endpoint, which writes through the ORM, sets them). Removed the doctor-side PATCH "Dispense" button, its dialog and handler, the dead `dispensePrescription` provider helper, and the "Dispensed" status option. | `backend/clinical/serializers.py`, `src/pages/Prescription.jsx`, `src/assets/context/PrescriptionProvider.jsx` |
| F12 | A user acting as Doctor (not Admin) may only name themself as prescriber; with no prescriber named, the server signs it with their own doctor profile. Admin may still record for any doctor of the hospital. | `backend/clinical/serializers.py` |
| F3 | `sync_appointment_status` now also moves the Visit to In Consultation / Completed / Cancelled with the token (cancelled visits stay cancelled). | `backend/encounters/services/appointment_status.py` |
| F2 | `seed_demo` links each OPD token to its appointment and syncs the appointment to Checked In. | `backend/users/management/commands/seed_demo.py` |

Tests added (written first, seen failing, then passing):
- `backend/clinical/test_prescription_integrity.py`: 7 tests (no API "Dispensed"/"Partially Dispensed", no new RX starting Dispensed, cancel still allowed, no prescribing or moving to another doctor, self-sign default, admin may name any doctor).
- `backend/appointments/test_status.py::test_token_flow_moves_the_visit_along`
- `backend/security_tests/test_seed_demo.py::test_opd_tokens_belong_to_their_appointments`

## 15. Tests re-run after fixes

| Suite | Result |
|---|---|
| New/changed tests before the fix | 9 failed for the right reasons (RED) |
| Related suites (clinical, pharmacy, appointments, encounters, seed, patient journey, RBAC, role matrix, e2e workflows, doctor scope) | **158 passed** |
| Full backend suite | **776 passed, 15 skipped, 0 failed** |
| Frontend vitest | **90 passed** |
| ESLint on changed files | 0 errors (1 pre-existing warning at `Prescription.jsx:239`, also present on HEAD) |
| **Browser re-run of the whole workflow on fixed code** (fresh DB) | PASS: one-click token went straight to the TEST patient (no duplicates); Visit showed "In Consultation" automatically and "Completed" after finishing; the Status dropdown has no "Dispensed"; the doctor page has no Dispense button; saving under Dr Verma's name showed "Not saved · doctor: You can only prescribe in your own name."; saving with "Not specified" produced RX-0001 signed Dr Asha Mehta; the pharmacist dispensed RX-0001 (201, 42 ms), stock 100→85 / 50→45, ₹45 |
| API probe re-run | Doctor PATCH fresh RX → Dispensed: **400**; impersonation: **400**; real pharmacy dispense after that: 201; all isolation and role cases unchanged ✅ |

## 16. Remaining issues (not changed. They need a product decision or are larger than a safe fix)

1. **F1 UHID**: decide the hospital's UHID format (auto-generate at registration, e.g. `<prefix>-<seq>`, or enter it manually at the desk).
2. **F9 Billing**: post pharmacy sales to the patient's invoice (or decide pharmacy billing stays separate).
3. **F13**: should pharmacists be able to create prescriptions (paper transcription), and if so must they name the doctor?
4. F6 pending-prescription queue for pharmacy; fix the `RX-2026-001` placeholder.
5. F8 show instructions to the pharmacist.
6. F4 open Prescription pre-filled from the current consultation.
7. F7 duplicate `/pharmacy-sales/` requests.
8. Queue: let the receptionist choose which appointment to check in; give row buttons accessible names.
9. `seed_demo`: optionally add sample pharmacy stock and ICD-10 terms for demos.

## 17. Overall workflow completion

| Expected stage | Status |
|---|---|
| Test patient saved | ✅ (no UHID: F1) |
| Appointment booked | ✅ |
| Doctor appointment list | ✅ |
| Doctor opens patient | ✅ |
| Consultation started | ✅ |
| Diagnosis saved | ✅ |
| Medicines prescribed | ✅ |
| Prescription generated | ✅ |
| Pharmacy receives prescription | ✅ (by ID only: F6) |
| Pharmacy verifies medicines | ✅ |
| Stock verified | ✅ |
| Dispensing processed | ✅ |
| Billing processed | ⚠️ pharmacy ledger only, not on the patient invoice (F9) |

**Core clinical workflow: 12 / 12 stages pass end to end (100%)** after the fixes, with DB-consistent records and enforced role and hospital boundaries. Counting the billing hand-off as a stage: **12 / 13 (≈92%)**.

---
*Changed files are uncommitted in the shared checkout: `backend/clinical/serializers.py`, `backend/clinical/test_prescription_integrity.py` (new), `backend/encounters/services/appointment_status.py`, `backend/users/management/commands/seed_demo.py`, `backend/appointments/test_status.py`, `backend/security_tests/test_seed_demo.py`, `src/pages/Prescription.jsx`, `src/assets/context/PrescriptionProvider.jsx`, plus this report and a new `e2e-workflow` entry in `.claude/launch.json`.*
