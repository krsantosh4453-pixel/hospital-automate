# Target system (proposal, awaiting approval)

Status: **proposal**. Nothing here is built yet. Items marked **DECISION** need the owner's approval before work starts.
Related: [current-system.md](current-system.md) · [implementation-roadmap.md](implementation-roadmap.md) · [risks-and-dependencies.md](risks-and-dependencies.md)

## 1. Principles

1. **Evolve the existing Django modular monolith.** It already has the modules, tenancy layer and tests. No FastAPI rewrite, no microservices, no second database.
2. **One API for web and mobile.** The Flutter app calls the same DRF endpoints as the React app. It never talks to PostgreSQL, and business rules stay on the server.
3. **Additive, reversible changes only.** New tables and nullable columns first; nothing renamed or dropped without a migration plan and approval.
4. **Evidence before claims.** Capacity figures come from load tests, not from the architecture.

## 2. Module map: requested modules against existing apps

| Requested module | Existing app(s) | Gap |
|---|---|---|
| Authentication | `users` (patient OTP, staff OTP, JWT, cookies) | Device/session list, mobile refresh handling, logout-all |
| Users, Memberships & Permissions | `users` (`StaffProfile`, `StaffHospitalMembership`, permission classes), `hospital.RoleModuleRestriction` | Explicit platform-admin role; membership switching endpoint for mobile |
| Hospital & Tenant Management | `hospital` | Tenant status (active/suspended/trial), subscription plan, onboarding flow |
| Patient Management | `patients` | None for mobile v1 |
| Doctor Management | `doctors` | Public doctor profile fields for discovery |
| Department Management | `hospital.Department` | None |
| Appointments, Doctor Schedules | `appointments`, `encounters.DoctorSchedule` | Slot generation, slot-level locking, idempotent booking |
| Medical Records, Prescriptions | `clinical`, `documents`, `patients.timeline` | Patient-safe read endpoints for mobile (reuse timeline) |
| Billing, Payments | `billing` | Payment gateway, webhooks, gateway idempotency |
| Pharmacy, Inventory | `pharmacy`, `procurement` | None for mobile v1 (staff web only) |
| Notifications | `notifications` | Push provider (FCM/APNs) and device tokens |
| AI Chatbot | none | New, patient-facing, non-diagnostic, Phase 9 |
| AI Voice Agent | `ai_scribe` (doctor dictation), `notifications.voice` (call fallback) | Mobile audio upload to the existing scribe; patient voice agent is a later decision |
| Reports & Analytics | `reports`, `home` | Mobile summary endpoints |
| Audit Logging | `audit` | None |

## 3. API strategy

- **DECISION A — versioning.** Mount the existing URLconf a second time at `/api/v1/` (same views, no copies). The web app moves to `/api/v1/` at its own pace and `/api/` is retired later. Breaking changes go to `/api/v2/` only.
- Keep the conventions already in use: DRF `PageNumberPagination` (50 per page), `config.exceptions.custom_exception_handler` for errors, `Idempotency-Key` header (already allowed by CORS), `X-Hospital-ID` for the acting hospital, OpenAPI from drf-spectacular.
- Generate the Dart API client from the OpenAPI schema. That needs the ~240 schema warnings reduced for the endpoints mobile uses.
- New endpoints, only where nothing exists:
  - `GET /api/v1/auth/me/contexts/` lists the user's hospitals and roles in each, for the role/hospital switcher.
  - `POST /api/v1/devices/` and `DELETE /api/v1/devices/{id}/` register and remove push tokens.
  - `GET /api/v1/auth/sessions/`, `POST /api/v1/auth/sessions/{id}/revoke/` and `POST /api/v1/auth/logout-all/`.
  - `GET /api/v1/appointments/slots/?doctor=&date=` returns free slots computed from `DoctorSchedule`.
  - `POST /api/v1/payments/orders/` and `POST /api/v1/payments/webhooks/{provider}/`, in Phase 8.

## 4. Authentication and tenant context for mobile

