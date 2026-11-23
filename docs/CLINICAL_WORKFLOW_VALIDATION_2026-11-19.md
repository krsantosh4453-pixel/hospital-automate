# Clinical Workflow Validation Report

2026-11-19, branch `ui/redesign-2026-10-25` (base commit `51572f0` plus the uncommitted changes listed in section 4). Prepared by engineering for the hospital's clinical safety review.

**This report is engineering evidence, not a clinical approval.** It shows what the software does and how that was tested. Whether that behaviour is clinically safe for this hospital is decided by qualified healthcare professionals, using `CLINICAL_SAFETY_REVIEW_PACK.md`. Nothing here has been reviewed or signed by a clinician yet.

Companion documents: `CLINICAL_HAZARD_REGISTER.md` (rated hazards H-01…H-23), `CLINICAL_SAFETY_REVIEW_PACK.md` (rules, questions, sign-off), `KNOWN_LIMITATIONS.md`.

## 1. Scope and method

- **Code read line by line in this pass:**
  - MAR (`nurses/views.py`, `nurses/models.py`, `nurses/serializers.py`);
  - prescribing and medication safety (`clinical/serializers.py`, `clinical/views.py`, `clinical/medication_safety.py`, `clinical/safety_rules.py`);
  - pharmacy dispensing (`pharmacy/dispensing.py`);
  - the AI scribe (`ai_scribe/views.py`, `ai_scribe/serializers.py`, `ai_scribe/models.py`);
  - the order form `src/components/ipd/MedicationOrders.jsx` and the prescription form.
- **Covered by existing automated tests, re-run here, but not re-read line by line in this pass:** registration, appointments, queue, consultation, notes and diagnosis, nursing notes, laboratory, emergency, IPD, billing, break-glass. Their earlier reviews are in `CLINICAL_SAFETY_REVIEW_PACK.md` and `PRODUCTION_READINESS_AUDIT_2026-11-18.md`.
- **Test environment:** a clean `git archive` copy of the branch, with a fresh Python 3.12 virtualenv from `backend/requirements-lock.txt`, SQLite, `config.settings.testing`, mock AI providers, and synthetic data only.
- **Not run in this pass:**
  - the Playwright E2E suite;
  - Flutter tests (no frontend or mobile code changed);
  - PostgreSQL row-lock tests (they skip on SQLite; CI runs them on PostgreSQL);
  - any real AI, SMS or Twilio provider.

## 2. Clinical workflow validation matrix

"Reviewed" = code read in this pass. "Tests" = automated tests that passed in the final run (section 4). Hazard ids refer to the register.

