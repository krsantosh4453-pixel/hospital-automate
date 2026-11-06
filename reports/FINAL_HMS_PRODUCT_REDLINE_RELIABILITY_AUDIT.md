# HMS: Product Readiness, Red-Line and Reliability Audit

| | |
|---|---|
| **Date** | 2026-11-05 |
| **Branch / commit** | `ui/redesign-2026-10-25` @ `ef09895` (2 commits ahead of `origin`; never seen by CI) |
| **Scope** | Whole repository: 25 Django apps, React frontend, Docker/nginx, CI, docs |
| **Method** | Static review + every test suite + live API workflows on PostgreSQL 16 + browser runs. All work done in an isolated `git archive HEAD` copy in the session scratchpad. |
| **Data** | Synthetic only (`seed_demo` + `AUDIT …` records). The project's `backend/db.sqlite3` and `.env` were never read, copied or touched. |
| **Changes made** | None to code, database, git state or untracked files. This report is the only file added. |

Labels used throughout:
- **VERIFIED**: observed in this audit, by running it.
- **CODE**: read in source, not executed.
- **CLAIMED**: stated by an earlier report and not re-verified here.
- **NOT VERIFIED**: no evidence either way.

---

## A. Executive summary

**Verdict: not ready for real patients today.** The core is unusually solid for a project at this stage:
- tenancy fails closed
- money is Decimal and row-locked
- stock deductions are atomic
- an allergy check blocks new prescriptions
- 847 of 847 backend tests pass on PostgreSQL

But this audit found **9 HIGH-severity issues**. Three of them are in patient safety or patient identity, and three make production operations unsafe (no automated or media backups, background jobs on a queue nobody reads, a hard Twilio dependency at boot). None is architectural; most are 0.5–3 day fixes.

### Completion estimate: ≈ 60 % of a production-ready product

The estimate is the mean of two separately scored parts, weighted 60/40:

| Part | How it was scored | Score |
|---|---|---|
| Functional completeness (60 %) | 23 modules scored 0–1 by verified status (section B): COMPLETE 0.9–1.0, PARTIAL 0.3–0.85 by how much is missing or broken, NOT IMPLEMENTED 0 | **16.7 / 23 = 73 %** |
| Production & operational readiness (40 %) | 28 checklist items (section G): DONE 1, PARTIALLY DONE 0.5, NOT DONE or NOT VERIFIED 0 | **11 / 28 = 39 %** |
| **Weighted** | 0.6 × 73 + 0.4 × 39 | **≈ 59–60 %** |

The application is far more complete than it is deployable. Feature breadth is high; operations, compliance and integrations are what remain.

### Status at a glance

| Dimension | Status | One-line reason |
|---|---|---|
| Product readiness | **PARTIAL** | Core OPD → pharmacy → billing works end to end. Patient pickers break past 50 patients on 7 pages. |
| Red-line status | **9 HIGH, 0 CRITICAL open** | Safety-check bypass, cross-role dispensing, patient mis-selection, duplicate money movements, backups, dead job queue, Twilio boot dependency, no error boundary, red E2E suite. |
| Reliability | **GOOD core, WEAK operations** | Concurrency verified on PostgreSQL. No automated backups, no media backup, no monitoring, one dead Celery queue. |
| Production readiness | **NOT READY** | Cannot boot without Twilio. No staging run on a real domain. No load test, pen test, DPIA or clinical sign-off. |

### Biggest remaining risks

1. **Patient safety:** a doctor can change a medicine on an existing prescription with **no allergy re-check** (RL-01, verified).
2. **Wrong patient:** billing, IPD, lab, prescription, radiology, blood bank and emergency pickers show only the **50 newest patients**. Manual billing also matches patients **by name** (RL-03, verified).
3. **Data loss:** **no automated backup**, and uploaded **patient documents are never backed up**. The DR plan describes WAL/PITR that does not exist (RL-07).
4. **Money integrity:** double-submitted payments and refunds are recorded twice (RL-04, RL-05, verified).
5. **Go-live blocker:** production refuses to start without Twilio Verify credentials, even with OTP turned off (RL-06, verified).

---

## B. Module-wise status

Columns:
- **FE**: frontend page exists and loads (VERIFIED for pages in the page-load run).
- **BE / API / DB**: implementation, wiring and persistence.
- **Tests**: automated coverage, and the result here.

Scores feed section A.

