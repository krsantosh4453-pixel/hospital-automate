# Current system (as built, 2026-11-09)

[V] = verified in code or config today. [A] = taken from an earlier report, not re-run.
Related: [repository-audit.md](repository-audit.md) · [target-system.md](target-system.md)

## 1. Shape

```
Browser (React 19 SPA) ──HTTPS──> nginx ──> gunicorn (Django 6 + DRF) ──> PostgreSQL 16
                                    │              │
                                    │              ├──> Redis (cache, sessions, rate limits, Celery broker)
                                    │              └──> Celery worker + beat (notifications, audit retention)
                                    └──> /static (built SPA), /media blocked
```

It is already a **modular monolith**: one Django project, 30 apps, one database, one deployable [V]. There are no microservices.

## 2. Request flow and tenancy

1. **Authentication**: `config.auth_cookies.CookieJWTAuthentication` accepts an `Authorization: Bearer` access token first, and otherwise reads the httpOnly access cookie and enforces CSRF. The browser opts into cookies with `X-Auth-Mode: cookie`; any other client gets tokens in the JSON body [V]. **A mobile client can use bearer tokens today without backend changes.**
2. **Acting hospital**: `users.permissions.get_request_hospital_id` reads it from the `hospital` body field, `?hospital=`, the `hospital_id` URL kwarg, or the `X-Hospital-ID` header [V].
3. **Membership check**: `HospitalScopedViewSet.get_acting_hospital_ids` intersects the acting hospital with `get_user_hospital_ids(user)` (active `StaffHospitalMembership` rows). An acting hospital the user does not belong to gives an empty scope, not another hospital's data [V].
4. **Role per hospital**: `get_user_roles(user, hospital_id)` returns the roles the user holds **in that hospital**, so a doctor in hospital A who is a receptionist in B has only receptionist rights while acting in B [V].
5. **Module restrictions**: `RoleModuleRestriction` lets a hospital admin narrow a role per module (view-only or none) [V].
6. **Care scope**: doctors and nurses see only patients in their care (`users/care_scope.py`); break-glass access is time-limited, audited and signed off [V].
7. **Sensitive-read audit**: every staff list/detail read of patient data writes an audit row [V].
8. **Patients** are linked to hospitals through `PatientHospital` (one UHID per hospital, unique per hospital ignoring case) [V].

Tenant isolation is enforced in the API layer only. **There is no PostgreSQL Row-Level Security** [V].

## 3. Authentication flows

| Who | Flow | Where |
|---|---|---|
| Staff | Username/password, then SMS OTP (Twilio Verify) when required by settings; invite link to set a password; password reset | `users/views.py`, `users/twilio_verify.py`, `users/staff_invite.py` |
| Patient | Phone OTP (Twilio Verify, rate-limited per phone and per IP), email OTP (keyed HMAC, 5-minute TTL, attempt limit), email + password, Google sign-in | `users/patient_auth.py` |
| Family/proxy | OTP-verified proxy access with grants the patient can revoke | `users/proxy_access.py`, `users/proxy_views.py` |
| Development | `dev/login/`, front-end bypass only when `VITE_DEV_AUTH_BYPASS=true` | `users/dev_login.py` |

Tokens: SimpleJWT, RS256 in production, access 10 min / refresh 1 day in production (15 min / 7 days in base), refresh rotation and blacklist-after-rotation on [V]. Throttles: login 5/min, OTP 3/min (scoped), user 3,000/h and anon 100/h in production [V; figures A from `LOAD_TEST.md`].

Platform super-admin is Django `is_superuser`, checked in 7 places (`hospital/views.py`, `notifications/views.py`, `reports/views.py`) [V]. There is no separate platform role.

## 4. Data model highlights

- About 150 models, integer `BigAutoField` keys [V].
- Tenant ownership: most clinical and financial models carry a `hospital` FK with `(hospital, …)` indexes [V]. Rows a past backfill could not assign stay invisible until `manage.py assign_tenant_hospital` assigns them [A].
- Constraints already in the database [V]:
  - `appointment_unique_active_slot`: one active booking per **patient + doctor + date + time**.
  - `unique_invoice_number_per_hospital`, per-hospital, per-financial-year invoice sequences.
  - `unique_uhid_per_hospital`, `one_uhid_sequence_per_hospital_year`.
  - `doctor_unique_user_per_hospital`.
  - `Payment.amount > 0`, `Invoice.total >= 0`, and a unique constraint on payment idempotency.
- Soft delete: "entered in error" (`EnteredInError` base, `all_objects` manager) [V].
- Row locks: UHID issue, queue token issue, IPD bed allocation and patient self-booking use `select_for_update` [V].

## 5. Appointment booking (patient self-booking)

`AppointmentViewSet` checks the patient is registered at the doctor's hospital, the slot is in the future and within 30 days, and the patient has fewer than the maximum number of upcoming bookings. It then locks the doctor's existing appointments for that day and rejects a taken slot with HTTP 409 [V].

**Fixed 2026-11-09 (Phase 2):** the lock used to cover only that day's existing appointment rows. On a day with no appointments nothing was locked, and a PostgreSQL test with 8 parallel patients reproduced 3 of them getting the same slot. Booking now locks the doctor row, and the test gets exactly one 201 and seven 409s. The endpoint also accepts an `Idempotency-Key` header (see section 4 of [risks-and-dependencies.md](risks-and-dependencies.md)).

Doctor availability is a weekly `DoctorSchedule` (day, start, end, available). There is no slot table, slot length or capacity per slot [V].

## 6. Background jobs and integrations

- Celery tasks: `notifications.tasks.send_notification_channel` (5 retries, exponential backoff, every attempt logged) and audit retention [V].
- Notification providers: in-app and console work; SMS, WhatsApp and voice are stubs until credentials are set [V].
- Push (FCM/APNs): settings only, no code [V].
- Payments: manual entry only, no gateway, no webhook endpoint [V].
- AI: doctor scribe (STT + LLM draft, doctor must review) and AI discharge draft; OpenAI provider or a development stub [V].

## 7. Deployment, quality and performance

- Docker Compose production stack, rehearsed locally with a self-signed certificate; not yet on a real staging host [A, `KNOWN_LIMITATIONS.md` L1].
- Media files live on the local filesystem volume (`FileSystemStorage`); no object storage or signed URLs [V].
- CI runs lint, unit and E2E tests and PostgreSQL row-lock tests [V].
- Load test (2026-11-08, local): 162 req/s, p95 368 ms, 0 errors with 50 clients and 4 sync gunicorn workers [A, `LOAD_TEST.md`]. This is evidence for a few hundred staff on one host, **not** for 10,000+ concurrent users.

## 8. Open release blockers already on record

From `docs/KNOWN_LIMITATIONS.md` [A]: L1 staging rehearsal, L2 real provider credentials, L4 clinical safety review, L5 penetration test and DPDP assessment. The mobile programme adds to these and does not replace them.
