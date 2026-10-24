# Deployment Guide

Single-server Docker Compose deployment (`docker-compose.prod.yml`).

The compose files were validated by parsing, but **Docker was not available where this guide was written**. Do a full staging rehearsal (steps 1–8) before production.

## 1. Prerequisites

- Linux host with Docker Engine 24+ and Compose v2; at least 4 GB RAM and 20 GB disk.
- DNS A record for your domain; TLS certificate (Let's Encrypt or commercial).
- Credentials:
  - SMTP;
  - Twilio Verify (required by production settings);
  - Google OAuth client id (required by production settings);
  - optional: an AI provider key, Sentry DSN.
- PostgreSQL 16 client tools (`pg_dump`/`psql`) on the host for backups. The backend image does not include them.

## 2. Configuration

Two files sit next to `docker-compose.prod.yml` and are never committed:

| File | Purpose |
|---|---|
| `.env` | Compose interpolation only: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `REDIS_PASSWORD`, `DOMAIN_NAME` |
| `.env.production` | Every Django process (backend, celery-worker, celery-beat). Copy `.env.production.example` and fill in **every REQUIRED value**. |

Production settings refuse to start if any of these are missing:

- `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
- `DATABASE_URL` and `REDIS_URL` (compose builds both)
- `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` (RS256 PEM)
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `GOOGLE_CLIENT_ID`
- Twilio Verify: `TWILIO_ACCOUNT_SID`, `TWILIO_API_KEY`, `TWILIO_API_SECRET`, `TWILIO_VERIFY_SERVICE_SID`

Generate the JWT key pair:

```bash
openssl genrsa -out jwt_private.pem 2048
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
```

Put the PEM text into `.env.production` (use `\n` for newlines, or a secret manager).

Policy and integration variables:

| Variable | Default (production) | Meaning |
|---|---|---|
| `STAFF_LOGIN_REQUIRE_OTP` | True | Staff must complete SMS OTP after the password |
| `AI_SCRIBE_ENABLED` | True | Without a provider key the AI endpoints answer 503 "not configured"; mock providers are never used in production |
| `FHIR_ENABLED`, `HL7_ENABLED`, `ABDM_ENABLED` | False | Their routes are not mounted; leave False |
| `AUDIT_LOG_RETENTION_DAYS` | 0 (keep forever) | Choose according to your legal retention obligations |

## 3. TLS

Place `fullchain.pem` and `privkey.pem` in `./ssl/`. For example, with certbot in standalone mode before first start:

```bash
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/*.pem ./ssl/
```

Renew with a cron job that copies the files and runs `docker compose -f docker-compose.prod.yml restart nginx`.

## 4. Build and start

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d postgres redis
docker compose -f docker-compose.prod.yml up -d backend    # migrates (RUN_MIGRATIONS=true)
docker compose -f docker-compose.prod.yml logs -f backend  # wait for gunicorn
docker compose -f docker-compose.prod.yml up -d celery-worker celery-beat frontend nginx
```

Only the `backend` container runs migrations and collectstatic; workers and beat don't, which avoids migration races.

## 5. First administrator and hospital

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Sign in to Django admin at `/<ADMIN_URL>/` as that superuser, then:

1. Create the hospital: `POST /api/hospital/hospitals/` as superuser, or use admin.
2. Create a `StaffProfile` for the first hospital Admin, with a `StaffHospitalMembership` (role Admin) at that hospital.
3. From then on, the hospital Admin approves staff in **Admin → Users** (staff register via "Create Account").
4. Link each doctor's login on their Doctor record (`user`). This is required for approving AI drafts and finalizing discharge summaries.

## 6. Post-deploy verification

```bash
curl -fsS https://yourdomain.com/health/live/
curl -fsS https://yourdomain.com/health/ready/   # database and cache must be healthy
docker compose -f docker-compose.prod.yml exec backend python manage.py check --deploy
docker compose -f docker-compose.prod.yml exec backend python manage.py showmigrations | grep '\[ \]'   # expect no output
```

Then in a browser:

- Sign in as the hospital Admin and confirm the hospital switcher shows only your hospital.
- Open Users, Departments and Reports.
- Check that `https://yourdomain.com/media/anything` returns 404.

**After upgrading from a pre-2026-10-24 database**, count the rows the tenancy backfill could not assign (see `DATABASE.md`) and assign them deliberately.

## 7. Backups

Run from the host with PostgreSQL 16 client tools and `pip install cryptography>=50.0.2`:

```bash
python backend/scripts/backup.py create  --database-url "$DATABASE_URL" --backup-dir /var/backups/hms --encryption-key "$BACKUP_ENCRYPTION_KEY"
python backend/scripts/backup.py verify  --database-url "$DATABASE_URL" --backup-dir /var/backups/hms --encryption-key "$BACKUP_ENCRYPTION_KEY" --backup-file <file>
python backend/scripts/backup.py restore --database-url "$DATABASE_URL" --backup-dir /var/backups/hms --encryption-key "$BACKUP_ENCRYPTION_KEY" --backup-file <file> --target-database hms_restore_check
```

Generate the key once with `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"` and store it away from the backups. This cycle was verified on PostgreSQL 16 (see `TEST_REPORT.md`). Schedule `create` daily with cron, and run a restore drill monthly into a scratch database.

## 8. Upgrades and rollback

1. Take a backup.
2. `git pull`.
3. Rebuild the images.
4. `up -d backend` (it migrates).
5. Check `/health/ready/`.
6. `up -d` the rest.

**Rollback:** check out the previous tag and rebuild. If migrations changed, reverse them first with `manage.py migrate <app> <previous>`. Every migration added in this work reverses without data loss. Otherwise restore the backup. See `ROLLBACK_STRATEGY.md`.

## Operational cautions

- `docker compose ... down -v` **deletes the database volume**. Never use `-v` on production.
- Services have fixed `container_name`s, so `--scale` does not work. To scale, remove `container_name` and put a load balancer in front.
- The frontend reads `VITE_API_BASE_URL` at build time and defaults to `/api`, which is correct for this compose layout. The Docker build excludes `.env*` (`.dockerignore`). A local `npm run build`, however, picks up a repo-root `.env`; if that file points at `http://localhost:8000/api`, the bundle will call localhost.
