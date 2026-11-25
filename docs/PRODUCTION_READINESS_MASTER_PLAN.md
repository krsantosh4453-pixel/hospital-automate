# Production Readiness Master Plan

Started 2026-11-21. Branch `ui/redesign-2026-10-25`, HEAD `cd6aef7`. Nothing in this plan has been committed, pushed or deployed.

## 1. Starting state

**Git:**
- 37 tracked report files are deleted in the working tree but not committed. This session did not delete them, and it has not restored or staged them. They include the root `*_REPORT.md` files, `SECURITY_FINDINGS.md`, most of `reports/`, and several in `docs/` (e.g. `FINAL_PRODUCTION_READINESS_REPORT.md`, `TEST_REPORT.md`).
- They were read from `HEAD` with `git show HEAD:<path>`.
- Untracked files that belong to other sessions or the owner were left alone: `.claude/`, `.ua/`, `backend/db.sqlite3.backup-2026-11-03-before-migrate`, `backend/patients/tests 2.py`, `reports/database-view.html`.

**Stack:**

| Part | Technology |
|---|---|
| Backend | Django 6, DRF, 28 apps. PostgreSQL in production, SQLite for development and tests. Celery and Redis. |
| Web | React and Vite, Vitest, Playwright. |
| Mobile | Flutter 3.47, Android. iOS has never been built. |
| Deployment | `docker-compose.prod.yml` with nginx. CI in `.github/workflows/ci.yml` and `mobile.yml`. |

**How it was run:** the project folder is iCloud-synced and stalls Python and Node. Every check ran in a `git archive HEAD` copy in the session scratchpad, with the changed files copied in. Only synthetic data was used.

**Sources read:**

| Kind | Documents |
|---|---|
| Registers | `docs/DEFECT_REGISTER.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/CLINICAL_HAZARD_REGISTER.md` |
| Audits | `docs/PRODUCTION_READINESS_AUDIT_2026-11-18.md`, `docs/SECURITY_HARDENING_2026-11-19.md` (by reference) |
| Reports at HEAD | `reports/billing-pharmacy-lab-2026-11-20.md`, `reports/android-live-e2e-final-2026-11-19.md` |
| This conversation | The 11-bug table (BUG-01 to BUG-11) |

**Baseline tests at HEAD:**

| Suite | Result |
|---|---|
| Backend | 1,402 run, 2 errors. Both errors came from the scratch copy missing `src/` and the compose files, which those tests read. With those files present the suite passes (see §4). |
| Web | 128 Vitest tests, plus 4 new ones = 132 |
| Mobile | 496 tests |

## 2. Status legend

| Status | Meaning |
|---|---|
| COMPLETE | Implemented and verified by tests in this session or in a cited earlier run |
| PARTIAL | Some functionality exists |
| NOT IMPLEMENTED | Missing |
| BROKEN | Existing implementation does not work |
| UNVERIFIED | Implementation exists, but evidence is insufficient |
| BLOCKED | Needs an external credential, provider, approval or person |

Findings are taken from the documents above. None were invented.

## 3. Task inventory

### 3.1 Clinical safety (P0)

| ID | Source | Finding | Status | Evidence / root cause | Plan and verification |
|---|---|---|---|---|---|
| H-14 | Hazard register (rated **Unacceptable**, 15) | No reference ranges, abnormal flags or critical-value alerting | **PARTIAL → engineering control COMPLETE (this session)**. Range values are BLOCKED on the lab director. | Before: `enter_result` stored whatever ranges and flags the client typed, and neither the web nor the mobile app sends any, so nothing was ever flagged. Done: see §4. | Each hospital loads its ranges. The lab director approves the values and the call procedure. |
| H-08 | Hazard register (Unacceptable, 15) | No dose-range, renal, hepatic, paediatric or weight-based checks | BLOCKED | Needs a licensed drug-knowledge database, or a formal acceptance by the P&T committee | Not built: engineering-invented dose limits would be unsafe |
| H-10 | Hazard register (Undesirable, 8) | PRN orders have no minimum interval and no 24-hour maximum | **Engineering control COMPLETE on backend, web and Android (this session)**; not run on a device | Before: no such fields, and no screen on web or Android could record a PRN dose at all (API only). Done: see §4. | Nursing and P&T decide whether the limits are mandatory. |
| A-1 | this session | The Android app could not record a PRN dose or set PRN limits | **COMPLETE (this session)**; not run on the emulator | Before: `git grep -i prn hospital-automate-mobile/lib` found only the scheduling preview flag | See §4, "A-1" |
| H-09, H-11, H-12, H-13, H-15 | Hazard register | Interaction list, second-nurse check, dose/route mismatch, held-dose reason, discharge checklist enforcement | BLOCKED (clinical decision) | Each needs a decision on what the rule is | Build once the rule is decided |
| H-16 | Hazard register | AI-scribe accuracy with real providers never measured | BLOCKED | Needs provider credentials and a study on consented recordings | — |
| H-17 to H-22 | Hazard register | Identity at the bedside, ER coverage (about half of 24 actions), break-glass rules, CNN not built, legacy MAR frequencies, salt-text substitution | BLOCKED (clinical) | — | — |

