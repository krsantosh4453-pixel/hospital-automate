import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/core/security/token_store.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/auth/auth_repository.dart';
import 'package:hms_mobile/features/auth/google_identity.dart';

/// Google's picker without the plugin: hands back [idToken] (null = the
/// person closed the picker) or throws [failure]. All values synthetic.
class FakeGoogleIdentity implements GoogleIdentity {
  FakeGoogleIdentity({this.idToken = 'google-id-token', this.failure});

  String? idToken;
  GoogleSignInFailure? failure;
  int requests = 0;

  @override
  bool get isAvailable => true;

  @override
  Future<String?> requestIdToken() async {
    requests++;
    if (failure != null) throw failure!;
    return idToken;
  }
}

/// Answers like the development backend unless a test overrides a field:
/// SMS OTP unavailable (so staff sign in with the password), one hospital
/// with a Doctor role. Every call is recorded by name in [calls]. All data
/// is synthetic.
class FakeAuthRepository implements AuthRepository {
  final List<String> calls = [];

  /// Bodies of the sign-in calls, to check what was sent (never logged).
  final List<Map<String, String>> sent = [];

  int _issued = 0;

  AuthTokens nextTokens() {
    _issued++;
    return AuthTokens(access: 'access-$_issued', refresh: 'refresh-$_issued');
  }

  Object? staffStartOtpError = const ApiException(
    kind: ApiErrorKind.unavailable,
    statusCode: 503,
    serverMessage:
        "SMS OTP is turned off on this server (OTP_PROVIDER is not 'twilio').",
    flags: {'otp_unavailable'},
  );
  Object? staffPasswordError;
  Object? otpVerifyError;
  Object? patientOtpVerifyError;
  Object? refreshError;
  Object? meContextsError;
  Object? logoutError;
  OtpDelivery patientOtpDelivery = const OtpDelivery(channel: 'console');
  Object? patientOtpRequestError;
  Object? proxyLoginError;
  Object? googleLoginError;

  /// Patients the family member may open after the code (synthetic).
  List<ProxyGrantChoice> proxyGrants = const [
    ProxyGrantChoice(
      id: 41,
      patientName: 'Test Patient One',
      relationship: 'Son',
    ),
  ];

  MeContexts contexts = const MeContexts(
    accountType: AccountType.staff,
    hospitals: [
      HospitalContext(
        id: 7,
        name: 'Test General Hospital',
        role: 'Doctor',
        permissions: {'Dashboard.View', 'Patients.View', 'Queue.View'},
      ),
      HospitalContext(
        id: 9,
        name: 'Test City Clinic',
        role: 'Nurse',
        permissions: {'Dashboard.View', 'Nurses.View'},
      ),
    ],
  );

  SessionUser staffUser = const SessionUser(
    id: 3,
    username: 'dr.test',
    displayName: 'Test Doctor',
    firstName: 'Test',
  );

  List<DeviceSessionInfo> devices = const [
    DeviceSessionInfo(id: 's-1', platform: 'android', current: true),
    DeviceSessionInfo(id: 's-2', platform: 'web', current: false),
  ];

  Future<T> _answer<T>(String name, Object? error, T Function() value) async {
    calls.add(name);
    if (error != null) throw error;
    return value();
  }

  @override
  Future<StaffOtpChallenge> staffStartOtp(
    String username,
    String password,
    DeviceInfo device,
  ) {
    sent.add({'username': username, ...device.toJson()});
    return _answer(
      'staffStartOtp',
      staffStartOtpError,
      () => const StaffOtpChallenge(
        challenge: 'signed-challenge',
        maskedPhone: '******3210',
      ),
    );
  }

  @override
  Future<AuthTokens> staffVerifyOtp(
    String challenge,
    String otp,
    DeviceInfo device,
  ) => _answer('staffVerifyOtp', otpVerifyError, nextTokens);

  @override
  Future<void> staffResendOtp(String challenge) =>
      _answer('staffResendOtp', null, () {});