| # | Module | FE | BE | API | DB | Tests | Status (score) | Remaining work |
|---|---|---|---|---|---|---|---|---|
| 1 | Patient management | ✓ | ✓ | ✓ verified | ✓ verified | ✓ pass | **PARTIAL (0.75)** | Pickers limited to page 1 (RL-03). `P###` ids instead of UHID on money and emergency screens (RL-16). Dedup is by phone only. |
| 2 | Doctor management | ✓ | ✓ | ✓ | ✓ | ✓ pass | **PARTIAL (0.75)** | Inviting a Doctor creates no `Doctor` profile; a second manual step links it by email (RL-15). |
| 3 | Appointments | ✓ | ✓ | ✓ verified | ✓ | ✓ pass | **PARTIAL (0.8)** | Same patient + doctor + slot can be booked twice (RL-10). |
| 4 | OPD queue & tokens | ✓ | ✓ | ✓ verified | ✓ verified | API ✓, browser spec **stale** | **COMPLETE (0.9)** | Token is idempotent under 10 parallel calls. Update the stale Playwright spec (RL-09). |
| 5 | Consultation & clinical records | ✓ | ✓ | ✓ verified | ✓ | ✓ pass | **PARTIAL (0.8)** | Vitals, allergy, diagnosis, notes verified. Item edit bypasses safety (RL-01). |
| 6 | EMR (within one hospital) | ✓ | ✓ | ✓ | ✓ | ✓ pass | **PARTIAL (0.7)** | Allergies don't follow the patient across hospitals (RL-14). Templates not offered in the notes editor (CLAIMED limitation). |
| 7 | EHR / interoperability (ABDM, FHIR, HL7) | — | partial | off by default | ✓ | unit only | **PARTIAL (0.3)** | FHIR read API admin-only and off. ABDM off, uncertified. HL7 not mounted. |
| 8 | Prescriptions | ✓ | ✓ | ✓ verified | ✓ | ✓ pass | **PARTIAL (0.8)** | Allergy block on create verified. Fix RL-01. |
| 9 | Pharmacy & medicine inventory | ✓ | ✓ | ✓ verified | ✓ verified | ✓ pass (API), browser spec stale | **PARTIAL (0.85)** | Atomic stock and expiry refusal verified. No drug DB, schedule class, HSN or MRP (RL-26). |
| 10 | Dispensing & returns | ✓ | ✓ | ✓ verified | ✓ verified | ✓ pass | **PARTIAL (0.8)** | Cross-role dispense bypass (RL-02). Refund figures disagree (RL-11). |
| 11 | Laboratory (and imaging) | ✓ | ✓ | ✓ | ✓ | ✓ browser pass | **PARTIAL (0.8)** | Picker page-1 limit. No lab tariff, so lab revenue is null by design. |
| 12 | IPD & beds | ✓ | ✓ | ✓ | ✓ | ✓ browser pass | **PARTIAL (0.8)** | Admission picker shows only 50 patients, without UHID (RL-03). |
| 13 | Emergency | ✓ | ✓ | ✓ | ✓ | ✓ browser pass | **PARTIAL (0.8)** | Picker page-1 limit. |
| 14 | Billing & payments | ✓ | ✓ | ✓ verified | ✓ verified | ✓ pass | **PARTIAL (0.65)** | RL-03 (manual bill patient lookup), RL-04, RL-05, RL-12 (GST). No payment gateway or UPI integration. |
| 15 | Blood bank | ✓ | ✓ | ✓ | ✓ | backend unit only | **PARTIAL / NOT VERIFIED E2E (0.6)** | No browser or workflow test. Picker page-1 limit. |
| 16 | Procurement & suppliers | ✓ | ✓ | ✓ | ✓ | ✓ browser pass (3 specs) | **PARTIAL (0.8)** | Ward stock not tracked after issue. Consignment not linked to payables (CLAIMED). |
| 17 | Nursing & compounder | ✓ | ✓ | ✓ | ✓ | MAR browser pass | **PARTIAL (0.7)** | Compounder backend is thin (82 lines) and not exercised here. |
| 18 | Hospital services (OT, ambulance, mortuary, CSSD, laundry, leave) | ✓ | ✓ | ✓ | ✓ | ✓ browser pass (2 specs) | **PARTIAL (0.75)** | Leave only (no HR/payroll). No ambulance GPS. Feedback entered by staff only. |
| 19 | Users, roles, hospital admin | ✓ | ✓ | ✓ verified | ✓ | ✓ pass | **PARTIAL (0.7)** | Invite flow verified (single-use links). RL-02, RL-06. Role customisation can only narrow access. |
| 20 | Notifications | ✓ | partial | ✓ | ✓ | ✓ pass | **PARTIAL (0.35)** | In-app works. **SMS, WhatsApp and generic voice providers are stubs** (RL-17). Email via SMTP NOT VERIFIED. Voice and OTP-cleanup jobs on a dead queue (RL-08b). |
| 21 | Audit logs | ✓ | ✓ | ✓ verified | ✓ verified | ✓ pass | **COMPLETE (0.9)** | Verified: hospital create, invites, Rx create, Rx-item update, UHID issue, payments, refunds, returns, sensitive reads. |
| 22 | Reports & analytics | ✓ | ✓ | ✓ | ✓ | ✓ pass | **PARTIAL (0.6)** | Scheduled reports are CRUD-only and never delivered (RL-18). ML tables are unused scaffolding. |
| 23 | Admin dashboard | ✓ | ✓ | ✓ verified | ✓ | ✓ | **PARTIAL (0.8)** | Loads with 11 API calls and no failures. Permissions page is read-only. |

### Workflow readiness

**Ready for real users after the P0 fixes:**
- registration and UHID
- appointment → token → consultation
- prescription → pharmacy queue → dispensing → automatic bill → partial/full payment → return with refund
- paper prescription with second-person check
- lab order → result
- IPD admit/bed
- ER triage
- MAR dose
- procurement purchase order → receipt
- break-glass access
- family access

**Still manual or missing:**
- SMS, WhatsApp and voice reminders (stubs)
- scheduled report delivery
- off-site backups
- doctor onboarding (two steps)
- insurance claims and TPA (model only)
- online payments
- ABDM linking
- drug database and interaction checks beyond 8 starter rules
- Schedule H1 register
- lab price list

### What would make hospitals choose this product

Strengths that are verified here:
- four-eyes transcription of paper prescriptions
- automatic pharmacy billing with return refunds
- break-glass with review
- strict hospital isolation
- full audit trail
- Hindi UI (CLAIMED)

To compete with established Indian HMS products, it still needs:
- ABDM (M1–M3) and PM-JAY/TPA claims
- UPI/payment-gateway collection
- WhatsApp reminders
- GST-compliant invoices
- a licensed drug database
- offline-tolerant front desk
- reliable patient search everywhere

---

## C. Red-line issue register

Ordered by severity, then by impact. "Blocks production" means it must be fixed before real patient data. Every HIGH item below blocks production.

### HIGH

**RL-01: Prescription-item edit bypasses the allergy and interaction check** · Clinical safety · **VERIFIED**
- **Where:** [clinical/views.py:270](backend/clinical/views.py:270) `PrescriptionItemViewSet` and [clinical/serializers.py:203](backend/clinical/serializers.py:203) `PrescriptionItemSerializer`. The only `check_items` call is at [clinical/serializers.py:410](backend/clinical/serializers.py:410), in `PrescriptionSerializer.validate`.
- **Evidence:** the patient had a recorded penicillin allergy, and creating an amoxicillin Rx was correctly refused (400, "Recorded allergy: Penicillin"). The same doctor then sent `PATCH /api/clinical/prescription-items/1/ {"name":"Amoxicillin 500mg"}`. It returned **200**; the prescription showed the new medicine with `safety_alerts: []` and was dispensable. The edit is audited (`clinical.prescriptionitem.update`), so it is traceable afterwards, not prevented.
- **Impact:** an allergic patient can be dispensed the drug the check exists to stop.
- **Fix:** re-run `check_items` over the whole prescription on item create, update and delete, with the same override-reason rule; or make items immutable after creation and require a new prescription. Store the new alerts on the prescription.
- **Tests:** PATCH and POST of an allergenic item → 400 without an override reason; with a reason → 200, alerts stored and audited.

**RL-02: Cross-role dispensing (RBAC bypass for multi-hospital staff)** · Pharmacy / security · **VERIFIED**
- **Where:** [pharmacy/views.py:275](backend/pharmacy/views.py:275) looks the prescription up in `get_user_hospital_ids(request.user)` (every hospital the user belongs to). The role check uses the acting hospital from `X-Hospital-ID`. It is the only such lookup in the codebase.
- **Evidence:** user `audit.multi…` was Pharmacist at Hospital A and only Receptionist at Hospital B. With header A they **dispensed B's prescription** (201): B stock moved and B invoice `INV-6F45278B0AB5` was created. A plain A-only pharmacist got 404 for the same call.
- **Impact:** in hospital chains, one person's role at one site grants pharmacy powers at every site they belong to.
- **Fix:** filter by `self.get_acting_hospital_ids()`, and require the prescription's hospital to equal the acting hospital.
- **Tests:** the multi-role probe → 404/403; a single-hospital pharmacist is unaffected.

