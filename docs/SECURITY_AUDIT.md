# Security Audit

Date: 2026-10-25 (updated the same evening by a second audit; see "Fixed in the second audit"). Scope: Django API, React client, nginx, Docker Compose and dependencies.

`SECURITY_AUDIT_CHECKLIST.md` is the deployment checklist; this file records what was found, what was fixed and what remains open.

## Fixed (with tests)

| # | Severity | Finding | Fix | Test |
|---|---|---|---|---|
| 1 | Critical | 25 endpoints returned another hospital's records; scoping fell back to "unscoped" and used patient memberships | Fail-closed scoping by the owning-hospital path; hospital columns plus backfill | `test_tenant_isolation` (67 models, list and detail, with and without `?hospital=`) |
| 2 | Critical | Any staff user could create, edit or delete any hospital, ward, bed or department | Hospital create/delete for superusers only; structure writes for that hospital's Admin/Manager | `test_rbac_and_writes` |
| 3 | Critical | Related ids from another hospital accepted on write; queue `issue` looked up the appointment unscoped | `_check_tenancy` on every scoped write; scoped lookup | `test_rbac_and_writes`, `test_e2e_workflows` |
| 4 | High | A role held in one hospital applied in all of them; the profile role also granted access | Roles taken from the membership in the acting hospital; object-level role check | `RolePerHospitalTests` |
| 5 | Critical | Staff OTP verify and resend accepted a bare `user_id` (the SMS code alone was enough) | Signed 10-minute challenge from the password step | `test_auth` |
| 6 | High | `/api/auth/token/` issued tokens with no staff checks | Removed | `test_auth` |
| 7 | High | No lockout; no password reset | 5 failures → 15-minute lock; OTP reset that revokes refresh tokens and doesn't reveal whether an account exists | `test_auth` |
| 8 | Critical | AI mock providers produced fabricated clinical text in production | Mocks only when `AI_SCRIBE_ALLOW_MOCK_PROVIDERS` (never in production); otherwise 503; mock drafts can't be approved | `test_ai_scribe_safety` |
| 9 | Critical | AI drafts could be approved via PATCH | Workflow fields read-only; approval needs a linked doctor at that hospital | `test_ai_scribe_safety` |
| 10 | Critical | Patient documents and audio publicly served by nginx `/media/` | `/media/` returns 404; files only via an authenticated, scoped and audited API | `test_documents` (API); nginx config by review |
| 11 | High | Document access granted to any staff when the patient had no direct hospital; downloads never JWT-authenticated | DRF views scoped by the document's hospital | `test_documents` |
| 12 | High | Upload type checked only by extension on one path | Content sniffing (`python-magic`) on both upload paths; non-inline types forced to download | `test_documents` |
| 13 | High | nginx reflected any `Origin` with credentials and dropped security headers on API responses | Removed; Django `CORS_ALLOWED_ORIGINS` is authoritative | Review |
| 14 | High | Lab results editable through PATCH; visible to patients before verification | Read-only status and result; patients see Released results only | `test_e2e_workflows` |
| 15 | High | Money client-writable; payments editable and deletable | Server-side Decimal billing; append-only payments | `test_financial_integrity` |
| 16 | Medium | Procurement lists answered anonymous requests | Authentication required | procurement tests |
| 17 | Medium | Malformed `?hospital=` caused a 500 | Validated (400) | `test_tenant_isolation` |
| 18 | Medium | Admin invite code compared non-constant-time | `hmac.compare_digest` | Review |
| 19 | Medium | Prescriptions with patient names cached in localStorage | Cache removed and cleared | Review |
| 20 | Medium | No audit trail written at all | `record_audit` plus automatic auditing of all scoped writes (old → new values) | `AuditTrailTests` |
| 21 | Medium | OTP rows (phone numbers) visible to any hospital admin | Platform superusers only | Review |
| 22 | Medium | Backup restore left a decrypted copy on disk | Private temporary directory, always removed | Manual PostgreSQL run |
| 23 | Medium | Vulnerable dependencies: gunicorn 21, cryptography 45, pytest 7, vite 8.2.0–8.2.2, source-map-js | Upgraded; `pip-audit` and `npm audit` clean | Audit runs |
| 24 | Low | Patient-OTP, registration and password-reset routes had no rate-limit rules | Rules added to the rate-limit middleware | Review |

## Fixed in the second audit (2026-10-25, evening)

Each fix has a regression test that failed before the fix. Ids refer to `DEFECT_REGISTER.md`.

