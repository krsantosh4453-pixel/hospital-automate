# Deployment Guide

Single-server Docker Compose deployment (`docker-compose.prod.yml`). The step-by-step staging procedure, the environment variable checklist, backups and rollback are in [`STAGING_DEPLOYMENT.md`](STAGING_DEPLOYMENT.md); this page summarises them.

Status (2026-11-18): the full stack was rehearsed on local Docker (Colima) with synthetic secrets and a private test CA, and it passed (`STAGING_DEPLOYMENT_REPORT_2026-11-18.md`). That is **not** a real-host staging rehearsal: there is still no staging server, domain or CA-signed certificate.

## 1. Prerequisites

- Linux host with Docker Engine 24+ and Compose v2; at least 4 GB RAM and 20 GB disk.
- DNS A record for your domain; TLS certificate from a public CA (Let's Encrypt or commercial).
- Credentials:
  - SMTP;
  - Twilio Verify, unless staff OTP and patient SMS OTP are switched off;
  - Google OAuth client id (required by production settings);
  - optional: an AI provider key, Sentry DSN.
- Nothing else on the host: backups run `pg_dump` and encryption inside the containers (`scripts/deploy/backup.sh`).

## 2. Configuration

One file, `.env.production`, sits next to `docker-compose.prod.yml` and is never committed. Copy `.env.production.example`, fill in **every REQUIRED value** and `chmod 600` it. The same file feeds every Django process and Compose's own `${...}` interpolation, so always pass it with `--env-file`:

```bash
dc() { docker compose --env-file .env.production -f docker-compose.prod.yml "$@"; }
```

Compose stops with an error if `POSTGRES_PASSWORD`, `REDIS_PASSWORD` or `DOMAIN_NAME` is missing. Production settings refuse to start if any of these are missing or unusable:

- `DJANGO_SECRET_KEY` (50+ characters, not a `django-insecure` key), `ALLOWED_HOSTS` (no `*`), `CORS_ALLOWED_ORIGINS`
- `DATABASE_URL` and `REDIS_URL` (compose builds both)
- `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`: an RS256 pair that loads and matches
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `GOOGLE_CLIENT_ID`
- Twilio Verify: `TWILIO_ACCOUNT_SID`, `TWILIO_API_KEY`, `TWILIO_API_SECRET`, `TWILIO_VERIFY_SERVICE_SID`, unless `STAFF_LOGIN_REQUIRE_OTP=False` and `PATIENT_OTP_DELIVERY=off`

Generate the JWT key pair and write each key on one line with `\n` escapes:

```bash
openssl genrsa -out jwt_private.pem 2048
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
awk 'BEGIN{ORS="\\n"}1' jwt_private.pem   # value for JWT_PRIVATE_KEY
```

Policy and integration variables:

| Variable | Default (production) | Meaning |
|---|---|---|
| `STAFF_LOGIN_REQUIRE_OTP` | True | Staff must complete SMS OTP after the password |
| `AI_SCRIBE_ENABLED` | True | Without a provider key the AI endpoints answer 503 "not configured"; mock providers are never used in production |
| `FHIR_ENABLED`, `HL7_ENABLED`, `ABDM_ENABLED` | False | Leave False until their conformance and security review |
| `AUDIT_LOG_RETENTION_DAYS` | 0 (keep forever) | Choose according to your legal retention obligations |
| `TRUSTED_PROXY_COUNT` | 1 | Proxies in front of Django that append to `X-Forwarded-For` (nginx). Rate limits, DRF throttles and the audit IP use the entry this many places from the right. Never set it higher than the real number of proxies. See `STAGING_DEPLOYMENT.md` §5 before putting a load balancer in front. |
| `CSP_REPORT_ONLY` | False | True sends Django's Content-Security-Policy as report-only while you test it (`CSP_REPORT_URI` collects reports) |
| `HMS_RELEASE` | latest | Image tag for the build; keep the previous one for rollback |

## 3. TLS

Place `fullchain.pem` and `privkey.pem` in `./ssl/`. Issue the first certificate with certbot in standalone mode before the first start, then renew through the webroot that nginx serves from `./certbot` (`STAGING_DEPLOYMENT.md` §4).

## 4. Build and start

```bash
export HMS_RELEASE=$(git rev-parse --short HEAD)
dc build
dc up -d          # postgres, redis -> backend (migrates) -> worker, beat, frontend, nginx
dc ps             # every service healthy (beat: running)
```

Compose orders the start-up itself: the worker and beat wait until the backend has migrated and answers `/health/ready/`. Only the `backend` container runs migrations and collectstatic. Django's log files live in the `app_logs` volume (`dc exec backend tail -f /app/logs/django_errors.log`).

## 5. First administrator and hospital

```bash
dc exec backend python manage.py createsuperuser
```

Sign in to Django admin at `/<ADMIN_URL>/` as that superuser, then:

1. Create the hospital: `POST /api/hospital/hospitals/` as superuser, or use admin.
2. Create a `StaffProfile` for the first hospital Admin, with a `StaffHospitalMembership` (role Admin) at that hospital.
3. From then on, the hospital Admin approves staff in **Admin → Users** (staff register via "Create Account").
4. Link each doctor's login on their Doctor record (`user`). This is required for approving AI drafts and finalizing discharge summaries.

## 6. Post-deploy verification

```bash
scripts/deploy/verify_host.sh                          # on the server
scripts/deploy/verify_public.sh staging.your-domain    # from another machine
```

They check health, DEBUG, mock AI providers, `check --deploy`, migrations, which container migrates, published ports, Redis auth, log rotation, the certificate, the HTTPS redirect, security headers, `/media/` and closed ports. Then sign in as the hospital Admin and open Users, Departments and Reports.

**After upgrading from a pre-2026-10-24 database**, count the rows the tenancy backfill could not assign (see `DATABASE.md`) and assign them deliberately.

## 7. Backups

```bash
BACKUP_DIR=/var/backups/hms scripts/deploy/backup.sh create            # database + media, encrypted
BACKUP_DIR=/var/backups/hms scripts/deploy/backup.sh restore-check FILE  # restore drill into a scratch DB
```

`BACKUP_ENCRYPTION_KEY` is required; keep a copy away from the server. Cron lines, off-host copies and the restore procedure are in `STAGING_DEPLOYMENT.md` §11 and §13. The files use the same format as `backend/scripts/backup.py`.

## 8. Upgrades and rollback

1. `scripts/deploy/backup.sh create`.
2. `git pull`, then `export HMS_RELEASE=$(git rev-parse --short HEAD)` and `dc build`.
3. Preview the migrations: `dc run --rm --no-deps -e RUN_MIGRATIONS=false backend python manage.py migrate --plan`.
4. `dc up -d` (the backend migrates first).
5. Run `scripts/deploy/verify_host.sh`.

**Rollback:** `HMS_RELEASE=<previous tag> dc up -d --no-build` when the release added no migrations. When it did, reverse them first with the new image still running (`dc exec backend python manage.py migrate <app> <previous>`), then switch the tag. If data was damaged, restore the backup into a new database. See `STAGING_DEPLOYMENT.md` §9 and `ROLLBACK_STRATEGY.md`.

## 9. Upgrading to the 2026-11-05 release (PR 7)

Read this before the first staging deploy of this release.

1. **Back up first** (section 7). Several migrations add constraints that check existing rows.
2. **Duplicate UHIDs:** run `dc exec backend python manage.py report_duplicate_uhids` (read only). Settle every group it lists by hand. `patients/0011` refuses to run while duplicates exist.
3. **Migrate:** `up -d backend` applies the new migrations:
   - `patients` 0011–0012, `clinical` 0011–0012, `nurses` 0008–0009: entered-in-error fields, MAR doctor, extra vitals.
   - `billing` 0008 (advance payments), `pharmacy` 0006 (returns, substitutes), `procurement` 0002 (requisitions, issues, returns), `hospital` 0007 (role restrictions).
   - New apps: `terminology`, `hospital_services`; `notifications` 0007 (voice fallback).
4. **ICD-10 codes:** the entrypoint runs `load_icd10 --if-empty`, loading about 190 common codes once. For the full code set, download the CMS ICD-10-CM "Code Descriptions in Tabular Order" file and run `manage.py load_icd10 <file>`.
5. **New settings (all optional, safe defaults):**
   - `VOICE_CALL_PROVIDER=noop` records voice fallbacks as skipped. Set `twilio` only with `TWILIO_VOICE_FROM_NUMBER` and Twilio Voice credentials.
   - The AI discharge draft uses the existing AI scribe provider settings. Without one, drafts are assembled from the records.
6. **After deploy, also check:**
   - `/api/schema/` still loads for a platform admin.
   - The Hospital services page opens.
   - Permissions shows the "At this hospital" column for the hospital Admin.
   - A test removal ("entered in error") asks for a reason.
7. **Rollback:** every migration in this release reverses (`manage.py migrate <app> <previous>`). Reversing the entered-in-error migrations drops the reason columns, so take the backup first. Records hidden as entered in error become visible again after a rollback.

Not done here, and needed before patients use the system: a real staging host with its own domain and certificate, provider credentials (Twilio Verify, SMS/WhatsApp, email, AI), the clinical and P&T sign-offs, a penetration test and the DPDP assessment.

## Operational cautions

- `docker compose ... down -v` **deletes the database volume**. Never use `-v` on production.
- Services have fixed `container_name`s, so `--scale` does not work. To scale, remove `container_name` and put a load balancer in front.
- The frontend reads `VITE_API_BASE_URL` at build time and defaults to `/api`, which is correct for this compose layout. The Docker build excludes `.env*` (`.dockerignore`). A local `npm run build`, however, picks up a repo-root `.env`; if that file points at `http://localhost:8000/api`, the bundle will call localhost.