**RL-03: Patient pickers show only the 50 newest patients; manual billing matches by name** · Patient identification · **VERIFIED**
- **Where:** `api.patients.list(hospitalId)` with no search or page, so it returns page 1 of `PAGE_SIZE=50`. Affected callers:
  - [billing.jsx:423](src/pages/billing.jsx:423)
  - [IPD.jsx:80](src/pages/IPD.jsx:80)
  - [laboratory.jsx:114](src/pages/laboratory.jsx:114)
  - [Prescription.jsx:210](src/pages/Prescription.jsx:210)
  - [Radiology.jsx:73](src/pages/Radiology.jsx:73)
  - [BloodBank.jsx:64](src/pages/BloodBank.jsx:64)
  - [Emergency.jsx:99](src/pages/Emergency.jsx:99)
- **Name matching:** billing then picks the **first case-insensitive name match**, or a `P###` id derived from the database id ([billing.jsx:424-427](src/pages/billing.jsx:424)).
- **Evidence:** with 76 patients in Hospital A, the page-1 request billing makes did not contain the earlier patient "AUDIT Ravi Sharma". Two different patients with that exact name existed, both created during the test.
- **Impact:** past 50 registrations (day one for most hospitals), staff cannot select most patients on 7 screens. Billing can charge the wrong same-name patient. IPD's dropdown shows name, age and phone but no UHID.
- **Fix:** one shared server-side search picker (name, phone or UHID, min 2–3 chars, debounced) that shows UHID, age, sex and masked phone, selects by id, and never matches by name.
- **Tests:** a component test of the picker; a browser test with more than 50 seeded patients on each page; duplicate names → both shown with distinct UHIDs.

**RL-04: Double-submitted payments are recorded twice** · Billing · **VERIFIED**
- **Where:** [billing.jsx:681](src/pages/billing.jsx:681) builds `idempotency_key: \`${id}-${Date.now()}\`` at click time, and the submit button ([billing.jsx:1716](src/pages/billing.jsx:1716)) is never disabled while saving.
- **Evidence:** the server-side idempotency key works (identical replay → 200 returning the original payment). But the same ₹0.50 payment sent 10 times with per-click keys was accepted **4 times**, until the balance ran out.
- **Impact:** over-recorded collections and cash-reconciliation errors. Bounded by the bill's balance, which is also why full-balance double clicks are refused.
- **Fix:** create the key once when the form opens; disable submit while a request is in flight.
- **Tests:** a component test where a double click sends one request; an API test where the same key returns the same payment.

**RL-05: Refunds have no idempotency; a double click refunds twice** · Billing · **VERIFIED**
- **Where:** [billing/services.py:128](backend/billing/services.py:128) `record_refund` takes no key.
- **Evidence:** `POST /api/billing/invoices/1/refund/ {"amount":"1.00"}` sent twice → **201, 201**, and both refunds were recorded.
- **Impact:** a cash leak at the counter.
- **Fix:** accept an idempotency key and enforce uniqueness per invoice as payments do; guard the UI the same way.
- **Tests:** replay returns the first refund; 10 parallel refunds with one key → one row.

**RL-06: Production cannot start without Twilio Verify, even with OTP disabled** · Auth / go-live · **VERIFIED**
- **Where:** [production.py:471](backend/config/settings/production.py:471).
- **Evidence:** `manage.py check` under production settings raised `ImproperlyConfigured: TWILIO_… are required` without Twilio values, **and again with `STAFF_LOGIN_REQUIRE_OTP=False`**. With placeholder values it boots and `check --deploy` reports 0 issues.
- **Lockout risk:** every invited staff member has a phone number, so with the default `STAFF_LOGIN_REQUIRE_OTP=True` and no working Twilio, staff cannot sign in.
- **Impact:** with Twilio unavailable today, the only way to go live is placeholder secrets plus OTP off, which is an undocumented workaround.
- **Fix:** require Twilio only when SMS OTP is enabled. Add email OTP (already built for patients) or TOTP as the staff second factor. Document the Twilio-free mode. See section I-Twilio.
- **Tests:** settings boot with OTP off and no Twilio; with OTP on and no Twilio → ImproperlyConfigured; staff login with email OTP works.

**RL-07: No automated backups; patient documents never backed up; DR plan describes things that don't exist** · Data protection · **CODE + VERIFIED config**
- **Where:**
  - [scripts/backup.py](backend/scripts/backup.py) dumps PostgreSQL only and is run by hand.
  - Beat schedules no backup ([base.py:581](backend/config/settings/base.py:581)), and `backup.tasks.*` is routed but no such module exists ([base.py:567](backend/config/settings/base.py:567)).
  - The `media` volume holds uploaded patient documents ([docker-compose.prod.yml:218](docker-compose.prod.yml:218)) and is in no backup.
  - [DISASTER_RECOVERY.md:36](docs/DISASTER_RECOVERY.md:36) promises WAL streaming, 6-hourly incrementals, cloud copies and daily media backups. None is implemented.
- **Impact:** a disk failure loses all documents, plus all data since whenever someone last ran the script by hand.
- **Fix:** a scheduled encrypted DB + media backup to off-site storage; a restore drill on a schedule; alerts on a missed backup; rewrite the DR doc to match reality (RPO/RTO you can actually meet).
- **Tests:** a restore drill into a clean instance, with checksums of DB and media.

**RL-08: No React error boundary; any render error blanks the whole app** · Frontend reliability · **CODE**
- **Where:** [App.jsx:106](src/App.jsx:106) uses `<BrowserRouter>` + `<Routes>`, which have no `errorElement`. No `ErrorBoundary` or `componentDidCatch` exists in `src/`.
- **Impact:** one malformed record (for example a null where a page expects a string) leaves a white screen mid-shift, with no message and no recovery but a reload.
- **Fix:** an app-level and per-route error boundary with a "reload / go home" screen and error reporting.
- **Tests:** a component throws → fallback rendered, navigation still works.

**RL-08b: Voice-call fallback and OTP cleanup jobs are sent to a queue the production worker never reads** · Background jobs · **VERIFIED**
- **Where:** Celery's default queue is `celery` (nothing sets `CELERY_TASK_DEFAULT_QUEUE`). The production worker consumes only `-Q default,notifications,reports,ai_processing,audit,maintenance` ([docker-compose.prod.yml:132](docker-compose.prod.yml:132)).
- **Evidence:** Celery's own router resolved `notifications.tasks.place_voice_call` → `celery` and `notifications.tasks.cleanup_expired_otp` (hourly beat task) → `celery`; neither is consumed. `send_notification_channel` and `cleanup_old_audit_logs` are routed correctly.
- **Impact:** voice fallback never runs. Expired OTP rows holding phone numbers are never purged (retention and privacy). Messages pile up in Redis. Nothing reports the failure.
- **Fix:** `CELERY_TASK_DEFAULT_QUEUE = "default"`; add a startup check that every scheduled or routed task resolves to a consumed queue.
- **Tests:** a unit test asserting the route of each registered task is in the worker's `-Q` list.