### 3.2 Billing integrity (P0/P1)

| ID | Source | Finding | Status | Evidence | Plan |
|---|---|---|---|---|---|
| B-1 | billing-pharmacy-lab report §10 | A hand-added consultation or lab line plus the automatic charge bills the same service twice | **COMPLETE for the web (this session)**; another client could still type its own free-text wording | Before: any price-list line could be added by hand, including the consultation, laboratory and bed categories that are charged automatically. The automatic charge is keyed, but hand lines have no key. | Done: those three categories are refused on hand-added lines (§4). Still open: a free-text line ("Consultation", typed price) can't be told apart from a miscellaneous charge. Remove free-text service lines when the price-list picker screen is built (B-4). |
| B-2 | same | Unpriced work is never back-filled once a price is added | **COMPLETE (API, this session)** | Before: audited as `billing.charge.unpriced` only | `GET /api/billing/price-list/unbilled/` and `POST …/charge-unbilled/` (§4). No screen yet (B-4). |
| B-3 | same | Lab and consultation charges on a cancelled bill are not re-captured | **COMPLETE (API, this session)** | A cancelled bill frees its charge keys, so the sweep finds the work again | Same sweep |
| B-4 | same / Android report §13 | No web or Android screen for the price list or bed management | **Web COMPLETE (this session)**; Android and bed management still API only | — | Android screens if the hospital wants them on phones |
| B-5 | Known limitations | Pharmacy refunds are not reflected in Billing; `laboratory_revenue` is null | PARTIAL | — | Now that lab tests are charged from the price list (BUG-07), report lab revenue from those invoice lines |

### 3.3 Laboratory (P1)

| ID | Source | Finding | Status | Plan |
|---|---|---|---|---|
| L-1 | billing-pharmacy-lab report §10 | No reject/correct step for a verifier; a wrong result is cancelled and re-ordered | **COMPLETE (2026-11-23)** | `POST /api/laboratory/{id}/reject_result/` {reason}. An entered or verified, unreleased result goes back to Processing; the values as entered are kept in `LabResultRejection`, and the step is audited `lab.result.rejected`. Web "Reject Result" and Android "Reject result" with a reason. A released result needs an amended report, which is not built. Tests: `laboratory/test_result_rejection.py` (6), Android `lab_screens_test.dart` (3), Playwright `laboratory.spec.js` (reject, re-enter, verify, release) |
| L-2 | this session | Structured result entry (per parameter) exists on the web only; the Android lab form still sends free text | PARTIAL | Android `_ResultForm`: one field per configured parameter |
| L-3 | this session | No screen to manage reference ranges (API only, Admin) | PARTIAL | Admin screen on the web |

### 3.4 Security and privacy

| ID | Source | Status | Note |
|---|---|---|---|
| S-L1 to S-L8, mobile FLAG_SECURE / R8 / backup | Readiness audit 2026-11-18 | COMPLETE (cited) | `SECURITY_HARDENING_2026-11-19.md` |
| Cross-hospital isolation | Defect register D-01/D-02/D-29, every-endpoint tenancy test | COMPLETE | `security_tests/test_tenant_isolation`: "LEAKS: none" in this session's run. The new `LabReferenceRange` model is routed and covered. |
| npm audit (picomatch via Vite, build-time only) | Readiness audit | PARTIAL (accepted Low) | The fix downgrades Vite, which breaks the build |
| L5: penetration test and DPDP assessment | Known limitations | BLOCKED | Commission both |

### 3.5 Integrations

