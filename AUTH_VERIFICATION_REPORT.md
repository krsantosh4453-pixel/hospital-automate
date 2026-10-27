> **Superseded (2026-10-25).** Historical report; it does not describe the current code. Current status: `docs/FINAL_PRODUCTION_READINESS_REPORT.md`, `docs/KNOWN_LIMITATIONS.md` and `docs/SECURITY_AUDIT.md`.

# Authentication & Authorization Architecture - Verification Report (UPDATED 2026-10-10)

## Overview
This document reports the authentication and authorization architecture for the Hospital Management System based on source code inspection. **Status labels updated to reflect actual verification evidence.**

**Status Legend:**
- ✅ **COMPLETE & VERIFIED** — Implemented with automated test evidence
- ⚠️ **IMPLEMENTED, NOT FULLY VERIFIED** — Implementation exists in code, but automated test coverage insufficient or not run
- ❌ **NOT IMPLEMENTED** — Missing entirely
- ⚠️ **PARTIALLY COMPLETE** — Some functionality exists, important work remains

---

**AUDIT NOTE (2026-10-10):** The original report marked 19/20 items as "✅ VERIFIED" but automated tests could not be run due to environment issues. Statuses below reflect source code inspection only. Items without test evidence are marked "IMPLEMENTED, NOT FULLY VERIFIED."

## 1. JWT Authentication ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Backend (Django SimpleJWT)
- **Access Token Lifetime**: 15 minutes
- **Refresh Token Lifetime**: 7 days
- **Rotation**: Enabled (`ROTATE_REFRESH_TOKENS: True`)
- **Blacklist After Rotation**: Enabled (`BLACKLIST_AFTER_ROTATION: True`)
- **Algorithm**: HS256
- **Signing Key**: From environment variable

### Frontend Token Handling
- Tokens stored in localStorage (`access_token`, `refresh_token`)
- Automatic token refresh on 401 responses
- Concurrent refresh protection via `refreshPromise`
- Session cleanup on refresh failure

### Token Claims (Staff)
```json
{
  "staff_id": 123,
  "staff_role": "Doctor",
  "roles": ["Doctor", "Admin"],
  "hospitals": [1, 2],
  "user_id": 123
}
```

### Token Claims (Patient)
```json
{
  "role": "Patient",
  "patient_id": 456,
  "user_id": 123
}
```

---

## 2. Access Token ⚠️ IMPLEMENTED, NOT FULLY VERIFIED
- Short-lived (15 min) for security
- Includes role and hospital claims for authorization
- Sent as `Authorization: Bearer <token>` header

---

## 3. Refresh Token ⚠️ IMPLEMENTED, NOT FULLY VERIFIED
- Long-lived (7 days) for session persistence
- Rotated on each use
- Blacklisted after rotation to prevent replay attacks
- Stored securely in localStorage

---

## 4. Token Expiration ⚠️ IMPLEMENTED, NOT FULLY VERIFIED
- Access token expires in 15 minutes
- Refresh token expires in 7 days
- Frontend automatically refreshes on 401
- If refresh fails → session cleared, user redirected to login

---

## 5. Logout ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Backend
- `POST /api/auth/staff/logout/` - Blacklists refresh token
- Uses `token.blacklist()` from simplejwt

### Frontend
- Calls backend logout endpoint
- Clears localStorage tokens and user data
- Dispatches `auth:logout` event for global cleanup
- Redirects to login page

---

## 6. OTP Authentication ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Staff OTP (Two-Factor)
1. **Step 1**: `POST /api/auth/staff/login/otp/start/`
   - Validates username/password first
   - Checks for registered phone number
   - Sends OTP via Twilio Verify
   - Returns `user_id` and masked phone

2. **Step 2**: `POST /api/auth/staff/login/otp/verify/`
   - Verifies OTP with Twilio
   - Issues JWT tokens on success

3. **Resend**: `POST /api/auth/staff/login/otp/resend/`
   - 60-second cooldown enforced
   - Rate limited (3/minute)

