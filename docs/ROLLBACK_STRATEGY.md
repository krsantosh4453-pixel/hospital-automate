# Deployment Rollback Strategy - Hospital Management System

## Overview

This document defines the rollback procedures for HMS deployments to minimize downtime and data loss during failed deployments.

## Rollback Principles

1. **Safety First**: Never perform destructive operations on production data
2. **Speed**: Rollback must complete within RTO (5 minutes for app, 30 minutes for DB)
3. **Verification**: Every rollback step must be verified before proceeding
4. **Communication**: All stakeholders notified during rollback
5. **Documentation**: Every rollback documented for post-mortem

## Rollback Triggers

### Automatic Triggers
- Health check failure > 3 consecutive checks
- Error rate > 5% for 5 minutes
- Latency p99 > 10 seconds for 5 minutes
- Database migration failure
- Critical security vulnerability in deployment

### Manual Triggers
- On-call engineer decision
- Stakeholder request
- Failed smoke tests post-deployment
- Performance regression detected

## Rollback Procedures

### Procedure 1: Application-Only Rollback (Blue-Green / Rolling)

**When**: New code deployed, database compatible
**RTO**: 2-5 minutes

```bash
# 1. Identify previous stable image tag
PREVIOUS_TAG=$(docker images hms-backend --format "{{.Tag}}" | grep -v latest | head -2 | tail -1)

# 2. Update deployment to previous version
# Docker Compose
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend

# Kubernetes
kubectl rollout undo deployment/backend -n hms

# 3. Verify health
for i in {1..30}; do
  if curl -f https://api.yourdomain.com/health/ready/; then
    echo "Rollback successful"
    exit 0
  fi
  sleep 10
done

# 4. If failed, escalate to Procedure 2
```

### Procedure 2: Database-Compatible Rollback (Code + Migrations)

**When**: Migrations applied but backward-compatible
**RTO**: 10-15 minutes

```bash
# 1. Rollback application (Procedure 1)
# 2. Rollback migrations (if needed)
kubectl exec -n hms deploy/backend -- python manage.py migrate <app> <previous_migration>

# 3. Verify data integrity
kubectl exec -n hms deploy/backend -- python manage.py check --deploy

# 4. Run smoke tests
kubectl exec -n hms deploy/backend -- python manage.py test --keepdb
```

### Procedure 3: Database-Incompatible Rollback (Destructive Migrations)

**When**: Migrations include destructive changes (DROP COLUMN, DELETE TABLE)
**RTO**: 30-60 minutes
**⚠️ HIGH RISK - Requires explicit approval**

```bash
# 1. STOP - Do not proceed without:
#    - Database backup verified (Procedure 4)
#    - Explicit approval from Database Engineer + CTO
#    - Maintenance window declared

# 2. Put application in maintenance mode
kubectl scale deployment/backend --replicas=0 -n hms

# 3. Restore database from pre-migration backup
# See Procedure 4

# 4. Rollback application code
# Procedure 1

# 5. Verify
# Procedure 2 verification steps

# 6. Remove maintenance mode
kubectl scale deployment/backend --replicas=3 -n hms
```

### Procedure 4: Database Restore from Backup

**When**: Data corruption, ransomware, destructive migration rollback
**RTO**: 30-120 minutes (depends on database size)

```bash
# 1. Identify backup to restore
# List available backups
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/backup.py list --backup-dir /backups

# SELECT BACKUP: hms_backup_20240115_020000.sql.gz.enc

# 2. Stop application writes
kubectl scale deployment/backend --replicas=0 -n hms
kubectl scale deployment/celery-worker --replicas=0 -n hms

# 3. Verify backup integrity
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/backup.py verify \
  --backup-file /backups/hms_backup_20240115_020000.sql.gz.enc \
  --encryption-key "$BACKUP_ENCRYPTION_KEY"

# 4. Restore database
docker-compose -f docker-compose.prod.yml exec backend \
  python scripts/backup.py restore \
  --database-url "$DATABASE_URL" \
  --backup-file /backups/hms_backup_20240115_020000.sql.gz.enc \
  --encryption-key "$BACKUP_ENCRYPTION_KEY"

# 5. Verify restore
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U hms_user -d hms_prod -c "SELECT count(*) FROM patients_patient;"

# 6. Restart application
kubectl scale deployment/backend --replicas=3 -n hms
kubectl scale deployment/celery-worker --replicas=4 -n hms

# 7. Verify application health
curl -f https://api.yourdomain.com/health/ready/
```