  @override
  Future<AuthTokens> staffPasswordLogin(
    String username,
    String password,
    DeviceInfo device,
  ) {
    sent.add({'username': username, ...device.toJson()});
    return _answer('staffPasswordLogin', staffPasswordError, nextTokens);
  }

  @override
  Future<OtpDelivery> patientRequestOtp(String phone) => _answer(
    'patientRequestOtp',
    patientOtpRequestError,
    () => patientOtpDelivery,
  );

  @override
  Future<AuthTokens> patientVerifyOtp(
    String phone,
    String otp,
    DeviceInfo device,
  ) => _answer('patientVerifyOtp', patientOtpVerifyError, nextTokens);

  @override
  Future<AuthTokens> patientEmailLogin(
    String email,
    String password,
    DeviceInfo device,
  ) => _answer('patientEmailLogin', null, nextTokens);

  @override
  Future<AuthTokens> patientIdLogin(
    String identifier,
    String password,
    DeviceInfo device,
  ) => _answer('patientIdLogin', null, nextTokens);

  @override
  Future<OtpDelivery> requestEmailOtp(String email) => _answer(
    'requestEmailOtp',
    null,
    () => const OtpDelivery(channel: 'email'),
  );

  @override
  Future<void> verifyEmailOtp(String email, String otp) =>
      _answer('verifyEmailOtp', null, () {});

  @override
  Future<RegistrationResult> registerPatient(
    PatientRegistration registration,
  ) => _answer(
    'registerPatient',
    null,
    () => RegistrationResult(
      email: registration.email,
      delivery: const OtpDelivery(channel: 'console'),
    ),
  );

  @override
  Future<OtpDelivery> proxyRequestOtp(String phone) => _answer(
    'proxyRequestOtp',
    null,
    () => const OtpDelivery(channel: 'console'),
  );

  @override
  Future<ProxyVerification> proxyVerifyOtp(String phone, String otp) => _answer(
    'proxyVerifyOtp',
    null,
    () => ProxyVerification(ticket: 'signed-ticket', grants: proxyGrants),
  );

  @override
  Future<AuthTokens> proxyLogin(String ticket, int grantId, DeviceInfo device) {
    sent.add({'ticket': ticket, 'grant': '$grantId', ...device.toJson()});
    return _answer('proxyLogin:$grantId', proxyLoginError, nextTokens);
  }

  @override
  Future<AuthTokens> googleLogin(String idToken, DeviceInfo device) {
    sent.add({'credential': idToken, ...device.toJson()});
    return _answer('googleLogin', googleLoginError, nextTokens);
  }

  @override
  Future<void> requestPasswordReset(String username) =>
      _answer('requestPasswordReset', null, () {});

  @override
  Future<void> confirmPasswordReset(
    String username,
    String code,
    String newPassword,
  ) => _answer('confirmPasswordReset', null, () {});

  @override
  Future<AuthTokens> refresh(String refreshToken) =>
      _answer('refresh', refreshError, nextTokens);

  @override
  Future<void> logout(String refreshToken) =>
      _answer('logout', logoutError, () {});

  @override
  Future<void> logoutAll() => _answer('logoutAll', null, () {});

  @override
  Future<MeContexts> meContexts() =>
      _answer('meContexts', meContextsError, () => contexts);

  @override
  Future<SessionUser> staffMe() => _answer('staffMe', null, () => staffUser);

  @override
  Future<SessionUser> patientMe(AccountType accountType) => _answer(
    'patientMe',
    null,
    () => SessionUser(
      displayName: 'Test Patient One',
      firstName: 'Test',
      accountType: accountType,
      patient: const PatientProfile(
        id: 101,
        name: 'Test Patient One',
        age: 34,
        gender: 'Female',
        phone: '9000000001',
        phoneVerified: true,
      ),
    ),
  );

  @override
  Future<List<DeviceSessionInfo>> sessions() =>
      _answer('sessions', null, () => devices);

  @override
  Future<void> revokeSession(String sessionId) =>
      _answer('revokeSession:$sessionId', null, () {});
}
