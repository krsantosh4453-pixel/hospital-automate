# Phase 3 plan: authentication and tenant context (proposal, awaiting approval)

Date: 2026-11-09. Builds on Phase 2 (`907df28`, `720a466`, pushed to `origin/ui/redesign-2026-10-25`).
Nothing in this document is implemented yet. [V] = verified in the code today; [A] = assumption.
Related: [implementation-roadmap.md](implementation-roadmap.md) · [target-system.md](target-system.md) · [risks-and-dependencies.md](risks-and-dependencies.md)

## 1. Audit of what exists

### 1.1 Sign-in and tokens

| Area | Today | Assessment |
|---|---|---|
| Staff sign-in | Password → `staff/login/` (refused when `STAFF_LOGIN_REQUIRE_OTP`, the production default) or password → signed challenge (`staff/login/otp/start/`) → Twilio Verify SMS code (`otp/verify/`); lockout counter per username [V] | Keep. The challenge is signed with a max age but not single-use; a stolen challenge only lets someone ask for another SMS within its lifetime [V] |
| Patient sign-in | Phone OTP (Twilio Verify), email OTP (keyed HMAC, 5-min TTL, attempt limit), email + password, Google [V] | Keep. No plaintext OTP is stored anywhere [V] |
| Token library | SimpleJWT 5.5: access 10 min / refresh 1 day in production, RS256, rotation + blacklist-after-rotation [V] | Keep |
| Token issuance | The same 6 lines are copied in 3 staff paths (`users/views.py` `_auth_response`, `staff_login`, `staff_otp_verify`); patients use `issue_login_tokens` [V] | Consolidate into one function |
| Claims | Staff access tokens carry `roles`, `hospitals`, `staff_role`; **nothing authorises from them** (every check reads memberships from the database on each request), and **a refreshed access token loses them** [V]. The web app reads roles from the sign-in response body, never from the token [V] | Remove the stale claims; keep the database as the only authority |
| Logout | Blacklists one refresh token [V] | No "sign out everywhere", no session list |
| Revocation | Password reset blacklists all outstanding refresh tokens [V]. Deactivating staff or removing memberships stops access on the next request (database check), but refresh tokens still mint access tokens that then fail permission checks [V] | Add session revocation on deactivation |
| Refresh-token reuse | A rotated (blacklisted) refresh token is refused, but nothing reacts to the reuse [V] | Treat reuse as theft: revoke the whole session |
| Devices | No device or session record [V] | New `DeviceSession` |

### 1.2 Tenant context and authorisation

- **Acting hospital** comes from `hospital` (body/query), the `hospital_id` URL kwarg or `X-Hospital-ID`, and is always intersected with the user's active memberships in active hospitals (`users/permissions.get_user_hospital_ids`). A forged id gives an empty scope [V].
- **Roles are per hospital** (`get_user_roles(user, hospital_id)`); the StaffProfile role grants nothing [V]. Gap: `get_user_roles(user)` *without* a hospital still counts roles held in **suspended** hospitals (`hospital.is_active=False`) [V]; it feeds `user_has_role` / `user_has_any_role`.
- **Module restrictions** per hospital and role (`RoleModuleRestriction`) [V]; care scope for doctors and nurses; break-glass [V].
- **Endpoint coverage** (144 view classes [V]):
  - 118 build on `HospitalScopedViewSet` / `ReadOnlyHospitalScopedViewSet`, directly or through `_OrgStructureViewSet`, `_ServiceViewSet`, `_SignedByDoctorViewSet` and `_AppendOnly` [V].
  - 26 are hand-written `APIView`/`ViewSet` classes, plus 28 function views. Each does its own membership check (ABDM, FHIR, consent, documents, reports, staff admin/invite, home, break-glass) or is deliberately global (health, schema, CSRF, public hospital directory, report templates, Twilio webhook) [V by reading the scoping calls; **not yet proven by a test for every one**].
  - Existing tests: tenant isolation, role matrix, RBAC/writes and read-role suites (47 tests) [V]. They cover the main modules, **not every endpoint**.
