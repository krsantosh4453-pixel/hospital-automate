import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/routing/app_router.dart';
import 'package:hms_mobile/core/security/session_controller.dart';

import '../../support/test_app.dart';

void main() {
  final receptionist = staffSession(
    role: 'Receptionist',
    permissions: {'Dashboard.View', 'Patients.View', 'Queue.View'},
  );
  const patient = SessionState(
    user: SessionUser(
      displayName: 'Test Patient',
      accountType: AccountType.patient,
    ),
    hospitals: [
      HospitalContext(id: 7, name: 'Test General Hospital', role: 'Patient'),
    ],
    activeHospitalId: 7,
  );

  test('visitors keep the web behaviour: staff pages ask to sign in, patient pages redirect', () {
    expect(redirectFor(SessionState.signedOut, '/patients'), isNull);
    expect(
      redirectFor(SessionState.signedOut, '/patient/bills'),
      '/patient-login',
    );
    expect(redirectFor(SessionState.signedOut, '/staff-login'), isNull);
  });

  test('signed-in people never see the sign-in pages', () {
    expect(redirectFor(receptionist, '/staff-login'), '/');
    expect(redirectFor(patient, '/register'), '/');
  });

  test('staff open what their role may view and are turned back elsewhere', () {
    expect(redirectFor(receptionist, '/patients'), isNull);
    expect(redirectFor(receptionist, '/queue'), isNull);
    expect(redirectFor(receptionist, '/laboratory'), '/?denied=%2Flaboratory');
    expect(
      redirectFor(receptionist, '/admin'),
      '/?denied=%2Fadmin',
      reason: 'Administration needs an admin module',
    );
    expect(redirectFor(receptionist, '/patient/bills'), '/');
  });

  test('an admin opens Administration', () {
    expect(redirectFor(staffSession(), '/admin/users'), isNull);
  });

  test('patients see Home, Settings and their own pages only', () {
    expect(redirectFor(patient, '/'), isNull);
    expect(redirectFor(patient, '/settings'), isNull);
    expect(redirectFor(patient, '/patient/prescriptions'), isNull);
    expect(redirectFor(patient, '/patients'), '/');
    expect(redirectFor(patient, '/admin'), '/');
  });
}
