# Hospital Automate — Post-Audit Reconciliation (2026-11-03)

**Audited revision:** `ui/redesign-2026-10-25` at `b445700`. There are no tracked uncommitted changes, and 4 untracked items: `.claude/`, `.ua/`, `backend/patients/tests 2.py`, `reports/database-view.html`.
**Baseline:** `reports/AUDIT_2026-11-02.md`, which audited `06345cb` plus 49 uncommitted changes.
**Method:** read-only. Sources were git history (log, show, cherry, branches, worktrees, stash), source code, tests, docs, and the local Claude Code transcripts (user messages and closing summaries only). Verification ran in an isolated `git archive` copy with a fresh Python 3.12 venv and `npm ci`, **no `.env`**, synthetic data only, and a throwaway PostgreSQL 16. Nothing in the project, its database, its git index or GitHub was changed.

---

## A. Executive summary

| Measure | Count |
|---|---:|
| Tasks discovered (23 baseline + 14 new) | 37 |
| Completed and verified | 21 |
| Partially completed | 5 |
| Pending, not started (engineering) | 8 |
| Blocked by an external dependency | 4 (staging, providers, pentest, DPDP) |
| Awaiting owner approval / decision | 5 (push, D6/K6/K8 branch, `tests 2.py`, R-03 policy, MAR order owner) |
| Awaiting clinical approval | 2 (safety sign-off, F7 rules) |
| Could not be verified this pass | 2 (Docker image build/run; CI on the 16 unpushed commits) |

**Maturity:** the software is feature-broad and its tests are green: 625 backend, 53 unit, 22 E2E, and the row-lock suite on PostgreSQL. Every engineering item from the original P0–P3 list that doesn't need outside parties is done. It is **still not ready for real patients**. The remaining blockers are external: staging deployment, real provider credentials, clinical sign-off, pentest and DPDP. Two process risks are new:

1. **16 commits are not pushed.** They include P2, the new E2E, P3, Hindi and the ER visit-number fix. PR #6's green CI covers only `521da12`.
2. **An abandoned branch** (`claude/intelligent-keller-502e5b`, 10-28) holds unmerged ICD-10 search (D6), AI discharge drafts (K6) and voice-call fallback (K8). The docs list all three as MISSING.

---

## B. Chronological timeline (after the audit baseline)

The 11-02 commits `8a9f520` (D4 structured notes), `152426e` (Hindi via UI components) and `06345cb` (sign-in dialog) were inside the audited baseline.

