# Prompt 3 — Patient Registration, Hospital Selection, UHID & Reception Enrolment: Evaluation

- **Date:** 2026-11-24 · **Branch:** `ui/redesign-2026-10-25` (uncommitted working tree on top of `1343ce1`; the Prompt 2 billing changes are also still uncommitted, see §3)
- **Source findings:** [`E2E_WEB_APPLICATION_AUDIT.md`](E2E_WEB_APPLICATION_AUDIT.md): Step 1 (Registration: PARTIAL), MF-001, MF-002, INT-003
- **Previous reports (unchanged):** [`PROMPT_1_ALLERGY_FIX_EVALUATION.md`](PROMPT_1_ALLERGY_FIX_EVALUATION.md), [`PROMPT_2_BILLING_FIX_EVALUATION.md`](PROMPT_2_BILLING_FIX_EVALUATION.md)
- **Evidence:** [`e2e-evidence/prompt-3/`](e2e-evidence/prompt-3/)
- **Test data:** synthetic only, in throwaway databases (Django test DB, the Playwright e2e SQLite, a temporary PostgreSQL 17 cluster). The development database was not touched; no SMS or email left the machine (console OTP, in-memory email).

## Final verdict: **FIXED AND VERIFIED**

A newly self-registered patient now chooses a hospital, receives that hospital's UHID, sees it on the dashboard after reload and re-login, and books an appointment there. The front desk can enrol an existing patient (and is told when the patient is already registered). Verified with unit, API, PostgreSQL concurrency and real-browser tests plus database checks. All non-passing regression items are pre-existing and unrelated (§15).

---

## 1. Original audit findings

1. The Create Account form had no hospital choice (MF-001).
2. A self-registered patient therefore had no hospital membership and no UHID; `booking-options` returned `{"hospitals": []}` and the booking form said "register at the reception first".
3. `POST /api/patients/link/` existed and worked (201, UHID issued) but no web screen called it (MF-002 / INT-003).

## 2. Root causes (investigated, not assumed)

The **backend was already complete**; the gap was entirely in the web frontend:

| Capability | Backend (already existed) | Web UI before |
|---|---|---|
| Hospitals a patient may choose | `GET /api/auth/patient/hospitals/` (public; active + `allow_patient_self_registration`) | not called |
| Choose at sign-up | `POST /api/auth/register/` accepts `hospital`, validates it (`hospital_for_self_registration`) and issues the UHID in the same transaction (`ensure_uhid`) | field missing |
| Join later as the patient | `POST /api/auth/patient/hospitals/join/` (idempotent, audited) | not called |
| Desk enrols an existing patient | `POST /api/patients/link/` `{phone, date_of_birth}` (Receptionist/Admin of the acting hospital; both details must match; never creates a patient) | not called |
| UHID shown to the patient | `GET /api/auth/patient/me/` returns `hospitals: [{id, name, uhid}]` | not shown |

The **mobile app already uses all of these** (`auth_repository.dart`, `reception_repository.dart`), which confirms the backend contract. The web app simply never wired them up.

One backend gap found: the link response body was identical for "newly registered" (201) and "already registered" (200), and the web API helper only exposes the body, so a screen could not tell them apart.

## 3. Files modified

**Prompt 3:**

| File | Change |
|---|---|
| `src/pages/Register.jsx` | Hospital choice (`HospitalChoice`): loaded from the API; loading / failed-with-retry / none-open states; required whenever a hospital is offered; sent as `hospital`; confirmation shows the hospital and UHID |
| `src/components/patients/EnrolExistingPatientDialog.jsx` (new) | Reception "Enrol existing patient": mobile + date of birth → `POST /api/patients/link/`; "now registered" / "already registered" with UHID; server errors shown |
| `src/pages/Patients.jsx` | "Enrol existing patient" button (Receptionist/Admin, same rule as the API) next to "Register patient"; list reloads after enrolment |
| `src/components/patient/HospitalMembership.jsx` (new) | `MyHospitalsCard` (hospitals + UHIDs from `patient/me`) and `JoinHospitalForm` (join an open hospital) |
| `src/pages/patient/PatientDashboard.jsx` | Shows `MyHospitalsCard` ("Your hospitals", UHID) |
| `src/pages/patient/BookAppointmentModal.jsx` | A patient with no hospital can register at an open one in place, then the form reloads its options |
| `src/services/api.js` | `auth.selfRegistrationHospitals`, `auth.joinHospital`, `patients.link` |
| `backend/patients/views.py` | `link` response adds `created: true/false` (status codes and other fields unchanged) |
| `src/assets/i18n/hiPages.js` | Hindi for the new labels (others fall back to English) |
| Tests | `src/__tests__/patientEnrollment.test.jsx` (new, 10), `src/__tests__/authDialog.test.jsx` (mock gains the hospital list), `backend/patients/test_registration_linking.py` (asserts `created`), `backend/security_tests/test_concurrency.py` (+2 PostgreSQL tests), `e2e/patient-registration.spec.js` (new, 4 scenarios) |

