# Prompt 4: Appointment scheduling, nursing vitals, temperature units, pharmacy

**Date:** 2026-11-24 · **Branch:** `ui/redesign-2026-10-25` · **Nothing committed or pushed.**

All testing used isolated environments:

- the Django test database (SQLite);
- a throwaway PostgreSQL 17 cluster on 127.0.0.1:55433, stopped afterwards;
- the Playwright e2e backend (`config.settings.e2e`, seeded synthetic "Demo City Hospital").

Twilio variables were blanked for test runs. No real SMS, email, OTP or payment was sent, and the development database was not touched. Authentication, RBAC, hospital isolation and audit logging were left as they were.

## Verdicts

| Finding | Verdict |
|---|---|
| BUG-003: bookings allowed on a doctor's day off | **FIXED AND VERIFIED** |
| BUG-008: duplicate daily bookings | **NOT CHANGED: business rule ambiguous.** Existing protections verified |
| BUG-005 / INT-001: nurse vitals not visible to doctors | **FIXED AND VERIFIED** |
| Temperature unit safety | **FIXED AND VERIFIED** (new readings); historical readings labelled, not converted |
| BUG-006: pharmacy returns search crash | **FIXED AND VERIFIED** |
| BUG-007: raw Python error shown in pharmacy | **FIXED AND VERIFIED** |

---

## 1. BUG-003: working days (FIXED AND VERIFIED)

**Root cause.** The free-text `Doctor.availability` field (for example "Mon-Sat 09:00-17:00") was shown to patients but never enforced. A Sunday got slots and could be booked.

**Fix.** The rule is enforced in one place on the server and is advisory in the UI.

- `backend/appointments/availability.py` (new): `parse_working_days()` reads the days out of the existing availability text. It understands:
  - ranges: "Mon-Sat", "Mon to Fri";
  - wrap-around ranges: "Fri-Mon";
  - lists;
  - "Weekdays", "Weekends", "Daily".

  Blank text, or text with no day in it, means **no restriction**, so existing doctors keep their current behaviour. Times are not parsed: that is outside this scope.
- `backend/appointments/views.py`: the day-off check is applied to:
  - the patient `book` action;
  - the staff create and update paths (via `_claim_place`);
  - `reschedule`.

  `booking-options` returns each doctor's `working_days`. On a day off it returns no slots, plus an `unavailable_reason`.
- `src/pages/patient/BookAppointmentModal.jsx`:
  - choosing a doctor moves the date to their next working day (`nextWorkingDate` in `src/utils/hospitalDate.js`);
  - a day off shows the server's reason and offers no times.

**Evidence.**

- `backend/appointments/test_working_days.py`. Covers the parser cases, plus:
  - Sunday is refused with 400 and Monday gives 201;
  - blank availability allows Sunday;
  - booking-options returns an empty slot list with a reason on a day off;
  - staff create on a Sunday gives 400;
  - reschedule to a Sunday gives 400.
- Vitest `nextWorkingDate` (in `src/__tests__/patientEnrollment.test.jsx`).
- Playwright `e2e/appointments-nursing-pharmacy.spec.js` test 1:
  - the UI shows the reason and no slots;
  - a direct `POST /api/appointments/book/` on a Sunday is refused with 400;
  - a Wednesday booking succeeds.
- Screenshot: `reports/e2e-evidence/prompt-4/1-sunday-no-slots.png`.

## 2. BUG-008: duplicate daily bookings (NOT CHANGED: ambiguous rule)

**What the system already enforces** (from the code, tests and seed data):

- **The same patient cannot hold two active bookings with the same doctor at the same date and time** (`appointments.models.clashing_booking`).
- **A slot never exceeds its capacity.** The doctor row is locked while a place is claimed.
- **Idempotency keys stop a retried request from booking twice.**

**What is not established anywhere:** a rule limiting a patient to one booking per doctor (or per hospital) **per day**. I searched the code, docs, tests and the mobile app and found no such rule. A morning consultation plus an afternoon review with the same doctor can be clinically legitimate. Per your instruction ("Do not invent a new scheduling policy"), **no per-day restriction was added.**

