# Operations Runbook

Day-to-day procedures. Deployment, backup and upgrade steps are in `DEPLOYMENT.md`; deeper recovery procedures are in `DISASTER_RECOVERY.md` and `ROLLBACK_STRATEGY.md`.

## Daily checks

| Check | How | Healthy |
|---|---|---|
| Liveness / readiness | `curl -fsS https://<host>/health/ready/` | `"status": "ready"`, database and cache healthy |
| Containers | `docker compose -f docker-compose.prod.yml ps` | All up; backend healthy |
| Backup ran | Newest file in the backup directory is dated today | Present; `backup.py verify` passes |
| Errors | `docker compose ... logs --since 24h backend \| grep -E "ERROR\|Traceback"` | None unexplained |
| Notification failures | `GET /api/notifications/deliveries/?status=failed` (Admin) | None, or explained (e.g. provider outage) |
| Lockouts / sign-in failures | Audit actions `auth.staff_login.failed` | No bursts from one IP |

## Common tasks

### Approve a new staff member

They register with "Create Account". The hospital Admin opens **Admin → Users**, chooses a role and clicks **Approve**. Only an Admin can grant Admin.

For doctors, also link their login to their Doctor record (`user` field, via Django admin or `PATCH /api/doctors/{id}/` by an Admin). Without that link they cannot approve AI drafts or finalize discharge summaries.

### Remove someone's access

**Admin → Users → Remove Access** deactivates the membership for this hospital immediately. Their next API call is refused, and their access token expires within 15 minutes. To revoke all sessions at once, use Django admin → Outstanding tokens → blacklist.

### Unlock an account

Failures lock an account for 15 minutes. To unlock sooner, clear the cache key `staff-login-failures:<username>` (`docker compose exec backend python manage.py shell -c "from django.core.cache import cache; cache.delete('staff-login-failures:<username>')"`), or let the user reset their password.

### Patient wants to stop sharing records

The patient uses **Notifications / Consent → Stop Sharing**. Staff at the source hospital can also call `POST /api/consent/shares/{id}/revoke/`. The recipient loses access immediately; the access log remains.

### Patient opts out of SMS or voice

Record it with `POST /api/notifications/consents/revoke/ {patient, purpose: "notifications_sms"}`. The newest answer wins.

### Correcting clinical data

Edit through the normal screens; every change keeps old → new values in the audit log. A finalized discharge summary cannot be edited; add a discharge note instead. MAR outcomes cannot be edited.

### Reading the audit trail

`GET /api/audit/audit-logs/?hospital=<id>` (Admin role). There is no viewer page yet.

## Incidents

| Symptom | Likely cause | Action |
|---|---|---|
| AI scribe says "AI service is not configured" | No provider key, or provider down | Document manually; configure `AI_SCRIBE_*` / provider keys. Nothing is written to the record on failure. |
| Staff can't sign in: "requires a one-time code" / OTP 503 | Twilio Verify not configured or down | Fix the Twilio credentials. As a temporary emergency measure an operator may set `STAFF_LOGIN_REQUIRE_OTP=False` and restart backend; record the decision. |
| Users see "You are not a member of that hospital" | Stale hospital selection | Sign out and back in; the switcher resets to a valid hospital |
| `/health/ready/` database unhealthy | PostgreSQL down or credentials wrong | `docker compose logs postgres`; check `DATABASE_URL` |
| Celery tasks not running | Worker or beat stopped | `docker compose up -d celery-worker celery-beat`; the only scheduled tasks are OTP and audit cleanup |
| Suspected data exposure | — | Preserve logs; pull audit rows for the user or IP; rotate secrets (`DJANGO_SECRET_KEY` invalidates sessions; replace the JWT keys); follow your breach-notification duties under the DPDP Act |

## Developer environment notes

- **The repo is on an iCloud-synced Desktop**, which evicts files and makes Python and Node stall or run very slowly. Move the project to a non-synced folder, such as `~/code/`. Until then, run Python with an out-of-tree cache:

  ```bash
  PYTHONPYCACHEPREFIX=/tmp/hms-pycache python manage.py ...
  ```

  If `backend_env` keeps stalling, create a fresh virtualenv outside iCloud and install `requirements-lock.txt`.
- **Tests:** `cd backend && python manage.py test --settings=config.settings.testing`. Both SQLite and PostgreSQL work: point a settings override at a scratch PostgreSQL database.
- **Regenerate API docs:** `python scripts/generate_api_docs.py`.
- **Frontend:** `npm run dev` (proxy target via `VITE_PROXY_TARGET`), `npm run lint`, `npm run build`.
