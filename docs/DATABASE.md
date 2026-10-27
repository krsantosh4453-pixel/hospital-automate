# Database

## Engines

| Environment | Engine | Settings |
|---|---|---|
| Production | PostgreSQL 16 (`postgres:16-alpine` in compose), `DATABASE_URL`, `CONN_MAX_AGE=60` | `config/settings/production.py` |
| Development | SQLite `backend/db.sqlite3` (not tracked in git) | `config/settings/development.py` |
| Tests | SQLite in memory | `config/settings/testing.py` |

Verification on 2026-10-25:

- All 114 migrations applied to an empty PostgreSQL 16 database.
- The 17 migrations added in this work reversed and re-applied cleanly.
- The full test suite (217 tests) passed on PostgreSQL 16 as well as SQLite.

Timestamps are timezone-aware (`USE_TZ=True`, stored in UTC). Money uses `DecimalField` (2 decimal places) and is computed with Python `Decimal` (`ROUND_HALF_UP`).

## Tenancy model

Every row that a hospital owns can be traced to exactly one `hospital.Hospital`, either directly or through a foreign-key chain. The chain is resolved by `users.viewsets.resolve_hospital_lookup`, for example:

| Model | Owning path |
|---|---|
| Visit, Appointment, Admission, Invoice, LabTest, Medicine, Prescription … | `hospital_id` |
| VitalSign, Diagnosis, ClinicalNote, ServiceOrder | `visit__hospital_id` |
| PrescriptionItem | `prescription__hospital_id` |
| InvoiceItem, Payment | `invoice__hospital_id` |
| BedAllocation, DischargePlan / Summary / Note | `admission__hospital_id` |
| Room, Bed | `ward__hospital_id`, `room__ward__hospital_id` |
| MARAdministration | `mar__hospital_id` |
| AIConsultationDraft, ConversationTranscript | `consultation__hospital_id` |

`patients.Patient` is a shared identity. A patient appears to a hospital that registered them, or where they hold an active `PatientHospital` membership (which also carries the hospital's UHID). The patient record is never used to decide which hospital owns clinical data.

Models with no path to a hospital get no rows, because scoping fails closed. Platform reference data (prompt templates, extraction schemas, report templates) is explicitly global.

### Hospital columns added in this work (with backfill)

| Model | Backfill rule (migration `clinical/0005_backfill_tenant_hospital`) |
|---|---|
| clinical.MedicalRecord | the visit's hospital, else the patient's registering hospital |
| billing.InsuranceClaim | the invoice's hospital, else the patient's registering hospital |
| clinical.Allergy, notifications.Consent, audit.AIInteraction, patients.PatientDocument | the patient's registering hospital (`Patient.hospital`) |
| audit.AuditLog | left empty; historic rows had no hospital context and are visible only to platform admins |

Rows whose patient has no registering hospital stay NULL, and hospital staff can't see them. **Manual action:** after deploying, count such rows and assign their hospital deliberately:

```sql
SELECT count(*) FROM clinical_allergy WHERE hospital_id IS NULL;
```

Repeat this for each table listed above.

## Integrity constraints added

| Constraint | Table |
|---|---|
| `invoice_discount_non_negative`, `invoice_total_non_negative` | billing_invoice |
| `invoiceitem_price_non_negative`, `invoiceitem_tax_rate_range` (0–100) | billing_invoiceitem |
| `payment_amount_positive`, `payment_unique_idempotency_key` (per invoice, when set) | billing_payment |
| `doctor_unique_user_per_hospital` | doctors_doctor |
| Payment → invoice is `PROTECT` (invoices with payments cannot be deleted) | billing_payment |

## New tables and columns

| Migration | Change |
|---|---|
| `consent/0001_initial` | `ConsentRecord`, `RecordShare`, `RecordShareAccess` |
| `notifications/0006` | `NotificationDelivery` (one row per channel attempt) |
| `billing/0006` | Payment: `kind` (payment / refund), `receipt_number`, `reference`, `idempotency_key`, `received_by` |
| `doctors/0006` | `Doctor.user` (login link) |
| `doctors/0007` | Links doctors to logins only on an unambiguous match: one active user with that email, who is an active Doctor member of the same hospital |
| `ai_scribe/0002` | `ConsultationSession.recording_consent_at` / `_by` |
| `audit/0003` | `AuditLog.hospital`, `ip_address`; AIInteraction hospital; ordering |
| `clinical/0006` | `Diagnosis.recorded_by` |
| `hospital/0005`, `0006` | Hospital `code`, `hospital_type`; Department `code`, `head` |
| `nurses/0005` | MAR dose `Scheduled` and `Excluded` states; `is_prn`; `recorded_by` |
| `nurses/0006` | Data fix: doses marked Administered with no administration time (never given) are set back to Scheduled. Rows with a time are unchanged. |

All schema migrations reverse automatically. Data migrations reverse as no-ops, and no migration deletes rows.

## Concurrency

- **Stock:** `UPDATE … WHERE quantity >= n` (atomic, so stock can't be oversold); a ledger row is written in the same transaction.
- **Payments:** the invoice row is locked (`SELECT … FOR UPDATE`) before the balance check, so concurrent payments can't both pass.
- **Beds:** the bed row is locked on allocation.

## Known data-model gaps

See `KNOWN_LIMITATIONS.md`. Gaps include: no emergency contacts or payer entities on Patient; no structured complaint, history or examination; no ICD-10 terminology table; no proxy-access model; no advance-payment model.