- Mobile uses **bearer tokens** (no `X-Auth-Mode: cookie`). The access token is held in memory and the refresh token in `flutter_secure_storage` (Keychain / Android Keystore). The backend already returns tokens in the body for non-cookie clients and accepts `refresh` in the body.
- Keep SimpleJWT rotation and blacklist. Add a `DeviceSession` row per sign-in (device id, platform, app version, refresh `jti`, last seen, revoked at), so users and admins can list and revoke sessions.
- OTP: reuse Twilio Verify for phone, and the HMAC email OTP. Never store a plaintext OTP; Twilio holds the SMS code.
- Acting hospital: the app sends `X-Hospital-ID` after the user picks a context. The server validates it on every request, as now. The client is never trusted.
- **DECISION B — platform super-admin.** Replace scattered `is_superuser` checks with an explicit `PlatformStaff` model (roles: `platform_admin`, `platform_support`). It has its own endpoints under `/api/v1/platform/`, is never a hospital membership, and gets no patient data by default. Super-admin screens ship in the web app first; mobile gets read-only tenant status at most.

## 5. Database changes (all additive)

| Change | Why | Risk |
|---|---|---|
| `DeviceSession` (user FK, device_id, platform, app_version, refresh_jti, created/last_seen/revoked) | Session list and revocation | Low, new table |
| `PushDevice` (user FK, token unique, platform, locale, enabled) | FCM/APNs | Low |
| `PlatformStaff` (user one-to-one, role) plus a data migration from current superusers | Separate platform from tenant admin | Medium: checks move from `is_superuser` |
| `Hospital.status` (active/suspended/trial), `Hospital.plan`, `HospitalSubscription` | Tenant lifecycle | Low, nullable/defaulted |
| `DoctorSchedule.slot_minutes`, `DoctorSchedule.max_per_slot` (defaults keep today's behaviour) | Slot generation and capacity | Low |
| Slot-safe booking: lock the `Doctor` row (or a per-doctor-day row) instead of existing appointments, plus `Appointment.idempotency_key` with a unique constraint `(patient, idempotency_key)` | Fixes the empty-day race; safe retries from mobile | Low, see risks section 4 |
| `PaymentOrder` (invoice FK, provider, provider_order_id unique, amount, status) and `WebhookEvent` (provider, event_id unique, payload hash, processed_at) | Gateway payments without double processing | Medium, Phase 8 |
| `ChatSession` / `ChatMessage` (patient, hospital, retention date) | Patient chatbot | Medium: PHI retention rules |
| Optional `public_id` UUID on Patient, Appointment, Invoice and Prescription | Non-guessable ids in deep links and push payloads | Low |

**DECISION C — UUID primary keys.** The brief asks for UUID primary keys. Converting about 150 tables with live foreign keys from integers to UUIDs is a large, destructive migration with little security gain, because every object access is already membership-checked. **Recommendation:** keep integer primary keys and add `public_id` UUIDs only where ids leave the system (deep links, push payloads, QR codes).

The other requested entities already exist under different names, so no new tables are needed for them: `hospital_memberships` = `StaffHospitalMembership` + `PatientHospital`; `otp_challenges` = `OTPVerification` + Twilio Verify; `refresh_sessions` = SimpleJWT `OutstandingToken`/`BlacklistedToken` (+ `DeviceSession`); `consent_records` = `consent.ConsentRecord`; `voice_sessions` = `ai_scribe.ConsultationSession`; `audit_logs` = `audit.AuditLog`; `file_metadata` = `patients.PatientDocument` / `documents`.

## 6. Row-Level Security (defence in depth)

**DECISION D.** Evaluate PostgreSQL RLS as a second wall behind the API checks:
- Set `app.hospital_ids` per request in a transaction-scoped setting (`SET LOCAL`) from middleware, with a policy `hospital_id = ANY(current_setting('app.hospital_ids')::bigint[])` on the highest-risk tables (patients, clinical, billing).
- Costs: every Celery task and management command must set the context or use a `BYPASSRLS` role; PgBouncer must run in transaction mode; patients span hospitals through `PatientHospital`, so their policy is a join, not a column check.
- Recommendation: pilot RLS on `billing_invoice` and `clinical_prescription` in Phase 11, after the mobile MVP, measure the overhead, then decide. Do not block the mobile work on it.

## 7. Flutter application

Location — **DECISION E:** `mobile/` inside this repository (monorepo), so API and app changes land in one reviewable PR and CI can check them together. The alternative is a separate repository.

Stack: Flutter (stable), Dart 3, Material 3, Riverpod, GoRouter, Dio, Drift (SQLite) with SQLCipher, `flutter_secure_storage`, `firebase_messaging` (FCM, with APNs on iOS), generated OpenAPI client.

```
mobile/lib/
  main.dart, app.dart
  core/      config (flavours: dev/staging/prod), network (Dio, auth + hospital interceptors, retry),
             security (secure storage, biometric unlock), database (Drift), routing (GoRouter + role guards),
             theme, notifications, errors (typed failures), utils
  shared/    widgets, components (loading/empty/error/offline states), models
  features/  authentication, onboarding, hospital_selection, patient, doctor, receptionist, admin,
             appointments, prescriptions, medical_records, billing, payments, pharmacy,
             notifications, chatbot, voice_agent
             └─ each: data/ (DTOs, API, local cache, repositories) · domain/ (entities, use cases) · presentation/ (screens, Riverpod notifiers)
```

Routing: after sign-in the app loads `me/contexts`. One context opens that role's home; several show the hospital/role picker. GoRouter redirects block routes the active role may not open, but the server remains the authority.

Role scope for the first mobile releases:

| Role | Mobile v1 | Later |
|---|---|---|
| Patient | OTP login, profile, hospital/department/doctor discovery, slot booking, appointment history, prescriptions, reports, bills, notifications | Online payment (Phase 8), chatbot (Phase 9) |
| Doctor | Today's appointments, queue, patient history (care-scoped), consultation notes, prescription creation, scribe dictation upload | Offline drafts |
| Receptionist | Patient search/registration, scheduling, check-in, queue | Billing counter |
| Hospital admin | Dashboard KPIs, staff list, department list | Role changes stay on web at first |
| Platform admin | Not in mobile v1 | Read-only tenant status |

## 8. Offline and synchronisation

- **Read cache:** last-seen appointments, prescriptions and profile, encrypted with Drift + SQLCipher. The key lives in secure storage, the cache is wiped on logout or account switch, and there is a retention cap (for example 30 days).
- **Write queue** only for low-risk drafts: consultation note drafts and receptionist registration drafts, each sent with an `Idempotency-Key`. Bookings and payments are **online-only**. An appointment created offline shows as "pending — not booked" until the server confirms.
- **Conflicts:** clinical records carry `updated_at`/version. The server rejects stale writes with 409 and the app shows both versions; it never overwrites silently.

## 9. Scalability path (to be proven by load tests)

1. Stateless API instances (already stateless: JWT, Redis-backed sessions and cache).
2. Switch gunicorn to more workers or `gthread`; add PgBouncer (transaction mode) before adding API instances.
3. Redis caching for public directory data (hospitals, departments, doctors, slots with short TTL).
4. Media to S3-compatible object storage with short-lived signed URLs (replaces `FileSystemStorage`).
5. Read replica for reports and analytics.
6. CDN for the web bundle.
7. k6 scenarios: patient login + booking burst, doctor queue polling, receptionist search, report runs. Record RPS, p50/p95/p99, error rate, DB CPU and connections, pool saturation, cache hit rate and Celery queue delay at 1×, 5×, 25× and 100× the current baseline.

The 10,000–50,000 concurrent-user target is a goal. No claim is made until those runs exist.

## 10. Security additions

Signed media URLs; push payloads without PHI (send an id, and the app fetches the details after authenticating); certificate pinning considered for release builds; no secrets in the app (Firebase client config is not secret, server keys stay on the server); jailbreak/root detection only as a warning; screenshot blocking on clinical screens (Android `FLAG_SECURE`); biometric re-unlock after background timeout; DPDP consent captured in-app through the existing `consent` endpoints; ABDM review before any ABHA feature on mobile.
