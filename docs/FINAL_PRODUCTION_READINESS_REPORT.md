# Final Production-Readiness Report

> **Superseded (2026-10-25, evening):** see `PRODUCTION_READINESS_AUDIT.md` and `DEFECT_REGISTER.md`. A second audit found and fixed further Critical and High defects that this report did not list.

Date: 2026-10-25 · Branch `audit/production-readiness-2026-10-24` · Baseline `baseline-before-readiness-audit-2026-10-24` (e58280c)

## Verdict

**CONDITIONALLY_READY_AFTER_LISTED_ACTIONS**

This applies only to the **defined pilot scope** below, and only after the five actions in "Conditions" are completed. The system is **not** ready against the full requirement set: 43% of requirement rows are partial, missing or blocked.

Why not PRODUCTION_READY_FOR_DEFINED_SCOPE: the production runtime (Docker, nginx, TLS) and the external providers that production settings depend on (Twilio Verify for staff sign-in) were never run, and one High security item (tokens in `localStorage`) is open.

Why not NOT_PRODUCTION_READY: no known critical security issue, unsafe clinical workflow, data-integrity defect or failing test remains in the pilot scope. All 13 baseline P0 findings are fixed with tests.

## Executive summary

At baseline the application was not safe to use with patient data:

- 25 endpoints returned other hospitals' records.
- The staff OTP could be completed with a bare user id.
- AI mock providers wrote invented clinical text and drafts could be approved via PATCH.
- Patient documents were publicly served.
- Money fields were client-writable.
- MAR recorded scheduled doses as already given.
- Many pages showed hard-coded demo data as if real.

22 commits fixed these issues and added 61 security / workflow tests. The suite has 217 tests, passing on SQLite and PostgreSQL 16. The frontend now reads real data; a browser pass covered all 33 routes.

## Defined pilot scope

Single-server deployment for one or a few hospitals, covering:

- staff sign-in with OTP;
- patient registration and portal (own records, consent, record sharing);
- appointments and OPD queue;
- consultation (vitals, diagnosis, notes, prescriptions);
- lab orders through result release;
- pharmacy sale and dispensing with a stock ledger;
- IPD admission, bed, nursing notes, MAR and discharge with a finalized summary;
- invoices, payments and refunds;
- AI scribe drafts with clinician approval (when a real provider is configured);
- in-app notifications;
- audit trail;
- KPI reports.

Excluded: everything listed as MISSING / BLOCKED in `KNOWN_LIMITATIONS.md`, notably drug-interaction alerting, ABDM, FHIR/HL7, voice calls, CSSD, OT and HR. Staff must be told these do not exist.

## Conditions (must all be completed)

1. **Staging rehearsal** of `DEPLOYMENT.md` steps 1–8 on Docker. Confirm TLS, `/media/` → 404, `/health/ready/` and `check --deploy`.
2. **Real credentials in staging.** Run Twilio Verify staff sign-in, email, the chosen STT/LLM provider (AI draft → approval) and Google sign-in end to end. Choose and test SMS/WhatsApp, or keep notifications in-app only.
3. **Session tokens.** Move to httpOnly cookies with CSRF, or have the security owner formally accept the risk with a tightened CSP (no `'unsafe-inline'` scripts).
4. **Clinical safety sign-off** of the MAR, discharge, lab-release and AI-draft rules by a clinician / pharmacist. This includes written acknowledgement that there is no drug-interaction checking.
5. **Penetration test and DPDP privacy assessment.** Also purge `backend/db.sqlite3` from git history if the repository will be shared.

## Coverage (from `REQUIREMENTS_TRACEABILITY.md`, 116 rows, counted by script)

| Status | Rows | % of 116 |
|---|---|---|
| VERIFIED (tested or browser-checked) | 42 | 36.2% |
| IMPLEMENTED (code reviewed, not separately tested) | 24 | 20.7% |
| PARTIAL | 23 | 19.8% |
| MISSING | 23 | 19.8% |
| BLOCKED | 3 | 2.6% |
| N/A (deliberately not built) | 1 | 0.9% |
| PLACEHOLDER / BROKEN | 0 | 0% |

Formulas:

- **Verified coverage** = VERIFIED / total = 42 / 116 = **36.2%**
- **Functional coverage** = (VERIFIED + IMPLEMENTED) / total = 66 / 116 = **56.9%**
- **Functional coverage excluding N/A** = 66 / 115 = **57.4%**
- **Weighted coverage** (PARTIAL counted as half) = (66 + 0.5 × 23) / 116 = 77.5 / 116 = **66.8%**
- **Mock / fake behaviour remaining** = (PLACEHOLDER + BROKEN) / total = 0 / 116 = **0%**