**RL-09: Release pipeline is red and HEAD has never been through CI** · Process · **VERIFIED**
- **Evidence:** Playwright: **25 passed, 5 failed, 2 did not run** of 32.
  - [e2e/pharmacy.spec.js:44](e2e/pharmacy.spec.js:44) (4 tests) still wait for the `RX-2026-001` placeholder that HEAD deliberately changed.
  - [e2e/opd-to-bill.spec.js:33](e2e/opd-to-bill.spec.js:33) expects the old one-click token flow, replaced by the Issue-token dialog.
  - `713874d` and `ef09895` are not pushed. CI's `e2e` job gates every deploy job, so pushing as-is fails CI.
- **Impact:** the newest pharmacy and token UI has no passing browser test, and deploys are blocked.
- **Fix:** update the 5 specs to the new UI, push, get CI green.
- **Tests:** the full Playwright suite green in CI.

### MEDIUM

| ID | Issue | Evidence | Impact | Fix (tests) |
|---|---|---|---|---|
| RL-10 | Same patient + doctor + date + time booked twice | VERIFIED: A3b `POST /api/appointments/` twice → 201, 201 | Duplicate queue entries and reminders | Unique-while-active rule or 409 with the existing booking (API test for the duplicate → 409) |
| RL-11 | Pharmacy return shows `refund_amount` ₹10.00 (pre-GST, [dispensing.py:102](backend/pharmacy/dispensing.py:102)) while the bill refunds ₹11.20 (incl. 12 % GST) | VERIFIED: E5 | Counter staff see two different refund figures for one return | One source of truth, tax-inclusive, shown in both places |
| RL-12 | GST handling: invoice discount applied **after** tax ([services.py:71](backend/billing/services.py:71)); invoice numbers are random (`INV-9EA882EEC021`, [services.py:78](backend/billing/services.py:78)); no GSTIN, HSN or MRP fields | CODE + VERIFIED number format | Likely non-compliant tax invoices for pharmacy sales (CGST Rule 46 expects a consecutive serial per financial year). **Confirm with a CA.** | Pre-tax discount, per-FY series per hospital, GSTIN/HSN/MRP fields, tax summary on print |
| RL-13 | Hard deletes cascade: `Invoice.patient`/`Invoice.hospital` are CASCADE ([billing/models.py:14](backend/billing/models.py:14)); `PatientAdmin` allows deletion; `HospitalViewSet.perform_destroy` hard-deletes ([hospital/views.py:93](backend/hospital/views.py:93)) | VERIFIED with Django's deletion collector (no rows deleted): before any billing, deleting Hospital A would remove 50 rows with **0 protected**; after pharmacy billing, 13 PROTECT rows block it | A superuser click can erase a hospital's or patient's clinical and financial history before PROTECT links exist | PROTECT on clinical and financial FKs; soft-delete hospitals; disable delete in Django admin for patient-linked models |
| RL-14 | Allergy check reads allergies of the **current hospital only** ([medication_safety.py:83](backend/clinical/medication_safety.py:83)) | CODE | An allergy recorded at Hospital A is not checked at Hospital B of the same group | Policy decision: share allergies under consent across a group, or show "check other records" |
| RL-15 | Inviting a Doctor creates no `Doctor` profile | VERIFIED: B's doctor list was empty after the invite; it worked after a second `POST /api/doctors/` with the same email | Newly invited doctors can't be booked or sign prescriptions until an admin repeats the work | Create or link the profile in the invite step |
| RL-16 | Display ids `P###`, `D###`, `A###`, `SALE###` built from database ids (11 places, e.g. [billing.jsx:88](src/pages/billing.jsx:88), [EmergencyAccess.jsx:69](src/pages/EmergencyAccess.jsx:69)) | CODE | Staff see two different patient identifiers (UHID vs `P012`) on money and break-glass screens | Show UHID everywhere a patient is identified |
| RL-17 | SMS, WhatsApp and generic Voice providers are stubs that always fail ([providers.py:188](backend/notifications/services/providers.py:188), [:218](backend/notifications/services/providers.py:218)) and read different env names (`SMS_PROVIDER_*`) from OTP (`TWILIO_*`) | CODE | No appointment or queue SMS or WhatsApp in production; recorded honestly as failed | Implement Twilio Messaging/WhatsApp (section I) |
| RL-18 | Scheduled reports: full CRUD, no delivery task; signal handlers are `pass` ([reports/signals.py:21](backend/reports/signals.py:21)) | CODE | Users can "schedule" a report that never arrives | Implement a beat task + email, or hide the feature |
| RL-19 | Throttles in production: `user` 1000/h, `anon` 100/h per IP ([production.py:539](backend/config/settings/production.py:539)); patient OTP 5/min per IP | VERIFIED page cost: 5–13 API calls per page load | Peak-hour pharmacy and front desk can approach 1000/h. Indian mobile carrier-grade NAT puts many patients behind one IP. | Load-test real shift patterns; raise the per-user rate; key patient OTP by phone |
| RL-20 | Staff second factor depends entirely on SMS | CODE | Staff can't sign in when the SMS provider is down | Email OTP / TOTP fallback |
| RL-26 | Pharmacy catalogue lacks drug schedule (H/H1/X/NDPS), Schedule H1 register, manufacturer, MRP, HSN | CODE ([pharmacy/models.py](backend/pharmacy/models.py)) | Likely regulatory gaps for a hospital pharmacy. **Confirm with a pharmacist or legal.** | Schedule field, H1 register report, MRP cap |

### LOW

| ID | Issue | Evidence |
|---|---|---|
| RL-21 | Main JS chunk **649 kB (177 kB gzip)**; `KNOWN_LIMITATIONS.md` still says 310 kB | VERIFIED `vite build` |
| RL-22 | Docs out of date: [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) says pharmacy sales aren't linked to billing (fixed in HEAD); the DR doc (RL-07) | VERIFIED |
| RL-23 | `/api/hospital/hospitals/` is fetched twice on every page; `awaiting_final_bill` twice on Billing | VERIFIED page-load run |
| RL-24 | Sign-in page probes `/api/auth/dev/login/` in production builds (404, harmless; the backend gate requires DEBUG + 3 flags) | VERIFIED |
| RL-25 | Unused ML scaffolding tables (`MLModel`, `FeatureStore`, `DataPipeline`) | CODE |
| RL-27 | ESLint: 11 warnings (8 fast-refresh, 3 hook dependency) | VERIFIED |

---

## D. Reliability report

### Database