| ID | Status | Note |
|---|---|---|
| Twilio Verify OTP, SMS, WhatsApp, voice, email, STT/LLM, Google sign-in (L2) | BLOCKED | The provider architecture, Celery retries and honest "skipped" logging exist (D-04, R-06). Never exercised with real credentials. |
| ABDM / FHIR / HL7 | BLOCKED (ABDM sandbox and certification); FHIR behind a flag; HL7 not mounted | — |

### 3.6 Infrastructure and release

| ID | Status | Note |
|---|---|---|
| L1: staging on a real host, domain and CA certificate | BLOCKED | The local production rehearsal passed (defect register 2026-10-26, 2026-11-03) |
| CI deploy steps | NOT IMPLEMENTED | Still `echo` until a staging target exists |
| M-1: mobile upload keystore | BLOCKED | The hospital creates its own key |
| iOS build | BLOCKED | The Xcode iOS platform component is not installed on this Mac |
| `dart format` CI gate | UNVERIFIED | The 2026-11-18 audit found 36 unformatted files; a later commit formatted the mobile code (`a0d93a3`). Not re-run in this session. |

### 3.7 The 11 Android E2E bugs (BUG-01 to BUG-11)

All COMPLETE, with live and regression evidence in `reports/android-live-e2e-final-2026-11-19.md` (at HEAD). The one gap was BUG-10's discharged-row label, which had unit tests only. A widget test was added in `cd6aef7`.

## 4. Work done in this session

### H-14: reference ranges, abnormal flags and critical values

**Backend:**
- `laboratory/models.py`:
  - New `LabReferenceRange` per hospital, with test name, parameter, unit, sex, low/high and critical low/high.
  - One active row per (hospital, test, parameter, sex), enforced by a database constraint that ignores case.
  - Rows are retired, never deleted.
  - `LabResult` gains `flag_details`, `has_critical` and critical-acknowledgement fields.
  - Migration `laboratory/0008` is additive only: new columns and one new table.
- `laboratory/flags.py` (new):
  - The server flags each numeric value as L, H, LL or HH.
  - A value that isn't a number is recorded as *not checked*, never as normal.
  - A sex-specific range takes precedence over "Any".
  - The client can no longer clear or rewrite a flag the server computed.
  - Ranges are copied onto the result, so a later change never alters an existing report.
- `laboratory/views.py`:
  - `enter_result` flags the values.
  - `verify_result` writes `lab.result.critical`.
  - New `GET /api/laboratory/critical-results/` (lab staff, doctors, nurses, read-only manager; `?mine=1`).
  - New `POST /api/laboratory/{id}/acknowledge_critical/` (doctor only, note required, once only, audited).
  - New `/api/laboratory/reference-ranges/`: clinical staff read, Admin writes, no DELETE.

**Web:**
- `src/components/laboratory/CriticalResults.jsx` (new): a panel on the Laboratory page listing unacknowledged critical values, with an Acknowledge button for doctors and admins.
- `src/pages/laboratory.jsx`: when the hospital has ranges for a test, result entry asks for each parameter's value.
- `src/services/api.js`: the three new endpoints.

**Mobile:**
- `record_models.dart` now reads the server's list of flagged names and the computed `flag_details`. Before, it expected a map, so flagged values were never marked as flagged on mobile.

**Tests:**

| Suite | Added | Result |
|---|---|---|
| Backend: `laboratory/test_reference_ranges.py` | 21 tests | Pass. With server flagging removed (mutation check), 4 of them fail. |
| Web: `src/__tests__/criticalResults.test.jsx` | 4 tests | Pass |
| Mobile: `patient_repository_test.dart` (H-14 group) | 2 tests | Pass |

**Full suites after the change:**

| Check | Result |
|---|---|
| Backend tests | 1,423 OK, 35 skipped (PostgreSQL-only) |
| `makemigrations --check` | "No changes detected" |
| Vitest | 36 files, 132 tests passed |
| ESLint | 0 errors; warnings unchanged from before the change |
| Web production build | OK |
| `flutter analyze` | No issues |
| `flutter test` | 498 passed |

**Not done for H-14:**
- No range values are shipped. They are the lab director's decision.
- There is no Admin screen for ranges yet (L-3).
- Android result entry is still free text (L-2).
- The critical list is a worklist on the Laboratory page. Nothing pages or texts the doctor, because SMS is blocked on credentials.
- Hindi text for the new labels isn't written yet; they show in English.
- Not run in a browser or on the emulator.

