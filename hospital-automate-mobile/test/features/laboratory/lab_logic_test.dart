import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/laboratory/data/lab_repository.dart';
import 'package:hms_mobile/features/laboratory/data/lab_workflow.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';

import '../../support/test_app.dart';

// Synthetic data only.
SessionState roleSession(String role, Set<String> permissions) => SessionState(
  user: const SessionUser(displayName: 'staff.test'),
  hospitals: [
    HospitalContext(
      id: 7,
      name: 'Test General Hospital',
      role: role,
      permissions: permissions,
    ),
  ],
  activeHospitalId: 7,
);

const labVAE = {'Laboratory.View', 'Laboratory.Add', 'Laboratory.Edit'};

final labTestJson = <String, Object?>{
  'id': 5,
  'hospital': 7,
  'name': 'Complete Blood Count',
  'patient': 41,
  'doctor': 3,
  'visit': 9,
  'priority': 'Urgent',
  'status': 'Dispatched',
  'test_date': '2026-11-15',
  'collected_at': '2026-11-15T04:00:00Z',
  'dispatched_at': '2026-11-15T04:30:00Z',
  'patient_name': 'Test Patient Lab',
  'doctor_name': 'Dr Test',
  'sample_collection': {
    'sample_id': 'LAB20261115-7-000005',
    'sample_type': 'Blood',
    'container_type': 'EDTA',
    'collected_by_name': 'Nurse Test',
    'collection_notes': 'Fasting',
    'collected_at': '2026-11-15T04:00:00Z',
  },
  'sample_dispatch': {
    'status': 'Dispatched',
    'dispatched_by_name': 'Lab Runner',
    'external_lab': '',
  },
  'lab_result': null,
};

({ApiLabRepository repo, FakeAdapter adapter}) labRepo(
  Map<String, (Object body, int status)> routes,
) {
  final adapter = FakeAdapter((options) async {
    final answer = routes[options.uri.path];
    if (answer == null) return jsonBody('{"detail":"Not found."}', 404);
    return jsonBody(jsonEncode(answer.$1), answer.$2);
  });
  final api = ApiClient(
    config: testConfig,
    accessToken: () async => 'access-token',
    hospitalId: () => 7,
    adapter: adapter,
    log: (_) {},
  );
  return (repo: ApiLabRepository(api), adapter: adapter);
}