| Check | Result |
|---|---|
| PostgreSQL compatibility | **VERIFIED.** Full suite on PostgreSQL 16, 847 / 847, with row-lock tests required |
| Migrations | **VERIFIED.** `makemigrations --check` reports no changes; `migrate` on an empty PostgreSQL clean. Data-safety commands exist (`report_duplicate_uhids`, `assign_missing_uhids`, `assign_tenant_hospital`) |
| Constraints | UHID unique per hospital (case-insensitive); `InvoiceItem.pharmacy_sale` one-to-one; medicine `tax_rate` check 0–100. **Missing:** a unique constraint on `QueueToken.appointment` (a lock prevents it; CLAIMED follow-up); no uniqueness on appointment slot (RL-10) |
| Indexes | Present on hospital/status/date combinations (CODE). No slow-query analysis under volume: **NOT VERIFIED** |
| Delete safety | See RL-13 |
| Connections | `CONN_MAX_AGE=60`; health readiness checks DB, cache and Redis (CODE). DB restart recovery **NOT VERIFIED** in this audit |

### Concurrency (PostgreSQL, 10 parallel requests each, VERIFIED)

| Probe | Result |
|---|---|
| 10 registrations | 10 × 201, **10 unique UHIDs** |
| 10 token issues for one appointment | 1 × 201 + 9 × 200, **one token** |
| 10 dispenses of one prescription | 1 × 201 + 9 × 409, **stock deducted once** (100 → 95) |
| 10 full-balance payments (distinct keys) | 1 × 201 + 9 × 400; paid = total exactly |
| 10 small payments with per-click keys | **4 accepted** (RL-04) |
| Server errors during all probes | **0 × 5xx** |

### API

- **Latency:** every workflow call took 5–134 ms (single user).
- **Light load:** 400 requests from 20 concurrent clients on the Django dev server gave 0 errors, p50 217 ms, p95 362 ms, about 86 req/s. *Indicative only: single-process dev server, not gunicorn.*
- Error envelope is consistent (`{error, status_code, message, details}`). Validation messages are human-readable (verified across about 100 calls).

### Frontend

| Check | Result |
|---|---|
| Production build | VERIFIED |
| Page loads | 5–13 API calls per page, network idle in 0.6–1.0 s locally; no failed API calls after sign-in (VERIFIED, 16 pages × 5 roles) |
| Error boundary | **None (RL-08)** |
| Duplicate submits | Unguarded on Billing (RL-04) |
| StrictMode double fetch | Dev only |

### Infrastructure

| Check | Result |
|---|---|
| Containers | 7-service `docker-compose.prod.yml` with health checks and `restart: unless-stopped` (CODE). Rehearsal on 2026-11-03 is **CLAIMED**, not repeated here. |
| nginx | TLS, headers, `/media/` denial and rate zones (CODE) |
| Monitoring and alerting | **NOT DONE.** `MONITORING_ENABLED` defaults to False; Sentry only with a DSN; no uptime, disk or backup alerts |
| Logs | JSON to console; Django errors go to a file in the `app_logs` volume, which a log shipper must collect |

### Recovery scenarios

| Scenario | Verdict |
|---|---|
| Duplicate API requests | **Survives** (verified), except UI-generated per-click keys and refunds |
| Partial transaction failure | Dispense, bill and payment are atomic, all-or-nothing (CODE + tests) |
| Unexpected input | Validated (verified 400s with field messages) |
| Server or DB restart, network loss, slow responses | **NOT VERIFIED** in this audit |
| Failed background jobs | Notification sends retry 5× with backoff. Voice and OTP-cleanup jobs never run (RL-08b). |

---

## E. End-to-end workflow report

All runs used the real API on PostgreSQL 16 with `seed_demo` plus synthetic records; the browser runs used Chromium against the same code. Each step's status code, timing and database effect was checked.

### Workflow A: patient to pharmacy · **PASS with defects** (28/28 expected outcomes; 4 defects surfaced)

Steps, in order:
1. Register patient → `DCH-2026-000005`; the same phone again → 409 with the match shown.
2. Same-name second patient allowed.
3. Appointment.
4. Token (re-issue returns the same token).
5. Call → start consultation.
6. Vitals, penicillin allergy, ICD-10 diagnosis.
7. Amoxicillin Rx **blocked** (allergy).
8. Paracetamol Rx 201.
9. Dispense 201; second dispense 409.
10. Stock 200 → 185 → 190 after the return.

- **Endpoints:** `/api/patients/`, `/api/appointments/`, `/api/encounters/queue-tokens/{issue,call,start-consultation}/`, `/api/clinical/{vitals,allergies,diagnoses,prescriptions,prescription-items}/`, `/api/pharmacy-sales/dispense-prescription/`, `/api/pharmacy-sales/{id}/return/`.
- **Defects found:** RL-01 (item PATCH bypass), RL-10 (double booking), RL-11, RL-05.

### Workflow B: paper prescription · **PASS** (8/8)

| Step | Result |
|---|---|
| Pharmacist transcribes (outside prescriber + registration no.) | 201, Pending Verification |
| Dispense before verification | 400 |
| Self-verify | 403 |
| Receptionist verifies | 403 |
| Admin verifies | 200 |
| Dispense | 201, bill `INV-EF2BBA771387` ₹18.00 |
| Paper dated 200 days ago | 400 |

### Workflow C: hospital staff · **PASS** (22/22 after correcting one probe URL)

1. Admin creates Hospital B.
2. UHID prefix `AHB` set; the duplicate prefix `DCH` is refused.
3. Department created.
4. Doctor, Pharmacist, Receptionist, Billing and Nurse invited; each link accepted once, then refused on reuse.
5. B doctor's `staff/me` lists only Hospital B.
6. Receptionist cannot invite (403).
7. Audit log holds `hospital.create`, `users.staff.invited`.

Defect: RL-15 (no Doctor profile on invite).

### Workflow D: patient safety and isolation · **FAIL on one probe** (25/26)

| Probe | Result |
|---|---|
| A desk reads B patient by id | 404 ✓ |
| A desk spoofs `X-Hospital-ID: B` | 403 ✓ |
| A pharmacist reads or dispenses B Rx | 404 ✓ |
| A billing lists `?hospital=B` | 403 ✓ |
| Doctor2 reads doctor1's patient Rx | 404 ✓ |
| Receptionist reads diagnoses or notes, creates Rx | 403 ✓ |
| Pharmacist PATCHes a doctor's Rx | 403 ✓ |
| Billing reads Rx | 403 ✓ |
| Anonymous on 4 APIs | 401 ✓ |
| Forged JWT | 401 ✓ |
| Receptionist reads audit log | 403 ✓ |
| Portal patient reads another patient or invoice | 404 ✓ |
| **Pharmacist@A + Receptionist@B dispenses B's Rx** | **201 ✗ (RL-02)** |

### Workflow E: billing · **PASS with defects**

