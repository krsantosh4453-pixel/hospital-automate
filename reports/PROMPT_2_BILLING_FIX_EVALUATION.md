# Prompt 2 — BUG-002 Billing Decimal Precision Fix: Evaluation

- **Date:** 2026-11-24 · **Branch:** `ui/redesign-2026-10-25` (uncommitted working tree on top of `1343ce1`)
- **Source finding:** [`E2E_WEB_APPLICATION_AUDIT.md`](E2E_WEB_APPLICATION_AUDIT.md) → BUG-002 (and BUG-004, in scope via TEST 12)
- **Previous report:** [`PROMPT_1_ALLERGY_FIX_EVALUATION.md`](PROMPT_1_ALLERGY_FIX_EVALUATION.md) (unchanged)
- **Evidence:** [`e2e-evidence/billing-*`](e2e-evidence/)
- **Test data:** synthetic only, in throwaway databases (Django test DB, e2e SQLite, a temporary PostgreSQL 17 cluster). The development database and real financial records were not touched; no payment gateway exists or was called.

## Final verdict: **FIXED AND VERIFIED**

All 12 required financial cases pass at the API (Django tests), with the browser cases also passing end to end against the real backend. Every invoice produced by the browser runs reconciles to the paisa. The only non-passing regression items are pre-existing and unrelated (§12).

---

## 1. Original bug

Paying a ₹33.60 bill (₹30 + 12% GST) on the billing page was impossible: the "Amount Paid" field rejected 33.60 ("The two nearest valid values are 33 and 34"). Paying ₹33 left ₹0.60 that could never be cleared through the form.

## 2. Root cause

**Frontend (the defect):**
1. **Primary:** `src/pages/billing.jsx` money inputs (`paid`, `discount`, and the `consultation`/`laboratory`/`pharmacy`/`other` charges) were `<input type="number" min="0">` with **no `step`**. The browser default is `step=1`, so only whole rupees were valid. This blocked decimal payments **and** decimal invoice amounts typed on the page.
2. The Edit Bill path compared the typed amount with a **pre-tax** client total (`subtotal − discount`), so a GST bill could not be paid in full there even with decimals.
3. Payment maths used floats (`Number()`, `Math.round(x*100)/100`, `Number(paid).toFixed(2)`); `toFixed` would silently turn 10.999 into 11.00. Table and dashboard sums added floats (`33.6 − 33 = 0.6000000000000014`) and printed "₹33.6".
4. Status names did not match the server: the billing filter used "Partial"/"Pending" (server: "Partially Paid"/"Unpaid", so the filter matched **nothing**); the badge colour checked "Partial"; the patient dashboard and Bills page counted only "Unpaid"/"Partial" (BUG-004), so partially paid bills were invisible as owing.

**Backend (hardening, not the reported failure):** the models (`DecimalField(…, decimal_places=2)`), `Decimal` arithmetic, row-locked `record_payment()`, idempotency keys and overpayment checks were already correct. One gap: `record_payment()`/`record_refund()` call `money()` (`quantize(ROUND_HALF_UP)`) **before** validating, so an internal caller passing 10.999 would have recorded ₹11.00. The public API was protected by DRF's `DecimalField(decimal_places=2)`.

## 3. Files modified

| File | Purpose |
|---|---|
| `src/utils/money.js` (new) | Exact integer-paise helpers: `toPaise`, `fromPaise`, `formatRupees`, `paymentToRecord`, `hasBalanceDue`, `AMOUNT_FORMAT_ERROR` |
| `src/pages/billing.jsx` | `step="0.01"` + `inputMode="decimal"` on 6 money inputs; payments computed in paise via `paymentToRecord`; Edit-path limit uses the server total (with GST); table and stats from server `total_amount`/`total_paid`/`balance_due` in paise, always 2 decimals; filter/badge use server status names |
| `src/pages/patient/PatientDashboard.jsx` | "Bills with balance due" uses `hasBalanceDue` (counts Partially Paid) |
| `src/pages/patient/PatientBills.jsx` | "Balance due" filter and total due use `hasBalanceDue`; total summed in paise |
| `backend/billing/services.py` | `received_amount()`: payments/refunds with more than 2 decimals are refused, never rounded |
| `src/__tests__/money.test.js` (new) | 31 tests |
| `backend/billing/test_decimal_payments.py` (new) | 11 API/service tests |
| `e2e/billing-decimal.spec.js` (new) | 5 Playwright tests on the real billing and patient pages |

