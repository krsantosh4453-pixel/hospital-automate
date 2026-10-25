# Deployment Checklist

Use this with `DEPLOYMENT.md` (how to do each step) and `SECURITY_AUDIT_CHECKLIST.md` (security sign-off). As of 2026-10-25, every box below that needs Docker, real credentials or people is **unchecked**: none of it has been done.

## 0. Before anything

- [ ] Decide R-01 (tokens in `localStorage`) and R-03 (patient and clinical hard deletes) in `DEFECT_REGISTER.md`. Both are policy or architecture decisions.
- [ ] If the repository will be shared, purge `backend/db.sqlite3` from git history (R-02) and rotate anything it held.
- [ ] Move the working copy out of iCloud Drive. Evicted files stall Python and Node; see `TEST_EXECUTION_REPORT.md`.
- [ ] Commit the current work and push to `master`. CI now triggers on `master`; confirm every job is green on GitHub.

## 1. Configuration (staging first, then production)

- [ ] `.env.production` filled from `.env.production.example`. Production refuses to start without:
  - `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DATABASE_URL`, `REDIS_URL`
  - `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`
  - `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`, `GOOGLE_CLIENT_ID`
  - Twilio Verify (`TWILIO_ACCOUNT_SID`, `TWILIO_API_KEY`, `TWILIO_API_SECRET`, `TWILIO_VERIFY_SERVICE_SID`)
- [ ] `TRUSTED_PROXY_COUNT` matches the proxies in front of Django (1 for the shipped nginx).
- [ ] `FHIR_ENABLED`, `HL7_ENABLED`, `ABDM_ENABLED` = False (not mounted).
- [ ] `AI_SCRIBE_API_KEY` set, or accept that the AI scribe is disabled (503).
- [ ] `AUDIT_LOG_RETENTION_DAYS` chosen per legal retention policy.
- [ ] Secrets stored in a secret manager or root-only files; never in git.

## 2. Build and start (staging rehearsal: never run before)

- [ ] `docker compose -f docker-compose.prod.yml build` succeeds.
- [ ] TLS certificate installed; HTTP redirects to HTTPS.
- [ ] `up -d backend` applies migrations once. This audit added **no** migrations, and `makemigrations --check` is clean.
- [ ] `python manage.py check --deploy` inside the backend container reports no issues.

## 3. Verify in staging

- [ ] `/health/ready/` returns 200 (database and cache).
- [ ] `/media/<anything>` returns 404; documents download only through `/api/documents/<id>/download/`.
- [ ] API responses carry `Content-Security-Policy`, `Strict-Transport-Security` and `X-Frame-Options: DENY`.
- [ ] Staff sign-in: password → real SMS OTP via Twilio Verify. Patient routes and Google sign-in refuse staff accounts (403).
- [ ] Patient sign-in: email verification and SMS OTP with real delivery.
- [ ] Notifications: in-app works. Email to a consenting test patient arrives. SMS/WhatsApp/Voice are recorded as **failed / not implemented** (R-06), not sent.
- [ ] AI scribe with the chosen provider: draft → clinician approval; a mock provider is refused.
- [ ] Two hospitals, mixed-role user: no cross-hospital rows with or without `X-Hospital-ID`.
- [ ] Rate limit: repeated login failures from one client are limited even when `X-Forwarded-For` changes.
- [ ] Browser pass of all 26 staff routes and 8 patient-portal routes over HTTPS.
- [ ] Backup → verify → restore on a staging copy (`scripts/backup.py`); restore time recorded.
- [ ] Load test against staging (none has been run); record p95 latency and error rate.

## 4. Sign-offs (people, not code)

- [ ] Clinical safety review: MAR, discharge, lab release and AI-draft rules, including written acknowledgement that there is **no drug-interaction checking**.
- [ ] Penetration test.
- [ ] DPDP Act 2023 privacy assessment (consent notices, retention, breach process). Report cyber incidents to CERT-In within 6 hours, per its 2022 directions, if applicable.
- [ ] Staff told which modules do not exist (`KNOWN_LIMITATIONS.md`).

## 5. Go-live and rollback

- [ ] Backup taken immediately before the release; rollback = previous image + restore (`DEPLOYMENT.md` §8, `ROLLBACK_STRATEGY.md`).
- [ ] Monitoring and alerting on `/health/ready/`, 5xx rate and the notification failure rate.
