from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

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
    staff_logout,
    staff_me,
)


urlpatterns = [
    path("google/", google_login, name="google-login"),
    path("register/", register_account, name="register-account"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Staff authentication endpoints
    path("staff/login/", staff_login, name="staff-login"),
    path("staff/logout/", staff_logout, name="staff-logout"),
    path("staff/me/", staff_me, name="staff-me"),
    path("patient/otp/request/", patient_otp_request, name="patient-otp-request"),
    path("patient/otp/verify/", patient_otp_verify, name="patient-otp-verify"),
    path("patient/email-otp/request/", patient_email_otp_request, name="patient-email-otp-request"),
    path("patient/email-otp/verify/", patient_email_otp_verify, name="patient-email-otp-verify"),
    path("patient/login/", patient_email_login, name="patient-email-login"),
    path("patient/token/", patient_token_login, name="patient-token-login"),
    path("patient/me/", patient_me, name="patient-me"),
]