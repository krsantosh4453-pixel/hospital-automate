# PHASE 4 — CURRENT STATE REPORT (UPDATED 2026-10-10)
## Intelligent Queue + Patient Notification Automation

**Status: NOT STARTED** — This report documents the state as of 2026-10-10 before Phase 4 work begins.

---

## 1. EXISTING MODELS (VERIFIED 2026-10-10)

### Appointment (backend/appointments/models.py)
- Fields: hospital, patient, doctor, appointment_date, appointment_time, status (default "Scheduled"), reason, village, contact
- Validation: Patient must belong to hospital, doctor must belong to hospital
- **Status: ✅ ACTIVE**

### QueueToken (backend/encounters/models.py)
- Fields: visit (FK), appointment (FK, nullable), hospital, patient, doctor, token_number, status (default "Waiting"), estimated_wait_minutes (default 0), created_at, token_date
- UniqueConstraint: (hospital, token_date, token_number)
- Ordering: token_date, token_number
- **Status: ✅ ACTIVE**

### Visit (backend/encounters/models.py)
- Fields: patient, doctor (nullable), hospital, visit_type (default "OPD"), chief_complaint, status (default "Waiting"), visit_date
- **Status: ✅ ACTIVE**

### Notification (backend/notifications/models.py)
- Fields: patient, title, message, notification_type, is_read, created_at
- No hospital scoping currently
- **Status: ⚠️ PARTIAL** — Model exists but no hospital FK, no provider abstraction

### Consent (backend/notifications/models.py)
- Fields: patient, purpose, granted, created_at
- **Status: ⚠️ PARTIAL** — Basic consent model only

### OTPVerification (backend/notifications/models.py)
- Fields: phone, otp, is_verified, attempts, expires_at, created_at
- **Status: ✅ ACTIVE** — Used for patient OTP flow

---

## 2. EXISTING SERIALIZERS (VERIFIED)

### QueueTokenSerializer (backend/encounters/serializers.py)
- Read-only display helpers: patient_name, patient_phone, doctor_name, department (doctor.specialization), visit_type, hospital_name
- `waiting_minutes` SerializerMethodField: calculates minutes since created_at when status="Waiting", else 0
- `token_number` and `token_date` not required (allocated server-side)
- `create()`: Generates next token number per hospital per day with retry loop + DB constraint
- Validators cleared (DB constraint + retry loop handles uniqueness)
- **Status: ✅ ACTIVE**

---

## 3. EXISTING VIEWS (VERIFIED)

### QueueTokenViewSet (backend/encounters/views.py)
- HospitalScopedViewSet (filters by hospital)
- Actions:
  - `issue` (POST /issue/): Appointment → Visit → QueueToken (idempotent)
  - `call` (POST /{id}/call/): status → "In Consultation"
  - `complete` (POST /{id}/complete/): status → "Completed"
  - `skip` (POST /{id}/skip/): status → "Skipped"
  - `call_next` (POST /call-next/?hospital=): Completes current "In Consultation", calls next "Waiting" by token order
- **Status: ✅ ACTIVE**

### Services (backend/encounters/services.py)
- `issue_queue_token_for_appointment(appointment, visit_type, chief_complaint)`:
  - Idempotent: returns existing token if appointment already has one
  - Reuses same-day Visit for patient/doctor/hospital, else creates new
  - Creates QueueToken with status="Waiting", estimated_wait_minutes=0
- **Status: ✅ ACTIVE**

---

## 4. EXISTING FRONTEND (VERIFIED)

### Queue.jsx (src/pages/Queue.jsx)
- Hospital-scoped queue display
- Fallback demo data when API unreachable
- Actions: Generate Token, Call Next, Call Specific, Complete, Skip
- Maps Django QueueToken → UI queue row
- Statistics: Waiting, In Consultation, Completed, Skipped counts
- Current token highlight
- **Status: ✅ ACTIVE**

### PatientQueue.jsx (src/pages/patient/PatientQueue.jsx)
- Patient-specific queue tokens (filters by patient.id, excludes Completed)
- Shows: token_number, status, estimated_wait_minutes, position_in_queue
- Polls every 30 seconds
- **Status: ✅ ACTIVE**