| # | Workflow | Key safety controls in the software | Depth | Evidence (tests) | Result | Open hazards / clinical questions |
|---|---|---|---|---|---|---|
| 1 | Patient registration and identity | UHID unique per hospital (case-insensitive, DB constraint); search by name, phone or UHID with masked phone; tenant isolation | Tests | `patients/test_uhid.py`, `test_uhid_generation.py`, `test_patient_lookup.py`; `security_tests/test_tenant_isolation.py` | Pass | H-17 (same-name patients; bedside two-identifier check) |
| 2 | Appointment booking and cancellation | One active booking per patient, doctor and slot; slot capacity; fixed status list | Tests | `appointments/tests.py`, `test_slot_capacity.py`, `test_status.py`; `security_tests/test_patient_booking.py` | Pass | — |
| 3 | Queue and token | One token per appointment; race-safe token issue; Call Next skips safely; hospital-day counts | Tests | `encounters/test_token_issue_race.py`, `test_call_next_safety.py`, `test_hospital_day.py`; `security_tests/test_department_queue.py` | Pass | — |
| 4 | Doctor consultation | The doctor lock on Start Consultation; one open consultation per doctor | Tests | `encounters/test_start_consultation_race.py`; `clinical/test_consultation_prescription.py` | Pass | — |
| 5 | Clinical notes and diagnosis | Signed in the requesting doctor's name; records marked entered in error, never erased | Tests | `clinical/test_structured_notes.py`; `security_tests/test_rbac_decisions.py`, `test_entered_in_error.py` | Pass | ICD-10 list is partial (`KNOWN_LIMITATIONS.md`) |
| 6 | Prescription generation | Own-visit, own-name, verified registration; idempotent create; revisions kept; safety check enforced on the server; **new:** no edit once MAR orders exist (H-03) | **Reviewed** | `clinical/test_prescription_idempotency.py`, `test_prescription_integrity.py`, `test_medication_safety.py`; `security_tests/test_clinical_safety_2026_11_19.py` | Pass after fixes | H-08, H-09 |
| 7 | Nursing workflows | Notes and assessments under the nurse's own profile; care scope | Tests | `security_tests/test_nursing_authorship.py`, `test_nurse_scope.py`; `nurses/tests.py` | Pass | — |
| 8 | Medication Administration Record | Doctor-only orders from the patient's own prescription; doses only through nurse actions; row-locked; order must be in force; **new:**<ul><li>exact frequency vocabulary (H-01)</li><li>no early recording (H-02)</li><li>STAT once</li><li>hospital clock (H-23)</li></ul> | **Reviewed** | `security_tests/test_mar_safety.py`, `test_clinical_safety_2026_11_19.py` | **4 defects found and fixed** | H-10, H-11, H-12, H-13, H-21 |
| 9 | Pharmacy dispensing | Cancelled and unverified paper prescriptions refused; prescription row-locked; remaining quantity per line; expired batches refused; same-salt substitution by a pharmacist with a reason; scheduled drugs prescription-only; **new:** a paper prescription changed after verification is verified again (H-04) | **Reviewed** | `pharmacy/test_dispense_prescription.py`, `test_regulatory.py`, `test_returns_substitutes.py`; `clinical/test_prescription_transcription.py`, `test_pharmacy_queue.py` | Pass after fix | H-22 |
| 10 | Laboratory ordering and results | Ordered → collected → entered → verified → released; patients see only released results; values locked after entry | Tests | `laboratory/tests.py`, `test_sample_scan.py`, `test_imaging.py`; `security_tests/test_e2e_workflows.py` | Pass | **H-14** (no reference ranges or critical values) |
| 11 | Emergency management | Triage and actions record the acting staff member; staff of another hospital refused | Tests | `emergency/test_er_actions.py`, `test_visit_numbers.py`; `security_tests/test_emergency_flow.py` | Pass | H-18 |
| 12 | IPD admission and bed allocation | One bed per admission; transfers race-safe (PostgreSQL); discharge needs a finalized summary | Tests | `ipd/tests.py`, `test_discharge_readiness.py`; `security_tests/test_concurrency.py` (PostgreSQL only, skipped here) | Pass (row-lock part not run here) | H-15 |
| 13 | Billing and advance payments | Catalogue prices; GST; invoice numbering; advances per patient and hospital; idempotent payments | Tests | `billing/test_advances.py`, `test_invoice_numbering.py`, `test_pharmacy_billing.py`; `security_tests/test_financial_integrity.py` | Pass | — |
| 14 | Audit and break-glass | Sensitive reads audited; break-glass needs a reason, is time-limited, and is reviewed by someone else | Tests | `security_tests/test_break_glass.py`, `test_entered_in_error.py`, `test_read_roles.py` | Pass | H-19 |
| 15 | AI scribe | See section 6 | **Reviewed** | `security_tests/test_ai_scribe_safety.py`, `test_clinical_safety_2026_11_19.py`, `test_security_hardening_2026_11.py`; `ai_scribe/test_scribe_workflow.py`, `test_stt_languages.py` | **2 defects found and fixed** | H-16 |

## 3. Medication safety checklist