- **Platform administrator** is Django `is_superuser`, checked in 9 places (`hospital/views.py` ×5, `notifications/views.py` `IsPlatformAdmin`, `reports/views.py` `IsTemplateEditor`, API docs) [V]. A superuser sees and edits every hospital row. Scoped viewsets give a superuser **no** patient data unless they hold a membership [A, to be locked in by a test].
- **Hospital onboarding**: an Admin account with no hospital (registered with the admin invitation code) can create a hospital and becomes its Admin (`hospital/views.can_add_hospital`) [V].

## 2. Design

### 2.1 Token and session lifecycle (reuses SimpleJWT, no new library)

1. **One issuing function**, `users/tokens.py: issue_session_tokens(user, request, account_type, device=None)`, used by every sign-in path (staff password, staff OTP, patient OTP/email/password/Google, proxy). It creates a `DeviceSession` and puts its id in a `sid` claim on both tokens. Access tokens carry only `user_id`, `sid`, `account_type`, `jti` and `exp`: no roles or hospitals.
2. **Refresh** (`auth/token/refresh/`, cookie and body modes unchanged): rotation and blacklist stay. In addition, the session must be active, the user active, and staff still active staff. The session's `last_used_at` and current `jti` are updated.
3. **Reuse detection**: presenting a refresh token that was already rotated revokes the whole session (all its outstanding tokens are blacklisted) and writes `auth.refresh_reuse` to the audit log.
4. **Access-token check**: `CookieJWTAuthentication` refuses an access token whose `sid` is revoked, so revocation takes effect at once instead of after up to 10 minutes. The revoked-session set is cached in Redis: one cache read per request, the database on a miss [A: measured in Phase 11].
5. **Revocation triggers**: logout (this session), logout-all, revoking one session, password change/reset (all sessions), staff deactivated or last membership removed (all sessions), a platform admin suspending a hospital (sessions of staff whose only hospital it was).
6. Tokens issued before the deploy have no `sid`. They keep working until they expire (at most 1 day for refresh) and are then replaced. Nobody is forced to sign out.

### 2.2 OTP hardening (no change of provider)

- The staff OTP challenge becomes **single use**: a nonce in the challenge is consumed on successful verification (cache, TTL = challenge lifetime).
- Uniform responses for unknown phones and emails are kept and covered by tests (no account enumeration).
- Mobile OTP endpoints are the existing ones under `/api/v1/auth/patient/otp/*` and `/api/v1/auth/staff/login/otp/*`. They gain OpenAPI request/response schemas (the Phase 2 gap).

### 2.3 Tenant context

- `GET /api/v1/auth/me/contexts/` returns what the signed-in account may act as:
  - staff: one entry per active membership in an active hospital: `{hospital: {id, name}, role, department, permissions: [...], restricted_modules: [...]}`;
  - patient: the hospitals they are registered at;
  - `platform_role` when the user is platform staff.

  The mobile app uses it for the hospital/role picker. The web app may use it later; no web change is needed now.
- The acting hospital stays `X-Hospital-ID`. **Writes** to hospital-scoped endpoints by a user with more than one hospital must name the hospital. Today `_check_tenancy` already requires this for most models [V]; the test matrix below will prove it for all.
- Fix `get_user_roles(user)` to ignore suspended hospitals.

### 2.4 Role- and permission-based authorisation

- **Keep** the role classes (`IsAdmin`, `IsDoctor`, …), per-hospital roles, module restrictions and care scope. No rewrite.
- **Add a code-defined permission catalogue**, `users/role_permissions.py`: named permissions (`appointments.book_for_patient`, `prescriptions.write`, `billing.collect_payment`, `staff.manage`, …) mapped to the existing roles and narrowed by `RoleModuleRestriction`. It is the source for `me/contexts.permissions` and for a `HasHospitalPermission("…")` class used by new Phase 3+ endpoints. Existing endpoints keep their current classes; they can migrate one by one, each with its own tests.
- **Decision P3-A (needs your approval):** the brief lists `roles`, `permissions` and `membership_roles` tables. I recommend the code-defined catalogue for now. The current roles are fixed by clinical-safety rules, and editable permission tables would let a hospital grant, for example, prescribing to a receptionist. Editable roles can come later on top of the catalogue.

### 2.5 Platform administration (Decision B, approved)