| Date (IST) | Task | Module | Changes made | Commit | Verification |
|---|---|---|---|---|---|
| 11-03 07:49 | P0-3 PG row locks + CI guard | IPD | Admission/bed locks; `REQUIRE_ROW_LOCK_TESTS=1` in CI | `009758d` | 7/7 on PG16 (this pass) |
| 11-03 07:50 | P0-4 Break-glass + read audit committed | Audit | `break_glass.py`, `read_audit.py`, migration 0004 | `a3f957d` | `test_break_glass.py` |
| 11-03 07:50 | Celery retry task for external channels | Notifications | `send_notification_channel`, 5 retries | `1e76cfa` | `test_async_delivery.py` |
| 11-03 07:50 | Tenant backfill command | Users | `assign_tenant_hospital` | `70a1ba4` | `test_assign_tenant_hospital.py` |
| 11-03 07:50 | Route-level code splitting | Frontend | `lazy()` per route | `afb5c70` | Build 311 kB |
| 11-03 07:50 | P0-4 Proxy/family access (A12, B13) | Portal | `ProxyAccess`, proxy login, Family Access card | `747e5a2` | `test_proxy_access.py`, E2E `family-access` (2) |
| 11-03 07:51 | Quick wins F-2, F-4, F-5, F-9 | Reports, AI scribe, viewsets | Lab revenue `null`, temp dir, ordering ×10, FHIR dup key | `7aebdd9` | `test_financial_report.py` |
| 11-03 07:51 | F-6 drop axios; pin cryptography | Deps | package.json, requirements | `2ab16f1` | npm audit 0 high |
| 11-03 07:51 | P0-1 Docker/nginx/TLS rehearsal fixes | Deploy, CI | Linux file-case bug, docs 500, duplicate headers, nginx 429; CI E2E + compose jobs | `1fade2d` | Local rehearsal (earlier session); compose valid (this pass) |
| 11-03 07:53 | P0-5 Review packs | Docs | Safety, pentest, DPDP packs | `0fd89a0` | Docs only, **not signed** |
| 11-03 08:20 | P1 Procurement UI (F-1) | Inventory | Suppliers, POs, receive, reorder level/unit/supplier | `9d58c25` | `test_stock_settings.py`, E2E `procurement` (2) |
| 11-03 08:25 | P1 Permissions page truthful (F-3) | Admin | Read-only matrix of built-in roles | `e367eae` | `permissionsPage.test.jsx` (3) |
| 11-03 08:42 | P1 Drug alerts Phase A (F7) | Clinical, Pharmacy | Salt field; allergy/duplicate/8-interaction check; audited override | `20ad09e`, `7017087` | `test_medication_safety.py`, E2E (3); rules **not P&T-approved** |
| 11-03 08:44 | PR #6 opened; bot fix | CI | Per-run CI DB password | `521da12` | GitHub CI green on `521da12` |
| 11-03 09:38 | P2 Dead code (F-8) | Backend | `hl7/`, `ai_advanced/` + unused modules removed (−1,418 lines) | `f4de91a` | Full suite |
| 11-03 09:38 | P2 Reports/forecast bugs | Reports | 400 on bad input, >7-day crash, daily totals | `441d596` | 15 new tests |
| 11-03 09:38 | P2 Rate limit + health leak | Config | Longest-prefix rules, shared budget; generic readiness error | `c31ab33` | `test_ratelimit.py`, `test_health.py` |
| 11-03 10:09 | Bug: only one ER visit could ever be registered | Emergency | `ER-<id>` numbering + migration 0005 | `ce32e8f` | `test_visit_numbers.py`, E2E |
| 11-03 10:09 | Bug: pharmacy couldn't find prescriptions | Pharmacy | Server fetch of RX | `3203fc1` | E2E `pharmacy` |
| 11-03 10:09 | P2 E2E lab/pharmacy/ER/MAR | E2E | 4 specs | `c99d0d6` | Passed (this pass) |
| 11-03 10:27 | Hindi part 1 (A17) | Frontend | Shell, home, clinical pages | `67f93d5` | Vitest, E2E |
| 11-03 12:47 | P3 whole-RX dispense, lab lookup, Add Medicine dialog | Pharmacy, Patients, Lab | `dispense-prescription/`, `patients/lookup/`, Modal | `bc0574c`, `bca354e` | 11 + 9 backend tests, 5 unit, E2E |
| 11-03 12:49 | Bug: Reports page crashed with any lab order | Reports UI | Removed price-less Amount column | `fa145d8` | E2E run |
| 11-03 12:49 | Hindi part 2 | Frontend | Admin, portal, sign-in, statuses, toasts | `426adda`, `e44d157` | Vitest |
| 11-03 14:11 | Hindi part 3 | Frontend | Lab, Pharmacy, dropdowns, list labels | `2bfe30b`, `b445700` | Vitest 53/53 |

**Push state:** `origin/ui/redesign-2026-10-25` = PR #6 head `521da12`. **The 16 commits from `f4de91a` onward are local only.**

### Requests found in session transcripts (2026-11-02 / 11-03)

| Session | User request (paraphrased) | Outcome |
|---|---|---|
| `224c42e9` | Open login on the same page, not a new page | Done (`06345cb`, baseline) |
| `6d16af31` | "Build K7 now" | K7 still **PARTIAL**: in-app only; SMS/WhatsApp need credentials |
| `a2a016b0` | Master audit → fix quick wins → order querysets → P0 list → verify in browser → start P1 → "suggest options" → option 1 (Phase A drug alerts) → Create PR → Auto-fix | Done; PR #6 open |
| `55276c96` | "Work on P3" (became P2 + E2E), "Commit, then E2E", Hindi parts 2 and 3 | Done, committed, **not pushed** |
| `c5d5055a` | "Work on P3" → commit | Done (`bc0574c`) |
| `d9e1ad00` | Commit the §10 quick wins | Nothing to commit (already in `7aebdd9`/`2ab16f1`) |
| `intelligent-keller` worktree (10-28) | D6, K6, K8, proxy access | **Never merged** (G-2) |

