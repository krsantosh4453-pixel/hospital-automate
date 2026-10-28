# Known Limitations

State as of 2026-10-25, branch `audit/production-readiness-2026-10-24`. Row ids refer to `REQUIREMENTS_TRACEABILITY.md`. Nothing here is presented in the UI as working.

## Release blockers (must be resolved before real patient use)

| # | Limitation | Why it blocks | Action |
|---|---|---|---|
| L1 | The Docker Compose stack and nginx were never started (no Docker on the audit machine) | Production routing, TLS, `/media/` denial and container health are unverified at runtime | Full staging rehearsal of `DEPLOYMENT.md` steps 1–8 |
| L2 | Twilio Verify, SMS/WhatsApp, email, STT/LLM providers and Google sign-in were never exercised with real credentials | Production settings require OTP; staff can't sign in if Verify fails; AI scribe answers 503 without a provider | Configure staging credentials and run the sign-in, OTP, AI-draft and notification flows end to end |
| L3 | Access and refresh tokens are in `localStorage` | One XSS exposes sessions to patient data | Move to httpOnly cookies + CSRF, or accept the risk formally with a strict CSP |
| L4 | No clinical safety review of the workflows | MAR, discharge, lab release and AI-draft rules were designed by engineering only | Sign-off by a clinical safety officer / pharmacist |
| L5 | No penetration test or DPDP Act privacy assessment | Required for health data in India | Commission both |

## Missing features (18 MISSING rows; B4, D10, D11, G3, H7 added 2026-10-28)

- **Access / portal:** proxy and caregiver access (A12, B13); breadcrumbs (A18); sticky patient context strip (A19).
- **EMR:** extra vitals set (D2); ICD-10 terminology search (D6); vaccination (D15).
- **Pharmacy:** OPD/IPD returns (F5); **drug-interaction and contraindication alerts (F7)** — there is no drug database, so no alerting exists; substitutes (F8).
- **Billing:** advance payments (H4).
- **Supply chain:** purchase requisition approval (I2); supplier return, department issue, consignment, quotation (I4); CSSD / laundry (I6).
- **Other services:** ambulance, mortuary, phlebotomy, OT (J5); HR, feedback, templates (J6).
- **AI / notifications:** discharge-summary AI assist (K6); voice-call fallback workflow (K8).

## Partial features (23 PARTIAL rows, main ones)

- Hindi covers navigation, the patient menu and the AI label; page bodies are English (A17).
- No combined longitudinal record/timeline (B9, D12); clinical notes are free text without structured sections (D4).
- Radiology is a lab test type (G4).
- Notifications: in-app works; SMS/WhatsApp need consent and credentials (K7).

## Blocked (3) and not applicable (1)

- Hindi/Hinglish speech recognition depends on the STT provider chosen (K5).
- ABDM/ABHA (K10) and FHIR/HL7 (K11): code exists but routes are not mounted. They need sandbox credentials, certification and a security review.
- ML/DL forecasting (K9) is deliberately not built: there is no labelled data or validation. Queue estimates are rule-based.

## Technical limitations

- Notifications are sent synchronously in the request (errors are caught); no Celery retry task yet.
- No row-level concurrency test under real parallel load (locks are in place; SQLite serialises writes).
- No frontend unit or E2E test harness; the frontend was verified by a manual browser pass plus the API contract test.
- Main JS bundle is 836 kB (no code-splitting); lint has 124 warnings (0 errors).
- No sensitive-read auditing for list endpoints; no break-glass emergency access.
- `backend/db.sqlite3` remains in git history.
- Rows that the tenancy backfill could not assign to a hospital stay invisible until assigned (see `DATABASE.md`).
- The project folder is iCloud-synced, which stalls Python/Node; move it before further development.