## 4. Backend implementation

```python
def received_amount(value):  # billing/services.py
    amount = Decimal(str(value).strip())            # invalid → 400 "Enter a valid amount in rupees."
    if amount != amount.quantize(CENT): raise ...   # 10.999 → 400 "at most 2 decimal places"
    return money(amount)
```
Used by `record_payment()` and `record_refund()` in place of the rounding `money(amount)`. Everything else was verified unchanged: `select_for_update` row lock, idempotent re-send (returns the original payment, HTTP 200), `amount > 0`, `amount ≤ balance`, status recalculated in the same transaction, `CheckConstraint(amount > 0)`, unique `(invoice, idempotency_key)`. Internal callers (`advances.py`, `pharmacy_charges.py`) already pass 2-decimal values; the full suite confirms no change for them.

## 5. Frontend implementation

- **Inputs:** `step="0.01"` (browser accepts paise, rejects a third decimal) and `inputMode="decimal"` (numeric keypad on phones).
- **Payment button:** `paymentToRecord({ total: server total_amount, alreadyPaid: server total_paid, enteredPaid })`, all in integer paise:
  - invalid, negative or >2 decimals → "Enter a valid amount in rupees, with at most 2 decimal places (for example 33.60)."
  - 0 → "must be greater than ₹0.00"
  - more than the bill → "cannot be more than the bill (₹33.60)"
  - not more than already received → existing "record a refund" message
  - otherwise sends exactly `fromPaise(new money)`, e.g. `"23.35"`.
- **Edit + pay / new bill:** same paise parsing; initial payment sends `fromPaise(paidPaise)`, never `toFixed`.
- **Duplicate submission:** unchanged existing protections (`useSubmitGuard` disables Save while saving; one idempotency key per opened form).
- **Display:** amounts come from the server's decimal strings and print with exactly two decimals (`₹33.60`, `₹1,000.99`); revenue and outstanding totals are integer-paise sums.
- **Status:** filter values `Partially Paid`/`Unpaid` (labels unchanged: "Partial"/"Pending"); badge colour for `Partially Paid`.

## 6. Database changes and migrations

**None.** All monetary columns were already `DecimalField(decimal_places=2)`; no data was migrated or altered.

## 7. Financial calculation strategy

- **Backend:** `Decimal` only; amounts must be exact to the paisa on the way in (refused otherwise); totals and tax use the existing `money()` quantization (ROUND_HALF_UP) as before.
- **Frontend:** strings from the user or API are parsed exactly into integer paise (`/^-?\d+(\.\d{1,2})?$/`, commas allowed); all comparisons and sums are integer paise; amounts are sent as 2-decimal strings. JS numbers are only ever already computed rupee values and are rounded to the nearest paisa (`Math.round(x*100)`). No new dependency.
- **Policy for >2 decimals:** refused everywhere (browser step, page validation, API serializer, service), never rounded.

## 8. API testing results (real endpoints, `billing.test_decimal_payments`)