Limitation: summarizer sessions were skipped. Button replies ("1", "Yes, part 3") were interpreted from the surrounding assistant text.

---

## C. Completed tasks (with evidence)

| ID | Task | Implementation | Backend tests | Frontend tests | E2E | Commit | Status |
|---|---|---|---|---|---|---|---|
| P0-3 | PG concurrency + CI | Row locks; CI fails if skipped | `test_concurrency.py` 7/7 on PG16 | — | `ipd-bed` | `009758d` | COMPLETED AND VERIFIED |
| P0-4 | Commit proxy/break-glass/audit WIP | 9 commits | proxy, break-glass suites | — | `family-access` (2) | `009758d`…`1fade2d` | COMPLETED AND VERIFIED |
| P1-8 | Procurement UI | Supplier/PO/GRN screens, real reorder levels | `test_stock_settings` | — | `procurement` (2) | `9d58c25` | COMPLETED AND VERIFIED |
| P1-9 | Permissions page | Truthful read-only built-in roles | — | 3 | — | `e367eae` | COMPLETED AND VERIFIED (not customisable, by choice) |
| P1-10 | Lab revenue | `laboratory_revenue: null` | yes | — | — | `7aebdd9` | COMPLETED AND VERIFIED |
| P2-12 | Swagger/ReDoc gating | `ApiDocsAccess`; prod default off | `test_api_docs.py` | — | — | `1fade2d` | COMPLETED AND VERIFIED (not on staging) |
| P2-14 | Remove HL7 + ai_advanced | Deleted | full suite | — | — | `f4de91a` | COMPLETED AND VERIFIED |
| P2-15 | Backend coverage | ~240 tests added since audit | 625 OK | — | — | several | COMPLETED (81% non-test source) |
| P2-16 | Reports/forecasting | 4 bugs + UI crash fixed | 15 | — | — | `441d596`, `fa145d8` | COMPLETED AND VERIFIED |
| P2-17 | Health disclosure | Generic `unhealthy` | 5 | — | — | `c31ab33` | COMPLETED AND VERIFIED |
| P2-18 | Rate-limit bugs | Longest prefix, one budget | 7 | — | — | `c31ab33` | COMPLETED AND VERIFIED |
| P2-19 | E2E lab/pharm/ER/MAR | 4 specs + 2 release-blocking bugs fixed | 3 | — | 5 tests | `c99d0d6`, `ce32e8f`, `3203fc1` | COMPLETED AND VERIFIED |
| P3-21 | Atomic multi-medicine dispensing | Conditional UPDATE; 409 on repeat | 11 | 5 | `pharmacy` | `bc0574c` | COMPLETED AND VERIFIED |
| P3-22 | Restricted lab patient lookup | 3+ chars, ≤20 rows, masked phone, audited | 9 | — | `laboratory` | `bc0574c` | COMPLETED AND VERIFIED |
| P3-23 | Add Medicine dialog + labels | Shared Modal, Field labels | — | — | `pharmacy` | `bc0574c` | COMPLETED AND VERIFIED |
| N-1 | Celery notification retries | Retry task | yes | — | — | `1e76cfa` | COMPLETED AND VERIFIED (external channels blocked) |
| N-2 | Tenant backfill command | `assign_tenant_hospital` | yes | — | — | `70a1ba4` | COMPLETED AND VERIFIED |
| N-3 | Route code splitting | `lazy()` | — | — | all | `afb5c70` | COMPLETED AND VERIFIED |
| N-4 | F-4/F-5/F-6/F-9 quick wins | as §B | yes | — | — | `7aebdd9`, `2ab16f1` | COMPLETED AND VERIFIED |
| N-5 | ER visit + RX search bugs | as §B | yes | — | yes | `ce32e8f`, `3203fc1` | COMPLETED AND VERIFIED (**unpushed**) |
| N-6 | CI credentials cleanup (bot review) | Per-run password | — | — | — | `521da12` | COMPLETED AND VERIFIED (GitHub CI green) |

