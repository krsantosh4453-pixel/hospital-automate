# Billing, pharmacy and laboratory integration (Prompt 4/5)

**Date:** 20 Nov 2026 · **Source:** [android-live-e2e-2026-11-19.md](android-live-e2e-2026-11-19.md) (BUG-06, BUG-07) · **State:** uncommitted, synthetic data only. No real payments or gateway, and no SMS, email or Twilio.

## Summary

| E2E finding | Status | What changed |
|---|---|---|
| Consultation not auto-billed | **Fixed** | Charged when the visit is Completed (visit PATCH or queue token "complete"). |
| Lab not auto-billed | **Fixed** | Charged when the result is **verified**. A test that is ordered, cancelled or never verified is never billed. |
| Bed/stay not auto-billed | **Fixed** | The final bill prices each started day from the price list, by the bed occupied at the start of that day. |
| No price list | **Fixed** | Hospital price list API, in INR, with effective dates. Prices are never edited. |
| Final IPD bill accepted ₹0 | **Fixed** | The typed `daily_rate` is gone (it must match the list if sent). ₹0 lines are refused, and a ₹0 bill is refused unless an Admin or Manager waives it. Discharge is blocked by an unexplained ₹0 or by any unpaid bill of the stay. |
| Same lab user entered and verified (BUG-06) | **Fixed** | Maker-checker on verification, plus an optional Admin exception policy that is audited. Results can no longer be edited through the API. |
| Pharmacy (worked in E2E) | **Kept** | Same figures reproduced. Added tests for duplicates, the stock ledger, returns and concurrency. |

## 1. Price list (`/api/billing/price-list/`)