### Appointments.jsx (src/pages/Appointments.jsx)
- Appointment CRUD with Django API sync
- Token numbers are UI-only (backend QueueToken handles real tokens)
- Fallback to localStorage when offline
- **Status: ✅ ACTIVE**

### PatientLogin.jsx (src/pages/PatientLogin.jsx)
- Mobile OTP, Token/ID, Google OAuth login
- Saves patient to AuthContext + PatientContext
- **Status: ✅ ACTIVE**

---

## 5. CURRENT QUEUE ESTIMATION (VERIFIED)
- **Only**: `waiting_minutes` = time since token created_at (when status="Waiting")
- **Missing**: queue_position, estimated_start_time, confidence, historical average consultation duration, doctor schedule awareness
- **Status: ⚠️ PARTIAL** — Only elapsed time tracking, no prediction

---

## 6. CURRENT NOTIFICATION SYSTEM (VERIFIED)
- Basic in-app Notification model only
- No SMS/WhatsApp/Voice/Email providers implemented
- No event-driven notifications
- No consent tracking for communications (only basic Consent model)
- **Status: ⚠️ BACKEND MODEL ONLY** — Not production-ready

---

## 7. STATE TRANSITIONS (Current — VERIFIED)
```
Waiting → In Consultation → Completed
Waiting → In Consultation → Skipped
Waiting → Skipped
```
- No validation against invalid transitions (e.g., Completed → Waiting)
- No CALLED, ACKNOWLEDGED, READY, NO_SHOW, CANCELLED states
- **Status: ⚠️ PARTIAL** — Basic transitions only, no state machine enforcement

---

## 8. IDENTIFIED GAPS FOR PHASE 4 (UPDATED)

| Requirement | Current State | Gap | Priority |
|-------------|---------------|-----|----------|
| Safe state transitions | Basic status field | No state machine, invalid transitions possible | P1 |
| Queue position | Not exposed | Need position_in_queue field/calculation | P1 |
| Estimated wait time | Only elapsed time | Need prediction based on patients ahead × avg duration | P1 |
| Estimated start time | Missing | Need calculated field | P1 |
| Prediction service | None | Need dedicated service layer | P2 |
| ML extensibility | Not designed | Need provider pattern | P3 |
| Notification providers | Only in-app | Need SMS/WhatsApp/Voice/Email abstraction | P1 |
| Notification events | None | Need event system for queue lifecycle | P1 |
| Consent for notifications | Basic Consent model | Need purpose-specific consent | P2 |
| Audit trail | Audit app exists | Need queue-specific audit events | P2 |

---

## 9. NEXT STEPS (UNCHANGED — Phase 4 Not Started)

1. **Queue Engine**: Add state machine validation, new states (CALLED, ACKNOWLEDGED, READY, NO_SHOW, CANCELLED)
2. **Queue Estimation**: Add queue_position, estimated_wait_minutes (predicted), estimated_start_time, last_updated
3. **QueuePredictionService**: Extract prediction logic, support BaselineEstimator + future MLModelEstimator
4. **Notification Engine**: Provider interface + concrete providers (console/log for now, extensible)
5. **Notification Events**: Event system for APPOINTMENT_CONFIRMED, QUEUE_TOKEN_CREATED, QUEUE_WAIT_ESTIMATE_UPDATED, PATIENT_CALLED, PATIENT_ACK_REQUIRED, PATIENT_READY, APPOINTMENT_DELAYED, APPOINTMENT_CANCELLED
6. **Frontend**: Update Queue.jsx and PatientQueue.jsx to use new fields
7. **Migrations**: Create and run migrations for model changes

---

## AUDIT NOTES (2026-10-10)

- This report was originally created as a Phase 4 starting state document
- All existing models, serializers, views, and frontend components verified against actual source code
- No Phase 4 work has been completed yet — all gaps remain
- The queue system (QueueToken, Visit, QueueTokenViewSet) is functional for basic operations
- Notification system is NOT ready for production — only basic in-app model exists
- Phase 4 should prioritize: state machine, queue estimation, notification providers