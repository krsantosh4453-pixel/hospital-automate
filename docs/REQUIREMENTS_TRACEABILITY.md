# Requirements Traceability Matrix

Status as of 2026-10-25, branch `audit/production-readiness-2026-10-24` (commit after `fd3ff71`).

**Sources**

- **UI** = `HMS_UI_Structure.md` (section number).
- **P1–P4** = `Hospital_Management_FINAL_MultiHospital_AI.pdf` Parts 1–4.
- **AI** = PDF "AI-First Clinical Consultation".
- **CALL** = PDF "AI Intelligent Call System".
- **MH** = PDF "Multi-Hospital Patient Entry System".

Both documents were read in full. The PDF is 43 pages and contains no images (verified: every page reports 0 embedded images), so the extracted text covers it completely.

**Status values**

| Status | Meaning |
|---|---|
| `VERIFIED` | Short for COMPLETE_AND_VERIFIED. Backend and UI exist, and behaviour is proven by an automated test, a live browser check against a seeded test backend, or both. |
| `IMPLEMENTED` | Short for IMPLEMENTED_NOT_FULLY_VERIFIED. Code exists and is wired up, but the full workflow was not exercised end to end. |
| `PARTIAL` | Some of the requirement exists. |
| `PLACEHOLDER` | Screen or code exists, but it shows or stores nothing real. |
| `MISSING` | Not implemented. |
| `BROKEN` | Implemented but known not to work. |
| `BLOCKED` | Needs external credentials, approvals or infrastructure. |
| `N/A` | Not applicable, with the justification given in the row. |

**Evidence codes**

- **T:file**: an automated test in `backend/security_tests/` or an app `tests.py`.
- **B**: a live browser check against the production build and a seeded test backend (2026-10-25).
- **R**: code review only.

## A. Platform and access management

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| A1 | Super/System admin: hospital list, add, edit | UI 3.1 | VERIFIED | `hospital/views.py` HospitalViewSet (create/delete = platform superuser; edit = that hospital's Admin/Manager); `pages/admin/Hospitals.jsx` | T:test_rbac_and_writes (OrganisationStructure), B |
| A2 | Hospital configuration (code, type, contact) | UI 3.1 | VERIFIED | Hospital.code / hospital_type | T, B |
| A3 | Multi-hospital tenancy and data isolation | MH 4, MH 6, P2 13 | VERIFIED | `users/viewsets.py` HospitalScopedViewSet (fails closed), X-Hospital-ID header | T:test_tenant_isolation (67 models × list/detail), test_rbac_and_writes |
| A4 | Staff login (username/password, hospital-aware) | UI 1.1 | VERIFIED | `users/views.py` staff_login, lockout | T:test_auth, B |
| A5 | Staff SMS OTP (second factor) | UI 1.1 | IMPLEMENTED | Twilio Verify; signed challenge binds OTP to password | T:test_auth (Twilio mocked). Real SMS: BLOCKED (no Twilio credentials) |
| A6 | Forgot password / OTP reset | UI 1.1 | IMPLEMENTED | password/reset, password/reset/confirm | T:test_auth (mocked SMS). Real SMS: BLOCKED |
| A7 | Patient OTP login (name + mobile → OTP) | MH 1, UI 1.2 | IMPLEMENTED | `users/patient_auth.py` | R, existing tests. Real SMS: BLOCKED. Gap: only patients who already have a login can use it, and family members sharing one phone are rejected (see KNOWN_LIMITATIONS) |
| A8 | Patient selects hospital after login | MH 2 | VERIFIED | Hospital directory + PatientLayout auto-select / picker | B |
| A9 | Hospital switcher for staff | UI 1.1, 2 | VERIFIED | Navbar → selectedHospital → X-Hospital-ID | B, T (header tests) |
| A10 | User management | UI 3.1 | VERIFIED | `/api/users/` + `pages/admin/Users.jsx` | T:test_staff_admin, B |
| A11 | Roles and permissions matrix | UI 3.1 | VERIFIED | Server-side role classes per membership; read-only matrix page | T (role-per-hospital tests), B |
| A12 | Delegated / proxy access rules | UI 3.1, P1 10 | MISSING | — | Consent forms record proxy signature only |
| A13 | Departments / clinics setup | UI 3.2 | VERIFIED | Department API (code, head) + page | T, B |
| A14 | Security settings screen | UI 3.1 | VERIFIED | Admin → Security settings (`/admin/security`): effective OTP, dev sign-in, token lifetimes, cookie/HTTPS/HSTS, password rules and rate limits, each marked recommended or not for production. Read only by design (environment variables); no secrets returned | users.test_security_settings (4); browser 2026-10-28 |
| A15 | Audit log viewer (admin only) | UI 3.1, 6 | VERIFIED | Admin → Audit log (`/admin/audit`): filters by action, record type, user and dates; newest first; read only | T:test_rbac_and_writes (AuditTrail), audit.tests.AuditLogFilterTests (5); browser 2026-10-28 |
| A16 | Role-specific dashboards and navigation | UI 2, 3 | IMPLEMENTED | Sidebar uses `canView`; ProtectedRoute checks backend roles | B (Admin role only) |
| A17 | Hindi / English toggle | UI 2, P1 | PARTIAL | LanguageContext: navigation, patient menu and AI label translated; page bodies are English | B |
| A18 | Breadcrumb bar | UI 2 | MISSING | — | — |
| A19 | Patient context strip (sticky) | UI 2 | MISSING | — | — |
| A20 | Global patient search (UHID / name / mobile) | UI 2, 6 | VERIFIED | `/api/patients/?search=` matches name, phone and the acting hospital's UHIDs (never another hospital's) | patients.tests (2 UHID tests); browser 2026-10-28 |
| A21 | Notifications bell / notification center | UI 2, 6 | VERIFIED | Header bell (`HeaderMenus.jsx` NotificationsMenu) lists the hospital's notifications and marks them read | T:test_notifications; browser 2026-10-28 |

