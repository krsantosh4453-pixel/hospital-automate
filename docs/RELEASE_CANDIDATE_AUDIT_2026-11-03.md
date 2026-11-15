# Final Release Candidate Audit — 2026-11-03

Revision audited: branch `ui/redesign-2026-10-25` at `120ca19` (in sync with `origin`, PR #6 open and mergeable). Read-only audit: no application code, migrations, pushes, merges or deletions. Synthetic data only; the production-stack rehearsal used a clean `git archive HEAD` with generated secrets and fake provider placeholders.

## A. Executive summary

Engineering is in good shape: every automated check passes on the current code, locally and in GitHub CI, and the production Docker stack builds from a clean checkout, starts healthy and survives a dump/restore drill. What stands between this and real patients is non-engineering: staging infrastructure, real SMS/OTP/email/AI providers, clinical sign-off, a pentest and a DPDP assessment.

Repository: clean tree, 0 ahead / 0 behind `origin`. Untracked: `.claude/`, `.ua/`, `backend/patients/tests 2.py`, `docs/POST_AUDIT_RECONCILIATION_2026-11-03.md`, `reports/database-view.html`. `master` has 5 merge commits not on this branch; PR #6 is mergeable. Unmerged branch with useful work: `claude/intelligent-keller-502e5b` (D6, K6, K8). One old stash and stale `agents/*` worktrees remain.

## B. Release decision

**Staging: CONDITIONAL GO.** Conditions:
1. A staging host with its own domain and a CA certificate.
2. Twilio Verify test credentials, or `STAFF_LOGIN_REQUIRE_OTP=False` on staging only (otherwise staff cannot sign in).
3. Synthetic data only.

**Production: NO-GO.** Missing: clinical sign-off, pentest, DPDP assessment, and providers never exercised with real credentials.

## C. Modules

"Done" means built and tested. No workflow is clinically reviewed or approved: every sign-off line in `CLINICAL_SAFETY_REVIEW_PACK.md` is blank.

| Module | Backend (coverage) | UI | Access / tenant evidence | Status |
|---|---|---|---|---|
| Users / auth | 83% | Yes | role matrix, cookie auth, OTP tests | Done (OTP provider not tested live) |
| Patients | 87% | Yes | care-scope and tenant tests | Done; UHID DB constraint missing |
| Doctors / Appointments / Encounters-Queue | 89% / 90% / 81% | Yes | department queue tests | Done; Queue page reads only the first 50 appointments |
| Nurses / MAR | 79% | Yes (administering) | `test_mar_safety` | Partial: no MAR order screen (E5) |
| Compounder | 84% | Yes | read-only role | Done |
| Pharmacy | 89% | Yes | PostgreSQL race tests | Done; drug alerts await P&T |
| Laboratory | 90% | Yes | order-to-release E2E | Done |
| Hospital admin | 91% | Yes | admin registry tests | Done |
| Clinical | 93% | Yes | `clinical/test_medication_safety.py` (10) | Done; awaiting clinical approval |
| IPD | 83% | Yes | bed race tests | Done |
| Emergency | 76% | Yes | triage E2E | Done |
| Billing | 79% | Yes | `test_financial_integrity` (8) | Done |
| Blood Bank | 76% | Yes | flow test | Done |
| Notifications | 87% | In-app | Celery retry task | Partial: SMS/WhatsApp need credentials |
| Audit / break-glass | 93% | Yes | API, page and E2E tests | Done; awaiting clinical approval |
| Procurement | 85% | Yes | per-hospital role tests | Done |
| AI Scribe | 74% | Yes | `test_ai_scribe_safety` (draft-only) | Blocked: no AI provider |
| Reports | 91% | Yes | `test_read_roles` | Done |
| Consent / Documents | 84% / 80% | Patient portal | `test_read_roles`, `test_consent_sharing` | Done |
| ABDM | 91% | None (only an "ABHA" ID-type option) | off in production | Blocked: ABDM sandbox |
| FHIR | 95% (`interoperability` 54%) | None | Admin-only, off in production | Blocked: conformance review |

## D. Remaining engineering tasks

| Priority | Task | Effort |
|---|---|---|
| P1 | Staff sign-in rate limit keyed only by IP | 0.5 day |
| P1 | CI deploy jobs only `echo` | 1–2 days, once staging exists |
| P1 | `(hospital, uhid)` DB constraint after `report_duplicate_uhids` | 0.5 day |
| P2 | MAR order screen (owner decides who enters orders) | 2–3 days |
| P2 | Queue page reads only the first 50 appointments | 0.5 day |
| P2 | `server_tokens off`, `STORAGES`, 70 lint warnings | 1 day |
| P2 | Tests for FHIR mapping code (54% coverage) | 1–2 days |
| P3 | 14 missing features (A18, A19, D2, D6, F5, F8, H4, I2, I4, I6, J5, J6, K6, K8); D6/K6/K8 exist on an unmerged branch | Weeks |

## E. External dependencies

- **Infrastructure:** staging host, domain, CA certificate, managed PostgreSQL, backup storage.
- **Providers:** Twilio Verify, SMS/WhatsApp (DLT registration in India), SMTP email, Google sign-in client, AI/STT provider, ABDM sandbox.
- **External reviews:** pentest firm, privacy counsel for DPDP.

## F. Approvals required (none obtained)

- **Clinicians:** MAR, laboratory, discharge, AI scribe, pharmacy/blood bank, emergency, break-glass, family access.
- **Pharmacy & Therapeutics:** drug-alert rules and the choice of a licensed drug database.
- **Hindi-speaking clinicians:** review of the Hindi UI.
- **Privacy counsel:** DPDP, including whether Significant Data Fiduciary status applies.
- **Owner:**
  - R-03 delete policy;
  - who enters MAR orders;
  - merging PR #6;
  - merging or retiring the D6/K6/K8 branch;
  - deleting `tests 2.py` and the stale worktrees.

## G. Security findings

No Critical or High findings.

| Severity | Component | Evidence | Impact | Remediation |
|---|---|---|---|---|
| MEDIUM | Clinical record deletion (R-03) | Doctor/Nurse/Receptionist can hard-delete clinical records | Loss of medical evidence | Owner policy: soft delete or admin-only |
| MEDIUM | Staff sign-in rate limit | `config/middleware/ratelimit.py:29`: 5 per minute per IP | A hospital behind one NAT address may lock staff out at shift change | Key by username plus IP, or allow-list the hospital's address |
| MEDIUM | External assurance | No pentest or DPDP assessment | Unknown residual risk | Commission both |
| LOW | UHID uniqueness (R-08) | API refuses duplicates; no DB constraint | Duplicates via other write paths | Run the report, then add the constraint |
| LOW | Version disclosure | `server: nginx/1.31.8` header | Fingerprinting | `server_tokens off` |
| LOW | Static storage (R-09) | `STATICFILES_STORAGE` ignored by Django 6 | None while nginx serves static files | Move to `STORAGES` |
| LOW | npm dev dependencies | 7 moderate (`minimatch`) | Build tooling only; 0 in production deps | Upgrade when convenient |
| INFO | FHIR CapabilityStatement | `fhir/views.py:159` is public when FHIR is enabled | As the FHIR spec requires; off in production | None |

Verified clean:
- **Production startup:** refuses to start without the secret key, allowed hosts, CORS origins, database, Redis, JWT keys or Twilio settings.
- **Cookies:** httpOnly, Secure and SameSite=Strict.
- **Headers over HTTPS on the running stack:** HSTS, CSP, X-Frame-Options DENY, nosniff.
- **Exposure:** API docs return 401; `/media/` is not served directly; open endpoints are sign-in flows only; dev login needs DEBUG and explicit settings.
- **Repository and scans:** no secrets tracked; Bandit (Medium and above) and pip-audit are clean.

## H. Test results (measured 2026-11-03 on the current code)

| Check | Result |
|---|---|
| Django tests | 650 run: 643 passed, 0 failed, 7 skipped (the 7 are the PostgreSQL-only tests below) |
| PostgreSQL 16 row-lock suite (`REQUIRE_ROW_LOCK_TESTS=1`) | 9/9 |
| Backend coverage | 81% (15,187 statements, 2,912 missed) |
| Vitest | 63/63 (14 files) |
| Playwright | 23/23, none flaky |
| ESLint | 0 errors, 70 warnings |
| Production build | OK; main bundle 310.6 kB (89.9 kB gzip) |
| Ruff gate, Bandit `-ll`, pip-audit, `makemigrations --check` | All clean |
| npm audit | 7 moderate (dev tooling only) |
| GitHub CI on `120ca19` | 7 checks green, including Docker build, Trivy and E2E; 2 deploy jobs skipped |
| Local production rehearsal | 7 containers up; HTTP redirects to HTTPS; `/health/ready/` reports database, cache, Redis and Celery healthy; 154 migrations applied, 0 pending; `check --deploy` clean; `pg_dump` → `pg_restore` drill OK |

Historical baseline, for comparison only: 625 tests with 6 skipped (2026-11-02), 53 Vitest tests, 22 Playwright tests.

## I. Staging deployment checklist

1. Provision the host, domain and certificate.
2. Create `.env.production` from the example, with a new secret key, JWT key pair and database/Redis passwords.
3. Add Twilio test credentials, or set `STAFF_LOGIN_REQUIRE_OTP=False` on staging only.
4. Build the images from a clean checkout.
5. Run `up -d` and check `/health/ready/`.
6. Run `check --deploy`.
7. Back up, then restore into a scratch database.
8. Seed synthetic data only.
9. Run the E2E suite against staging.
10. Hand over to the pentest firm.

## J. Rollback and recovery

- **Backup and restore:** documented in `DEPLOYMENT.md` §7 and `DISASTER_RECOVERY.md`. Tested today as a raw dump/restore drill. The `backup.py` script runs from the host by design; it last passed in the morning rehearsal of 2026-11-03.
- **Application rollback:** documented but never tested. `ROLLBACK_STRATEGY.md` describes blue-green and Kubernetes setups that do not exist here.

## K. Final action plan

**Must fix before staging:**
- Staging infrastructure and certificate.
- An OTP decision for staging.
- Merge PR #6, or deploy from its branch.
- Real deploy steps in CI.

**Must fix before production:**
- Clinical and P&T sign-off.
- Pentest and DPDP assessment.
- Real providers tested end to end.
- R-03 delete policy.
- Sign-in rate-limit fix.
- UHID database constraint.
- MAR order screen, or a documented manual process.
- One application-rollback rehearsal.
- Hindi review.

**Can be deferred until after the initial release:**
- The 14 missing features.
- FHIR and ABDM (they stay off).
- Lint warnings, `STORAGES`, `server_tokens`, the npm dev-dependency issues.
- Documentation cleanup.

## L. Evidence and outdated documentation

Evidence for each claim is cited inline above: file paths with lines, test names, and the commands that were run.

Outdated documentation:
- **`README.md`:** status line dated 2026-10-25 and footer dated 2026-10-10. It links to `FINAL_PRODUCTION_READINESS_REPORT.md`, which marks itself as superseded.
- **Deployment and rollback docs:** three overlapping files (`DEPLOYMENT`, `DEPLOYMENT_GUIDE`, `DEPLOYMENT_CHECKLIST`), and `ROLLBACK_STRATEGY.md` describes infrastructure that does not exist.
- **Repository root:** old phase reports such as `CURRENT_PROJECT_STATUS.md` and `PHASE_*`.

The rehearsal folder `~/.cache/hms-rc` (synthetic secrets only) can be deleted.