### Patient OTP
- `POST /api/auth/patient/otp/request/` - Request OTP
- `POST /api/auth/patient/otp/verify/` - Verify OTP
- Phone enumeration prevention (same response for registered/unregistered)
- Rate limited (3/minute per phone)
- Console/email fallback for development

### Email OTP (Patient)
- `POST /api/auth/patient/email-otp/request/`
- `POST /api/auth/patient/email-otp/verify/`
- 6-digit code, 5-minute expiry
- Rate limited (3/minute per email)

---

## 7. Google Authentication ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Flow
1. Frontend uses Google Identity Services (GIS)
2. Sends ID token to `POST /api/auth/google/`
3. Backend verifies with Google OAuth2 endpoint
4. Finds/creates user account
5. Links to existing staff or patient profile
6. Returns JWT tokens

### Security
- Verifies `aud` claim matches configured `GOOGLE_CLIENT_ID`
- Verifies issuer (`accounts.google.com`)
- Requires `email_verified: true`
- Sets unusable password for Google-only accounts

---

## 8. Password Authentication ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Staff Login
- `POST /api/auth/staff/login/`
- Uses Django's `authenticate()` (supports username or email)
- Returns JWT tokens + user data with roles/hospitals

### Patient Email Login
- `POST /api/auth/patient/login/`
- Uses `authenticate_patient_email()`
- Same error message for missing account/wrong password (enumeration prevention)
- Requires email verification

### Patient Token/ID Login
- `POST /api/auth/patient/token/`
- Accepts patient ID, UHID, username, or email
- Password verified against Django hasher

---

## 9. Password Reset ⚠️ NOT IMPLEMENTED

**Status**: Throttle rate configured (`password_reset: 2/hour`) but no endpoints exist.

**Required Endpoints**:
- `POST /api/auth/password/reset/` - Request reset email
- `POST /api/auth/password/reset/confirm/` - Confirm with token

---

## 10. Account Lockout / Rate Limiting ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### DRF Throttling (Configured)
| Scope | Rate |
|-------|------|
| anon | 100/hour |
| user | 1000/hour |
| login | 5/minute |
| otp | 3/minute |
| password_reset | 2/hour |

### Custom Middleware (`RateLimitMiddleware`)
Added to `MIDDLEWARE` in `base.py`

| Endpoint | Limit | Window | Scope |
|----------|-------|--------|-------|
| /api/auth/staff/login/ | 5 | 60s | IP |
| /api/auth/token/ | 10 | 60s | IP |
| /api/auth/token/refresh/ | 20 | 60s | User |
| /api/auth/google/ | 5 | 60s | IP |
| /api/auth/staff/logout/ | 30 | 60s | User |
| /api/notifications/otp/ | 3 | 60s | Phone |
| /api/notifications/otp/verify/ | 5 | 60s | Phone |
| /api/auth/password/reset/ | 2 | 3600s | Email |

### OTP-Level Rate Limiting
- Per-phone/email: 3 requests per 10 minutes
- Resend cooldown: 60 seconds
- Attempt limit: 5 per OTP

---

## 11. Create Account Flow ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Endpoint: `POST /api/auth/register/`

### Role Handling
| Role | Behavior |
|------|----------|
| Patient | Immediate activation, email verification required |
| Doctor/Nurse/Compounder/Receptionist | Staff profile created with `is_active_staff=False`, pending admin approval |
| Admin | Requires `ADMIN_INVITE_CODE` environment variable, active immediately |

### Validation
- Password: minimum 8 characters
- Phone: 10 digits required
- Email: required for Patient, validated format
- Duplicate email/phone prevention

---

## 12. Role Selection ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Backend Roles (StaffRole enum)
1. Admin
2. Doctor
3. Nurse
4. Compounder
5. Receptionist
6. Pharmacist
7. Lab Staff
8. Blood Bank Staff
9. Billing Staff
10. Inventory Staff
11. Hospital Manager

### Frontend Roles (DEFAULT_ROLES)
All 11 backend roles + Patient role now synchronized.

