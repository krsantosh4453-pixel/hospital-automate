from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from config.auth_cookie_views import CookieTokenRefreshView, csrf_token

from .dev_login import dev_login
from .security_settings import security_settings
from .staff_invite import accept_staff_invite
from .views import (
    google_login,
    patient_email_login,
    patient_email_otp_request,
    patient_email_otp_verify,
    patient_me,
    patient_otp_request,
    patient_otp_verify,
    patient_token_login,
    register_account,
    staff_login,
    staff_login_start_otp,
    staff_logout,
    staff_me,
    staff_otp_resend,
    staff_otp_verify,
    staff_password_reset_confirm,
    staff_password_reset_request,
)


urlpatterns = [
    path("google/", google_login, name="google-login"),
    path("dev/login/", dev_login, name="dev-login"),
    path("register/", register_account, name="register-account"),
    # Tokens are only issued by the staff/patient sign-in views, which apply
    # lockout, OTP policy and audit. The bare SimpleJWT obtain view is not exposed.
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("csrf/", csrf_token, name="csrf-token"),
    path("security-settings/", security_settings, name="security-settings"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Staff authentication endpoints
    path("staff/login/", staff_login, name="staff-login"),
    path("staff/login/otp/start/", staff_login_start_otp, name="staff-login-otp-start"),
    path("staff/login/otp/verify/", staff_otp_verify, name="staff-otp-verify"),
    path("staff/login/otp/resend/", staff_otp_resend, name="staff-otp-resend"),
    path("staff/logout/", staff_logout, name="staff-logout"),
    path("staff/me/", staff_me, name="staff-me"),
    path("staff/invite/<str:uidb64>/<str:token>/", accept_staff_invite, name="staff-invite-accept"),
    path("password/reset/", staff_password_reset_request, name="staff-password-reset"),
    path("password/reset/confirm/", staff_password_reset_confirm, name="staff-password-reset-confirm"),
    path("patient/otp/request/", patient_otp_request, name="patient-otp-request"),
    path("patient/otp/verify/", patient_otp_verify, name="patient-otp-verify"),
    path("patient/email-otp/request/", patient_email_otp_request, name="patient-email-otp-request"),
    path("patient/email-otp/verify/", patient_email_otp_verify, name="patient-email-otp-verify"),
    path("patient/login/", patient_email_login, name="patient-email-login"),
    path("patient/token/", patient_token_login, name="patient-token-login"),
    path("patient/me/", patient_me, name="patient-me"),
]