- `ServicePrice` row fields: hospital, category (consultation, laboratory, bed, inpatient, procedure, other), code, name, `applies_to` (lab test name, bed type or visit type), optional doctor (a doctor's own consultation fee), `unit_price` Decimal(10,2), GST 0–100, currency `INR` only, `effective_from` and `effective_to`.
- DB constraints enforce: price > 0, GST range, INR only, and dates in order.
- **History is kept:**
  - A new price for the same service must start today or later, after the current one. The current one is closed the day before.
  - A price can be retired but never PATCHed or deleted (405).
  - Bill lines keep `service_price` (PROTECT) and copy the price, so old bills never change.
- **Who:** Admin or Hospital Manager add and retire prices. Billing roles read. Nurses and other roles get 403. Rows are scoped to one hospital.
- **Pharmacy prices** stay on the stock batch (`Medicine.price`, capped by MRP), because that is what dispensing charges. `GET /price-list/medicines/` lists them read-only.
- **Lookup order:**
  - Consultation: doctor + visit type, then doctor, then hospital + visit type, then hospital default.
  - Bed: bed type, then default.
  - Laboratory: exact test name only.
- Invoice lines may name a `service_price`. The list then sets the price, GST and description, and a different client price is refused.

## 2. Automatic charges (`billing/charges.py`)

- **One charge per service:**
  - Every charge has a key: `visit:<id>:consultation`, `labtest:<id>` or `admission:<id>:bed:<price id>`.
  - `InvoiceItem.charge_key` is unique when not empty.
  - The source row (visit or lab test) is locked with `SELECT … FOR UPDATE` before the check.
  - A retried or concurrent request returns the existing line.
- **Same transaction as the work:** a failed charge rolls back the completion or verification.
- **Where a charge goes:**
  - Admitted patient: the stay's running bill.
  - Otherwise: the visit's open bill.
  - If neither has an open bill (Unpaid, no payments), a new invoice is started.
- **No price:** the service is not billed and the clinical work is not blocked. The event is logged and audited as `billing.charge.unpriced`, so billing can add the price.
- Each captured charge is audited as `billing.charge.captured` (key, invoice, quantity, price code).
- **Cancelling a bill** that holds captured charges (or is a final bill) needs an Admin or Hospital Manager and a reason. Cancelling (`/cancel/`) voids its keys (`…#void-<invoice>`), so a replacement bill can charge those services again. The cancelled bill keeps its lines.
- **Captured lines are locked:** they cannot be edited or deleted, and an invoice holding them cannot be deleted. Cancel it instead.

## 3. Final bill and ₹0 rules

- `POST /ipd/admissions/{id}/final_bill/ {items?}`:
  - Takes the stay's running bill, or a new one.
  - Adds the bed days from the price list and any extra lines (each over ₹0).
  - Sets `is_final` and recalculates.
  - A total of ₹0 or less is refused and rolled back.
- If no bed price exists, the request is refused and no invoice or number is used.
- `awaiting_final_bill` now returns a `bed_charges` preview, shown on web and Android instead of a rate field.
- **Bed days:** started 24-hour periods since admission (at least 1, as before).
  - Day *k* is charged at the rate of the bed occupied at `admission + k days`.
  - Before the first bed, the first bed's rate applies. Days with no price for that date use today's price.
- **Discounts:** a discount can never bring a bill with charges to ₹0. Empty manual bills and ₹0 lines are refused.
- **Waiver** (`POST /billing/invoices/{id}/waive/ {reason}`):
  - Admin or Hospital Manager only, with a reason of at least 10 characters.
  - Refused once money was taken.
  - It writes an `InvoiceWaiver` row (amount, reason, approver, time) and audits `billing.invoice.waived`.
- **Discharge readiness** now blocks on:
  - no final bill;
  - a final bill at ₹0 without a waiver;
  - **any** live bill of the stay with money still due, including charges posted after the final bill.

## 4. Laboratory separation of duties (BUG-06)

1. **Entry:** Lab Staff (or Admin) enter the result once, under a row lock.
   - An empty result is refused.
   - A second entry returns 409.
   - The test is set to "Result Entered" (pending verification).
2. **Verification:** a different authorised user must verify.
   - The same user gets 403 with `same_user: true`.
   - Nurse, doctor and pharmacist get 403.
3. **No silent overwrite:**
   - `lab-results/` and `result-verifications/` are read-only (PATCH, PUT and DELETE return 405).
   - Every `LabResult` field is read-only in the serializer.
4. **Recorded:** `verified_by`, `verified_at`, a `ResultVerification` row (`self_verified`) and the audit events `lab.result.entered`, `lab.result.verified` and `lab.result.released`.
5. **Release:** only a verified result can be released. Patients see only released tests. The doctor of the visit sees it.
6. **Exception policy** (`GET/POST /api/laboratory/verification-policy/`):
   - Lab staff can read it. Only an Admin can change it, with a reason.
   - When it is on, a self-verification is allowed, marked `self_verified`, and audited as `lab.result.self_verified` with the policy reason.

## 5. Financial calculations (from the evidence run below)

| Bill | Lines | Calculation | Total |
|---|---|---|---|
| INV/26-27/000001 (OPD visit 1) | Consultation, Lipid profile | 1 × 500.00 + 1 × 650.00, GST 0% | **₹1,150.00** (Unpaid) |
| INV/26-27/000002 (RX-0001) | Pantoprazole × 5 | 5 × 6.00 = 30.00; GST 12% = 3.60 | **₹33.60** (matches E2E) |
| INV/26-27/000003 (stay 1, final) | Lipid profile; ICU 2 days; General 1 day | 650.00 + 2 × 5,000.00 + 1 × 1,000.00 | **₹11,650.00** (Paid) |

- **Stay timeline:** admitted 2 days 3 hours ago, so 3 started days.
  - ICU from admission until 25 hours in: covers day 0 (0 h) and day 1 (24 h).
  - General from 25 hours: covers day 2 (48 h).
  - 2 × ₹5,000 + 1 × ₹1,000 = ₹11,000 in beds. The lab test of the stay (₹650) was already on the running bill.
- **Discount before GST** (rule P1-05, unchanged):
  - Example: a ₹250.00 dressing (18% GST) with a ₹50 discount has tax = (250 − 50) × 18% = 36.00, total ₹236.00.
  - A test covers 2 × 250 = 500 + 18% = ₹590.00.
- **Waiver example:**
  - Bill: ₹1,000 + 5% GST = ₹1,050.00.
  - The waiver sets discount = gross 1,000.00, so tax becomes 0.00 and the total ₹0.00 (Paid).
  - `InvoiceWaiver.amount` = 1,050.00, the amount the patient would have paid.
- **Pharmacy return** (test): 2 of 5 returned and restocked gives a line of 3 × 6.00 = 18.00 + 12% = ₹20.16, and stock 75 → 77 with a ledger IN row.

## 6. Database evidence (fresh PostgreSQL 17, migrated, scripted through the real API)

```
admin adds CON-OPD / LAB-LIPID / BED-GEN / BED-ICU: HTTP 201
billing clerk adds a price: HTTP 403
admin adds a ₹0 price: HTTP 400 A price must be more than ₹0. Free care is recorded as a waiver.
doctor completes visit: HTTP 200 · retry the same request: HTTP 200 (no second line)
tech A enters result: 201 · tech A verifies own result: 403 "You entered this result…" · nurse verifies: 403
tech B verifies: 200 · tech B verifies again: 400 · PATCH lab-result directly: 405 · release: 200
dispense Aspirin (0 in stock): 400 "Insufficient stock of Aspirin. Available: 0."
dispense Pantoprazole x5: 201 · repeat: 400 "Only 0 of Pantoprazole is still to be dispensed."
final bill with daily_rate 0: 400 "Bed charges come from the price list (₹1000.00, ₹5000.00 per day)…"
final bill with a ₹0 extra line: 400 · final bill (price list): 201 total 11650.00
discharge before payment: 400 "The final bill has ₹11650.00 still due."
discount the final bill to 0: 400 · billing clerk waives it: 403
cash payment: 201 · same payment retried (same idempotency key): 200 · complete discharge: 200

invoice_number   | status | visit | rx | admission | is_final | discount | tax  | total    | paid
INV/26-27/000001 | Unpaid | 1     | -  | -         | False    | 0.00     | 0.00 | 1150.00  | 0
INV/26-27/000002 | Unpaid | -     | 1  | -         | False    | 0.00     | 3.60 | 33.60    | 0
INV/26-27/000003 | Paid   | -     | -  | 1         | True     | 0.00     | 0.00 | 11650.00 | 11650.00

invoice | category     | description                                  | qty | unit    | gst%  | subtotal | price     | charge_key
000001  | consultation | Consultation (OPD) · Dr Synthetic Evidence   | 1   | 500.00  | 0.00  | 500.00   | CON-OPD   | visit:1:consultation
000001  | laboratory   | Laboratory: Lipid Profile (LAB-1)            | 1   | 650.00  | 0.00  | 650.00   | LAB-LIPID | labtest:1
000002  | pharmacy     | Pantoprazole · batch DEMO-PAN-01 · RX-0001   | 5   | 6.00    | 12.00 | 30.00    | -         |
000003  | laboratory   | Laboratory: Lipid Profile (LAB-2)            | 1   | 650.00  | 0.00  | 650.00   | LAB-LIPID | labtest:2
000003  | bed          | Bed charges (ICU, ₹5000.00/day): 2 day(s)    | 2   | 5000.00 | 0.00  | 10000.00 | BED-ICU   | admission:1:bed:4
000003  | bed          | Bed charges (General, ₹1000.00/day): 1 day(s)| 1   | 1000.00 | 0.00  | 1000.00  | BED-GEN   | admission:1:bed:3

duplicate charge keys: []            payments: 000003 | payment | 11650.00 | Cash | ev-final-1 (one row)
stock: Pantoprazole DEMO-PAN-01 = 75, Aspirin DEMO-ASP-01 = 0 · ledger: OUT 5 "Pharmacy sale" SALE-1
lab: test 1 Released, entered ev_lab_a, verified ev_lab_b, verified_at set, self_verified False
     test 2 Verified, entered ev_lab_a, verified ev_lab_b, verified_at set, self_verified False
audit: billing.price.create ×4, billing.charge.captured ×5, lab.result.entered/verified/released,
       pharmacy.sale.create, billing.invoice.pharmacy_charges, billing.invoice.final_bill,
       billing.payment.create, ipd.admission.discharged
admission: Discharged · bed G-2: Available
```

## 7. Tests

| Suite | Result |
|---|---|
| New: `billing/test_price_list.py` (23), `billing/test_charge_capture.py` (18, 2 PostgreSQL-only), `laboratory/test_result_verification.py` (8), `pharmacy/test_dispense_integrity.py` (7, 2 PostgreSQL-only) | All pass |
| Full backend, SQLite | 1,352 run, 1,350 pass, 2 fail (date window, see below) |
| Full backend on PostgreSQL 17 (real row locks, parallel tests run) | 1,352 run, 1,350 pass, the same 2 date-window failures |
| Flutter (`flutter analyze`, `flutter test`) | No issues; 463 passed |

- **Not caused by this work:** `security_tests.test_home_stats…test_revenue_is_net_of_refunds` fails the same way on an untouched copy of the last commit. It ran at 01:39 IST, when the UTC date is still the day before, so "today" doesn't match. `encounters.test_visit_lifecycle…test_a_waiting_visit_opened_before_the_token_is_reused` (Prompt 1) has the same date-window cause.
- **Existing tests changed** (for behaviour this prompt changes on purpose):
  - The IPD final-bill tests now set a bed price instead of typing `daily_rate`.
  - The E2E lab step has a second technician verify.

## 8. Code review fixes

An independent review of the change found these issues. All were fixed and have regression tests:

- **(High) Cancel bypass:** a billing clerk could cancel a bill of captured charges, so discharge saw nothing due. Cancelling such a bill now needs an Admin or Hospital Manager and a reason.
- **(High) Line edits:** adding, editing or deleting one line could bring a bill under its discount to ₹0 "Paid", or leave it empty. Every line change now runs the ₹0 check, and the last line cannot be deleted.
- **(Medium) Repricing:** a price-list line could be repriced by a PATCH. Its price and GST are now locked.
- **(Medium) Waived bills:** these could take new lines. They are now frozen.
- **(Medium) Concurrent bills:** two charges for one patient at the same moment could each start a bill. The patient row now serialises bill creation.
- **(Medium) First prices:** two first prices for a service could both land. The hospital row now serialises new prices.
- **(Medium) Time zone:** bed days were dated in UTC. They now use the hospital's date (IST), like price start dates.

## 9. Data migration

- `billing 0012`: new tables and columns. Every existing invoice linked to a stay is marked `is_final=True`, because before this change only the final-bill action set that link. Existing medicine lines are tagged `pharmacy`. Amounts and statuses are not touched.
- `laboratory 0007`: the policy table and the `self_verified` flag.

## 10. Not done / follow-ups

- No screens yet for managing the price list or picking a priced line (web or Android). The API exists.
- No reject/correct step for a lab verifier. Today a wrong result is cancelled and re-ordered.
- Lab and consultation charges on a **cancelled** bill are not re-captured automatically. Bed days are, through the final bill.
- **No prices after deploy:** unpriced services are audited, not billed, and nothing back-fills them once a price is added. Each hospital must load its price list before go-live. A sweep command or an "unbilled work" list is a follow-up.
- **Hand-typed lines:** a hand-typed consultation or lab line has no charge key, so it plus the automatic charge would bill twice. Staff should pick the price-list line, and the next screen work should remove free-text service lines.
- Not re-run on the Android emulator. Verified through the API on PostgreSQL and in widget tests.
