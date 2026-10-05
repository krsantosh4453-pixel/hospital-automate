# Hospital Management System - Deployment Documentation

## Overview

This document describes the complete deployment process for the Hospital Management System (HMS) in production environments.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                            │
│                     (SSL Termination)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Nginx #1    │  │   Nginx #2    │  │   Nginx #N    │
│  (Frontend)   │  │  (Frontend)   │  │  (Frontend)   │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Backend #1   │  │  Backend #2   │  │  Backend #N   │
│  (Gunicorn)   │  │  (Gunicorn)   │  │  (Gunicorn)   │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  PostgreSQL   │  │     Redis     │  │   Celery      │
│   (Primary)   │  │   (Cluster)   │  │  (Workers)    │
└───────────────┘  └───────────────┘  └───────────────┘
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
- PostgreSQL 16+
- Redis 7+
- Nginx (or cloud load balancer)
- SSL Certificates (Let's Encrypt or commercial)

### Domain & DNS

- A record pointing to load balancer IP
- Wildcard SSL certificate for `*.yourdomain.com`
- Subdomain for API: `api.yourdomain.com`

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
| `SECRET_KEY` | Deprecated, use DJANGO_SECRET_KEY | - |

### Email (Required for notifications)

| Variable | Description |
|----------|-------------|
| `EMAIL_HOST` | SMTP server |
| `EMAIL_PORT` | SMTP port (587) |
| `EMAIL_USE_TLS` | Use TLS (True) |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password |

### Optional Integrations

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `AI_SCRIBE_API_KEY` | OpenAI/Anthropic API key |
| `ABDM_CLIENT_ID` | ABDM client ID |
| `ABDM_CLIENT_SECRET` | ABDM client secret |
| `TWILIO_ACCOUNT_SID` | Twilio SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `SENTRY_DSN` | Sentry DSN for error tracking |
| `BACKUP_ENCRYPTION_KEY` | Encryption key for backups |

## Deployment Methods

### Method 1: Docker Compose (Single Server)

```bash
# 1. Clone repository
git clone <repository-url>
cd hospital-automate

# 2. Configure environment
cp .env.example .env
# Edit .env with production values

# 3. Create SSL certificates directory
mkdir -p ssl
# Place fullchain.pem and privkey.pem in ssl/

# 4. Start services
docker-compose -f docker-compose.prod.yml up -d

# 5. Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 6. Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# 7. Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### Method 2: Kubernetes (Production)

See `k8s/` directory for Kubernetes manifests.

```bash
# Apply manifests
kubectl apply -f k8s/

# Check status
kubectl get pods -n hms
```

### Method 3: Cloud Provider (AWS/GCP/Azure)

Use managed services:
- **Database**: RDS/Cloud SQL/Cloud SQL for PostgreSQL
- **Cache**: ElastiCache/Memorystore/Redis Cache
- **Storage**: S3/GCS/Blob Storage for media files
- **Compute**: ECS/Fargate/Cloud Run/AKS
- **Load Balancer**: ALB/Cloud Load Balancer/Application Gateway

## Database Setup

### PostgreSQL Configuration

```sql
-- Create database and user
CREATE DATABASE hms_prod;
CREATE USER hms_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE hms_prod TO hms_user;

-- Extensions
\c hms_prod
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### Connection Pooling (PgBouncer)

For high-traffic deployments, use PgBouncer:

```ini
# pgbouncer.ini
[databases]
hms_prod = host=postgres port=5432 dbname=hms_prod

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

## Redis Configuration

```redis
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
appendonly yes
requirepass your_redis_password
```

## SSL/TLS Setup

### Let's Encrypt (Automatic)

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com -d api.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Manual Certificates

Place in `ssl/` directory:
- `fullchain.pem` - Certificate chain
- `privkey.pem` - Private key

Set permissions:
```bash
chmod 600 ssl/privkey.pem
chmod 644 ssl/fullchain.pem
```

## Nginx Configuration

See `nginx.prod.conf` for production configuration.

Key features:
- SSL termination
- Rate limiting
- Static file serving
- Health check endpoints
- Security headers

## Service Management

### Starting Services

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### Stopping Services

```bash
# Graceful shutdown
docker-compose -f docker-compose.prod.yml down

# With volumes (WARNING: deletes data!)
docker-compose -f docker-compose.prod.yml down -v
```

### Restarting Services

```bash
# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# Restart all
docker-compose -f docker-compose.prod.yml restart
```

## Database Migrations

### Safe Migration Process

```bash
# 1. Create pre-migration backup
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/migrate_safe.py backup \
  --database-url "$DATABASE_URL" \
  --backup-dir /backups

# 2. Check migration plan
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/migrate_safe.py plan

# 3. Verify migration safety
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/migrate_safe.py verify

# 4. Apply migrations
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/migrate_safe.py apply \
  --database-url "$DATABASE_URL" \
  --backup-dir /backups

# 5. Verify application works
curl -f https://api.yourdomain.com/health/ready/
```

### Rollback Procedure

```bash
# 1. Identify migration to rollback
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py showmigrations

# 2. Rollback specific migration
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/migrate_safe.py rollback \
  --app <app_name> \
  --migration <migration_name>

# 3. Restore from backup if needed
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/backup.py restore \
  --database-url "$DATABASE_URL" \
  --backup-file /backups/hms_backup_YYYYMMDD_HHMMSS.sql.gz.enc
```

## Backup & Recovery

### Automated Backups

Backups run daily via Celery Beat:

```bash
# Manual backup
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/backup.py create \
  --database-url "$DATABASE_URL" \
  --backup-dir /backups \
  --encryption-key "$BACKUP_ENCRYPTION_KEY"

# List backups
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/backup.py list \
  --backup-dir /backups
```

### Recovery Procedure

1. Stop application services
2. Restore database from backup
3. Restore media files from backup
4. Start application services
5. Verify data integrity

### Backup Verification

```bash
# Verify backup integrity
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/backup.py verify \
  --backup-file /backups/hms_backup_YYYYMMDD_HHMMSS.sql.gz.enc \
  --encryption-key "$BACKUP_ENCRYPTION_KEY"
```

## Monitoring & Observability

### Health Checks

| Endpoint | Purpose |
|----------|---------|
| `/health/live/` | Liveness - process is alive |
| `/health/ready/` | Readiness - can serve traffic |
| `/health/` | Basic health |

### Metrics

- Prometheus metrics at `/metrics/`
- Key metrics: request latency, error rate, DB connections, cache hit rate

### Logging

Structured JSON logs in `/app/logs/`:
- Application logs: `django.log`
- Error logs: `django_errors.log`
- Access logs: Nginx access log

### Alerting

Configure alerts for:
- CPU > 80%
- Memory > 85%
- Disk > 85%
- Error rate > 1%
- Response time > 2s
- Database connections > 80%
- Celery queue depth > 100

## Security Checklist

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` from environment
- [ ] `ALLOWED_HOSTS` configured
- [ ] HTTPS enforced (`SECURE_SSL_REDIRECT=True`)
- [ ] Secure cookies (`SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`)
- [ ] HSTS enabled
- [ ] CORS restricted to known origins
- [ ] Rate limiting enabled
- [ ] Admin URL obfuscated
- [ ] Database credentials from environment
- [ ] Redis password set
- [ ] Backup encryption enabled
- [ ] Sentry configured
- [ ] Security headers present
- [ ] File upload validation
- [ ] Private media protected
- [ ] Hospital isolation enforced
- [ ] RBAC configured
- [ ] Audit logging enabled

## Scaling

### Horizontal Scaling

```bash
# Scale backend workers
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Scale celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4
```

### Vertical Scaling

Increase resources in docker-compose or Kubernetes:

```yaml
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '2'
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check backend health, increase timeout |
| Database connection refused | Verify PostgreSQL is running, check credentials |
| Redis connection refused | Verify Redis is running, check password |
| Static files 404 | Run `collectstatic`, check Nginx config |
| Media files 404 | Check media volume mount, permissions |
| Celery tasks not processing | Check Redis connection, worker logs |
| Migration stuck | Check for locks, kill stale connections |

### Debug Commands

```bash
# Check backend logs
docker-compose -f docker-compose.prod.yml logs backend

# Check database
docker-compose -f docker-compose.prod.yml exec postgres psql -U hms_user -d hms_prod

# Check Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping

# Check Celery
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A config inspect active
```

## Maintenance

### Daily
- Monitor error rates
- Check backup completion
- Review slow queries

### Weekly
- Review security alerts
- Update dependencies
- Check disk space

### Monthly
- Rotate secrets
- Test restore procedure
- Review performance metrics
- Update SSL certificates

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
| 1.0.0 | 2024-01-01 | Initial deployment documentation |