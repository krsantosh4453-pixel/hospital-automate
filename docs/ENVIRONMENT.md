# Environment Variables Documentation

**Source:** `.env.example` (created by Stage 7)
**Last Updated:** 2026-10-06

This document describes every environment variable used by the Hospital Management System. Variables are categorized by subsystem.

---

## Quick Reference Table

| Variable | Required | Secret | Dev Default | Prod Requirement |
|----------|----------|--------|-------------|------------------|
| `DJANGO_ENV` | Yes | No | `development` | `production` |
| `DJANGO_SECRET_KEY` | Yes | **YES** | `django-insecure-...` | **Generate unique 50+ char key** |
| `JWT_SECRET_KEY` | Yes | **YES** | (empty) | **Generate unique key** |
| `DATABASE_URL` | Yes | **YES** | `postgres://...@localhost:5432/hms_dev` | **Production PostgreSQL URL** |
| `REDIS_URL` | Yes | **YES** | `redis://localhost:6379/0` | **Production Redis URL** |
| `ALLOWED_HOSTS` | Yes | No | `localhost,127.0.0.1,0.0.0.0` | **Your domain(s)** |
| `CORS_ALLOWED_ORIGINS` | Yes | No | `http://localhost:5173,...` | **Your frontend domain(s)** |
| `VITE_API_BASE_URL` | Yes | No | `http://localhost:8000/api` | **Your API domain** |

---

## Django Core Settings

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `DJANGO_ENV` | Environment selector: `development`, `testing`, `production` | `development` | `production` | No | `config/settings/__init__.py` |
| `DJANGO_SECRET_KEY` | Django cryptographic signing key (sessions, CSRF, passwords) | `django-insecure-dev-key` | **Generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`** | **YES** | `config/settings/base.py`, `production.py` |
| `JWT_SECRET_KEY` | Separate key for JWT token signing (SimpleJWT) | (empty = uses DJANGO_SECRET_KEY) | **Generate unique key** | **YES** | `config/settings/base.py` → `SIMPLE_JWT.SIGNING_KEY` |
| `ALLOWED_HOSTS` | Comma-separated hostnames Django will serve | `localhost,127.0.0.1,0.0.0.0` | `api.yourdomain.com,yourdomain.com` | No | `config/settings/base.py` |
| `ADMIN_URL` | Admin URL prefix (obfuscate in production) | `admin/` | `a1b2c3d4-admin/` | No | `config/settings/base.py`, `config/urls.py` |

---

## Database (PostgreSQL)

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `DATABASE_URL` | Primary database connection (postgres://user:pass@host:port/db) | `postgres://hms_user:hms_password@localhost:5432/hms_dev` | **Production managed DB URL** | **YES** | `config/settings/base.py` → `dj_database_url.parse()` |
| `POSTGRES_DB` | Alternative: database name | `hms_dev` | Required if not using DATABASE_URL | **YES** | `config/settings/base.py` (fallback) |
| `POSTGRES_USER` | Alternative: database user | `hms_user` | Required if not using DATABASE_URL | **YES** | `config/settings/base.py` (fallback) |
| `POSTGRES_PASSWORD` | Alternative: database password | `hms_password` | Required if not using DATABASE_URL | **YES** | `config/settings/base.py` (fallback) |
| `POSTGRES_HOST` | Alternative: database host | `localhost` | Required if not using DATABASE_URL | No | `config/settings/base.py` (fallback) |
| `POSTGRES_PORT` | Alternative: database port | `5432` | Required if not using DATABASE_URL | No | `config/settings/base.py` (fallback) |

---

