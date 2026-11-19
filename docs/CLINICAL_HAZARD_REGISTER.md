# Clinical Hazard Register

Version 1, 2026-11-19, branch `ui/redesign-2026-10-25`. Prepared by engineering from the code and its tests.

**Status: DRAFT FOR CLINICAL REVIEW.** The severity, likelihood and risk ratings below are engineering's proposals. They are not a clinical safety approval. A qualified clinical safety officer must review, re-rate and accept each hazard. Their sign-off goes in `CLINICAL_SAFETY_REVIEW_PACK.md`.

Related: `CLINICAL_WORKFLOW_VALIDATION_2026-11-19.md` (test report and evidence), `CLINICAL_SAFETY_REVIEW_PACK.md` (rules as implemented, questions and sign-off), `KNOWN_LIMITATIONS.md`.

## Risk matrix

The matrix follows the common clinical-risk-management style (as in DCB0129 / ISO 14971). The hospital may replace it with its own.

**Severity**

| Level | Meaning |
|---|---|
| 5 Catastrophic | Death, or permanent harm to one or more patients |
| 4 Major | Severe injury, or harm needing major intervention |
| 3 Considerable | Harm needing extra treatment or a longer stay |
| 2 Significant | Minor injury, or a delay in care |
| 1 Minor | Inconvenience; no harm |

**Likelihood:** 5 Very high · 4 High · 3 Medium · 2 Low · 1 Very low.

**Risk = severity × likelihood**

| Score | Rating | Meaning |
|---|---|---|
| 15–25 | Unacceptable | Must be fixed before patient use |
| 8–12 | Undesirable | Needs a recorded clinical decision and controls |
| 4–6 | Tolerable | Monitor |
| 1–3 | Acceptable | |

How to read a row: "Initial" is the risk before the engineering control, "Residual" the risk after it. A control marked **(clinical)** depends on a procedure or decision that only the hospital can make.

## A. Hazards found and fixed in this review (2026-11-19)

Each fix has a regression test in `backend/security_tests/test_clinical_safety_2026_11_19.py`. Each test failed before the fix and passes after it; the evidence is in the validation report, section 4.