| Step | Result |
|---|---|
| Auto bill on dispense | `INV-9EA882EEC021`, ₹33.60 = 15 × ₹2.00 + 12 % GST ✓ |
| Partial ₹16.80 | Partially Paid ✓ |
| Same idempotency key replayed | 200, no double charge ✓ |
| Overpayment | 400 ✓ |
| Full payment | Paid, due 0.00 ✓ |
| Return 5 | bill total ₹22.40, refund ₹11.20, still Paid ✓ |
| Return more than sold | 400 ✓ |
| Manual refund sent twice | **2 refunds (RL-05)** |

Defects: RL-04, RL-11, RL-12.

### Browser (Playwright, existing suite, 32 tests) · 25 PASS / 5 FAIL / 2 NOT RUN

**Pass:**
- advance payment
- break-glass
- ICD-10 pick, AI discharge draft (mock provider), extra vitals
- ER triage
- family access (3)
- OT and ambulance and leave (2)
- IPD bed
- lab order → release; lab walk-in
- login (3)
- medication safety (3)
- MAR dose
- book appointment
- procurement (3)

**Fail (stale specs, RL-09):** issue token (1), pharmacy (4).

### Not tested in this audit

- Real SMS, WhatsApp, email or OTP delivery (no credentials)
- ABDM
- Hindi pages
- Mobile layouts
- Accessibility
- Printing
- Docker production stack
- Restore drill
- Server or DB restart

---

## F. Security report

**Verified strong:**
- **Tenancy:** fail-closed tenancy in [users/viewsets.py](backend/users/viewsets.py). Every model resolves its owning hospital or returns nothing; the acting hospital is honoured only if the user is a member.
- **Per-hospital roles:** a Doctor in A and Receptionist in B cannot list B's clinical rows by omitting the header (CODE + tests). The exception is RL-02.
- **Care scope:** doctors and nurses see only patients in their care (verified 404 for doctor2).
- **Production settings:**
  - JWT is RS256 with 10-minute access tokens, in httpOnly cookies.
  - Session and CSRF cookies are `Secure`, `HttpOnly` and `SameSite=Strict`; HSTS is preload.
  - `check --deploy` reports **0 issues** (verified).
- **Brute force:** staff login is limited 5/min per account and 60/min per IP, with account lockout. OTP and reset limits exist. nginx has zones too.
- **Uploads:** size, extension and libmagic content check.
- **Sensitive reads:** audited per request.
- **Break-glass:** a reason is required, the grant is time-limited, and a different person reviews it.
- **Dependencies:** `pip-audit` **0** known vulnerabilities in `requirements-lock.txt`; `npm audit --omit=dev` **0** (verified 2026-11-05).

**Open:**
- RL-01 (clinical safety bypass)
- RL-02 (cross-role privilege)
- RL-06 / RL-20 (second factor tied to SMS)
- RL-08b (PII-bearing OTP rows never purged)
- RL-13 (destructive deletes)
- RL-19 (throttle keys under NAT)
- No penetration test (L5, CLAIMED pending)
- Media files on a local volume with no backup or encryption at rest (RL-07)

**Privacy:** the phone number is masked in lookups; patient data never appears in URLs from the app (CODE). The DPDP gaps are in section G.

---

## G. Production deployment checklist

| # | Item | Status | Evidence / gap |
|---|---|---|---|
| 1 | PostgreSQL production configuration | **DONE** | Required `DATABASE_URL`; suite green on PG16 |
| 2 | Environment variable management | **PARTIALLY DONE** | Fail-fast on missing values; Twilio forced even when unused (RL-06) |
| 3 | Authentication & authorization | **PARTIALLY DONE** | Strong design; RL-01, RL-02 open |
| 4 | HTTPS & secure cookies | **PARTIALLY DONE** | Configured, `check --deploy` clean; never run on a real domain or CA cert |
| 5 | Docker production config | **NOT VERIFIED** | Rehearsal 2026-11-03 CLAIMED; not repeated for HEAD |
| 6 | Migration strategy | **DONE** | Clean migrations; pre-migration data checks |
| 7 | Static & media storage | **PARTIALLY DONE** | Hashed static via nginx; media on a local volume only |
| 8 | Logging | **PARTIALLY DONE** | JSON logs; errors in a file volume needing a shipper |
| 9 | Monitoring & alerting | **NOT DONE** | No metrics, uptime, disk or backup alerts |
| 10 | Error reporting | **PARTIALLY DONE** | Sentry hook, no DSN; no frontend error capture (RL-08) |
| 11 | Backup automation | **NOT DONE** | Manual script (RL-07) |
| 12 | Media backup | **NOT DONE** | RL-07 |
| 13 | Restore tested | **PARTIALLY DONE** | Drill CLAIMED (2026-11-03), not repeated |
| 14 | Disaster recovery plan matches reality | **NOT DONE** | DR doc describes WAL/PITR that doesn't exist |
| 15 | Deployment & rollback | **PARTIALLY DONE** | Documented; not exercised here |
| 16 | CI/CD | **PARTIALLY DONE** | Full pipeline exists; HEAD unpushed; E2E red (RL-09) |
| 17 | Security headers | **DONE** | `check --deploy` clean; nginx headers (CODE) |
| 18 | Rate limiting | **DONE** | Three layers; tuning risk RL-19 |
| 19 | Dependency vulnerabilities | **DONE** | 0 / 0 |
| 20 | Health checks | **DONE** | `/health/live`, `/health/ready` (DB, cache, Redis) |
| 21 | Background jobs | **PARTIALLY DONE** | Notification retries OK; dead queue (RL-08b) |
| 22 | Load testing | **NOT DONE** | Only the indicative dev-server probe |
| 23 | SMS / WhatsApp delivery | **NOT DONE** | Providers are stubs (RL-17) |
| 24 | OTP (Twilio Verify) | **NOT VERIFIED (blocked)** | Code exists; no credentials |
| 25 | Email delivery | **NOT VERIFIED** | SMTP configured by env; never sent for real |
| 26 | DPDP Act readiness | **NOT DONE** | See below |
| 27 | Clinical safety sign-off | **NOT DONE** | L4 CLAIMED pending; review pack exists |
| 28 | Penetration test | **NOT DONE** | L5 CLAIMED pending |

**Score: 11 / 28** (DONE = 1, PARTIALLY DONE = 0.5).

### India: legal requirements vs technical recommendations vs optional integrations

*Not legal advice; confirm with counsel and a CA.*

#### Legal: DPDP Act 2023 and DPDP Rules 2025

The Rules were notified in November 2025 with phased commencement; confirm the dates that apply to you.