**Prompt 2 (still uncommitted, not changed here):** `backend/billing/services.py`, `backend/billing/test_decimal_payments.py`, `src/pages/billing.jsx`, `src/pages/patient/PatientBills.jsx`, `src/utils/money.js`, `src/__tests__/money.test.js`, `e2e/billing-decimal.spec.js`; `PatientDashboard.jsx` carries both prompts' edits.

## 4. Frontend implementation

- **Registration:** for Patient sign-ups only (Admin sign-ups unchanged). Hospital list from `GET /api/auth/patient/hospitals/`, labelled "Name (City)"; no names or IDs hard-coded. Submit is refused with a message while the list is loading or failed ("Try again" reloads it), and when hospitals are offered but none chosen. If **no** hospital accepts online registration the page says so and still creates the account (the reception can enrol the patient later). Duplicate submission is prevented by the existing disabled-while-loading button.
- **Confirmation:** "Registered at Demo City Hospital. Your patient ID (UHID) there is DCH-2026-000001." taken from the server's response, followed by the existing email-verification step (unchanged).
- **Dashboard:** "Your hospitals" lists each hospital with its UHID from `GET /api/auth/patient/me/`; with none, it offers `JoinHospitalForm`.
- **Booking:** with no hospital, the form offers `JoinHospitalForm`; after joining, `booking-options` is reloaded and normal booking continues (all booking rules stay on the server).
- **Reception:** dialog on the Patients page for the selected hospital; 10-digit mobile and date of birth checked before sending; result states "X is now registered at H" or "X is already registered at H", with the UHID; 404/409/403 server messages shown as-is.

## 5. Backend implementation

Only one change: `PatientViewSet.link` returns `{...patient, "created": created}`. The 201/200 codes and every existing field are unchanged; the mobile reception client reads named keys, so the extra key is ignored. No other backend logic was added or duplicated.

## 6. API integration (real requests in the browser runs)

| Call | Used by | Verified |
|---|---|---|
| `GET /api/auth/patient/hospitals/` | Register, JoinHospitalForm | list shown; no auth needed |
| `POST /api/auth/register/` + `hospital` | Register | 201; `patient.hospitals[0].uhid` = `DCH-2026-000001` |
| `GET /api/auth/patient/me/` | Dashboard | `hospitals[].uhid` equals the confirmation's UHID (spec A) |
| `POST /api/auth/patient/hospitals/join/` | Booking / dashboard | 201, UHID issued (spec D) |
| `POST /api/patients/link/` | Reception dialog | 201 `created: true`; repeat 200 `created: false`, same UHID; wrong details 404 |
| `GET /api/appointments/booking-options/`, `POST /api/appointments/book/` | Booking | hospital listed after registration; appointment saved for that patient and hospital (spec C) |

## 7. Database changes

**None** (no migration). Existing constraints used as they are: unique `(patient, hospital)` membership, unique `(hospital, lower(uhid))`, UHID issued with a row lock inside a transaction (`ensure_uhid` → `next_uhid`).

## 8. UHID generation and uniqueness strategy (existing, verified)

