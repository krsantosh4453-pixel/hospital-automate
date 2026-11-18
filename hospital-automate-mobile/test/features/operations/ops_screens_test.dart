import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/localization/locale_controller.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/routing/app_router.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/emergency/data/emergency_models.dart';
import 'package:hms_mobile/features/hospital/data/hospital_models.dart';
import 'package:hms_mobile/features/ipd/data/ipd_models.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_hi.dart';
import 'package:hms_mobile/shared/widgets/hms_button.dart';

import '../../support/test_app.dart';

// Synthetic data only: no real patients, staff or hospitals.

final t = AppLocalizationsEn();

const nursePermissions = {
  'Dashboard.View',
  'Patients.View',
  'Emergency.View',
  'Emergency.Add',
  'Emergency.Edit',
  'IPD.View',
  'IPD.Edit',
};

const managerPermissions = {
  'Dashboard.View',
  'Emergency.View',
  'IPD.View',
  'Users.View',
  'Hospitals.View',
  'Departments.View',
  'Departments.Add',
};

SessionState session(String role, Set<String> permissions) =>
    staffSession(role: role, permissions: permissions);

const _validationRefusal = ApiException(
  kind: ApiErrorKind.validation,
  statusCode: 400,
);

EmergencyVisit erVisit(
  int id,
  String name, {
  String status = ErStatus.waiting,
  String level = 'Urgent',
  int minute = 0,
}) => EmergencyVisit(
  id: id,
  status: status,
  triageLevel: level,
  patientName: name,
  visitNumber: 'ER-$id',
  arrivalTime: DateTime.utc(2026, 11, 15, 9, minute),
);

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> pickDropdown(WidgetTester tester, Key key, String item) async {
  await tapVisible(tester, find.byKey(key));
  await tester.tap(find.text(item).last);
  await tester.pumpAndSettle();
}

VoidCallback? onPressedOf(WidgetTester tester, Key key) =>
    tester.widget<HmsButton>(find.byKey(key)).onPressed;

