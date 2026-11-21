import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/auth/auth_errors.dart';
import 'package:hms_mobile/features/auth/auth_service.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_hi.dart';

void main() {
  final t = AppLocalizationsEn();

  ApiException signIn(
    int status,
    String error, [
    Set<String> flags = const {},
  ]) => ApiException(
    kind: ApiException.kindForStatus(status),
    statusCode: status,
    serverMessage: error,
    flags: flags,
  );

  test('a wrong password says so, never "your session has ended"', () {
    final message = authErrorMessage(
      t,
      signIn(401, 'Invalid credentials.'),
      AuthStep.credentials,
    );

    expect(message, t.authInvalidCredentials);
    expect(message, isNot(t.errorUnauthorized));
  });

  test(
    'an unrecognised 401 on the password step is still a credentials problem',
    () {
      const error = ApiException(
        kind: ApiErrorKind.unauthorized,
        statusCode: 401,
      );

      expect(
        authErrorMessage(t, error, AuthStep.credentials),
        t.authInvalidCredentials,
      );
      expect(authErrorMessage(t, error, AuthStep.code), t.authInvalidOtp);
    },
  );

  test('sign-in sentences ({"error": "..."}) map to their own messages', () {
    expect(
      authErrorMessage(
        t,
        signIn(401, 'Account is disabled.'),
        AuthStep.credentials,
      ),
      t.authAccountDisabled,
    );
    expect(
      authErrorMessage(t, signIn(401, 'Invalid OTP.'), AuthStep.code),
      t.authInvalidOtp,
    );
    expect(
      authErrorMessage(t, signIn(401, 'OTP has expired.'), AuthStep.code),
      t.authOtpExpired,
    );
    // Seen live from patient/otp/verify on the development backend.
    expect(
      authErrorMessage(
        t,
        signIn(401, 'Invalid or expired OTP.'),
        AuthStep.code,
      ),
      t.authResetCodeInvalid,
    );
    expect(
      authErrorMessage(
        t,
        signIn(
          400,
          'Sign-in session expired or invalid. Enter your password again.',
        ),
        AuthStep.code,
      ),
      t.authChallengeExpired,
    );
    expect(
      authErrorMessage(
        t,
        signIn(
          429,
          'Too many failed sign-in attempts. Try again in 15 minutes or reset your password.',
        ),
        AuthStep.credentials,
      ),
      t.authLockedOut,
    );
    expect(
      authErrorMessage(
        t,
        signIn(
          403,
          'Staff accounts must sign in with username, password and the SMS code.',
        ),
        AuthStep.code,
      ),
      t.authStaffUseStaffLogin,
    );
    expect(
      authErrorMessage(
        t,
        signIn(
          400,
          'We could not create an account with these details. If you already '
          'have an account, sign in or reset your password.',
        ),
        AuthStep.registration,
      ),
      t.authRegistrationUnavailable,
    );
  });

  test('the server requiring OTP while SMS is unavailable is explained', () {
    final error = signIn(
      403,
      'This hospital requires a one-time code. Use the OTP sign-in.',
      {'otp_required'},
    );

    expect(
      authErrorMessage(t, error, AuthStep.credentials),
      t.authOtpRequiredUnavailable,
    );
  });

  test(
    'standard envelope errors and network failures use the app-wide messages',
    () {
      const envelope = ApiException(
        kind: ApiErrorKind.server,
        statusCode: 500,
        serverMessage: 'Internal error',
      );
      const offline = ApiException(kind: ApiErrorKind.network);

      expect(
        authErrorMessage(t, envelope, AuthStep.credentials),
        t.errorServer,
      );
      expect(authErrorMessage(t, offline, AuthStep.code), t.errorNetwork);
    },
  );

  test('SMS not configured (503) and unsupported accounts are explained', () {
    expect(
      authErrorMessage(
        t,
        signIn(503, 'Twilio Verify is not configured.'),
        AuthStep.code,
      ),
      t.authSmsUnavailable,
    );
    expect(
      authErrorMessage(
        t,
        const UnsupportedAccountException(),
        AuthStep.credentials,
      ),
      t.authUnsupportedAccount,
    );
  });

  test('messages are translated, not the server text', () {
    final hi = AppLocalizationsHi();

    final message = authErrorMessage(
      hi,
      signIn(401, 'Invalid credentials.'),
      AuthStep.credentials,
    );

    expect(message, hi.authInvalidCredentials);
    expect(message, isNot(contains('Invalid credentials')));
  });
}