- Format `<prefix>-<year>-<6 digits>` per hospital (`DCH-2026-000001`), prefix = hospital `uhid_prefix` → code → `H<id>`; per-hospital, per-year sequence.
- **Hospital-specific**: one patient record, one membership (and UHID) per hospital; a patient can belong to several hospitals.
- Issued once and never changed: `ensure_uhid` returns an existing UHID unchanged; login and dashboard only read it.
- Not client-settable: `uhid` is read-only in the patient serializer (the hospital's own value is computed server-side).
- Concurrency: verified on PostgreSQL (§10).

## 9. Reception enrolment implementation

The desk enters the patient's **mobile number and date of birth**; the server enrols only when both match exactly one existing patient. This is the existing, deliberate privacy rule ("nobody is found by the number alone"): a desk cannot browse or search patients of other hospitals by name or UHID. Patients already registered at this hospital remain searchable on the Patients list by name, phone or UHID (existing behaviour). No patient or user is ever created by this path; repeats return the same registration.

## 10. The 12 test cases

| # | Case | Evidence | Result |
|---|---|---|---|
| 1 | New patient registers with a hospital | e2e A (UI → 201 → UHID on confirmation and dashboard); unit; backend `test_registration_with_a_hospital_links_it_and_issues_a_uhid` | **PASS** |
| 2 | Missing hospital | unit: submit refused with "Choose the hospital…" and no request when hospitals are offered; the backend keeps `hospital` optional for API compatibility (mobile app, join later): no partial records, since the account is created whole or not at all | **PASS** (policy documented) |
| 3 | Invalid / unauthorised hospital | backend `test_a_patient_cannot_pick_a_closed_inactive_or_unknown_hospital`, `test_a_patient_cannot_join_a_closed_hospital` (400) | **PASS** |
| 4 | UHID uniqueness | DB check: 3 new patients → `DCH-2026-000001..3`, no duplicate UHID per hospital; `patients.test_uhid*` (21 tests) | **PASS** |
| 5 | Desk enrols an existing patient | e2e B: "now registered", UHID; DB: one patient row with that mobile number | **PASS** |
| 6 | Duplicate enrolment | e2e B: "already registered", same UHID; backend `created: false`, membership count 1 | **PASS** |
| 7 | Unauthorised role | backend `test_other_roles_and_other_hospitals_cannot_link` (nurse 403), `test_staff_and_strangers_cannot_use_the_patient_join`; UI shows the button only to Receptionist/Admin | **PASS** |
| 8 | Cross-hospital isolation | backend: another hospital's desk 403 and cannot see the linked patient (`test_another_hospitals_desk_cannot_see_the_linked_patient`) | **PASS** |
| 9 | Registration → appointment | e2e A + C: register with hospital → sign in → book → appointment for that patient at Demo City Hospital | **PASS** |
| 10 | Refresh and re-login | e2e A: reload keeps the UHID; e2e C: new OTP sign-in after the 60 s resend cooldown shows the same UHID | **PASS** |
| 11 | Concurrent enrolment | PostgreSQL: 8 parallel enrolments → 8 distinct UHIDs; 8 parallel enrolments of one patient → one membership (1×201, 7×200) | **PASS** |
| 12 | Existing patients | seeded `DEMO-…` UHIDs unchanged (DB); existing journeys pass (§15); a hospital-less legacy account (the audit's scenario) can now join from the booking form (e2e D) | **PASS** |

## 11. Eight-step evaluation

| Step | Result | Notes |
|---|---|---|
| 1 Code review | PASS | Reuses existing endpoints and rules; no second identity system; no hard-coded hospitals; one additive backend field; lint clean |
| 2 Database | PASS | `e2e-evidence/prompt-3/database-verification.txt`: one membership per patient and hospital, no duplicate UHIDs, no duplicate patients per mobile, seeded data intact, audit rows for join/link/repeat |
| 3 API | PASS | §6 |
| 4 Backend tests | PASS | patients + registration + appointments: 143/143; concurrency on PostgreSQL 2/2; full suite 1,472 tests: only the 2 known `.env` failures |
| 5 Frontend tests | PASS | Vitest 225/225 (42 files) incl. 10 new; build passes |
| 6 Real browser E2E | PASS | `patient-registration.spec.js` 4/4 (A registration + UHID + dashboard + reload; C re-login + booking; B desk enrolment + repeat + wrong details; D join from booking) |
| 7 Regression | PASS (pre-existing exceptions) | Full Playwright 43/44, incl. allergy (Prompt 1), billing (Prompt 2), OPD-to-bill, family access, login |
| 8 Independent verification | PASS | Audit scenario reproduced in the browser on a fresh database: self-registration with hospital → UHID → booking; plus a hospital-less account joining from the booking form; desk enrolment of an existing account. DB records and API responses match (§6, §14) |

Notes on how tests were made to pass honestly:
- The re-login test waits out the server's 60-second OTP resend cooldown rather than bypassing it.
- A first draft of the e2e spec re-read the *previous* OTP from the log ("Invalid or expired OTP", a test race); the spec now waits for a new code.
- The backend `created` assertions were added right after the view change, so they were not observed failing first.

## 12. Browser screenshots (`e2e-evidence/prompt-3/`, from the final full regression run)

| File | Shows |
|---|---|
| `A1-registered-with-uhid.png` | Create Account confirmation with hospital and UHID |
| `A2-dashboard-uhid.png` | Patient dashboard "Your hospitals": Demo City Hospital, UHID |
| `B1-enrolled.png` | Reception: "… is now registered at Demo City Hospital", UHID |
| `B2-already-registered.png` | Reception, repeat: "… is already registered", same UHID |
| `C-booked.png` | The new patient's booked appointment |
| `D-joined-from-booking.png` | Booking form after joining a hospital in place |

UHID numbers in the screenshots differ from the database listing because they come from the final full run (other specs register patients first); the listing comes from the isolated spec run.

## 13. API evidence

Captured and asserted inside the specs (status codes and bodies): register 201 with `patient.hospitals[0].uhid`; `patient/me` UHID equals the confirmation; link 201 `created: true` then 200 `created: false` with the same UHID; link with unknown details 404 with "No patient has this mobile number and date of birth"; join 201 with UHID; appointment row `hospital_name` and `patient_name` match.

## 14. Database verification

From `database-verification.txt`:

| Patient (synthetic) | Hospital | UHID | Login |
|---|---|---|---|
| Synthetic Signup | Demo City Hospital | DCH-2026-000001 | yes |
| Synthetic Existing | Demo City Hospital | DCH-2026-000002 | yes |
| Synthetic Joiner | Demo City Hospital | DCH-2026-000003 | yes |

Duplicate UHIDs: none. Duplicate patients per mobile number: none. Double memberships: none. Seeded `DEMO-…` UHIDs: unchanged. Audit: `patients.self_registration.join` 2, `patients.link` 1, `patients.link.repeat` 1.

## 15. Regression results

- **Playwright (full suite):** 43/44. The failure was `hospital-services` "ambulance call …" (timeout waiting for a leave row to become stable). It passes on a fresh database and fails only when repeated on the same one (it uses a fixed date, 2030-02-01); no services code changed. The earlier flaky `nurse-mar` spec passed in this run.
- **Backend (full suite):** 1,472 tests; 2 failures caused by the developer's `.env` (`AI_SCRIBE_MODEL`, `DJANGO_ENV`), unchanged since Prompt 1 (pass in a clean copy without `.env`). One registration test fails only when real Twilio credentials from `.env` leak into test settings; it passes with them blanked.
- **Frontend:** 225/225; lint clean; build passes.
- **Earlier prompts' evidence:** the full runs re-captured the committed Prompt 1 `allergy-*.png`, which were restored to their committed versions. The Prompt 2 `billing-*.png` were never committed and were re-captured by the same unchanged spec with the same assertions (no prior copy existed to restore).

## 16. Security findings

All verified rather than assumed:
- A patient can only choose or join **open** hospitals (server-checked; unknown, closed or inactive ids refused).
- Only Receptionist/Admin **of the acting hospital** can enrol; other roles and other hospitals' desks get 403.
- Enrolment needs mobile **and** date of birth; no browsing of other hospitals' patients; wrong details reveal nothing (404).
- UHIDs are issued by the server only, never accepted from the client, never changed once issued.
- No duplicate memberships or UHIDs, including under parallel load (PostgreSQL).
- RBAC and hospital scoping unchanged (no permission code modified).
- No new findings requiring a fix in this scope.

## 17. Remaining limitations (documented, not changed)

1. **Hospital is optional at the API.** The web form requires a choice whenever hospitals are offered; the API keeps it optional so the mobile app and the "join later" path keep working.
2. **Email verification in e2e mode** cannot be exercised (in-memory mailbox); patients signed in with Mobile OTP. Email verification was verified on the dev server in the original work.
3. **No cross-hospital search by name or UHID at reception**, by design of the existing privacy rule (§9).
4. The `hospital-services` ambulance spec is not repeat-safe (fixed date); unrelated to this work.
5. Other audit items (BUG-003 Sunday slots, BUG-008 same-day double booking, etc.) are untouched; Prompt 4 was not started.

## 18. Final verdict

**FIXED AND VERIFIED.** The missing web workflows (hospital choice at sign-up, the patient's UHID, joining a hospital, and reception enrolment) now use the existing backend rules end to end; a new patient can register, receive the right UHID and book. No duplicate patients, memberships or UHIDs; no weakening of verification, RBAC or hospital isolation. Nothing was committed or pushed.
