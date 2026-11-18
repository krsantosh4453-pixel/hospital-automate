import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/emergency/data/emergency_models.dart';
import 'package:hms_mobile/features/emergency/data/emergency_repository.dart';
import 'package:hms_mobile/features/ipd/data/ipd_models.dart';
import 'package:hms_mobile/features/ipd/data/ipd_repository.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';
import 'package:hms_mobile/shared/widgets/hms_button.dart';

import '../../support/test_app.dart';

// Synthetic data only: no real patients, staff or hospitals.

final t = AppLocalizationsEn();

const _permissions = {
  'Dashboard.View',
  'Patients.View',
  'Emergency.View',
  'Emergency.Add',
  'Emergency.Edit',
  'IPD.View',
  'IPD.Edit',
};

SessionState _staff(String role) => SessionState(
  user: const SessionUser(id: 90, displayName: 'staff.test'),
  hospitals: [
    HospitalContext(
      id: 7,
      name: 'Test General Hospital',
      role: role,
      permissions: _permissions,
    ),
  ],
  activeHospitalId: 7,
);

EmergencyVisit _visit(String status) => EmergencyVisit(
  id: 5,
  status: status,
  triageLevel: 'Urgent',
  patientId: 41,
  patientName: 'Patient Five',
  visitNumber: 'ER-5',
);

const _freeBed = AvailableBed(
  id: 31,
  place: BedPlace(ward: 'General', room: 'G2', bed: 'G2-1'),
);

({ApiClient api, FakeAdapter adapter}) _client(Map<String, Object?> routes) {
  final adapter = FakeAdapter((options) async {
    final key = '${options.method} ${options.uri.path}';
    return jsonBody(
      jsonEncode(routes[key] ?? {'detail': 'x'}),
      routes.containsKey(key) ? 200 : 404,
    );
  });
  return (
    api: ApiClient(
      config: testConfig,
      accessToken: () async => 'token',
      hospitalId: () => 7,
      adapter: adapter,
      log: (_) {},
    ),
    adapter: adapter,
  );
}

Future<void> _tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> _type(WidgetTester tester, String key, String text) async {
  final field = find.descendant(
    of: find.byKey(ValueKey('er-vital-$key')),
    matching: find.byType(TextField),
  );
  await tester.ensureVisible(field);
  await tester.enterText(field, text);
  await tester.pump();
}