## B. Patient registration and portal

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| B1 | Register patient and retrieve persisted record | P1 4.1 | VERIFIED | PatientViewSet | T:test_e2e_workflows |
| B2 | UHID per hospital | MH 5, P1 4 | IMPLEMENTED | PatientHospital.uhid | R |
| B3 | Full demographics (DOB, marital status, ID type, address parts, payer) | P1 4.1 | VERIFIED | Patients form → More details: DOB, marital status, address line / city / district / state / PIN, ID type with only the last 4 characters (full government ID numbers are not stored), payer type / name / policy | patients.tests (3 demographic tests); browser 2026-10-28 |
| B4 | Emergency contact / relative | P1 4.1 | VERIFIED | `patients.tests` (4 emergency-contact tests); browser check 2026-10-28 | Added 2026-10-28: name, relation, phone on the patient; a name needs a phone |
| B5 | Duplicate prevention / existing-patient match | — | VERIFIED | Staff registration with a mobile number already registered at that hospital returns 409 with the matches; staff open the existing record or confirm a different person (`confirm_new`). Other hospitals' patients are never shown | patients.tests (3 duplicate tests); browser 2026-10-28 |
| B6 | Patient portal home | MH 3, UI 4 | VERIFIED | `pages/patient/*` | B |
| B7 | Book appointment (specialty → doctor → slot) | UI 4 | IMPLEMENTED | Patient appointment page | B (render only) |
| B8 | My appointments / queue token status | UI 4 | IMPLEMENTED | PatientQueue (15 s polling) | B (render only) |
| B9 | Medical records (longitudinal EHR, read-only) | UI 4, P1 9 | PARTIAL | Lab, prescriptions and documents per hospital; no combined timeline | B |
| B10 | Prescriptions / lab reports (released only) | UI 4 | VERIFIED | Patients see only Released lab results | T:test_e2e_workflows |
| B11 | Documents upload / view by folder | P4 11, UI 4 | VERIFIED | Hospital-scoped, content-checked, audited downloads | T:test_documents |
| B12 | Consent and record sharing (recipient, scope, expiry, revoke, audit) | UI 4, P1 10 | VERIFIED | `consent/` app + PatientConsent page | T:test_consent_sharing, B (signing) |
| B13 | Proxy / caregiver management | UI 4 | MISSING | — | — |
| B14 | Language / communication preferences | UI 4 | PARTIAL | Language: yes. Channel opt-in/out: API only (`consents/grant`, `revoke`) | T:test_notifications |
| B15 | Notification history (SMS / WhatsApp / voice log) | UI 4 | PARTIAL | `/api/notifications/deliveries/` (staff); no patient page | T:test_notifications |

