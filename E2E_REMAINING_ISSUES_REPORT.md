# Remaining E2E Issues — Implementation and Verification Report

**Date:** 2026-11-05 · **Branch:** `ui/redesign-2026-10-25` · **Base:** HEAD `713874d` (the four fixes in `E2E_HOSPITAL_WORKFLOW_REPORT.md` were already committed there) · **State:** all changes below are **uncommitted**. Follows up §16 of `E2E_HOSPITAL_WORKFLOW_REPORT.md`.

Method: code edited in the project folder, copied byte-for-byte into an isolated `git archive` copy in the session scratchpad (fresh venv from `requirements-lock.txt`, `npm ci`), and every test, build and browser run done there. The project's real `backend/db.sqlite3` and `.env` were never read or touched. Synthetic data only.

Policy decisions taken from you before implementation:
- **F13:** remove pharmacist prescribing; add a paper-transcription workflow with a **second-person check** (another pharmacist or an Admin).
- **F9 returns on a paid bill:** lower the line and **refund the over-payment on that bill** automatically.
- **F1 format:** `PREFIX-YYYY-000001`, sequence per hospital per year.

## 1–2. Remaining issues and outcome

| ID | Issue | Status |
|---|---|---|
| F1 | No UHID at registration | **PASS** (unit, PostgreSQL race, browser) |
| F9 | Pharmacy sales never reach the patient invoice | **PASS** (unit, browser, DB) |
| F13 | Pharmacists could create prescriptions with no doctor | **PASS** (unit, browser, API probes) |
| F6 | No pending-prescription queue; wrong `RX-2026-001` placeholder | **PASS** (unit, browser) |
| F8 | Instructions not shown to the pharmacist / not printed | **PASS** (unit, browser) |
| F4 | Prescription page not linked to the consultation | **PASS** (unit, browser) |
| F7 | `/api/pharmacy-sales/` requested 6× per page load | **PASS** (now 2× in dev = StrictMode only; 1 per mount) |
| Queue | Choose appointment before token; no duplicate tokens; accessible button names | **PASS** (unit, PostgreSQL race, browser) |
| Seed | Medicines, stock batches, expiry, ICD-10 for demos | **PASS** (unit, browser) |

Found and fixed along the way:
- **Dispensing a Cancelled prescription was allowed.** It is now refused (400).
- **Pharmacists could edit doctors' prescription lines** through `/clinical/prescription-items/`. They now have read-only access.
- **Medicines could be rewritten after dispensing** (the item replace orphaned sales and bill lines). This is now refused.
- **A doctor could attach a prescription to another doctor's visit.** This is now refused; Admin is still allowed.
- **Pharmacy expiry banner:** it flagged a batch as expired for the whole of its last month (the page compared against the 1st of the month, the batch picker against month-end). Both now use month-end.

F7 root cause: `SaleReturns` fetched sales itself and refetched whenever its `refreshKey={sales}` prop changed. The page's own load replaced that array, so one load was page + child mount + child refetch = 3, doubled by StrictMode in dev = 6. It now renders the page's rows. StrictMode was not touched.

## 3. Files changed

**Backend (modified):** `hospital/models.py`, `hospital/serializers.py`, `patients/models.py`, `patients/serializers.py`, `patients/views.py`, `billing/models.py`, `billing/serializers.py`, `billing/views.py`, `pharmacy/models.py`, `pharmacy/serializers.py`, `pharmacy/views.py`, `pharmacy/dispensing.py`, `clinical/models.py`, `clinical/serializers.py`, `clinical/views.py`, `encounters/services/token_issue.py`, `users/permissions.py`, `users/management/commands/seed_demo.py`, `patients/test_patient_lookup.py`, `security_tests/test_seed_demo.py`.

**Backend (new):** `patients/uhid.py`, `patients/management/commands/assign_missing_uhids.py`, `billing/pharmacy_charges.py`, and tests `patients/test_uhid_generation.py`, `billing/test_pharmacy_billing.py`, `clinical/test_prescription_transcription.py`, `clinical/test_pharmacy_queue.py`, `clinical/test_consultation_prescription.py`, `encounters/test_token_issue_race.py`.

**Frontend (modified):** `pages/Patients.jsx`, `pages/admin/Hospitals.jsx`, `pages/pharmacy.jsx`, `pages/Consultation.jsx`, `pages/Prescription.jsx`, `pages/queue.jsx`, `components/pharmacy/SaleReturns.jsx`, `components/pharmacy/DispenseLine.jsx`, `assets/context/{HospitalsContext,PharmacyProvider,PrescriptionProvider}.jsx`, `services/api.js`, `utils/dispenseBatches.js`, `assets/i18n/hiPages.js`, tests `dispenseBatches.test.js`, `saleReturns.test.jsx`.