### H-10: PRN dose limits

**Backend:**
- `nurses/models.py`: `MAR.prn_min_interval_minutes` and `MAR.prn_max_doses_per_24h`, both optional. Migration `nurses/0014` adds two nullable columns and nothing else.
- `nurses/serializers.py`: limits are accepted only on an as-needed (PRN/SOS) order. The interval must be 15 to 10,080 minutes and the maximum 1 to 48 doses.
- `nurses/prn_limits.py` (new): refuses a dose inside the minimum interval or over the maximum in the last 24 hours. Only doses recorded as given count. The message gives the last dose's time and when the next one is allowed, in hospital time.
- `nurses/views.py`: the `prn` action locks the order row, checks the limits, and records the dose in the same transaction. A refusal returns 409 and is audited as `nurses.mar.prn_refused`.

**Web:**
- `src/components/ipd/MedicationOrders.jsx`: the doctor's order form shows "Minimum hours between doses" and "Most doses in 24 hours" when the frequency is as-needed. The orders table shows the limits. A nurse gets a **Give dose** button on active PRN orders, with an optional note; a refusal is shown as the server words it.
- Before this, nurses had no screen to record a PRN dose at all.
- Supporting changes: `src/utils/prnLimits.js` (new), `src/pages/IPD.jsx` (`canGive` for nurses), and `api.nurses.mar.givePrn`.

**Tests:**

| Suite | Added | Result |
|---|---|---|
| Backend: `security_tests/test_prn_limits.py` | 9 tests | Pass. With enforcement removed (mutation check), 2 of them fail. |
| Web: `src/__tests__/prnOrders.test.jsx` | 7 tests | Pass |

**Full suites after H-14 and H-10 together:**

| Check | Result |
|---|---|
| Backend tests | 1,432 OK, 35 skipped |
| `makemigrations --check` | "No changes detected" |
| Vitest | 37 files, 139 tests passed |
| ESLint | 0 errors, 11 warnings (unchanged) |
| Web production build | OK |
| Mobile | Unchanged by H-10; 498 passed after H-14 |

### A-1: PRN doses and limits on Android

**Server:**
- The 409 refusal now also carries boolean flags `prn_min_interval` / `prn_max_per_24h`, because the app words errors from flags and never shows server text raw.

**App:**
- `nursing_models.dart`:
  - The order reads `prn_min_interval_minutes` and `prn_max_doses_per_24h`.
  - New `isPrn`, using the same as-needed words as the server.
- `nursing_repository.dart`: new `givePrnDose`, which calls `POST nurses/mar/{id}/prn/`.
- `ward_medication_section.dart`:
  - A PRN order shows its limits and a **Give dose** button.
  - The confirmation shows the patient's name and UHID, medicine, dose and route, with an optional note.
  - A refusal is worded from the order's own limits ("one dose every 4 h", "at most 3 doses in 24 hours").
