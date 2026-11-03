# Clinical Safety Review Pack

For a clinical safety officer, senior doctor and pharmacist. Prepared 2026-10-26 from the code and its tests; updated 2026-11-03 (sections 7 and 8 are new). **Engineering cannot sign this off:** each section ends with questions only a clinician can answer, and a signature line.

How to use it:

1. Read the rule as implemented.
2. Try it in a staging copy with synthetic patients (never real data).
3. Answer the questions.
4. Sign or list the changes needed.

Test names point to `backend/security_tests/`.

## 0. What the system does NOT do (must be acknowledged)

- **No drug–drug, drug–allergy or dose-range checking.** There is no drug database; prescriptions are free text plus a medicine catalogue.
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
- Frequency parsing understands `QnH`, `BID`, `TID` and otherwise defaults to once daily. **Unusual frequencies are not rejected.**
- Engineering note: one older MAR model test (`nurses/tests.py`) is permanently skipped ("Requires Prescription/PrescriptionItem setup"). The behaviour above is covered by `test_mar_safety`, which runs.

**Questions for the reviewer:**

- Is defaulting unknown frequencies to once daily acceptable, or must they be refused?
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

## Sign-off

| Area | Approved as is / Changes required | Reviewer | Date |
|---|---|---|---|
| MAR | | | |
| Laboratory | | | |
| Discharge | | | |
| AI scribe | | | |
| Pharmacy / blood bank | | | |
| Emergency | | | |
| Break-glass access | | | |
| Family / caregiver access | | | |