void main() {
  group('Emergency', () {
    testWidgets('board lists active visits, most urgent first, with counts', (
      tester,
    ) async {
      final repo = FakeEmergencyRepository(
        visitList: [
          erVisit(1, 'Patient Low', level: 'Non-Urgent'),
          erVisit(2, 'Patient Critical', level: 'Critical', minute: 20),
          erVisit(3, 'Patient Done', status: ErStatus.discharged),
        ],
        board: const ErDashboard(
          statusCounts: {'Waiting': 2, 'Discharged': 1},
          triageCounts: {},
          totalActive: 2,
        ),
      );
      await pumpApp(
        tester,
        testServices(
          session: session('Nurse', nursePermissions),
          emergency: repo,
        ),
        location: '/emergency',
      );

      expect(find.text(t.erActiveNow), findsOneWidget);
      expect(find.text('Patient Done'), findsNothing);
      final critical = tester.getTopLeft(find.text('Patient Critical')).dy;
      final low = tester.getTopLeft(find.text('Patient Low')).dy;
      expect(critical, lessThan(low));
      expect(find.byKey(const Key('er-register')), findsOneWidget);

      await tapVisible(tester, find.text(t.erFilterClosed));
      expect(find.text('Patient Done'), findsOneWidget);
      expect(find.text('Patient Low'), findsNothing);
    });

    testWidgets('a manager sees the board read-only', (tester) async {
      final repo = FakeEmergencyRepository(
        visitList: [erVisit(1, 'Patient A')],
      );
      await pumpApp(
        tester,
        testServices(
          session: session('Hospital Manager', managerPermissions),
          emergency: repo,
        ),
        location: '/emergency/1',
      );
      expect(find.text(t.erReadOnly), findsOneWidget);
      expect(
        find.byKey(const ValueKey('er-action-startConsultation')),
        findsNothing,
      );
      expect(find.byKey(const Key('er-add-note')), findsNothing);
    });

    test('a receptionist is kept off the emergency pages', () {
      final receptionist = session('Receptionist', {
        'Dashboard.View',
        'Patients.View',
      });
      expect(redirectFor(receptionist, '/emergency'), startsWith('/?denied='));
      expect(redirectFor(receptionist, '/ipd/3'), startsWith('/?denied='));
    });

    testWidgets('registration is confirmed only after the server accepts it', (
      tester,
    ) async {
      final repo = FakeEmergencyRepository(
        patients: const [
          PatientSummary(id: 41, name: 'Test Patient', uhid: 'TGH-1'),
        ],
      );
      await pumpApp(
        tester,
        testServices(
          session: session('Nurse', nursePermissions),
          emergency: repo,
        ),
        location: '/emergency',
      );
      await tapVisible(tester, find.byKey(const Key('er-register')));
      await tester.enterText(find.byType(TextField).first, 'Test');
      await tapVisible(tester, find.text(t.opsSearch));
      await tapVisible(tester, find.byKey(const ValueKey('er-patient-41')));

      final register = find.widgetWithText(HmsButton, t.erRegister);
      expect(tester.widget<HmsButton>(register).onPressed, isNull);
      await pickDropdown(
        tester,
        const Key('er-triage-level'),
        t.triageCritical,
      );
      await tapVisible(tester, register);

      expect(repo.registrations.single, {
        'patient': 41,
        'triage_level': 'Critical',
        'remarks': '',
      });
      expect(find.text(t.erRegistered), findsOneWidget);
    });

    testWidgets('a refused registration keeps the sheet open with the reason', (
      tester,
    ) async {
      final repo = FakeEmergencyRepository(
        patients: const [PatientSummary(id: 41, name: 'Test Patient')],
      )..failWith = _validationRefusal;
      await pumpApp(
        tester,
        testServices(
          session: session('Nurse', nursePermissions),
          emergency: repo,
        ),
        location: '/emergency',
      );
      await tapVisible(tester, find.byKey(const Key('er-register')));
      await tester.enterText(find.byType(TextField).first, 'Test');
      await tapVisible(tester, find.text(t.opsSearch));
      await tapVisible(tester, find.byKey(const ValueKey('er-patient-41')));
      await pickDropdown(tester, const Key('er-triage-level'), t.triageUrgent);
      await tapVisible(tester, find.widgetWithText(HmsButton, t.erRegister));

      expect(find.text(t.opsStepRefused), findsOneWidget);
      expect(find.text(t.erRegistered), findsNothing);
      expect(repo.registrations, isEmpty);
    });

    testWidgets('start triage moves the visit after confirmation', (
      tester,
    ) async {
      final repo = FakeEmergencyRepository(
        visitList: [erVisit(5, 'Patient Five', status: ErStatus.registered)],
      );
      await pumpApp(
        tester,
        testServices(
          session: session('Nurse', nursePermissions),
          emergency: repo,
        ),
        location: '/emergency/5',
      );
      expect(
        find.byKey(const ValueKey('er-action-completeTriage')),
        findsNothing,
      );
      await tapVisible(
        tester,
        find.byKey(const ValueKey('er-action-startTriage')),
      );
      await tester.tap(find.text(t.erStartTriage).last);
      await tester.pumpAndSettle();

      expect(repo.calls, ['start_triage:5']);
      expect(find.text(t.erStatusTriage), findsOneWidget);
      expect(
        find.byKey(const ValueKey('er-action-completeTriage')),
        findsOneWidget,
      );
    });

    testWidgets('a closed visit offers only notes', (tester) async {
      final repo = FakeEmergencyRepository(
        visitList: [erVisit(6, 'Patient Six', status: ErStatus.discharged)],
      );
      await pumpApp(
        tester,
        testServices(
          session: session('Doctor', nursePermissions),
          emergency: repo,
        ),
        location: '/emergency/6',
      );
      expect(find.text(t.erVisitClosed), findsOneWidget);
      for (final action in ErAction.values) {
        expect(find.byKey(ValueKey('er-action-${action.name}')), findsNothing);
      }
      expect(find.byKey(const Key('er-add-note')), findsOneWidget);
    });

    testWidgets('a network failure shows an error with retry, not data', (
      tester,
    ) async {
      final repo = FakeEmergencyRepository()
        ..loadError = const ApiException(kind: ApiErrorKind.network);
      await pumpApp(
        tester,
        testServices(
          session: session('Nurse', nursePermissions),
          emergency: repo,
        ),
        location: '/emergency',
      );
      expect(find.text(t.errorNetwork), findsWidgets);
      expect(find.text(t.tryAgain), findsWidgets);
    });

    testWidgets('the page is translated into Hindi', (tester) async {
      await pumpApp(
        tester,
        testServices(
          session: session('Nurse', nursePermissions),
          language: AppLanguage.hi,
        ),
        location: '/emergency',
      );
      expect(find.text(AppLocalizationsHi().erIntro), findsOneWidget);
      expect(find.text(t.erIntro), findsNothing);
    });
  });

  group('IPD', () {
    const bed = BedAllocationRecord(
      id: 9,
      bedId: 21,
      isActive: true,
      place: BedPlace(ward: 'General', room: 'G1', bed: 'G1-2'),
    );

    testWidgets('lists stays in hospital and the bed board', (tester) async {
      final repo = FakeIpdRepository(
        admissionList: const [
          IpdAdmission(
            id: 1,
            status: AdmissionStatus.admitted,
            patientName: 'In Bed',
            currentBed: bed,
          ),
          IpdAdmission(
            id: 2,
            status: AdmissionStatus.admitted,
            patientName: 'No Bed Yet',
          ),
          IpdAdmission(
            id: 3,
            status: AdmissionStatus.discharged,
            patientName: 'Gone Home',
          ),
        ],
        overviewData: const IpdOverview(
          admitted: 2,
          dischargeInitiated: 0,
          discharged: 1,
          availableBeds: 4,
        ),
        board: const BedBoard(
          complete: false,
          beds: [
            HospitalBed(
              id: 21,
              status: BedStatus.occupied,
              currentPatient: 'In Bed',
              place: BedPlace(ward: 'General', room: 'G1', bed: 'G1-2'),
            ),
            HospitalBed(
              id: 22,
              status: BedStatus.available,
              place: BedPlace(ward: 'General', room: 'G1', bed: 'G1-3'),
            ),
          ],
        ),
      );
      await pumpApp(
        tester,
        testServices(session: session('Nurse', nursePermissions), ipd: repo),
        location: '/ipd',
      );
      expect(repo.overviewHospitals, [7]);
      expect(find.text('In Bed'), findsOneWidget);
      expect(find.textContaining(t.ipdAwaitingBed), findsOneWidget);
      expect(find.text('Gone Home'), findsNothing);

      await tapVisible(tester, find.text(t.ipdTabBeds));
      expect(find.text(t.ipdBedsPartial(2)), findsOneWidget);
      expect(find.byKey(const ValueKey('bed-22')), findsOneWidget);
      expect(find.text('${t.bedAvailable}: 1'), findsOneWidget);
    });

    testWidgets('complete discharge stays off until the server says ready', (
      tester,
    ) async {
      final repo = FakeIpdRepository(
        admissionList: const [
          IpdAdmission(
            id: 3,
            status: AdmissionStatus.dischargeInitiated,
            patientName: 'Leaving',
            currentBed: bed,
          ),
        ],
        readinessData: const DischargeReadiness(ready: false, hasPlan: true),
      );
      await pumpApp(
        tester,
        testServices(session: session('Nurse', nursePermissions), ipd: repo),
        location: '/ipd/3',
      );
      expect(onPressedOf(tester, const Key('ipd-complete-discharge')), isNull);
      expect(find.textContaining(t.ipdNoFinalBill), findsWidgets);
      expect(repo.calls, isEmpty);
    });

    testWidgets('a ready discharge completes after confirmation', (
      tester,
    ) async {
      final repo = FakeIpdRepository(
        admissionList: const [
          IpdAdmission(
            id: 3,
            status: AdmissionStatus.dischargeInitiated,
            patientName: 'Leaving',
            currentBed: bed,
          ),
        ],
        readinessData: const DischargeReadiness(
          ready: true,
          hasPlan: true,
          summaryFinalized: true,
          finalBill: FinalBill(id: 1, balanceDue: 0, total: 1000),
        ),
      );
      await pumpApp(
        tester,
        testServices(session: session('Nurse', nursePermissions), ipd: repo),
        location: '/ipd/3',
      );
      await tapVisible(tester, find.byKey(const Key('ipd-complete-discharge')));
      await tester.tap(find.text(t.ipdCompleteDischarge).last);
      await tester.pumpAndSettle();
      expect(repo.calls, ['complete_discharge:3']);
      expect(find.text(t.ipdDischargeDone), findsOneWidget);
    });

    testWidgets('a bed is allocated from the free beds the server lists', (
      tester,
    ) async {
      final repo = FakeIpdRepository(
        admissionList: const [
          IpdAdmission(
            id: 4,
            status: AdmissionStatus.admitted,
            patientName: 'Needs Bed',
          ),
        ],
        free: const [
          AvailableBed(
            id: 31,
            place: BedPlace(ward: 'General', room: 'G2', bed: 'G2-1'),
          ),
        ],
      );
      await pumpApp(
        tester,
        testServices(session: session('Nurse', nursePermissions), ipd: repo),
        location: '/ipd/4',
      );
      await tapVisible(tester, find.byKey(const Key('ipd-move-bed')));
      expect(onPressedOf(tester, const Key('ipd-save-bed')), isNull);
      await tapVisible(tester, find.byKey(const ValueKey('free-bed-31')));
      await tapVisible(tester, find.byKey(const Key('ipd-save-bed')));
      expect(repo.calls, ['available_beds:7', 'allocate_bed:4:31']);
      expect(find.text(t.ipdBedSaved), findsOneWidget);
    });

    testWidgets('a bed taken meanwhile is refused and the list reloads', (
      tester,
    ) async {
      final repo = FakeIpdRepository(
        admissionList: const [
          IpdAdmission(
            id: 4,
            status: AdmissionStatus.admitted,
            patientName: 'Needs Bed',
          ),
        ],
        free: const [
          AvailableBed(
            id: 31,
            place: BedPlace(ward: 'General', room: 'G2', bed: 'G2-1'),
          ),
        ],
      )..failWith = _validationRefusal;
      await pumpApp(
        tester,
        testServices(session: session('Nurse', nursePermissions), ipd: repo),
        location: '/ipd/4',
      );
      await tapVisible(tester, find.byKey(const Key('ipd-move-bed')));
      await tapVisible(tester, find.byKey(const ValueKey('free-bed-31')));
      await tapVisible(tester, find.byKey(const Key('ipd-save-bed')));
      expect(find.text(t.ipdBedTaken), findsOneWidget);
      expect(
        repo.calls.where((c) => c.startsWith('available_beds')),
        hasLength(2),
      );
      expect(find.text(t.ipdBedSaved), findsNothing);
    });

    testWidgets('a nurse is told summaries are for doctors and managers', (
      tester,
    ) async {
      final repo =
          FakeIpdRepository(
              admissionList: const [
                IpdAdmission(
                  id: 3,
                  status: AdmissionStatus.admitted,
                  patientName: 'P',
                ),
              ],
            )
            ..summaryError = const ApiException(
              kind: ApiErrorKind.forbidden,
              statusCode: 403,
            );
      await pumpApp(
        tester,
        testServices(session: session('Nurse', nursePermissions), ipd: repo),
        location: '/ipd/3',
      );
      expect(find.text(t.ipdSummaryDoctorsOnly), findsOneWidget);
    });

    testWidgets('a manager cannot move beds or discharge', (tester) async {
      final repo = FakeIpdRepository(
        admissionList: const [
          IpdAdmission(
            id: 4,
            status: AdmissionStatus.admitted,
            patientName: 'P',
          ),
        ],
      );
      await pumpApp(
        tester,
        testServices(
          session: session('Hospital Manager', managerPermissions),
          ipd: repo,
        ),
        location: '/ipd/4',
      );
      expect(find.text(t.ipdReadOnly), findsOneWidget);
      expect(find.byKey(const Key('ipd-move-bed')), findsNothing);
      expect(onPressedOf(tester, const Key('ipd-initiate-discharge')), isNull);
    });
  });

  group('Hospital', () {
    SessionState twoHospitals() => const SessionState(
      user: SessionUser(displayName: 'manager.test'),
      hospitals: [
        HospitalContext(
          id: 7,
          name: 'Test General Hospital',
          role: 'Hospital Manager',
          permissions: managerPermissions,
        ),
        HospitalContext(
          id: 8,
          name: 'Test City Clinic',
          role: 'Hospital Manager',
          permissions: managerPermissions,
        ),
      ],
      activeHospitalId: 7,
    );

    testWidgets('switching hospital reloads the page for the new hospital', (
      tester,
    ) async {
      final repo = FakeHospitalRepository(
        info: const {
          7: HospitalInfo(id: 7, name: 'Test General Hospital', departments: 3),
          8: HospitalInfo(id: 8, name: 'Test City Clinic', departments: 1),
        },
        wardList: const [
          Ward(id: 1, name: 'General Ward', wardType: 'General'),
        ],
      );
      final services = testServices(session: twoHospitals(), hospital: repo);
      await pumpApp(tester, services, location: '/admin/hospitals');
      expect(find.text('General Ward'), findsOneWidget);
      expect(find.text(t.hospCurrent), findsOneWidget);

      await tapVisible(tester, find.text(t.hospSwitch));
      expect(services.session.activeHospitalId, 8);
      expect(repo.requestedHospitals, [7, 8]);
      expect(find.text('3'), findsNothing);
    });

    testWidgets('departments are listed', (tester) async {
      final repo = FakeHospitalRepository(
        departmentList: const [
          Department(
            id: 2,
            name: 'Cardiology',
            headName: 'Dr Test',
            doctors: 4,
          ),
        ],
      );
      await pumpApp(
        tester,
        testServices(
          session: session('Hospital Manager', managerPermissions),
          hospital: repo,
        ),
        location: '/admin/departments',
      );
      expect(find.text('Cardiology'), findsOneWidget);
      expect(find.text('Dr Test'), findsOneWidget);
    });

    testWidgets('staff list shows roles and departments', (tester) async {
      final repo = FakeHospitalRepository(
        departmentList: const [Department(id: 2, name: 'Cardiology')],
        staffList: const [
          StaffMember(
            userId: 5,
            name: 'Test Nurse',
            role: 'Nurse',
            departmentId: 2,
            membershipActive: true,
          ),
          StaffMember(
            userId: 6,
            name: 'Test Invitee',
            role: 'Doctor',
            invitePending: true,
          ),
        ],
      );
      await pumpApp(
        tester,
        testServices(
          session: session('Hospital Manager', managerPermissions),
          hospital: repo,
        ),
        location: '/admin/users',
      );
      expect(find.text('Nurse · Cardiology'), findsOneWidget);
      expect(find.text(t.staffInvitePending), findsOneWidget);
    });

    testWidgets('a 403 on the staff list is explained, not shown as data', (
      tester,
    ) async {
      final repo = FakeHospitalRepository()
        ..staffError = const ApiException(
          kind: ApiErrorKind.forbidden,
          statusCode: 403,
        );
      await pumpApp(
        tester,
        testServices(
          session: session('Hospital Manager', managerPermissions),
          hospital: repo,
        ),
        location: '/admin/users',
      );
      expect(find.text(t.staffManagersOnly), findsOneWidget);
    });
  });
}