### Role Mapping
- Backend `Reception` → Frontend `Receptionist`
- Backend `Pharmacist` → Frontend `Compounder` (legacy)
- New roles: `Lab Staff`, `Blood Bank Staff`, `Billing Staff`, `Inventory Staff`, `Hospital Manager`

---

## 13. Backend RBAC ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Permission Classes
All views use role-based permission classes:

| View | Permission Classes |
|------|-------------------|
| Patients | IsReceptionist \| IsDoctor \| IsNurse \| IsAdmin \| IsPatientReadOnly |
| Appointments | IsAdmin \| IsHospitalManager \| IsReceptionist \| IsDoctor \| IsPatientReadOnly |
| Doctors | IsAdmin \| IsHospitalManager \| IsDoctor |
| Nurses | IsAdmin \| IsHospitalManager \| IsNurse |
| Compounder | IsAdmin \| IsHospitalManager \| IsCompounder |
| Pharmacy | IsAdmin \| IsHospitalManager \| IsPharmacist |
| Laboratory | IsLabStaff \| IsDoctor \| IsNurse \| IsPatientReadOnly |
| Billing | IsAdmin \| IsHospitalManager \| IsBillingStaff \| IsReceptionist \| IsPatientReadOnly |
| IPD | IsDoctor \| IsNurse |
| Encounters/Queue | IsAdmin \| IsHospitalManager \| IsDoctor \| IsNurse \| IsReceptionist \| IsPatientReadOnly |
| Clinical | IsAdmin \| IsHospitalManager \| IsDoctor \| IsNurse \| IsPharmacist |
| Nurses (Assessments/MAR) | IsNurse \| IsDoctor \| IsAdmin |
| Audit | IsAdmin \| (IsDoctor for some) |
| Notifications | IsAdmin \| IsHospitalManager \| IsReceptionist \| IsDoctor \| IsNurse |
| AI Scribe | IsDoctor |

### Base Classes
- `IsStaffUser` - Authenticated active staff
- `IsHospitalMember` - Hospital-scoped access
- `RoleBasedPermission` - Role + hospital membership
- `IsAdmin`, `IsDoctor`, `IsNurse`, `IsReceptionist`, `IsPharmacist`, `IsLabStaff`, `IsBillingStaff`, `IsInventoryStaff`, `IsBloodBankStaff`, `IsHospitalManager`, `IsCompounder`
- `IsClinicalStaff`, `IsAdminOrManager`
- `IsOwnerOrHospitalAdmin` - Object-level
- `IsPatientReadOnly` - Patient read access
- `IsLinkedPatient` - Patient-only access
- `IsHospitalScoped` - Object-level hospital isolation

---

## 14. Hospital-Level Data Isolation ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Implementation
- All API calls include `?hospital=<id>` query parameter
- `IsHospitalMember` permission checks hospital membership
- `IsHospitalScoped` object-level permission
- StaffHospitalMembership model links staff to hospitals with roles
- Querysets filtered by hospital in views

### Frontend
- Hospital selected via Navbar dropdown
- Selected hospital passed to all API calls
- Context providers manage hospital state

---

## 15. Unauthorized API Access ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Handling
- 401 → Automatic token refresh attempt
- 403 → Forbidden (insufficient role/hospital access)
- 429 → Rate limited (retry-after header)
- Frontend redirects to appropriate login page

### Frontend ProtectedRoute
- Checks authentication state
- Verifies role permissions for module access
- Redirects unauthorized users

---

## 16. Token Refresh Failures ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

### Frontend Flow
1. Request returns 401
2. `shouldAttemptRefresh()` checks if endpoint eligible
3. `refreshAccessToken()` calls `/api/auth/token/refresh/`
4. On success: retry original request
5. On failure: `failAuthSession()` → clear tokens, dispatch `auth:logout`, redirect to login

---

## 17. Expired Token Behavior ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

- Access token expired (15 min) → Auto-refresh via refresh token
- Refresh token expired (7 days) → Full logout, redirect to login
- No tokens stored → Redirect to login
- `loadUserFromToken()` on app init validates session

---

## 18. Invalid OTP Behavior ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

