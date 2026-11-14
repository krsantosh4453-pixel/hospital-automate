import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/core/security/token_store.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';

/// Shapes copied from the Django views (users/views.py, sessions_views.py);
/// values are synthetic.
void main() {
  test('AuthTokens reads the pair every sign-in view returns', () {
    final tokens = AuthTokens.fromJson({
      'access': 'a.b.c',
      'refresh': 'd.e.f',
      'user': {},
    });

    expect(tokens.access, 'a.b.c');
    expect(tokens.refresh, 'd.e.f');
    expect(tokens.toString(), isNot(contains('a.b.c')));
    expect(
      () => AuthTokens.fromJson({'access': 'only'}),
      throwsFormatException,
    );
  });

  test('the OTP challenge keeps the masked phone and hides itself', () {
    final challenge = StaffOtpChallenge.fromJson({
      'otp_required': true,
      'message': 'OTP sent to your registered mobile number (******3210).',
      'challenge': 'signed:value',
      'user_id': 3,
      'staff_role': 'Doctor',
    });

    expect(challenge.maskedPhone, '******3210');
    expect(challenge.toString(), isNot(contains('signed:value')));
  });

  test('me/contexts gives hospitals, roles and permissions', () {
    final contexts = MeContexts.fromJson({
      'account_type': 'staff',
      'platform_role': null,
      'contexts': [
        {
          'hospital': {'id': 7, 'name': 'Test General Hospital'},
          'role': 'Receptionist',
          'department': 'Front Office',
          'permissions': ['Patients.View', 'Patients.Add', 'Billing.View'],
          'restricted_modules': {},
        },
      ],
    });

    expect(contexts.accountType, AccountType.staff);
    final hospital = contexts.hospitals.single;
    expect(hospital.id, 7);
    expect(hospital.role, 'Receptionist');
    expect(hospital.permissions, contains('Billing.View'));
  });

  test('platform staff and empty accounts are not supported account types', () {
    expect(
      MeContexts.fromJson({'account_type': 'platform', 'contexts': []})
          .accountType,
      isNull,
    );
    expect(
      MeContexts.fromJson({'account_type': 'proxy', 'contexts': []})
          .accountType,
      AccountType.proxy,
    );
  });

  test('staff/me and patient/me become the signed-in user', () {
    final staff = staffUserFromJson({
      'user': {
        'id': 3,
        'username': 'dr.test',
        'first_name': 'Test',
        'last_name': 'Doctor',
      },
      'roles': ['Doctor'],
      'hospitals': [],
    });
    final patient = patientUserFromJson({
      'patient': {
        'id': 101,
        'name': 'Test Patient One',
        'age': 34,
        'gender': 'Female',
        'phone': '9000000001',
        'email': 'p@example.invalid',
        'email_verified': true,
        'phone_verified': false,
      },
      'user': {'id': 12, 'username': 'p101'},
    }, AccountType.patient);

    expect(staff.displayName, 'Test Doctor');
    expect(staff.isStaff, isTrue);
    expect(patient.isStaff, isFalse);
    expect(patient.firstName, 'Test');
    expect(patient.patient!.emailVerified, isTrue);
  });

  test('sessions list marks this device', () {
    final devices = DeviceSessionInfo.listFromJson({
      'sessions': [
        {
          'id': 'u-1',
          'platform': 'android',
          'current': true,
          'last_used_at': '2026-11-11T08:00:00Z',
        },
        {'id': 'u-2', 'platform': 'web', 'current': false},
      ],
    });

    expect(devices.map((d) => d.current), [true, false]);
    expect(devices.first.lastUsedAt, DateTime.utc(2026, 11, 11, 8));
  });

  test(
    'a registration body carries only the documented fields and hides itself',
    () {
      const registration = PatientRegistration(
        fullName: 'Test Patient',
        email: 'p@example.invalid',
        phone: '9000000001',
        password: 'longpassword',
        confirmPassword: 'longpassword',
        gender: 'Female',
      );

      expect(registration.toJson().keys, [
        'role',
        'full_name',
        'email',
        'phone',
        'password',
        'confirm_password',
        'gender',
      ]);
      expect(registration.toJson()['role'], 'Patient');
      expect(registration.toString(), isNot(contains('longpassword')));
    },
  );
}
