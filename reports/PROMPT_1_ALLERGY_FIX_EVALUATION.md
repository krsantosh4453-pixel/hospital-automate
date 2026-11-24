# Prompt 1 — BUG-001 Allergy Safety Fix: Evaluation

- **Date:** 2026-11-24 · **Branch:** `ui/redesign-2026-10-25` (uncommitted working tree on top of `e71bb63`)
- **Source finding:** [`E2E_WEB_APPLICATION_AUDIT.md`](E2E_WEB_APPLICATION_AUDIT.md) → BUG-001 (unchanged by this work)
- **Evidence:** [`e2e-evidence/allergy-*`](e2e-evidence/)
- **Test data:** synthetic only (`seed_demo` "Demo …" patients, "Synthetic …" allergens), in throwaway databases. The development database was not touched.

## Final verdict: **FIXED AND VERIFIED**

Every required check passed for the changed behaviour, in unit, API, backend and real-browser tests, with an independent QA reproduction. The only non-passing items found during regression are pre-existing and unrelated (see §12), and each was proven unrelated with evidence.

---

## 1. Original bug

The doctor's Consultation screen (patient summary strip) showed **"No known allergies"** for a patient whose allergies had never been asked or recorded (`allergy_status: "Unknown"`). A prescriber could read "never asked" as "asked: none".

## 2. Root cause

`src/components/clinical/PatientContextStrip.jsx` decided allergy status **only from the allergy list** (`GET /api/clinical/allergies/?patient=`). An empty list rendered "No known allergies". It never read the patient's `allergy_status`, and a failed patient fetch was silently ignored.

Investigation found a second, more serious path. The allergy list is **scoped to the selected hospital**, while `allergy_status` ("Has allergies") counts allergies at **every** hospital. A patient with an allergy recorded at another hospital therefore had an empty list here and was shown **"No known allergies" despite having a recorded allergy**.

The backend data model was already correct. `Patient.allergy_status` defaults to "Unknown" (`db_default`); "No known allergies" is only set explicitly by doctors or nurses through an audited endpoint and is refused (409) while an allergy is on record; adding an allergy resets the stored value to "Unknown", so removing it later never silently becomes "none". The defect was in the frontend presentation, and there was no UI for doctors to record NKA.

## 3. Files modified

| File | Change |
|---|---|
| `src/components/clinical/allergyStatus.js` (new) | Pure function `allergySummary()` deciding what may be shown |
| `src/components/clinical/PatientContextStrip.jsx` | Uses the summary; tracks the patient-record load state; clears previous patient's facts; doctor/nurse actions to record NKA or add an allergy |
| `src/services/api.js` | `api.patients.setAllergyStatus(id, status)` for the existing endpoint |
| `src/assets/i18n/hiPages.js` | Hindi text for the new labels (untranslated text falls back to English) |
| `src/__tests__/allergyStatus.test.jsx` (new) | 17 unit/component tests |
| `backend/ipd/test_clinical_workflows.py` | 4 tests added to `AllergyStatusTests` |
| `e2e/allergy-status.spec.js` (new) | 3 Playwright tests against the real e2e backend |

No backend application code, no migration, no settings and no Git history were changed.

## 4. Backend changes

None to application code; the existing behaviour was verified and pinned with tests (§7). Endpoints used:
- `GET /api/patients/{id}/` → `allergy_status` ∈ {"Unknown", "No known allergies", "Has allergies"}
- `POST /api/patients/{id}/allergy-status/` (Doctor | Nurse; audited `patients.allergy_status.set`; 409 while an allergy is on record; 400 for any other value)
- `POST /api/clinical/allergies/` (Doctor | Nurse only)

## 5. Frontend changes

`allergySummary()` maps the two API answers to one of six displays:

| Condition | Shown |
|---|---|
| Allergy list has rows (even if the patient record failed) | **Allergies:** chips with name (severity), red |
| Either request still loading | "Checking allergies…" |
| Either request failed | ⚠ "Allergies could not be checked — confirm with the patient" |
| Status "No known allergies" and list empty | "No known allergies" |
| Status "Has allergies" but list empty (recorded at another hospital) | ⚠ **"Allergies are on record elsewhere — review with the patient"** |
| Status "Unknown", null, missing, unexpected, or no record | ⚠ **"Allergy status unknown — ask the patient"** |