---

## D. Partially completed tasks

| ID | Done | Remaining | Why incomplete | To finish | Files |
|---|---|---|---|---|---|
| P0-1 Docker/nginx/TLS | Local prod-compose rehearsal, self-signed TLS, synthetic secrets; 4 defects fixed; compose files valid | Real staging host, domain, CA cert, OCSP, real secrets; image build not re-run this pass (colima stopped) | Infrastructure | `DEPLOYMENT.md` 1–8 on staging; build from a clean checkout | compose, nginx, Dockerfiles |
| P1-11 Drug alerts (F7) | Phase A: allergy + class, duplicate salt, 8 interactions, server-enforced reason | P&T approval of rules; licensed DB (Phase B); dose-range checks | Clinical approval + vendor decision | P&T sign-off (`CLINICAL_SAFETY_REVIEW_PACK.md` §9); pick a database | `clinical/medication_safety.py`, `safety_rules.py` |
| A17 Hindi | ~1,900 strings; 63 distinct English strings left (names, IDs, abbreviations) | "just now", server audit text, split fragments; native clinical review | Engineering translation | Review by Hindi-speaking clinical staff | `src/assets/i18n/hiPages.js` |
| K7 Notifications | In-app, Celery retries, delivery log | SMS/WhatsApp providers | Credentials (L2) | Twilio Messaging behind consent | `notifications/services/providers.py` |
| P0-5 Safety/pentest/DPDP | Packs prepared | Signatures and engagements | External parties | Commission | `docs/CLINICAL_SAFETY_REVIEW_PACK.md`, `PRIVACY_AND_PENTEST_PACK.md` |

---

## E. Pending tasks

| ID | Task | Status |
|---|---|---|
| P0-1 | Staging deployment with real domain/TLS | BLOCKED BY EXTERNAL DEPENDENCY |
| P0-2 | Twilio Verify, SMS/WhatsApp, email, STT/LLM, Google sign-in | BLOCKED BY EXTERNAL DEPENDENCY (deferred by owner) |
| P0-5 | Clinical safety sign-off | AWAITING CLINICAL APPROVAL |
| P0-6 | External penetration test | BLOCKED BY EXTERNAL DEPENDENCY |
| P0-7 | DPDP privacy assessment | BLOCKED BY EXTERNAL DEPENDENCY |
| NEW-1 | Push the 16 local commits; CI on them; merge PR #6 | AWAITING OWNER APPROVAL |
| NEW-2 | Unmerged D6/K6/K8 branch | AWAITING OWNER APPROVAL |
| P1-11 | F7 rules P&T approval; Phase B drug DB | AWAITING CLINICAL APPROVAL |
| P2-13 | Delete `backend/patients/tests 2.py` | AWAITING OWNER APPROVAL (confirmed stale) |
| E5 | MAR order entry screen | AWAITING OWNER APPROVAL (who enters orders) |
| R-03 | Patient/clinical hard-delete policy | AWAITING OWNER APPROVAL |
| R-15 | Read-role gate on consent/documents/reports/home | NOT STARTED |
| R-16 | Home dashboard lab counts always 0 | NOT STARTED |
| R-08 | Email OTP HMAC; `(hospital, uhid)` uniqueness | NOT STARTED |
| R-10 | Pin Trivy, gate Bandit, Node base image | NOT STARTED |
| R-13 / R-14 | localStorage patient fallback; dev auth bypass default | NOT STARTED |
| G-8 | Break-glass screen | NOT STARTED |
| G-9 / G-10 | Dispense race test on PG; un-skip MAR model test | NOT STARTED |
| G-7 | Docs drift fixes | NOT STARTED |
| — | MISSING features A18, A19, D2, F5, F8, H4, I2, I4, I6, J5, J6 (+ D6, K6, K8 code on unmerged branch) | NOT STARTED |