### Procedure 5: Full Infrastructure Rollback (Terraform/Infrastructure)

**When**: Infrastructure changes cause issues
**RTO**: 15-30 minutes

```bash
# 1. Identify previous Terraform state
cd infra/terraform

# 2. Review plan
terraform plan -out=rollback.plan

# 3. Apply previous state
terraform apply -auto-approve rollback.plan

# 4. Verify infrastructure
# - Database accessible
# - Redis accessible
# - Load balancer healthy
# - DNS correct

# 5. Deploy application to rolled-back infrastructure
# Procedure 1
```

## Rollback Decision Matrix

| Scenario | Procedure | Approval Required | Max Time |
|----------|-----------|-------------------|----------|
| App crash, no DB changes | 1 | On-call engineer | 5 min |
| App bug, backward-compat migrations | 2 | On-call + Tech Lead | 15 min |
| Destructive migration | 3 | DB Engineer + CTO | 60 min |
| Data corruption | 4 | DB Engineer + CTO | 120 min |
| Infrastructure failure | 5 | DevOps Lead | 30 min |
| Ransomware | 4 + Security | Security + CTO + Legal | 4 hours |

## Pre-Deployment Checklist (Prevents Rollbacks)

- [ ] All tests pass (unit, integration, e2e)
- [ ] Migration safety check passed (`migrate_safe.py verify`)
- [ ] Pre-migration backup created
- [ ] Staging deployment verified
- [ ] Smoke tests pass on staging
- [ ] Performance benchmarks met
- [ ] Security scan clean
- [ ] Rollback plan reviewed and approved
- [ ] On-call engineer notified
- [ ] Stakeholders informed of deployment window

## Post-Rollback Actions

1. **Immediate** (within 30 minutes)
   - [ ] Verify all services healthy
   - [ ] Notify stakeholders of rollback completion
   - [ ] Document rollback reason and timeline

2. **Short-term** (within 24 hours)
   - [ ] Root cause analysis
   - [ ] Create incident report
   - [ ] Update runbooks if needed
   - [ ] Schedule fix deployment

3. **Long-term** (within 1 week)
   - [ ] Post-mortem meeting
   - [ ] Action items assigned
   - [ ] Process improvements implemented
   - [ ] Metrics reviewed

## Rollback Testing

### Schedule
- **Monthly**: Application rollback drill (Procedure 1)
- **Quarterly**: Database rollback drill (Procedure 4) on staging
- **Semi-annually**: Full DR rollback (Procedure 4 + 5) on DR environment

### Test Criteria
- [ ] Rollback completes within RTO
- [ ] Zero data loss (verified by row counts)
- [ ] Application functional post-rollback
- [ ] No manual intervention required beyond runbook
- [ ] All team members familiar with procedures

## Communication Templates

### Rollback Initiated
```
Subject: [ROLLBACK] HMS Production - Deployment Rolled Back

Deployment v{X.Y.Z} has been rolled back to v{X.Y.Z-1}.

Reason: {brief reason}
Impact: {user impact}
Rollback started: {timestamp}
Rollback completed: {timestamp}
Next steps: {investigation/fix timeline}
```

### Rollback Complete
```
Subject: [RESOLVED] HMS Production - Rollback Complete

Rollback to v{X.Y.Z-1} completed successfully.

All health checks passing.
Error rate: {X}%
Latency p99: {X}ms
Post-mortem scheduled: {date/time}
```

## Tooling

### Rollback Scripts
- `scripts/migrate_safe.py rollback` - Safe migration rollback
- `scripts/backup.py restore` - Database restore from backup
- `scripts/deploy_rollback.sh` - Application rollback wrapper

### Monitoring During Rollback
- Health checks: `/health/ready/` every 10 seconds
- Error rate: Datadog/Prometheus alerts
- Database: Connection count, replication lag
- Logs: Structured JSON with correlation IDs

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-01 | DevOps Team | Initial version |