| Check | Status | How it is enforced / evidence |
|---|---|---|
| Correct patient–prescription association | Done | The prescription's patient must belong to the hospital, and its visit must be that patient's. A MAR order must use the patient's own prescription and item (`MARSerializer.validate`, `test_mar_safety.test_order_must_match_the_patients_own_prescription`). |
| Medicine name required | Done | `PrescriptionItemSerializer.validate_name` |
| **Frequency validation** | **Done (new, MAR)** | `nurses/frequency.py`, H-01. On the prescription itself frequency stays free text, because it is printed for the patient; it is validated when a MAR order is made from it. |
| Dose validation | **Not done** | Dose is free text; no dose-range checking (H-08) |
| Route validation | Partial | MAR route comes from a fixed list in the web form; the API accepts free text. |
| Duplicate medication | Partial | Same salt twice on one prescription is a moderate alert; other active prescriptions are not checked (H-09). |
| Allergy checks | Done, with limits | Allergy classes and salts; across hospitals; **new:** brand-name allergies via the catalogue, and an "allergy not checked" note (H-05). High alerts block until a reason of 10+ characters is written; overrides are audited. |
| Interactions | Partial | 8 starter rules, pending P&T approval (H-09) |
| Stock and dispensing consistency | Done | Row-locked stock; expired batches refused; per-line remaining quantity; stock ledger (`test_financial_integrity`, `test_dispense_prescription`) |
| MAR recording and audit history | Done | Each outcome records nurse, login and time, and writes an audit entry; doses cannot be edited directly; **new:** history can no longer be erased by a prescription edit (H-03). |
| Unauthorised prescription changes | Done | Only the prescribing doctor (or the pharmacy for its own paper transcriptions) may change a prescription. Lines change only through the whole prescription, which re-runs the safety check. Dispensed prescriptions are locked. Every version is kept. **New:** paper changes need re-verification (H-04). |

## 4. Defects found, fixes and regression evidence

Each test below was run against the unfixed code (RED) and after the fix (GREEN), in the same scratch copy.

| Hazard | Defect | Fix (file) | RED result before the fix | GREEN |
|---|---|---|---|---|
| H-01 | Unknown frequencies scheduled once daily; WEEKLY daily; STAT repeated; SOS scheduled; Q0H infinite loop | New `backend/nurses/frequency.py`; `nurses/views.py` `generate_schedule`, `prn`; `nurses/serializers.py` `validate_frequency` | WEEKLY: `15 != 3` doses. `1-0-1`: interval `1 day != 12 hours`. STAT: `15 != 1`. "as directed" saved: `201 != 400`. SOS: doses scheduled. Stopped order scheduled: `200 != 400`. Q0H: the request never finished (the run was stopped after 10 minutes). | Pass |
| H-02 | Future dose recordable as given or missed | `nurses/views.py` `administer`, `mark_missed` (`not_yet_due`) | Dose due in 5 h recorded as given: `200 != 400` | Pass |
| H-03 | Prescription edit cascade-deleted the MAR | `clinical/serializers.py` `update`; `nurses/models.py` PROTECT; migration `nurses/0010_mar_protect_prescription.py` | Edit accepted (`200 != 400`). A separate probe showed `MAR rows left 0, doses left 0` after the edit. | Pass |
| H-04 | Paper prescription changed after verification stayed Confirmed | `clinical/serializers.py` `_send_back_for_verification` | `'Confirmed' != 'Pending Verification'` | Pass |
| H-05 | Brand-name or unreadable allergies not checked | `clinical/medication_safety.py` `_brand_salts`, `allergy_unchecked` alert | Augmentin allergy + amoxicillin: no alert (`not found in set()`). Unreadable allergy: `0 != 1` notes. | Pass |
| H-06 | Audio uploaded and transcribed without consent | `ai_scribe/views.py` `_no_recording_consent` in `upload_audio`, `transcribe` | Upload without consent: `200 != 400` | Pass |
| H-07 | Rejection not in the audit log; concurrent approvals | `ai_scribe/views.py` `reject` (audit), `approve` (row lock and re-check) | `AuditLog.DoesNotExist` for `ai.draft.rejected` | Pass. The lock is a no-op on SQLite; it takes effect on PostgreSQL. |
| H-23 | Naive start time read as UTC | `nurses/views.py` `generate_schedule` | First dose at `(13, 30) != (8, 0)` | Pass |