## C. Appointments, reception and OPD

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| C1 | Appointment booking, calendar, status | P1 3 | VERIFIED | AppointmentViewSet | T:test_e2e_workflows, appointments tests |
| C2 | Cancel / reschedule | P1 3 | IMPLEMENTED | Actions exist | Existing tests |
| C3 | Appointment → visit → queue token | P1 4.4, CALL 1 | VERIFIED | `queue-tokens/issue/` (previously always 500) | T:test_e2e_workflows, test_notifications |
| C4 | Visit dashboard (new / nurse-seen / doctor-seen / completed) | P1 4.5, UI 3.3 | PARTIAL | Queue statuses; no nurse-seen state | R |
| C5 | Token call, call-next, skip, complete | CALL 3 | IMPLEMENTED | encounters actions | Existing tests |
| C6 | Waiting-time estimate | P1 3.3, CALL 3 | IMPLEMENTED | QueuePredictionService (rule-based, not ML) | R |
| C7 | Emergency quick entry | UI 3.3 | IMPLEMENTED | EmergencyVisit | Existing tests |
| C8 | OPD billing | UI 3.3 | VERIFIED | See H | T |

## D. Doctor consultation and EMR

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| D1 | Vitals (BP, temperature, pulse, RR, SpO2, height, weight, sugar) | P1 5.2, P4 1 | VERIFIED | VitalSign | T:test_e2e_workflows |
| D2 | Extra vitals (BMI, urine output, AVPU, trauma, mobility, O2, intake/output), recorder | P4 1 | MISSING | — | — |
| D3 | Allergies | P1 5 | IMPLEMENTED | Allergy (now hospital-scoped) | T (isolation) |
| D4 | Current medication / complaint / history and examination | P1 5 | PARTIAL | ClinicalNote free text; no structured sections | R |
| D5 | Diagnosis with ICD-10, type, responsible clinician | P1 6 | VERIFIED | Diagnosis.icd10_code, recorded_by | T:test_e2e_workflows |
| D6 | ICD-10 search by name / code | P1 6 | MISSING | Code is free text; no terminology table | — |
| D7 | Investigation / procedure orders | P1 5, P4 2 | IMPLEMENTED | ServiceOrder, Procedure, LabTest | T (lab flow) |
| D8 | Prescription medicine | P1 5 | VERIFIED | Prescription + items; UI saves only on server success | T:test_e2e_workflows |
| D9 | Advice | P1 5 | PARTIAL | Prescription item instructions only | R |
| D10 | Medical certificate | UI 3.4 | VERIFIED | `clinical.test_certificates_referrals` (10); `PrintSheet.test.jsx`; browser check 2026-10-28 | Added 2026-10-28: Consultation → Certificates & referrals. Signed by the requesting doctor's profile; never edited or deleted; patients read their own |
| D11 | Refer to doctor | UI 3.4 | VERIFIED | `clinical.test_certificates_referrals` (6); browser check 2026-10-28 | Added 2026-10-28: to a doctor of the same hospital or an outside facility; only the status changes later; printable letter |
| D12 | Previous visits / timeline | UI 3.4 | PARTIAL | Visit list per patient; no timeline view | R |
| D13 | Discharge summary authoring and finalization | P3, P4 7 | VERIFIED | Finalize action (linked doctor), locked after; discharge requires it | T:test_e2e_workflows |
| D14 | Corrections and history of clinical records | Brief 7 | IMPLEMENTED | Audit stores old → new values on every update | T (audit) |
| D15 | Vaccination | P1 5 | MISSING | — | — |

## E. Nursing and inpatient

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| E1 | Nursing station list (admitted patients) | P3 35 | VERIFIED | Nurses page lists IPD admissions | B |
| E2 | Admission, ward / room / bed allocation | P3 | VERIFIED | allocate_bed (row-locked) | T:test_e2e_workflows |
| E3 | Nursing notes, shift assessments | P3 36 | VERIFIED | API + Nurses page (saves to server) | T:test_e2e_workflows, B |
| E4 | Nursing vitals (on admitted patients) | P3 36 | IMPLEMENTED | Saved as Focused nursing assessment with vitals | R (UI wired; not browser-saved) |
| E5 | MAR states: due, next due, delay, administered, not given, excluded, PRN | P4 5 | VERIFIED | Scheduled / Administered / Held / Refused / Missed / Vomited / Excluded, is_delayed, PRN | T:test_mar_safety, B (dose given via UI) |
| E6 | Bed transfer / doctor transfer | P3 | IMPLEMENTED | admissions transfer action | Existing tests |
| E7 | Discharge planning checklist | P3 34, P4 7 | VERIFIED | Four-item checklist on DischargePlan, ticked from IPD → Discharges; `complete_discharge` refuses until every item, the signed summary and the paid final bill are done (`readiness` lists what is left). Ward nurses keep the patient in care during discharge | ipd.test_discharge_readiness (11), ipd.tests, test_e2e_workflows; browser 2026-10-28 |
| E8 | Discharge notes | P4 7 | IMPLEMENTED | DischargeNote | R |
| E9 | Sample collection / dispatch from ward | P4 3 | VERIFIED | Nurse can collect and dispatch | T:test_e2e_workflows |
| E10 | Drug / consumable order | P4 4 | PARTIAL | Via prescriptions only | R |
| E11 | Blood request / receive / return | P4 6 | IMPLEMENTED | bloodbank requests / transactions | Existing tests |
| E12 | Final billing at discharge | P3 | VERIFIED | Billing → Discharge bills: one live final invoice per stay (`Invoice.admission`), bed days × daily rate plus extra lines; discharge waits for it to be paid | ipd.test_discharge_readiness; browser 2026-10-28 |

