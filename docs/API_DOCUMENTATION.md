# API Documentation

Base path: `/api/`. Interactive schema: `/api/schema/` (OpenAPI 3), `/api/docs/` (Swagger), `/api/redoc/`.

The route table at the end is generated from the live URL configuration:

```
cd backend && python scripts/generate_api_docs.py
```

## Conventions

### Authentication

- Staff sign in with `POST /api/auth/staff/login/` (username or email plus password). This is refused when `STAFF_LOGIN_REQUIRE_OTP` is on, which is the production default.
- With OTP: `POST /api/auth/staff/login/otp/start/` returns `challenge`. Then call `POST .../otp/verify/` with `{challenge, otp}` (or `.../otp/resend/` with `{challenge}`). The challenge is signed and lasts 10 minutes.
- Patients sign in with `/api/auth/patient/otp/*`, `/api/auth/patient/email-otp/*`, `/api/auth/patient/login/` (verified email plus password) or Google.
- Responses carry JWT `access` (15 minutes) and `refresh` (7 days, rotated, blacklisted on logout). Send `Authorization: Bearer <access>`.
- Five failed passwords lock the account for 15 minutes (HTTP 429).
- Password reset: `POST /api/auth/password/reset/ {username}`, then `POST /api/auth/password/reset/confirm/ {username, code, new_password}`. Reset revokes all refresh tokens.
- There is no bare `/api/auth/token/` obtain endpoint.

### Acting hospital

Every staff request acts in one hospital, taken from (in order):

1. `?hospital=<id>`
2. a `hospital` field in the body
3. the `X-Hospital-ID` header, which the frontend sends for the hospital selected in the switcher.

Requests for a hospital you are not an active member of get 403. Without any of these, lists cover all your hospitals.

Roles are those of your membership in the acting hospital. A role held elsewhere grants nothing.

### Errors

```json
{"error": true, "status_code": 400, "message": "field: reason", "details": {"field": ["reason"]}}
```

Status codes:

- **400** validation
- **401** not signed in
- **403** not allowed (role or hospital)
- **404** not found or not in your hospital; Hospital B's ids look like 404s to Hospital A
- **405** operation not offered (e.g. editing a payment)
- **429** rate-limited or locked
- **503** dependency not configured (AI provider, SMS)

### Pagination

List endpoints return `{count, next, previous, results}` with 50 items per page; use `?page=`.

### Money

Amounts are decimal strings with two places (`"607.99"`). The server computes every total, tax amount, status and balance; values sent by a client are ignored.

### Idempotency

`POST /api/billing/payments/` accepts an `Idempotency-Key` header or an `idempotency_key` field. Repeating a key returns the original payment with status 200 and does not charge again.

### Audit

Every create, update and delete through the scoped viewsets writes an `AuditLog` row with the user, hospital, action, object and, for updates, old → new values. Sign-ins, password resets, document downloads, consent changes, payments and refunds, and AI approvals are also audited.

## Workflow endpoints

| Workflow | Calls |
|---|---|
| Register → appointment → queue | `POST /api/patients/`, `POST /api/appointments/`, `POST /api/encounters/queue-tokens/issue/ {appointment}` (creates visit and token) |
| Consultation | `POST /api/clinical/vitals/`, `/diagnoses/` (records clinician), `/prescriptions/` (with `items`) |
| AI scribe | `POST /api/ai/consultation-sessions/`, then `{id}/start_recording/ {patient_consent: true}`, `{id}/stop_recording/` (multipart audio) and `{id}/transcribe/`. A draft is created; then `POST /api/ai/drafts/{id}/generate/` and `{id}/approve/`. Only a doctor linked to the login at that hospital can approve; drafts are labelled "AI Draft — Pending Review" until then. |
| Lab | `POST /api/laboratory/`, then `{id}/collect_sample/` (lab or nurse), `dispatch_sample/`, `receive_sample/`, `start_processing/`, `enter_result/ {result_text}`, `verify_result/` and `release_result/` (lab staff only) |
| Pharmacy | `POST /api/pharmacy-sales/ {medicine, quantity, prescription?}`. The price comes from the medicine record; expired batches are refused; the stock ledger is written. |
| IPD | `POST /api/ipd/admissions/`, `{id}/allocate_bed/ {bed_id}`, `initiate_discharge/`, `POST /api/ipd/discharge-summaries/`, `{id}/finalize/` (linked doctor), then `admissions/{id}/complete_discharge/` (requires a finalized summary) |
| MAR | `POST /api/nurses/mar/{id}/generate_schedule/`, `GET /api/nurses/mar/due_medications/?hospital=`; per dose `POST /api/nurses/mar-administrations/{id}/administer/`, `hold/`, `refuse/`, `mark_missed/` or `exclude/ {reason}`; PRN doses `POST /api/nurses/mar/{id}/prn/` |
| Billing | `POST /api/billing/invoices/ {patient, discount, items_data}`, `POST /api/billing/payments/`, `POST /api/billing/invoices/{id}/refund/ {amount, reason}`, `.../cancel/` |
| Consent | `GET/POST /api/consent/records/`, `{id}/revoke/`; `GET/POST /api/consent/shares/`, `{id}/revoke/`, `{id}/access-log/`, `shares/received/`, `{id}/records/` (recipient clinical staff) |
| Communication consent | `POST /api/notifications/consents/grant/ {purpose}`, `revoke/`, `GET check/?purpose=`; delivery log `GET /api/notifications/deliveries/` |
| Staff administration | `GET /api/users/`, `POST /api/users/{id}/approve/ {role}`, `PATCH /api/users/{id}/membership/` |
| Documents | `POST /api/documents/patient/{id}/upload/` (content-type checked); `GET /api/documents/{id}/download/` (audited) |