**Existing test changed:** `security_tests/test_security_hardening_2026_11.py`, `AudioUploadValidationTests.setUp`, now records consent first. Without that, two of its "refused" tests would pass only because consent was missing, not because of the audio checks they test. All three pass with consent recorded.

**Full backend suite, final run:** `Ran 1216 tests in 41.459s — OK (skipped=29)`. `makemigrations --check` reports "No changes detected". The 29 skips are the PostgreSQL row-lock tests and other environment-gated tests, as before. One earlier full run had found the audio-validation test described next.

Files changed (uncommitted; nothing was committed or deployed):

- `backend/nurses/frequency.py` (new), `backend/nurses/views.py`, `backend/nurses/serializers.py`, `backend/nurses/models.py`, `backend/nurses/migrations/0010_mar_protect_prescription.py` (new)
- `backend/clinical/serializers.py`, `backend/clinical/medication_safety.py`
- `backend/ai_scribe/views.py`
- `backend/security_tests/test_clinical_safety_2026_11_19.py` (new, 20 tests), `backend/security_tests/test_security_hardening_2026_11.py`
- `docs/CLINICAL_HAZARD_REGISTER.md` (new), this report (new), `docs/CLINICAL_SAFETY_REVIEW_PACK.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/README.md`

## 5. Before deploying these fixes

The frequency rule (H-01) applies to new and edited MAR orders. Orders already in a database may hold text the parser refuses (H-21). They also may already have doses scheduled at the wrong rate, by the old logic. Before deployment, run this read-only check and give the list to the doctors:

```bash
python manage.py shell -c "from nurses.models import MAR; from nurses.frequency import parse_frequency, FrequencyError
for m in MAR.objects.filter(is_active=True):
    try: parse_frequency(m.frequency)
    except FrequencyError: print(m.pk, m.patient_id, m.medicine_name, repr(m.frequency))"
```

For every active order whose frequency is not once daily, also check that its future scheduled doses match the intended rate. The old logic scheduled BD, TDS, `1-0-1`, EOD and WEEKLY once a day. The doctor should stop and re-order any that are wrong.

## 6. AI scribe safety

| Requirement | Status | How it is enforced | Evidence |
|---|---|---|---|
| AI output is always a draft | Done | Drafts carry a "Pending Review" label and live in `AIConsultationDraft`; nothing is written to `ClinicalNote` before approval. | `test_ai_scribe_safety.test_draft_needs_clinician_approval_before_entering_record` |
| No automatic clinical approval | Done | Approval is a separate doctor action. Clients cannot set status through create, edit or delete (405). Generation never approves. | `test_ai_scribe_safety.test_transcripts_reviews_and_drafts_cannot_be_written_directly` |
| Doctor review is mandatory | Done | Approval requires a Doctor profile linked to the login, in that hospital. The doctor must be the consulting doctor, and generation must have finished. | same file |
| Approval and rejection auditable | Done (**rejection new**) | `ai.draft.approved`, `ai.draft.generated`, `ai.draft.section_edited` and, **new**, `ai.draft.rejected` with the reason; every action also has a `DoctorReview` row. | `test_clinical_safety_2026_11_19.ScribeConsentTests` |
| Patient consent enforced | Done (**upload and transcribe new**) | Consent is recorded through Start recording (who and when, audited). **New:** upload and transcription are refused without it. | `ScribeConsentTests.test_audio_cannot_be_uploaded_or_transcribed_without_consent` |
| Transcripts and drafts cannot be forged | Done | Transcripts and review history are read-only. Drafts accept only workflow actions. Edits go through `review` with section coercion and are audited. | `test_ai_scribe_safety` (all `405`) |
| Provider failure never fabricates content | Done | Mock providers are refused in production settings. Without a provider the feature answers 503 "unavailable". A failure leaves the draft unapprovable, because `generation_completed_at` is empty. | `test_ai_scribe_safety` provider-failure tests; `ai_scribe/test_scribe_workflow.py` |
| Accuracy of a real provider | **Not verified** | Never run with real credentials. | H-16 |

