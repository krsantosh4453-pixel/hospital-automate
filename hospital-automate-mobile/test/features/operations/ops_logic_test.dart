import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/emergency/data/emergency_models.dart';
import 'package:hms_mobile/features/emergency/data/emergency_repository.dart';
import 'package:hms_mobile/features/emergency/ui/emergency_screen.dart';
import 'package:hms_mobile/features/emergency/ui/emergency_ui.dart';
import 'package:hms_mobile/features/hospital/data/hospital_models.dart';
import 'package:hms_mobile/features/hospital/data/hospital_repository.dart';
import 'package:hms_mobile/features/ipd/data/ipd_models.dart';
import 'package:hms_mobile/features/ipd/data/ipd_repository.dart';
import 'package:hms_mobile/features/ipd/ui/ipd_screen.dart';
import 'package:hms_mobile/features/ipd/ui/ipd_ui.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';

import '../../support/test_app.dart';

// Synthetic data only.

/// A client whose answers come from [routes] ("METHOD path" -> body), and
/// that records every request. Unknown routes answer 404.
({ApiClient api, FakeAdapter adapter}) clientFor(
  Map<String, Object?> routes, {
  int? hospitalId = 7,
  Map<String, int> statuses = const {},
}) {
  final adapter = FakeAdapter((options) async {
    final key = '${options.method} ${options.uri.path}';
    final status = statuses[key] ?? (routes.containsKey(key) ? 200 : 404);
    return jsonBody(jsonEncode(routes[key] ?? {'detail': 'x'}), status);
  });
  final api = ApiClient(
    config: testConfig,
    accessToken: () async => 'token',
    hospitalId: () => hospitalId,
    adapter: adapter,
    log: (_) {},
  );
  return (api: api, adapter: adapter);
}

const _visitJson = {
  'id': 12,
  'patient': 41,
  'hospital': 7,
  'visit_number': 'ER-12',
  'triage_level': 'Urgent',
  'status': 'Waiting',
  'arrival_time': '2026-11-15T09:30:00Z',
  'patient_name': 'Test Patient',
  'attending_doctor_name': null,
  'triage': {'chief_complaint': 'Chest pain', 'pain_score': 6},
  'vitals_records': [
    {'id': 1, 'systolic_bp': 120, 'diastolic_bp': 80, 'temperature': '37.20'},
  ],
  'orders': <Object>[],
  'medications': [
    {'id': 3, 'name': 'Test Med', 'administered': true},
  ],
  'notes': [
    {'id': 4, 'note': 'Seen', 'written_by_username': 'nurse.test'},
  ],
};

EmergencyVisit _visit(int id, String status, String level, {int minute = 0}) =>
    EmergencyVisit(
      id: id,
      status: status,
      triageLevel: level,
      arrivalTime: DateTime.utc(2026, 11, 15, 9, minute),
    );

const _admissionJson = {
  'id': 3,
  'patient': 41,
  'status': 'Admitted',
  'admission_date': '2026-11-14T10:00:00Z',
  'patient_name': 'Test Patient',
  'admitting_doctor_name': 'Dr Test',
  'current_bed': {
    'id': 9,
    'bed': 21,
    'bed_number': 'G1-2',
    'room_number': 'G1',
    'ward_name': 'General',
    'is_active': true,
  },
  'bed_allocations': [
    {'id': 9, 'bed': 21, 'bed_number': 'G1-2', 'is_active': true},
  ],
};

Matcher _apiError(ApiErrorKind kind) =>
    throwsA(isA<ApiException>().having((e) => e.kind, 'kind', kind));

