# Known Limitations

State as of 2026-10-25, updated 2026-11-03, branch `audit/production-readiness-2026-10-24`. Row ids refer to `REQUIREMENTS_TRACEABILITY.md`. Nothing here is presented in the UI as working.

## Release blockers (must be resolved before real patient use)

| # | Limitation | Why it blocks | Action |
|---|---|---|---|
| L1 | Partly done 2026-11-03: `docker-compose.prod.yml` was run locally with production settings, a self-signed certificate and synthetic secrets (all 7 containers healthy; TLS, headers, `/media/` denial, rate limits, restart, persistence and a backup/restore drill verified; four defects fixed). Not yet run on a real staging host with its domain, a CA certificate (OCSP stapling) and real provider credentials | Behaviour behind a real domain, certificate and network edge is unverified | Repeat the rehearsal on the staging host (`DEPLOYMENT.md` steps 1–8). Build images from a clean git checkout: one file's case on the Mac disk differed from git and broke the Linux build |
| L2 | Twilio Verify, SMS/WhatsApp, email, STT/LLM providers and Google sign-in were never exercised with real credentials | Production settings require OTP; staff can't sign in if Verify fails; AI scribe answers 503 without a provider | Configure staging credentials and run the sign-in, OTP, AI-draft and notification flows end to end |
| L4 | No clinical safety review of the workflows | MAR, discharge, lab release, AI-draft, break-glass and family-access rules were designed by engineering only | Sign-off by a clinical safety officer / pharmacist using `CLINICAL_SAFETY_REVIEW_PACK.md` (updated 2026-11-03) |
| L5 | No penetration test or DPDP Act privacy assessment | Required for health data in India | Commission both; brief and baseline in `PRIVACY_AND_PENTEST_PACK.md` (updated 2026-11-03) |

## Missing features (16 MISSING rows on 2026-11-03; A12, B13 and D15 are now done)

- **Access / portal:** breadcrumbs (A18); sticky patient context strip (A19).
- **EMR:** extra vitals set (D2); ICD-10 terminology search (D6).
- **Pharmacy:** OPD/IPD returns (F5); substitutes (F8). Drug alerts (F7) are partial: allergy, duplicate-salt and a starter list of 8 interactions, pending Pharmacy & Therapeutics approval; no licensed drug database and no dose-range checks (`CLINICAL_SAFETY_REVIEW_PACK.md` section 9).
- **Billing:** advance payments (H4).
- **Supply chain:** purchase requisition approval (I2); supplier return, department issue, consignment, quotation (I4); CSSD / laundry (I6).
- **Other services:** ambulance, mortuary, phlebotomy, OT (J5); HR, feedback, templates (J6).
- **AI / notifications:** discharge-summary AI assist (K6); voice-call fallback workflow (K8).

## Partial features (23 PARTIAL rows, main ones)

- Hindi (A17, 2026-11-03): the shell, home dashboard, clinical, admin, patient-portal and sign-in pages show their own text in Hindi, as do server status values, toast messages and about 120 sentences with names or numbers (through `t()` `{placeholders}`). Still English: the Laboratory and Pharmacy pages; labels kept in JavaScript arrays (admin quick links, role descriptions, filter options such as "All Status"); plain `<select>` options; a few sentence fragments split around links. Clinical and patient data stay as entered. The translations were written by engineering and need review by Hindi-speaking clinical staff.
- Notifications: in-app works; SMS/WhatsApp need consent and credentials (K7).
- Procurement (2026-11-03): Inventory has Suppliers and Purchase orders tabs (raise an order, receive full or partial goods with invoice number, batch and expiry) and per-item unit, reorder level and usual supplier. Not built: purchase requisition approval (I2), supplier returns, department issue, consignment and quotations (I4), and cancelling a purchase order from the screen.
- Admin → Permissions is a read-only view of the built-in roles (2026-11-03). Roles cannot be customised: changing what a role may do needs a code change to both `RoleContext.jsx` and the backend permission classes.
- MAR orders have no screen (E5, found 2026-11-03): nothing in the UI creates a medication order or its dose schedule (`/api/nurses/mar/` and `generate_schedule/`), so the nurse's MAR tab stays empty unless orders are created through the API. Giving, holding and refusing doses work once an order exists. Needs a decision on who enters the order (prescribing doctor, or nurse transcription with a second check).
- Dispensing a prescription (2026-11-03) issues every medicine in one step, or none if any line fails. The pharmacist picks a stock batch per medicine (earliest-expiring batch with enough stock is pre-selected). The batch must have the prescribed medicine's exact name: brand substitution (F8) and partial dispensing are not supported.
- Lab staff (2026-11-03) find a walk-in patient by searching name, phone or UHID (3+ characters, at most 20 matches, masked phone, every lookup audited); they still cannot browse the patient list or register a new patient.
- The financial report returns `laboratory_revenue: null`: lab tests carry no price, so lab charges appear only as invoice lines inside billing revenue.

## Blocked (3) and not applicable (1)

- Hindi/Hinglish speech recognition depends on the STT provider chosen (K5).
- ABDM/ABHA (K10) and FHIR (K11): routes are mounted at `/api/abdm/` and `/api/fhir/` but are off in production unless `ABDM_ENABLED` / `FHIR_ENABLED` is set. ABDM needs sandbox credentials, certification and a security review. HL7 v2 is still not mounted.
- ML/DL forecasting (K9) is deliberately not built: there is no labelled data or validation. Queue estimates are rule-based.

## Technical limitations

- SMS, WhatsApp and voice delivery are not implemented and need provider credentials. External channels already go through the Celery retry task (`notifications.tasks.send_notification_channel`: 5 retries, exponential backoff, every attempt logged), so adding a provider needs no queue changes.
- Row-lock tests (`security_tests/test_concurrency.py`) run only on PostgreSQL (`TEST_DATABASE_URL`); on SQLite they are skipped. CI runs them on PostgreSQL 16 with `REQUIRE_ROW_LOCK_TESTS=1`, which fails the run instead of skipping. They found and fixed two IPD races: one admission getting several beds, and parallel transfers. A refused transfer no longer releases the patient's current bed.
- Frontend tests: 51 Vitest unit tests plus 22 Playwright E2E tests in `e2e/`, run in CI. Since 2026-11-03 these include lab order to release, pharmacy dispensing, emergency registration and triage, and a nurse giving a MAR dose.
- Route-level code-splitting brings the main JS bundle to 310 kB (89.5 kB gzip). Lint has 70 warnings and 0 errors: unused variables in page files and the context-plus-hook pattern, which only affects dev hot reload.
- API schema / Swagger / ReDoc work again (they returned 500 before 2026-11-03) and are platform-admin only in production (`API_DOCS_PUBLIC`). drf-spectacular reports 241 documentation warnings (mostly missing type hints).
- Django errors are written to `django_errors.log` in the `app_logs` volume, not to container output; log shipping must collect that volume.
- Sensitive reads are audited: every list or detail read of patient data by staff writes `<model>.list` / `<model>.read` with the patient ids. That is one row per request, so plan audit retention (`AUDIT_LOG_RETENTION_DAYS`). Break-glass access (`/api/audit/break-glass/`) is API-only; there is no screen for it yet.
- `backend/db.sqlite3` remains in git history; removing it needs a history rewrite and a force-push, which the owner must decide.
- Rows the tenancy backfill could not assign stay invisible until assigned. `python manage.py assign_tenant_hospital` reports them and assigns the unambiguous ones (see `DATABASE.md`).
- The project folder is iCloud-synced, which stalls Python/Node; move it before further development.
