# Implementation roadmap (proposal, awaiting approval)

Entry point for the SaaS + mobile programme. Read with [repository-audit.md](repository-audit.md), [current-system.md](current-system.md), [target-system.md](target-system.md) and [risks-and-dependencies.md](risks-and-dependencies.md).

Every phase follows the same loop: state the objective → list the files → write regression tests first → make the smallest change → run backend, frontend and E2E tests → check the web app still works → update these docs → list known issues.
Affected repository for every phase: `krsantosh4453-pixel/hospital-automate` (backend `backend/`, web `src/`, mobile `mobile/` if Decision E is approved).

Sizes are rough engineering effort for one developer with AI help, not calendar promises: S ≈ 1–3 days, M ≈ 1–2 weeks, L ≈ 3+ weeks.

| # | Phase | Objective | Main files | Depends on | Exit criteria | Size |
|---|---|---|---|---|---|---|
| 1 | Audit & architecture | Map what exists; agree the target | `docs/architecture/*` | None | Owner approves decisions A–E | Done (this) |
| 2 | API & backend readiness (**in progress**, see below) | `/api/v1/` alias; fix the empty-day booking race; booking idempotency; remove dead URL modules; clean the OpenAPI schema for mobile endpoints | `config/urls.py`, `appointments/views.py`, `appointments/models.py` + migration, `doctors/urls.py` etc., `config/openapi_schema.py` | 1 | Concurrency test proves two patients cannot take one slot (PostgreSQL); web E2E green on `/api/v1/`; schema has no warnings for mobile endpoints | M |
| 3 | Auth & tenant context | `me/contexts`, `DeviceSession`, session list/revoke/logout-all, `PlatformStaff` replacing `is_superuser`, cross-hospital tests per endpoint | `users/` (models, views, urls, permissions), `hospital/views.py`, `notifications/views.py`, `reports/views.py`, `security_tests/` | 2 | Tenancy test matrix: every mobile endpoint × (own hospital, other hospital, no membership, wrong role) | M |
| 4 | Flutter foundation | Project skeleton, flavours, Dio + interceptors, secure storage, OTP sign-in, context picker, GoRouter role guards, theme, error/empty/offline widgets, CI (analyze, test, Android build; iOS build on macOS runner) | `mobile/**`, `.github/workflows/mobile.yml` | 3; Flutter SDK installed | Sign in by OTP on a staging backend, pick a hospital, see the role home; Android and iOS debug builds in CI | M |
| 5 | Patient app + booking | Discovery, slots, booking, history, prescriptions, reports, bills (view only) | `mobile/lib/features/{patient,appointments,prescriptions,medical_records,billing}`, `appointments/` slots endpoint, `encounters/models.py` (slot fields) | 4 | Booking E2E with integration tests; double-booking test from two devices; offline shows cached data with "may be out of date" | L |
| 6 | Doctor app + prescriptions | Today's list, queue, care-scoped history, consultation, prescription creation, scribe dictation upload | `mobile/lib/features/doctor`, reuse `clinical/`, `ai_scribe/` | 5 | Care-scope tests; prescription integrity tests reused from web; draft never auto-signed | L |
| 7 | Receptionist & admin | Registration, scheduling, check-in, queue, search; admin KPIs and staff/department lists | `mobile/lib/features/{receptionist,admin}`, reuse `patients/`, `encounters/`, `home/`, `reports/` | 5 | Role tests; UHID uniqueness under concurrent registration from mobile | M |
| 8 | Pharmacy, billing, payments | Choose gateway (Decision F); `PaymentOrder`, `WebhookEvent`, signature check, idempotent capture, reconciliation report | `billing/` (models, services, views, webhooks), `mobile/lib/features/payments` | 7; gateway account | Replayed and duplicated webhooks credit once; amount mismatch rejected; test-mode end to end | L |
| 9 | AI chatbot & voice | Patient chatbot (FAQ, booking help, non-diagnostic, with escalation), retention rules; mobile dictation for doctors on the existing scribe | new `assistant/` app, `ai_scribe/`, `mobile/lib/features/{chatbot,voice_agent}` | 6; LLM provider and DPA; clinical safety sign-off (L4) | Red-team prompts refused; no PHI sent to the provider without consent; every AI output labelled | L |
| 10 | Notifications & offline sync | FCM/APNs provider, `PushDevice`, PHI-free payloads, Celery fan-out; encrypted cache, draft queue, conflict screen | `notifications/services/providers.py`, `notifications/models.py`, `mobile/lib/core/{notifications,database}` | 4 (push needs Firebase project + APNs key) | Push delivery logged like other channels; sync conflict test; logout wipes cache | M |
| 11 | Security, performance, load | RLS pilot (Decision D), PgBouncer, object storage + signed URLs, k6 scenarios at 1×/5×/25×/100×, penetration test and DPDP assessment (L5) | `config/settings/production.py`, `docker-compose.prod.yml`, `loadtest/`, `docs/LOAD_TEST.md` | 5–10 on staging (L1) | Measured capacity written down with bottlenecks; no critical or high pentest findings open | L |
| 12 | Release preparation | Store listings, privacy labels, data-safety form, signing, crash reporting, phased rollout, support runbook | `mobile/android`, `mobile/ios`, `docs/` | 11 | Internal testing track → closed beta at one pilot hospital → production | M |

## Phase 2 in detail

Status 2026-11-09: items 1–6 below are done and tested; they are not committed yet. Remaining Phase 2 work: reduce OpenAPI schema warnings for the endpoints mobile uses (item 7), and Decision G.



1. **Regression first:** a PostgreSQL concurrency test in `security_tests/` where two patients book the same slot of a doctor with no appointments that day. Expected today: it fails, because both bookings succeed.
2. **Fix:** in `AppointmentViewSet` self-booking, lock the `Doctor` row (`Doctor.objects.select_for_update().get(pk=…)`) before checking taken slots. Optionally add a partial unique constraint on `(doctor, appointment_date, appointment_time)` for active statuses, but only if the OPD workflow never puts two patients in one slot on purpose (to confirm with the owner, see risks section 4).
3. **Idempotency:** accept `Idempotency-Key` on self-booking, and return the existing appointment on a retry with the same key.
4. **Versioning:** `path("api/v1/", include(api_patterns))` next to `api/`, with a test that both prefixes resolve the same views. Rate limits, cookie sign-in and the family-access write rule compare paths through `config/api_paths.unversioned_path`, so `/api/v1/` cannot bypass them and both prefixes share one budget. The schema documents `/api/v1/` only.
5. **Dead code:** deleted `appointments/`, `pharmacy/`, `compounder/`, `patients/` and `doctors/urls.py`; the full list of 2,263 resolved routes was byte-identical before and after.
6. **Docs:** update `docs/API_DOCUMENTATION.md` and this roadmap.
Review notes (2026-11-09): moving the web app to `/api/v1/` first needs the refresh cookie path widened from `/api/auth/` (and logout clearing both paths). Migration `appointments/0008` builds a small partial unique index non-concurrently, a brief write lock on `appointments_appointment`; fine at current size.
7. **Schema clean-up (open):** add serializer type hints / `extend_schema` to the mobile endpoints (auth, patient me, booking options and book, appointments, prescriptions, invoices) until they generate without warnings.

## Not in scope until asked

Payroll/HR, ABDM on mobile, HL7 v2, ML forecasting, splitting the monolith, a second database.
