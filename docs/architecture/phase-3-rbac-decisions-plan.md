# Phase 3 RBAC decisions: verification and plan (awaiting approval)

Date: 2026-11-09. Applies the owner's three RBAC decisions to the code at `28be9d2`.
Nothing here is implemented yet. [V] = verified in the code today.
Related: [phase-3-plan.md](phase-3-plan.md) · [implementation-roadmap.md](implementation-roadmap.md)

## 1. What the code does today, against the decisions

### 1.1 Staff role assignment (decision 1)

| Rule in the decision | Today | Conflict |
|---|---|---|
| Manager may invite/assign Doctor, Nurse, Pharmacist, Compounder, Receptionist in their own hospital | Allowed: the Admin and Hospital Manager of the acting hospital may assign **every** role except Admin (`users/staff_admin._role`, used by invites and role changes) [V] | A Manager may also assign Lab Staff, Billing Staff, Inventory Staff, Blood Bank Staff **and Hospital Manager** (question Q1) |
| Cannot assign Hospital Admin or Super Admin | Only an Admin grants Admin [V]; platform roles cannot be assigned through any API (`PlatformStaff` is admin-site only) [V] | None |
| Cannot escalate own permissions | "You cannot change your own access" [V], tested [V] | None |
| Doctor qualifications and registration verified | `Doctor.registration_number` and `StaffProfile.license_number` exist as free text; **nothing records a verification** [V] | **Gap** |
| All invitations and role changes audited | `users.staff.invited`, `invite_resent`, `invite_accepted` and `membership_changed` are written [V] | None (tests will lock it in) |

### 1.2 Clinical records and prescriptions (decision 2)

Write access (create/update) today, from each viewset's permission classes [V]:

| Record | Admin | Hospital Manager | Doctor | Nurse | Pharmacist |
|---|---|---|---|---|---|
| Clinical notes | **writes** | – | writes | – | – |
| Diagnoses | **writes** | **writes** | writes | – | – |
| Procedures | **writes** | **writes** | writes | – | – |
| Medical records | **writes** | **writes** | writes | writes | – |
| Prescriptions + items | **writes** | – | writes | read | read; transcribes paper prescriptions (F13) |
| Vitals, allergies, service orders | **writes** | **writes** | writes | writes | – |
| Immunisations | **writes** | – | writes | writes | – |
| Nursing notes, assessments, MAR | – | – | writes | writes | – |
| IPD, emergency, discharge summaries | – | read | writes | writes | – |
| Certificates, referrals, AI drafts | – | – | writes | – | – |

Conflicts:
- **Admin writes 10 kinds of clinical record**, where the decision says read-only.
- **Hospital Manager writes diagnoses, procedures, medical records, vitals, allergies and service orders**, where the decision says no independent clinical editing.
- **Clinical notes trust a client-supplied `doctor`** (`ClinicalNoteSerializer`): an Admin can file a note in a doctor's name today. Prescriptions already force "your own name" [V]; diagnoses, vitals, medical records and immunisations record `recorded_by` from the signed-in user [V].
- **There is no signed state.** Prescriptions, notes and diagnoses are edited in place. The audit log keeps each changed field's old and new value (`HospitalScopedViewSet.perform_update`) [V], but there is no "signed" lock and no version history. Prescription lines can be replaced until medicine is dispensed [V]. Certificates are never edited once issued [V].
- Pharmacists already cannot change a doctor's prescription. Their writes are transcription of paper prescriptions and dispensing, which records `dispensed_at` and sales, not the prescribed content [V].
- Patients read their own records only (`IsPatientReadOnly` + linked patient) [V].
- The web app's role table (`RoleContext.jsx`) shows Admin as "Add/Edit/Delete" on Prescriptions, IPD, Emergency, AI Scribe and Laboratory. The backend already refuses Admin writes on IPD, emergency, AI drafts and lab [V].

### 1.3 Security settings (decision 3)

- `GET /api/auth/security-settings/` (Admin of any hospital) returns **server-wide configuration**: debug flag, cookie and throttle settings, proxy count; no secrets [V]. Nothing is editable through the API [V].
- There is no per-hospital view of sessions, sign-in history, permissions or alerts. The data exists: `DeviceSession` (Phase 3), sign-in events in `AuditLog`, the permission catalogue, `RoleModuleRestriction`, break-glass grants and `auth.refresh_reuse` audit rows [V].

## 2. Plan

### Step A — Staff assignment and doctor verification
1. Manager-assignable roles: Doctor, Nurse, Pharmacist, Compounder, Receptionist, **plus** whatever Q1 decides. The Admin keeps every role, as today.
2. Doctor verification (migration `doctors/0010`, additive): `registration_council` (text), `registration_verified_at`, `registration_verified_by` (FK user, null). A new action, `POST /api/v1/doctors/{id}/verify-registration/`, for the hospital's **Admin** (not the Manager), audited (`doctors.registration_verified`) and refused without a registration number. Enforcement per Q2.
3. Tests: every role a Manager may and may not assign, at their own and at another hospital; self-change refused; audit rows for invite, resend, accept, role change, deactivation and verification.