**Frontend (new):** `components/pharmacy/{PrescriptionQueue,TranscribeDialog,DispensingSlip}.jsx`, `components/queue/IssueTokenDialog.jsx`, `utils/{patientIdentity,prescriptionRecord}.js`, tests `prescriptionQueue.test.jsx`, `consultationPrescription.test.jsx`, `issueTokenDialog.test.jsx`, `patientIdentity.test.js`.

Also: a new `e2e-remaining` entry in `.claude/launch.json` (local, untracked).

## 4. Database migrations

All migrations add nullable or defaulted columns only; no existing data is rewritten. `makemigrations --check` reports no changes.

| Migration | Change |
|---|---|
| `hospital/0008_hospital_uhid_prefix` | `Hospital.uhid_prefix` (blank default) + unique-when-set constraint |
| `patients/0013_uhidsequence` | `UhidSequence(hospital, year, last_value)`, unique (hospital, year) |
| `billing/0009_invoice_prescription_invoiceitem_pharmacy_sale` | `Invoice.prescription` FK (SET_NULL); `InvoiceItem.pharmacy_sale` one-to-one (PROTECT), so a sale can be billed only once |
| `pharmacy/0007_medicine_tax_rate` | `Medicine.tax_rate` (default 0, check 0–100) |
| `clinical/0013_prescription_transcription` | `Prescription.source`, `original_prescriber_name`, `original_prescriber_registration`, `original_prescription_date`, `transcribed_by`, `verified_by`, `verified_at` |

**After deploying, run** `python manage.py assign_missing_uhids` (dry run), review the counts, then `--apply`. Existing UHIDs are never changed.

## 5. APIs created or modified

- `POST /api/patients/` now issues the UHID in the same transaction and returns it as `uhid`; the issue is audited (`patients.uhid.issue`).
- `POST /api/patient-hospitals/` with a blank `uhid` issues the next one. Blanking an issued UHID is refused.
- `PATCH /api/hospital/hospitals/{id}/` accepts `uhid_prefix` (A–Z0–9, max 10, unique).
- `GET /api/patients/lookup/` is now also open to **Pharmacist** (minimal fields, masked phone, max 20 results, audited). This is used to find the patient on a paper prescription.
- `GET /api/clinical/prescriptions/` gains comma-separated `status`, `search` (RX number, patient, UHID, doctor, outside prescriber) and `order=oldest`. Responses add `patient_uhid` and the source/transcription fields.
- **New** `POST /api/clinical/prescriptions/transcribe/` (Pharmacist, Admin) → saved as Pending Verification.
- **New** `POST /api/clinical/prescriptions/{id}/verify/` (Pharmacist, Admin; never the transcriber) → Confirmed.
- `POST /api/pharmacy-sales/dispense-prescription/` and `POST /api/pharmacy-sales/` (with a prescription) bill the sale and return `invoice {invoice_number, status, total, balance_due}`. Both refuse Cancelled and Pending Verification prescriptions.
- `POST /api/pharmacy-sales/{id}/return/` also adjusts the bill and returns `invoice` and `invoice_refund`.
- `GET /api/pharmacy-sales/` adds `invoice_number`; `/api/pharmacy/` adds `tax_rate`. Invoices expose `prescription` and items expose `pharmacy_sale` (both read-only).
- `POST /api/encounters/queue-tokens/issue/` now locks the appointment row (no duplicate tokens under concurrency).

## 6. Frontend pages and components

- **Patients:** UHID shown in the list, the phone list and the details dialog; the registration message names the UHID.
- **Hospitals admin:** "UHID prefix" field.
- **Pharmacy:**
  - Queue with tabs To dispense / Awaiting verification / Dispensed. Each row shows RX number, date and time, patient, UHID, doctor (or paper prescriber), each medicine with quantity and a stock badge, and status. It has search and pagination; selecting a row opens it.
  - The placeholder is now `RX-0001`.
  - The details panel shows UHID, paper source and verification, a "Verify against the paper" button, and a printable dispensing slip.
  - Dispense is hidden for Cancelled and unverified prescriptions.
  - The success message names the bill.
  - The medicine form has a GST % field.