- New `PlatformStaff` model: user one-to-one, `role` = `platform_admin` | `platform_support`, `is_active`, timestamps.
- A data migration creates a `platform_admin` row for each existing active superuser, so nobody loses access. Reversible.
- Replace the 9 `is_superuser` checks with `is_platform_admin(user)`. Django's own admin site keeps using `is_superuser`/`is_staff`.
- Platform staff get tenant-level data (hospital list, status, counts) and **no patient data** unless they also hold a hospital membership. A test locks this in.
- Hospital creation stays as today (an Admin account creates its hospital). Platform-controlled onboarding and subscriptions are left for the admin phase.

### 2.6 Tenancy guard for every endpoint (requirement 8)

1. **Static contract test**: it walks every resolved URL. Each DRF view must be a `HospitalScopedViewSet`/`ReadOnlyHospitalScopedViewSet` subclass **or** be listed in `config/tenancy_exemptions.py` with a written reason and category (`auth`, `public`, `platform`, `patient-self`, `own-checks`, `infrastructure`). A new endpoint that is neither fails CI.
2. **Dynamic cross-hospital matrix**: for every scoped list/detail endpoint, `security_tests/factory.py` seeds a row in Hospital B. An Admin of Hospital A then calls the endpoint:
   - with no header, with `X-Hospital-ID: A`, with `X-Hospital-ID: B`, and with `?hospital=B`;
   - expected: B's row never appears, B's id gives 404 on detail, and a write naming hospital B gives 403/400 and creates nothing.
3. **Hand-written views in the `own-checks` category** each get an explicit negative test (ABDM, FHIR, consent, documents, reports, staff admin/invite, home, break-glass).

## 3. Affected files

| File | Change |
|---|---|
| `backend/users/models.py` | `DeviceSession`, `PlatformStaff` |
| `backend/users/migrations/0006_*.py`, `0007_*.py` | Create both tables; copy active superusers into `PlatformStaff` (additive) |
| new `backend/users/tokens.py` | One token-issuing path, `sid` claim, session refresh and reuse handling |
| new `backend/users/sessions_views.py` | `sessions/`, `sessions/{id}/revoke/`, `logout-all/`, `me/contexts/` |
| new `backend/users/role_permissions.py` | Permission catalogue, `HasHospitalPermission` |
| `backend/users/views.py` | Use `tokens.issue_session_tokens` in the 3 staff paths; logout revokes the session |
| `backend/users/patient_auth.py`, `backend/users/proxy_views.py` | Same issuing function |
| `backend/users/security.py` | Single-use OTP challenge |
| `backend/users/permissions.py` | `is_platform_admin`; suspended hospitals ignored in `get_user_roles(user)` |
| `backend/users/urls.py` | New routes (also under `/api/v1/`) |
| `backend/config/auth_cookies.py`, `backend/config/auth_cookie_views.py` | Revoked-session check; refresh through the session |
| `backend/hospital/views.py`, `backend/notifications/views.py`, `backend/reports/views.py`, `backend/config/schema.py` | `is_superuser` → `is_platform_admin` |
| new `backend/config/tenancy_exemptions.py` | Classified non-scoped endpoints |
| `backend/users/staff_admin.py` | Revoke sessions on deactivation or removal of the last membership |
| new tests | See section 6 |
| `docs/API_DOCUMENTATION.md`, `docs/architecture/*` | Updated |

Not touched: the React frontend (none of its contracts change), and billing, clinical, pharmacy and the other modules, apart from the `is_superuser` lines named above.

## 4. Database changes (all additive, no data removed)

| Table | Columns | Notes |
|---|---|---|
| `users_devicesession` | `id` UUID PK, `user_id` FK, `account_type`, `device_id` (client-supplied, ≤ 64), `platform` (web/android/ios/other), `app_version`, `user_agent` (≤ 200), `ip_prefix` (/24 or /48, not the full address), `current_jti`, `created_at`, `last_used_at`, `revoked_at`, `revoked_reason` | Index `(user, revoked_at)`. Retention: rows deleted 90 days after revocation by the existing Celery beat |
| `users_platformstaff` | `id`, `user_id` one-to-one, `role`, `is_active`, `created_at`, `updated_at` | Data migration from active superusers |

No column is dropped or renamed, and no existing table is rewritten. Both migrations are reversible.

## 5. API changes (all under `/api/v1/` and `/api/`)

