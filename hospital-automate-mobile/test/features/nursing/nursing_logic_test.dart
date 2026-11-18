import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/doctor/data/doctor_repository.dart';
import 'package:hms_mobile/features/nursing/data/nursing_models.dart';
import 'package:hms_mobile/features/nursing/data/nursing_repository.dart';
import 'package:hms_mobile/features/nursing/ui/nursing_ui.dart';
import 'package:hms_mobile/features/nursing/ui/ward_care_sections.dart';
import 'package:hms_mobile/features/nursing/ui/ward_patients_screen.dart';
import 'package:hms_mobile/features/nursing/ui/ward_vitals_section.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';

import '../../support/test_app.dart';

({ApiNursingRepository repo, FakeAdapter adapter}) nursingRepo(
  Map<String, (Object, int)> routes,
) {
  final adapter = FakeAdapter((options) async {
    final answer = routes['${options.method} ${options.uri.path}'];
    if (answer == null) return jsonBody('{"detail":"Not found."}', 404);
    return jsonBody(jsonEncode(answer.$1), answer.$2);
  });
  final api = ApiClient(
    config: testConfig,
    accessToken: () async => 'nurse-token',
    hospitalId: () => 7,
    adapter: adapter,
    log: (_) {},
  );
  return (
    repo: ApiNursingRepository(api, ApiDoctorRepository(api)),
    adapter: adapter,
  );
}

Map<String, Object?> page(List<Map<String, Object?>> rows) => {
  'count': rows.length,
  'next': null,
  'results': rows,
};

const base = '/api/v1/';

RequestOptions only(FakeAdapter adapter) => adapter.requests.single;