---

## F. Original audit vs current state

| Original finding | Priority | Current status | Evidence | Remaining work |
|---|---|---|---|---|
| 1 Docker/Nginx/TLS | P0 | PARTIAL (local only) | `1fade2d`; compose valid | Staging |
| 2 External providers | P0 | BLOCKED | No credentials used | Staging creds + end to end |
| 3 PG concurrency + CI | P0 | COMPLETED AND VERIFIED | 7/7 PG16 | Dispense race test |
| 4 Commit proxy/break-glass/audit | P0 | COMPLETED AND VERIFIED | 9 commits; E2E | — |
| 5 Clinical safety review | P0 | AWAITING CLINICAL APPROVAL | Pack updated | Sign-off |
| 6 Pentest | P0 | BLOCKED | Pack ready | Commission |
| 7 DPDP | P0 | BLOCKED | Pack ready | Commission |
| 8 Procurement UI | P1 | COMPLETED AND VERIFIED | `9d58c25` | I2/I4, PO cancel |
| 9 Permissions | P1 | COMPLETED (truthful read-only) | `e367eae` | Custom roles only if wanted |
| 10 Lab revenue | P1 | COMPLETED AND VERIFIED | `7aebdd9` | — |
| 11 Drug alerts | P1 | PARTIALLY IMPLEMENTED | `20ad09e` | P&T, Phase B |
| 12 Swagger/ReDoc | P2 | COMPLETED AND VERIFIED | `ApiDocsAccess` | Confirm on staging |
| 13 `tests 2.py` | P2 | AWAITING OWNER APPROVAL | Still untracked | Delete on OK |
| 14 HL7 / ai_advanced | P2 | COMPLETED AND VERIFIED | Dirs absent | — |
| 15 Coverage | P2 | COMPLETED | 81% | interoperability 54%, config 61% |
| 16 Reports/forecast | P2 | COMPLETED AND VERIFIED | 15 tests | R-16 |
| 17 Health disclosure | P2 | COMPLETED AND VERIFIED | 5 tests | — |
| 18 Rate limiting | P2 | COMPLETED AND VERIFIED | 7 tests | Load test not done |
| 19 E2E lab/pharm/ER/MAR | P2 | COMPLETED AND VERIFIED | 22/22 this pass | — |
| 20 KNOWN_LIMITATIONS | P2 | COMPLETED WITH DRIFT | G-7 | Fix stale lines |
| 21 Multi-medicine dispensing | P3 | COMPLETED AND VERIFIED | tests + E2E | F8 substitution, partial dispense |
| 22 Lab walk-in lookup | P3 | COMPLETED AND VERIFIED | tests + E2E | — |
| 23 Add Medicine dialog | P3 | COMPLETED AND VERIFIED | E2E by label | — |

---

## G. New issues discovered (evidence-backed only)