- `clinical_work_sections.dart` (doctor's ward order form):
  - "Minimum hours between doses" and "Most doses in 24 hours" appear for an as-needed frequency.
  - Hours are sent as minutes.
  - Impossible values are refused before anything is sent.
  - The orders list shows the limits.
- 12 new strings in English and Hindi. The Hindi was written by engineering and needs review.

**Tests:**
- 9 new tests (Android `nursing_screens_test.dart`, `clinical_work_test.dart`): giving a dose and cancelling it, the too-soon and daily-limit refusals, an order without limits, the helpers, limits sent in minutes, an impossible limit refused, and no limits on a scheduled order.
- With the refusal wording disabled (mutation check), the refusal test fails.
- `flutter analyze`: no issues. `flutter test`: 507 passed.
- Backend `security_tests.test_prn_limits`: 9 OK after the flag change.

**Not done for H-10:**
- Android was not run on the emulator.
- The row lock is checked with a mock on SQLite, not against a real PostgreSQL lock.
- Not run in a browser.

### B-1, B-2, B-3: double billing and unbilled work

**B-1 (`billing/price_list.py`):**
- A price-list line in the consultation, laboratory or bed category can no longer be added to a bill by hand. These services are charged automatically: at completion, at verification, and on the final bill.
- The refusal explains why and points to the sweep.
- `price_line` is the one path for line create, line edit and nested invoice creation, so all three are covered.
- Other categories (procedure, inpatient service, other) are unchanged.

**B-2 and B-3 (`billing/unbilled.py` new; `billing/views.py` price-list actions):**
- `GET unbilled/?since=` (billing roles) lists completed consultations and verified laboratory tests with no live charge, saying whether each has a price today.
- `POST charge-unbilled/` (Admin or Hospital Manager) charges the priced ones through the same capture functions, so each is charged once only. The sweep is audited as `billing.charge.unbilled_swept`.
- The look-back is 30 days by default and at most 90.
- Work left on a cancelled bill is found again, because cancelling frees its charge keys.
- Bed days are not swept, since the final bill charges them.
- Swept work is priced at today's price-list entry.

**Tests: `billing/test_unbilled.py`, 9 tests:**
- refused categories, with the other categories still allowed
- list then charge once, with a second sweep charging nothing
- unpriced work reported and not charged
- a lab test swept
- a cancelled bill re-billed
- roles
- look-back limits
- other hospitals' work never listed

With the guard removed (mutation check), the refusal checks fail.

**Results:**

| Check | Result |
|---|---|
| Backend tests | 1,441 OK, 35 skipped |
| `makemigrations --check` | "No changes detected" (no migration needed) |

**Not done:**
- No web or Android screen for the sweep or for picking price-list lines (B-4).
- Free-text service lines (B-1 residual).
- A swept consultation follows the normal capture rule: if the patient is now admitted, it goes on the stay's running bill.

### B-4: billing screens (web), and four existing Billing-page bugs

**New panels on the Billing page:**
- **Price list** (`src/components/billing/PriceList.jsx`):
  - Every role that can open Billing sees the prices in force.
  - An Admin or Hospital Manager adds a price (category, code, name, applies to, price, GST) or retires one, after a confirmation.
- **Unbilled work** (`UnbilledWork.jsx`):
  - Shown only when there's something to bill.
  - Lists the work, marking each item "Priced" or "Add a price first", with an optional start date.
  - An Admin or Hospital Manager bills the priced work after a confirmation.
- **Services from the price list** (`PricedServicePicker.jsx`, inside Create invoice):
  - Picks a procedure, inpatient or other service with a quantity.
  - The price and GST come from the list.
  - Consultations, lab tests and bed days are not offered.

**Invoice form (B-1):**
- The typed "Doctor Consultation" and "Laboratory Services" amounts are gone from new bills. A note says those services are billed automatically.
- They reappear only when editing an older bill that already has such lines, so nothing is lost.
- Server backstop: a new bill with a free-text line named exactly "Doctor Consultation" or "Laboratory Services" is refused (`billing/serializers.py`). Editing an older bill that has one still works.
- The browser test `e2e/opd-to-bill.spec.js` typed exactly that duplicate consultation charge. It now uses Other charges. It was not re-run here.

**Existing bugs found while checking it in a browser, now fixed:**
1. **Save Changes on a bill always failed** (400, "patient: This field is required."). The web client sent `PUT` with only the discount and lines. It now sends `PATCH`.
2. **Editing a bill right after creating or editing one failed** ("Cannot update: missing server record ID"). Three copies of the bill-list reload left out the server record. They now use the page's one loader.
3. **Editing a bill deleted every line except the four typed amounts** (priced lines, other hand-typed lines). Those lines are now carried through unchanged (`utils/billingLines.js` `otherLinesOf`).
4. **The bill list ignored GST:** Total, Due and Outstanding were the line sum minus the discount. They now show the server's total. In the run, a bill with ₹27 of GST showed ₹210 before and ₹237 after.

**Checked in a browser** (throwaway e2e server on `seed_demo` data, signed in as the demo hospital manager):
- Added a consultation price (₹500) and a Dressing procedure (₹150, 18% GST).
- The picker offered only Dressing.
- Created a bill with Dressing and ₹50 of other charges. On the server, the Dressing line is linked to its price with ₹27 GST, total ₹227.
- Edited it to ₹60 of other charges. The Dressing line was kept and the total became ₹237.
- An uncharged completed visit showed under Unbilled work as "Priced". Billing it created a ₹500 bill, and the panel cleared.
- A fresh page load had no console errors.

**Tests:**

| Suite | Result |
|---|---|
| `src/__tests__/billingScreens.test.jsx` (new) | 9 tests |
| `billing/test_unbilled.py` | +2 tests: free-text refusal, and editing an older bill |
| Vitest | 38 files, 148 passed |
| ESLint | 0 errors, 11 warnings (unchanged) |
| Web production build | OK |
| Backend | 1,443 OK, 35 skipped |

### Code review of this session's work (2026-11-23) and its fixes

A high-effort review of commit `3632693` found 8 issues. All 8 are fixed in the commit that follows it.

| # | Severity | Issue | Fix | Evidence |
|---|---|---|---|---|
| 1 | Important | The Billing **Payment** button reused the edit form without resetting the price-list lines, so paying bill B could replace its lines with those of a bill edited earlier. The Payment form also could never submit (pre-existing). | Payment-only mode: records the payment against the server's total and sends no bill lines. Every way of opening or closing the form clears the extra lines. An edit of a bill holding automatic charges sends only the discount. | Checked in a browser: edit A, close, pay B. Only `POST /payments/` was sent, B stayed "Other Services ₹100" and Paid, A was unchanged. |
| 2 | Important | The sweep listed every uncharged completed visit and verified test, including ones billed by hand before automatic charging, so it would bill them twice. | Lists only work audited as `billing.charge.unpriced`, plus charges from cancelled bills. | `test_work_billed_before_automatic_charging_is_never_listed` |
| 3 | Important | The bulk sweep re-billed charges an Admin had cancelled on purpose. | Those rows show the bill and cancel reason and are billed only when picked (`items: [{kind, id}]`). | `test_a_charge_on_a_cancelled_bill_is_billed_again`, `test_a_bad_pick_list_is_refused`, Vitest "bills a charge from a cancelled bill only when picked" |
| 4 | Important | The unbilled list made a few queries per visit on every Billing page load, and could rewrite charge keys while listing. | Candidates come from audit rows and voided keys; live charges are found in one query; prices are cached per service; listing never writes. | `test_listing_is_read_only_and_does_not_grow_with_the_work`: the same query count for 1 and 5 rows, and no billing UPDATE or DELETE |
| 5 | Important | A lab value whose parameter had limits, but none for the patient's sex, was silently unflagged. | Recorded as not checked, with the reason. | `test_a_patient_with_no_matching_sex_range_is_marked_not_checked` |
| 6 | Nit | Critical results showed only on the Laboratory page. | Also shown on the Consultation page, where doctors work. | Vitest suite; component tests unchanged |
| 7 | Nit | The free-text consultation block didn't cover `POST /invoice-items/`. | Checked on standalone line creation too; editing an older bill still works. | `test_the_old_lines_cannot_be_added_to_an_existing_bill_either` |
| 8 | Nit | Changing a limited PRN order to a scheduled frequency gave a confusing 400. | The limits are cleared automatically unless sent in the same request. | `test_changing_a_limited_order_to_a_schedule_clears_its_limits` |

**Suites after the fixes:**

| Check | Result |
|---|---|
| Backend tests | 1,449 OK, 35 skipped |
| `makemigrations --check` | "No changes detected" |
| Vitest | 38 files, 149 passed |
| ESLint | 0 errors, 11 warnings |
| Web production build | OK |

Mobile was not changed in this round.

## 5. Next phases, in order

1. **L-3** reference-range admin screen, then **L-2** Android structured entry. L-1 is done (2026-11-23).
3. Re-run Playwright E2E and the PostgreSQL row-lock suite (`REQUIRE_ROW_LOCK_TESTS=1`) on the combined changes. Add a real two-connection PRN lock test there.
4. Documentation set listed in the brief. These already exist: `README.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, `docs/API_DOCUMENTATION.md`, `docs/DEPLOYMENT.md`. Still to do: `docs/SECURITY.md` and `docs/BACKUP_AND_RESTORE.md` (fold in `SECURITY_AUDIT.md` and `DISASTER_RECOVERY.md`), then the final report.

## 6. Current decision

**NOT PRODUCTION READY** for real patients. These remain open:
- L1 staging on a real host
- L2 real provider credentials
- L4 clinical safety sign-off, including H-08, which is still rated Unacceptable
- L5 penetration test and DPDP assessment
- M-1 mobile keystore

None of these can be closed by engineering alone. H-14's engineering control is now in place, but it protects patients only once each hospital has loaded and approved its ranges.