**Verification of the existing rules under concurrency.** I ran them on PostgreSQL 17 (`security_tests.test_concurrency` plus `appointments`): **70 tests OK, none skipped**. These include:

- `test_parallel_reception_bookings_put_one_patient_in_a_slot`
- `test_one_slot_on_an_empty_day_goes_to_one_patient`
- `test_parallel_bookings_never_exceed_a_slots_capacity`
- `test_parallel_booking_retries_with_one_idempotency_key_book_once`

**Decision needed from you:** should a patient be limited to one active booking per doctor per day, or per hospital per day? Either is a small change to `clashing_booking` once the policy is decided.

## 3. BUG-005 / INT-001: nurse vitals reach the doctor (FIXED AND VERIFIED)

**Root cause.** Ward vitals are stored as `NursingAssessment.vitals`, but the doctor's Vitals tab only read visit `VitalSign` rows. So the nurse's readings never appeared, although the API already allowed doctors of the same hospital to read them.

**Fix (read-through, no copying, no migration).**

- `src/components/clinical/NursingObservations.jsx` (new) is shown in Consultation, Vitals tab, under "Vital history". It lists the patient's nursing assessments with vitals: time, the nurse who recorded them, and the temperature with its unit, BP, pulse, SpO₂ and respiratory rate. It has loading, empty and error states.
- Access is unchanged and enforced by the server. Only doctors and nurses of the same hospital may read, and only for patients in their care (the existing care rule). Other roles and other hospitals are refused.

**Evidence.**

- `backend/nurses/test_ward_temperature.py`:
  - a doctor sees the reading with `nurse_name` and `assessed_at` only once the patient is in their care;
  - pharmacist, lab and billing roles get 403;
  - a doctor at another hospital gets an empty list for their own hospital, and 403 for this one.
- Vitest `src/__tests__/temperatureUnits.test.jsx`.
- Playwright test 2: the nurse records 99.1 °F and pulse 88 in the UI. Doctor demo.doctor1 then sees "99.1 °F", "88" and the nurse's name in Consultation.
- Screenshots: `2-nurse-saved-with-unit.png`, `3-doctor-sees-nurse-vitals.png`.

## 4. Temperature unit safety (FIXED AND VERIFIED for new data)

**Root cause.** Ward temperatures were stored as bare numbers.

- The web nurse form said °F.
- The mobile nursing app gives no unit.
- Clinical `VitalSign.temperature` is °C.

So the same number could mean either unit.

**Fix.**

- **Backend** (`nurses/serializers.py`): a reading may carry `temperature_unit` "C" or "F". With a unit, the value must be a possible body temperature in that unit: C 10–46, F 50–115. "98.6 °C" and "37.0 °F" are refused with a clear message, and any other unit is refused. Extremes such as 32.5 °C, 42.1 °C and 95.0 °F are accepted.
- **Readings without a unit are still accepted and stored exactly as sent.** This keeps the mobile app and older clients working. Nothing is guessed or converted.
- **Web nurse form** (`src/pages/Nurses.jsx`): it sends `temperature_unit: "F"` (the unit the form asks for) and displays the stored unit.
- **Display** (`src/utils/temperature.js` `formatTemperature`): always "98.6 °F" or "37.2 °C". A legacy reading without a unit shows "98.6 (unit not recorded)". **A temperature is never shown without its unit, and historical values are never converted.**
- **No database migration:** historical rows are unchanged.

**Evidence.** `nurses.test_ward_temperature` covers:

- the unit is stored;
- impossible readings are refused, with nothing saved;
- extremes are accepted;
- a unit-less reading is kept byte-for-byte.

Vitest covers `formatTemperature` and the legacy label.

**Remaining gaps (outside Prompt 4, not changed):**

- the mobile nursing app still sends no unit, so its new readings show "unit not recorded" until it sends one;
- `src/pages/Compounter.jsx` keeps its vitals in local state only, with a °F label.

## 5. BUG-006: pharmacy returns search crash (FIXED AND VERIFIED)

**Root cause.** `SaleReturns.jsx` passed `(e) => setQuery(e.target.value)` to `SearchInput`, but `SearchInput` calls `onChange` with the text itself. So `e.target` was undefined, and the first keystroke threw "Cannot read properties of undefined (reading 'value')".