| # | Severity | Finding | Fix | Test |
|---|---|---|---|---|
| 25 (D-01) | Critical | Deleting a patient in Hospital A cascaded into Hospital B's visits, prescriptions, labs and invoices | Delete refused (409) when the patient is registered at, or has records in, another hospital | `PatientDeleteTests` |
| 26 (D-02) | High | List requests without an acting hospital used the union of roles across hospitals (a Receptionist in B listed B's vitals via a Doctor role in A) | Lists cover only hospitals where the view's permissions pass for the role held there | `RolePerHospitalTests` |
| 27 (D-03) | High | Report templates readable and writable by any authenticated account, including patients; schedules movable to foreign hospitals; cross-hospital recipients; 500 on missing hospital | Templates: staff read, superuser write; hospital validated on create and update; recipients restricted to that hospital's staff | `test_reports_access` |
| 28 (D-05) | High | A staff member with a linked patient record skipped password + OTP through the patient login routes, then acted as staff | Patient token routes refuse staff accounts | `test_auth` |
| 29 (D-06) | High | Staff Google sign-in without password or OTP | Fixed by the owner before this audit; verified | `test_auth` |
| 30 (D-04) | High | Notification providers recorded unsent SMS/WhatsApp/voice/email as delivered and logged message bodies (PHI) at INFO | Email really sent; unimplemented channels fail honestly; logs carry ids only | `ProviderHonestyTests` |
| 31 (D-08) | Medium | Rate limits, DRF throttles, the audit IP and IP allow-lists trusted a client-supplied `X-Forwarded-For` | `TRUSTED_PROXY_COUNT` (1 behind nginx) and DRF `NUM_PROXIES`; one shared helper | `test_client_ip` |
| 32 (D-09) | Medium | Django sent no CSP header in production (django-csp 4 ignores `CSP_*`) | `CONTENT_SECURITY_POLICY` with the intended directives | `test_settings_loading` |
| 33 (D-11) | Medium | Patient and appointment rows left in `localStorage` after logout on shared PCs; timeouts saved duplicate records locally | Cleared on logout and session expiry, in storage and memory; timeouts no longer trigger local saves | `apiSession.test.js` |

## Verified controls

- DRF default is `IsAuthenticated`.
- JWT: access 15 minutes, refresh 7 days, rotation and blacklist. Production uses RS256 keys from the environment.
- Production settings refuse to start without `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DATABASE_URL`, JWT keys, email credentials, Twilio Verify and `REDIS_URL`. HTTPS redirect, HSTS (1 year), secure cookies and `X-Frame-Options: DENY` are set.
- No real secrets are tracked in git. `.env` is ignored; `.env.example` and `.env.production.example` contain placeholders only (checked). `backend/db.sqlite3` is no longer tracked, though it remains in git history.

## Open items (not fixed)

Current list with ids and next actions: `DEFECT_REGISTER.md` ("Remaining"). It adds:

- R-03: clinical hard deletes, and single-hospital patient delete by non-admin roles.
- R-06: SMS/WhatsApp/Voice not implemented.
- R-07: non-viewset endpoints not re-checked for the role-union pattern.
- R-08: UHID uniqueness, unsalted email OTP hash.
- R-09 to R-14: static storage, CI pinning, public API docs, code quality, offline cache, dev auth bypass.

| Severity | Item | Why open / action |
|---|---|---|
| High | Access and refresh tokens are kept in `localStorage`, so any successful XSS exposes the session | Moving to httpOnly cookies needs CSRF handling and a coordinated frontend change. Mitigations: React escaping; nginx CSP. CSP still allows `'unsafe-inline'` scripts — tighten after removing inline scripts. |
| High | `backend/db.sqlite3` remains in git history | Purge with `git filter-repo` before publishing the repository, if it ever held real data |
| Medium | Self-registration: Admin accounts can be created with `ADMIN_INVITE_CODE`, and pending staff are visible to every hospital's admins | Prefer invite-only staff creation per hospital |
| Medium | Development logging prints SQL with parameters, which would put patient data into logs | Development only; production logging is WARNING with JSON output. Do not use development settings with real data. |
| Medium | No sensitive-read audit for list endpoints (only writes, downloads and consent reads are audited) | Add read auditing for clinical detail views if required by policy |
| Medium | Staff `X-Hospital-ID` is trusted only after a membership check, but there is no hospital "break-glass" emergency access workflow | Define the policy first, then implement it with an audit trail |
| Low | DRF browsable API enabled in development | Production uses JSON-only renderers |

## External / organisational

- Penetration testing, a DPDP Act (India) privacy assessment, and ABDM certification were not performed and require qualified reviewers.
- Twilio, the AI providers and Google OAuth need real credentials. Their failure paths are tested; their success paths are mocked.