void main() {
  final t = AppLocalizationsEn();

  group('models read the serializers', () {
    test('admission reads its current bed', () {
      final a = Admission.fromJson({
        'id': 3,
        'patient': 11,
        'patient_name': 'Test Ward Patient',
        'status': 'Admitted',
        'admitting_doctor_name': 'Dr Test',
        'current_bed': {
          'ward_name': 'Ward A',
          'room_number': '2',
          'bed_number': 'B4',
        },
      });
      expect(a.inWard, isTrue);
      expect(a.awaitingBed, isFalse);
      expect([a.wardName, a.roomNumber, a.bedNumber], ['Ward A', '2', 'B4']);
    });

    test('an admission with no bed is awaiting one; discharged is not in ward',
        () {
      expect(
        Admission.fromJson({'id': 1, 'status': 'Admitted'}).awaitingBed,
        isTrue,
      );
      expect(
        Admission.fromJson({'id': 1, 'status': 'Discharged'}).inWard,
        isFalse,
      );
    });

    test('a dose keeps the doctor\'s dose, route and the server flags', () {
      final d = Dose.fromJson({
        'id': 9,
        'mar': 2,
        'status': 'Scheduled',
        'medicine_name': 'Synthetic Paracetamol',
        'dose': '500 mg',
        'route': 'Oral',
        'scheduled_time': '2026-11-15T08:00:00Z',
        'is_delayed': true,
      });
      expect(d.isDue, isTrue);
      expect(d.isDelayed, isTrue);
      expect([d.dose, d.route, d.orderId], ['500 mg', 'Oral', 2]);
    });

    test('a medication order nests its doses', () {
      final o = MedicationOrder.fromJson({
        'id': 2,
        'medicine_name': 'Synthetic Paracetamol',
        'is_active': true,
        'administrations': [
          {'id': 9, 'status': 'Scheduled', 'medicine_name': 'X'},
          {'id': 10, 'status': 'Administered', 'medicine_name': 'X'},
        ],
      });
      expect(o.doses.map((d) => d.isDue), [true, false]);
    });

    test('an assessment keeps its vitals JSON as recorded', () {
      final a = NursingAssessment.fromJson({
        'id': 1,
        'assessment_type': 'Focused',
        'vitals': {'bp': '120/80', 'pulse': '', 'spo2': 98},
      });
      expect(a.vitals, {'bp': '120/80', 'spo2': '98'});
      expect(a.hasVitals, isTrue);
    });
  });

  group('ward vitals use the web keys', () {
    test('blood pressure is joined, other values keep the web names', () {
      expect(
        wardVitalsJson({
          VitalField.systolicBp: '120',
          VitalField.diastolicBp: '80',
          VitalField.heartRate: '72',
          VitalField.spo2: '98',
          VitalField.temperature: '36.8',
          VitalField.respiratoryRate: '16',
        }),
        {
          'bp': '120/80',
          'pulse': '72',
          'respiratory_rate': '16',
          'temperature': '36.8',
          'spo2': '98',
        },
      );
    });

    test('half a blood pressure is refused', () {
      expect(wardVitalsJson({VitalField.systolicBp: '120'}), isNull);
    });

    test('checkVitals applies server limits, blood pressure pairs and empties',
        () {
      const stay = AdmissionTarget(Admission(id: 1, status: 'Admitted'));
      final over = checkVitals(stay, {VitalField.spo2: '101'});
      expect(over.fields[VitalField.spo2], VitalError.tooHigh);
      expect(checkVitals(stay, {VitalField.diastolicBp: '80'}).bpIncomplete,
          isTrue);
      expect(checkVitals(stay, {}).empty, isTrue);
      final ok = checkVitals(stay, {VitalField.heartRate: '72'});
      expect([ok.fields.isEmpty, ok.bpIncomplete, ok.empty], [true, false, false]);
    });

    test('a stay offers only the web fields; a visit offers all', () {
      const stay = AdmissionTarget(Admission(id: 1, status: 'Admitted'));
      const visit = VisitTarget(Visit(id: 2, status: 'Waiting'));
      expect(stay.fields, isNot(contains(VitalField.weight)));
      expect(visit.fields, VitalField.values);
    });
  });

  group('ward list', () {
    const stay = Admission(
      id: 1,
      status: 'Admitted',
      patientId: 11,
      patientName: 'Zed Test',
      wardName: 'Ward A',
      bedNumber: 'B4',
    );
    const waiting = Admission(
      id: 2,
      status: 'Admitted',
      patientId: 12,
      patientName: 'Amy Test',
    );
    const gone = Admission(
      id: 3,
      status: 'Discharged',
      patientId: 13,
      patientName: 'Old Test',
    );
    const duty = DutyAssignment(
      id: 1,
      shift: 'Morning',
      patientId: 11,
      patientName: 'Zed Test',
    );

    test('merges stays and assignments, one row per patient, by name', () {
      final rows = wardPatients([stay, waiting, gone], [duty]);
      expect(rows.map((r) => r.name), ['Amy Test', 'Zed Test']);
      expect(rows.last.assignedShift, 'Morning');
      expect(rows.last.admission?.bedNumber, 'B4');
    });

    test('filters and search match what the server sent', () {
      final rows = wardPatients([stay, waiting], [duty]);
      expect(
        rows.where((r) => matchesWardFilter(r, WardFilter.awaitingBed)).map((r) => r.name),
        ['Amy Test'],
      );
      expect(
        rows.where((r) => matchesWardFilter(r, WardFilter.assigned)).map((r) => r.name),
        ['Zed Test'],
      );
      expect(rows.where((r) => matchesWardSearch(r, 'b4')).length, 1);
      expect(rows.where((r) => matchesWardSearch(r, 'ward a')).length, 1);
      expect(rows.where((r) => matchesWardSearch(r, '')).length, 2);
    });
  });

  group('notes and errors', () {
    test('a note needs text and a sane length', () {
      expect(checkNote(t, '   '), t.noteTextRequired);
      expect(checkNote(t, 'x' * (maxNoteLength + 1)), t.noteTooLong(maxNoteLength));
      expect(checkNote(t, 'Patient comfortable.'), isNull);
    });

    test('a refused dose is explained without the server text', () {
      expect(
        doseErrorMessage(t, const ApiException(kind: ApiErrorKind.validation)),
        t.doseNotRecorded,
      );
      expect(
        doseErrorMessage(t, const ApiException(kind: ApiErrorKind.timeout)),
        t.doseOutcomeUnknown,
      );
      expect(
        doseErrorMessage(t, const ApiException(kind: ApiErrorKind.forbidden)),
        t.errorForbidden,
      );
    });
  });

  group('ApiNursingRepository', () {
    test('finds the own profile by login among the hospital nurses', () async {
      final s = nursingRepo({
        'GET ${base}nurses/nurses/': (
          page([
            {'id': 4, 'user': 1, 'name': 'Other Nurse'},
            {'id': 5, 'user': 2, 'name': 'Test Nurse'},
          ]),
          200,
        ),
      });
      final me = await s.repo.myProfile(hospitalId: 7, userId: 2);
      expect(me?.id, 5);
      expect(only(s.adapter).uri.queryParameters['hospital'], '7');
      expect(only(s.adapter).headers['X-Hospital-ID'], '7');
    });

    test('ward vitals are a Focused assessment on the stay', () async {
      final s = nursingRepo({
        'POST ${base}nurses/assessments/': ({'id': 1, 'assessment_type': 'Focused'}, 201),
      });
      await s.repo.addWardVitals(
        hospitalId: 7,
        patientId: 11,
        admissionId: 3,
        vitals: {'pulse': '72'},
      );
      expect(only(s.adapter).data, {
        'hospital': 7,
        'patient': 11,
        'admission': 3,
        'assessment_type': 'Focused',
        'vitals': {'pulse': '72'},
      });
    });

    test('a note never names a nurse: the server sets the author', () async {
      final s = nursingRepo({
        'POST ${base}nurses/notes/': ({'id': 1, 'note_type': 'Progress', 'note': 'x'}, 201),
      });
      await s.repo.addNote(
        hospitalId: 7,
        patientId: 11,
        admissionId: 3,
        type: 'Progress',
        text: '  Settled overnight.  ',
      );
      final body = only(s.adapter).data as Map;
      expect(body.containsKey('nurse'), isFalse);
      expect(body['note'], 'Settled overnight.');
    });

    test('a dose outcome posts to its action with the reason only', () async {
      final s = nursingRepo({
        'POST ${base}nurses/mar-administrations/9/hold/': (
          {'id': 9, 'status': 'Held', 'medicine_name': 'X'},
          200,
        ),
        'POST ${base}nurses/mar-administrations/9/administer/': (
          {'id': 9, 'status': 'Administered', 'medicine_name': 'X'},
          200,
        ),
      });
      await s.repo.recordDose(9, DoseAction.hold, reason: ' NPO for surgery ');
      expect(s.adapter.requests.last.data, {'reason': 'NPO for surgery'});
      final given = await s.repo.recordDose(9, DoseAction.administer);
      expect(s.adapter.requests.last.data, <String, Object?>{});
      expect(given.status, 'Administered');
      // No Idempotency-Key is invented: the server's row lock decides.
      expect(s.adapter.requests.last.headers['Idempotency-Key'], isNull);
    });

    test('a refused dose surfaces as a validation error', () async {
      final s = nursingRepo({
        'POST ${base}nurses/mar-administrations/9/administer/': (
          {
            'error': true,
            'status_code': 400,
            'message': 'Already administered.',
            'details': {'detail': 'Already administered.'},
          },
          400,
        ),
      });
      await expectLater(
        s.repo.recordDose(9, DoseAction.administer),
        throwsA(
          isA<ApiException>().having((e) => e.kind, 'kind', ApiErrorKind.validation),
        ),
      );
    });

    test('due doses ask for the acting hospital', () async {
      final s = nursingRepo({
        'GET ${base}nurses/mar/due_medications/': (
          [
            {'id': 1, 'status': 'Scheduled', 'medicine_name': 'X'},
          ],
          200,
        ),
      });
      final due = await s.repo.dueDoses(7);
      expect(due.single.isDue, isTrue);
      expect(only(s.adapter).uri.queryParameters['hospital'], '7');
    });

    test('open visits keep only Waiting / In Consultation', () async {
      final s = nursingRepo({
        'GET ${base}encounters/visits/': (
          page([
            {'id': 1, 'status': 'Waiting', 'patient': 11},
            {'id': 2, 'status': 'Completed', 'patient': 11},
          ]),
          200,
        ),
      });
      final visits = await s.repo.openVisits(11);
      expect(visits.map((v) => v.id), [1]);
    });
  });
}
