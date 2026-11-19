# Clinical Safety Review Pack

For a clinical safety officer, senior doctor and pharmacist. Prepared 2026-10-26 from the code and its tests; updated 2026-11-03 (sections 7 and 8 are new) and 2026-11-19 (sections 10–12, the approval checklist and the hazard register). **Engineering cannot sign this off:** each section ends with questions only a clinician can answer, and a signature line.

Read with: `CLINICAL_HAZARD_REGISTER.md` (rated hazards and residual risks) and `CLINICAL_WORKFLOW_VALIDATION_2026-11-19.md` (workflow test report and regression evidence).

How to use it:

1. Read the rule as implemented.
2. Try it in a staging copy with synthetic patients (never real data).
3. Answer the questions.
4. Sign or list the changes needed.

Test names point to `backend/security_tests/`.

## 0. What the system does NOT do (must be acknowledged)

- **Only limited medication checking (section 9).** Allergy, duplicate-salt and a starter list of 8 interactions are checked; there is no full drug database and no dose-range checking.
- No ICD-10 coding, no structured EMR sections, no clinical decision support.
- AI scribe output is a draft only (section 4); its accuracy for Hindi/Hinglish depends on the provider chosen.
- SMS, WhatsApp and voice alerts are not sent. Patients are not told by SMS that results are ready.

| Acknowledged by (name, role) | Signature | Date |
|---|---|---|
| | | |

## 1. Medication Administration Record (MAR) — `nurses/views.py`

**As implemented** (`test_mar_safety`):

- Generating a schedule creates doses as **Scheduled**. Nothing is ever recorded as given automatically.
- A dose becomes **Administered** only through the nurse's "administer" action. The nurse and the time are recorded.
- Administering the same dose twice is refused.
- Regenerating the schedule keeps doses already recorded.
- A dose cannot be marked Administered by editing its status field directly.
- **Excluding** a dose (e.g. NPO) requires a reason.
- **PRN** doses can only be recorded against a PRN order, and are recorded as administered at that moment with notes.
- Frequencies (since 2026-11-19, hazard H-01): only a fixed vocabulary is accepted, and anything else is **refused** when the doctor saves the order. Until then, unknown frequencies, including BD, TDS, `1-0-1` and WEEKLY, were silently scheduled once daily. The vocabulary:
  - OD/BD/TDS/QDS/HS and BID/TID/QID;
  - Q*n*H or "every *n* hours" (1–168);
  - the `1-0-1` pattern (scheduled at equal intervals);
  - EOD, WEEKLY;
  - STAT/ONCE (one dose only);
  - PRN/SOS (never scheduled).
- A dose can be recorded as given from 60 minutes before its time (`MAR_EARLY_ADMINISTRATION_MINUTES`), and cannot be marked missed before it is due (H-02).
- Engineering note: one older MAR model test (`nurses/tests.py`) is permanently skipped ("Requires Prescription/PrescriptionItem setup"). The behaviour above is covered by `test_mar_safety`, which runs.

**Questions for the reviewer:**

- Approve the frequency vocabulary above. Is equal-interval scheduling of `1-0-1` acceptable, or must doses follow fixed ward times (e.g. 08:00 / 20:00)?
- Is 60 minutes the right early-administration window?
- Must PRN orders carry a minimum interval and a maximum per 24 hours (H-10)?
- Is a reason needed for "missed" or "refused" doses as well as exclusions?
- Is a second-nurse check required for high-alert drugs (insulin, opioids)? None exists.

## 2. Laboratory results — `laboratory/views.py`

**As implemented** (`test_e2e_workflows`):

- Flow: Ordered → Sample collected → Result entered → **Verified** (lab staff; only from "Result entered") → **Released** (lab staff; only after verification).
- Patients see results only when Released.
- Result values cannot be changed through ordinary edits after entry.
- Released or verified tests cannot be cancelled.
- No reference-range flagging or critical-value alerting to the ordering doctor.

**Questions:**

- Must verification and release be done by different people?
- Which critical values need a phone call, and who records it?
- Are reference ranges and abnormal flags required before go-live?

## 3. Inpatient discharge — `ipd/views.py`

**As implemented** (`test_e2e_workflows`):