## F. Pharmacy and medication safety

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| F1 | Prescription queue → dispensing | P2 4 | VERIFIED | Sale linked to prescription; stock deducted atomically | T:test_e2e_workflows |
| F2 | Stock deduction with ledger | P2 7 | VERIFIED | StockTransaction OUT / IN / ADJUST | T:test_financial_integrity |
| F3 | Batch and expiry tracking; expired batches blocked | P2 4 | VERIFIED | Expired sale refused | T |
| F4 | OPD sale | P2 4 | VERIFIED | Server-side price | T |
| F5 | OPD / IPD returns | P2 4 | MISSING | — | — |
| F6 | Barcode scan | P2 4 | PARTIAL | Sample `barcoded` flag; no scanner flow | R |
| F7 | Drug interaction / contraindication alerts | P2 4 | MISSING | No drug database. Must not be presented as available. | — |
| F8 | Generic / substitute | P2 4 | MISSING | — | — |

## G. Laboratory and radiology

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| G1 | Orders, collection, lab number, dispatch, receive, process | P4 3 | VERIFIED | LabTest actions; lab number generated | T:test_e2e_workflows, B (page) |
| G2 | Result entry, verification, release (lab staff only) | UI 3.7 | VERIFIED | Role-restricted actions; status not editable directly | T |
| G3 | Result printing / export | UI 3.7 | IMPLEMENTED | `PrintSheet.test.jsx` (released-only, abnormal flags) | Added 2026-10-28: print / Save-as-PDF on the Laboratory page and patient Lab reports, released results only. Not clicked through in a browser |
| G4 | Radiology | P1 | PARTIAL | Treated as lab test type only | R |
| G5 | Collection queue view (patient, UHID, lab no., ward, count) | P4 3 | PARTIAL | Lab page list; no ward / UHID columns | B |

## H. Billing, payments and insurance

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| H1 | Invoice line items, quantity, subtotal, discount, tax, total (server computed, Decimal) | P2 16, P4 8 | VERIFIED | `billing/services.py` | T:test_financial_integrity |
| H2 | Payments, receipts, outstanding balance | P2 6 | VERIFIED | record_payment (row lock, idempotency) | T |
| H3 | Refunds | P2 6 | VERIFIED | refund action | T |
| H4 | Advance payments | P2 6 | MISSING | Payments cannot exceed the bill | — |
| H5 | Duplicate-payment prevention | Brief 4 | VERIFIED | Idempotency-Key | T |
| H6 | Insurance / TPA claims | UI 3.8 | IMPLEMENTED | InsuranceClaim (amount ≤ invoice) | Existing tests |
| H7 | Invoice PDF / export | P2 16 | IMPLEMENTED | Layout shared with the tested PrintSheet | Added 2026-10-28: patient Bills page prints the invoice with payments (browser "Save as PDF"); staff Billing already had Print Bill. Not clicked through in a browser |
| H8 | IPD / discharge billing | UI 3.8 | VERIFIED | Same as E12: started days are counted on the server; billing roles see only patient name, dates and days, not the admission record | ipd.test_discharge_readiness; browser 2026-10-28 |