- The previous patient's facts are cleared on every patient change, and late responses for an old patient are discarded (`cancelled` flag).
- Doctors and nurses (`activeRoleName`) see **"Record no known allergies"** (unknown state only, behind a confirmation that it was asked and is saved in their name) and **"Add allergy"** (allergen, reaction, severity, type). After saving, the strip **re-reads from the server** rather than trusting what it sent. Other roles see no actions; the backend refuses them regardless.
- Existing design tokens and shared `Button`, `ConfirmDialog`, `Modal` and `Field` components are reused; no layout redesign.

## 6. Database changes and migrations

**None.** The existing `allergy_status` field (migration `patients.0016`, `db_default="Unknown"`) already separates unknown from explicit NKA. Existing allergy rows and statuses are untouched. The test for existing allergies surviving an NKA attempt confirms this.

## 7. Tests added or modified

**Frontend: `src/__tests__/allergyStatus.test.jsx` (17)**
- TEST 1: empty list + Unknown → unknown (function and rendered strip, the original BUG-001 render)
- TEST 2: explicit NKA → "No known allergies"
- TEST 3: recorded allergy → "Penicillin (Severe)"
- TEST 4: "Has allergies" with empty list → review
- TEST 5: switching patient 1 → 2 with a delayed response: patient 1's allergy is never shown for patient 2
- TEST 6: null, missing, unexpected status and null record → unknown; failed or loading → never NKA; patient-fetch failure renders "could not be checked"
- Recording NKA requires confirmation, calls the audited endpoint, and shows the value read back

**Backend: `ipd.test_clinical_workflows.AllergyStatusTests` (+4; 10 total)**
- TEST 7: Pharmacist, Lab Staff and Receptionist get 403 for both the status endpoint and allergy creation; nothing changes in the DB
- TEST 7: the patient cannot change their own allergy facts (403)
- TEST 4/8: an allergy at another hospital → status "Has allergies", this hospital's list empty, NKA refused (409)
- TEST 8: a recorded allergy survives an NKA attempt (409), and the row is unchanged

These backend tests pin behaviour that already existed, so they passed when first run (no backend code changed). The frontend tests were written first and failed (module missing) before the implementation.

**Browser: `e2e/allergy-status.spec.js` (3, real backend)**
1. Demo Ravi (never asked): API `Unknown` → strip "Allergy status unknown", no "No known allergies" → doctor records NKA (confirmed) → API "No known allergies" → doctor adds "Synthetic penicillin" (Severe) → API "Has allergies" → still shown after reload.
2. Second visit (Demo Kiran): switching Ravi → Kiran shows "unknown" and never Ravi's penicillin; back to Ravi shows it.
3. Pharmacist session: status endpoint and allergy creation → 403.

## 8. Test execution results

| Suite | Result |
|---|---|
| New frontend tests | 17/17 pass |
| Full frontend suite (Vitest) | **40 files, 184/184 pass** |
| ESLint (changed files) | clean |
| Production build (`vite build`) | passes (17 min: iCloud file reads in this folder, not the code) |
| Backend `AllergyStatusTests` | 10/10 pass |
| Full backend suite | 1,459 tests: 2 failures, both caused by the developer's `.env` (see §12); in a clean copy without `.env` both pass (12/12 with the allergy class) |
| New Playwright spec | 3/3 pass |
| Full Playwright suite (final run, no other load) | **34/35 pass**; the one failure is the pre-existing flaky `nurse-mar` spec (passes 2/2 alone) |

## 9. Eight-step evaluation

