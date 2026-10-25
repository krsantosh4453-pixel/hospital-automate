# Test Execution Report

Audit date 2026-10-25 (evening). Revision: branch `ui/redesign-2026-10-25` at `e2900f2`, plus the owner's uncommitted changes, plus this audit's changes (uncommitted). The previous report, `TEST_REPORT.md` (217 tests), describes the earlier audit.

## Environment and method

**Machine.** macOS (Darwin 25.5), Python 3.12.15, Node 26.7.0 locally (CI uses Node 24), PostgreSQL 16 (Homebrew).

**Why a copy was used.**

- The project folder is iCloud-synced and many files are evicted ("dataless"): 13,651 files, including most of `backend_env/`.
- In the project folder, `manage.py check` did not finish in 5 minutes.
- So the code was exported with `git archive HEAD`, the 10 uncommitted files were overlaid, and everything ran in a scratch copy with a fresh virtualenv built from `backend/requirements-lock.txt` and `npm ci`.
- Every source change was made in the project folder and copied to the scratch copy.
- A byte-for-byte comparison of all 35 changed files confirmed the two match before the final run.

**Data and secrets.**

- The local `.env` was **not** used. That is how D-07 was found: the test settings could not load without it.
- Only synthetic data was used.
- Production settings were exercised with synthetic environment values.

## Commands

```bash
# backend (from backend/)
python manage.py check --settings=config.settings.testing
python manage.py makemigrations --check --dry-run --settings=config.settings.testing
python manage.py test --noinput --settings=config.settings.testing
TEST_DATABASE_URL=postgres://hms_test:hms_test@127.0.0.1:55432/hms_test \
  python manage.py test --noinput --settings=config.settings.testing
DJANGO_SETTINGS_MODULE=config.settings.production <synthetic env> python manage.py check --deploy
ruff check backend/ --select E9,F63,F7,F82 --exclude 'backend/*/migrations/*'
pip-audit -r backend/requirements-lock.txt
# frontend (repo root)
npm run lint && npm test && npm run build && npm audit
```

## Test matrix

