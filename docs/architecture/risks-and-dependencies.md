# Risks and dependencies (2026-11-09)

Related: [implementation-roadmap.md](implementation-roadmap.md) · [target-system.md](target-system.md)

## 1. Decisions the owner must make

| Id | Decision | Recommendation | Blocks |
|---|---|---|---|
| A | API versioning | Mount the same URLconf at `/api/v1/`; keep `/api/` until the web app moves | Phase 2 |
| B | Platform super-admin | New `PlatformStaff` model, separate `/api/v1/platform/` endpoints, no patient data by default | Phase 3 |
| C | UUID primary keys | Keep integer keys; add `public_id` UUIDs only where ids leave the system | Phase 2–3 |
| D | PostgreSQL RLS | Pilot on two tables in Phase 11, then decide | Phase 11 |
| E | Where the Flutter app lives | `mobile/` in this repository | Phase 4 |
| F | Payment gateway | Choose a provider (for example Razorpay, Cashfree or PayU in India); needs a merchant account | Phase 8 |
| G | Same-slot policy | **Decided 2026-11-09:** one patient per doctor slot by default; a hospital admin may raise `Doctor.slot_capacity` (1–20) for group consultations. Enforced by a database constraint on numbered places plus the doctor-row lock | Done (Phase 2) |

## 2. External dependencies

| Dependency | Needed for | Status |
|---|---|---|
| Flutter SDK + Android SDK on the dev machine; macOS CI runner for iOS | Phase 4+ | Not installed (Xcode present) |
| Apple Developer account, Google Play Console account | Builds on devices, release | Unknown |
| Firebase project + APNs auth key | Push | Not set up |
| Twilio Verify with real credentials | Mobile OTP sign-in | Never exercised (L2) |
| Staging host with domain and CA certificate | Testing the app against a real backend | Not done (L1) |
| Payment gateway merchant account | Phase 8 | Not chosen |
| LLM provider with a data-processing agreement, India data residency reviewed | Chatbot, scribe | Not set up |
| Clinical safety officer sign-off | Prescriptions, AI, offline rules | Pending (L4) |
| Penetration test, DPDP assessment | Production | Pending (L5) |

## 3. Security risks

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| A new mobile endpoint skips `HospitalScopedViewSet` and leaks another hospital's data | Medium / critical | All mobile endpoints extend the scoped viewsets; per-endpoint cross-hospital test matrix (Phase 3); RLS pilot as a second wall |
| Refresh token stolen from a device | Low / high | Secure storage, rotation + blacklist (exists), device sessions with revoke, biometric unlock |
| PHI in push notifications or device logs | Medium / high | Id-only payloads; no PHI in Dio logs; release builds strip debug logging |
| Encrypted cache key lost or cache readable after logout | Low / high | Key in Keychain/Keystore; wipe on logout and account switch; retention cap |
| `is_superuser` paths grow during migration to `PlatformStaff` | Medium / high | Replace all 7 checks in one change, with tests asserting a hospital admin is refused |
| OTP abuse (SMS pumping) from the public app | Medium / medium (cost) | Per-phone + per-IP limits (exist); Twilio fraud guard; app attestation (Play Integrity / App Attest) later |
| Webhook spoofing or replay | Medium / high | Signature check, unique `event_id`, amount and order match, idempotent capture |
| AI chatbot gives clinical advice | Medium / high | Non-diagnostic scope, refusal tests, escalation, clinical sign-off |

## 4. Correctness risk found during the audit (fixed 2026-11-09)

**Patient self-booking race on an empty day** (`backend/appointments/views.py`, self-booking action). The transaction locks `Appointment` rows for the doctor and day with `select_for_update`. When the day has no rows yet nothing is locked, and the unique constraint `appointment_unique_active_slot` includes `patient`, so it does not stop two different patients. Two simultaneous bookings for the first slot of an empty day can therefore both succeed.
- **Reproduced** on PostgreSQL 16: 8 parallel patients, 3 got the slot (`security_tests/test_concurrency.py::test_one_slot_on_an_empty_day_goes_to_one_patient`).
- **Fixed** in Phase 2: `book` locks the `Doctor` row before checking taken slots; the same test now gets one 201 and seven 409s. Retries with one `Idempotency-Key` book once (`test_parallel_booking_retries_with_one_idempotency_key_book_once`).
- Decision G (2026-11-09) closed the remaining gap: staff bookings, edits and reschedules take a place under the same doctor lock, and a database constraint refuses two active bookings on one place. Concurrency tests: 8 parallel patients against capacity 3 → exactly 3 booked; 8 parallel receptionist bookings against capacity 1 → exactly 1.
- Every application write path takes its place through `appointments/slots.py`, including a queue token put back in the queue: a No Show or Completed booking becomes active again only if its slot still has a free place, otherwise it keeps its status and the token is served from the queue. Lowering a doctor's capacity never closes existing bookings; new bookings are refused until the slot is below the new capacity.
- Residual risk: a direct database edit or a Django admin save that skips `appointments/slots.py` is still stopped by the database constraint, but fails with an error page instead of a clear message.

## 5. Scalability risks

| Risk | Note |
|---|---|
| Only one measured data point (162 req/s, 50 clients, local) | Every capacity claim waits for Phase 11 |
| Sync gunicorn workers and `CONN_MAX_AGE=60` with many instances will exhaust PostgreSQL connections | PgBouncer before horizontal scaling |
| One audit row per sensitive read | Audit table growth; partition by month and keep the retention task |
| Local filesystem media | Blocks multiple API instances; move to object storage |
| Mobile polling (queue, notifications) multiplies load | Push first; ETag/`If-Modified-Since` on polling endpoints; sensible intervals |
| Reports on the primary database | Read replica or snapshot tables (`reports.KPISnapshot` exists) |

## 6. Delivery risks

- Shared checkout with other agent sessions: commit only your own changes, and stage right before committing.
- The project folder sits in iCloud and commands can stall on evicted files. Run heavy test suites in a `git archive` scratch copy.
- The web app must keep working throughout: every phase runs the existing Vitest, Playwright and backend suites before merging.
- Scope: twelve phases is a large programme. Phases 2–5 form the smallest useful release, a patient booking app on a hardened API.
