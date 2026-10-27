# Clinical Safety Review Pack

For a clinical safety officer, senior doctor and pharmacist. Prepared 2026-10-26 from the code and its tests. **Engineering cannot sign this off:** each section ends with questions only a clinician can answer, and a signature line.

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

## Sign-off

| Area | Approved as is / Changes required | Reviewer | Date |
|---|---|---|---|
| MAR | | | |
| Laboratory | | | |
| Discharge | | | |
| AI scribe | | | |
| Pharmacy / blood bank | | | |
| Emergency | | | |