| Scenario | Response |
|----------|----------|
| Invalid format (not 6 digits) | "Invalid OTP." |
| Expired OTP | "OTP has expired." / "Invalid OTP." |
| Wrong OTP | "Invalid OTP." |
| Too many attempts | "Too many OTP requests. Please try again later." (429) |
| Rate limited | 429 with retry-after |

**Note**: Same error message for all failures prevents enumeration.

---

## 19. Invalid Credentials Behavior ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

| Scenario | Response |
|----------|----------|
| Wrong username | "Invalid credentials." / "Invalid email or password." |
| Wrong password | "Invalid credentials." / "Invalid email or password." |
| Inactive account | "Account is disabled." |
| Not staff | "Not authorized as staff." (403) |
| No patient profile | "Invalid email or password." / "Invalid patient credentials." |

**Note**: Same message for missing account and wrong password prevents enumeration.

---

## 20. Authentication Error Messages ⚠️ IMPLEMENTED, NOT FULLY VERIFIED

All endpoints return consistent error format:
```json
{
  "error": "Human-readable error message"
}
```

### HTTP Status Codes
- 400 - Bad Request (validation errors)
- 401 - Unauthorized (invalid credentials, expired tokens)
- 403 - Forbidden (insufficient permissions, inactive staff)
- 429 - Too Many Requests (rate limiting)
- 503 - Service Unavailable (OTP provider not configured)

---

## Permission Matrix

### Staff Roles vs Modules

| Module | Admin | Doctor | Nurse | Compounder | Receptionist | Pharmacist | Lab Staff | Blood Bank | Billing | Inventory | Hospital Mgr |
|--------|-------|--------|-------|------------|--------------|------------|-----------|------------|---------|-----------|--------------|
| Dashboard | CRUD | R | R | R | R | R | R | R | R | R | R |
| Patients | CRUD | RU | RU | R | CRUD | - | - | - | - | - | CRUD |
| Appointments | CRUD | RU | R | - | CRUD | - | - | - | - | - | CRUD |
| Queue | CRUD | R | RU | R | RU | - | - | - | - | - | R |
| Doctors | CRUD | R | R | - | R | - | - | - | - | - | CRUD |
| Nurses | CRUD | - | RU | - | - | - | - | - | - | - | CRUD |
| Compounders | CRUD | - | - | RU | - | - | - | - | - | - | - |
| Pharmacy | CRUD | - | - | CRUD | - | CRUD | - | - | - | - | CRUD |
| Laboratory | CRUD | R | R | - | - | - | CRUD | - | - | - | CRUD |
| Billing | CRUD | - | - | - | CR | - | - | - | CRUD | - | CRUD |
| Inventory | CRUD | - | - | RU | - | - | - | - | - | CRUD | CRUD |
| Prescriptions | CRUD | CRUD | R | RU | - | - | - | - | - | - | - |
| Reports | CRUD | R | R | - | R | R | R | R | R | R | CRUD |
| Emergency | CRUD | - | - | - | - | - | - | - | - | - | CRUD |
| Blood Bank | CRUD | - | - | - | - | - | - | CRUD | - | - | CRUD |
| IPD | CRUD | - | RU | - | CR | - | - | - | - | - | CRUD |
| AI Scribe | CRUD | - | - | - | - | - | - | - | - | - | CRUD |
| Users | CRUD | - | - | - | - | - | - | - | - | - | R |
| Roles | CRUD | - | - | - | - | - | - | - | - | - | - |
| Hospitals | CRUD | - | - | - | - | - | - | - | - | - | R |
| Departments | CRUD | - | - | - | - | - | - | - | - | - | CRUD |
| Permissions | CRUD | - | - | - | - | - | - | - | - | - | - |

**Legend**: C=Create, R=Read/View, U=Update/Edit, D=Delete

### Patient Role
| Module | Permissions |
|--------|-------------|
| Dashboard | View |
| Appointments | View, Create |
| Queue | View |
| Prescriptions | View |
| Laboratory | View |
| Billing | View |

---

## Development Mode Configuration

### Environment Variable
```bash
VITE_AUTH_REQUIRED=false  # Allows Home page access without login
VITE_GOOGLE_CLIENT_ID=your-google-client-id
```