## Module-by-module

Functional coverage = (V + I) / rows.

| Area | Rows | V | I | P | M | B / NA | Functional coverage | Assessment |
|---|---|---|---|---|---|---|---|---|
| A. Platform and access | 21 | 9 | 4 | 5 | 3 | – | 61.9% | Tenancy, roles, auth and audit verified. UI gaps: breadcrumbs, context strip, audit viewer |
| B. Registration and portal | 15 | 5 | 3 | 5 | 2 | – | 53.3% | Registration, portal, consent and sharing work. Missing proxy access and emergency contact |
| C. Appointments / OPD | 8 | 3 | 4 | 1 | 0 | – | 87.5% | Queue-token 500 fixed; flow tested |
| D. Consultation / EMR | 15 | 4 | 3 | 3 | 5 | – | 46.7% | Core notes / diagnosis / prescriptions work. No ICD-10 search, structured EMR, certificates, referral or vaccination |
| E. Nursing / IPD | 12 | 5 | 4 | 3 | 0 | – | 75.0% | MAR and discharge fixed and tested; discharge checklist and billing link partial |
| F. Pharmacy | 8 | 4 | 0 | 1 | 3 | – | 50.0% | Ledgered stock, expiry block. **No interaction alerts**, returns or substitutes |
| G. Lab / radiology | 5 | 2 | 0 | 2 | 1 | – | 40.0% | Workflow and release rules tested; no printing; radiology minimal |
| H. Billing | 8 | 4 | 1 | 1 | 2 | – | 62.5% | Financial integrity tested; no advance payments or invoice PDF |
| I. Supply chain | 6 | 1 | 2 | 0 | 3 | – | 50.0% | Procurement basics; requisition, returns and CSSD missing |
| J. Emergency / other | 7 | 1 | 3 | 1 | 2 | – | 57.1% | About half of ER actions; ambulance, OT and HR missing |
| K. AI / notifications / ML | 11 | 4 | 0 | 1 | 2 | 3 B, 1 NA | 36.4% | AI safety verified with mocks; real providers, ABDM and FHIR blocked |
| **Total** | **116** | **42** | **24** | **23** | **23** | **3 B, 1 NA** | **56.9%** | |

## Code changes

See `IMPLEMENTATION_CHANGELOG.md`: 22 commits, 151 files, +8,517 / −6,497 lines, 17 new migrations (all reversible).

## Test results (`TEST_REPORT.md`)

| Check | Result |
|---|---|
| Backend tests | 217 run, 216 pass, 1 skipped (pre-existing), on SQLite and PostgreSQL 16 |
| End-to-end scenarios 1–14 | 14 / 14 pass. Scenario 14 is partial for notifications: no injected provider exception |
| Migrations (PostgreSQL 16) | 114 apply; the 17 new ones reverse and re-apply |
| Backup create → verify → restore | Identical row counts; wrong key rejected |
| Frontend build / lint | Build passes; lint 0 errors, 124 warnings |
| Dependency audits | pip-audit and npm audit clean |
| Browser pass | 25 staff + 8 patient routes render without errors; five crashes found and fixed |

## Deployment readiness

| Item | Status |
|---|---|
| Production settings fail closed on missing secrets | Verified by review and startup checks |
| Compose file and migrate-once design | Parsed and reviewed; **not run** |
| nginx (TLS, rate limits, private media) | Reviewed; **not run** |
| Health checks | Verified (200, database and cache) |
| Backups | Verified on PostgreSQL 16, run from the host |
| Rollback | Baseline tag; reversible migrations |
| Runbook | `OPERATIONS_RUNBOOK.md` |

## Outstanding issues

Full list in `KNOWN_LIMITATIONS.md` and `SECURITY_AUDIT.md` (open items). The highest:

- **High:** tokens in `localStorage`.
- **High:** `db.sqlite3` in git history.
- **Medium:** self-registered Admin via invite code.
- **Medium:** no read-auditing of list endpoints.
- **Medium:** no break-glass access.
- **Medium:** synchronous notifications.
- **Low / quality:** no frontend test harness; 836 kB bundle.

## Evidence index

`REQUIREMENTS_TRACEABILITY.md` · `INITIAL_AUDIT_REPORT.md` · `SECURITY_AUDIT.md` · `TEST_REPORT.md` · `ARCHITECTURE.md` · `DATABASE.md` · `API_DOCUMENTATION.md` · `DEPLOYMENT.md` · `OPERATIONS_RUNBOOK.md` · `KNOWN_LIMITATIONS.md` · `IMPLEMENTATION_CHANGELOG.md`