- **DispenseLine:** dose, frequency, duration and instructions as separate fields; a blank instruction shows "None written".
- **Consultation:** "Write prescription" link → `/prescription?visit=<id>`. It also honours `?visit=` so you can come back to the same visit.
- **Prescription:** pre-fills visit and patient from `?visit=` (even when they're not on the first page of the dropdowns), shows a banner and "Back to consultation".
- **Queue:** "Issue token" opens a dialog to choose the appointment, showing patient, time, doctor, phone and reason. Every row button has a full accessible name ("Call token #3, …").
- **SaleReturns:** uses the page's sales instead of fetching them again. It tells the user when a return refunded money on the bill.
- **Hindi** strings added for the new text.

## 7. Security changes

- Pharmacists are read-only on `prescriptions` and `prescription-items` (the role table already said R); they write only through `transcribe`.
- Four-eyes rule: the transcriber can't verify; verification needs another Pharmacist or an Admin.
- Dispensing refuses Cancelled and Pending Verification prescriptions.
- A doctor (not Admin) may prescribe only on their own (or unassigned) visit. Patient-in-care and visit↔patient↔hospital checks still apply.
- Medicine lines on bills can't be edited or deleted, and a bill holding them can't be deleted; cancelling it instead is allowed.
- Hospital isolation: tenancy is enforced on every new endpoint; UHID search only matches the acting hospital's UHIDs.
- Audit events added: `patients.uhid.issue`, `clinical.prescription.transcribed`, `clinical.prescription.verified`, `billing.invoice.pharmacy_charges`, `billing.invoice.pharmacy_return`.
- Concurrency: UHID numbers come from a row-locking UPDATE; token issue locks the appointment row; dispensing already locked the prescription, so billing runs inside that lock.

## 8–12. Tests

| Suite | Before (HEAD) | After | Result |
|---|---|---|---|
| Backend, SQLite | 776 passed, 15 skipped | **847 passed, 17 skipped** | PASS |
| Backend, PostgreSQL 16 (throwaway, `REQUIRE_ROW_LOCK_TESTS=1`) | not run here | **847 passed, 0 skipped** | PASS |
| Frontend (Vitest) | 90 passed | **105 passed** | PASS |
| ESLint | 0 errors, 11 warnings | **0 errors, 11 warnings** (same warnings as HEAD) | PASS |
| `vite build` | — | built | PASS (existing >500 kB chunk advisory) |
| `makemigrations --check`, `manage.py check` | — | no changes, no issues | PASS |

**Skipped:** the 17 SQLite skips are the PostgreSQL-only row-lock tests: the 15 existing ones plus the 2 new race tests (UHID, token). All of them ran and passed on PostgreSQL.

**RED checks:**
- With the appointment lock removed, the token race test failed: 8 parallel issues for one appointment produced 6 different tokens plus errors. With the lock, exactly 1.
- The new frontend test caught a real race in the `?visit=` pre-fill (fixed).

**Failed:** none at the end.

**Tests added:** 71 backend and 15 frontend.

## 13. Browser E2E (real UI → real API → throwaway SQLite, `seed_demo` data)

| # | Step | Result |
|---|---|---|
| 1–2 | Receptionist registers "TEST E2E Remaining Patient" | **PASS:** "Patient registered. UHID DCH-2026-000001", shown in list |
| 3 | Book appointment (Dr Asha Mehta, 17:45) | **PASS** (A003) |
| 4–5 | Queue → Issue token dialog shows patient, time, doctor, phone, reason → token | **PASS:** Token #3. Only the new appointment was offered; seeded ones got no duplicates |
| 6 | Doctor's queue | **PASS:** own token visible, Dr Verma's patient hidden |
| 7 | Call → Start consultation | **PASS:** visit 3 opens "In Consultation" |
| 8 | Vitals 120/78, pulse 84, SpO₂ 98, 38.1 °C | **PASS** (DB) |
| 9 | Diagnosis via ICD-10 typeahead (now seeded) → J02.9 Final; clinical note | **PASS** (DB) |
| 10–11 | "Write prescription" → visit 3 + patient pre-filled → RX-0001 (Paracetamol 500mg ×15 "After food", Cetirizine 10mg ×5 "At bedtime") | **PASS:** visit 3, patient 6, auto-signed Dr Asha Mehta, Electronic |
| 12–14 | Pharmacist: RX-0001 in the queue with UHID, doctor, medicines, "In stock"; instructions per line; dispensing slip printed with instructions | **PASS** |
| 15 | Stock and expiry: earliest-expiring batch auto-chosen; expired / expiring-soon banners correct (after fix) | **PASS** |
| 16–19 | Dispense → "Charged on bill INV-814C416EC708 (₹50.40, Unpaid)" | **PASS:** 2 sales tied to items; StockTransaction OUT 15/5; stock 30→15, 100→95; 2 bill lines tied to the sales, 12% GST |
| 20 | Billing staff: bill visible on Billing page; pay ₹20 → Partially Paid (₹30.40 due); pay ₹30.40 → Paid | **PASS** |
| 21 | One chain in the DB: Patient 6 – UHID – Appointment 3 – Token 3 – Visit 3 – vitals/diagnosis/note – RX 1 – items – sales – stock txns – invoice lines; audit rows present | **PASS** |
| 22 | Isolation and roles (API probes, same DB; second synthetic hospital) | **PASS:** see below |
| F13 | Pharmacist transcribes a paper prescription (outside doctor, reg. no.) → RX-0002 Pending Verification. Verify is disabled for them; API dispense 400; self-verify 403; direct create/patch 403. Admin verifies → Confirmed → dispensed, ₹47.04 billed | **PASS** |
| F9 return | Return 5 of a sale on the **paid** bill → refund ₹11.20 on the bill, total ₹39.20, paid ₹39.20, Paid | **PASS** |

Probes:
- An other-hospital pharmacist got **403** with a spoofed `X-Hospital-ID`, and **404** for RX-1 and for verifying RX-2.
- Other-hospital billing staff got **404** for the bill; an other-hospital desk searching the UHID got **0 rows**.
- A receptionist creating or transcribing a prescription got **403**.
- Dr Verma prescribing on Dr Mehta's visit got **400**; a doctor calling the dispense endpoint got **403**; re-dispensing got **409**.

## 14. Performance (local dev stack: SQLite, Vite dev, StrictMode)

| Operation | Measured |
|---|---|
| Pharmacy page load | `/api/pharmacy-sales/` **2×** (was 6×); `/api/clinical/prescriptions/` 2× (queue). Both are 1 per mount × StrictMode |
| Dispense RX-0001 | `POST dispense-prescription` **49 ms** (including billing); then 1 sales reload (34 ms), 1 stock reload (28 ms), 1 queue reload (15 ms) |
| Prescription queue list | constant query count as the queue grows (test) |
| Full backend suite | 8 s SQLite (4 workers), 38 s PostgreSQL |

## 15. Known limitations

- Medicine lines carry GST per medicine; there is no per-line discount. Discounts stay invoice-level, set by billing (existing behaviour).
- A fully returned unpaid bill becomes total ₹0, which the existing billing rules mark "Paid".
- Changing a hospital's UHID prefix mid-year continues the same yearly number with the new prefix.
- Numbers used by rolled-back registrations are skipped (gaps are normal).
- No database unique constraint on `QueueToken.appointment`. The row lock prevents new duplicates; a constraint would fail to migrate if a past race already left duplicates. A check-then-constrain migration is a follow-up.
- Walk-in "Issue medicine" sales (free-text name, no patient record) are not billed to any patient, as before.
- Load testing and real SMS/WhatsApp delivery were **NOT TESTED** (`e2e` settings use the console provider).

## 16. Decisions requiring your approval

1. **Pharmacist access to `/api/patients/lookup/`.** This widens a boundary that an existing test deliberately pinned (2026-11-03). I retargeted that test to Inventory Staff, which is still refused. It's needed so the pharmacist can pick the patient named on a paper prescription.
2. **Automatic refunds on paid bills after a pharmacy return** (your choice). The refund is recorded with payment method Cash; change it if your counter refunds differently.
3. **Transcription rules:** an outside doctor's registration number is required, and paper older than 180 days is refused (`MAX_PAPER_AGE_DAYS`). Confirm both.
4. **Visit ownership:** a doctor may prescribe only on their own visit. Admin can still record for any visit.

## 17. Remaining production risks

- Run `assign_missing_uhids` on production data and review it before `--apply`.
- Applying the billing migration on a large PostgreSQL `billing_invoiceitem` table adds a unique index; plan it for a quiet window.
- Billing staff UI shows the pharmacy bills, but there is no dedicated "pharmacy bill" filter on the Billing page.
- The deployment rehearsal (`docker-compose.prod.yml`) was not repeated for these changes.

## 18. Git status

- Nothing committed or pushed.
- 36 tracked files modified (+1058/−126) and 27 new files: migrations, services, components, tests and this report. All are this session's work.
- Untracked files that are not mine and were left untouched: `.claude/` (shared launch config, where I added one entry), `.ua/`, `backend/db.sqlite3.backup-2026-11-03-before-migrate`, `backend/patients/tests 2.py`, `docs/POST_AUDIT_RECONCILIATION_2026-11-03.md`, `docs/RELEASE_CANDIDATE_AUDIT_2026-11-03.md`, `reports/database-view.html`.
