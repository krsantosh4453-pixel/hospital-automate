# Test Report

Date: 2026-10-25. Every result below comes from commands run on that date. Test data is synthetic (names such as "Synthetic Kamla Devi", phone numbers 9000000xxx); no real patient data was used.

## Commands and results

Run Python with an out-of-tree bytecode cache (`PYTHONPYCACHEPREFIX`), because the iCloud folder stalls imports; see `OPERATIONS_RUNBOOK.md`.

| Command | Result |
|---|---|
| `python manage.py check --settings=config.settings.testing` | No issues |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=config.settings.testing` (SQLite) | **217 tests, OK, 1 skipped** |
| Same suite on PostgreSQL 16 (throwaway local cluster) | **217 tests, OK, 1 skipped** |
| Same suite in a clean environment built only from `requirements-lock.txt` | 217 OK (SQLite and PostgreSQL) |
| `npm run build` | Passes (main JS chunk 836 kB, 176 kB gzip; Vite warns above 500 kB) |
| `npm run lint` | **0 errors**, 124 warnings (unused variables, hook dependencies). `no-undef` and `no-use-before-define` are now enabled. |
| `pip-audit -r requirements.txt -r requirements-production.txt` | No known vulnerabilities (after upgrades) |
| `npm audit` | 0 vulnerabilities (after `npm audit fix`) |
| Migrations on an empty PostgreSQL 16 database | 114 applied; 17 new ones reversed and re-applied |
| Migrations on a copy of the local dev database (SQLite) | 10 pending → applied → reversed → re-applied |
| `scripts/backup.py` create → verify → restore (PostgreSQL 16) | Restored database had identical row counts; a wrong key failed verification; no decrypted leftovers |
| `/health/`, `/health/live/`, `/health/ready/` (PostgreSQL) | 200; database and cache healthy |

The skipped test is the pre-existing `nurses` MAR test (`skipTest("Requires Prescription/PrescriptionItem setup")`). MAR is covered by `security_tests/test_mar_safety.py` instead.

## Test inventory (217 test methods)

| Area | Tests |
|---|---|
| Existing app tests: users 37, procurement 36, patients 11, pharmacy 11, clinical 7, appointments 5, billing 5, doctors 5, hospital 5, nurses 5, audit 4, emergency 4, encounters 4, laboratory 4, notifications 4, bloodbank 3, ipd 3, compounder 2 | 156 |
| New `backend/security_tests/` (12 files) | 61 |

New suites:

| File | Covers |
|---|---|
| `test_tenant_isolation.py` | A Hospital A admin lists and reads one record of every hospital-owned model (67) in Hospital B; foreign `?hospital=`; malformed id |
| `test_rbac_and_writes.py` | Per-hospital roles, foreign `X-Hospital-ID`, related-object smuggling, hospital/ward/department administration, department head, audit rows, per-hospital documents |
| `test_auth.py` | OTP challenge binding, forged challenge, lockout, OTP-required policy, removed token endpoint, password reset (no account enumeration, weak password, token revocation) |
| `test_ai_scribe_safety.py` | Consent before recording, approval only by a linked doctor, PATCH bypass, mock drafts blocked where mocks are disallowed, no-provider 503, provider failure, schema coercion, non-audio upload |
| `test_financial_integrity.py` | Server-side totals, discount limit, overpay, zero amount, idempotency, refund, immutable payments, ledger consistency, expired batch, billing KPIs, patients blocked from analytics, dashboard API |
| `test_e2e_workflows.py` | Scenarios 1–3, 5–7, 10 and 11 (see below) |
| `test_mar_safety.py` | Doses start Scheduled, administer records who and when, no double dose, regeneration keeps outcomes, exclude with reason, PRN |
| `test_consent_sharing.py` | Share → recipient read → access log → revoke → denied; expiry; recipient role; third hospital; form sign and revoke |
| `test_documents.py` | Cross-hospital download denied, patient's own download, audit row, content sniffing, delete role, route order, anonymous |
| `test_notifications.py` | Opt-in, opt-out honoured, skipped deliveries logged, queue event delivery, lab sub-route reachability |
| `test_staff_admin.py` | Own-hospital staff only, approval, Admin role grant rules, cross-hospital change refused |
| `test_frontend_contract.py` | Every URL in `src/services/api.js` resolves to a real route (no router index, no literal action captured as a pk) |
| `test_query_budget.py` | Patients, invoices and lab lists use ≤ 15 queries at 30 rows (measured: 8, 9, 10; invoices were 99 before) |

## Mandated end-to-end scenarios

| # | Scenario | Result | Evidence |
|---|---|---|---|
| 1 | Register patient, retrieve persisted record | PASS | `test_e2e_workflows.register_patient` |
| 2 | Appointment → queue / visit | PASS (found and fixed a 500 on token issue) | `test_opd_consultation_prescription_and_lab` |
| 3 | Encounter, vitals, diagnosis | PASS | same test |
| 4 | AI draft needs authorized human approval | PASS | `test_draft_needs_clinician_approval_before_entering_record` |
| 5 | Prescription → pharmacy | PASS | same OPD test (sale at catalogue price, stock 100 → 91) |
| 6 | Lab order, sample, result | PASS (found and fixed: missing id, 500 on collect, wrong roles) | same OPD test |
| 7 | Admit, bed, nursing note, discharge | PASS (found and fixed: discharge without a finalized summary) | `test_admission_bed_nursing_and_discharge` |
| 8 | Invoice, payment, balance | PASS | `test_payment_flow_balance_overpay_idempotency_refund` |
| 9 | Stock and dispensing consistency | PASS | `test_sale_uses_catalogue_price_and_keeps_ledger_consistent` |
| 10 | Patient sees only their own authorized records | PASS | OPD test (only own, released results) |
| 11 | Unauthorized role refused | PASS | Reception → diagnosis 403; nurse → result verify 403; and others |
| 12 | Hospital A cannot access Hospital B | PASS | `test_tenant_isolation` |
| 13 | Revoked sharing consent denies access | PASS | `test_share_read_then_revoke` |
| 14 | External AI / notification failure doesn't corrupt records | PASS for AI (no note written, draft restored). Notifications: send errors are caught and the queue change persists; no test injects a provider exception. | `test_provider_failure_does_not_touch_clinical_record`, `test_queue_event_records_in_app_delivery` |

## Browser verification

Production build, served by `vite preview`, against a seeded throwaway backend.

- **Staff:** all 25 staff routes render with no uncaught error. Signed in as Admin. Gave a MAR dose through the UI and confirmed in the database that it was recorded as Administered by the signed-in user. The Users page lists the real staff; Reports shows server KPIs that match the seed; the Hindi toggle translates navigation and persists across reload.
- **Patient:** all 8 patient routes render with no error. Signed a consent form through the UI.
- **Bugs this pass found and fixed:**
  - Home, Pharmacy, Permissions and Reports crashed.
  - The analytics SQL was PostgreSQL-only and failed on SQLite.
  - MAR due doses were hidden.
  - The patient portal had no hospital selected.
  - Every API error displayed as "true".

Not covered by automated frontend tests: there is no Jest or Playwright harness in the repository. Frontend behaviour is covered by the browser pass above and the API contract test.

## Not tested

- Real SMS, WhatsApp, email and voice delivery; real STT and LLM providers; Google sign-in. No credentials were available; all are mocked in tests.
- Docker Compose startup and nginx at runtime (Docker is not installed on this machine). The YAML was validated by parsing; nginx config by review only.
- Load and concurrency under real parallel traffic. Row locks and the atomic update are in place, but there was no parallel test because SQLite serialises writes.
- Mobile layout beyond the pane's phone-width rendering of the login page.