- Discharge must first be initiated.
- Completion is refused until **a doctor finalizes the discharge summary**.
- A finalized summary is locked; later information is added as discharge notes (addenda).
- Completing discharge frees the bed.
- The discharge checklist is **not enforced**, and discharge is **not linked to final billing**.

**Questions:**

- Which checklist items (medicine reconciliation, follow-up, patient education) must block discharge?
- Who may discharge against medical advice, and what must be recorded?

## 4. AI medical scribe — `ai_scribe/views.py`

**As implemented** (`test_ai_scribe_safety`):

- AI output is a **draft**. Nothing enters the clinical record until a doctor linked to that hospital approves it.
- Drafts cannot be approved by editing fields.
- Mock (development) providers are never allowed in production. Without a real provider the feature answers "unavailable" rather than producing invented text.
- Provider failures do not modify the record.
- Only audio uploads are accepted.

**Questions:**

- Is the approving doctor required to edit or acknowledge each section, or is one approval enough?
- Must the original audio be kept, and for how long (consent and retention)?
- Which provider will be used, and has it been checked for Hindi/Hinglish accuracy?

## 5. Pharmacy and blood bank

**As implemented** (`test_financial_integrity`, `test_bloodbank_flow`):

- Sales use catalogue prices.
- **Expired batches cannot be dispensed.**
- The stock ledger stays consistent.
- Blood requests cannot be approved beyond available stock; issue deducts stock.
- There is no cross-matching record.

**Questions:**

- Is a pharmacist check required before dispensing?
- What blood-bank records (cross-match, issue-to-transfusion) are mandatory locally?

## 6. Emergency

**As implemented** (`test_emergency_flow`):

- Triage and the ER flow record which staff member acted.
- Staff from another hospital cannot be recorded.
- About half of the 24 ER actions listed in the requirements exist (`KNOWN_LIMITATIONS.md`).

## 7. Break-glass emergency access — `audit/break_glass.py` (new)

**As implemented** (`test_break_glass`):

- A **Doctor or Nurse** may open access to a patient of their hospital who is not in their care. A written reason of at least 20 characters is required.
- Access lasts `BREAK_GLASS_DURATION_MINUTES` (default **60 minutes**), or until they end it.
- Every read made under it is marked in the audit trail.
- An **Admin or Hospital Manager** of that hospital reviews each grant afterwards, and may not review their own.
- It is API-only: there is no screen for it yet, so in practice it cannot be used by clinical staff today.

**Questions:**

- Which roles may break the glass? Should nurses be allowed, or doctors only?
- Is 60 minutes right? Should the person be able to extend it, or must they open a new grant?
- How soon must a grant be reviewed, and what happens when a reason is found inadequate?
- Must the patient be told afterwards that their record was opened this way?

## 8. Family and caregiver (proxy) access — `users/proxy_access.py` (new)

**As implemented** (`test_proxy_access`, E2E `e2e/family-access.spec.js`):

- The **patient** adds up to 5 family members (name, relationship, mobile). Staff cannot add them.
- A family member signs in with an OTP sent to **their own** mobile and then sees the patient's appointments, prescriptions, released lab results, bills and documents. A banner says they are viewing someone else's records.
- Access is **view-only**: they cannot sign consents, upload, share or manage access. Every request re-checks the grant, so removing access ends it at once.
- There is **no per-category restriction**: a family member sees everything the patient sees in the portal.

**Questions:**

- Should some results be hidden from family members (for example HIV, mental health, reproductive or genetic results)?
- For **minors** and patients who lack capacity, who may grant access? Today only the patient can, from their own account.
- Should a doctor be able to see who has family access when sharing sensitive news?

## 9. Medication safety check when prescribing — `clinical/medication_safety.py`, `clinical/safety_rules.py` (new, Phase A)

**As implemented** (`clinical/test_medication_safety.py`, E2E `e2e/medication-safety.spec.js`):