| Test ID | Area | Test / command | Before | After | Evidence | Next action |
|---|---|---|---|---|---|---|
| T-001 | Backend | `manage.py check` (testing settings) | PASS with `.env`; **FAIL** without (`DJANGO_SECRET_KEY … required`) | PASS | "System check identified no issues" | — |
| T-002 | Backend | `makemigrations --check --dry-run` | PASS | PASS | "No changes detected" | — |
| T-003 | Backend | Full suite, SQLite | 229 run, 228 pass, 1 skipped (only with `.env`); **0 run** without `.env` | **254 run, 253 pass, 0 fail, 1 skipped** | `Ran 254 tests … OK (skipped=1)` | — |
| T-004 | Backend | Full suite, PostgreSQL 16 (throwaway cluster) | NOT RUN (settings had no PostgreSQL option) | **254 run, 253 pass, 1 skipped** | `Ran 254 tests in 8.2s OK` | — |
| T-005 | Security | `check --deploy`, production settings | PASS | PASS | "no issues" | Run again in staging with real values |
| T-006 | Security | Hospital isolation scan (`test_tenant_isolation`, 68 models, list + detail) | PASS | PASS | "LEAKS: none" | — |
| T-007 | Security | List without an acting hospital, mixed roles (D-02) | FAIL (reproduced) | PASS | `RolePerHospitalTests` | R-07: non-viewset endpoints |
| T-008 | Security | Cross-hospital patient delete (D-01) | FAIL (204, B's visit deleted) | PASS | `PatientDeleteTests` | R-03 policy |
| T-009 | Security | Report templates / schedules (D-03) | FAIL ×5 | PASS ×7 | `test_reports_access` | — |
| T-010 | Security | Notification honesty (D-04) | FAIL ×3 | PASS | `ProviderHonestyTests` | R-06 |
| T-011 | Security | Staff OTP bypass via patient login (D-05) and Google (D-06) | FAIL ×2 (patient routes); Google tests already passed | PASS | `test_auth` | — |
| T-012 | Security | Client IP / `X-Forwarded-For` (D-08) | Module absent | PASS | `test_client_ip` | — |
| T-013 | Security | Production CSP header (D-09) | FAIL (no header) | PASS | `test_settings_loading` | R-11 |
| T-014 | API | Frontend paths resolve to backend routes | PASS | PASS | `test_frontend_contract` | — |
| T-015 | API | Frontend HTTP methods accepted by routes (291 calls) | NOT RUN (no test) | PASS; a mutation (POST→DELETE) fails it | `FrontendMethodContractTests` | — |
| T-016 | Static | Ruff correctness rules (E9, F63, F7, F82) | FAIL (2 × F821) | PASS | "All checks passed!" | — |
| T-017 | Static | Ruff full rule set / black / isort (the old CI lint) | FAIL (1,467 findings; 284 files unformatted) | FAIL (1,469, unchanged scope) | Ruff statistics | R-12, not gating |
| T-018 | Frontend | `npm run lint` | PASS (0 errors, 68 warnings) | PASS (0 errors, 68 warnings) | ESLint output | R-12 |
| T-019 | Frontend | `npm test` (Vitest) | NOT RUN (no runner) | **4/4 PASS** (2 files) | Vitest output | Add component tests |
| T-020 | Frontend | `npm run build` | PASS (818 kB JS) | PASS (818 kB JS) | Vite output | R-12 |
| T-021 | Deps | `pip-audit` (lock file) | PASS | PASS | "No known vulnerabilities" | — |
| T-022 | Deps | `npm audit` (incl. Vitest, jsdom) | PASS | PASS | "0 vulnerabilities" | — |
| T-023 | Secrets | Pattern scan of the tree (Twilio, OpenAI, Google, GitHub, Slack keys, private keys) and history for `.env`/keys | PASS (tree) / `db.sqlite3` in history | Same | Masked grep; `git log --diff-filter=A` | R-02 |
| T-024 | CI | Workflow parses; triggers include `master` | FAIL (never triggered) | PASS locally | `yaml.safe_load` | Confirm on GitHub after push |
| T-025 | E2E (manual browser) | 26 staff routes as a synthetic Admin: render, no crash, no uncaught error | NOT RUN after the redesign | PASS (26/26) | Scripted route walk | Automate with Playwright |
| T-026 | E2E (manual browser) | Queue: appointment booked server-side → issue token (D-10) | FAIL (by code) | PASS: "Token #1 generated" | Browser | — |
| T-027 | E2E (manual browser) | AI scribe revisit (D-12) | FAIL: 400 "already exists" | PASS: GET only | Network log | — |
| T-028 | E2E | 8 patient-portal routes | — | **NOT RUN** this round (passed in the earlier audit) | — | Re-run with a patient login |
| T-029 | Infra | Docker image build, Compose stack, nginx/TLS | BLOCKED | BLOCKED | No Docker on this machine | Staging rehearsal |
| T-030 | Integrations | Twilio Verify/SMS, SMTP, STT/LLM, Google sign-in with real credentials | BLOCKED | BLOCKED | No credentials (deliberately not used) | Staging with real credentials |
| T-031 | Ops | Backup → verify → restore | NOT RUN this round | NOT RUN | Passed in the earlier audit (PostgreSQL 16) | Re-run in staging |
| T-032 | Perf | Load / response-time tests | NOT RUN | NOT RUN | No load tool configured; no safe target | Run k6/Locust against staging |
| T-033 | Security | Bandit | NOT RUN | NOT RUN | Report-only in CI; never triaged | Triage once |

**Skipped test.** `nurses.tests` "MAR administration model" is skipped with "Requires Prescription/PrescriptionItem setup". It was skipped before this audit too. MAR safety is covered separately by `security_tests/test_mar_safety.py`.

## Summary by area

Counting method: each backend test method counts once per database run. The SQLite run is the headline; the PostgreSQL run is a repeat of the same 254 tests and is shown separately, not added. Manual browser checks count one per scenario.

| Area | Executed | Passed | Failed | Blocked | Not run |
|---|---:|---:|---:|---:|---:|
| Backend tests (SQLite) | 254 | 253 | 0 | 0 | 1 (skipped) |
| Backend tests (PostgreSQL 16, same tests) | 254 | 253 | 0 | 0 | 1 (skipped) |
| Frontend unit tests | 4 | 4 | 0 | 0 | 0 |
| Static / build / config checks (T-001, 002, 005, 016, 018, 020, 024) | 7 | 7 | 0 | 0 | 0 |
| Style lint (T-017, informational) | 1 | 0 | 1 | 0 | 0 |
| Dependency and secret scans (T-021–023) | 3 | 3 | 0 | 0 | 0 |
| Manual browser scenarios (T-025–027) | 3 | 3 | 0 | 0 | 1 (T-028) |
| Infra / integrations / ops / perf / Bandit (T-029–033) | 0 | 0 | 0 | 2 | 3 |

**New tests in this audit:** 25 backend (254 − 229) and 4 frontend.

| Area | New tests |
|---|---|
| Settings loading | 3 |
| Role-scoped lists | 2 |
| Patient delete | 4 |
| Reports | 7 |
| Notifications | 3 |
| Client IP | 3 |
| Dual-role login | 2 |
| Method contract | 1 |

No existing test was deleted, skipped or weakened, and no existing assertion was changed. One assertion was briefly displaced by an edit and then restored, as the diff shows.

## Update 2026-10-26

**Environment changes:**

- The scratch copy was rebuilt from `git archive` after the session restarted.
- Docker 29.5 runs via Colima (Homebrew).
- The rehearsal ran from `~/hms-rehearsal`, because Colima only shares the home folder with its VM.

| Test ID | Area | Test / command | Result | Evidence |
|---|---|---|---|---|
| T-034 | Backend | Full suite, SQLite | **262 run, 261 pass, 1 skipped** (+8 cookie-session tests) | `Ran 262 tests … OK (skipped=1)` |
| T-035 | Backend | Full suite, PostgreSQL 16 (`postgres:16-alpine` container, `TEST_DATABASE_URL`) | **262 run, 261 pass, 1 skipped** | Same |
| T-036 | Frontend | `npm test` | **8/8 pass** (+4 cookie-session tests) | Vitest |
| T-037 | Frontend | lint / build / `npm audit` | 0 errors (68 warnings) / pass / 0 vulnerabilities | Command output |
| T-038 | Deps | `pip-audit`; Ruff correctness | Clean; pass | Command output |
| T-029 → PASS (local) | Infra | `docker compose -f docker-compose.prod.yml build` + `up` | **PASS after D-19 to D-27**: all 7 containers healthy | `docker compose ps`; container logs |
| T-039 | Infra | Production checks on `https://localhost` | PASS: redirect 301, `/health/ready/` 200 (DB, cache, Redis, Celery), `/media/` 404, anonymous API 401, HSTS/CSP/XFO/nosniff present, static 200, `check --deploy` clean | curl output |
| T-040 | Infra | Upgrade path: recreate backend only, nginx untouched | PASS (200); backend stopped → 504 (was a fake 404) | curl output |
| T-041 | Security | Cookie session over HTTPS through nginx: login → cookies `HttpOnly; Secure`, no tokens in body → me 200 → write without CSRF 403 → with CSRF passes → refresh 200 → logout 200 → me 401 | PASS | curl output |
| T-042 | Security | 40 bad logins with rotating spoofed `X-Forwarded-For` | PASS: 429 after 3 (Django), 503 after the nginx burst | curl output |
| T-043 | E2E (browser) | Dev stack: staff sign-in → no JWT in storage, cookies hidden from JS → reload keeps session → create department 201 → logout → protected page redirects to login | PASS | Browser pane |
| T-030 | Integrations | Real Twilio / SMTP / Google / AI | **BLOCKED**: every Twilio key in `.env` is blank and no SMTP settings exist | `.env` keys inspected (values never printed) |

**Still not run:**

- Backup/restore on the containers.
- Load test.
- Bandit.
- Patient-portal browser pass.
- A rehearsal on a real server with a real domain and CA certificate.
