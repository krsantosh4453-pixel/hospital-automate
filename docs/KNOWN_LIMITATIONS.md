# Known Limitations

State as of 2026-10-25, updated 2026-11-03, branch `ui/redesign-2026-10-25`. Row ids refer to `REQUIREMENTS_TRACEABILITY.md`. Nothing here is presented in the UI as working.

## Release blockers (must be resolved before real patient use)

| # | Limitation | Why it blocks | Action |
|---|---|---|---|
| L1 | Partly done 2026-11-03: `docker-compose.prod.yml` was run locally with production settings, a self-signed certificate and synthetic secrets (all 7 containers healthy; TLS, headers, `/media/` denial, rate limits, restart, persistence and a backup/restore drill verified; four defects fixed). Not yet run on a real staging host with its domain, a CA certificate (OCSP stapling) and real provider credentials | Behaviour behind a real domain, certificate and network edge is unverified | Repeat the rehearsal on the staging host (`DEPLOYMENT.md` steps 1–8). Build images from a clean git checkout: one file's case on the Mac disk differed from git and broke the Linux build |
| L2 | Twilio Verify, SMS/WhatsApp, email, STT/LLM providers and Google sign-in were never exercised with real credentials | Production settings require OTP; staff can't sign in if Verify fails; AI scribe answers 503 without a provider | Configure staging credentials and run the sign-in, OTP, AI-draft and notification flows end to end |
| L4 | No clinical safety review of the workflows | MAR, discharge, lab release, AI-draft, break-glass and family-access rules were designed by engineering only | Sign-off by a clinical safety officer / pharmacist using `CLINICAL_SAFETY_REVIEW_PACK.md` (updated 2026-11-03) |
| L5 | No penetration test or DPDP Act privacy assessment | Required for health data in India | Commission both; brief and baseline in `PRIVACY_AND_PENTEST_PACK.md` (updated 2026-11-03) |

## Missing features (none MISSING as of 2026-11-05; J6 is PARTIAL, see below)

- **Pharmacy:** drug alerts (F7) are partial: allergy, duplicate-salt and a starter list of 8 interactions, pending Pharmacy & Therapeutics approval; no licensed drug database and no dose-range checks (`CLINICAL_SAFETY_REVIEW_PACK.md` section 9).
D6, K6 and K8 were ported on 2026-11-05 from the branch `claude/intelligent-keller-502e5b`, which can now be retired. Limits that remain:

- **ICD-10 (D6):** only about 190 common ICD-10-CM codes ship with the app (`terminology/data/icd10_common.csv`, loaded at start when the table is empty). Load the full yearly CMS release with `manage.py load_icd10 <file>`. The diagnosis box still accepts free text.
- **AI discharge draft (K6):** with no AI provider configured, the draft is assembled from the admission's records, not written by a model. A doctor must tick "I have reviewed" before saving, and finalizing and signing stays a separate step. The draft prompt and its output need clinical review before a real model is used.
- **Voice-call fallback (K8):** the default provider is `noop`, which records every call as skipped and dials nothing. Real calls need `VOICE_CALL_PROVIDER=twilio`, Twilio Voice credentials and a voice-capable number; this has not been tested with a real call. A call waits 10 minutes and is skipped if a text message or call reached the patient meanwhile.

- **Hospital services (2026-11-05):** OT, ambulance, mortuary, CSSD, laundry, staff leave, patient feedback and templates are on the Hospital services page. The OT schedule is shown to every doctor and nurse of the hospital, not only to those caring for the patient, because theatre staff work cases outside their own patients. HR covers leave only (no payroll, attendance or general roster); feedback is entered by staff (not yet from the patient portal); templates are kept but not yet offered inside the notes editor. Ambulance tracking has no GPS or live location.

## Partial features (8 PARTIAL rows, recounted 2026-11-03; main ones)

- Hindi (A17, 2026-11-03): every page shows its own text in Hindi, including Laboratory and Pharmacy, dropdown options, filter and role labels kept in JavaScript lists, server status values, toast messages and sentences with names or numbers (through `t()` `{placeholders}`). A Hindi pass over 30 pages leaves 63 distinct English strings, nearly all names, dates, IDs and abbreviations (MAR, OPD, AVPU). Since 2026-11-05 notification and activity times ("just now", "5 min ago") and the admin dashboard's activity lines are translated, and sentences around links are translated whole. Still English: raw audit action codes on the Audit log page (technical identifiers) and any audit action not in the dashboard's word list. Clinical and patient data (diagnoses, bill lines, document titles, notifications) stay exactly as entered. The translations were written by engineering and need review by Hindi-speaking clinical staff.
- Notifications: in-app works; SMS/WhatsApp need consent and credentials (K7).
- Procurement (2026-11-05): Inventory has Suppliers, Purchase orders, Requisitions and Issues & returns tabs. Requisitions are approved by an admin or manager other than the requester and ordered directly or through a quotation; stock can be issued to departments, returned to suppliers and, for consignment orders, settled as used. Limits: stock issued to a department leaves the store's count and is not tracked as ward stock afterwards; consignment settlement records the amount payable but is not linked to accounts payable; nurses can raise requisitions through the API but do not have the Inventory page.
- Admin → Permissions is a read-only view of the built-in roles (2026-11-03). Roles cannot be customised: changing what a role may do needs a code change to both `RoleContext.jsx` and the backend permission classes.
- Medicine orders (MAR) are written only by doctors, from the IPD page, and only from the patient's own prescription. There is no verbal or telephone order path for nurses, by the owner's decision (2026-11-05).
- Records removed as entered in error are hidden everywhere, including from the Django admin; they are read through `all_objects` or the Audit log page. A removed patient's visits, bills and other records stay visible where they are listed on their own.
- Dispensing (2026-11-05): by default every medicine still owed is issued in one step, or none if any line fails. A pharmacist can give part now and the rest later, and can give another brand only when it has the same salt as the prescribed brand's catalogue entry, with a reason. Substitution depends on the salt (generic name) being recorded for both brands in Inventory; it is not a clinical equivalence check, and a different salt still needs the doctor to change the prescription. Sales made outside the prescription screen are not counted against a prescription's remaining quantity.
- Medicine returns (F5) record the refund amount, but pharmacy sales are not linked to billing invoices, so the cash refund is paid at the pharmacy counter and is not reflected in Billing.
- Lab staff (2026-11-03) find a walk-in patient by searching name, phone or UHID (3+ characters, at most 20 matches, masked phone, every lookup audited); they still cannot browse the patient list or register a new patient.
- The financial report returns `laboratory_revenue: null` by design (checked 2026-11-05): lab tests carry no price, and no requirement defines a lab price list, so lab charges appear only as invoice lines inside billing revenue. A real figure needs a hospital-approved lab tariff and invoice lines linked to lab tests; it is not invented.
- Advance payments (H4) are per patient and hospital. Advance money cannot move to another hospital, and the advance is shown on the Billing page, not on the patient's own portal.