| ID | Severity | Issue | Evidence |
|---|---|---|---|
| G-1 | HIGH (process) | 16 commits unpushed, including release-blocking fixes (ER numbering, RX search) and all P2/P3/Hindi work. They exist only on an iCloud-synced disk, and CI has never run on them. | `git rev-list origin/ui/redesign-2026-10-25..HEAD` = 16; PR #6 head `521da12` |
| G-2 | MEDIUM | Unmerged `claude/intelligent-keller-502e5b` (10-28): D6 ICD-10 search (776 lines, tests), K6 AI discharge drafts (621 lines, inside `ai_advanced`, which `f4de91a` deleted, so it would conflict), K8 voice-call fallback (687 lines, migration 0007), and an alternative proxy implementation (superseded). The docs say D6/K6/K8 are MISSING. | `git cherry -v HEAD claude/intelligent-keller-502e5b` |
| G-3 | MEDIUM | R-15 still open: consent and document views check roles on writes, but their `get_queryset` has no role filter, so any active staff role at the hospital can list them. | `consent/views.py`, `documents/views.py` (code read; not re-tested) |
| G-4 | LOW | R-16 still open: home dashboard lab counts filter on `Pending`/`Completed`, which aren't `LabTest` statuses, so they're always 0. | `home/views.py:107-108` vs `laboratory/models.py:11-20` |
| G-5 | LOW | R-08 still open: email OTP stored as unsalted SHA-256; no `(hospital, uhid)` unique constraint found. | `users/patient_auth.py:154,204,240`; `patients/models.py` |
| G-6 | LOW | R-10 still open: Trivy `@master`, Bandit `\|\| true`, `node:20-alpine` (Node 20 is past end of life). | `ci.yml:215,231`; `Dockerfile.frontend:2` |
| G-7 | INFO | Docs drift: (a) traceability summary says MISSING 23 / PARTIAL 23, rows and KNOWN_LIMITATIONS say about 16 MISSING; (b) K10/K11 say "routes not mounted" (they're mounted, flag-gated); (c) KNOWN_LIMITATIONS says `db.sqlite3` is still in git history, but remote history is clean (R-02 done) and only old local `agents/*` branches hold it; (d) DEFECT_REGISTER still lists R-05, R-06, R-11, R-12 as open though they're done or mostly done; (e) doc headers name the old branch. | file reads; `git log --remotes -- backend/db.sqlite3` is empty |
| G-8 | LOW | Break-glass is API-only. MAR orders can't be created in the UI (`nurses/mar` create is in `api.js` but no page calls it). | grep of `src/` |
| G-9 | LOW | No PostgreSQL race test for `dispense-prescription`. It's guarded by a conditional UPDATE plus a dispensed flag, but that's untested under real parallel load. | `pharmacy/views.py:151-159,262` |
| G-10 | LOW | MAR model test permanently skipped. | `nurses/tests.py:168` |
| G-11 | LOW | R-14: `.env.example` has `VITE_DEV_AUTH_BYPASS=true` (dev only). R-13: `PatientContext.jsx` writes patient rows to localStorage. R-09: `STATICFILES_STORAGE` is ignored by Django 6 (nginx mitigates). | file reads |
| G-12 | INFO | npm audit: 7 moderate, dev-only (eslint/minimatch), 0 high. pip-audit: 0. | this pass |
| G-13 | INFO | Housekeeping: 9 stale `agents/*` worktrees, `stash@{0}` on master; master is 5 merge commits ahead (merges cleanly). | `git worktree list`, `git stash list` |

---

## H. Current verification (this pass; scratch copy; no `.env`)

| # | Check | Command | Result | Passed | Failed | Skipped | Blocked / reason |
|---|---|---|---|---:|---:|---:|---|
| 1 | Django system check | `manage.py check` | No issues | ✓ | 0 | — | — |
| 2 | Django tests | `manage.py test --noinput` | **625 OK** (23 s) | 619 | 0 | 6 | 5 PG-only + 1 MAR model test |
| 3 | Backend coverage | `coverage run manage.py test` (tests, migrations omitted) | **81%** of 15,200 stmts | — | — | — | Earlier "86%" used a different omit set |
| 4 | Vitest | `npm test` | **53/53** (11 files) | 53 | 0 | 0 | — |
| 5 | Playwright | `npx playwright test` | **22/22** (2.2 min) | 22 | 0 | 0 | — |
| 6 | ESLint | `eslint -c eslint.config.cjs .` (scratch venv excluded) | 0 errors, 70 warnings | ✓ | 0 | — | — |
| 7 | Build | `npm run build` | OK; main JS 311.3 kB (90.0 kB gzip) | ✓ | 0 | — | — |
| 8 | Migration drift | `makemigrations --check --dry-run` | No changes | ✓ | 0 | — | — |
| 9 | Ruff gate | `ruff check --select E9,F63,F7,F82` | All passed | ✓ | 0 | — | — |
| 10 | Dependency audit | `pip-audit`; `npm audit` | pip 0; npm 7 moderate dev-only, 0 high | ✓ | — | — | — |
| 11 | Compose validation | `docker compose config -q` (dev; prod as in CI) | Both valid | ✓ | 0 | — | Image build/run BLOCKED: colima not running |
| 12 | PG concurrency | `test security_tests.test_concurrency` on throwaway PG16, `REQUIRE_ROW_LOCK_TESTS=1` | **7/7 OK** | 7 | 0 | 0 | — |
| — | GitHub CI | PR #6 | All green at `521da12` | — | — | — | Not run on the 16 unpushed commits |
| — | External providers | — | Not run | — | — | — | BLOCKED: no credentials |

---

## I. Prioritized remaining roadmap

| Priority | ID | Description | Module | Required changes | Dependencies | Acceptance criteria |
|---|---|---|---|---|---|---|
| P0 | R0-1 | Push, run CI on all commits, merge PR #6 | Git/CI | `git push`; review; merge | Owner OK | 9 CI jobs green on the head |
| P0 | R0-2 | Staging deployment | Deploy | Host, DNS, CA cert, secrets manager | Infrastructure | `DEPLOYMENT.md` 1–8 pass on staging |
| P0 | R0-3 | Providers on staging | Auth, notifications, AI | Twilio Verify/Messaging, SMTP, STT/LLM | Accounts, DLT registration | OTP sign-in, SMS/WhatsApp, AI draft work end to end |
| P0 | R0-4 | Clinical safety sign-off (incl. F7 rules) | Clinical | Reviewer's changes | Safety officer, P&T | Signed pack |
| P0 | R0-5 | Pentest + DPDP | Security/Privacy | Fix findings | Vendor, counsel | No open critical/high |
| P1 | R1-1 | R-15 read-role gating | Backend | Read-role sets per resource | Role matrix | Per-role security tests |
| P1 | R1-2 | MAR order entry (E5) | Nursing | Order form + schedule | Clinical decision | E2E order → dose |
| P1 | R1-3 | Land or retire the D6/K6/K8 branch | Clinical, AI, Notifications | Rebase; re-home K6 | Owner decision | Merged with green tests, or retired and documented |
| P1 | R1-4 | Deletion policy (R-03) | Patients/Clinical | Soft delete / admin-only | Owner policy | Tests |
| P2 | R2-1 | R-16 lab counts | Home | Real statuses | — | Test |
| P2 | R2-2 | R-08 OTP HMAC + UHID uniqueness | Users/Patients | HMAC; constraint | Data check | Tests; migration on a copy |
| P2 | R2-3 | R-10 CI hardening + Node 22 | CI | Pin, gate, bump | — | CI green |
| P2 | R2-4 | Dispense race test; MAR model test | Tests | New tests | PG CI | Pass |
| P2 | R2-5 | Coverage: interoperability, twilio_verify, llm, bloodbank | Tests | Unit tests | — | ≥80% each |
| P2 | R2-6 | Docs truth pass + `tests 2.py` | Docs | Edits | Owner OK | Docs match code |
| P2 | R2-7 | Break-glass screen | Admin | UI over API | Safety review | E2E |
| P3 | R3-1 | MISSING features | Various | Per feature | Product priority | Per feature |
| P3 | R3-2 | Phase B drug DB, dose ranges | Clinical | Integration | Vendor | P&T approved |
| P3 | R3-3 | Hindi native review | Frontend | String fixes | Reviewers | Sign-off |
| P3 | R3-4 | R-13/R-14, 70 lint warnings, repo housekeeping | Frontend/Git | Cleanup | — | Lint 0 warnings |

---

## J. Recommended next 10 tasks

1. **Push and merge PR #6.** *Why:* 16 commits of verified work exist only on one iCloud-synced disk. *Files:* git. *Approach:* push, let CI run, review, merge. *Tests:* the 9 CI jobs. *Done:* CI green on the head, merged. *Needs:* owner OK.
2. **Decide on the D6/K6/K8 branch.** *Why:* about 2,000 tested lines are stranded, and the docs say these features are missing. *Files:* `backend/terminology/`, `notifications/services/voice*.py`, the K6 discharge code. *Approach:* rebase D6 and K8; move K6 out of the deleted `ai_advanced`; drop its proxy commit. *Tests:* its suites, the full suite, E2E. *Done:* merged or retired. *Needs:* owner decision; K6 also needs clinical review.
3. **Staging deployment (L1).** *Why:* the first P0 blocker. *Approach:* build from a clean checkout, real domain and certificate. *Tests:* rehearsal checklist, backup/restore drill. *Done:* staging passes. *Needs:* a host and DNS.
4. **Providers on staging (L2).** *Why:* production staff sign-in requires Twilio Verify. *Files:* `users/twilio_verify.py` (39% covered), `notifications/services/providers.py`, `ai_scribe/services/llm.py` (49%). *Done:* OTP, SMS/WhatsApp and AI drafts work. *Needs:* credentials.
5. **Clinical safety sign-off.** *Why:* MAR, discharge, lab release, AI drafts, F7 rules, break-glass and family access were designed by engineering only. *Done:* signed pack. *Needs:* a clinician and P&T.
6. **Pentest and DPDP assessment.** *Why:* a legal and security prerequisite. *Approach:* run against staging. *Done:* reports issued, criticals and highs fixed. *Needs:* vendor and counsel.
7. **R-15 read-role gating.** *Why:* the remaining Medium access-control defect. *Files:* `consent/`, `documents/`, `reports/`, `home/` views. *Tests:* per-role security tests. *Done:* unauthorised roles are refused. *Needs:* a role matrix.
8. **MAR order entry (E5).** *Why:* the nurse MAR tab is empty without API-created orders. *Tests:* unit and E2E. *Done:* order → schedule → dose works in the UI. *Needs:* a clinical decision on who enters orders.
9. **Small defect sweep: R-16, R-08, G-9, G-10.** *Tests:* red → green for each. *Needs:* a data check before the UHID constraint.
10. **Docs truth pass and housekeeping (G-7, `tests 2.py`, stale worktrees).** *Why:* the docs are meant to be the source of truth. *Done:* counts and statuses match the code. *Needs:* owner OK for deletions.

---

## K. Master checklist

**P0**
- [x] PostgreSQL row-lock suite + CI guard
- [x] Proxy / break-glass / read-audit work committed (+ family-access E2E)
- [~] Docker/nginx/TLS rehearsal (local done; staging pending)
- [!] Provider credentials: Twilio Verify, SMS/WhatsApp, email, STT/LLM, Google
- [!] Clinical safety sign-off
- [!] External penetration test
- [!] DPDP privacy assessment
- [ ] Push the 16 local commits and merge PR #6

**P1**
- [x] Procurement UI
- [x] Permissions page truthful (read-only built-in roles)
- [x] Laboratory revenue reporting
- [~] Drug alerts (Phase A built; P&T approval and Phase B pending)
- [ ] R-15 read-role gating
- [!] MAR order entry screen (needs ownership decision)
- [!] D6 / K6 / K8 unmerged branch decision
- [!] Patient hard-delete policy (R-03)

**P2**
- [x] Swagger/ReDoc gated in production
- [!] Delete `backend/patients/tests 2.py` (awaiting OK)
- [x] HL7 and ai_advanced removed
- [x] Backend coverage raised (81% non-test source)
- [x] Reports and forecasting fixes
- [x] Health endpoint disclosure fixed
- [x] Rate-limiting bugs fixed
- [x] E2E for lab, pharmacy, emergency, nurse MAR
- [~] KNOWN_LIMITATIONS updated (drift remains)
- [ ] R-16 dashboard lab counts
- [ ] R-08 OTP HMAC + UHID uniqueness
- [ ] R-10 CI hardening + Node base image
- [ ] Dispense race test on PG; un-skip MAR model test
- [ ] Break-glass screen

**P3**
- [x] Atomic multi-medicine dispensing
- [x] Restricted lab walk-in lookup
- [x] Add Medicine dialog and labels
- [~] Hindi UI (native clinical review pending)
- [ ] Remaining MISSING features (A18, A19, D2, F5, F8, H4, I2, I4, I6, J5, J6)
- [ ] Phase B drug database, dose-range checks
- [ ] R-13 / R-14 cleanup; 70 lint warnings
