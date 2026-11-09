"""
API views that are not built on HospitalScopedViewSet, each with the reason
(Phase 3). security_tests/test_tenancy_guard.py fails when an /api/ view is
neither hospital-scoped nor listed here, so a new endpoint cannot skip the
tenancy check unnoticed.

Categories:
- auth: signs in or out, or acts only on the caller's own account.
- public: no tenant data (docs, CSRF, reference data, directory).
- platform: platform-wide data guarded by a platform permission or Admin.
- own-checks: tenant data with the view's own membership checks; each has a
  cross-hospital test in security_tests/test_handwritten_views_isolation.py.
- webhook: called by a provider with a signature, no user.
"""

AUTH, PUBLIC, PLATFORM, OWN_CHECKS, WEBHOOK = "auth", "public", "platform", "own-checks", "webhook"

TENANCY_EXEMPTIONS = {
    # Sign-in, sign-out and the caller's own account
    "config.auth_cookie_views.CookieTokenRefreshView": (AUTH, "Refreshes the caller's own session"),
    "config.auth_cookie_views.csrf_token": (PUBLIC, "CSRF token for the browser"),
    "rest_framework_simplejwt.views.TokenVerifyView": (AUTH, "Checks a token's signature only"),
    "users.dev_login.dev_login": (AUTH, "Development-only sign-in, off in production"),
    "users.proxy_views.family_access": (AUTH, "The signed-in patient's own family-access grants"),
    "users.proxy_views.proxy_login": (AUTH, "Family-member sign-in"),
    "users.proxy_views.proxy_otp_request": (AUTH, "Family-member OTP"),
    "users.proxy_views.proxy_otp_verify": (AUTH, "Family-member OTP"),
    "users.proxy_views.revoke_family_access": (AUTH, "Revokes the signed-in patient's own grant"),
    "users.sessions_views.logout_all": (AUTH, "The caller's own sessions"),
    "users.sessions_views.me_contexts": (AUTH, "The caller's own memberships"),
    "users.sessions_views.session_list": (AUTH, "The caller's own sessions"),
    "users.sessions_views.session_revoke": (AUTH, "The caller's own sessions (404 for others)"),
    "users.staff_invite.accept_staff_invite": (AUTH, "Signed one-time invite link"),
    "users.views.google_login": (AUTH, "Patient sign-in"),
    "users.views.patient_email_login": (AUTH, "Patient sign-in"),
    "users.views.patient_email_otp_request": (AUTH, "Patient OTP"),
    "users.views.patient_email_otp_verify": (AUTH, "Patient OTP"),
    "users.views.patient_me": (AUTH, "The signed-in patient's own profile"),
    "users.views.patient_otp_request": (AUTH, "Patient OTP"),
    "users.views.patient_otp_verify": (AUTH, "Patient OTP"),
    "users.views.patient_token_login": (AUTH, "Patient sign-in"),
    "users.views.register_account": (AUTH, "Account registration"),
    "users.views.staff_login": (AUTH, "Staff sign-in"),
    "users.views.staff_login_start_otp": (AUTH, "Staff sign-in"),
    "users.views.staff_logout": (AUTH, "Signs the presented session out"),
    "users.views.staff_me": (AUTH, "The signed-in staff member's own profile and memberships"),
    "users.views.staff_otp_resend": (AUTH, "Staff OTP"),
    "users.views.staff_otp_verify": (AUTH, "Staff OTP"),
    "users.views.staff_password_reset_confirm": (AUTH, "Password reset"),
    "users.views.staff_password_reset_request": (AUTH, "Password reset"),
    # No tenant data
    "config.schema.RedocView": (PUBLIC, "API documentation"),
    "config.schema.SchemaAPIView": (PUBLIC, "API documentation"),
    "config.schema.SwaggerUIView": (PUBLIC, "API documentation"),
    "rest_framework.routers.APIRootView": (PUBLIC, "Lists route names only"),
    "terminology.views.ICD10SearchView": (PUBLIC, "ICD-10 reference codes"),
    "hospital.views.HospitalDirectoryView": (PUBLIC, "Public names and cities of active hospitals"),
    "consent.rights.PrivacyNoticeView": (PUBLIC, "Published privacy notice"),
    "consent.views.ConsentFormListView": (PUBLIC, "Consent form templates, shared by all hospitals"),
    "consent.views.ConsentFormDetailView": (PUBLIC, "Consent form templates, shared by all hospitals"),
    "documents.views.DocumentCategoryListView": (PUBLIC, "Document categories, shared by all hospitals"),
    "documents.views.DocumentCategoryDetailView": (PUBLIC, "Document categories, shared by all hospitals"),
    # Platform-wide
    "hospital.views.HospitalViewSet": (PLATFORM, "Members see their hospitals; platform staff see all"),
    "notifications.views.OTPVerificationViewSet": (PLATFORM, "platform.otp_log.view only"),
    "reports.views.ReportTemplateViewSet": (PLATFORM, "Shared templates; platform.report_templates.edit to change"),
    "users.security_settings.security_settings": (PLATFORM, "Server configuration, no secrets and no tenant data; "
                                                          "readable by any hospital Admin (Security settings page)"),
    # Tenant data with their own checks (tested in test_handwritten_views_isolation.py)
    "abdm.views.StatusView": (OWN_CHECKS, "Requires X-Hospital-ID and membership"),
    "abdm.views.RequestOTPView": (OWN_CHECKS, "Requires X-Hospital-ID and membership"),
    "abdm.views.ConfirmOTPView": (OWN_CHECKS, "Requires X-Hospital-ID and membership"),
    "abdm.views.LinkListView": (OWN_CHECKS, "Requires X-Hospital-ID and membership"),
    "audit.break_glass.BreakGlassAccessViewSet": (OWN_CHECKS, "Filters by the caller's hospitals"),
    "consent.rights.RightsRequestListView": (OWN_CHECKS, "Filters by the caller's hospitals"),
    "consent.rights.RightsRequestRespondView": (OWN_CHECKS, "Checks the request's hospital"),
    "consent.views.ConsentRecordListView": (OWN_CHECKS, "Filters by the caller's hospitals"),
    "consent.views.ConsentRecordDetailView": (OWN_CHECKS, "Checks the record's hospital"),
    "consent.views.ConsentRecordRevokeView": (OWN_CHECKS, "Checks the record's hospital"),
    "consent.views.RecordShareListView": (OWN_CHECKS, "Filters by the caller's hospitals"),
    "consent.views.RecordShareRevokeView": (OWN_CHECKS, "Checks the share's hospital"),
    "consent.views.RecordShareAccessLogView": (OWN_CHECKS, "Checks the share's hospital"),
    "consent.views.ReceivedShareListView": (OWN_CHECKS, "Shares received by the caller's hospitals"),
    "consent.views.SharedRecordsView": (OWN_CHECKS, "Only the recipient hospital, only shared parts"),
    "documents.views.DocumentListView": (OWN_CHECKS, "Filters by the caller's hospitals"),
    "documents.views.DocumentDetailView": (OWN_CHECKS, "Checks the document's hospital"),
    "documents.views.DocumentDownloadView": (OWN_CHECKS, "Checks the document's hospital"),
    "documents.views.DocumentPreviewView": (OWN_CHECKS, "Checks the document's hospital"),
    "documents.views.DocumentSearchView": (OWN_CHECKS, "Filters by the caller's hospitals"),
    "documents.views.PatientDocumentListView": (OWN_CHECKS, "Only the caller's hospitals' documents"),
    "documents.views.PatientDocumentUploadView": (OWN_CHECKS, "Into the acting hospital only"),
    "fhir.views.CapabilityStatementView": (OWN_CHECKS, "Admin of the acting hospital; off unless FHIR_ENABLED"),
    "fhir.views.ResourceSearchView": (OWN_CHECKS, "Admin of the acting hospital; off unless FHIR_ENABLED"),
    "fhir.views.ResourceReadView": (OWN_CHECKS, "Admin of the acting hospital; off unless FHIR_ENABLED"),
    "fhir.views.PatientEverythingView": (OWN_CHECKS, "Admin of the acting hospital; off unless FHIR_ENABLED"),
    "home.views.home_dashboard": (OWN_CHECKS, "Checks the requested hospital's membership"),
    "home.views.home_stats_summary": (OWN_CHECKS, "Checks the requested hospital's membership"),
    "reports.views.AnalyticsViewSet": (OWN_CHECKS, "Checks the requested hospital's membership"),
    "reports.views.KPISnapshotViewSet": (OWN_CHECKS, "Filters by the caller's hospitals"),
    "reports.views.SavedReportViewSet": (OWN_CHECKS, "Own reports in the caller's hospitals"),
    "reports.views.ScheduledReportViewSet": (OWN_CHECKS, "Filters by the caller's hospitals"),
    "users.staff_admin.StaffListView": (OWN_CHECKS, "Admin or Manager of the acting hospital"),
    "users.staff_admin.StaffMembershipView": (OWN_CHECKS, "Admin or Manager of the acting hospital"),
    "users.staff_invite.StaffInviteView": (OWN_CHECKS, "Admin or Manager of the acting hospital"),
    "users.staff_invite.StaffInviteResendView": (OWN_CHECKS, "Admin or Manager of the acting hospital"),
    # Provider callbacks
    "notifications.views.TwilioStatusView": (WEBHOOK, "Signed by Twilio; one delivery status per call"),
}