| Request | Response | Effect |
|---|---|---|
| `POST /api/billing/invoices/` 1 × ₹30.00 @ 12% | 201, `total_amount "33.60"` | |
| `POST /api/billing/payments/` `"33.60"` | 201 | `Paid`, `total_paid "33.60"`, `balance_due "0.00"` |
| `"10.25"` | 201 | `Partially Paid`, `"23.35"` due |
| `"33.61"` | 400 "exceeds the outstanding balance (33.60)" | no row |
| `"0.00"`, `"0"`, `"-10.00"` | 400 | no row |
| `"10.999"`, `"10.001"`, `"33.595"` | 400 | no row |
| same `idempotency_key` twice | 201 then 200, same id | 1 row |
| `GET /api/billing/payments/?invoice=` | exact `"30.25"`, `"20.25"`, `"50.00"`, `paid_at`, `receipt_number`, `invoice` | |
| Billing-staff only | pharmacist/nurse/lab already 403 (audit + `billing` tests) | |

## 9. The 12 financial test results

| # | Case | Backend API | Browser | Result |
|---|---|---|---|---|
| 1 | ₹33.60 paid with ₹33.60 → Paid, ₹0.00 | ✓ | ✓ (+ reload) | **PASS** |
| 2 | ₹10.25 of ₹33.60 → ₹23.35, Partially Paid | ✓ | ✓ (₹10.25 of ₹100.50 → ₹90.25, + reload) | **PASS** |
| 3 | ₹100.50 = 30.25 + 20.25 + 50.00 → Paid | ✓ (status after each) | ✓ (10.25 + 90.25) | **PASS** |
| 4 | ₹33.61 on ₹33.60 → refused, unchanged, no row | ✓ | ✓ (no payment row) | **PASS** |
| 5 | ₹0.00 refused | ✓ | ✓ (page) | **PASS** |
| 6 | −₹10.00 refused | ✓ | (page refuses; unit test) | **PASS** |
| 7 | ₹10.999 refused (policy: never rounded) | ✓ API and service, refunds too | ✓ | **PASS** |
| 8 | ₹100.00 whole rupees | ✓ | ✓ existing `opd-to-bill` ₹325 | **PASS** |
| 9 | Same payment twice → one row | ✓ (idempotency key) | Save disabled while saving (existing guard) | **PASS** |
| 10 | Concurrent payments → no overpayment | ✓ sequential; ✓ **parallel on PostgreSQL** (`security_tests.test_concurrency`: 8 threads, exactly 2 × ₹50 accepted on ₹100) | n/a | **PASS** |
| 11 | Payment history exact (amount, time, bill, kind) | ✓ | — | **PASS** |
| 12 | Patient and admin dashboards | ✓ unit (`hasBalanceDue`) | ✓ patient tile = API owing count; Bills "Balance due" lists the bill with ₹23.35; admin filter "Partial" shows the bill, "Paid" hides it | **PASS** |

## 10. Eight-step evaluation

| Step | Result | Evidence |
|---|---|---|
| 1 Code review | PASS | No float payment maths left in billing (`grep` for `Number(paid` / `toFixed(2)` in payment paths: none); no integer parsing; one helper module, no duplicated logic; unused float variables removed; ESLint clean |
| 2 Database | PASS | Columns already `DECIMAL(…,2)`; no migration; reconciliation below; 0 payment rows with sub-paisa amounts |
| 3 API | PASS | §8 |
| 4 Backend tests | PASS | `test_decimal_payments` 11/11; billing + pharmacy + financial-integrity: 189/189 (SQLite); concurrency + decimal on PostgreSQL 17: 33/33, 0 skipped |
| 5 Frontend tests | PASS | Vitest 215/215 (41 files) incl. `money.test.js` 31/31; production build passes |
| 6 Real browser E2E | PASS | `billing-decimal.spec.js` 5/5: ₹33.60 full → Paid ₹0.00 → persists after reload; ₹100.50 partial ₹10.25 → Partially Paid ₹90.25 → persists → completed; ₹10.999/₹33.61 refused with no payment row; ₹250.75 bill raised on the page; patient dashboard and Bills page |
| 7 Regression | PASS (pre-existing exceptions) | Full Playwright 39/40 (only the known flaky `nurse-mar`, 1/1 alone); full backend 1,470 tests, 2 known `.env` failures |
| 8 Independent verification | PASS | SQL recomputation over **every** invoice left by the billing, OPD-to-bill, advance-payment and pharmacy specs (10 invoices): total = net paid + balance for all; statuses consistent; 0 overpaid; 0 sub-paisa rows — `e2e-evidence/billing-reconciliation.txt` |

