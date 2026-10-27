# Security Audit Checklist - Hospital Management System

**AUDIT NOTE (2026-10-10):** This checklist was created as a target for production readiness. As of 2026-10-10, many items are implemented in source code but **automated verification could not be completed** due to environment issues. Items marked with [x] below reflect source code implementation status only, not test verification.

---

## Executive Summary

This checklist validates the security posture of the HMS before production deployment. Each item must be verified and signed off.

## Authentication & Authorization

### Authentication
- [ ] **SEC-001**: `DEBUG=False` in production settings
- [ ] **SEC-002**: `SECRET_KEY` sourced from environment variable (not hardcoded)
- [ ] **SEC-003**: `JWT_SECRET_KEY` separate from Django secret key
- [ ] **SEC-004**: JWT tokens use HS256 (or RS256 with key rotation)
- [ ] **SEC-005**: Access token lifetime ≤ 15 minutes
- [ ] **SEC-006**: Refresh token lifetime ≤ 7 days with rotation
- [ ] **SEC-007**: Refresh tokens blacklisted after rotation
- [ ] **SEC-008**: Password hashing uses PBKDF2/Argon2 (not MD5/SHA1)
- [ ] **SEC-009**: Password validation enforced (length, complexity, common passwords)
- [ ] **SEC-010**: Account lockout after failed attempts (configurable)
- [ ] **SEC-011**: MFA/2FA support for admin accounts
- [ ] **SEC-012**: Google OAuth configured with restricted scopes
- [ ] **SEC-013**: Session cookies: `Secure`, `HttpOnly`, `SameSite=Strict`
- [ ] **SEC-014**: CSRF cookies: `Secure`, `HttpOnly`, `SameSite=Strict`
- [ ] **SEC-015**: Session timeout configured (24 hours max)

### Authorization
- [ ] **SEC-020**: Role-based access control (RBAC) implemented
- [ ] **SEC-021**: Hospital-level data isolation enforced
- [ ] **SEC-022**: Object-level permissions for sensitive resources
- [ ] **SEC-023**: Staff hospital membership required for data access
- [ ] **SEC-024**: Admin interface restricted (IP whitelist, obfuscated URL)
- [ ] **SEC-025**: API permissions default to `IsAuthenticated`
- [ ] **SEC-026**: Cross-hospital data access blocked
- [ ] **SEC-027**: Patient data access requires hospital membership

## Data Protection

### Encryption
- [ ] **SEC-030**: TLS 1.2+ enforced for all connections
- [ ] **SEC-031**: HSTS enabled with preload (1 year)
- [ ] **SEC-032**: Database connections encrypted (SSL mode=require)
- [ ] **SEC-033**: Redis connections encrypted (TLS)
- [ ] **SEC-034**: Backup encryption at rest (AES-256)
- [ ] **SEC-035**: Media file encryption for sensitive documents
- [ ] **SEC-036**: Email transmission uses TLS

### Data Handling
- [ ] **SEC-040**: PII/PHI not logged (passwords, tokens, medical data)
- [ ] **SEC-041**: Audit logs exclude sensitive fields
- [ ] **SEC-042**: File upload validation (type, size, content)
- [ ] **SEC-043**: Private media served through authenticated views
- [ ] **SEC-044**: Document access controlled by hospital membership
- [ ] **SEC-045**: Audio recordings encrypted at rest
- [ ] **SEC-046**: Database columns encrypted for sensitive fields
- [ ] **SEC-047**: Data retention policies implemented
- [ ] **SEC-048**: Secure deletion for removed sensitive data

## Network Security

### Transport
- [ ] **SEC-050**: HTTPS enforced (`SECURE_SSL_REDIRECT=True`)
- [ ] **SEC-051**: SSL/TLS certificates valid, not expired
- [ ] **SEC-052**: Certificate pinning for external APIs
- [ ] **SEC-053**: Internal service communication encrypted
- [ ] **SEC-054**: Database not publicly accessible
- [ ] **SEC-055**: Redis not publicly accessible
- [ ] **SEC-056**: Management ports (SSH, RDP) restricted

### Network Controls
- [ ] **SEC-060**: VPC/subnet isolation for tiers
- [ ] **SEC-061**: Security groups/firewalls restrict traffic
- [ ] **SEC-062**: Load balancer terminates SSL
- [ ] **SEC-063**: WAF configured for API endpoints
- [ ] **SEC-064**: DDoS protection enabled
- [ ] **SEC-065**: Rate limiting on all endpoints

## Application Security

### Input Validation
- [ ] **SEC-070**: All inputs validated (DRF serializers)
- [ ] **SEC-071**: SQL injection prevented (ORM parameterization)
- [ ] **SEC-072**: XSS prevented (auto-escaping, CSP)
- [ ] **SEC-073**: Path traversal prevented (secure file paths)
- [ ] **SEC-074**: Command injection prevented (no shell execution)
- [ ] **SEC-075**: XXE prevented (XML parser config)
- [ ] **SEC-076**: SSRF prevented (URL validation)