- Before a prescription is saved, each medicine's **salt** is identified from the hospital catalogue (Inventory/Pharmacy "Salt (generic name)") or from a salt name written in the text (for example "Tab Ibuprofen 400").
- It is checked against:
  - the patient's **allergies recorded in this hospital**, including drug classes (penicillins, cephalosporins, sulfonamides, NSAIDs, fluoroquinolones, macrolides);
  - the **same salt twice** on one prescription;
  - a **starter list of 8 interactions**: PDE5 inhibitors + nitrates/nicorandil; warfarin/acenocoumarol + NSAIDs; simvastatin/lovastatin + clarithromycin, erythromycin, azole antifungals or ritonavir; linezolid/MAOIs + SSRIs/SNRIs/tramadol; methotrexate + co-trimoxazole; tizanidine + ciprofloxacin/fluvoxamine (all **high**); clopidogrel + omeprazole/esomeprazole; ACE inhibitors/ARBs + spironolactone/eplerenone/potassium chloride (**moderate**).
- **High** alerts (allergy, high interactions) block saving until the doctor writes a reason (at least 10 characters). The alerts and reason are stored on the prescription and an audit entry `clinical.prescription.safety_override` is written. The server enforces this, not only the screen.
- **Moderate** alerts and duplicates are shown but do not block. A medicine whose salt is not recognised is shown as "not identified, so it was not checked".
- **Not checked:** dose ranges, renal/hepatic dosing, pregnancy, age, interactions outside the list, other active prescriptions of the patient, allergies recorded in other hospitals, and free-text brand names without a catalogue salt.

**Questions for the Pharmacy & Therapeutics committee:**

- Approve, amend or replace each of the 8 interaction rules and the allergy classes (`clinical/safety_rules.py`, version `2026-11-03.1`). Which further pairs are mandatory before go-live?
- Is "prescribe anyway with a written reason" acceptable for allergy alerts, or must some be a hard stop?
- Should duplicates also be checked against the patient's other active prescriptions?
- Who reviews `clinical.prescription.safety_override` audit entries, and how often?
- Which licensed drug database should replace or extend this list (Phase B)?

## 10. Defects fixed on 2026-11-19 (for confirmation)

Found while preparing this pack. Each one has a test that failed before the fix and passes after it (`CLINICAL_WORKFLOW_VALIDATION_2026-11-19.md`, section 4). Details and ratings are in `CLINICAL_HAZARD_REGISTER.md`.

| Hazard | What was wrong | What it does now |
|---|---|---|
| H-01 | MAR scheduled BD, TDS, `1-0-1`, EOD and **WEEKLY** once daily, repeated STAT doses daily, scheduled SOS doses, and hung on Q0H. | Exact vocabulary; anything else refused (section 1). |
| H-02 | A future dose could be recorded as given or missed. | Given from 60 minutes before its time; missed only once due. |
| H-03 | Editing a prescription **erased** its MAR orders and every recorded dose. | A prescription with MAR orders cannot be edited: stop the orders and write a new one. Links are protected. |
| H-04 | A verified paper prescription could be changed and dispensed without a new check. | Any change sends it back for verification by someone else. |
| H-05 | Allergies recorded by brand name were never matched; unreadable allergies passed silently. | Brands are matched through the catalogue; an unreadable allergy shows "not checked — check it yourself". |
| H-06 | AI-scribe audio could be uploaded and transcribed without the patient's consent. | Refused until consent is recorded. |
| H-07 | AI-draft rejections were not in the audit log; two approvals at once could write two notes. | Rejections audited; approval locked. |
| H-23 | A MAR start time typed as 08:00 was taken as UTC (13:30 at the hospital). | Hospital clock. |

**Questions:**

- Confirm each new behaviour, especially that **H-03** (stop and re-order instead of editing) fits the ward workflow.
- **Before deployment:** existing MAR orders may have been scheduled at the wrong rate by the old logic. Who reviews the list produced in section 5 of the validation report?

## 11. Image prediction (CNN): not built

There is no image model, dataset or approved use case. The feature reports "blocked" in the app and API, and nothing was built, simulated or enabled. Section 7 of the validation report lists what is required first:
- intended use;
- a validated local dataset;
- evaluation, including false-negative and false-positive analysis;
- CDSCO medical-device status;
- ethics committee approval;
- monitoring.

**Acknowledgement:** image prediction stays disabled until a separate validation and authorisation is signed.