| Step | Result | Notes |
|---|---|---|
| 1 Code review | PASS | No defaulting to NKA anywhere; one decision function, no duplicated logic; no unrelated changes; failed save keeps the entered allergy; lint clean |
| 2 Database | PASS | No schema change needed; default "Unknown"; null and missing handled in the UI; existing rows preserved |
| 3 API | PASS | Status values and transitions, 400/403/409 verified by backend tests and the browser spec |
| 4 Backend tests | PASS | 10/10 allergy tests; full-suite failures proven `.env`-related |
| 5 Frontend tests | PASS | 184/184 |
| 6 Real browser E2E | PASS | Unknown → NKA → known → persistence; switching; RBAC (screenshots 1–4) |
| 7 Regression | PASS (with pre-existing exceptions) | Consultation, prescribing safety, labs, pharmacy, OPD-to-bill, IPD, login all pass |
| 8 Independent verification | PASS | Separate fresh database; allergy put on record at a second hospital for Demo Sunil; as his doctor, real browser: API `Has allergies`, 0 rows listed here, strip **"Allergies are on record elsewhere — review with the patient"** (old code: "No known allergies"); no NKA button offered (`allergy-5-review-other-hospital.png`). The original "never asked" scenario is covered by Playwright test 1 (`allergy-1-unknown.png`). |

## 10. Browser evidence

| File | Shows |
|---|---|
| `e2e-evidence/allergy-1-unknown.png` | Never-asked patient: "Allergy status unknown — ask the patient" |
| `e2e-evidence/allergy-2-nka.png` | After the doctor records it: "No known allergies" |
| `e2e-evidence/allergy-3-known.png` | Recorded allergy chip after reload |
| `e2e-evidence/allergy-4-switched.png` | Switched to another patient: unknown, no carry-over |
| `e2e-evidence/allergy-5-review-other-hospital.png` | Allergy recorded at another hospital: review warning |
| `e2e-evidence/allergy-playwright-suite.txt` | Final full Playwright run, per test |

## 11. API verification

| Call | Expected | Observed |
|---|---|---|
| `GET /api/patients/{ravi}/` before any action | `Unknown` | `Unknown` |
| `POST …/allergy-status/` "No known allergies" (doctor) | 200, then GET → NKA | NKA |
| `POST /api/clinical/allergies/` (doctor) | 201, then GET → "Has allergies" | "Has allergies" |
| Same writes as pharmacist / lab / receptionist / patient | 403, DB unchanged | 403, unchanged |
| NKA while an allergy is on record (incl. other hospital) | 409 | 409 |
| Status "Has allergies" sent to the endpoint | 400 | 400 |

## 12. Regression results and unrelated findings

- **Backend (environment):** `ai_scribe…test_capabilities_report_providers_without_keys_and_block_cnn` (expects model `gpt-4o-mini`, gets `gpt-4`) and `security_tests…test_production_boots_without_twilio_when_sms_otp_is_off` fail only because the project `.env` (`AI_SCRIBE_MODEL`, `DJANGO_ENV`) is loaded by the test settings. A clean `git archive` copy without `.env` passes both. Not related to this fix.
- **Playwright (flaky):** `nurse-mar.spec.js` failed in the audit baseline before this change and again in one full run (different step); passes 2/2 alone; the MAR pages do not use the changed component.
- **Playwright (load):** in one run made while another server and browser were active, three specs timed out (`clinical-assist` D2, `emergency`, `hospital-services` theatre). Rerun together with the allergy spec on the same shared database: 9/9 pass; the final full run passed them too.

## 13. Remaining limitations (documented, not fixed: out of scope)

1. **Prescribing does not warn on unknown allergy status.** `backend/clinical/medication_safety.py` checks recorded allergies only; a prescription for a never-asked patient raises no allergy prompt. Recommended as a follow-up.
2. **No per-allergy verification workflow.** There is no "unconfirmed / verified" field on `Allergy`; the "review" state here covers the one real case the data supports (recorded at another hospital, not visible at this one). A clinician-verification workflow would need a schema change and was not invented.
3. The allergy list for the selected hospital cannot show allergies recorded elsewhere; the strip now says so, but the details are not listed.
4. The ER allergy panel (`ErActions.jsx`) lists allergies but shows nothing for none or unknown; it does not claim NKA, so it was left unchanged.

## 14. Final verdict

**FIXED AND VERIFIED.** An undocumented allergy status can no longer be displayed as "No known allergies": the only path to that text is an explicit, audited NKA record read back from the server. Verified by unit, backend, API and real-browser tests and an independent reproduction on fresh data. No backend, schema or RBAC weakening; existing records unchanged. Nothing was committed or pushed.