| Method | Path | Purpose |
|---|---|---|
| GET | `auth/me/contexts/` | Hospitals, roles and permissions the account may act with |
| GET | `auth/sessions/` | The user's own active sessions (device, platform, last used; current one marked) |
| POST | `auth/sessions/{id}/revoke/` | Sign out one device |
| POST | `auth/logout-all/` | Sign out everywhere |
| (changed) | all sign-in responses | Same body as today. Tokens now carry `sid` and no role/hospital claims. Optional `device_id`, `platform`, `app_version` in the request body |
| (changed) | `auth/token/refresh/` | Same request and response. Refused for revoked sessions, inactive users and inactive staff; reuse revokes the session |
| (changed) | `auth/staff/logout/` | Also revokes its session |

OpenAPI schemas are added for all sign-in, OTP, refresh, logout, session and context endpoints.

## 6. Security test cases (written before the implementation)

**Tokens and sessions**
1. A refreshed access token carries `sid`, and no `roles` or `hospitals` claims.
2. Reusing a rotated refresh token gives 401, and the session's other tokens stop working.
3. Revoking a session: its access token is refused on the next request (not after 10 minutes); other sessions keep working.
4. Logout-all: every session is refused; signing in again works.
5. Deactivated staff: refresh refused, access refused.
6. Removing a user's last membership revokes their sessions.
7. Password reset revokes all sessions (regression).
8. A user cannot list or revoke another user's session (404).
9. Tokens without `sid` (issued before the deploy) still work until they expire.

**OTP**
10. A staff OTP challenge cannot be used again after a successful sign-in.
11. An expired challenge, an expired email OTP and too many attempts are all refused (regression).
12. An unknown phone or email gets the same response as a known one.
13. No OTP value appears in the database, logs or audit rows (searched by value after a run).

**Tenant context and roles**
14. `me/contexts` lists only active memberships in active hospitals; a suspended hospital disappears and its role stops counting anywhere.
15. An Admin of A who is a Receptionist of B has only Receptionist permissions with `X-Hospital-ID: B`.
16. A permission removed by a module restriction is missing from `me/contexts` and refused by `HasHospitalPermission`.

**Cross-hospital isolation (negative)**
17. Static contract: every endpoint is scoped, or classified with a reason.
18. Matrix over every scoped list/detail endpoint (section 2.6): B's rows are never visible to A's Admin with any header or query combination; detail gives 404; writes naming B are refused and create nothing.
19. Explicit negative tests for each `own-checks` view (ABDM, FHIR, consent, documents, reports, staff admin/invite, home, break-glass).
20. A patient of A cannot read appointments, prescriptions, bills or documents of a patient of B, nor book at B.
21. A family-access (proxy) login sees only its patient and stays read-only under both prefixes (regression).

**Platform administration**
22. Existing superusers keep platform access after the migration.
23. Platform staff without a membership get hospital rows but **no** patient, clinical or billing rows.
24. A hospital Admin cannot reach platform-only actions (delete a hospital, the OTP log, template edits).

**Regression**
25. Full backend suite on PostgreSQL, with row-lock tests required.
26. Web: the Vitest unit tests and the Playwright E2E sign-in and appointment journeys against a local stack (not run since Phase 1; will be run and reported).

## 7. Order of work after approval

1. The tests from section 6 that can fail today, written failing-first in the working tree (never pushed red).
2. Token/session layer (2.1) and OTP challenge (2.2).
3. Platform staff (2.5).
4. Contexts and permission catalogue (2.3, 2.4).
5. Tenancy guard and matrix (2.6), fixing any endpoint the matrix catches.
6. Full backend suite, web Vitest and Playwright, code review, docs; one commit per step.

## 8. Risks and open points

- **The matrix may find leaks** in hand-written views. They will be fixed in this phase and listed in the report.
- **The per-request session check** adds one cache read per request; it gets measured in Phase 11.
- **Twilio Verify is still untested with real credentials** (L2). The OTP tests use the existing test doubles.
- **Web E2E** needs the local dev stack. If it can't run on this machine, the report will say so instead of claiming a pass.
- **RLS** (Decision D) stays out of this phase.
- **Decision P3-A** (a code-defined permission catalogue instead of editable permission tables) needs your answer.