| ID | Workflow | Hazard and cause | Possible harm | Initial S×L | Engineering control (done) | Residual S×L | Open for clinician |
|---|---|---|---|---|---|---|---|
| H-01 | MAR scheduling | The dose scheduler matched substrings and treated any frequency it did not know as **once daily**:<ul><li>`BD`, `TDS`, `QDS` and the `1-0-1` pattern (the prescription screen's own example), which the IPD order form copies into the MAR, all became once daily.</li><li>`WEEKLY` became daily: a weekly methotrexate order produced 15 daily doses in the test.</li><li>`EOD` matched "OD" and became daily.</li><li>`STAT` was repeated daily for 7 days.</li><li>`SOS` (as needed) got fixed doses.</li><li>`Q0H` looped forever.</li></ul> | Under-dosing (antibiotics given once instead of 2–3 times a day). Fatal over-dosing (daily methotrexate). Repeated STAT doses. | 5×4 = **20 Unacceptable** | New `nurses/frequency.py` reads only a fixed vocabulary and **refuses everything else**. Supported:<ul><li>OD/BD/TDS/QDS/HS</li><li>BID/TID/QID</li><li>Q*n*H and "every *n* hours" (1–168)</li><li>the `1-0-1` pattern</li><li>EOD, WEEKLY</li><li>STAT/ONCE (exactly one dose, never re-added)</li><li>PRN/SOS (never scheduled)</li></ul>The doctor's order form refuses an unknown frequency when it is saved. Scheduling refuses older rows with one, and refuses stopped orders. | 5×1 = **5 Tolerable** | Approve the vocabulary. The `1-0-1` pattern is scheduled at equal intervals (e.g. 12-hourly), not at fixed clock times (morning/afternoon/night): is that acceptable? |
| H-02 | MAR recording | A nurse could record a dose scheduled days ahead as **given now**, or as **missed** before it was due. | The same dose given again at its real time (double dose); a false "missed" record. | 4×3 = **12 Undesirable** | A dose can be recorded as given only from 60 minutes before its scheduled time (`MAR_EARLY_ADMINISTRATION_MINUTES`, default 60). It cannot be marked missed before it is due. | 4×1 = **4 Tolerable** | Confirm the 60-minute window, or set the hospital's policy value. |
| H-03 | Prescription edit / MAR | Saving a changed prescription deletes and re-creates its medicine lines. The MAR order was linked with cascade delete, so **the medication order and every dose recorded under it were permanently erased**. The test confirmed 0 orders and 0 doses left after one edit. | Loss of the legal administration record, and no trace of doses already given, so a dose could be repeated. | 5×3 = **15 Unacceptable** | A prescription that has MAR orders can no longer be edited: the doctor stops the orders and writes a new prescription. The MAR's links to the prescription are now `PROTECT` (migration `nurses/0010`), so no other path can cascade-delete them. | 5×1 = **5 Tolerable** | None. |
| H-04 | Paper prescription (pharmacy) | After a second pharmacist verified a transcribed paper prescription, any pharmacist could still change its medicines. It **stayed "Confirmed"** and could be dispensed with no second check. | Wrong medicine or dose dispensed from a transcription error. | 4×3 = **12 Undesirable** | Changing the medicines of a paper prescription sends it back to "Pending Verification". The editor is recorded as the transcriber, so someone else must verify it. | 4×1 = **4 Tolerable** | None. |
| H-05 | Prescribing (allergy check) | An allergy recorded by **brand name** (e.g. "Augmentin") was never matched, so prescribing amoxicillin passed without an alert. An allergy the checker could not read passed **silently**, which looked the same as a clean check. | Anaphylaxis or other allergic harm. | 5×3 = **15 Unacceptable** | Allergy names are also looked up in the hospital's medicine catalogue (brand → salts). An allergy that cannot be matched to any medicine now shows an info alert: "could not be matched … not checked. Check it yourself." | 5×2 = **10 Undesirable** | The residual is still high because spelling variants (e.g. "amoxycillin") and brands missing from the catalogue are not matched. A licensed drug database is needed (H-08). Should an allergy to one penicillin cover the whole class? |
| H-06 | AI scribe consent | `upload_audio` and `transcribe` did not check that the patient's recording consent was recorded. Patient audio could be stored and sent to the speech-to-text provider without consent. | Privacy breach (DPDP Act); loss of trust. | 3×3 = **9 Undesirable** | Both refuse with a message until consent is recorded through "Start recording". Both clients already record consent first, so normal use is unchanged. | 3×1 = **3 Acceptable** | Retention period for consented audio (pack section 4). |
| H-07 | AI scribe audit | A rejected draft was logged only in the scribe's own review table, not in the main audit log. Two approvals at the same moment could each write a clinical note. | Incomplete audit trail; duplicate notes in the record. | 2×2 = **4 Tolerable** | `ai.draft.rejected` is written to the audit log with the reason. Approval locks the draft and re-checks its status inside the transaction. | 2×1 = **2 Acceptable** | None. |
| H-23 | MAR scheduling (timestamps) | A start time typed without a time zone (e.g. `08:00`) was read as server time (UTC), so the doses fell at **13:30** hospital time. The test confirmed 13:30 before the fix. The web form sends no start time, so this affected API callers. | Doses 5½ hours late. | 3×2 = **6 Tolerable** | Read as the hospital's clock (`HOSPITAL_TIME_ZONE`, default Asia/Kolkata). The "not yet due" message also shows hospital time. | 3×1 = **3 Acceptable** | None. |

## B. Open hazards (not fixed by engineering; need a clinical decision or a licensed product)

| ID | Workflow | Hazard | S×L | Existing control | What is needed | Owner |
|---|---|---|---|---|---|---|
| H-08 | Prescribing | No dose-range, renal/hepatic, paediatric, pregnancy or weight-based dose checking. | 5×3 = **15 Unacceptable** | The doctor's judgement; the starter checks in pack section 9. | A licensed drug-knowledge database (Phase B), **or** the hospital formally accepts this before go-live with a pharmacist review of every IPD order. | P&T committee |
| H-09 | Prescribing | Only 8 interaction rules (pending P&T approval). Duplicates are checked within one prescription, not against the patient's other active prescriptions. | 4×3 = **12 Undesirable** | High alerts block until a reason is written, and the override is audited. | P&T approval of the rule list; decide whether cross-prescription duplicate checks are required. | P&T committee |
| H-10 | MAR (PRN) | PRN doses have no minimum interval and no maximum per 24 hours. | 4×2 = **8 Undesirable** | Each PRN dose is recorded with nurse, time and notes. | The order should carry a minimum interval and a maximum daily dose; the hospital decides. | Nursing / P&T |
| H-11 | MAR | No second-nurse check for high-alert medicines (insulin, opioids, heparin, potassium). | 5×2 = **10 Undesirable** | None in software. | Clinical decision (pack section 1). | Nursing lead |
| H-12 | MAR | A nurse may record a dose or route different from the order without any warning. The actual values are stored. | 4×2 = **8 Undesirable** | The record shows ordered and given values side by side, and the change is audited. | Decide whether a mismatch must be refused, warned or allowed with a reason. | Nursing lead |
| H-13 | MAR | A reason is optional for held and refused doses; it is required only for exclusion. | 2×3 = **6 Tolerable** | None. | Clinical decision (pack section 1). | Nursing lead |
| H-14 | Laboratory | No reference ranges, abnormal flags or critical-value alerting to the ordering doctor. | 5×3 = **15 Unacceptable** | Results are released only after verification. | Reference ranges and a critical-value call procedure **(clinical)** before go-live. | Lab director |
| H-15 | Discharge | The discharge checklist (medicine reconciliation, follow-up, education) is not enforced. | 3×3 = **9 Undesirable** | A doctor-finalized summary is required. | Decide which items must block discharge. | Medical director |
| H-16 | AI scribe | Accuracy with real providers, especially for Hindi/Hinglish, was never measured. Approval is one action for the whole draft. | 4×3 = **12 Undesirable** | The draft is clearly labelled and needs doctor approval; mock providers are blocked in production; a provider failure produces no text. | A provider accuracy study on synthetic or consented recordings; decide whether each section must be acknowledged. | Medical director |
| H-17 | Patient identity | Same-name patients. | 4×2 = **8 Undesirable** | Search by UHID, masked phone shown, UHID unique per hospital. | A wristband/two-identifier check at the bedside **(clinical)**. | Nursing lead |
| H-18 | Emergency | About half of the 24 ER actions in the requirements are built. | 3×3 = **9 Undesirable** | Built actions record who acted. | The hospital confirms ER use with paper fallback for missing actions. | ER lead |
| H-19 | Break-glass / family access | Roles, duration, review timeliness and sensitive-result visibility are engineering defaults. | 3×2 = **6 Tolerable** | Every use is audited and reviewed. | Decisions in pack sections 7 and 8. | Clinical safety officer |
| H-20 | Image prediction (CNN) | **Not built.** If added without validation it could give false reassurance (false negative) or cause unnecessary treatment (false positive). | 5×1 = **5 Tolerable** (while blocked) | Hard-blocked: `/api/ai/capabilities/` reports it blocked; there is no model, dataset or ML library in the code. | See validation report section 7 before any work starts. | Medical director |
| H-21 | MAR ordering (new, caused by the H-01 fix) | Frequencies that used to be accepted silently are now refused (e.g. "Q4-6H", "1-0-1 after food"), so a doctor must rewrite them. Older orders with such text cannot be re-scheduled until they are edited. | 2×3 = **6 Tolerable** | The refusal message lists what is accepted; the prescription text itself is unchanged. | Before deployment, list existing MAR rows the parser refuses (validation report section 5) and have the doctor correct them. | Engineering + doctors |
| H-22 | Dispensing | A brand substitution is allowed when the salt *text* matches; this is not a clinical equivalence check (strength, release form). | 3×2 = **6 Tolerable** | Pharmacist only, with a written reason, audited. | P&T decides substitution rules. | P&T committee |

## Review

| Reviewed by (name, role, registration no.) | Decision (accept / changes required) | Signature | Date |
|---|---|---|---|
| | | | |
| | | | |