void main() {
  final t = AppLocalizationsEn();

  group('emergency models', () {
    test('parses a visit with triage, vitals, medicines and notes', () {
      final visit = EmergencyVisit.fromJson(_visitJson);
      expect(visit.id, 12);
      expect(visit.visitNumber, 'ER-12');
      expect(visit.triage?.chiefComplaint, 'Chest pain');
      expect(visit.vitals.single.temperature, '37.20');
      expect(visit.medications.single.administered, isTrue);
      expect(visit.notes.single.writtenByName, 'nurse.test');
      expect(visit.isClosed, isFalse);
    });

    test('offers only the moves the server allows from each status', () {
      expect(erActionsFor(ErStatus.registered), contains(ErAction.startTriage));
      expect(
        erActionsFor(ErStatus.registered),
        isNot(contains(ErAction.completeTriage)),
      );
      expect(
        erActionsFor(ErStatus.triage),
        containsAll([ErAction.completeTriage, ErAction.startConsultation]),
      );
      expect(
        erActionsFor(ErStatus.waiting),
        isNot(contains(ErAction.startTriage)),
      );
      for (final closed in ErStatus.closed) {
        expect(erActionsFor(closed), isEmpty, reason: closed);
      }
    });

    test('sorts most urgent first, then by arrival', () {
      final sorted = byUrgency([
        _visit(1, ErStatus.waiting, 'Non-Urgent'),
        _visit(2, ErStatus.waiting, 'Critical', minute: 30),
        _visit(3, ErStatus.waiting, 'Critical', minute: 10),
        _visit(4, ErStatus.waiting, 'Urgent'),
      ]);
      expect(sorted.map((v) => v.id), [3, 2, 4, 1]);
    });

    test('active filter hides closed visits', () {
      final rows = [
        _visit(1, ErStatus.waiting, 'Urgent'),
        _visit(2, ErStatus.discharged, 'Urgent'),
      ];
      expect(filterVisits(rows, ErFilter.active).map((v) => v.id), [1]);
      expect(filterVisits(rows, ErFilter.closed).map((v) => v.id), [2]);
      expect(filterVisits(rows, ErFilter.all), hasLength(2));
    });

    test('triage draft sends only entered scores', () {
      const draft = TriageDraft(
        chiefComplaint: ' Fever ',
        triageLevel: 'Urgent',
      );
      expect(draft.toJson(), {
        'chief_complaint': 'Fever',
        'triage_level': 'Urgent',
      });
    });

    test('dashboard counts default to zero', () {
      final board = ErDashboard.fromJson({
        'status_counts': {'Waiting': 2},
        'triage_counts': <String, Object>{},
        'total_active': 5,
      });
      expect(board.status(ErStatus.waiting), 2);
      expect(board.status(ErStatus.triage), 0);
      expect(board.totalActive, 5);
    });
  });

  group('emergency repository', () {
    test(
      'registers with patient and level; hospital from the header',
      () async {
        final c = clientFor({
          'POST /api/v1/emergency/emergency-visits/': {'patient': 41},
        });
        await ApiEmergencyRepository(c.api)
            .register(patientId: 41, triageLevel: 'Critical');
        final request = c.adapter.requests.single;
        expect(request.data, {'patient': 41, 'triage_level': 'Critical'});
        expect(request.headers['X-Hospital-ID'], '7');
      },
    );

    test('status moves post to the backend actions', () async {
      const base = '/api/v1/emergency/emergency-visits/12';
      final c = clientFor({
        'POST $base/complete_triage/': _visitJson,
        'POST $base/start_consultation/': _visitJson,
        'POST $base/refer/': _visitJson,
      });
      final repo = ApiEmergencyRepository(c.api);
      await repo.completeTriage(
        12,
        const TriageDraft(
          chiefComplaint: 'Pain',
          triageLevel: 'Urgent',
          painScore: 4,
        ),
      );
      await repo.startConsultation(12, doctorId: 3);
      await repo.refer(
        12,
        referredTo: 'City Hospital',
        diagnosis: '',
        followUp: '',
      );
      expect(c.adapter.requests[0].data, {
        'chief_complaint': 'Pain',
        'triage_level': 'Urgent',
        'pain_score': 4,
      });
      expect(c.adapter.requests[1].data, {'doctor_id': 3});
      expect(
        (c.adapter.requests[2].data as Map)['referred_to'],
        'City Hospital',
      );
    });

    test('a refused move surfaces as a validation error', () async {
      const path = 'POST /api/v1/emergency/emergency-visits/12/start_triage/';
      final c = clientFor(
        {
          path: {'detail': 'no'},
        },
        statuses: {path: 400},
      );
      await expectLater(
        ApiEmergencyRepository(c.api).startTriage(12),
        _apiError(ApiErrorKind.validation),
      );
    });

    test("another hospital's visit is a 404, not data", () async {
      final c = clientFor({});
      await expectLater(
        ApiEmergencyRepository(c.api).visit(99),
        _apiError(ApiErrorKind.notFound),
      );
    });
  });

  group('ipd', () {
    test('parses the current bed and the bed moves allowed', () {
      final a = IpdAdmission.fromJson(_admissionJson);
      expect(a.currentBed?.place.label, 'General · G1 · G1-2');
      expect(a.canAllocateBed, isFalse);
      expect(a.canTransferBed, isTrue);
      expect(a.canInitiateDischarge, isTrue);
    });

    test('a stay without a bed may get one; a discharged one may not', () {
      const waiting = IpdAdmission(id: 1, status: AdmissionStatus.admitted);
      const done = IpdAdmission(id: 2, status: AdmissionStatus.discharged);
      expect(waiting.canAllocateBed, isTrue);
      expect(done.canAllocateBed || done.canTransferBed, isFalse);
    });

    test('readiness blockers come from the structured fields', () {
      final readiness = DischargeReadiness.fromJson({
        'ready': false,
        'blockers': ['Server sentence'],
        'checklist': [
          {'field': 'medications_reconciled', 'label': 'x', 'done': true},
          {'field': 'follow_up_arranged', 'label': 'x', 'done': false},
        ],
        'plan': 5,
        'summary_finalized': false,
        'final_invoice': {'id': 1, 'total': '1000.00', 'balance_due': '400.00'},
      });
      const admission = IpdAdmission(
        id: 3,
        status: AdmissionStatus.dischargeInitiated,
      );
      expect(dischargeBlockers(t, admission, readiness), [
        t.ipdCheckFollowUp,
        t.ipdSummaryNotFinalized,
        t.ipdBillDue,
      ]);
      expect(readiness.billPaid, isFalse);
    });

    test('unknown blockers fall back to the server text', () {
      const readiness = DischargeReadiness(
        ready: false,
        hasPlan: true,
        summaryFinalized: true,
        serverBlockers: ['Something new'],
        finalBill: FinalBill(id: 1, balanceDue: 0),
      );
      const admission = IpdAdmission(
        id: 3,
        status: AdmissionStatus.dischargeInitiated,
      );
      expect(dischargeBlockers(t, admission, readiness), ['Something new']);
    });

    test('ready means no blockers', () {
      const admission = IpdAdmission(
        id: 3,
        status: AdmissionStatus.dischargeInitiated,
      );
      expect(
        dischargeBlockers(t, admission, const DischargeReadiness(ready: true)),
        isEmpty,
      );
    });

    test('current filter keeps stays still in hospital', () {
      const rows = [
        IpdAdmission(id: 1, status: AdmissionStatus.admitted),
        IpdAdmission(id: 2, status: AdmissionStatus.dischargeInitiated),
        IpdAdmission(id: 3, status: AdmissionStatus.discharged),
      ];
      expect(filterAdmissions(rows, IpdFilter.current).map((a) => a.id), [
        1,
        2,
      ]);
      expect(filterAdmissions(rows, IpdFilter.discharged).map((a) => a.id), [
        3,
      ]);
    });

    test('overview reads the server count and the free beds', () async {
      final c = clientFor({
        'GET /api/v1/ipd/admissions/': {
          'count': 4,
          'next': null,
          'results': <Object>[],
        },
        'GET /api/v1/ipd/bed-allocations/available_beds/': [
          {'id': 1, 'bed_number': 'A'},
          {'id': 2, 'bed_number': 'B'},
        ],
      });
      final o = await ApiIpdRepository(c.api).overview(7);
      expect(o.admitted, 4);
      expect(o.discharged, 4);
      expect(o.availableBeds, 2);
      final bedCall = c.adapter.requests.firstWhere(
        (r) => r.uri.path.contains('available_beds'),
      );
      expect(bedCall.queryParameters['hospital'], 7);
    });

    test('bed moves send bed_id', () async {
      final c = clientFor({
        'POST /api/v1/ipd/admissions/3/allocate_bed/': {'id': 1},
        'POST /api/v1/ipd/admissions/3/transfer/': {'id': 2},
      });
      final repo = ApiIpdRepository(c.api);
      await repo.allocateBed(3, 21);
      await repo.transferBed(3, 22);
      expect(c.adapter.requests.map((r) => r.data), [
        {'bed_id': 21},
        {'bed_id': 22},
      ]);
    });

    test('an occupied bed is refused by the server and not hidden', () async {
      final c = clientFor(
        {},
        statuses: {'POST /api/v1/ipd/admissions/3/allocate_bed/': 400},
      );
      await expectLater(
        ApiIpdRepository(c.api).allocateBed(3, 21),
        _apiError(ApiErrorKind.validation),
      );
    });

    test('the discharge summary is matched by admission', () async {
      final c = clientFor({
        'GET /api/v1/ipd/discharge-summaries/': {
          'next': null,
          'results': [
            {'id': 1, 'admission': 2, 'summary': 'Other stay'},
            {
              'id': 5,
              'admission': 3,
              'summary': 'This stay',
              'finalized': true,
            },
          ],
        },
      });
      final summary = await ApiIpdRepository(c.api).dischargeSummary(3);
      expect(summary?.summary, 'This stay');
      expect(summary?.finalized, isTrue);
    });

    test('the bed board stops at the page cap and says so', () async {
      final c = clientFor({
        'GET /api/v1/hospital/beds/': {
          'next': 'more',
          'results': [
            {'id': 1, 'status': 'Available', 'ward_name': 'General'},
          ],
        },
      });
      final board = await ApiIpdRepository(c.api).bedBoard();
      expect(board.complete, isFalse);
      expect(board.beds, hasLength(maxBedPages));
      expect(board.count(BedStatus.available), maxBedPages);
    });
  });

  group('hospital', () {
    test('parses the hospital record without inventing fields', () {
      final h = HospitalInfo.fromJson({
        'id': 7,
        'name': 'Test General Hospital',
        'city': 'Testpur',
        'departments': 3,
        'is_active': true,
      });
      expect(h.fullAddress, 'Testpur');
      expect(h.departments, 3);
      expect(h.phone, isNull);
    });

    test('staff rows keep role and membership', () async {
      final c = clientFor({
        'GET /api/v1/users/': {
          'staff': [
            {
              'id': 5,
              'name': 'Test Nurse',
              'employee_id': 'E1',
              'invite_pending': false,
              'membership': {
                'role': 'Nurse',
                'department': 2,
                'is_active': true,
              },
            },
          ],
        },
      });
      final staff = await ApiHospitalRepository(c.api).staff(search: ' nur ');
      expect(staff.single.role, 'Nurse');
      expect(staff.single.membershipActive, isTrue);
      expect(c.adapter.requests.single.queryParameters['search'], 'nur');
    });

    test('the staff list for a non-manager is a 403', () async {
      final c = clientFor({}, statuses: {'GET /api/v1/users/': 403});
      await expectLater(
        ApiHospitalRepository(c.api).staff(),
        _apiError(ApiErrorKind.forbidden),
      );
    });
  });

  test('no hospital header is sent when none is chosen', () async {
    final c = clientFor({
      'GET /api/v1/emergency/emergency-visits/dashboard/': {'total_active': 0},
    }, hospitalId: null);
    await ApiEmergencyRepository(c.api).dashboard();
    final RequestOptions request = c.adapter.requests.single;
    expect(request.headers.containsKey('X-Hospital-ID'), isFalse);
    expect(request.headers['Authorization'], 'Bearer token');
  });

  group('BUG-10 bed line of a stay', () {
    final t = AppLocalizationsEn();
    setUpAll(() => initializeDateFormatting('en'));
    IpdAdmission stayWith({
      Map<String, Object?>? current,
      List<Object?> history = const [],
    }) => IpdAdmission.fromJson({
      'id': 3,
      'status': 'Discharged',
      'current_bed': current,
      'bed_allocations': history,
    });
    const bed = {
      'ward_name': 'Ward A',
      'room_number': '1',
      'bed_number': 'E2E-2',
    };

    test(
      'a discharged stay shows the released bed, not "Waiting for a bed"',
      () {
        final stay = stayWith(
          history: [
            {
              ...bed,
              'id': 1,
              'is_active': false,
              'released_at': '2026-11-20T10:00:00+05:30',
            },
          ],
        );
        expect(stay.releasedBed, isNotNull);
        expect(bedLabel(t, stay), contains('released'));
        expect(bedLabel(t, stay), isNot(t.ipdAwaitingBed));
      },
    );

    test('a stay with no bed yet still says Waiting for a bed', () {
      expect(bedLabel(t, stayWith()), t.ipdAwaitingBed);
    });

    test('the latest released bed is shown after a transfer', () {
      final stay = stayWith(
        history: [
          {
            'id': 1,
            'ward_name': 'ICU',
            'bed_number': 'I1',
            'is_active': false,
            'released_at': '2026-11-18T10:00:00Z',
          },
          {
            'id': 2,
            'ward_name': 'Ward A',
            'bed_number': 'A9',
            'is_active': false,
            'released_at': '2026-11-20T10:00:00Z',
          },
        ],
      );
      expect(stay.releasedBed!.id, 2);
    });
  });
}
