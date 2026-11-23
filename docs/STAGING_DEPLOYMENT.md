# Staging Deployment Procedure

How to stand up a production-like staging environment for Hospital Automate on one Linux host with `docker-compose.prod.yml`, verify it, back it up, and roll it back. Production uses the same procedure with its own host, domain and credentials.

**Status, 2026-11-18:** every step that can run without a real server was rehearsed on local Docker (Colima) with synthetic secrets and a private test CA. Evidence is in [`STAGING_DEPLOYMENT_REPORT_2026-11-18.md`](STAGING_DEPLOYMENT_REPORT_2026-11-18.md). **No real-host staging rehearsal has been done.** Section 14 marks which boxes still need the real host.

Related: [`DEPLOYMENT.md`](DEPLOYMENT.md) (summary, first administrator, release notes), [`ROLLBACK_STRATEGY.md`](ROLLBACK_STRATEGY.md), [`OPERATIONS_RUNBOOK.md`](OPERATIONS_RUNBOOK.md).

## 1. Architecture (unchanged)

```
internet ──80/443──▶ nginx (TLS, headers, rate limits)
                       ├── /            ──▶ frontend (nginx, built React app)
                       ├── /api/ /admin/ /health/ ──▶ backend (gunicorn, Django; the only container that migrates)
                       ├── /static/     ──▶ staticfiles volume (hashed names, cached 1 year)
                       └── /media/      ──▶ 404 (documents download only through the API)
backend, celery-worker, celery-beat ──▶ postgres (16) and redis (7) on the private compose network
```

Only nginx publishes ports to the network. PostgreSQL and the backend publish to `127.0.0.1` only (for host-side tools), and Redis publishes nothing. Docker writes its own iptables rules and bypasses `ufw` for published ports. That is why the loopback binding matters, and why you must not change it to `0.0.0.0`.

## 2. Inputs the hospital must provide

None of these exist yet, and none may be invented. Staging needs its **own** values, separate from production:

| Input | Used for |
|---|---|
| Staging host name, e.g. `staging.<hospital-domain>`, and control of its DNS | `DOMAIN_NAME`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, certificate |
| A Linux server (4+ GB RAM, 2+ vCPU, 40+ GB disk), with SSH access and a firewall you control | the host |
| An off-host backup location (another server, object storage or NAS) | copies of the encrypted backups |
| SMTP account | password reset, patient e-mail OTP |
| Twilio Verify service (or the decision to run staff and patients without SMS OTP) | OTP |
| Google OAuth client id with the staging origin authorised | patient Google sign-in |
| Optional: AI provider key and STT provider; Sentry DSN; an uptime monitor | AI scribe; monitoring |

Staging holds **synthetic data only** unless the DPDP assessment explicitly allows otherwise.

## 3. Host preparation

1. Install a supported Linux LTS release with automatic security updates, Docker Engine 24+ and the Compose v2 plugin. Run `systemctl enable --now docker`, so the stack comes back after a reboot (rehearsed: all 7 services healthy again 61 s after a VM restart).
2. Firewall: allow inbound 22 (from admin addresses only), 80 and 443. Block everything else.
3. Time sync: enable `chrony` or `systemd-timesyncd`. JWT expiry and TLS need a correct clock.
4. Put `/var/lib/docker` and `/var/backups/hms` on disks with room to grow. Alert at 80 % full.
5. Clone the repository to a normal local disk (for example `/opt/hms`, **not** a synced folder such as iCloud or Dropbox) and check out the release tag or commit you are deploying.
6. Create the folders that the compose file mounts: `mkdir -p ssl certbot backups`.

## 4. DNS and the CA-signed certificate

1. Create an `A` record (and an `AAAA` record only if the host has working IPv6) for the staging name, pointing at the host. Check it from outside with `dig +short staging.<domain>`.
2. **First certificate** (port 80 must be free, so before the first `up`):

   ```bash
   sudo certbot certonly --standalone -d staging.<domain> --agree-tos -m <ops-mailbox>
   sudo cp -L /etc/letsencrypt/live/staging.<domain>/fullchain.pem ssl/
   sudo cp -L /etc/letsencrypt/live/staging.<domain>/privkey.pem ssl/
   sudo chmod 600 ssl/privkey.pem
   ```

   With a commercial CA, `fullchain.pem` must contain the server certificate followed by the intermediates. Check the chain with `openssl verify -untrusted fullchain.pem fullchain.pem`.