- **Already in place:** consent records, revocation, record shares and a share access log ([consent/](backend/consent/), tested in `security_tests/test_consent_sharing.py`); audit trails.
- **Missing:**
  - itemised notice at collection
  - data-principal requests: access/summary, correction, erasure, grievance, nominee
  - a published grievance officer contact and response SLA
  - a breach-notification procedure (Board + affected people)
  - a retention schedule tied to medical-record law
  - a processor (vendor) register: Twilio, email, AI provider
  - children's data / guardian consent rules
  - a DPIA if notified as a Significant Data Fiduciary

#### Legal: other regimes (confirm)

- **Medical-record retention:** NMC/MCI guidance (3 years for in-patient records) and state Clinical Establishments rules. `AUDIT_LOG_RETENTION_DAYS` and the cleanup task must not delete records you are required to keep.
- **Drugs & Cosmetics Rules:** Schedule H1 register (RL-26).
- **GST invoice rules:** RL-12.

#### Technical recommendations

- encryption at rest for DB and media
- off-site backups
- monitoring
- pen test
- staff second factor not tied to one SMS vendor
- an access review report per hospital

#### Optional integrations (not legally mandatory for a private hospital, but often commercially required)

- **ABDM (ABHA, HIP/HIU, M1–M3):** routes exist but are off; needs sandbox, certification and NRCeS FHIR profiles.
- **FHIR R4:** read-only, admin-only, off.
- **HL7 v2:** not mounted.
- **PM-JAY / TPA / NHCX claims:** model only.

---

## H. Remaining work

Effort is in focused developer-days for someone who knows the codebase, excluding review and waiting on third parties.

### P0: must fix before production

| ID | Task | Reason | Files / modules | Depends on | Effort | Acceptance criteria | Verification |
|---|---|---|---|---|---|---|---|
| P0-01 | Re-check medication safety on every item change, or make items immutable | RL-01 | `clinical/views.py`, `clinical/serializers.py` | — | 1 d | Allergenic item via POST/PATCH → 400 unless an override reason; alerts stored | New unit tests + the A13 probe |
| P0-02 | Scope dispense lookup to the acting hospital | RL-02 | `pharmacy/views.py:275` | — | 0.5 d | Multi-role probe → 404 | Unit test with a two-hospital, two-role user |
| P0-03 | Shared server-side patient search picker with UHID, used on 7 pages; remove name matching in billing | RL-03, RL-16 | `billing.jsx`, `IPD.jsx`, `laboratory.jsx`, `Prescription.jsx`, `Radiology.jsx`, `BloodBank.jsx`, `Emergency.jsx`, new `components/PatientPicker.jsx` | — | 3 d | Any of 500+ patients selectable by name, phone or UHID; same-name patients distinguishable | Component tests; browser test with 60+ patients |
| P0-04 | Payment and refund idempotency end to end | RL-04, RL-05 | `billing.jsx`, `billing/services.py`, `billing/views.py`, migration (refund key) | — | 1.5 d | Double click = one payment and one refund | API replay + parallel tests; component double-click test |
| P0-05 | Fix the Celery default queue; add a route test | RL-08b | `config/settings/base.py`, `production.py` | — | 0.5 d | Every task resolves to a consumed queue | Unit test over registered tasks |
| P0-06 | Automated encrypted DB + media backups off-site, restore drill, alert on a miss; rewrite the DR doc | RL-07 | `scripts/backup.py`, compose or host cron, `docs/DISASTER_RECOVERY.md` | Storage account | 3 d | Nightly DB + media in off-site storage; documented RPO/RTO met in a drill | Restore into a clean host, checksums match |
| P0-07 | App and route error boundaries with error reporting | RL-08 | `src/App.jsx`, new `ErrorBoundary.jsx` | — | 1 d | A thrown render error shows a recovery screen | Component test |
| P0-08 | Update the 5 stale Playwright specs, push, CI green | RL-09 | `e2e/pharmacy.spec.js`, `e2e/opd-to-bill.spec.js` | — | 1 d | 32/32 locally and in CI | CI run on the PR |
| P0-09 | Decouple boot from Twilio; add a staff email-OTP or TOTP second factor | RL-06, RL-20 | `config/settings/production.py`, `users/views.py`, `StaffLogin.jsx` | — | 2–3 d | Prod boots without Twilio when SMS OTP is off; staff sign in with the second factor | Settings tests; login tests |
| P0-10 | Staging rehearsal on a real domain and CA cert; monitoring and alerting (Sentry DSN, uptime, disk, backup age) | Checklist 4, 5, 9 | Deployment | Domain, host | 2–3 d | Staging passes `DEPLOYMENT.md` steps 1–8; alerts fire on test faults | Rehearsal log |

**P0 total ≈ 16–18 developer-days.**

### P1: before onboarding a real hospital

| ID | Task | Reason | Effort | Acceptance |
|---|---|---|---|---|
| P1-01 | Clinical safety officer sign-off (MAR, discharge, lab release, AI draft, break-glass, transcription) | L4 | external + 2 d fixes | Signed review pack |
| P1-02 | Penetration test + remediation | L5 | external + 3 d | Report with no open high findings |
| P1-03 | DPDP: notice, rights request workflow (access, correct, erase-where-lawful, grievance), breach runbook, retention schedule, processor list | Section G | 6–8 d | Requests logged, actioned, audited within SLA |
| P1-04 | Prevent duplicate bookings (RL-10); unique constraint on `QueueToken.appointment` after a duplicate report | RL-10 | 1 d | 409 on a duplicate; migration safe on existing data |
| P1-05 | One tax-inclusive refund figure (RL-11); GST invoice compliance (RL-12) with CA input | RL-11, RL-12 | 3–4 d | CA-approved invoice format; per-FY series |
| P1-06 | Doctor profile created in the invite step | RL-15 | 1 d | Invited doctor bookable at once |
| P1-07 | Decide cross-hospital allergy visibility | RL-14 | 1–2 d | Documented policy, implemented and tested |
| P1-08 | Load test realistic shifts on gunicorn + PostgreSQL; tune throttles (patient OTP keyed by phone) | RL-19 | 2–3 d | p95 < 1 s at target users; no 429 for normal work |
| P1-09 | Twilio Messaging/WhatsApp providers (when credentials arrive) | RL-17 | 3–4 d | Real delivery recorded as sent, with receipts |
| P1-10 | Pharmacy regulatory fields: schedule, H1 register, MRP, HSN | RL-26 | 3 d | H1 register report; sale above MRP refused |
| P1-11 | Guard hard deletes (PROTECT, admin delete off, soft-delete hospitals) | RL-13 | 1.5 d | Deletion collector shows no CASCADE into clinical or financial tables |

### P2: important improvements