### Step B — Clinical write rules
1. Remove Admin and Hospital Manager from the **write** side of clinical notes, diagnoses, procedures, medical records, prescriptions and items, vitals, allergies, service orders and immunisations. Both keep **read** access under the existing care-scope and tenancy rules. Paper-prescription transcription and verification follow Q5.
2. Clinical notes: `doctor` is set from the signed-in doctor, as for prescriptions, and a doctor edits only their own notes.
3. Signed records (Q4): add `signed_at`/`signed_by` to clinical notes and diagnoses (migration `clinical/00xx`, additive). A signed record refuses PATCH/PUT/DELETE with 409; a correction is a new record with `amends` pointing at the original, and both are kept. Prescriptions count as signed at creation: a change before dispensing creates a new version and marks the old one superseded (status), never deleting its lines.
4. Web app: in `RoleContext.jsx`, Admin becomes "View" on Prescriptions, IPD, Emergency, AI Scribe and Laboratory, mirrored in `users/role_permissions.py` (the drift test keeps them equal). Pages already hide buttons by permission; no other UI change.
5. Tests: for each record type and each role, create/update/delete allowed or refused as in the table in section 3; a signed note refuses edits; an amendment keeps both; a note's author cannot be forged; a pharmacist cannot change prescribed content; a patient sees only their own records; all at the own and another hospital.

### Step C — Hospital security overview
1. New `GET /api/v1/hospital/security-overview/` (Admin of the acting hospital, read-only, hospital-scoped) returns:
   - active sessions of the hospital's staff (device, platform, last used; no IP address);
   - sign-in history from the audit log (last 30 days, paginated);
   - users with their roles and effective permissions, and restricted modules;
   - alerts: refresh-token reuse, OTP and password lockouts, break-glass grants awaiting sign-off.

   For staff who also work elsewhere, only their activity at this hospital is shown. Sessions belong to the person, so each of their hospitals' Admins sees them (Q3).
2. Session sign-out from the overview: per Q3.
3. Server-wide configuration (`auth/security-settings/`) moves behind a platform permission, `platform.security.view`, so hospital Admins no longer see it. Nothing becomes editable through the API; global policies, credentials and secrets stay in environment variables.
4. Web app: the Security settings page shows the hospital overview; the server-configuration block is shown only to platform staff.
5. Tests: Admin of A sees only A's staff, sessions, history and alerts; a forged `X-Hospital-ID: B` is refused; non-Admins are refused; no IP address or token value appears in the response; platform staff see the server configuration and hospital Admins do not.

## 3. Target write matrix (after Step B)

| Record | Admin | Manager | Doctor | Nurse | Pharmacist | Patient |
|---|---|---|---|---|---|---|
| Clinical notes, diagnoses, procedures | read | read | write own, sign | read | – | own, read |
| Medical records | read | read | write | Q6 | – | own, read |
| Prescriptions | read | – | write own (versioned) | read | read, dispense; transcribe paper (Q5) | own, read |
| Vitals, allergies, service orders, immunisations | read | read | write | write | – | own, read |
| Nursing notes, assessments, MAR | – | – | write | write | – | – |

## 4. Database changes (all additive, reversible)

| Migration | Change |
|---|---|
| `doctors/0010` | `registration_council`, `registration_verified_at`, `registration_verified_by` |
| `clinical/00xx` | `signed_at`, `signed_by`, `amends` on clinical notes and diagnoses; `supersedes` and a `Superseded` status on prescriptions |

No column is removed or rewritten. Existing records stay unsigned (editable by their author) until signed.

## 5. Questions before implementation

- **Q1** Besides the five roles you listed, may a Manager assign Lab Staff, Billing Staff, Inventory Staff and Blood Bank Staff (operational, non-clinical)? And **Hospital Manager** (a peer with the same powers)? Recommendation: yes to the four operational roles, no to Hospital Manager (Admin only).
- **Q2** Doctor verification: is it enough that the hospital Admin records who checked the registration and when? And what happens to an unverified doctor: (a) a warning only, or (b) they cannot sign prescriptions or notes until verified? Existing doctors would start unverified. Recommendation: (b), switched on per hospital once its Admin has verified its current doctors, so nobody is blocked on deploy day.
- **Q3** Sessions on the overview: read-only (recommended), or may the Admin sign a staff member out when this is their only hospital?
- **Q4** Signed clinical notes and diagnoses: signed when the doctor presses Sign, with an unsigned draft until then (recommended), or automatically at creation?
- **Q5** Paper-prescription transcription and verification are Admin or Pharmacist today. Keep the Admin? Recommendation: Pharmacist only.
- **Q6** Medical records: nurses write them today. Keep that (recommended, for nursing entries), or doctors only?

## 6. Not touched

Billing, pharmacy stock, the laboratory workflow, IPD and emergency permissions (already clinical-only), the AI scribe, platform staff, the Phase 3 sessions and tokens, and any module not named above.