## Route table

The permission column shows the viewset's class-level permissions. Several actions override them in code (for example, lab result actions require `IsLabStaff`), and hospital scoping applies on top.

| Path | Methods | View | Permission classes |
|---|---|---|---|
| `/api/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/ai/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/ai/consultation-sessions/` | GET, POST | ai_scribe.ConsultationSessionViewSet | IsClinicalStaff |
| `/api/ai/consultation-sessions/{pk}/` | DELETE, GET, PATCH, PUT | ai_scribe.ConsultationSessionViewSet | IsClinicalStaff |
| `/api/ai/consultation-sessions/{pk}/start_recording/` | POST | ai_scribe.ConsultationSessionViewSet | IsClinicalStaff |
| `/api/ai/consultation-sessions/{pk}/stop_recording/` | POST | ai_scribe.ConsultationSessionViewSet | IsClinicalStaff |
| `/api/ai/consultation-sessions/{pk}/transcribe/` | POST | ai_scribe.ConsultationSessionViewSet | IsClinicalStaff |
| `/api/ai/consultation-sessions/{pk}/upload_audio/` | POST | ai_scribe.ConsultationSessionViewSet | IsClinicalStaff |
| `/api/ai/drafts/` | GET, POST | ai_scribe.AIConsultationDraftViewSet | IsDoctor |
| `/api/ai/drafts/{pk}/` | DELETE, GET, PATCH, PUT | ai_scribe.AIConsultationDraftViewSet | IsDoctor |
| `/api/ai/drafts/{pk}/approve/` | POST | ai_scribe.AIConsultationDraftViewSet | IsDoctor |
| `/api/ai/drafts/{pk}/generate/` | POST | ai_scribe.AIConsultationDraftViewSet | IsDoctor |
| `/api/ai/drafts/{pk}/regenerate/` | POST | ai_scribe.AIConsultationDraftViewSet | IsDoctor |
| `/api/ai/drafts/{pk}/reject/` | POST | ai_scribe.AIConsultationDraftViewSet | IsDoctor |
| `/api/ai/drafts/{pk}/review/` | POST | ai_scribe.AIConsultationDraftViewSet | IsDoctor |
| `/api/ai/prompts/` | GET, POST | ai_scribe.AIPromptTemplateViewSet | IsDoctor |
| `/api/ai/prompts/{pk}/` | DELETE, GET, PATCH, PUT | ai_scribe.AIPromptTemplateViewSet | IsDoctor |
| `/api/ai/reviews/` | GET, POST | ai_scribe.DoctorReviewViewSet | IsClinicalStaff |
| `/api/ai/reviews/{pk}/` | DELETE, GET, PATCH, PUT | ai_scribe.DoctorReviewViewSet | IsClinicalStaff |
| `/api/ai/schemas/` | GET, POST | ai_scribe.ClinicalExtractionSchemaViewSet | IsDoctor |
| `/api/ai/schemas/{pk}/` | DELETE, GET, PATCH, PUT | ai_scribe.ClinicalExtractionSchemaViewSet | IsDoctor |
| `/api/ai/transcripts/` | GET, POST | ai_scribe.ConversationTranscriptViewSet | IsClinicalStaff |
| `/api/ai/transcripts/{pk}/` | DELETE, GET, PATCH, PUT | ai_scribe.ConversationTranscriptViewSet | IsClinicalStaff |
| `/api/appointments/` | GET, POST | appointments.AppointmentViewSet | OperandHolder |
| `/api/appointments/{pk}/` | DELETE, GET, PATCH, PUT | appointments.AppointmentViewSet | OperandHolder |
| `/api/appointments/{pk}/cancel/` | POST | appointments.AppointmentViewSet | OperandHolder |
| `/api/appointments/{pk}/reschedule/` | POST | appointments.AppointmentViewSet | OperandHolder |
| `/api/audit/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/audit/ai-interactions/` | GET | audit.AIInteractionViewSet | OperandHolder |
| `/api/audit/ai-interactions/{pk}/` | GET | audit.AIInteractionViewSet | OperandHolder |
| `/api/audit/audit-logs/` | GET | audit.AuditLogViewSet | IsAdmin |
| `/api/audit/audit-logs/{pk}/` | GET | audit.AuditLogViewSet | IsAdmin |
| `/api/auth/google/` | POST | users.google_login | AllowAny |
| `/api/auth/password/reset/` | POST | users.staff_password_reset_request | AllowAny |
| `/api/auth/password/reset/confirm/` | POST | users.staff_password_reset_confirm | AllowAny |
| `/api/auth/patient/email-otp/request/` | POST | users.patient_email_otp_request | AllowAny |
| `/api/auth/patient/email-otp/verify/` | POST | users.patient_email_otp_verify | AllowAny |
| `/api/auth/patient/login/` | POST | users.patient_email_login | AllowAny |
| `/api/auth/patient/me/` | GET | users.patient_me | IsAuthenticated |
| `/api/auth/patient/otp/request/` | POST | users.patient_otp_request | AllowAny |
| `/api/auth/patient/otp/verify/` | POST | users.patient_otp_verify | AllowAny |
| `/api/auth/patient/token/` | POST | users.patient_token_login | AllowAny |
| `/api/auth/register/` | POST | users.register_account | AllowAny |
| `/api/auth/staff/login/` | POST | users.staff_login | AllowAny |
| `/api/auth/staff/login/otp/resend/` | POST | users.staff_otp_resend | AllowAny |
| `/api/auth/staff/login/otp/start/` | POST | users.staff_login_start_otp | AllowAny |
| `/api/auth/staff/login/otp/verify/` | POST | users.staff_otp_verify | AllowAny |
| `/api/auth/staff/logout/` | POST | users.staff_logout | IsAuthenticated |
| `/api/auth/staff/me/` | GET | users.staff_me | IsAuthenticated |
| `/api/auth/token/refresh/` | POST | rest_framework_simplejwt.TokenRefreshView | — |
| `/api/auth/token/verify/` | POST | rest_framework_simplejwt.TokenVerifyView | — |
| `/api/billing/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/billing/insurance-claims/` | GET, POST | billing.InsuranceClaimViewSet | OperandHolder |
| `/api/billing/insurance-claims/{pk}/` | DELETE, GET, PATCH, PUT | billing.InsuranceClaimViewSet | OperandHolder |
| `/api/billing/invoice-items/` | GET, POST | billing.InvoiceItemViewSet | OperandHolder |
| `/api/billing/invoice-items/{pk}/` | DELETE, GET, PATCH, PUT | billing.InvoiceItemViewSet | OperandHolder |
| `/api/billing/invoices/` | GET, POST | billing.InvoiceViewSet | OperandHolder |
| `/api/billing/invoices/{pk}/` | DELETE, GET, PATCH, PUT | billing.InvoiceViewSet | OperandHolder |
| `/api/billing/invoices/{pk}/cancel/` | POST | billing.InvoiceViewSet | OperandHolder |
| `/api/billing/invoices/{pk}/refund/` | POST | billing.InvoiceViewSet | OperandHolder |
| `/api/billing/payments/` | GET, POST | billing.PaymentViewSet | OperandHolder |
| `/api/billing/payments/{pk}/` | DELETE, GET, PATCH, PUT | billing.PaymentViewSet | OperandHolder |
| `/api/bloodbank/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/bloodbank/inventory/` | GET, POST | bloodbank.BloodInventoryViewSet | OperandHolder |
| `/api/bloodbank/inventory/{pk}/` | DELETE, GET, PATCH, PUT | bloodbank.BloodInventoryViewSet | OperandHolder |
| `/api/bloodbank/requests/` | GET, POST | bloodbank.BloodRequestViewSet | OperandHolder |
| `/api/bloodbank/requests/pending/` | GET | bloodbank.BloodRequestViewSet | OperandHolder |
| `/api/bloodbank/requests/{pk}/` | DELETE, GET, PATCH, PUT | bloodbank.BloodRequestViewSet | OperandHolder |
| `/api/bloodbank/requests/{pk}/approve/` | POST | bloodbank.BloodRequestViewSet | OperandHolder |
| `/api/bloodbank/requests/{pk}/issue/` | POST | bloodbank.BloodRequestViewSet | OperandHolder |
| `/api/bloodbank/requests/{pk}/reject/` | POST | bloodbank.BloodRequestViewSet | OperandHolder |
| `/api/bloodbank/transactions/` | GET, POST | bloodbank.BloodTransactionViewSet | OperandHolder |
| `/api/bloodbank/transactions/adjust/` | POST | bloodbank.BloodTransactionViewSet | OperandHolder |
| `/api/bloodbank/transactions/receive/` | POST | bloodbank.BloodTransactionViewSet | OperandHolder |
| `/api/bloodbank/transactions/stock_summary/` | GET | bloodbank.BloodTransactionViewSet | OperandHolder |
| `/api/bloodbank/transactions/{pk}/` | DELETE, GET, PATCH, PUT | bloodbank.BloodTransactionViewSet | OperandHolder |
| `/api/clinical/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/clinical/allergies/` | GET, POST | clinical.AllergyViewSet | OperandHolder |
| `/api/clinical/allergies/{pk}/` | DELETE, GET, PATCH, PUT | clinical.AllergyViewSet | OperandHolder |
| `/api/clinical/clinical-notes/` | GET, POST | clinical.ClinicalNoteViewSet | OperandHolder |
| `/api/clinical/clinical-notes/{pk}/` | DELETE, GET, PATCH, PUT | clinical.ClinicalNoteViewSet | OperandHolder |
| `/api/clinical/diagnoses/` | GET, POST | clinical.DiagnosisViewSet | OperandHolder |
| `/api/clinical/diagnoses/{pk}/` | DELETE, GET, PATCH, PUT | clinical.DiagnosisViewSet | OperandHolder |
| `/api/clinical/medical-records/` | GET, POST | clinical.MedicalRecordViewSet | OperandHolder |
| `/api/clinical/medical-records/{pk}/` | DELETE, GET, PATCH, PUT | clinical.MedicalRecordViewSet | OperandHolder |
| `/api/clinical/prescription-items/` | GET, POST | clinical.PrescriptionItemViewSet | OperandHolder |
| `/api/clinical/prescription-items/{pk}/` | DELETE, GET, PATCH, PUT | clinical.PrescriptionItemViewSet | OperandHolder |
| `/api/clinical/prescriptions/` | GET, POST | clinical.PrescriptionViewSet | OperandHolder |
| `/api/clinical/prescriptions/{pk}/` | DELETE, GET, PATCH, PUT | clinical.PrescriptionViewSet | OperandHolder |
| `/api/clinical/procedures/` | GET, POST | clinical.ProcedureViewSet | OperandHolder |
| `/api/clinical/procedures/{pk}/` | DELETE, GET, PATCH, PUT | clinical.ProcedureViewSet | OperandHolder |
| `/api/clinical/service-orders/` | GET, POST | clinical.ServiceOrderViewSet | OperandHolder |
| `/api/clinical/service-orders/{pk}/` | DELETE, GET, PATCH, PUT | clinical.ServiceOrderViewSet | OperandHolder |
| `/api/clinical/vitals/` | GET, POST | clinical.VitalSignViewSet | OperandHolder |
| `/api/clinical/vitals/{pk}/` | DELETE, GET, PATCH, PUT | clinical.VitalSignViewSet | OperandHolder |
| `/api/compounder/` | GET, POST | compounder.CompounderViewSet | OperandHolder |
| `/api/compounder/{pk}/` | DELETE, GET, PATCH, PUT | compounder.CompounderViewSet | OperandHolder |
| `/api/consent/forms/` | GET | consent.ConsentFormListView | IsAuthenticated |
| `/api/consent/forms/{id}/` | GET | consent.ConsentFormDetailView | IsAuthenticated |
| `/api/consent/records/` | GET, POST | consent.ConsentRecordListView | IsAuthenticated |
| `/api/consent/records/{id}/` | GET | consent.ConsentRecordDetailView | IsAuthenticated |
| `/api/consent/records/{id}/revoke/` | POST | consent.ConsentRecordRevokeView | IsAuthenticated |
| `/api/consent/shares/` | GET, POST | consent.RecordShareListView | IsAuthenticated |
| `/api/consent/shares/received/` | GET | consent.ReceivedShareListView | IsAuthenticated |
| `/api/consent/shares/{id}/access-log/` | GET | consent.RecordShareAccessLogView | IsAuthenticated |
| `/api/consent/shares/{id}/records/` | GET | consent.SharedRecordsView | IsAuthenticated |
| `/api/consent/shares/{id}/revoke/` | POST | consent.RecordShareRevokeView | IsAuthenticated |
| `/api/docs/` | GET | config.SwaggerUIView | AllowAny |
| `/api/doctors/` | GET, POST | doctors.DoctorViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/doctors/{pk}/` | DELETE, GET, PATCH, PUT | doctors.DoctorViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/documents/` | GET | documents.DocumentListView | IsAuthenticated |
| `/api/documents/categories/` | GET | documents.DocumentCategoryListView | IsAuthenticated |
| `/api/documents/categories/{id}/` | GET | documents.DocumentCategoryDetailView | IsAuthenticated |
| `/api/documents/patient/{patient_id}/` | GET | documents.PatientDocumentListView | IsAuthenticated |
| `/api/documents/patient/{patient_id}/upload/` | POST | documents.PatientDocumentUploadView | IsAuthenticated |
| `/api/documents/search/` | GET | documents.DocumentSearchView | IsAuthenticated |
| `/api/documents/{id}/` | GET, DELETE | documents.DocumentDetailView | IsAuthenticated |
| `/api/documents/{id}/download/` | GET | documents.DocumentDownloadView | IsAuthenticated |
| `/api/documents/{id}/preview/` | GET | documents.DocumentPreviewView | IsAuthenticated |
| `/api/emergency/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/emergency/emergency-visits/` | GET, POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/dashboard/` | GET | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/` | DELETE, GET, PATCH, PUT | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/add_medication/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/add_order/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/add_vitals/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/administer_medication/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/admit_to_ipd/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/complete_triage/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/discharge/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/refer/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/start_consultation/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/emergency-visits/{pk}/start_triage/` | POST | emergency.EmergencyVisitViewSet | OperandHolder |
| `/api/emergency/medications/` | GET, POST | emergency.EmergencyMedicationViewSet | OperandHolder |
| `/api/emergency/medications/{pk}/` | DELETE, GET, PATCH, PUT | emergency.EmergencyMedicationViewSet | OperandHolder |
| `/api/emergency/orders/` | GET, POST | emergency.EmergencyOrderViewSet | OperandHolder |
| `/api/emergency/orders/{pk}/` | DELETE, GET, PATCH, PUT | emergency.EmergencyOrderViewSet | OperandHolder |
| `/api/emergency/orders/{pk}/complete/` | POST | emergency.EmergencyOrderViewSet | OperandHolder |
| `/api/emergency/triage/` | GET, POST | emergency.EmergencyTriageViewSet | OperandHolder |
| `/api/emergency/triage/{pk}/` | DELETE, GET, PATCH, PUT | emergency.EmergencyTriageViewSet | OperandHolder |
| `/api/emergency/vitals/` | GET, POST | emergency.EmergencyVitalsViewSet | OperandHolder |
| `/api/emergency/vitals/{pk}/` | DELETE, GET, PATCH, PUT | emergency.EmergencyVitalsViewSet | OperandHolder |
| `/api/encounters/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/encounters/doctor-schedules/` | GET, POST | encounters.DoctorScheduleViewSet | OperandHolder |
| `/api/encounters/doctor-schedules/{pk}/` | DELETE, GET, PATCH, PUT | encounters.DoctorScheduleViewSet | OperandHolder |
| `/api/encounters/queue-tokens/` | GET, POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/call-next/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/estimates/` | GET | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/issue/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/` | DELETE, GET, PATCH, PUT | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/acknowledge/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/call/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/cancel/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/complete/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/no-show/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/ready/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/requeue/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/skip/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/queue-tokens/{pk}/start-consultation/` | POST | encounters.QueueTokenViewSet | OperandHolder |
| `/api/encounters/visits/` | GET, POST | encounters.VisitViewSet | OperandHolder |
| `/api/encounters/visits/{pk}/` | DELETE, GET, PATCH, PUT | encounters.VisitViewSet | OperandHolder |
| `/api/home/` | GET | home.home_dashboard | IsAuthenticated |
| `/api/home/stats/` | GET | home.home_stats_summary | IsAuthenticated |
| `/api/home/stats/detail/` | GET | home.home_dashboard | IsAuthenticated |
| `/api/hospital/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/hospital/beds/` | GET, POST | hospital.BedViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/hospital/beds/{pk}/` | DELETE, GET, PATCH, PUT | hospital.BedViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/hospital/departments/` | GET, POST | hospital.DepartmentViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/hospital/departments/{pk}/` | DELETE, GET, PATCH, PUT | hospital.DepartmentViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/hospital/directory/` | GET | hospital.HospitalDirectoryView | IsAuthenticated |
| `/api/hospital/hospitals/` | GET, POST | hospital.HospitalViewSet | IsAuthenticated, IsStaffUser |
| `/api/hospital/hospitals/{pk}/` | DELETE, GET, PATCH, PUT | hospital.HospitalViewSet | IsAuthenticated, IsStaffUser |
| `/api/hospital/rooms/` | GET, POST | hospital.RoomViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/hospital/rooms/{pk}/` | DELETE, GET, PATCH, PUT | hospital.RoomViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/hospital/wards/` | GET, POST | hospital.WardViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/hospital/wards/{pk}/` | DELETE, GET, PATCH, PUT | hospital.WardViewSet | IsAuthenticated, IsStaffUser, IsHospitalMember |
| `/api/ipd/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/ipd/admissions/` | GET, POST | ipd.AdmissionViewSet | OperandHolder |
| `/api/ipd/admissions/{pk}/` | DELETE, GET, PATCH, PUT | ipd.AdmissionViewSet | OperandHolder |
| `/api/ipd/admissions/{pk}/allocate_bed/` | POST | ipd.AdmissionViewSet | OperandHolder |
| `/api/ipd/admissions/{pk}/complete_discharge/` | POST | ipd.AdmissionViewSet | OperandHolder |
| `/api/ipd/admissions/{pk}/initiate_discharge/` | POST | ipd.AdmissionViewSet | OperandHolder |
| `/api/ipd/admissions/{pk}/release_bed/` | POST | ipd.AdmissionViewSet | OperandHolder |
| `/api/ipd/admissions/{pk}/transfer/` | POST | ipd.AdmissionViewSet | OperandHolder |
| `/api/ipd/bed-allocations/` | GET, POST | ipd.BedAllocationViewSet | OperandHolder |
| `/api/ipd/bed-allocations/available_beds/` | GET | ipd.BedAllocationViewSet | OperandHolder |
| `/api/ipd/bed-allocations/{pk}/` | DELETE, GET, PATCH, PUT | ipd.BedAllocationViewSet | OperandHolder |
| `/api/ipd/discharge-notes/` | GET, POST | ipd.DischargeNoteViewSet | OperandHolder |
| `/api/ipd/discharge-notes/{pk}/` | DELETE, GET, PATCH, PUT | ipd.DischargeNoteViewSet | OperandHolder |
| `/api/ipd/discharge-plans/` | GET, POST | ipd.DischargePlanViewSet | OperandHolder |
| `/api/ipd/discharge-plans/{pk}/` | DELETE, GET, PATCH, PUT | ipd.DischargePlanViewSet | OperandHolder |
| `/api/ipd/discharge-summaries/` | GET, POST | ipd.DischargeSummaryViewSet | IsDoctor |
| `/api/ipd/discharge-summaries/{pk}/` | DELETE, GET, PATCH, PUT | ipd.DischargeSummaryViewSet | IsDoctor |
| `/api/ipd/discharge-summaries/{pk}/finalize/` | POST | ipd.DischargeSummaryViewSet | IsDoctor |
| `/api/laboratory/` | GET, POST | laboratory.LabTestViewSet | OperandHolder |
| `/api/laboratory/lab-results/` | GET, POST | laboratory.LabResultViewSet | OperandHolder |
| `/api/laboratory/lab-results/{pk}/` | DELETE, GET, PATCH, PUT | laboratory.LabResultViewSet | OperandHolder |
| `/api/laboratory/result-verifications/` | GET, POST | laboratory.ResultVerificationViewSet | IsLabStaff |
| `/api/laboratory/result-verifications/{pk}/` | DELETE, GET, PATCH, PUT | laboratory.ResultVerificationViewSet | IsLabStaff |
| `/api/laboratory/sample-collections/` | GET, POST | laboratory.SampleCollectionViewSet | OperandHolder |
| `/api/laboratory/sample-collections/{pk}/` | DELETE, GET, PATCH, PUT | laboratory.SampleCollectionViewSet | OperandHolder |
| `/api/laboratory/sample-dispatches/` | GET, POST | laboratory.SampleDispatchViewSet | IsLabStaff |
| `/api/laboratory/sample-dispatches/{pk}/` | DELETE, GET, PATCH, PUT | laboratory.SampleDispatchViewSet | IsLabStaff |
| `/api/laboratory/{pk}/` | DELETE, GET, PATCH, PUT | laboratory.LabTestViewSet | OperandHolder |
| `/api/laboratory/{pk}/cancel/` | POST | laboratory.LabTestViewSet | OperandHolder |
| `/api/laboratory/{pk}/collect_sample/` | POST | laboratory.LabTestViewSet | OperandHolder |
| `/api/laboratory/{pk}/dispatch_sample/` | POST | laboratory.LabTestViewSet | OperandHolder |
| `/api/laboratory/{pk}/enter_result/` | POST | laboratory.LabTestViewSet | OperandHolder |
| `/api/laboratory/{pk}/receive_sample/` | POST | laboratory.LabTestViewSet | OperandHolder |
| `/api/laboratory/{pk}/release_result/` | POST | laboratory.LabTestViewSet | OperandHolder |
| `/api/laboratory/{pk}/start_processing/` | POST | laboratory.LabTestViewSet | OperandHolder |
| `/api/laboratory/{pk}/verify_result/` | POST | laboratory.LabTestViewSet | OperandHolder |
| `/api/notifications/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/notifications/consents/` | GET, POST | notifications.ConsentViewSet | OperandHolder |
| `/api/notifications/consents/check/` | GET | notifications.ConsentViewSet | OperandHolder |
| `/api/notifications/consents/grant/` | POST | notifications.ConsentViewSet | OperandHolder |
| `/api/notifications/consents/revoke/` | POST | notifications.ConsentViewSet | OperandHolder |
| `/api/notifications/consents/{pk}/` | DELETE, GET, PATCH, PUT | notifications.ConsentViewSet | OperandHolder |
| `/api/notifications/deliveries/` | GET | notifications.NotificationDeliveryViewSet | OperandHolder |
| `/api/notifications/deliveries/{pk}/` | GET | notifications.NotificationDeliveryViewSet | OperandHolder |
| `/api/notifications/notifications/` | GET, POST | notifications.NotificationViewSet | OperandHolder |
| `/api/notifications/notifications/{pk}/` | DELETE, GET, PATCH, PUT | notifications.NotificationViewSet | OperandHolder |
| `/api/notifications/notifications/{pk}/mark_read/` | POST | notifications.NotificationViewSet | OperandHolder |
| `/api/notifications/otp-verifications/` | GET | notifications.OTPVerificationViewSet | IsPlatformAdmin |
| `/api/notifications/otp-verifications/{pk}/` | GET | notifications.OTPVerificationViewSet | IsPlatformAdmin |
| `/api/nurses/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/nurses/assessments/` | GET, POST | nurses.NursingAssessmentViewSet | OperandHolder |
| `/api/nurses/assessments/{pk}/` | DELETE, GET, PATCH, PUT | nurses.NursingAssessmentViewSet | OperandHolder |
| `/api/nurses/care-tasks/` | GET, POST | nurses.CareTaskViewSet | OperandHolder |
| `/api/nurses/care-tasks/my_tasks/` | GET | nurses.CareTaskViewSet | OperandHolder |
| `/api/nurses/care-tasks/{pk}/` | DELETE, GET, PATCH, PUT | nurses.CareTaskViewSet | OperandHolder |
| `/api/nurses/care-tasks/{pk}/complete/` | POST | nurses.CareTaskViewSet | OperandHolder |
| `/api/nurses/care-tasks/{pk}/start/` | POST | nurses.CareTaskViewSet | OperandHolder |
| `/api/nurses/mar-administrations/` | GET, POST | nurses.MARAdministrationViewSet | OperandHolder |
| `/api/nurses/mar-administrations/{pk}/` | DELETE, GET, PATCH, PUT | nurses.MARAdministrationViewSet | OperandHolder |
| `/api/nurses/mar-administrations/{pk}/administer/` | POST | nurses.MARAdministrationViewSet | OperandHolder |
| `/api/nurses/mar-administrations/{pk}/exclude/` | POST | nurses.MARAdministrationViewSet | OperandHolder |
| `/api/nurses/mar-administrations/{pk}/hold/` | POST | nurses.MARAdministrationViewSet | OperandHolder |
| `/api/nurses/mar-administrations/{pk}/mark_missed/` | POST | nurses.MARAdministrationViewSet | OperandHolder |
| `/api/nurses/mar-administrations/{pk}/refuse/` | POST | nurses.MARAdministrationViewSet | OperandHolder |
| `/api/nurses/mar/` | GET, POST | nurses.MARViewSet | OperandHolder |
| `/api/nurses/mar/due_medications/` | GET | nurses.MARViewSet | OperandHolder |
| `/api/nurses/mar/{pk}/` | DELETE, GET, PATCH, PUT | nurses.MARViewSet | OperandHolder |
| `/api/nurses/mar/{pk}/generate_schedule/` | POST | nurses.MARViewSet | OperandHolder |
| `/api/nurses/mar/{pk}/prn/` | POST | nurses.MARViewSet | OperandHolder |
| `/api/nurses/notes/` | GET, POST | nurses.NursingNoteViewSet | OperandHolder |
| `/api/nurses/notes/{pk}/` | DELETE, GET, PATCH, PUT | nurses.NursingNoteViewSet | OperandHolder |
| `/api/nurses/nurses/` | GET, POST | nurses.NurseViewSet | OperandHolder |
| `/api/nurses/nurses/{pk}/` | DELETE, GET, PATCH, PUT | nurses.NurseViewSet | OperandHolder |
| `/api/nurses/patient-assignments/` | GET, POST | nurses.PatientAssignmentViewSet | OperandHolder |
| `/api/nurses/patient-assignments/assign_patients/` | POST | nurses.PatientAssignmentViewSet | OperandHolder |
| `/api/nurses/patient-assignments/{pk}/` | DELETE, GET, PATCH, PUT | nurses.PatientAssignmentViewSet | OperandHolder |
| `/api/patient-hospitals/` | GET, POST | patients.PatientHospitalViewSet | OperandHolder |
| `/api/patient-hospitals/{pk}/` | DELETE, GET, PATCH, PUT | patients.PatientHospitalViewSet | OperandHolder |
| `/api/patients/` | GET, POST | patients.PatientViewSet | OperandHolder |
| `/api/patients/documents/{doc_id}/` | DELETE | patients.PatientViewSet | OperandHolder |
| `/api/patients/{pk}/` | DELETE, GET, PATCH, PUT | patients.PatientViewSet | OperandHolder |
| `/api/patients/{pk}/documents/` | GET, POST | patients.PatientViewSet | OperandHolder |
| `/api/pharmacy-sales/` | GET, POST | pharmacy.SaleViewSet | OperandHolder |
| `/api/pharmacy-sales/{pk}/` | DELETE, GET, PATCH, PUT | pharmacy.SaleViewSet | OperandHolder |
| `/api/pharmacy/` | GET, POST | pharmacy.MedicineViewSet | OperandHolder |
| `/api/pharmacy/{pk}/` | DELETE, GET, PATCH, PUT | pharmacy.MedicineViewSet | OperandHolder |
| `/api/procurement/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/procurement/grn-items/` | GET, POST | procurement.GoodsReceiptItemViewSet | ReadOnlyScopePermission |
| `/api/procurement/grn-items/{pk}/` | DELETE, GET, PATCH, PUT | procurement.GoodsReceiptItemViewSet | ReadOnlyScopePermission |
| `/api/procurement/grns/` | GET, POST | procurement.GoodsReceiptViewSet | ReadOnlyScopePermission |
| `/api/procurement/grns/{pk}/` | DELETE, GET, PATCH, PUT | procurement.GoodsReceiptViewSet | ReadOnlyScopePermission |
| `/api/procurement/purchase-items/` | GET, POST | procurement.PurchaseItemViewSet | RequiresHospitalScope |
| `/api/procurement/purchase-items/{pk}/` | DELETE, GET, PATCH, PUT | procurement.PurchaseItemViewSet | RequiresHospitalScope |
| `/api/procurement/purchases/` | GET, POST | procurement.PurchaseOrderViewSet | RequiresHospitalScope |
| `/api/procurement/purchases/{pk}/` | DELETE, GET, PATCH, PUT | procurement.PurchaseOrderViewSet | RequiresHospitalScope |
| `/api/procurement/purchases/{pk}/receive/` | POST | procurement.PurchaseOrderViewSet | RequiresHospitalScope |
| `/api/procurement/stock-transactions/` | GET, POST | procurement.StockTransactionViewSet | ReadOnlyScopePermission |
| `/api/procurement/stock-transactions/adjust/` | POST | procurement.StockTransactionViewSet | ReadOnlyScopePermission |
| `/api/procurement/stock-transactions/{pk}/` | DELETE, GET, PATCH, PUT | procurement.StockTransactionViewSet | ReadOnlyScopePermission |
| `/api/procurement/suppliers/` | GET, POST | procurement.SupplierViewSet | RequiresHospitalScope |
| `/api/procurement/suppliers/{pk}/` | DELETE, GET, PATCH, PUT | procurement.SupplierViewSet | RequiresHospitalScope |
| `/api/redoc/` | GET | config.RedocView | AllowAny |
| `/api/reports/` | GET | rest_framework.APIRootView | IsAuthenticated |
| `/api/reports/analytics/ai-scribe/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/appointments/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/billing/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/bloodbank/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/clinical/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/dashboard/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/doctors/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/emergency/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/financial/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/forecast/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/forecast/appointments/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/forecast/beds/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/forecast/emergency/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/forecast/laboratory/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/forecast/medicine/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/forecast/patients/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/forecast/queue/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/forecast/revenue/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/inventory/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/ipd/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/laboratory/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/operational/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/patient-summary/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/patients/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/pharmacy/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/analytics/queue/` | GET | reports.AnalyticsViewSet | IsAuthenticated |
| `/api/reports/saved/` | GET, POST | reports.SavedReportViewSet | IsAuthenticated |
| `/api/reports/saved/{pk}/` | DELETE, GET, PATCH, PUT | reports.SavedReportViewSet | IsAuthenticated |
| `/api/reports/scheduled/` | GET, POST | reports.ScheduledReportViewSet | IsAuthenticated |
| `/api/reports/scheduled/{pk}/` | DELETE, GET, PATCH, PUT | reports.ScheduledReportViewSet | IsAuthenticated |
| `/api/reports/snapshots/` | GET | reports.KPISnapshotViewSet | IsAuthenticated |
| `/api/reports/snapshots/{pk}/` | GET | reports.KPISnapshotViewSet | IsAuthenticated |
| `/api/reports/templates/` | GET, POST | reports.ReportTemplateViewSet | IsAuthenticated |
| `/api/reports/templates/{pk}/` | DELETE, GET, PATCH, PUT | reports.ReportTemplateViewSet | IsAuthenticated |
| `/api/schema/` | GET | config.SchemaAPIView | AllowAny |
| `/api/users/` | GET | users.StaffListView | IsAuthenticated |
| `/api/users/{user_id}/approve/` | POST | users.StaffApproveView | IsAuthenticated |
| `/api/users/{user_id}/membership/` | PATCH | users.StaffMembershipView | IsAuthenticated |
| `/health/` | GET | config.HealthCheckView | — |
| `/health/live/` | GET | config.HealthCheckView | — |
| `/health/ready/` | GET | config.HealthCheckView | — |

320 routes.