| ID | Task | Effort |
|---|---|---|
| P2-01 | Deliver scheduled reports or hide the feature (RL-18) | 1–2 d |
| P2-02 | Bundle splitting back under ~350 kB (RL-21) | 1 d |
| P2-03 | Remove redundant fetches (RL-23) | 0.5 d |
| P2-04 | Refresh `KNOWN_LIMITATIONS.md`, DR and README to match HEAD (RL-22) | 1 d |
| P2-05 | Hindi review by clinical staff; mobile and accessibility pass (both NOT VERIFIED here) | 3–5 d |
| P2-06 | Lab tariff, so lab revenue and lab bills exist | 2 d |
| P2-07 | Blood bank and compounder browser workflows + tests | 2 d |
| P2-08 | Remove unused ML scaffolding (RL-25) | 0.5 d |
| P2-09 | Note templates in the editor; patient-portal feedback | 2 d |

### P3: future enhancements

- ABDM M1–M3 + NRCeS FHIR profiles
- UPI / payment gateway
- TPA / PM-JAY / NHCX claims
- licensed drug database with dose-range checks
- HL7 v2
- ambulance GPS
- HR attendance and payroll
- offline-tolerant front desk

---

## I. Twilio: what works without it, and what remains

**Works without Twilio today (verified unless noted):**
- every clinical, pharmacy, billing, lab, IPD, ER and admin workflow
- staff password sign-in (with `STAFF_LOGIN_REQUIRE_OTP=False`)
- patient email/password and email OTP (needs SMTP; NOT VERIFIED)
- in-app notifications
- the full audit trail

**Blocked or degraded without Twilio:**
1. **Production boot:** refused (RL-06). Workaround: placeholder values; real fix: P0-09.
2. **Staff SMS OTP:** with OTP on, invited staff (who all have phones) can't sign in.
3. **Patient SMS OTP** (`PATIENT_OTP_DELIVERY=sms`).
4. **SMS and WhatsApp reminders:** these also need implementing, not just credentials (RL-17).
5. **Voice-call fallback:** also needs the RL-08b fix.

**Exact remaining Twilio integration work, once credentials exist:**
1. Verify Service SID + API key; send and check OTP from staging to a real Indian number. Confirm DLT registration of the sender and template with Twilio's India requirements.
2. Implement `SMSProvider.send` and `WhatsAppProvider.send` via Twilio Messaging (approved WhatsApp templates); unify env names with `TWILIO_*`.
3. Delivery-status webhook (signature-validated) updating `NotificationDelivery` to delivered/failed.
4. Voice: `VOICE_CALL_PROVIDER=twilio`, a voice-capable number, a real test call (after RL-08b).
5. Monitoring: alert on OTP failure rate and Twilio balance.
6. Add Twilio to the DPDP processor list.

**Estimate:** ≈ 4–6 developer-days plus DLT/WhatsApp approval lead time.

---

## J. Final verdict

1. **What percentage is genuinely complete?** About **60 %** toward a production-ready product: 73 % functional, 39 % operational readiness (method in section A).
2. **How much work remains?** About **16–18 developer-days** of P0 engineering, **≈ 30–40 days** of P1, plus external work: clinical safety review, pen test, CA and legal input, Twilio/DLT approvals. Realistically **6–10 weeks** to a first supervised hospital go-live with one developer.
3. **Can a real hospital safely use it today?** **No.** RL-01 (allergy bypass), RL-03 (wrong or unfindable patients past 50 records), RL-07 (no backups) and RL-06 (cannot boot without Twilio) each block it on their own.
4. **Can it handle multiple hospitals?** **Yes, architecturally, and isolation is verified:** 13 cross-hospital probes refused, separate UHID series (`DCH-…`, `AHB-…`). One gap: users with different roles in different hospitals (RL-02).
5. **Can it handle concurrent users reliably?** **For data integrity, yes:** every duplicate-request race tested on PostgreSQL resolved correctly, with no 5xx errors. **For capacity: not verified.** The only load probe was indicative (86 req/s on a dev server); no load test on the production stack, and throttles may bite at peak (RL-19).
6. **Are patient records and billing data safe?** **Access control: largely yes** (verified). **Durability: no** (RL-07). **Money: mostly, except** double-submitted payments and refunds (RL-04, RL-05) and GST format (RL-12). **Clinical: not yet** (RL-01).
7. **Top 10 remaining tasks:** P0-01 to P0-10 in section H, in that order.
8. **What must be done before production?** All P0 items, plus P1-01 (clinical sign-off), P1-02 (pen test) and the DPDP minimum in P1-03 (notice, grievance contact, breach runbook).
9. **What can wait until after the first hospital?**
   - P1-09 (SMS/WhatsApp; in-app and email cover the pilot)
   - P1-10, if the pilot pharmacy keeps a paper H1 register
   - all P2 and P3
   - ABDM, unless the pilot hospital needs ABHA or PM-JAY on day one
10. **Recommended next phase:** a **2-week "go-live hardening" sprint**:
    1. Week 1: P0-01 to P0-05, P0-07 and P0-08, each with tests, CI green.
    2. Week 2: P0-06, P0-09, P0-10 on a staging host with a real domain, then a supervised dry run with hospital staff on synthetic data.

    Then a single-hospital pilot with paper fallback, while the clinical review, pen test and DPDP work run in parallel.

---

### Appendix: test and command results (this audit, 2026-11-05)

| Suite / command | Total | Passed | Failed | Skipped | Errors | Not run | Notes |
|---|---|---|---|---|---|---|---|
| `manage.py check` / `makemigrations --check` | — | ✓ | — | — | — | — | No issues, no changes |
| Backend, SQLite (`--parallel 4`) | 847 | 830 | 0 | 17 | 0 | 0 | 17 skips = PostgreSQL-only row-lock tests, by design |
| Backend, PostgreSQL 16, `REQUIRE_ROW_LOCK_TESTS=1` | 847 | 847 | 0 | 0 | 0 | 0 | 49 s |
| Vitest | 105 (29 files) | 105 | 0 | 0 | 0 | 0 | |
| ESLint | — | 0 errors | — | — | — | — | 11 warnings |
| `vite build` | — | ✓ | — | — | — | — | 649 kB main chunk warning |
| Playwright (Chromium) | 32 | 25 | 5 | 0 | 0 | 2 | Failures are stale specs (RL-09) |
| API workflow probes A–E | 90 steps | 88 as expected | 2 defects (A13 bypass, D20) | — | 0 | — | Plus 4 further defects observed (RL-04, RL-05, RL-10, RL-11) |
| Concurrency probes | 6 × 10 parallel | 5 | 1 (RL-04) | — | 0 × 5xx | — | |
| `pip-audit` (lock file) | — | 0 vulns | — | — | — | — | |
| `npm audit --omit=dev` | — | 0 vulns | — | — | — | — | |
| `check --deploy` (production settings, synthetic env) | — | 0 issues | — | — | — | — | Needs placeholder Twilio values to boot |

**Not executed:**
- Docker production stack (time; claimed 2026-11-03)
- real-provider delivery (no credentials)
- restart and failover tests
- formal load test
- accessibility, mobile and Hindi review