### Behavior When `VITE_AUTH_REQUIRED=false`
- Root path `/` accessible without authentication
- Home page shows guest view with service exploration
- All other staff routes still require authentication
- Login/Create Account components remain available at `/staff-login`, `/patient-login`, `/register`

---

## Critical Issues Fixed

1. **Development Routing**: Added `VITE_AUTH_REQUIRED` flag to allow Home page access without login during development
2. **Rate Limit Middleware**: Added `RateLimitMiddleware` to Django MIDDLEWARE
3. **Frontend Role Sync**: Added missing backend roles (Pharmacist, Lab Staff, Blood Bank Staff, Billing Staff, Inventory Staff, Hospital Manager) to frontend DEFAULT_ROLES
4. **Google Client ID**: Moved from hardcoded to environment variable `VITE_GOOGLE_CLIENT_ID`
5. **Login Roles**: Updated LOGIN_ROLES to include all staff roles

---

## Remaining Work

1. **Password Reset**: Implement reset request and confirm endpoints
2. **Frontend Build**: Pre-existing pharmacy.jsx parse errors (duplicate declarations) - not related to auth
3. **Testing**: End-to-end authentication flow testing with backend running

---

## Verification Evidence

**Source Code Inspection Only — Automated Tests Not Executed (Environment Issues)**

| # | Component | Status | Evidence |
|---|-----------|--------|----------|
| 1 | JWT Authentication | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | SimpleJWT config in settings, token claims in views |
| 2 | Access Token | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | 15-min lifetime, claims in token payload |
| 3 | Refresh Token | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | 7-day lifetime, rotation, blacklist configured |
| 4 | Token Expiration | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Frontend auto-refresh logic in api.js |
| 5 | Logout | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Backend endpoint + frontend token clearing |
| 6 | OTP Authentication | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Staff/patient OTP endpoints, Twilio integration |
| 7 | Google Authentication | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Google OAuth endpoint, ID token verification |
| 8 | Password Authentication | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Staff/patient login endpoints, enumeration prevention |
| 9 | Password Reset | ❌ NOT IMPLEMENTED | Throttle configured, **no endpoints exist** |
| 10 | Account Lockout/Rate Limiting | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | DRF throttling + custom middleware configured |
| 11 | Create Account Flow | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Registration endpoint with role handling |
| 12 | Role Selection | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | 11 backend roles, frontend sync |
| 13 | Backend RBAC | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Permission classes on all ViewSets |
| 14 | Hospital-Level Data Isolation | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | HospitalScopedViewSet, IsHospitalMember |
| 15 | Unauthorized API Access | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | 401/403/429 handling, ProtectedRoute |
| 16 | Token Refresh Failures | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Frontend refresh logic with failAuthSession |
| 17 | Expired Token Behavior | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Auto-refresh, logout on refresh expiry |
| 18 | Invalid OTP Behavior | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Consistent error messages, enumeration prevention |
| 19 | Invalid Credentials Behavior | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Consistent error messages, enumeration prevention |
| 20 | Authentication Error Messages | ⚠️ IMPLEMENTED, NOT FULLY VERIFIED | Standardized JSON error format |

**Summary:** 18/20 components implemented in source code. 0/20 have automated test verification. 1 critical gap (Password Reset). Frontend role hiding is UI-only — NOT a security boundary.

---

## Files Modified

| File | Changes |
|------|---------|
| `.env` | Added `VITE_AUTH_REQUIRED=false`, `VITE_GOOGLE_CLIENT_ID` |
| `src/App.jsx` | Conditional routing based on `VITE_AUTH_REQUIRED` |
| `src/assets/context/RoleContext.jsx` | Added 5 missing backend roles to DEFAULT_ROLES |
| `src/utils/roleRouting.js` | Updated LOGIN_ROLES and mapBackendRoleToUi |
| `src/pages/PatientLogin.jsx` | Google Client ID from environment variable |
| `backend/config/settings/base.py` | Added RateLimitMiddleware to MIDDLEWARE |