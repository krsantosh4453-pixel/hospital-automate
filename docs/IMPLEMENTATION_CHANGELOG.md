# Implementation Changelog

Branch `audit/production-readiness-2026-10-24`, from baseline tag `baseline-before-readiness-audit-2026-10-24` (e58280c). 22 code commits; 151 files changed, +8,517 / −6,497 lines (the large deletion count is mostly hard-coded demo data removed from pages). Roll back by checking out the tag; every new migration reverses.

## Security and tenancy

| Commit | Change |
|---|---|
| e2d7f4d | Fail-closed hospital scoping by each model's owning-hospital path (25 endpoints leaked across hospitals); hospital columns + backfill migrations; per-hospital membership roles; `record_audit` and automatic write auditing; 67-model isolation test |
| 1299a51 | Staff OTP bound to a signed challenge from the password step; lockout; OTP password reset revoking refresh tokens; unprotected `/api/auth/token/` removed; production compose and Celery app fixed |
| bd66f90 | Patient documents private and hospital-scoped with content sniffing and audited downloads; nginx `/media/` denied; CORS reflection removed; per-location proxying |
| 52ec7d8 | Staff administration API: approve, change role, remove access, own hospital only |
| 08301e9 | gunicorn, cryptography, pytest, vite upgraded (pip-audit / npm audit clean); `requirements-lock.txt` |
| fd3ff71 | `.env.example` tracked with placeholders and current settings |

## Clinical safety

| Commit | Change |
|---|---|
| 7044390 | AI scribe: mock providers only when explicitly allowed (never production); 503 without a provider; drafts labelled "AI Draft — Pending Review"; workflow fields read-only; approval only by a linked doctor; consent before recording; schema coercion; broken imports fixed |
| 0de1e42 | OPD queue-token 500 fixed; lab sample/result workflow and roles; patients see only released results; discharge requires a finalized, immutable summary |
| 4fe06b9 | MAR: doses were recorded as already given; now Scheduled → Administered / Held / Refused / Missed / Vomited / Excluded with who and when, no double dosing, PRN |
| cd2ce85 | Prescriptions saved and dispensed only after server confirmation (no local-only success) |
| 7178cf4 | Consent forms and patient-controlled record sharing with access log and revocation |

## Financial integrity

| Commit | Change |
|---|---|
| 9bcd125 | Server-side Decimal billing; locked, idempotent, append-only payments; refunds; discount and overpay limits; ledgered pharmacy stock, catalogue prices, expired-batch block |
| d9010df | Invoice list 99 → 9 queries; billing page uses append-only payments with idempotency keys |
| dc69688 | Billing KPI figures corrected; Reports page on server KPIs |

## Frontend: real data instead of mocks

| Commit | Change |
|---|---|
| aa1be1f | Hospitals from the API everywhere; patient consent and sharing UI |
| 383a297 | Frontend/backend API contract mismatches fixed; contract test |
| a544eac | Nurses and Laboratory pages on the API; demo fallbacks removed |
| c37552f | Admin Users / Departments / Roles on real data (Department code and head) |
| 094683b | Hindi/English switch |
| 199310c | Five page crashes found by browsing the built app; analytics SQL portable; stricter lint (`no-undef`, `no-use-before-define`) |
| 80ee2b5 | Patient portal selects the patient's hospital; real API error messages |

## Operations

| Commit | Change |
|---|---|
| dfe1e82 | `scripts/backup.py` fixed and verified (create → verify → restore on PostgreSQL 16); API docs generator |

## Documentation (this commit)

New: `REQUIREMENTS_TRACEABILITY`, `INITIAL_AUDIT_REPORT`, `API_DOCUMENTATION`, `DATABASE`, `SECURITY_AUDIT`, `TEST_REPORT`, `OPERATIONS_RUNBOOK`, `KNOWN_LIMITATIONS`, `IMPLEMENTATION_CHANGELOG`, `FINAL_PRODUCTION_READINESS_REPORT`. Rewritten: `ARCHITECTURE`, `DEPLOYMENT` (the deployment guide). Corrected: `ROLLBACK_STRATEGY`, `DISASTER_RECOVERY`, README. Older root-level reports are marked superseded.
