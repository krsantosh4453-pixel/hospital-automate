import '../../core/network/api_client.dart';
import '../../core/security/session_controller.dart';
import '../../core/security/token_store.dart';
import 'auth_models.dart';

/// Every authentication endpoint the backend has (`/api/v1/auth/`), through
/// the shared [ApiClient]. Sign-in calls are anonymous: they carry no token
/// and a 401 from them never triggers a token refresh.
///
/// Failures are thrown as `ApiException`; nothing here logs request bodies.
abstract interface class AuthRepository {
  /// `GET auth/staff/login/options/`: whether staff sign-in needs or can use
  /// a one-time code on this server.
  Future<StaffLoginOptions> staffLoginOptions();

  Future<StaffOtpChallenge> staffStartOtp(
    String username,
    String password,
    DeviceInfo device,
  );
  Future<AuthTokens> staffVerifyOtp(
    String challenge,
    String otp,
    DeviceInfo device,
  );
  Future<void> staffResendOtp(String challenge);
  Future<AuthTokens> staffPasswordLogin(
    String username,
    String password,
    DeviceInfo device,
  );

  Future<OtpDelivery> patientRequestOtp(String phone);
  Future<AuthTokens> patientVerifyOtp(
    String phone,
    String otp,
    DeviceInfo device,
  );
  Future<AuthTokens> patientEmailLogin(
    String email,
    String password,
    DeviceInfo device,
  );
  Future<AuthTokens> patientIdLogin(
    String identifier,
    String password,
    DeviceInfo device,
  );
  Future<OtpDelivery> requestEmailOtp(String email);
  Future<void> verifyEmailOtp(String email, String otp);
  Future<RegistrationResult> registerPatient(PatientRegistration registration);

  /// Hospitals open to patient self-registration (sign-up and joining).
  Future<List<PublicHospital>> patientHospitals();

  /// The signed-in patient registers at a hospital; the server issues its
  /// UHID once (repeating returns the same one).
  Future<void> joinHospital(int hospitalId);

  /// Family member / caregiver: code to their own mobile, then a ticket to
  /// open one patient's records view-only.
  Future<OtpDelivery> proxyRequestOtp(String phone);
  Future<ProxyVerification> proxyVerifyOtp(String phone, String otp);
  Future<AuthTokens> proxyLogin(String ticket, int grantId, DeviceInfo device);

  /// Patients only: the server refuses staff accounts here.
  Future<AuthTokens> googleLogin(String idToken, DeviceInfo device);

  Future<void> requestPasswordReset(String username);
  Future<void> confirmPasswordReset(
    String username,
    String code,
    String newPassword,
  );

  /// Rotates the pair; the old refresh token stops working.
  Future<AuthTokens> refresh(String refreshToken);
  Future<void> logout(String refreshToken);
  Future<void> logoutAll();

  Future<MeContexts> meContexts();
  Future<SessionUser> staffMe();
  Future<SessionUser> patientMe(AccountType accountType);

  Future<List<DeviceSessionInfo>> sessions();
  Future<void> revokeSession(String sessionId);
}

