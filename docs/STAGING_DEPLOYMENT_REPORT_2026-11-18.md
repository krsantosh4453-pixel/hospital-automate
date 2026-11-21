# Production Deployment and Staging Preparation: Implementation Report, 2026-11-18

Baseline: `PRODUCTION_READINESS_AUDIT_2026-11-18.md` (decision CONDITIONALLY READY; blocker L1 = no real-host staging rehearsal).
Revision: branch `ui/redesign-2026-10-25`, HEAD `a108928`, plus the uncommitted changes listed in section B. Nothing was staged, committed, pushed, merged or deployed. Nothing was bought or created in any cloud.

## Status

| Item | Result |
|---|---|
| Engineering fixes to the deployment (section B) | Done, tested |
| Local Docker rehearsal of the full production stack (section C) | **PASSED**, with synthetic secrets, a private test CA and loopback only |
| Real-host staging rehearsal (real domain, CA-signed certificate, real providers) | **NOT DONE: BLOCKED.** No staging server, domain, certificate or provider credentials exist (section E) |
| **Task status** | **NOT COMPLETE.** The completion criterion (a verified real-host deployment) cannot be met until the section E inputs exist. The local rehearsal is not a substitute for it. |

## A. How it was run

- The project folder is iCloud-synced, so everything ran in a `git archive HEAD` copy under `~/.cache/hms-staging-2026-11-18`. Colima shares only `$HOME`. Every changed file was copied in and checked with `cmp`.
- Docker: Colima (4 vCPU, 6 GB), Compose 5.6.1, nginx 1.31.8, PostgreSQL 16-alpine, Redis 7-alpine.
- Secrets: generated in the scratch copy only (`openssl rand`, a throwaway RS256 pair, a Fernet key). The real `.env` was not read or copied.
- TLS: a throwaway "HMS Local Rehearsal CA (synthetic)" signed a 2-day certificate for `hms-staging.example.test` (a reserved `.test` name).
- The user's own PostgreSQL on `127.0.0.1:5432` was left alone. The rehearsal's PostgreSQL and backend published on loopback ports 55440 and 58000 instead, a choice the compose file now allows.
- The user's database files and untracked files were not touched.

## B. Defects found and fixed

"Observed" means it was reproduced on the HEAD image or compose file before the fix. "Config" means it was found by review and fixed in configuration, without a reproduction.