## I. Inventory and supply chain

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| I1 | Suppliers, purchase orders, GRN, stock ledger | P2 5 | IMPLEMENTED | procurement app | procurement tests (36) |
| I2 | Purchase requisition → approval | P2 5 | MISSING | — | — |
| I3 | Opening stock / stock adjustment | P2 5 | VERIFIED | Ledger entries on create and correction | T |
| I4 | Supplier return, department issue, consignment, quotation | P2 5 | MISSING | — | — |
| I5 | Expiry monitoring | P2 5 | IMPLEMENTED | Pharmacy alerts, KPIs | B (page renders) |
| I6 | CSSD / laundry | P2 5, UI 3.9 | MISSING | — | — |

## J. Emergency and other services

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| J1 | ER patient list, triage, vitals, orders, medication | P4 12–13 | IMPLEMENTED | emergency app actions | Existing tests (4) |
| J2 | ER → inpatient transfer, ER discharge | P4 13 | IMPLEMENTED | admit_to_ipd, discharge | R |
| J3 | ER action menu (all 24 actions) | P4 13 | VERIFIED | Emergency → All actions on every ER row: all 24 spec actions. ER-owned ones run in place (doctor notes, allergy, investigation results, consent / emergency / generic forms, drug receive, transfer to IP, charge slip + bill preview, ER discharge summary, medical certificate); vitals, service order, drug request and discharge reuse the ER dialogs; sample collection/dispatch, blood request/receive, bed transfer, billing, update details and medical record open that module with the patient chosen (`?patient=&q=`). The ER board no longer fails for doctors (nurse list optional) | emergency.test_er_actions (5), erActions.test.js (24-action spec check); browser 2026-10-28 |
| J4 | Blood bank | UI 3.12 | IMPLEMENTED | Inventory, requests, transactions | Existing tests |
| J5 | Ambulance, mortuary, phlebotomy, OT / procedure room | UI 3.12, P1 | MISSING | — | — |
| J6 | HR, feedback, custom templates | UI 3.2 | MISSING | — | — |
| J7 | MIS dashboard and reports | UI 3.1 | VERIFIED | Reports page on server KPIs | T (dashboard API), B |

## K. AI, notifications and ML

| ID | Requirement | Source | Status | Implementation | Evidence |
|---|---|---|---|---|---|
| K1 | Recording with consent → STT → transcript | AI 1 | VERIFIED (software) | ai_scribe; consent required | T:test_ai_scribe_safety (mock provider). Real STT: BLOCKED (no provider key) |
| K2 | Structured extraction (symptoms, complaint, history, medicines, allergies, duration, summary), schema-validated | AI 2 | VERIFIED (software) | `_validate_extraction` coerces to schema | T |
| K3 | "AI Draft — Pending Review" until approval; no auto-finalize | AI 7, UI 5 | VERIFIED | review_label; read-only status; linked doctor approves | T, B (label shown) |
| K4 | Provider failure does not corrupt records | Brief 14 | VERIFIED | 503 response; no note is written | T |
| K5 | Hindi / Hinglish speech | AI 2 | BLOCKED | Depends on the chosen STT provider; not validated | — |
| K6 | Discharge-summary AI assist, patient-friendly explanation | UI 5 | MISSING | — | — |
| K7 | Waiting-list notifications with consent and delivery log | CALL 1, 7 | PARTIAL | In-app sent and logged; SMS/WhatsApp need consent and credentials | T:test_notifications. Real channels: BLOCKED |
| K8 | Voice-call fallback, acknowledgement, "no answer ≠ left" | CALL 3 | MISSING | VoiceProvider class only; no call workflow | — |
| K9 | ML / DL use cases | P2 12 | N/A | Not implemented on purpose: no labelled data, validation or monitoring available, and the PDF itself says "only after validation". Queue estimates are rule-based. | — |
| K10 | ABDM / ABHA | P1 3.5 | BLOCKED | Code present, routes not mounted; needs ABDM sandbox credentials and approval | — |
| K11 | FHIR / HL7 interoperability | P1 2 | BLOCKED | Code present, routes not mounted; needs a conformance and security review | — |

## Totals

Counted by script from the rows above; each row is counted once.

| Status | Count | Share |
|---|---|---|
| VERIFIED (2 of these are "software only": real provider not tested) | 42 | 36.2% |
| IMPLEMENTED | 24 | 20.7% |
| PARTIAL | 23 | 19.8% |
| PLACEHOLDER | 0 | 0% |
| MISSING | 23 | 19.8% |
| BROKEN | 0 known | 0% |
| BLOCKED | 3 | 2.6% |
| N/A | 1 | 0.9% |
| **Total** | **116** | |

The production-readiness report derives its completion percentages from these counts.