Reconciliation (from `billing-reconciliation.txt`):

| Invoice | Status | Total | Net paid | Balance | Check |
|---|---|---|---|---|---|
| …/000002 | Paid | 33.60 | 33.60 | 0.00 | ok |
| …/000003 | Paid | 100.50 | 100.50 | 0.00 | ok |
| …/000004 | Unpaid | 33.60 | 0.00 | 33.60 | ok (₹10.999/₹33.61 refused) |
| …/000005 | Unpaid | 250.75 | 0.00 | 250.75 | ok |
| …/000006 | Partially Paid | 33.60 | 10.25 | 23.35 | ok |
| 000001, 000007–000010 | (other specs) | | | | ok |

## 11. Browser screenshots

| File | Shows |
|---|---|
| `e2e-evidence/09-billing-paise-payment-blocked.png` | Before (audit): ₹33.60 rejected by the field |
| `e2e-evidence/billing-1-paid-33.60.png` | After: ₹33.60 paid, due ₹0.00, after reload |
| `e2e-evidence/billing-2-partial-10.25.png` | Partially Paid, ₹90.25 due, after reload |
| `e2e-evidence/billing-3-patient-dashboard.png` | Patient dashboard counting the partly paid bill |

## 12. Regression results

- **Playwright (full suite):** 39/40 pass, including the existing pharmacy billing, advance payment, OPD-to-bill and laboratory journeys. The failure is `nurse-mar.spec.js`, flaky since before Prompt 1 (passes 1/1 alone; nurse pages do not touch billing).
- **Backend (full suite):** 1,470 tests; 2 failures (`ai_scribe…capabilities…`, `security_tests…production_boots…`) caused by the developer's `.env` (`AI_SCRIBE_MODEL`, `DJANGO_ENV`). They passed in a clean copy without `.env` (Prompt 1 report §12).
- **Frontend:** 215/215; lint clean; build passes.
- Authentication and RBAC: unchanged (no permission code touched).
- Prompt 1 evidence: the full Playwright runs re-captured the four `allergy-*.png` screenshots; they were restored to their committed versions so the previous report's evidence is unchanged.

## 13. Remaining limitations and separate findings (not fixed: out of scope)

1. **New-bill limit is pre-tax.** When a bill is first created on the page, GST is computed by the server, so the page can only check the initial payment against the pre-tax total. The server still refuses any real overpayment, but the invoice is then created without the payment (error toast). Paying in full afterwards with the Payment button works (TEST 1).
2. **Invoice detail / print view** shows a few amounts via `Number(...)` formatting; they display correctly in the cases seen but were not converted to paise formatting (display only, no calculation).
3. **BUG-010 (audit):** the Edit Bill / Payment modal is still not an accessible dialog and the "Payment" action opens the combined "Edit Bill" form. UI/UX scope, not BUG-002.
4. **Concurrency on SQLite:** the dev database cannot run true row locks; the parallel test is verified on PostgreSQL (production engine).
5. **Refund UI** was not exercised in the browser; the refund service precision guard is covered by a backend test.

## 14. Final verdict

**FIXED AND VERIFIED.** A ₹33.60 bill can be paid exactly; partial and multiple paise payments produce exact balances and the right status; overpayment, zero, negative and sub-paisa amounts are refused without creating records; duplicates and concurrent payments cannot double-charge; dashboards count partially paid bills. Verified by API tests, PostgreSQL concurrency tests, real-browser tests with reloads, and an independent database reconciliation. Nothing was committed or pushed.
