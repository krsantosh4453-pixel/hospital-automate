import '../../core/localization/l10n.dart';
import '../../core/network/api_exception.dart';
import 'auth_service.dart';
import 'google_identity.dart';

/// Which part of a sign-in flow failed, so an unrecognised 401 or 400 is
/// explained in the right terms (a wrong password is never "session ended").
enum AuthStep { credentials, code, newPassword, registration, request }

/// A translated, safe message for a failed sign-in step.
///
/// Sign-in views answer `{"error": "<sentence>"}`; known sentences map to
/// translated messages (matched, never shown raw), everything else falls
/// back on the status code and [step]. Network and server failures use the
/// app-wide messages.
String authErrorMessage(AppLocalizations t, Object error, AuthStep step) {
  if (error is UnsupportedAccountException) return t.authUnsupportedAccount;
  if (error is GoogleSignInFailure) {
    return error.misconfigured ? t.authGoogleNotSetUp : t.authGoogleFailed;
  }
  if (error is! ApiException) return t.errorUnknown;
  if (error.hasFlag('otp_required')) return t.authOtpRequiredUnavailable;
  final known = _knownMessage(t, error.serverMessage);
  if (known != null) return known;
  return switch (error.kind) {
    ApiErrorKind.unauthorized => switch (step) {
      AuthStep.code => t.authInvalidOtp,
      AuthStep.newPassword => t.authResetCodeInvalid,
      _ => t.authInvalidCredentials,
    },
    ApiErrorKind.validation => switch (step) {
      AuthStep.code => t.authInvalidOtp,
      AuthStep.newPassword || AuthStep.registration => t.authPasswordRejected,
      _ => t.errorValidation,
    },
    ApiErrorKind.forbidden => t.authNotAllowed,
    ApiErrorKind.rateLimited => t.authTooManyRequests,
    ApiErrorKind.unavailable => t.authSmsUnavailable,
    _ => apiErrorMessage(t, error),
  };
}

String? _knownMessage(AppLocalizations t, String? message) {
  if (message == null) return null;
  final text = message.toLowerCase();
  bool has(String part) => text.contains(part);
  if (has('password are required')) return t.authFieldsRequired;
  if (has('too many failed sign-in')) return t.authLockedOut;
  if (has('invalid credentials') ||
      has('invalid email or password') ||
      has('invalid patient credentials')) {
    return t.authInvalidCredentials;
  }
  if (has('account is disabled')) return t.authAccountDisabled;
  if (has('not authorized as staff')) return t.authNotStaff;
  if (has('sign-in session expired')) return t.authChallengeExpired;
  if (has('your sign-in has expired')) return t.authFamilyTicketExpired;
  if (has('family access is not available')) return t.authFamilyNotAvailable;
  if (has('family members have view-only')) return t.authNotAllowed;
  if (has('too many wrong codes')) return t.authOtpLocked;
  if (has('wait before requesting')) return t.authOtpCooldown;
  if (has('invalid or expired otp')) return t.authResetCodeInvalid;
  if (has('otp has expired')) return t.authOtpExpired;
  if (has('invalid otp')) return t.authInvalidOtp;
  if (has('too many otp requests')) return t.authTooManyRequests;
  if (has('10-digit mobile')) return t.authInvalidPhone;
  if (has('valid email address')) return t.authInvalidEmail;
  if (has('email is not verified')) return t.authEmailNotVerified;
  if (has('staff accounts must sign in')) return t.authStaffUseStaffLogin;
  if (has('staff accounts are created by your hospital')) {
    return t.authStaffInviteOnly;
  }
  if (has('password reset by sms is not configured')) {
    return t.authResetUnavailable;
  }
  if (has('code is invalid or has expired')) return t.authResetCodeInvalid;
  if (has('at least 8 characters')) return t.authPasswordTooShort;
  if (has('do not match')) return t.authPasswordMismatch;
  if (has('full name is required')) return t.authNameRequired;
  if (has('date of birth')) return t.authInvalidDob;
  if (has('already exists with this email')) return t.authEmailExists;
  if (has('already exists with this mobile')) return t.authPhoneExists;
  if (has('verification email')) return t.authEmailSendFailed;
  if (has('google authentication failed') || has('google credential')) {
    return t.authGoogleFailed;
  }
  return null;
}