| Acknowledged by (name, role) | Signature | Date |
|---|---|---|
| | | |

## 12. AI scribe safety summary

All of these are enforced in the server, with tests (validation report section 6):
- the output is a draft;
- it is never approved automatically;
- only the consulting doctor, linked to a doctor profile, can approve it;
- approval, rejection and edits are audited;
- consent is required before recording, upload and transcription;
- transcripts and review history cannot be edited;
- mock providers are refused in production, and a provider failure writes nothing.

**Not verified:** accuracy of any real provider (H-16).

## Clinical approval checklist (before any real patient use)

Each line is ticked by the named role, not by engineering.

| # | Item | Owner | Done (initials, date) |
|---|---|---|---|
| 1 | Every hazard in `CLINICAL_HAZARD_REGISTER.md` reviewed, re-rated if needed, and accepted or sent back | Clinical safety officer | |
| 2 | Decision recorded on H-08 (no dose-range checking): a licensed drug database, or written acceptance with pharmacist review of IPD orders | P&T committee | |
| 3 | Starter interaction rules and allergy classes approved or amended (section 9) | P&T committee | |
| 4 | MAR frequency vocabulary, early-administration window and PRN limits approved (section 1) | Nursing lead + P&T | |
| 5 | Existing MAR orders checked after deploying the H-01 fix (validation report section 5) | Ward doctors | |
| 6 | Laboratory reference ranges and the critical-value call procedure in place (H-14) | Lab director | |
| 7 | Discharge checklist items that must block discharge decided (section 3) | Medical director | |
| 8 | AI scribe provider chosen and accuracy checked on synthetic or consented recordings; audio retention period set (section 4) | Medical director + DPO | |
| 9 | Break-glass and family-access rules decided (sections 7 and 8) | Clinical safety officer | |
| 10 | Each workflow tried in staging with synthetic patients by its user group (doctor, nurse, pharmacist, lab, ER, billing) | Department leads | |
| 11 | Paper fallback procedure for downtime and for ER actions not built (H-18) | Medical director | |
| 12 | Image prediction acknowledged as disabled (section 11) | Medical director | |

## Sign-off

Sign only after trying the workflow in staging with synthetic patients. Engineering does not sign this table.

| Area | Approved as is / Changes required | Reviewer (name, role, registration no.) | Signature | Date |
|---|---|---|---|---|
| MAR (incl. section 10 changes) | | | | |
| Laboratory | | | | |
| Discharge | | | | |
| AI scribe | | | | |
| Pharmacy / blood bank | | | | |
| Emergency | | | | |
| Break-glass access | | | | |
| Family / caregiver access | | | | |
| Medication safety rules (section 9) | | | | |
| Prescription changes and paper re-verification (section 10) | | | | |
| Hazard register (all hazards) | | | | |
| Image prediction disabled (section 11) | | | | |

## Changes since 2026-11-03 for the clinical safety officer (added 2026-11-08)

Please review and sign off each item; the code and tests are in commit history under P0/P1.

1. **Medicine lines are changed only through the whole prescription** (RL-01). The item endpoint is read-only. Every change re-runs the allergy, duplicate and interaction check, and an override still needs a written reason.
2. **Allergies follow the patient across hospitals** (P1-07, owner's decision). An allergy recorded at another hospital blocks prescribing and names that hospital. Confirm this is the intended clinical behaviour.
3. **Scheduled drugs are prescription-only** (P1-10). Schedule H, H1, X and NDPS medicines cannot be sold over the counter. Sales of H1/X/NDPS drugs appear in the Schedule H1 register with prescriber, registration number, patient, batch and quantity.
4. **Patients are chosen by search with UHID** (RL-03). Pickers in IPD, lab, prescription, radiology, blood bank, emergency and billing no longer list only 50 patients. Same-name patients show different UHIDs and masked phones.
5. **Cross-role dispensing closed** (RL-02). A user dispenses only where they hold the Pharmacist role.
6. **Double bookings refused** (P1-04). One active booking per patient, doctor and slot, and one queue token per appointment.

Open for the reviewer:
- the starter interaction list (8 rules) still needs Pharmacy & Therapeutics approval
- there is no dose-range checking