## Redis

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `REDIS_URL` | Redis connection (redis://[:password@]host:port/db) | `redis://localhost:6379/0` | **Production Redis (ElastiCache, Memorystore, etc.)** | **YES** | `config/settings/base.py` → `CACHES`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| `REDIS_PASSWORD` | Redis password (if using authenticated Redis) | (empty) | **Required for managed Redis** | **YES** | `config/settings/production.py` |

---

## Celery

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `CELERY_BROKER_URL` | Celery message broker | `redis://localhost:6379/0` | Same as REDIS_URL | **YES** | `config/settings/base.py` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://localhost:6379/0` | Same as REDIS_URL | **YES** | `config/settings/base.py` |
| `CELERY_WORKER_CONCURRENCY` | Worker processes per node | `4` | Match CPU cores | No | `config/settings/base.py` |

---

## CORS & CSRF

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174` | **Your frontend domain(s): `https://yourdomain.com,https://app.yourdomain.com`** | No | `config/settings/base.py` → `CORS_ALLOWED_ORIGINS` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated CSRF trusted origins | (empty) | **Same as CORS for production: `https://yourdomain.com,https://api.yourdomain.com`** | No | `config/settings/production.py` |

---

## HTTPS/SSL (Production Only)

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `SECURE_SSL_REDIRECT` | Redirect HTTP → HTTPS | `False` | `True` | No | `config/settings/production.py` |
| `SECURE_HSTS_SECONDS` | HSTS max-age in seconds | `0` | `31536000` (1 year) | No | `config/settings/production.py` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | Apply HSTS to subdomains | `False` | `True` | No | `config/settings/production.py` |
| `SECURE_HSTS_PRELOAD` | Enable HSTS preload list | `False` | `True` | No | `config/settings/production.py` |

---

## Email (SMTP)

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `EMAIL_HOST` | SMTP server hostname | `smtp.gmail.com` | **Production SMTP (SendGrid, Mailgun, SES, etc.)** | No | `config/settings/base.py`, `production.py` |
| `EMAIL_PORT` | SMTP port | `587` | `587` (TLS) or `465` (SSL) | No | `config/settings/base.py` |
| `EMAIL_USE_TLS` | Use STARTTLS | `True` | `True` | No | `config/settings/base.py` |
| `EMAIL_HOST_USER` | SMTP username | `your-email@gmail.com` | **Production SMTP credentials** | **YES** | `config/settings/base.py` |
| `EMAIL_HOST_PASSWORD` | SMTP password / app password | `your-app-password` | **Production SMTP credentials** | **YES** | `config/settings/base.py` |
| `DEFAULT_FROM_EMAIL` | Default sender address | `HMS <noreply@hospital.local>` | **Your domain: `HMS <noreply@yourdomain.com>`** | No | `config/settings/base.py` |

---

## Google OAuth

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID (public) | `xxx.apps.googleusercontent.com` | **Production Google Cloud OAuth client ID** | No (public) | `config/settings/base.py` → `GOOGLE_CLIENT_ID`, frontend `vite.config.js` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | (commented in .env.example) | **Required for OAuth flow** | **YES** | `config/settings/production.py` (not in base) |

---

## AI Medical Scribe

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `AI_SCRIBE_ENABLED` | Enable AI Scribe module | `True` | `True` (if using) | No | `config/settings/base.py` |
| `AI_SCRIBE_PROVIDER` | LLM provider: `openai`, `anthropic`, `local` | `openai` | Your chosen provider | No | `config/settings/base.py` |
| `AI_SCRIBE_API_KEY` | API key for LLM provider | `your-openai-api-key` | **Production API key** | **YES** | **NOT YET CONSUMED** — Provider integration is mocked |
| `AI_SCRIBE_MODEL` | Model name | `gpt-4` | Your chosen model | No | `config/settings/base.py` |
| `AI_SCRIBE_MAX_TOKENS` | Max tokens per request | `4000` | Per model limits | No | `config/settings/base.py` |
| `AI_SCRIBE_TEMPERATURE` | Sampling temperature | `0.1` | Low for clinical accuracy | No | `config/settings/base.py` |

> **Note:** AI Scribe provider integration is currently a **mock/demo pipeline**. The `AI_SCRIBE_API_KEY` is defined but not consumed by working provider code.

---

## FHIR Interoperability (Not Implemented)

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `FHIR_ENABLED` | Enable FHIR endpoints | `True` | `False` (not implemented) | No | `config/settings/base.py` |
| `FHIR_BASE_URL` | Base URL for FHIR API | `https://yourdomain.com/api/fhir/` | Required if FHIR enabled | No | `config/settings/base.py` |
| `FHIR_VERSION` | FHIR version | `R4` | `R4` | No | `config/settings/base.py` |

> **Note:** FHIR endpoints are **commented out** in `config/urls.py` — not implemented.

---

## HL7 Messaging (Not Implemented)

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `HL7_ENABLED` | Enable HL7 listener | `True` | `False` (not implemented) | No | `config/settings/base.py` |
| `HL7_LISTEN_PORT` | HL7 MLLP listen port | `2575` | Required if HL7 enabled | No | `config/settings/base.py` |
| `HL7_MSH_SENDING_APPLICATION` | MSH-3 Sending Application | `HMS` | Your application name | No | `config/settings/base.py` |
| `HL7_MSH_SENDING_FACILITY` | MSH-4 Sending Facility | `HOSPITAL` | Your facility name | No | `config/settings/base.py` |

> **Note:** HL7 endpoints are **commented out** in `config/urls.py` — not implemented.

---

## ABDM/ABHA Integration (Not Implemented)

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `ABDM_ENABLED` | Enable ABDM integration | `True` | `False` (not implemented) | No | `config/settings/base.py` |
| `ABDM_BASE_URL` | ABDM gateway URL | `https://dev.abdm.gov.in` | Production ABDM URL | No | `config/settings/base.py` |
| `ABDM_CLIENT_ID` | ABDM client ID | `your-abdm-client-id` | **Production ABDM credentials** | **YES** | `config/settings/base.py` |
| `ABDM_CLIENT_SECRET` | ABDM client secret | `your-abdm-client-secret` | **Production ABDM credentials** | **YES** | `config/settings/base.py` |

> **Note:** ABDM endpoints are **commented out** in `config/urls.py` — not implemented.

---

## Notifications (SMS/WhatsApp/Push)

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `SMS_PROVIDER` | SMS provider: `twilio` | `twilio` | `twilio` (or other) | No | `config/settings/base.py` |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | `your-twilio-account-sid` | **Production Twilio credentials** | **YES** | `config/settings/production.py` |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | `your-twilio-auth-token` | **Production Twilio credentials** | **YES** | `config/settings/production.py` |
| `TWILIO_PHONE_NUMBER` | Twilio sender phone | `+1234567890` | **Verified Twilio number** | **YES** | `config/settings/production.py` |
| `WHATSAPP_PROVIDER` | WhatsApp provider: `twilio` | `twilio` | `twilio` | No | `config/settings/base.py` |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business number ID | `your-whatsapp-phone-number-id` | **Production WhatsApp credentials** | **YES** | `config/settings/production.py` |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp access token | `your-whatsapp-access-token` | **Production WhatsApp credentials** | **YES** | `config/settings/production.py` |
| `PUSH_NOTIFICATION_PROVIDER` | Push provider: `firebase` | `firebase` | `firebase` | No | `config/settings/base.py` |
| `FIREBASE_CREDENTIALS_PATH` | Path to Firebase service account | `/path/to/firebase-credentials.json` | **Production Firebase credentials** | **YES** | `config/settings/production.py` |
| `PATIENT_OTP_DELIVERY` | OTP delivery: `console`, `cache`, `sms` | `sms` | `sms` (or configured provider) | No | `config/settings/base.py` |

---

## Cloud Storage (AWS S3 Example)

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key | (commented) | **If using S3 for media** | **YES** | `config/settings/production.py` (storage backend) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | (commented) | **If using S3 for media** | **YES** | `config/settings/production.py` |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name | (commented) | **If using S3 for media** | No | `config/settings/production.py` |
| `AWS_S3_REGION_NAME` | S3 region | `us-east-1` | Your bucket region | No | `config/settings/production.py` |
| `AWS_S3_CUSTOM_DOMAIN` | CloudFront/CDN domain | (commented) | If using CDN | No | `config/settings/production.py` |

---

## Monitoring & Error Tracking

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `SENTRY_DSN` | Sentry DSN for error tracking | `https://xxx@sentry.io/xxx` | **Production Sentry DSN** | **YES** | `config/settings/production.py` → `sentry_sdk.init()` |
| `SENTRY_ENVIRONMENT` | Sentry environment name | `production` | `production` | No | `config/settings/production.py` |
| `SENTRY_TRACES_SAMPLE_RATE` | Transaction sampling rate | `0.1` | `0.1` (10%) | No | `config/settings/production.py` |
| `SENTRY_PROFILES_SAMPLE_RATE` | Profiling sampling rate | `0.1` | `0.1` | No | `config/settings/production.py` |

---

## Backup

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `BACKUP_ENABLED` | Enable automated backups | `True` | `True` | No | `config/settings/base.py`, Celery beat tasks |
| `BACKUP_STORAGE_PATH` | Local backup directory | `/backups` | **Mounted volume / cloud path** | No | `scripts/backup.py` |
| `BACKUP_RETENTION_DAYS` | Backup retention | `30` | Per compliance policy | No | `scripts/backup.py` |
| `BACKUP_ENCRYPTION_KEY` | Backup encryption key (AES-256) | `your-backup-encryption-key` | **Generate: `openssl rand -base64 32`** | **YES** | `scripts/backup.py` |

---

## Frontend (Vite)

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `VITE_API_BASE_URL` | API base URL for frontend | `http://localhost:8000/api` | **`https://api.yourdomain.com/api`** | No | `src/services/api.js` → `API_BASE_URL` |

> **Note:** Only variables prefixed with `VITE_` are exposed to the frontend build.

---

## Domain Name

| Variable | Purpose | Dev Example | Prod Requirement | Secret | Consumed In |
|----------|---------|-------------|------------------|--------|-------------|
| `DOMAIN_NAME` | Primary domain for nginx config | `yourdomain.com` | **Your production domain** | No | `nginx.prod.conf`, Docker Compose |

---

## Security Notes

### Never Commit Secrets
- **Never** commit `.env` with real values to version control
- Use `.env.example` as template only
- In production, inject secrets via:
  - Docker secrets
  - Kubernetes secrets
  - Cloud provider secret managers (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault)
  - CI/CD protected variables

### Key Generation Commands

```bash
# Django secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# JWT secret key (32+ bytes base64)
openssl rand -base64 32

# Backup encryption key (32 bytes = 256 bits)
openssl rand -base64 32

# Database password
openssl rand -base64 24

# Redis password
openssl rand -base64 24
```

### Variable Precedence

1. **Docker/Kubernetes secrets** (highest)
2. **System environment variables**
3. **`.env` file** (loaded by `python-dotenv` in `config/settings/__init__.py`)
4. **Defaults in `config/settings/base.py`** (lowest)

---

## Validation Checklist

Before deploying to production, verify:

- [ ] `DJANGO_SECRET_KEY` is unique, 50+ characters, not the dev default
- [ ] `JWT_SECRET_KEY` is set and different from Django secret
- [ ] `DATABASE_URL` points to production PostgreSQL with SSL
- [ ] `REDIS_URL` uses TLS (`rediss://`) in production
- [ ] `ALLOWED_HOSTS` contains only your production domains
- [ ] `CORS_ALLOWED_ORIGINS` contains only your frontend domains
- [ ] `CSRF_TRUSTED_ORIGINS` matches CORS for production
- [ ] `SECURE_SSL_REDIRECT=True` and HSTS settings enabled
- [ ] `EMAIL_*` credentials work for transactional emails
- [ ] `SENTRY_DSN` configured for error tracking
- [ ] `BACKUP_ENCRYPTION_KEY` generated and stored securely
- [ ] All `*_SECRET`, `*_PASSWORD`, `*_KEY`, `*_TOKEN` values are production credentials
- [ ] No development values (localhost, insecure keys) remain