### Security Headers
- [ ] **SEC-080**: `X-Frame-Options: DENY`
- [ ] **SEC-081**: `X-Content-Type-Options: nosniff`
- [ ] **SEC-082**: `X-XSS-Protection: 1; mode=block`
- [ ] **SEC-083**: `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] **SEC-084**: `Content-Security-Policy` configured
- [ ] **SEC-085**: `Permissions-Policy` configured
- [ ] **SEC-086**: `Strict-Transport-Security` (HSTS)

### API Security
- [ ] **SEC-090**: Rate limiting on auth endpoints (5/min)
- [ ] **SEC-091**: Rate limiting on AI endpoints (30/min)
- [ ] **SEC-092**: Rate limiting on file upload (10/min)
- [ ] **SEC-093**: CORS restricted to known origins
- [ ] **SEC-094**: API versioning implemented
- [ ] **SEC-095**: Deprecated endpoints removed
- [ ] **SEC-096**: GraphQL/REST introspection disabled in prod
- [ ] **SEC-097**: Request size limits configured
- [ ] **SEC-098**: Correlation ID for request tracing

## Infrastructure Security

### Container Security
- [ ] **SEC-100**: Base images updated regularly
- [ ] **SEC-101**: Non-root user in containers
- [ ] **SEC-102**: Read-only root filesystem
- [ ] **SEC-103**: Capabilities dropped (no privileged)
- [ ] **SEC-104**: Resource limits configured
- [ ] **SEC-105**: Health checks implemented
- [ ] **SEC-106**: Secrets not in images (build args, env)
- [ ] **SEC-107**: Vulnerability scanning in CI/CD

### Secrets Management
- [ ] **SEC-110**: No secrets in source code
- [ ] **SEC-111**: No secrets in Docker images
- [ ] **SEC-112**: No secrets in CI/CD logs
- [ ] **SEC-113**: Secrets rotated periodically (90 days)
- [ ] **SEC-114**: Secret access audited
- [ ] **SEC-115**: External secret manager (AWS Secrets Manager, Vault)

## Monitoring & Incident Response

### Logging
- [ ] **SEC-120**: Structured JSON logging
- [ ] **SEC-121**: Correlation IDs in all logs
- [ ] **SEC-122**: Audit logs for all data modifications
- [ ] **SEC-123**: Failed authentication logged
- [ ] **SEC-124**: Authorization failures logged
- [ ] **SEC-125**: Admin actions logged
- [ ] **SEC-126**: Log retention ≥ 1 year
- [ ] **SEC-127**: Logs shipped to centralized system

### Alerting
- [ ] **SEC-130**: Alert on failed login bursts
- [ ] **SEC-131**: Alert on authorization anomalies
- [ ] **SEC-132**: Alert on data export/bulk access
- [ ] **SEC-133**: Alert on privilege escalation
- [ ] **SEC-134**: Alert on configuration changes
- [ ] **SEC-135**: Alert on backup failures
- [ ] **SEC-136**: Alert on certificate expiration

### Incident Response
- [ ] **SEC-140**: Incident response plan documented
- [ ] **SEC-141**: Runbooks for common scenarios
- [ ] **SEC-142**: Forensic readiness (disk images, logs)
- [ ] **SEC-143**: Communication templates ready
- [ ] **SEC-144**: Regulatory notification procedures
- [ ] **SEC-145**: Post-incident review process

## Compliance

### Healthcare Regulations
- [ ] **SEC-150**: HIPAA compliance (US)
- [ ] **SEC-151**: GDPR compliance (EU)
- [ ] **SEC-152**: HITECH Act compliance
- [ ] **SEC-153**: Local healthcare regulations
- [ ] **SEC-154**: Data processing agreements with subprocessors
- [ ] **SEC-155**: Business associate agreements (BAAs)
- [ ] **SEC-156**: Patient consent management
- [ ] **SEC-157**: Right to access/rectify/erase implemented
- [ ] **SEC-158**: Data breach notification procedures

### Standards
- [ ] **SEC-160**: ISO 27001 alignment
- [ ] **SEC-161**: SOC 2 Type II readiness
- [ ] **SEC-162**: NIST Cybersecurity Framework
- [ ] **SEC-163**: OWASP Top 10 mitigated
- [ ] **SEC-164**: FHIR security best practices
- [ ] **SEC-165**: HL7 security considerations

## Vulnerability Management

- [ ] **SEC-170**: Dependency scanning in CI/CD
- [ ] **SEC-171**: Container scanning in CI/CD
- [ ] **SEC-172**: SAST/DAST in CI/CD
- [ ] **SEC-173**: Penetration testing annually
- [ ] **SEC-174**: Bug bounty program
- [ ] **SEC-175**: Patch management process
- [ ] **SEC-176**: CVE monitoring for dependencies
- [ ] **SEC-177**: Emergency patch procedure

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Security Engineer | | | |
| DevOps Engineer | | | |
| Backend Lead | | | |
| CTO / Security Officer | | | |

## Remediation Tracking

| Finding ID | Severity | Description | Owner | Due Date | Status |
|------------|----------|-------------|-------|----------|--------|
| | | | | | |

---

**Note**: This checklist must be completed and all Critical/High findings remediated before production deployment. Medium findings should have a remediation plan with timeline. Low findings are tracked for continuous improvement.