void main() {
  group('vitals format', () {
    test('whole-number fields refuse decimals and negatives', () {
      expect(checkVital(ErVitalField.systolic, '120'), isNull);
      expect(
        checkVital(ErVitalField.systolic, '120.5'),
        VitalInputError.notWhole,
      );
      expect(checkVital(ErVitalField.spo2, '-1'), VitalInputError.negative);
      expect(checkVital(ErVitalField.spo2, 'abc'), VitalInputError.notANumber);
    });

    test('decimal fields keep the column precision', () {
      expect(checkVital(ErVitalField.temperature, '37.25'), isNull);
      expect(
        checkVital(ErVitalField.temperature, '37.255'),
        VitalInputError.tooPrecise,
      );
      // temperature is 5 digits with 2 decimals: at most 3 before the point.
      expect(
        checkVital(ErVitalField.temperature, '1000'),
        VitalInputError.tooLong,
      );
      expect(checkVital(ErVitalField.bloodSugar, '9999.99'), isNull);
    });

    test('the body carries only entered fields, as numbers', () {
      expect(
        vitalsBody({
          ErVitalField.systolic: '120',
          ErVitalField.temperature: ' 37.2 ',
          ErVitalField.spo2: '',
        }, recordedBy: 5),
        {'systolic_bp': 120, 'temperature': '37.2', 'recorded_by': 5},
      );
    });
  });

  group('repository', () {
    test('add_vitals and admit_to_ipd post to the visit actions', () async {
      const base = '/api/v1/emergency/emergency-visits/5';
      final c = _client({
        'POST $base/add_vitals/': {'id': 1, 'spo2': 97},
        'POST $base/admit_to_ipd/': {
          'detail': 'Patient admitted to IPD',
          'admission': {'id': 9, 'patient': 'P', 'bed': 'General - G2 - G2-1'},
        },
      });
      final repo = ApiEmergencyRepository(c.api);
      final vitals = await repo.addVitals(5, {ErVitalField.spo2: '97'});
      final admission = await repo.admitToIpd(5, bedId: 31);
      expect(vitals.spo2, 97);
      expect(c.adapter.requests[0].data, {'spo2': 97});
      expect(c.adapter.requests[1].data, {'bed_id': 31});
      expect(admission.admissionId, 9);
      expect(admission.bed, 'General - G2 - G2-1');
    });

    test('admissions of one patient are asked for by ?patient=', () async {
      final c = _client({
        'GET /api/v1/ipd/admissions/': {'next': null, 'results': <Object>[]},
      });
      await ApiIpdRepository(c.api).admissions(patientId: 41);
      expect(c.adapter.requests.single.queryParameters['patient'], 41);
    });
  });

  group('screens', () {
    testWidgets(
      'admission is offered only from the statuses the server allows',
      (tester) async {
        for (final status in [ErStatus.waiting, ErStatus.discharged]) {
          await pumpApp(
            tester,
            testServices(
              session: _staff('Doctor'),
              emergency: FakeEmergencyRepository(visitList: [_visit(status)]),
            ),
            location: '/emergency/5',
          );
          expect(
            find.byKey(const Key('er-admit')),
            findsNothing,
            reason: status,
          );
        }
        await pumpApp(
          tester,
          testServices(
            session: _staff('Doctor'),
            emergency: FakeEmergencyRepository(
              visitList: [_visit(ErStatus.underConsultation)],
            ),
          ),
          location: '/emergency/5',
        );
        expect(find.byKey(const Key('er-admit')), findsOneWidget);
      },
    );

    testWidgets('a closed visit takes no vitals', (tester) async {
      await pumpApp(
        tester,
        testServices(
          session: _staff('Nurse'),
          emergency: FakeEmergencyRepository(
            visitList: [_visit(ErStatus.referred)],
          ),
        ),
        location: '/emergency/5',
      );
      expect(find.byKey(const Key('er-record-vitals')), findsNothing);
    });

    testWidgets(
      'bad vitals are refused on the phone; good ones are sent under the nurse',
      (tester) async {
        final repo = FakeEmergencyRepository(
          visitList: [_visit(ErStatus.waiting)],
        );
        await pumpApp(
          tester,
          testServices(session: _staff('Nurse'), emergency: repo),
          location: '/emergency/5',
        );
        await _tapVisible(tester, find.byKey(const Key('er-record-vitals')));
        final save = find.widgetWithText(HmsButton, t.saveVitals);

        await _tapVisible(tester, save);
        expect(find.text(t.erVitalsEmpty), findsOneWidget);

        await _type(tester, 'systolic_bp', '120.5');
        await _tapVisible(tester, save);
        expect(find.text(t.vitalWholeNumber), findsOneWidget);
        expect(repo.vitalsSent, isEmpty);

        await _type(tester, 'systolic_bp', '120');
        await _type(tester, 'temperature', '37.2');
        await _tapVisible(tester, save);
        expect(repo.vitalsSent.single, {
          'systolic_bp': 120,
          'temperature': '37.2',
          'recorded_by': FakeNursingRepository.testNurse.id,
        });
        expect(find.text(t.vitalsSaved), findsOneWidget);
      },
    );

    testWidgets('admitting warns of an open stay, then links to the new one', (
      tester,
    ) async {
      final er = FakeEmergencyRepository(
        visitList: [_visit(ErStatus.underConsultation)],
      );
      final ipd = FakeIpdRepository(
        free: const [_freeBed],
        admissionList: const [
          IpdAdmission(
            id: 3,
            status: AdmissionStatus.admitted,
            patientId: 41,
            patientName: 'Patient Five',
          ),
          IpdAdmission(
            id: 77,
            status: AdmissionStatus.admitted,
            patientId: 99,
            patientName: 'Someone Else',
          ),
        ],
      );
      await pumpApp(
        tester,
        testServices(session: _staff('Doctor'), emergency: er, ipd: ipd),
        location: '/emergency/5',
      );
      await _tapVisible(tester, find.byKey(const Key('er-admit')));
      expect(find.text(t.erAlreadyAdmitted), findsOneWidget);

      final admit = find.widgetWithText(HmsButton, t.erAdmitToIpd).last;
      expect(tester.widget<HmsButton>(admit).onPressed, isNull);
      await _tapVisible(tester, find.byKey(const ValueKey('admit-bed-31')));
      await _tapVisible(tester, admit);

      expect(er.calls, ['admit_to_ipd:5:31']);
      expect(find.text(t.erAdmitted), findsOneWidget);
      await _tapVisible(tester, find.byKey(const Key('er-open-admission')));
      expect(find.text('Someone Else'), findsOneWidget);
    });

    testWidgets('a refused admission keeps the sheet open and reloads beds', (
      tester,
    ) async {
      final er = FakeEmergencyRepository(
        visitList: [_visit(ErStatus.underConsultation)],
      )..failWith = const ApiException(kind: ApiErrorKind.validation);
      final ipd = FakeIpdRepository(free: const [_freeBed]);
      await pumpApp(
        tester,
        testServices(session: _staff('Doctor'), emergency: er, ipd: ipd),
        location: '/emergency/5',
      );
      await _tapVisible(tester, find.byKey(const Key('er-admit')));
      await _tapVisible(tester, find.byKey(const ValueKey('admit-bed-31')));
      await _tapVisible(
        tester,
        find.widgetWithText(HmsButton, t.erAdmitToIpd).last,
      );
      expect(find.text(t.opsStepRefused), findsOneWidget);
      expect(find.text(t.erAdmitted), findsNothing);
      expect(
        ipd.calls.where((c) => c.startsWith('available_beds')),
        hasLength(2),
      );
    });
  });
}