## Blocked (3) and not applicable (1)

- Hindi/Hinglish speech recognition depends on the STT provider chosen (K5).
- ABDM/ABHA (K10) and FHIR (K11): routes are mounted at `/api/abdm/` and `/api/fhir/` but are off in production unless `ABDM_ENABLED` / `FHIR_ENABLED` is set. ABDM needs sandbox credentials, certification and a security review. HL7 v2 is still not mounted.
- ML/DL forecasting (K9) is deliberately not built: there is no labelled data or validation. Queue estimates are rule-based.

## Technical limitations

- SMS, WhatsApp and voice delivery are not implemented and need provider credentials. External channels already go through the Celery retry task (`notifications.tasks.send_notification_channel`: 5 retries, exponential backoff, every attempt logged), so adding a provider needs no queue changes.
- Row-lock tests (`security_tests/test_concurrency.py`) run only on PostgreSQL (`TEST_DATABASE_URL`); on SQLite they are skipped. CI runs them on PostgreSQL 16 with `REQUIRE_ROW_LOCK_TESTS=1`, which fails the run instead of skipping. They found and fixed two IPD races: one admission getting several beds, and parallel transfers. A refused transfer no longer releases the patient's current bed.
- Frontend tests: 65 Vitest unit tests plus 23 Playwright E2E tests in `e2e/`, run in CI. Since 2026-11-03 these include lab order to release, pharmacy dispensing, emergency registration and triage, a nurse giving a MAR dose, and break-glass access opened by a doctor and signed off by an administrator.
- Route-level code-splitting brings the main JS bundle to 310 kB (89.9 kB gzip). Lint has 22 warnings and 0 errors (2026-11-03): 18 are the context-plus-hook file pattern, which only affects dev hot reload, and 4 are effect dependencies that need their own testing before changing.
- API schema / Swagger / ReDoc work again (they returned 500 before 2026-11-03) and are platform-admin only in production (`API_DOCS_PUBLIC`). drf-spectacular reports 241 documentation warnings (mostly missing type hints).
- Django errors are written to `django_errors.log` in the `app_logs` volume, not to container output; log shipping must collect that volume.
- Sensitive reads are audited: every list or detail read of patient data by staff writes `<model>.list` / `<model>.read` with the patient ids. That is one row per request, so plan audit retention (`AUDIT_LOG_RETENTION_DAYS`). Break-glass access has a screen at `/emergency-access` (2026-11-03): a Doctor or Nurse opens time-limited access by patient number with a written reason and can end it; an Admin or Hospital Manager signs each grant off. Its rules still need clinical sign-off (L4).
- `backend/db.sqlite3` was purged from the GitHub history on 2026-10-26 (R-02). Old local `agents/*` branches on the development machine still contain it; delete them locally when they are no longer needed. GitHub's read-only `refs/pull/1/*` may still reference the old commits until GitHub Support purges them.
- Reads are limited by role (R-15, 2026-11-03): consent records and shares go to Admin, Hospital Manager, Receptionist, Doctor and Nurse; patient documents to the roles that upload them; Doctors and Nurses see only patients in their care. Money figures (billing and pharmacy revenue, revenue forecast) go to Admin, Hospital Manager, Billing Staff and Receptionist; other roles get counts only.
- UHIDs are unique within a hospital, ignoring case, in the API and in the database (R-08). Before migrating a real database, run `python manage.py report_duplicate_uhids` (read only) and settle any duplicates; the migration stops with that instruction if it finds some.
- Email OTPs are stored as a keyed HMAC since 2026-11-03; codes issued before the deploy (5-minute lifetime) stop working and the patient asks for a new one.
- Rows the tenancy backfill could not assign stay invisible until assigned. `python manage.py assign_tenant_hospital` reports them and assigns the unambiguous ones (see `DATABASE.md`).
- The project folder is iCloud-synced, which stalls Python/Node; move it before further development.
