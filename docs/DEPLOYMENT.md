# Hospital Management System - Deployment Documentation

**AUDIT NOTE (2026-10-10):** This deployment guide documents the intended production deployment process. As of 2026-10-10, the system is **NOT PRODUCTION READY** — automated tests cannot be executed, frontend build has Node.js compatibility issues, and several modules are incomplete (MOCK/STUB/UNMOUNTED). See README.md for current module status.

---

## Overview

This document describes the complete deployment process for the Hospital Management System (HMS) in production environments.

## Architecture

```
Internet
   │
   ▼
┌─────────────────────────────────────┐
│         Nginx (SSL Termination)     │
│    Port 80 (redirect) / 443 (HTTPS) │
└──────────────────┬──────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌──────────┐
   │Static  │ │ Media  │ │  API/    │
   │ Files  │ │ Files  │ │  Admin   │
   └────────┘ └────────┘ └────┬─────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌─────────────────────────────┐
              │     Django (Gunicorn)       │
              │  Port 8000 (internal only)  │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         ┌──────────┐  ┌──────────┐  ┌──────────┐
         │PostgreSQL│  │  Redis   │  │  Celery  │
         │  (DB)    │  │ (Cache/  │  │ (Workers)│
         │          │  │  Broker) │  │          │
         └──────────┘  └──────────┘  └──────────┘
```

## Prerequisites

### Infrastructure Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 vCPU | 8+ vCPU |
| RAM | 8 GB | 16+ GB |
| Storage | 100 GB SSD | 500+ GB NVMe |
| Network | 1 Gbps | 10 Gbps |

### Software Requirements