void main() {
  group('workflow', () {
    test('each status has exactly the step the server accepts next', () {
      expect(nextLabStep('Ordered'), LabStep.collect);
      expect(nextLabStep('Sample Pending'), LabStep.collect);
      expect(nextLabStep('Collected'), LabStep.dispatch);
      expect(nextLabStep('Dispatched'), LabStep.receive);
      expect(nextLabStep('Received'), LabStep.startProcessing);
      expect(nextLabStep('Processing'), LabStep.enterResult);
      expect(nextLabStep('Result Entered'), LabStep.verify);
      expect(nextLabStep('Verified'), LabStep.release);
      expect(nextLabStep('Released'), isNull);
      expect(nextLabStep('Cancelled'), isNull);
      expect(nextLabStep('Unknown'), isNull);
    });

    test('every server status falls in exactly one worklist group', () {
      const all = [
        'Ordered',
        'Sample Pending',
        'Collected',
        'Dispatched',
        'Received',
        'Processing',
        'Result Entered',
        'Verified',
        'Released',
        'Cancelled',
      ];
      for (final status in all) {
        expect(
          LabQueue.values.where((q) => q.statuses.contains(status)),
          hasLength(1),
          reason: status,
        );
      }
    });

    test(
      'lab staff may run every step; a nurse only collects and dispatches',
      () {
        final lab = roleSession('Lab Staff', labVAE);
        final nurse = roleSession('Nurse', {
          'Laboratory.View',
          'Laboratory.Edit',
        });
        for (final step in LabStep.values) {
          expect(mayRunLabStep(lab, step), isTrue, reason: step.name);
        }
        expect(mayRunLabStep(nurse, LabStep.collect), isTrue);
        expect(mayRunLabStep(nurse, LabStep.dispatch), isTrue);
        expect(mayRunLabStep(nurse, LabStep.enterResult), isFalse);
        expect(mayRunLabStep(nurse, LabStep.verify), isFalse);
        expect(mayRunLabStep(nurse, LabStep.release), isFalse);
        expect(mayOrderLabTests(nurse), isFalse); // view + edit only
      },
    );

    test('doctors, managers and patients are offered no lab step', () {
      final doctor = roleSession('Doctor', {
        'Laboratory.View',
        'Laboratory.Add',
      });
      final manager = roleSession('Hospital Manager', {'Laboratory.View'});
      for (final step in LabStep.values) {
        expect(mayRunLabStep(doctor, step), isFalse);
        expect(mayRunLabStep(manager, step), isFalse);
        expect(mayRunLabStep(patientSession(), step), isFalse);
      }
      expect(mayOrderLabTests(doctor), isTrue);
      expect(mayOrderLabTests(manager), isFalse);
      expect(mayCancelLabOrder(manager, 'Ordered'), isFalse);
    });

    test('a step needs the edit permission even for the right role', () {
      // A hospital restriction that makes Laboratory view-only drops Edit.
      final restricted = roleSession('Lab Staff', {'Laboratory.View'});
      expect(mayRunLabStep(restricted, LabStep.collect), isFalse);
    });

    test(
      'verified, released or cancelled orders are never offered a cancel',
      () {
        final lab = roleSession('Lab Staff', labVAE);
        expect(mayCancelLabOrder(lab, 'Processing'), isTrue);
        for (final status in ['Verified', 'Released', 'Cancelled']) {
          expect(mayCancelLabOrder(lab, status), isFalse, reason: status);
        }
      },
    );
  });

  group('model', () {
    test('reads the sample trail and staff fields', () {
      final test = LabTest.fromJson(labTestJson);
      expect(test.hospitalId, 7);
      expect(test.visitId, 9);
      expect(test.sample!.sampleId, 'LAB20261115-7-000005');
      expect(test.sample!.containerType, 'EDTA');
      expect(test.sample!.collectedByName, 'Nurse Test');
      expect(test.dispatch!.dispatchedByName, 'Lab Runner');
      expect(test.dispatch!.externalLab, isNull);
      expect(test.collectedAt, isNotNull);
      expect(test.result, isNull);
    });

    test('reads who entered and verified a result', () {
      final test = LabTest.fromJson({
        ...labTestJson,
        'status': 'Verified',
        'lab_result': {
          'result_data': <String, Object?>{},
          'result_text': 'Haemoglobin 13.1 g/dL',
          'entered_by_name': 'Lab Tech',
          'verified_by_name': 'Lab Lead',
          'is_verified': true,
          'abnormal_flags': <Object?>[],
        },
      });
      expect(test.result!.text, 'Haemoglobin 13.1 g/dL');
      expect(test.result!.enteredByName, 'Lab Tech');
      expect(test.result!.verifiedByName, 'Lab Lead');
      expect(test.result!.isVerified, isTrue);
      expect(test.result!.flags, isEmpty);
    });
  });

  group('repository', () {
    test(
      'a step posts to its own action and returns the updated test',
      () async {
        final setup = labRepo({
          '/api/v1/laboratory/5/collect_sample/': (
            {
              'lab_test': {...labTestJson, 'status': 'Collected'},
              'sample_collection': {'sample_id': 'S1'},
            },
            201,
          ),
        });
        final updated = await setup.repo.advance(
          5,
          LabStep.collect,
          const SampleCollectionInput(
            sampleType: 'Urine',
            containerType: 'Urine Container',
            sampleId: ' BAR-9 ',
          ).toJson(),
        );
        expect(updated.status, 'Collected');
        final request = setup.adapter.requests.single;
        expect(request.method, 'POST');
        expect(request.headers['X-Hospital-ID'], '7');
        expect(request.data, {
          'sample_type': 'Urine',
          'container_type': 'Urine Container',
          'sample_id': 'BAR-9',
        });
      },
    );

    test('start_processing answers with the test itself', () async {
      final setup = labRepo({
        '/api/v1/laboratory/5/start_processing/': (
          {...labTestJson, 'status': 'Processing'},
          200,
        ),
      });
      final updated = await setup.repo.advance(5, LabStep.startProcessing);
      expect(updated.status, 'Processing');
    });

    test('a refused step surfaces as a validation error', () async {
      final setup = labRepo({
        '/api/v1/laboratory/5/verify_result/': (
          {
            'error': true,
            'message': 'Result must be entered before verification.',
          },
          400,
        ),
      });
      await expectLater(
        setup.repo.advance(5, LabStep.verify),
        throwsA(
          isA<ApiException>().having(
            (e) => e.kind,
            'kind',
            ApiErrorKind.validation,
          ),
        ),
      );
    });

    test(
      'a new order sends the hospital, patient, name and priority',
      () async {
        final setup = labRepo({
          '/api/v1/laboratory/': ({...labTestJson, 'status': 'Ordered'}, 201),
        });
        await setup.repo.createOrder(
          const LabOrderDraft(
            hospitalId: 7,
            patientId: 41,
            testName: '  Lipid Profile ',
            priority: 'Urgent',
          ),
        );
        expect(setup.adapter.requests.single.data, {
          'hospital': 7,
          'patient': 41,
          'name': 'Lipid Profile',
          'priority': 'Urgent',
        });
      },
    );

    test('patient lookup uses the minimal lookup endpoint', () async {
      final setup = labRepo({
        '/api/v1/patients/lookup/': (
          [
            {
              'id': 41,
              'name': 'Test Patient Lab',
              'uhid': 'UH-1',
              'phone': '******0001',
            },
          ],
          200,
        ),
      });
      final found = await setup.repo.lookupPatients(' Test ');
      expect(found.single.uhid, 'UH-1');
      expect(setup.adapter.requests.single.uri.queryParameters, {
        'search': 'Test',
      });
    });

    test('sample lookup sends the scanned number', () async {
      final setup = labRepo({
        '/api/v1/laboratory/by_sample/': (labTestJson, 200),
      });
      final found = await setup.repo.findBySample(' LAB20261115-7-000005 ');
      expect(found.id, 5);
      expect(
        setup.adapter.requests.single.uri.queryParameters['sample_id'],
        'LAB20261115-7-000005',
      );
    });
  });
}
