# PHASE 4 — CURRENT STATE REPORT
## Intelligent Queue + Patient Notification Automation

---

## 1. EXISTING MODELS

### Appointment (backend/appointments/models.py)
- Fields: hospital, patient, doctor, appointment_date, appointment_time, status (default "Scheduled"), reason, village, contact
- Validation: Patient must belong to hospital, doctor must belong to hospital

### QueueToken (backend/encounters/models.py)
- Fields: visit (FK), appointment (FK, nullable), hospital, patient, doctor, token_number, status (default "Waiting"), estimated_wait_minutes (default 0), created_at, token_date
- UniqueConstraint: (hospital, token_date, token_number)
- Ordering: token_date, token_number

### Visit (backend/encounters/models.py)
- Fields: patient, doctor (nullable), hospital, visit_type (default "OPD"), chief_complaint, status (default "Waiting"), visit_date

### Notification (backend/notifications/models.py)
- Fields: patient, title, message, notification_type, is_read, created_at
- No hospital scoping currently

### Consent (backend/notifications/models.py)
- Fields: patient, purpose, granted, created_at

### OTPVerification (backend/notifications/models.py)
- Fields: phone, otp, is_verified, attempts, expires_at, created_at

---

## 2. EXISTING SERIALIZERS

### QueueTokenSerializer (backend/encounters/serializers.py)
- Read-only display helpers: patient_name, patient_phone, doctor_name, department (doctor.specialization), visit_type, hospital_name
- `waiting_minutes` SerializerMethodField: calculates minutes since created_at when status="Waiting", else 0
- `token_number` and `token_date` not required (allocated server-side)
- `create()`: Generates next token number per hospital per day with retry loop + DB constraint
- Validators cleared (DB constraint + retry loop handles uniqueness)

---

## 3. EXISTING VIEWS

### QueueTokenViewSet (backend/encounters/views.py)
- HospitalScopedViewSet (filters by hospital)
- Actions:
  - `issue` (POST /issue/): Appointment → Visit → QueueToken (idempotent)
  - `call` (POST /{id}/call/): status → "In Consultation"
  - `complete` (POST /{id}/complete/): status → "Completed"
  - `skip` (POST /{id}/skip/): status → "Skipped"
  - `call_next` (POST /call-next/?hospital=): Completes current "In Consultation", calls next "Waiting" by token order

### Services (backend/encounters/services.py)
- `issue_queue_token_for_appointment(appointment, visit_type, chief_complaint)`:
  - Idempotent: returns existing token if appointment already has one
  - Reuses same-day Visit for patient/doctor/hospital, else creates new
  - Creates QueueToken with status="Waiting", estimated_wait_minutes=0

---

## 4. EXISTING FRONTEND

### Queue.jsx (src/pages/Queue.jsx)
- Hospital-scoped queue display
- Fallback demo data when API unreachable
- Actions: Generate Token, Call Next, Call Specific, Complete, Skip
- Maps Django QueueToken → UI queue row
- Statistics: Waiting, In Consultation, Completed, Skipped counts
- Current token highlight

### PatientQueue.jsx (src/pages/patient/PatientQueue.jsx)
- Patient-specific queue tokens (filters by patient.id, excludes Completed)
- Shows: token_number, status, estimated_wait_minutes, position_in_queue
- Polls every 30 seconds

### Appointments.jsx (src/pages/Appointments.jsx)
- Appointment CRUD with Django API sync
- Token numbers are UI-only (backend QueueToken handles real tokens)
- Fallback to localStorage when offline

### PatientLogin.jsx (src/pages/PatientLogin.jsx)
- Mobile OTP, Token/ID, Google OAuth login
- Saves patient to AuthContext + PatientContext

---

## 5. CURRENT QUEUE ESTIMATION
- **Only**: `waiting_minutes` = time since token created_at (when status="Waiting")
- **Missing**: queue_position, estimated_start_time, confidence, historical average consultation duration, doctor schedule awareness

---

## 6. CURRENT NOTIFICATION SYSTEM
- Basic in-app Notification model only
- No SMS/WhatsApp/Voice/Email providers
- No event-driven notifications
- No consent tracking for communications

---

## 7. STATE TRANSITIONS (Current)
```
Waiting → In Consultation → Completed
Waiting → In Consultation → Skipped
Waiting → Skipped
```
- No validation against invalid transitions (e.g., Completed → Waiting)
- No CALLED, ACKNOWLEDGED, READY, NO_SHOW, CANCELLED states

---

## 8. IDENTIFIED GAPS FOR PHASE 4

| Requirement | Current State | Gap |
|-------------|---------------|-----|
| Safe state transitions | Basic status field | No state machine, invalid transitions possible |
| Queue position | Not exposed | Need position_in_queue field/calculation |
| Estimated wait time | Only elapsed time | Need prediction based on patients ahead × avg duration |
| Estimated start time | Missing | Need calculated field |
| Prediction service | None | Need dedicated service layer |
| ML extensibility | Not designed | Need provider pattern |
| Notification providers | Only in-app | Need SMS/WhatsApp/Voice/Email abstraction |
| Notification events | None | Need event system for queue lifecycle |
| Consent for notifications | Basic Consent model | Need purpose-specific consent |
| Audit trail | Audit app exists | Need queue-specific audit events |

---

## 9. NEXT STEPS

1. **Queue Engine**: Add state machine validation, new states (CALLED, ACKNOWLEDGED, READY, NO_SHOW, CANCELLED)
2. **Queue Estimation**: Add queue_position, estimated_wait_minutes (predicted), estimated_start_time, last_updated
3. **QueuePredictionService**: Extract prediction logic, support BaselineEstimator + future MLModelEstimator
4. **Notification Engine**: Provider interface + concrete providers (console/log for now, extensible)
5. **Notification Events**: Event system for APPOINTMENT_CONFIRMED, QUEUE_TOKEN_CREATED, QUEUE_WAIT_ESTIMATE_UPDATED, PATIENT_CALLED, PATIENT_ACK_REQUIRED, PATIENT_READY, APPOINTMENT_DELAYED, APPOINTMENT_CANCELLED
6. **Frontend**: Update Queue.jsx and PatientQueue.jsx to use new fields
7. **Migrations**: Create and run migrations for model changes