## 7. CNN image prediction: assessment (not built)

The software has **no image model, no dataset and no machine-learning library** (checked: no torch, tensorflow, keras or onnx in the code or `requirements-lock.txt`). `GET /api/ai/capabilities/` reports `image_prediction: blocked` with the reason "No validated imaging model, dataset or approved medical use case is configured", and the mobile AI screen shows it as Blocked. **Nothing was built, simulated or enabled in this review.**

Before any image-prediction work begins, the hospital needs:

1. **A defined intended use.** One modality, body part, finding, patient population, setting and user, for example: "chest X-ray triage for suspected pneumothorax in adult ED patients, read by an ED doctor". The output must be a second reader or triage aid, never a diagnosis.
2. **A validated dataset.** De-identified images, collected with consent and ethics approval, labelled by qualified radiologists with an agreed reference standard. They must come from the hospital's own machines and population, with separate training, tuning and *locally held-out* test sets, plus at least one external site.
3. **Evaluation before use:**
   - sensitivity and specificity at a pre-registered operating point;
   - PPV and NPV at local prevalence, and AUROC with confidence intervals;
   - calibration;
   - results per subgroup (age, sex, device, image quality);
   - a reader study comparing clinicians with and without the aid.
4. **False-negative / false-positive risk analysis.**
   - A false negative (missed finding) can delay treatment and give false reassurance; this is usually the more severe error.
   - A false positive can lead to unneeded tests, treatment and anxiety, and alert fatigue.
   
   The acceptable rates and the operating point are clinical decisions, recorded in the hazard register before go-live.
5. **Regulatory and clinical approval.** In India, software intended for diagnosis is regulated as a medical device (CDSCO, Medical Devices Rules 2017); regulatory counsel must confirm the class and licence needed. The hospital ethics committee, the medical director and the clinical safety officer must also approve.
6. **Operational controls:** model version pinned and logged with every prediction; clinician confirmation required; live performance monitoring and drift checks; a kill switch; a process for incident reporting.

Until all of this exists and is signed, image prediction must stay blocked (H-20).

## 8. Clinical data integrity

| Area | Finding |
|---|---|
| Patient identity consistency | UHID unique per hospital (database constraint since R-08); `report_duplicate_uhids` before migrating real data. |
| Encounter and prescription relationships | A prescription's visit must be the same patient's and hospital's, and the doctor's own. MAR orders must use the patient's own prescription and item. **New:** MAR orders can no longer lose their prescription link (H-03). |
| Hospital-level isolation | Every viewset is hospital-scoped, fail-closed (`test_tenant_isolation`, `test_handwritten_views_isolation`, `test_tenancy_guard`). |
| Modification history | Prescriptions keep every version (`PrescriptionRevision`). Clinical records are marked entered in error, never deleted. Audit entries hold before-values. **New:** the MAR history is protected (H-03). |
| Timestamps | Stored in UTC (`USE_TZ=True`); "today" follows `HOSPITAL_TIME_ZONE`. **New:** MAR start times typed without a zone use the hospital clock (H-23). |
| Duplicate records | Bookings, queue tokens and prescriptions are idempotent or unique. A STAT dose is never scheduled twice (new). |
| Concurrent operations | MAR doses, dispensing, bed allocation, consultation start and token issue are row-locked. **New:** AI draft approval is row-locked. The PostgreSQL lock tests run in CI, not in this SQLite run. |
| Error and recovery | Provider failures leave records unchanged. A dispensing failure issues nothing (all-or-nothing). Refusals explain what to do. |

## 9. Known clinical limitations

The open hazards H-08 to H-22 in `CLINICAL_HAZARD_REGISTER.md`, and `KNOWN_LIMITATIONS.md`.

Rated **Unacceptable**; a clinical decision is needed before real patient use:

- **H-08:** no dose-range checking;
- **H-14:** no laboratory reference ranges or critical values.

Rated **Undesirable**; also needed before go-live:

- **H-09:** starter interaction list not yet approved;
- **H-16:** AI scribe accuracy not measured.