3. **Renewal** goes through nginx's webroot (`./certbot` is mounted at `/var/www/certbot`), so nginx keeps running:

   ```bash
   sudo certbot renew --webroot -w /opt/hms/certbot \
     --deploy-hook 'cp -L $RENEWED_LINEAGE/fullchain.pem $RENEWED_LINEAGE/privkey.pem /opt/hms/ssl/ && cd /opt/hms && docker compose --env-file .env.production -f docker-compose.prod.yml exec nginx nginx -s reload'
   ```

   Run it from cron or a systemd timer twice a day. `scripts/deploy/verify_public.sh` fails when the certificate has fewer than 14 days left.
4. Let's Encrypt no longer publishes OCSP. With its certificates, nginx logs a harmless `ssl_stapling` warning.

## 5. Reverse proxy and trusted proxies

- The shipped layout terminates TLS in the `nginx` container and proxies directly to the backend, so `TRUSTED_PROXY_COUNT=1`. Django then reads the client address from the right-most `X-Forwarded-For` entry, which nginx appends. Rehearsed: repeated failed logins were limited after 5 attempts even with a different forged `X-Forwarded-For` on every request.
- Requests for any other host name (a bare IP, stale DNS) are dropped by nginx. Port 80 closes the connection and port 443 refuses the TLS handshake, so they never reach Django.
- **A cloud load balancer in front** changes this:
  - **L4 / TCP pass-through** (nginx still terminates TLS): nothing changes and `TRUSTED_PROXY_COUNT` stays 1. This is the recommended option.
  - **L7 / TLS-terminating** balancer or CDN: nginx would see plain HTTP and send `X-Forwarded-Proto: http`, so Django would redirect in a loop. That layout needs a reviewed nginx change (trust the balancer's `X-Forwarded-Proto` from its addresses only, `set_real_ip_from`) plus `TRUSTED_PROXY_COUNT=2`. It is **not** supported as shipped.
- Never set `TRUSTED_PROXY_COUNT` higher than the real number of proxies. Clients could then choose their own rate-limit and audit address.

## 6. Environment file

```bash
cp .env.production.example .env.production
chmod 600 .env.production
openssl rand -hex 40                    # DJANGO_SECRET_KEY
openssl rand -hex 24                    # POSTGRES_PASSWORD, REDIS_PASSWORD (separately)
openssl genrsa -out jwt_private.pem 2048 && openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
awk 'BEGIN{ORS="\\n"}1' jwt_private.pem # one-line value for JWT_PRIVATE_KEY (same for the public key)
python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"   # BACKUP_ENCRYPTION_KEY
shred -u jwt_private.pem jwt_public.pem # once they are in the env file / secret manager
```

- Use hex secrets. `$` is interpolated by Compose, and `@ : /` break `DATABASE_URL`.
- Store a copy of `BACKUP_ENCRYPTION_KEY` and the JWT keys **off the server** (password manager or secret manager). Without the backup key, the backups cannot be restored.
- Every variable is listed in §15.

Use this shell function in every command below. It passes the same file to Compose for interpolation:

```bash
dc() { docker compose --env-file .env.production -f docker-compose.prod.yml "$@"; }
```

## 7. Build and first start

```bash
export HMS_RELEASE=$(git rev-parse --short HEAD)   # image tag; keep the previous one for rollback
dc build
dc up -d
dc ps                     # all healthy (celery-beat: running)
dc logs -f backend        # migrations, then "Listening at: http://0.0.0.0:8000"
```

What happens, in order:
1. PostgreSQL and Redis start and become healthy.
2. The backend migrates (statement timeout lifted for this step only), loads the starter ICD-10 codes once, runs collectstatic, then starts gunicorn.
3. Its health check calls `/health/ready/` (database and cache).
4. Only then do the worker and beat start. Both log `RUN_MIGRATIONS is not true: skipping migrate`.

Rehearsed: a first start with 190 migrations was healthy in about 65 s on 4 vCPU.

Then create the first administrator and hospital (`DEPLOYMENT.md` §5).

## 8. Verification

On the server:

```bash
scripts/deploy/verify_host.sh
```

This checks:
- every service is healthy;
- `DEBUG=False`;
- mock AI providers are disallowed and none is registered;
- HTTPS redirect, Secure cookies, HSTS, dev sign-in off, no wildcard host;
- `manage.py check --deploy`;
- no unapplied migrations;
- only the backend has `RUN_MIGRATIONS=true`, and the worker and beat logs show migrate skipped;
- PostgreSQL and the backend are published on 127.0.0.1 only, and Redis not at all;
- Redis refuses clients without a password;
- logs rotate;
- `/health/ready/` reports database and cache healthy.

From a machine **outside** the server:

```bash
scripts/deploy/verify_public.sh staging.<domain>
```

This checks:
- the certificate verifies against the system CA store and has 14+ days left;
- TLS 1.0/1.1 is refused;
- HTTP redirects to HTTPS on the same name;
- HSTS, CSP, `X-Frame-Options: DENY`, `nosniff` and `Referrer-Policy` are sent on `/`, `/api/` and `/health/`;
- the nginx version is hidden;
- `/health/ready/` returns 200 and `/media/` returns 404;
- `/api/schema/` needs a sign-in;
- the login endpoint returns 4xx, not 5xx;
- unknown host names are dropped;
- 5432, 6379, 8000 and 5555 are closed.

A real staging pass runs this script **without** `HMS_CA_FILE`/`HMS_CONNECT_IP`. Those switches exist only for the local rehearsal, and the script labels such a run LOCAL.

Then the manual checks in §14 (sign-in with real OTP, e-mail, a browser pass).

## 9. Migrations and rollback

**Before every deploy**
1. `scripts/deploy/backup.sh create` (§11). Note the file name and the currently running `HMS_RELEASE`.
2. Build the new release under a new tag, then preview what it will migrate without migrating:

   ```bash
   dc run --rm --no-deps -e RUN_MIGRATIONS=false backend python manage.py migrate --plan
   ```

   `-e RUN_MIGRATIONS=false` matters: `dc run backend` otherwise inherits the backend's `RUN_MIGRATIONS=true` and would migrate.
3. Read the release notes in `DEPLOYMENT.md` (for example duplicate checks before constraint migrations).

**Deploy:** `dc up -d`. The backend migrates once, and the worker and beat restart on the same image. Web, worker and beat share one image (`hms-backend:$HMS_RELEASE`), so they cannot run different code.

**Rollback, from least to most invasive:**

| Situation | Action | Rehearsed |
|---|---|---|
| New release misbehaves, and it added **no** migrations (the preview said "No planned migration operations") | `HMS_RELEASE=<previous> dc up -d --no-build` | Yes: back to the previous image and healthy in 19 s |
| The release **added migrations** | With the new image still running, reverse them first: `dc exec backend python manage.py migrate <app> <last migration of the previous release>` for each app. Then `HMS_RELEASE=<previous> dc up -d --no-build` | Yes: all 36 migrations added since 2026-11-03 reversed and re-applied on PostgreSQL 16 with data, 0 failures |
| Data damaged, or a migration cannot be reversed | Restore the pre-deploy backup into a **new** database and switch to it (§13) | Yes: 52 s from data loss to recovered |

Caveats:
- Reversing a migration drops whatever it added. For example, reversing `terminology` to `zero` deletes the ICD-10 rows; the next backend start reloads the starter set.
- Reversing the "entered in error" migrations makes hidden records visible again (`DEPLOYMENT.md` §9).
- Take the backup first, every time.

## 10. Static and media files

- **Static:** the backend's collectstatic writes content-hashed names (`ManifestStaticFilesStorage`) into the `staticfiles` volume. nginx serves `/static/` from there with a one-year immutable cache. Nothing to do per deploy.
- **Media** (patient documents, consultation audio): stored in the `media` volume. Never served by nginx (`/media/` returns 404). Downloads go through `/api/documents/<id>/download/`, which checks access and audits. Included in every backup (`hms_media_*.tar.gz.enc`).
- Both volumes are named `<project>_staticfiles` / `<project>_media`, where the project is the folder name unless `COMPOSE_PROJECT_NAME` is set. **Never run `dc down -v`:** it deletes the database and media volumes.

## 11. Automated backups and restore verification

`scripts/deploy/backup.sh` needs only Docker. `pg_dump` runs in the postgres container, and encryption runs in a one-off backend container. It writes:
- `hms_backup_<UTC>.sql.gz.enc`: Fernet-encrypted, gzip, plain SQL. The same format as `backend/scripts/backup.py`.
- `hms_media_<UTC>.tar.gz.enc`: the media volume.

Without `BACKUP_ENCRYPTION_KEY` it refuses to run.

Cron (root or the deploy user, in `/opt/hms`):

```cron
BACKUP_DIR=/var/backups/hms
30 1 * * *  cd /opt/hms && scripts/deploy/backup.sh create        >> /var/log/hms-backup.log 2>&1
0  3 * * 0  cd /opt/hms && scripts/deploy/backup.sh restore-check "$(ls -t /var/backups/hms/hms_backup_*.enc | head -1)" >> /var/log/hms-backup.log 2>&1
15 2 * * *  cd /opt/hms && RETENTION_DAYS=30 scripts/deploy/backup.sh prune >> /var/log/hms-backup.log 2>&1
```

- `restore-check` restores the newest backup into a scratch database, `hms_restore_check`. It compares the table and migration counts with the live database, then drops the scratch database. The live database is never written. Rehearsed: 146 tables and 190 migrations matched, 2–4 s.
- **Off-host copy:** after `create`, copy the two new files to the hospital's chosen off-host storage (for example `rsync` to a backup server or `rclone` to object storage). The tool and destination are the hospital's choice and are not configured here.
- Alert on a missing or failed backup. The newest file should be less than 26 hours old (`OPERATIONS_RUNBOOK.md`).
- Once a month, do a full restore drill (§13) on a staging copy. Record how long it took.

## 12. Logging and monitoring

- **Container logs:** every service uses `json-file` with 20 MB × 5 rotation, read with `dc logs <service>`. nginx access logs carry `request_id` and upstream timing. gunicorn access logs go to stdout.
- **Django application logs:** JSON on stdout, and in the `app_logs` volume (`/app/logs/django.log` and `django_errors.log`, 10 MB × 10).
- **Health endpoints:**
  - `/health/live/` (process up);
  - `/health/ready/` (database and cache, 503 otherwise; the body shows only status words).
- **Monitoring to set up on the real host** (none exists yet; the hospital chooses the tools):
  1. An external uptime check on `https://staging.<domain>/health/ready/` every minute. Alert after 3 failures.
  2. A certificate-expiry alert (14 days), or run `verify_public.sh` daily from CI.
  3. Disk usage of `/var/lib/docker` and `/var/backups/hms`.
  4. Backup freshness (§11).
  5. Optional `SENTRY_DSN` with `SENTRY_ENVIRONMENT=staging`. Check that no patient data is sent before enabling it.
  6. Alerts on the 5xx rate in nginx logs and on the notification failure rate.

## 13. Restart, recovery and restore

| Event | What happens / what to do | Rehearsed |
|---|---|---|
| Host reboot | Docker starts on boot and `restart: unless-stopped` brings every service back in dependency order | Yes: healthy 61 s after a VM restart |
| Backend process exits | Docker restarts it | Yes: healthy again after 7 s |
| PostgreSQL restarts | Reused connections are health-checked (`CONN_HEALTH_CHECKS`), so no request fails | Yes: 12/12 requests 200 right after the restart. Before the fix, the first one returned 503 |
| Redis restarts | AOF keeps queued tasks; the app reconnects | Yes: 6/6 requests 200 |
| A bad release | §9 rollback table | Yes |
| `dc down` then `dc up -d` | Data and media persist (named volumes) | Yes |
| Restart one service | `dc restart <service>` (nginx: `dc exec nginx nginx -s reload` for config/cert changes) | — |

**Restore after data loss** (the live database is never overwritten):

```bash
dc stop backend celery-worker celery-beat
scripts/deploy/backup.sh restore /var/backups/hms/hms_backup_<UTC>.sql.gz.enc hms_prod_restored_<date>
# edit .env.production: POSTGRES_DB=hms_prod_restored_<date>
dc up -d
scripts/deploy/verify_host.sh
```

- The damaged database stays in place for investigation. Drop it later, deliberately.
- To restore media, decrypt the matching `hms_media_*.tar.gz.enc` and unpack it into the media volume. Do this only after checking what would be overwritten.
- Rehearsed: all 193 ICD-10 rows were deleted, restored into a new database and switched over. The app was back on the restored database in 52 s.

## 14. Staging checklist

Legend: **[L]** = passed in the local Docker rehearsal on 2026-11-18 (synthetic secrets, private CA, loopback); the real host must still repeat it. **[ ]** = needs the real host, real credentials or people.

**Host and network**
- [ ] Inputs in §2 obtained (staging domain, server, SMTP, Twilio or the decision to run without it, Google client id, off-host backup target)
- [ ] Host prepared (§3): firewall 22/80/443 only, time sync, Docker enabled at boot
- [ ] DNS record resolves from outside
- [ ] CA-signed certificate issued, renewal timer installed, and a renewal dry run passes (`certbot renew --dry-run`)

**Configuration**
- [ ] `.env.production` filled from §15, `chmod 600`, secrets also stored off-host
- [L] Compose refuses to start without `POSTGRES_PASSWORD`, `REDIS_PASSWORD` or `DOMAIN_NAME`
- [L] Production refuses a missing, short or development `DJANGO_SECRET_KEY`, a `*` host, invalid or mismatched JWT keys, and missing e-mail, Google or Twilio values

**Deploy**
- [L] `dc build` and `dc up -d` from an empty host: migrations run once in the backend only; worker and beat wait for it
- [L] `scripts/deploy/verify_host.sh`: all checks pass
- [L] `scripts/deploy/verify_public.sh`, LOCAL mode: all pass except certificate lifetime (the test certificate was made to expire in 2 days)
- [ ] `scripts/deploy/verify_public.sh staging.<domain>` from outside, **without** LOCAL switches: all pass, including closed ports
- [ ] SSL Labs (or `testssl.sh`) grade A or better

**Application, on the real host with real providers**
- [ ] First administrator and hospital created (`DEPLOYMENT.md` §5)
- [ ] Staff sign-in with real SMS OTP (or OTP deliberately off); patient e-mail OTP arrives
- [ ] Google sign-in works on the staging origin
- [ ] AI scribe with the chosen provider, or confirmed "unavailable" (503) without one; a mock provider is never used
- [ ] Browser pass of the staff and patient routes over HTTPS; no CSP errors in the console
- [ ] Two hospitals: no cross-hospital data

**Operations**
- [L] Backup create → verify → restore-check; wrong key refused; restore into a new database and switch-over
- [ ] Cron jobs installed; first off-host copy confirmed
- [ ] Monitoring and alerts from §12 set up and tested (stop the backend, see the alert)
- [L] Restart and recovery table in §13
- [L] Rollback: image tag switch, migration reversal on PostgreSQL
- [ ] Rollback rehearsed once on the real host
- [ ] Load test against staging (`LOAD_TEST.md`); p95 and error rate recorded

**People (outside engineering)**
- [ ] Clinical safety sign-off, penetration test, DPDP assessment (`KNOWN_LIMITATIONS.md`)

## 15. Environment variable checklist

R = required (start-up refuses without it), S = secret. "Checked by" names what enforces it.

| Variable | R | S | Staging value | Checked by |
|---|---|---|---|---|
| `DJANGO_SECRET_KEY` | R | S | `openssl rand -hex 40`, unique to staging | settings: present, 50+ chars, not `django-insecure` |
| `ALLOWED_HOSTS` | R | | `staging.<domain>` | settings: present, no `*` |
| `CORS_ALLOWED_ORIGINS` | R | | `https://staging.<domain>` | settings: present |
| `DOMAIN_NAME` | R | | `staging.<domain>` | Compose (`:?`) |
| `ADMIN_URL` | | | non-default path ending in `/` | — |
| `POSTGRES_USER`, `POSTGRES_DB` | | | defaults `hms_user`, `hms_prod` | — |
| `POSTGRES_PASSWORD` | R | S | `openssl rand -hex 24` | Compose (`:?`) |
| `REDIS_PASSWORD` | R | S | `openssl rand -hex 24`, different from the above | Compose (`:?`); `verify_host.sh` checks Redis refuses no-auth clients |
| `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` | R | S (private) | staging-only RS256 pair, one line with `\n` | settings: loads, RSA, pair matches |
| `JWT_ISSUER`, `JWT_AUDIENCE` | | | defaults | — |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | | | hospital SMTP | — |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | R | S | staging SMTP account | settings |
| `GOOGLE_CLIENT_ID` | R | | client id with the staging origin authorised | settings |
| `STAFF_LOGIN_REQUIRE_OTP` | | | `True` (or `False` until Twilio exists) | settings |
| `PATIENT_OTP_DELIVERY` | | | `sms` or `off` (dev modes refused) | settings |
| `OTP_PROVIDER` | | | `twilio` or `disabled` | settings |
| `TWILIO_ACCOUNT_SID`, `TWILIO_API_KEY`, `TWILIO_API_SECRET`, `TWILIO_VERIFY_SERVICE_SID` | R if SMS OTP on | S | staging Twilio sub-account | settings |
| `TWILIO_MESSAGING_SERVICE_SID`, `TWILIO_WHATSAPP_*`, `TWILIO_STATUS_CALLBACK_URL` | | S (SIDs) | optional reminders; callback `https://staging.<domain>/api/notifications/twilio/status/` | — |
| `AI_SCRIBE_ENABLED`, `AI_SCRIBE_API_KEY`, `AI_SCRIBE_LLM_BASE_URL`, `AI_SCRIBE_MODEL`, `AI_SCRIBE_STT_*` | | S (keys) | off, or a provider approved for patient audio | settings: mock providers always off |
| `FHIR_ENABLED`, `HL7_ENABLED`, `ABDM_ENABLED` | | | `False` | settings (extra values required when True) |
| `API_DOCS_PUBLIC` | | | `False` | — |
| `SECURE_SSL_REDIRECT` | | | `True` | `verify_host.sh` |
| `SECURE_HSTS_SECONDS` | | | `31536000` (nginx sends HSTS regardless) | `verify_host.sh` |
| `TRUSTED_PROXY_COUNT` | | | `1` for the shipped layout (§5) | — |
| `AUDIT_LOG_RETENTION_DAYS` | | | `0` until the retention policy is decided | — |
| `BACKUP_ENCRYPTION_KEY` | R for backups | S | Fernet key, stored off-host too | `backup.sh` refuses without it |
| `SENTRY_DSN`, `SENTRY_ENVIRONMENT` | | S (DSN) | optional; `staging` | — |
| `GUNICORN_WORKERS`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`, `CELERY_WORKER_CONCURRENCY` | | | 2 × vCPU workers; defaults otherwise | — |
| `HMS_RELEASE` | | | git short SHA, exported in the shell when building/deploying | — |
| `POSTGRES_HOST_PORT`, `BACKEND_HOST_PORT`, `HTTP_PORT`, `HTTPS_PORT` | | | defaults (5432, 8000, 80, 443); loopback-only for the first two | `verify_host.sh` |
| `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD` | | S | leave unset; create the admin interactively | entrypoint (backend only) |