**Fix.** `onChange={setQuery}`. The filter also tolerates rows with a missing patient or medicine name.

**Evidence.**

- Vitest: typing fast, changing, clearing, no matches, and rows with null names, all without throwing.
- Playwright test 3: typing "D", "Do", "Dolo", "", "zzzz", "SALE-" produced no page errors.
- Screenshot: `4-pharmacy-search.png`.

## 6. BUG-007: raw Python error in pharmacy (FIXED AND VERIFIED)

**Root cause.** Two problems combined:

- the API exception handler built `message` with `str()` of nested error dicts, which printed `lines: {0: {'quantity': [ErrorDetail(string='…', code='min_value')]}}`;
- the dispense panel let a negative quantity be sent.

**Fix.**

- `backend/config/exceptions/__init__.py`: nested errors are flattened into sentences, for example "Line 1, quantity: Ensure this value is greater than or equal to 1." The status code and the structured `details` are unchanged, so existing clients keep working.
- `src/utils/dispenseBatches.js`: a negative, fractional or non-numeric quantity is refused before any request ("enter a whole number of units").

**Evidence.**

- `backend/config/test_exception_messages.py` checks that no `ErrorDetail`, `{`, `[` or `code=` reaches the message, and that simple messages are unchanged.
- Vitest: -1, "-1", 1.5, "2.5" and "abc" are all refused.
- Playwright test 3: the real `POST /api/pharmacy-sales/dispense-prescription/` with quantity -1 returns 400 with "Line 1, quantity: …".

---

## Regression results

| Suite | Result |
|---|---|
| Backend (Django, full, Twilio blanked) | 1489 tests: 1450 pass, 37 skipped, **2 fail**. Both failures are the known `.env`-caused ones, seen before Prompt 4: `ai_scribe…test_capabilities_report_providers_without_keys_and_block_cnn` and `security_tests…test_production_boots_without_twilio_when_sms_otp_is_off` |
| Backend on PostgreSQL 17 (appointments + concurrency) | 70 OK, none skipped |
| Vitest | 43 files, 235 tests pass |
| ESLint (`src/`, `e2e/`) | 0 errors. Two errors and one unsafe optional chain in my own Prompt 3 spec were fixed. The one remaining repo-wide error is in an untracked mobile build artifact (`hospital-automate-mobile/build/…/record.worklet.js`) |
| Vite build | OK |
| Playwright, Prompt 4 spec | 3 / 3 pass |
| Playwright, full suite | 47 specs: **46 passed, 1 failed** (9.4 min). The failure was `nurse-mar.spec.js` "ward nurse gives a due dose from the MAR" (30 s timeout), already known as flaky in the E2E audit (P5-08). Re-run alone twice after the full run, it **passed both times** (11.6 s, 11.7 s). The full run re-captured the committed Prompt 1 `allergy-*.png` and Prompt 3 `prompt-3/*.png` screenshots; those were restored with `git restore` and are unchanged |

## Files changed in Prompt 4

**Backend:**

- `appointments/availability.py` (new)
- `appointments/views.py`
- `appointments/test_working_days.py` (new)
- `nurses/serializers.py`
- `nurses/test_ward_temperature.py` (new)
- `config/exceptions/__init__.py`
- `config/test_exception_messages.py` (new)

**Frontend:**

- `src/pages/patient/BookAppointmentModal.jsx`
- `src/utils/hospitalDate.js`
- `src/utils/temperature.js` (new)
- `src/components/clinical/NursingObservations.jsx` (new)
- `src/pages/Consultation.jsx`
- `src/pages/Nurses.jsx`
- `src/components/pharmacy/SaleReturns.jsx`
- `src/utils/dispenseBatches.js`

**Tests:**

- `src/__tests__/temperatureUnits.test.jsx` (new)
- `src/__tests__/saleReturns.test.jsx`
- `src/__tests__/dispenseBatches.test.js`
- `src/__tests__/patientEnrollment.test.jsx`
- `e2e/appointments-nursing-pharmacy.spec.js` (new)
- `e2e/patient-registration.spec.js` (lint fixes only)

**Evidence:** `reports/e2e-evidence/prompt-4/` (4 screenshots, new). Earlier reports were not modified.
