# Disaster Recovery Plan - Hospital Management System

## Overview

This document defines the disaster recovery strategy for the Hospital Management System (HMS), including Recovery Point Objective (RPO), Recovery Time Objective (RTO), and detailed recovery procedures.

## Recovery Objectives

### RPO (Recovery Point Objective)

| Data Tier | RPO | Description |
|-----------|-----|-------------|
| **Clinical Data** | 0 minutes (synchronous) | Patient records, prescriptions, lab results - zero data loss |
| **Financial Data** | 0 minutes (synchronous) | Invoices, payments, insurance claims - zero data loss |
| **Operational Data** | 15 minutes | Appointments, queue, bed allocations |
| **Audit Logs** | 1 hour | System audit trails, AI interactions |
| **Documents/Media** | 24 hours | Patient documents, reports, audio files |
| **Configuration** | 24 hours | System settings, user preferences |

### RTO (Recovery Time Objective)

| Scenario | RTO | Description |
|----------|-----|-------------|
| **Application Failure** | 5 minutes | Single backend pod/container failure |
| **Database Failure** | 30 minutes | PostgreSQL primary failure, failover to replica |
| **Cache Failure** | 5 minutes | Redis failure, rebuild from database |
| **Storage Failure** | 2 hours | Media/storage failure, restore from backup |
| **Full Site Failure** | 4 hours | Complete infrastructure failure |
| **Ransomware/Corruption** | 24 hours | Malicious data corruption, full restore |

## Backup Strategy

### Backup Schedule

| Backup Type | Frequency | Retention | Storage |
|-------------|-----------|-----------|---------|
| **PostgreSQL Continuous** | Real-time (WAL) | 7 days | Local + Cloud |
| **PostgreSQL Full** | Daily 02:00 UTC | 30 days | Cloud (encrypted) |
| **PostgreSQL Incremental** | Every 6 hours | 7 days | Cloud (encrypted) |
| **Redis Snapshots** | Every 1 hour | 24 hours | Local |
| **Media Files** | Daily 03:00 UTC | 90 days | Cloud (encrypted) |
| **Configuration** | On change | 90 days | Git + Cloud |
| **Kubernetes/Infra** | On change | 90 days | Git |

### Backup Verification

- **Automated**: Daily restore test to staging environment
- **Manual**: Monthly full restore drill
- **Quarterly**: Full disaster recovery exercise

## Recovery Procedures

### Scenario 1: Application Server Failure

**Detection**: Health check fails, load balancer removes instance
**Impact**: Partial capacity loss
**Recovery**:
1. Auto-scaling group launches replacement (2-3 minutes)
2. New instance pulls image, runs migrations
3. Health check passes, added to load balancer
**Verification**: `/health/ready/` returns 200

### Scenario 2: Database Primary Failure

**Detection**: Connection errors, replication lag alerts
**Impact**: Read/write unavailable
**Recovery**:
1. Promote synchronous replica to primary (automated, <30 seconds)
2. Update DNS/connection strings to new primary
3. Verify application connectivity
4. Provision new replica
**Verification**: Write test record, confirm replication

### Scenario 3: Database Corruption/Deletion

**Detection**: Application errors, data inconsistency
**Impact**: Potential data loss
**Recovery**:
1. Stop application writes (maintenance mode)
2. Identify last known good backup (point-in-time recovery)
3. Restore from WAL + base backup to new instance
4. Verify data integrity
5. Switch application to restored database
6. Rebuild replicas
**Verification**: Row counts, checksums, application smoke tests

### Scenario 4: Redis Cache Failure

**Detection**: Cache miss spike, connection errors
**Impact**: Performance degradation, session loss
**Recovery**:
1. Provision new Redis instance
2. Warm cache from database (critical keys first)
3. Update application configuration
4. Monitor hit rates
**Verification**: Cache hit rate > 80% within 10 minutes

### Scenario 5: Storage/Media Failure

**Detection**: File access errors, missing documents
**Impact**: Document unavailable
**Recovery**:
1. Restore from latest backup (daily)
2. Verify file integrity (checksums)
3. Re-process any failed uploads
**Verification**: Sample document access, audit log check

### Scenario 6: Full Site Failure (Region Outage)

**Detection**: All health checks failing, DNS unavailable
**Impact**: Complete service outage
**Recovery**:
1. Activate DR region (pre-provisioned)
2. Restore database from latest backup to DR region
3. Deploy application to DR region
4. Update DNS to DR region (TTL 60s)
5. Verify all services
6. Communicate to stakeholders
**Verification**: Full smoke test suite, stakeholder sign-off

### Scenario 7: Ransomware/Malicious Corruption

**Detection**: Unauthorized encryption, data modification alerts
**Impact**: Data integrity compromised
**Recovery**:
1. **Isolate** - Disconnect affected systems immediately
2. **Assess** - Determine scope and last clean backup
3. **Eradicate** - Rebuild infrastructure from clean images
4. **Restore** - Restore from verified clean backup (pre-incident)
5. **Verify** - Full data integrity verification
6. **Monitor** - Enhanced monitoring for 30 days
**Verification**: Independent audit, penetration test