- Docker 24+
- Docker Compose 2+
- SSL Certificates (Let's Encrypt or commercial)

### Domain & DNS

- A record pointing to server IP
- SSL certificate for `yourdomain.com` (and `api.yourdomain.com` if separate)

## Environment Variables

Create `.env` file from `.env.example`:

```bash
cp .env.example .env
# Edit .env with production values
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key (50+ chars) | `django-insecure-xyz...` |
| `JWT_SECRET_KEY` | JWT signing key (separate from Django) | `jwt-secret-xyz...` |
| `DATABASE_URL` | PostgreSQL connection URL | `postgres://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection URL | `redis://:pass@host:6379/0` |
| `ALLOWED_HOSTS` | Comma-separated hostnames | `api.yourdomain.com,yourdomain.com` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend URLs | `https://yourdomain.com` |

### Email (Required for notifications)

| Variable | Description |
|----------|-------------|
| `EMAIL_HOST` | SMTP server |
| `EMAIL_PORT` | SMTP port (587) |
| `EMAIL_USE_TLS` | Use TLS (True) |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password |

### Optional Integrations (set to enable)

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `AI_SCRIBE_API_KEY` | OpenAI/Anthropic API key (enables AI Scribe) |
| `ABDM_CLIENT_ID` | ABDM client ID (enables ABDM integration) |
| `ABDM_CLIENT_SECRET` | ABDM client secret |
| `TWILIO_ACCOUNT_SID` | Twilio SID (enables SMS/WhatsApp) |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `SENTRY_DSN` | Sentry DSN for error tracking |
| `BACKUP_ENCRYPTION_KEY` | Encryption key for backups |

### Feature Flags (default: enabled, set to `False` to disable)

| Variable | Description |
|----------|-------------|
| `AI_SCRIBE_ENABLED` | AI Medical Scribe |
| `FHIR_ENABLED` | FHIR R4 interoperability |
| `HL7_ENABLED` | HL7 v2 messaging |
| `ABDM_ENABLED` | ABDM/ABHA integration |
| `MONITORING_ENABLED` | Sentry monitoring |
| `BACKUP_ENABLED` | Automated backups |

## Deployment Method: Docker Compose (Single Server)

### 1. Prepare Server

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group changes

# Install Docker Compose v2 (if not included)
docker compose version
```

### 2. Clone and Configure

```bash
# 1. Clone repository
git clone <repository-url>
cd hospital-automate

# 2. Configure environment
cp .env.example .env
# Edit .env with production values (see required variables above)

# 3. Create SSL certificates directory
mkdir -p ssl
# Place fullchain.pem and privkey.pem in ssl/
# See SSL/TLS Setup section below
```

### 3. SSL/TLS Setup

#### Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get update && sudo apt-get install -y certbot

# Generate certificates (standalone mode - stop nginx first if running)
sudo certbot certonly --standalone -d yourdomain.com

# Certificates will be in /etc/letsencrypt/live/yourdomain.com/
# Copy to ssl/ directory for Docker access
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/
sudo chown $USER:$USER ssl/*

# Set up auto-renewal
sudo certbot renew --dry-run
# Add to crontab: 0 3 * * * certbot renew --quiet --post-hook "cp /etc/letsencrypt/live/yourdomain.com/*.pem /path/to/hospital-automate/ssl/ && docker compose -f /path/to/hospital-automate/docker-compose.prod.yml restart nginx"
```

#### Manual Certificates

Place in `ssl/` directory:
- `fullchain.pem` - Certificate chain
- `privkey.pem` - Private key

Set permissions:
```bash
chmod 600 ssl/privkey.pem
chmod 644 ssl/fullchain.pem
```

### 4. Start Services

```bash
# Start all services (builds images on first run)
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Check status
docker compose -f docker-compose.prod.yml ps
```

The entrypoint script automatically:
- Waits for database connectivity
- Runs migrations
- Collects static files
- Creates superuser (if DJANGO_SUPERUSER_* vars set)

### 5. Verify Deployment

```bash
# Check health endpoints
curl -f http://localhost/health/live/
curl -f http://localhost/health/ready/

# Check frontend
curl -f http://localhost/

# Check API
curl -f http://localhost/api/
```

## Service Management

### Starting Services

```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Check status
docker compose -f docker-compose.prod.yml ps
```

### Stopping Services

```bash
# Graceful shutdown
docker compose -f docker-compose.prod.yml down

# With volumes (WARNING: deletes database data!)
docker compose -f docker-compose.prod.yml down -v
```

### Restarting Services

```bash
# Restart specific service
docker compose -f docker-compose.prod.yml restart backend

# Restart all
docker compose -f docker-compose.prod.yml restart
```

### Scaling

```bash
# Scale backend workers
docker compose -f docker-compose.prod.yml up -d --scale backend=3

# Scale celery workers
docker compose -f docker-compose.prod.yml up -d --scale celery-worker=4
```

Note: When scaling backend, ensure your load balancer/nginx upstream configuration supports multiple backend instances.

## Database Migrations

Migrations run automatically on container startup via the entrypoint script.

### Manual Migration Commands

```bash
# Run migrations manually
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Show migration status
docker compose -f docker-compose.prod.yml exec backend python manage.py showmigrations

# Create new migrations (after model changes)
docker compose -f docker-compose.prod.yml exec backend python manage.py makemigrations
```

### Rollback Procedure

```bash
# 1. Identify migration to rollback
docker compose -f docker-compose.prod.yml exec backend python manage.py showmigrations

# 2. Rollback specific migration
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate <app_name> <migration_name>

# 3. Restore from backup if needed (see Backup section)
```

## Backup & Recovery

### Automated Backups

Backups run daily via Celery Beat (when `BACKUP_ENABLED=True` and `BACKUP_ENCRYPTION_KEY` set).

### Manual Backup

```bash
# Create database backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U hms_user hms_prod | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup media files
docker compose -f docker-compose.prod.yml exec backend tar -czf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /app media/
```

### Recovery Procedure

1. Stop application services: `docker compose -f docker-compose.prod.yml stop backend celery-worker celery-beat nginx frontend`
2. Restore database: `gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker compose -f docker-compose.prod.yml exec -T postgres psql -U hms_user -d hms_prod`
3. Restore media files: `docker compose -f docker-compose.prod.yml exec -T backend tar -xzf media_backup_YYYYMMDD_HHMMSS.tar.gz -C /app`
4. Start application services: `docker compose -f docker-compose.prod.yml start backend celery-worker celery-beat nginx frontend`
5. Verify data integrity

## Monitoring & Observability

### Health Checks

| Endpoint | Purpose |
|----------|---------|
| `/health/live/` | Liveness - process is alive (no dependency checks) |
| `/health/ready/` | Readiness - can serve traffic (checks DB, cache) |
| `/health/` | Basic health |

### Logging

Structured JSON logs in `/app/logs/` (mounted to `./logs/` on host):
- Application logs: `django.log`
- Error logs: `django_errors.log`
- Access logs: Nginx access log (stdout)

### Sentry (Optional)

Set `SENTRY_DSN` and `MONITORING_ENABLED=True` to enable error tracking.

## Security Checklist

- [ ] `DEBUG=False` (enforced in production settings)
- [ ] `DJANGO_SECRET_KEY` from environment (50+ random chars)
- [ ] `JWT_SECRET_KEY` from environment (separate from Django secret)
- [ ] `ALLOWED_HOSTS` configured with actual domain names
- [ ] HTTPS enforced (`SECURE_SSL_REDIRECT=True`)
- [ ] Secure cookies (`SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`)
- [ ] HSTS enabled (`SECURE_HSTS_SECONDS=31536000`)
- [ ] CORS restricted to known origins (`CORS_ALLOWED_ORIGINS`)
- [ ] Rate limiting enabled (nginx + DRF throttling)
- [ ] Admin URL obfuscated (`ADMIN_URL` env var)
- [ ] Database credentials from environment
- [ ] Redis password set (`REDIS_PASSWORD`)
- [ ] SSL certificates valid and auto-renewing
- [ ] Security headers present (CSP, HSTS, X-Frame-Options, etc.)
- [ ] Hospital isolation enforced (`ENFORCE_HOSPITAL_ISOLATION=True`)
- [ ] Audit logging enabled (`AUDIT_LOG_ENABLED=True`)

## Implemented Features

The following features are implemented and deployed:
- ✅ Patient management (registration, documents, hospital memberships)
- ✅ Doctor management (schedules, availability)
- ✅ Appointment scheduling
- ✅ Nursing (assessments, care tasks, MAR)
- ✅ Clinical workflows (visits, vitals, diagnoses, prescriptions, procedures)
- ✅ IPD (admissions, bed management, discharge)
- ✅ Emergency (triage, orders, medications)
- ✅ Laboratory (tests, samples, results)
- ✅ Pharmacy (inventory, sales, procurement/GRN)
- ✅ Blood Bank (inventory, requests, transactions)
- ✅ Billing (invoices, payments, insurance claims)
- ✅ Notifications (email, SMS, WhatsApp, push, in-app)
- ✅ Audit logging
- ✅ Reports (patient summary, financial, clinical, operational)
- ✅ AI Medical Scribe (consultation recording, transcription, clinical drafts)
- ✅ Multi-hospital support with isolation

## Not Implemented / Placeholder Features

The following are configured in settings but not fully implemented:
- ⚠️ FHIR R4 endpoints (configured, routes commented out)
- ⚠️ HL7 v2 messaging (configured, routes commented out)
- ⚠️ ABDM/ABHA integration (configured, routes commented out)
- ⚠️ Prometheus metrics (`/metrics/` - not implemented)
- ⚠️ Automated backup scripts (`scripts/backup.py` - not implemented)
- ⚠️ Safe migration scripts (`scripts/migrate_safe.py` - not implemented)

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check backend health (`docker compose logs backend`), increase proxy timeouts |
| Database connection refused | Verify PostgreSQL is running, check `DATABASE_URL` credentials |
| Redis connection refused | Verify Redis is running, check `REDIS_URL` and `REDIS_PASSWORD` |
| Static files 404 | Run `collectstatic` (auto on startup), check nginx staticfiles volume |
| Media files 404 | Check media volume mount, permissions |
| Celery tasks not processing | Check Redis connection, worker logs (`docker compose logs celery-worker`) |
| Migration stuck | Check for locks, kill stale connections |
| SSL certificate errors | Verify cert paths in `ssl/`, check nginx config |

### Debug Commands

```bash
# Check backend logs
docker compose -f docker-compose.prod.yml logs backend

# Check database
docker compose -f docker-compose.prod.yml exec postgres psql -U hms_user -d hms_prod

# Check Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping

# Check Celery
docker compose -f docker-compose.prod.yml exec celery-worker celery -A config inspect active

# Check nginx config
docker compose -f docker-compose.prod.yml exec nginx nginx -t

# Enter backend container
docker compose -f docker-compose.prod.yml exec backend bash
```

## Maintenance

### Daily
- Monitor error rates (check logs)
- Check backup completion (if enabled)
- Review slow queries (PostgreSQL logs)

### Weekly
- Review security alerts (Sentry if configured)
- Update dependencies (check for security updates)
- Check disk space (`df -h`)

### Monthly
- Rotate secrets (DJANGO_SECRET_KEY, JWT_SECRET_KEY, passwords)
- Test restore procedure
- Review performance metrics
- Update SSL certificates (if not auto-renewed)

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push/PR:

1. **Backend Lint** - Ruff, Black, isort
2. **Frontend Lint & Build** - ESLint, Vite build
3. **Backend Tests** - pytest with PostgreSQL and Redis services
4. **Security Scan** - Trivy, Bandit, npm audit
5. **Docker Build Test** - Build and test Docker images
6. **Deploy Staging** (on develop branch) - placeholder
7. **Deploy Production** (on version tags) - placeholder

## Support Contacts

| Role | Contact |
|------|---------|
| DevOps | devops@yourdomain.com |
| Backend Team | backend@yourdomain.com |
| Frontend Team | frontend@yourdomain.com |
| Security | security@yourdomain.com |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-10-06 | Initial deployment documentation for Stage 7 |