| # | Defect | Evidence before | Fix | Files |
|---|---|---|---|---|
| D1 | Backend health check sends `Host: localhost`, which Django refuses, so the backend is never "healthy" | Observed: `/health/live/` with `Host: localhost:8000` returns **400**; with the real host, 200 | Probe sends the first `ALLOWED_HOSTS` entry | `docker-compose.prod.yml` |
| D2 | JWT keys written on one line with `\n` escapes, as `.env.production.example` told operators to, boot fine, but every sign-in then fails | Observed: `InvalidKeyError: Could not parse the provided public key` when signing a token | Escapes are turned into newlines. Start-up refuses keys that don't load, aren't RSA, or don't match | `config/settings/production.py` |
| D3 | nginx never received `DOMAIN_NAME`: `server_name localhost`, and HTTP redirected to `https://localhost/...` | Observed in the rendered config: nginx `environment: None` | Passed to nginx and required (`:?`) | `docker-compose.prod.yml`, `.env.production.example` |
| D4 | ACME webroot `/var/www/certbot` not mounted, so certificate renewal needed downtime (standalone mode) | Observed in the rendered config | `./certbot` mounted. Rehearsed: a challenge file is served on port 80 | `docker-compose.prod.yml`, `nginx.conf.template` |
| D5 | Missing `POSTGRES_PASSWORD`/`REDIS_PASSWORD` only gave a warning, and Compose started with blank passwords | Observed: `variable is not set. Defaulting to a blank string` | `${VAR:?}`: Compose stops with an error. CI asserts it | `docker-compose.prod.yml`, `.github/workflows/ci.yml` |
| D6 | Web, worker and beat each built their own image, so `build backend` + `up -d` ran different code in each | Observed: three different image IDs after a backend-only rebuild | One image `hms-backend:${HMS_RELEASE}`. Release tags make image rollback possible | `docker-compose.prod.yml` |
| D7 | After a PostgreSQL restart, a reused connection failed its next request | Observed: first `/health/ready/` after a restart = **503** | `CONN_HEALTH_CHECKS: True`. After: 12/12 × 200 | `config/settings/production.py` |
| D8 | Worker and beat started alongside the migrating backend (beat's `DatabaseScheduler` reads tables that migrate creates) | Config: `depends_on` listed only postgres and redis | Both wait for `backend: service_healthy` | `docker-compose.prod.yml` |
| D9 | Redis is also the Celery broker, but used `allkeys-lru`, which can evict queued tasks under memory pressure | Config | `volatile-lru`: only keys with a TTL (cache, sessions, results) are evicted | `docker-compose.prod.yml` |
| D10 | Redis published on host `127.0.0.1:6379` with no consumer. PostgreSQL's fixed `5432` collides with a host PostgreSQL (it did on this Mac) | Config / observed port conflict | Redis unpublished. PostgreSQL and backend host ports configurable, still loopback-only | `docker-compose.prod.yml` |
| D11 | Migrations ran under the 30 s web `statement_timeout`, so an index build on a large table would be killed mid-migration | Config | `DB_STATEMENT_TIMEOUT_MS=0` for `migrate` only. Web keeps 30 s | `entrypoint.sh`, `production.py` |
| D12 | `createsuperuser` ran in all three containers (race; worker/beat before tables exist) | Config | Backend only | `backend/entrypoint.sh` |
| D13 | No Docker log rotation (json-file grows until the disk is full) | Config | 20 MB × 5 on every service | `docker-compose.prod.yml` |
| D14 | Any Host header (bare IP, scanners) reached Django and produced 400s plus error-log noise | Config | Default servers: port 80 returns 444, port 443 refuses the handshake for unknown SNI. Rehearsed | `nginx.conf.template` |
| D15 | Weak secrets accepted: short or `django-insecure` `SECRET_KEY`, `ALLOWED_HOSTS=*`, spaces in `ALLOWED_HOSTS` | Config | Refused or trimmed at start-up | `production.py` |
| D16 | Backups needed host `pg_dump` and Python `cryptography`, skipped media, and had no automated restore verification | Config | `scripts/deploy/backup.sh`: Docker-only, encrypted DB **and** media, `restore-check` drill, non-destructive `restore` into a new DB, same file format as `backend/scripts/backup.py` | new |
| D17 | Small items: deprecated `listen … http2`; PostgreSQL's 10 s stop then SIGKILL; no nginx health check; `.env.production.example` cited a test file that doesn't exist and lacked `DOMAIN_NAME`; `DEPLOYMENT.md` described a two-file setup, host backup tools and "Docker not available" | Config | `http2 on`; stop grace 60 s/40 s; loopback `/nginx-health`; example and docs corrected | several |

No architecture changed. The containers, settings layout, React build, Django apps and Flutter app are as before.

New tests (`backend/security_tests/test_settings_loading.py`, `ProductionSecretValidationTests`, 9 tests):
- non-PEM JWT key refused;
- mismatched public key refused;
- one-line escaped PEMs load;
- short and development secret keys refused;
- `*` host refused;
- hosts trimmed;
- statement timeout default and override;
- reused connections health-checked;
- `DEBUG` and mock AI stay off even when the environment asks for them.

The existing production-settings tests now use a real generated RS256 pair instead of `"x"`.

## C. Test evidence (local Docker rehearsal)

### C1. Automated suites

| Suite | Result |
|---|---|
| Full backend suite in the built image (`config.settings.testing`, SQLite) | **1146 OK, 29 skipped** (1137 at the audit + 9 new) |
| `security_tests` + `config` with the repository files present (includes the Celery-routing test that parses `docker-compose.prod.yml`) | 418 OK, 21 skipped |
| `ruff check backend/ --select E9,F63,F7,F82` (the CI rule set) | All checks passed |
| `docker compose config` with and without required values | Renders correctly. Without the env file it stops: "required variable POSTGRES_PASSWORD is missing a value" |
| `bash -n` on the three new scripts | OK (shellcheck not installed) |

### C2. Stack bring-up (`dc build && dc up -d` on empty volumes)

- Order: postgres and redis healthy, then the backend applied **190 migrations**, then it was healthy, then the worker and beat started. About 65 s.
- Worker and beat logs: `RUN_MIGRATIONS is not true: skipping migrate and collectstatic`, 0 "Applying" lines. Backend: 190.
- `scripts/deploy/verify_host.sh`: **31 PASS, 0 FAIL**. Checked:
  - all services healthy;
  - DEBUG False;
  - mock AI disallowed, with no mock LLM or STT provider registered;
  - SSL redirect, Secure cookies, HSTS, dev login off, no wildcard host;
  - `check --deploy` (0 issues);
  - 0 unapplied migrations;
  - RUN_MIGRATIONS on the backend only;
  - postgres and backend on 127.0.0.1 only, Redis unpublished;
  - Redis returns `NOAUTH` without a password;
  - log rotation;
  - readiness.
- Negative controls: the port check rejects `0.0.0.0:5432`, and Redis without a password returns NOAUTH. With `DEBUG=True` and `AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True` injected into the running backend, it still reports `DEBUG False mock False providers []`.
- `seed_demo` under production settings: refused ("runs only on a development server").

### C3. HTTPS and headers (`verify_public.sh`, LOCAL mode: private CA, 127.0.0.1)

- **26 PASS, 1 FAIL.** The failure is "certificate valid for 14+ more days": the test certificate was made to expire in 2 days, so this shows the check works.
- Certificate chain verified against the rehearsal CA. Without that CA, `curl` refuses it ("self signed certificate in certificate chain"), which is what a browser would do.
- TLS 1.0/1.1 refused.
- `http://…/some/path?x=1` returns 301 to `https://hms-staging.example.test/some/path?x=1`. Before D3 the target host would have been `localhost`.
- HSTS (`max-age=31536000; includeSubDomains; preload`), CSP, `X-Frame-Options: DENY`, `nosniff` and `Referrer-Policy` on `/`, `/api/` and `/health/live/`. `Server: nginx` with no version.
- `/health/ready/` 200; `/media/…` 404; `/api/schema/` 401; bad staff login 400 (not 5xx).
- Unknown Host on port 80: no response. Unknown SNI on 443: `tlsv1 unrecognized name` alert.
- Trusted proxy: 8 bad logins, each with a different forged `X-Forwarded-For`, returned `401 ×5, then 429 ×3`.
- Closed-port checks from outside: **not possible locally**, so the script skips them for a loopback target.

### C4. Backups and restore

- `backup.sh create`: `hms_backup_*.sql.gz.enc` (90 KB) and `hms_media_*.tar.gz.enc`, mode 0600, both verified. No SQL text readable in the file.
- `restore-check`: live and restored both "146 tables, 190 migrations"; 2–4 s; scratch DB dropped.
- `backend/scripts/backup.py verify` accepts the same file. A wrong key fails with `InvalidToken`.
- `restore` into an existing database name: refused.
- Data-loss drill: 193 ICD-10 rows deleted in the live DB. The app was stopped, the backup restored into a new DB, `POSTGRES_DB` switched and the stack restarted. The app ran on the restored DB with 193 rows, **52 s** after the loss. The damaged DB was kept.

### C5. Rollback

- Image rollback: deployed a simulated `r2`, then `HMS_RELEASE=r1 dc up -d --no-build`. Web, worker and beat were back on `r1` and healthy in **19 s**.
- Migration rollback on PostgreSQL 16 with data: every app reversed to its 2026-11-03 state (`bf1d6c1`). **36 migrations unapplied in 63 s, 0 failures**, then re-applied in 10 s, ending with 0 unapplied.
  - Found: reversing `terminology` to zero empties the ICD-10 table. The next backend start reloads it (`load_icd10 --if-empty`; 0, then 193 rows). Documented.
- Migration preview `dc run --rm --no-deps -e RUN_MIGRATIONS=false backend python manage.py migrate --plan` skipped migrate and listed the plan.

### C6. Restart and recovery

| Event | Result |
|---|---|
| PostgreSQL restart | Before D7: 1 × 503. After: 12/12 × 200 |
| Redis restart | 6/6 × 200 |
| Gunicorn master terminated | restart count 1, healthy again in 7 s |
| `dc down` + `dc up -d` | user row and media file intact |
| Upgrade path (`up -d` with a new image) | "No migrations to apply", healthy |
| Host reboot (Colima VM restart) | VM back in 30 s, all 7 services healthy 61 s after the restart, no manual step |

`nginx -t` on the final config shows one warning: `ssl_stapling ignored, no OCSP responder URL` (the test CA has no OCSP; Let's Encrypt has none either). Harmless.

## D. Deliverables

| Deliverable | Where |
|---|---|
| Implementation report and test evidence | this file |
| Staging deployment configuration | `docker-compose.prod.yml`, `nginx.conf.template`, `.env.production.example`, `backend/entrypoint.sh`, `backend/config/settings/production.py` |
| Deployment procedure, staging checklist (§14), environment variable checklist (§15), rollback (§9), restore and recovery (§13) | `docs/STAGING_DEPLOYMENT.md` |
| Ops scripts | `scripts/deploy/backup.sh`, `scripts/deploy/verify_host.sh`, `scripts/deploy/verify_public.sh` |
| Updated summaries | `docs/DEPLOYMENT.md`, `docs/DEPLOYMENT_CHECKLIST.md`, `docs/ROLLBACK_STRATEGY.md` (header) |
| CI | compose validation passes `DOMAIN_NAME` and asserts a blank `REDIS_PASSWORD` is refused |

## E. Remaining blockers (none can be done by engineering alone)

1. **Real staging host:** a server, a staging host name with DNS, and a CA-signed certificate. Nothing was invented or bought. Until they exist, these remain unverified:
   - certificate issuance and renewal;
   - the HTTPS checks with no LOCAL switches;
   - closed ports seen from the internet;
   - Docker/ufw behaviour on a real Linux host;
   - an SSL Labs grade.
2. **Provider credentials** for staging (SMTP, Twilio Verify or the decision to run without SMS OTP, Google client id, optional AI/STT), carried over from L2.
3. **Off-host backup destination** and the monitoring and alerting tools (`STAGING_DEPLOYMENT.md` §11, §12). The hospital has to choose them; none are configured.
4. **A cloud L7 load balancer** in front of nginx is not supported as shipped (`STAGING_DEPLOYMENT.md` §5). A TCP pass-through balancer is.
5. Carried over, unchanged: the clinical safety sign-off, the penetration test and DPDP assessment, the mobile upload keystore, and load figures on staging.
6. CI's `deploy-staging` and `deploy-production` jobs are still placeholders that only `echo`. They report success without deploying anything. Left as is: wiring them needs the host and its credentials.

## F. Housekeeping

- The rehearsal containers, volumes and images were removed afterwards, and Colima was stopped. They lived only in the scratch copy and held synthetic data.
- Git status after this work: modified tracked files and new files only (section D). No staging, no commits. Untracked files from other sessions or the user (`.claude/`, `.ua/`, `reports/database-view.html`, `backend/db.sqlite3.backup-2026-11-03-before-migrate`, `backend/patients/tests 2.py`) were not touched.