## Recovery Runbooks

### Runbook: Database Point-in-Time Recovery

```bash
# 1. Identify recovery target time
RECOVERY_TIME="2024-01-15 14:30:00 UTC"

# 2. Provision new PostgreSQL instance
# (Use infrastructure as code)

# 3. Restore base backup
pg_basebackup -h backup-host -D /var/lib/postgresql/data -U replicator -P

# 4. Configure recovery
cat > /var/lib/postgresql/data/recovery.signal <<EOF
restore_command = 'cp /backups/wal_archives/%f %p'
recovery_target_time = '${RECOVERY_TIME}'
recovery_target_action = 'promote'
EOF

# 5. Start PostgreSQL
systemctl start postgresql

# 6. Verify
psql -c "SELECT count(*) FROM patients_patient;"
```

### Runbook: Full Application Restore

```bash
# 1. Provision infrastructure (Terraform)
cd infra/terraform
terraform apply -var="environment=dr"

# 2. Restore database (see database runbook)

# 3. Restore media files
aws s3 sync s3://hms-backups/media/ /app/media/

# 4. Deploy application
kubectl apply -f k8s/ -n hms-dr

# 5. Run migrations
kubectl exec -n hms-dr deploy/backend -- python manage.py migrate

# 6. Verify
curl -f https://dr-api.yourdomain.com/health/ready/
```

## Communication Plan

### Internal Notification

| Severity | Channel | Escalation |
|----------|---------|------------|
| Critical | PagerDuty + Slack #incidents | CTO, VP Engineering |
| High | Slack #incidents + Email | Engineering Lead |
| Medium | Slack #ops | On-call Engineer |
| Low | Slack #ops | Next business day |

### External Communication

| Audience | Channel | Template |
|----------|---------|----------|
| Customers | Status page, Email | "We're experiencing degraded performance..." |
| Partners | Email, Phone | "Service disruption affecting API..." |
| Regulators | Formal notification | Per regulatory requirements |

### Status Page Updates

1. **Investigating** - Issue detected, analysis in progress
2. **Identified** - Root cause found, fix in progress
3. **Monitoring** - Fix deployed, verifying recovery
4. **Resolved** - Service restored, post-mortem scheduled

## Testing & Validation

### Schedule

| Test Type | Frequency | Participants |
|-----------|-----------|--------------|
| Automated backup verify | Daily | CI/CD |
| Restore to staging | Weekly | DevOps |
| Single component failover | Monthly | Engineering |
| Full DR drill | Quarterly | All teams |
| Ransomware simulation | Semi-annual | Security + Engineering |

### Success Criteria

- [ ] RPO met for all data tiers
- [ ] RTO met for all scenarios
- [ ] Data integrity verified (checksums, row counts)
- [ ] Application functional (smoke tests pass)
- [ ] Performance within SLA
- [ ] No data loss confirmed
- [ ] Stakeholder sign-off obtained

## Roles & Responsibilities

| Role | Responsibility |
|------|----------------|
| **Incident Commander** | Overall coordination, decision making |
| **Database Engineer** | Database recovery, replication |
| **DevOps Engineer** | Infrastructure provisioning, deployment |
| **Backend Engineer** | Application recovery, data verification |
| **Security Engineer** | Forensics, eradication (ransomware) |
| **Communications Lead** | Internal/external communication |
| **Executive Sponsor** | Business decisions, resource allocation |

## Contact Information

| Role | Primary | Secondary |
|------|---------|-----------|
| Incident Commander | [Name] - [Phone] | [Name] - [Phone] |
| Database Engineer | [Name] - [Phone] | [Name] - [Phone] |
| DevOps Engineer | [Name] - [Phone] | [Name] - [Phone] |
| Security Engineer | [Name] - [Phone] | [Name] - [Phone] |

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-01 | DevOps Team | Initial version |

## Appendix: Backup Locations

| Backup Type | Primary Location | Secondary Location |
|-------------|------------------|-------------------|
| PostgreSQL WAL | `/backups/wal_archives/` | `s3://hms-backups/wal/` |
| PostgreSQL Base | `/backups/base/` | `s3://hms-backups/base/` |
| Media Files | `/backups/media/` | `s3://hms-backups/media/` |
| Configuration | Git repository | `s3://hms-backups/config/` |

## Appendix: Recovery Checklist

- [ ] Incident declared, team assembled
- [ ] Impact assessed, severity determined
- [ ] Communication initiated
- [ ] Recovery procedure selected
- [ ] Recovery executed
- [ ] Verification completed
- [ ] Service restored
- [ ] Post-mortem scheduled
- [ ] Lessons learned documented
- [ ] Runbooks updated