class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository(this._api);

  final ApiClient _api;

  Future<AuthTokens> _signIn(String path, Map<String, Object?> body) =>
      _api.post(path, body: body, anonymous: true, decode: AuthTokens.fromJson);

  @override
  Future<StaffLoginOptions> staffLoginOptions() => _api.get(
    'auth/staff/login/options/',
    anonymous: true,
    decode: StaffLoginOptions.fromJson,
  );

  @override
  Future<StaffOtpChallenge> staffStartOtp(
    String username,
    String password,
    DeviceInfo device,
  ) => _api.post(
    'auth/staff/login/otp/start/',
    body: {'username': username, 'password': password, ...device.toJson()},
    anonymous: true,
    decode: StaffOtpChallenge.fromJson,
  );

  @override
  Future<AuthTokens> staffVerifyOtp(
    String challenge,
    String otp,
    DeviceInfo device,
  ) => _signIn('auth/staff/login/otp/verify/', {
    'challenge': challenge,
    'otp': otp,
    ...device.toJson(),
  });

  @override
  Future<void> staffResendOtp(String challenge) => _api.post(
    'auth/staff/login/otp/resend/',
    body: {'challenge': challenge},
    anonymous: true,
    decode: (_) {},
  );

  @override
  Future<AuthTokens> staffPasswordLogin(
    String username,
    String password,
    DeviceInfo device,
  ) => _signIn('auth/staff/login/', {
    'username': username,
    'password': password,
    ...device.toJson(),
  });

  @override
  Future<OtpDelivery> patientRequestOtp(String phone) => _api.post(
    'auth/patient/otp/request/',
    body: {'phone': phone},
    anonymous: true,
    decode: OtpDelivery.fromJson,
  );

  @override
  Future<AuthTokens> patientVerifyOtp(
    String phone,
    String otp,
    DeviceInfo device,
  ) => _signIn('auth/patient/otp/verify/', {
    'phone': phone,
    'otp': otp,
    ...device.toJson(),
  });

  @override
  Future<AuthTokens> patientEmailLogin(
    String email,
    String password,
    DeviceInfo device,
  ) => _signIn('auth/patient/login/', {
    'email': email,
    'password': password,
    ...device.toJson(),
  });

  @override
  Future<AuthTokens> patientIdLogin(
    String identifier,
    String password,
    DeviceInfo device,
  ) => _signIn('auth/patient/token/', {
    'identifier': identifier,
    'password': password,
    ...device.toJson(),
  });

  @override
  Future<OtpDelivery> requestEmailOtp(String email) => _api.post(
    'auth/patient/email-otp/request/',
    body: {'email': email},
    anonymous: true,
    decode: OtpDelivery.fromJson,
  );

  @override
  Future<void> verifyEmailOtp(String email, String otp) => _api.post(
    'auth/patient/email-otp/verify/',
    body: {'email': email, 'otp': otp},
    anonymous: true,
    decode: (_) {},
  );

  @override
  Future<RegistrationResult> registerPatient(
    PatientRegistration registration,
  ) => _api.post(
    'auth/register/',
    body: registration.toJson(),
    anonymous: true,
    decode: (json) => RegistrationResult.fromJson(json, registration.email),
  );

  @override
  Future<List<PublicHospital>> patientHospitals() => _api.get(
    'auth/patient/hospitals/',
    anonymous: true,
    decode: (json) => [
      for (final row in json is List ? json : const [])
        PublicHospital.fromJson(row),
    ],
  );

  @override
  Future<void> joinHospital(int hospitalId) => _api.post(
    'auth/patient/hospitals/join/',
    body: {'hospital': hospitalId},
    decode: (_) {},
  );

  @override
  Future<OtpDelivery> proxyRequestOtp(String phone) => _api.post(
    'auth/proxy/otp/request/',
    body: {'phone': phone},
    anonymous: true,
    decode: OtpDelivery.fromJson,
  );

  @override
  Future<ProxyVerification> proxyVerifyOtp(String phone, String otp) =>
      _api.post(
        'auth/proxy/otp/verify/',
        body: {'phone': phone, 'otp': otp},
        anonymous: true,
        decode: ProxyVerification.fromJson,
      );

  @override
  Future<AuthTokens> proxyLogin(
    String ticket,
    int grantId,
    DeviceInfo device,
  ) => _signIn('auth/proxy/login/', {
    'ticket': ticket,
    'grant': grantId,
    ...device.toJson(),
  });

  @override
  Future<AuthTokens> googleLogin(String idToken, DeviceInfo device) =>
      _signIn('auth/google/', {'credential': idToken, ...device.toJson()});

  @override
  Future<void> requestPasswordReset(String username) => _api.post(
    'auth/password/reset/',
    body: {'username': username},
    anonymous: true,
    decode: (_) {},
  );

  @override
  Future<void> confirmPasswordReset(
    String username,
    String code,
    String newPassword,
  ) => _api.post(
    'auth/password/reset/confirm/',
    body: {'username': username, 'code': code, 'new_password': newPassword},
    anonymous: true,
    decode: (_) {},
  );

  @override
  Future<AuthTokens> refresh(String refreshToken) =>
      _signIn('auth/token/refresh/', {'refresh': refreshToken});

  @override
  Future<void> logout(String refreshToken) => _api.post(
    'auth/staff/logout/',
    body: {'refresh': refreshToken},
    anonymous: true,
    decode: (_) {},
  );

  @override
  Future<void> logoutAll() => _api.post('auth/logout-all/', decode: (_) {});

  @override
  Future<MeContexts> meContexts() =>
      _api.get('auth/me/contexts/', decode: MeContexts.fromJson);

  @override
  Future<SessionUser> staffMe() =>
      _api.get('auth/staff/me/', decode: staffUserFromJson);

  @override
  Future<SessionUser> patientMe(AccountType accountType) => _api.get(
    'auth/patient/me/',
    decode: (json) => patientUserFromJson(json, accountType),
  );

  @override
  Future<List<DeviceSessionInfo>> sessions() =>
      _api.get('auth/sessions/', decode: DeviceSessionInfo.listFromJson);

  @override
  Future<void> revokeSession(String sessionId) => _api.post(
    'auth/sessions/${Uri.encodeComponent(sessionId)}/revoke/',
    decode: (_) {},
  );
}
