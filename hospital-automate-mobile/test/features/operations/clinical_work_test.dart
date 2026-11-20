import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/theme/app_colors.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/ipd/data/clinical_work_repository.dart';
import 'package:hms_mobile/features/ipd/data/ipd_models.dart';

import 'package:hms_mobile/shared/widgets/hms_button.dart';

import '../../support/test_app.dart';

// Prompt 3, synthetic data only.

class FakeClinicalWork implements ClinicalWorkRepository {
  String status = AllergyStatus.unknown;
  final List<AllergyRecord> allergyRows = [];
  Object? statusError;
  final List<String> calls = [];
  final List<MedicationOrderDraft> orderDrafts = [];
  final List<MedicationOrderDraft> previewDrafts = [];
  Object? previewError;
  SchedulePreview preview = SchedulePreview(
    mode: FirstDose.nextRound,
    firstDoseAt: DateTime(2026, 11, 20, 14),
    doses: [
      DateTime(2026, 11, 20, 14),
      DateTime(2026, 11, 21, 14),
      DateTime(2026, 11, 22, 14),
    ],
    doseCount: 3,
    rounds: const ['08:00', '14:00', '20:00'],
  );
  final List<MedicationOrder> orders = [];
  DischargePlanRecord? plan;
  String? summaryText;
  List<StayAwaitingBill> stays = const [];
  List<TimelineEvent> events = const [];

  @override
  Future<String> allergyStatus(int patientId) async =>
      allergyRows.isEmpty ? status : AllergyStatus.recorded;

  @override
  Future<List<AllergyRecord>> allergies(int patientId) async {
    if (allergiesError != null) throw allergiesError!;
    return allergyRows;
  }

  Object? allergiesError;

  @override
  Future<AllergyRecord> addAllergy(
    int patientId, {
    required String name,
    required String category,
    String reaction = '',
    String severity = '',
  }) async {
    final row = AllergyRecord(
      id: allergyRows.length + 1,
      name: name,
      category: category,
      reaction: reaction,
    );
    allergyRows.add(row);
    status = AllergyStatus.unknown;
    return row;
  }

  @override
  Future<String> setAllergyStatus(int patientId, String value) async {
    calls.add('status:$value');
    if (statusError != null) throw statusError!;
    status = value;
    return value;
  }

  @override
  Future<IpdAdmission> admit(
    int patientId,
    int hospitalId,
    String reason,
  ) async {
    calls.add('admit:$patientId:$hospitalId:$reason');
    return const IpdAdmission(id: 77, status: 'Admitted', patientId: 2);
  }

  @override
  Future<List<MedicationOrder>> medicationOrders(int admissionId) async =>
      orders;

  @override
  Future<List<PrescribedMedicine>> prescribedMedicines(int patientId) async =>
      const [
        PrescribedMedicine(
          id: 5,
          prescriptionId: 4,
          name: 'Synthetic Pantoprazole 40mg',
          dosage: '40 mg',
          frequency: 'OD',
        ),
      ];

  @override
  Future<MedicationOrder> orderMedication(
    int admissionId,
    int patientId,
    int hospitalId,
    MedicationOrderDraft draft,
  ) async {
    orderDrafts.add(draft);
    final order = MedicationOrder(
      id: 9,
      medicineName: draft.medicine.name,
      dose: draft.dose,
      route: draft.route,
      frequency: draft.frequency,
      isActive: true,
      instructions: draft.instructions,
    );
    orders.add(order);
    return order;
  }

  @override
  Future<SchedulePreview> previewSchedule(
    int hospitalId,
    MedicationOrderDraft draft,
  ) async {
    previewDrafts.add(draft);
    if (previewError != null) throw previewError!;
    return preview;
  }

  @override
  Future<void> stopMedication(int orderId) async => calls.add('stop:$orderId');

  @override
  Future<DischargePlanRecord?> dischargePlan(int admissionId) async => plan;

  @override
  Future<DischargePlanRecord> saveDischargePlan(
    int admissionId,
    DischargePlanRecord value, {
    int? existingId,
  }) async {
    plan = DischargePlanRecord(
      id: 3,
      instructions: value.instructions,
      medicationsReconciled: value.medicationsReconciled,
    );
    return plan!;
  }

  @override
  Future<void> saveDischargeSummary(
    int admissionId,
    String summary, {
    int? existingId,
  }) async => summaryText = summary;

  @override
  Future<void> finalizeDischargeSummary(int summaryId) async =>
      calls.add('finalize:$summaryId');

  @override
  Future<List<StayAwaitingBill>> staysAwaitingFinalBill() async => stays;

  @override
  Future<void> createFinalBill(int admissionId) async {
    calls.add('bill:$admissionId');
    if (billError != null) throw billError!;
  }

  Object? billError;

  @override
  Future<List<TimelineEvent>> history(int patientId) async => events;
}

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> typeInto(WidgetTester tester, String key, String text) async {
  final field = find.descendant(
    of: find.byKey(ValueKey(key)),
    matching: find.byType(TextField),
  );
  await tester.ensureVisible(field);
  await tester.enterText(field, text);
  await tester.pump();
}

Future<void> choose(WidgetTester tester, String key, String option) async {
  await tapVisible(tester, find.byKey(ValueKey(key)));
  await tester.tap(find.text(option).last);
  await tester.pumpAndSettle();
}

const _doctorPermissions = {...allViewPermissions, 'IPD.Edit'};

/// A doctor login (with a user id, so the doctor's own profile loads).
SessionState _doctorSession() => const SessionState(
  user: SessionUser(id: 90, displayName: 'dr.synthetic', firstName: 'Test'),
  hospitals: [
    HospitalContext(
      id: 7,
      name: 'Test General Hospital',
      role: 'Doctor',
      permissions: _doctorPermissions,
    ),
  ],
  activeHospitalId: 7,
);

const _visit = Visit(
  id: 5,
  status: Visit.inConsultation,
  patientId: 2,
  patientName: 'Synthetic Ward Patient',
  doctorId: 3,
  hospitalId: 7,
  visitType: 'OPD',
);

void main() {
  group('allergies (consultation)', () {
    Future<FakeClinicalWork> pumpConsultation(
      WidgetTester tester, [
      FakeClinicalWork? given,
    ]) async {
      final work = given ?? FakeClinicalWork();
      await pumpApp(
        tester,
        testServices(
          session: _doctorSession(),
          doctor: FakeDoctorRepository(visitRows: const [_visit]),
          clinicalWork: work,
        ),
        location: '/consultation/5',
      );
      return work;
    }

    testWidgets('unknown is shown as unknown, then recorded as none', (
      tester,
    ) async {
      final work = await pumpConsultation(tester);
      expect(find.text('Not known (not asked yet)'), findsOneWidget);

      await tapVisible(tester, find.byKey(const Key('allergy-none')));

      expect(work.calls, ['status:${AllergyStatus.none}']);
      expect(find.text('No known allergies'), findsOneWidget);
    });

    testWidgets('an added drug allergy is listed and shown as Has allergies', (
      tester,
    ) async {
      await pumpConsultation(tester);
      await typeInto(tester, 'allergy-name', 'Penicillin');
      await typeInto(tester, 'allergy-reaction', 'Hives');

      await tapVisible(tester, find.byKey(const Key('allergy-add')));

      expect(find.textContaining('Penicillin · Drug · Hives'), findsOneWidget);
      expect(find.text('Has allergies'), findsOneWidget);
    });

    bool noneEnabled(WidgetTester tester) =>
        tester
            .widget<HmsButton>(find.byKey(const Key('allergy-none')))
            .onPressed !=
        null;

    testWidgets(
      'an allergy on record disables no known allergies and says why',
      (tester) async {
        final work = FakeClinicalWork()
          ..allergyRows.add(
            const AllergyRecord(id: 1, name: 'Penicillin', category: 'Drug'),
          );
        await pumpConsultation(tester, work);

        expect(noneEnabled(tester), isFalse);
        expect(find.byKey(const Key('allergy-none-blocked')), findsOneWidget);
        expect(work.calls, isEmpty);
      },
    );

    testWidgets('adding an allergy disables no known allergies at once', (
      tester,
    ) async {
      await pumpConsultation(tester);
      expect(noneEnabled(tester), isTrue);
      expect(find.byKey(const Key('allergy-none-blocked')), findsNothing);

      await typeInto(tester, 'allergy-name', 'Penicillin');
      await tapVisible(tester, find.byKey(const Key('allergy-add')));

      expect(noneEnabled(tester), isFalse);
    });

    testWidgets('a failed allergy load offers no allergy actions', (
      tester,
    ) async {
      await pumpConsultation(
        tester,
        FakeClinicalWork()
          ..allergiesError = const ApiException(kind: ApiErrorKind.network),
      );

      expect(find.byKey(const Key('allergy-none')), findsNothing);
      expect(find.text('No known allergies'), findsNothing);
    });

    testWidgets('no known allergies is refused while one is on record', (
      tester,
    ) async {
      await pumpConsultation(
        tester,
        FakeClinicalWork()
          ..statusError = const ApiException(
            kind: ApiErrorKind.conflict,
            statusCode: 409,
            flags: {'allergy_on_record'},
          ),
      );

      await tapVisible(tester, find.byKey(const Key('allergy-none')));

      expect(find.textContaining('An allergy is on record'), findsOneWidget);
    });
  });

  testWidgets('a doctor admits a patient straight into a free bed', (
    tester,
  ) async {
    final work = FakeClinicalWork();
    final ipd = FakeIpdRepository(
      free: const [
        AvailableBed(
          id: 31,
          place: BedPlace(ward: 'General', room: 'G2', bed: 'G2-1'),
        ),
      ],
      admissionList: const [
        IpdAdmission(id: 77, status: 'Admitted', patientId: 2),
      ],
    );
    await pumpApp(
      tester,
      testServices(
        session: _doctorSession(),
        doctor: FakeDoctorRepository(visitRows: const [_visit]),
        ipd: ipd,
        clinicalWork: work,
      ),
      location: '/ipd/admit/2',
    );

    await tapVisible(tester, find.byKey(const Key('admit-confirm')));
    expect(find.text('Enter the reason for admission.'), findsOneWidget);
    expect(work.calls, isEmpty);

    await typeInto(tester, 'admit-reason', 'Synthetic observation');
    await choose(tester, 'admit-ward', 'General');
    final bedLabel = const BedPlace(
      ward: 'General',
      room: 'G2',
      bed: 'G2-1',
    ).label;
    await choose(tester, 'admit-bed-General', bedLabel);
    await tapVisible(tester, find.byKey(const Key('admit-confirm')));

    expect(work.calls, ['admit:2:7:Synthetic observation']);
    expect(ipd.calls, contains('allocate_bed:77:31'));
  });

  group('admission screen (doctor)', () {
    Future<FakeClinicalWork> pumpAdmission(
      WidgetTester tester, {
      String status = 'Admitted',
      DischargeSummaryRecord? summary,
    }) async {
      final work = FakeClinicalWork();
      await pumpApp(
        tester,
        testServices(
          session: _doctorSession(),
          ipd: FakeIpdRepository(
            admissionList: [
              IpdAdmission(
                id: 77,
                status: status,
                patientId: 2,
                patientName: 'Synthetic Ward Patient',
              ),
            ],
            summary: summary,
          ),
          clinicalWork: work,
        ),
        location: '/ipd/77',
      );
      return work;
    }

    testWidgets('a ward order is placed; nothing is recorded as given', (
      tester,
    ) async {
      final work = await pumpAdmission(tester);

      await choose(
        tester,
        'order-medicine',
        'Synthetic Pantoprazole 40mg · 40 mg',
      );
      await choose(tester, 'order-route', 'IV');
      await typeInto(tester, 'order-instructions', 'Before breakfast');
      await tapVisible(tester, find.byKey(const Key('order-add')));
      // The doctor reviews the first dose before anything is saved.
      expect(work.orderDrafts, isEmpty);
      expect(find.text('Review the dose schedule'), findsOneWidget);
      expect(find.textContaining('Next medication round'), findsWidgets);
      expect(find.textContaining('3 doses scheduled'), findsOneWidget);
      await tapVisible(tester, find.text('Order medicine').last);

      final draft = work.orderDrafts.single;
      expect(draft.firstDose, FirstDose.nextRound);
      expect((draft.dose, draft.route, draft.frequency), ('40 mg', 'IV', 'OD'));
      expect(draft.instructions, 'Before breakfast');
      expect(find.textContaining('Before breakfast'), findsOneWidget);
      expect(find.textContaining('Given'), findsNothing);
    });

    testWidgets('a first dose the server cannot place asks for a choice', (
      tester,
    ) async {
      final work = await pumpAdmission(tester)
        ..previewError = const ApiException(
          kind: ApiErrorKind.validation,
          statusCode: 400,
          fieldErrors: {
            'first_dose': ['No rounds.'],
          },
          flags: {'first_dose_required'},
        );
      await choose(
        tester,
        'order-medicine',
        'Synthetic Pantoprazole 40mg · 40 mg',
      );
      await tapVisible(tester, find.byKey(const Key('order-add')));

      expect(
        find.textContaining('Choose Start now or a specific time'),
        findsOneWidget,
      );
      expect(work.orderDrafts, isEmpty);
    });

    testWidgets('start now is sent; cancelling the review saves nothing', (
      tester,
    ) async {
      final work = await pumpAdmission(tester);
      await choose(
        tester,
        'order-medicine',
        'Synthetic Pantoprazole 40mg · 40 mg',
      );
      await tapVisible(tester, find.byKey(const Key('first-dose-now')));
      await tapVisible(tester, find.byKey(const Key('order-add')));
      expect(work.previewDrafts.single.firstDose, FirstDose.now);
      await tapVisible(tester, find.text('Cancel').last);
      expect(work.orderDrafts, isEmpty);
    });

    testWidgets('closing the time picker keeps the earlier choice', (
      tester,
    ) async {
      final work = await pumpAdmission(tester);
      await choose(
        tester,
        'order-medicine',
        'Synthetic Pantoprazole 40mg · 40 mg',
      );
      await tapVisible(tester, find.byKey(const Key('first-dose-at')));
      // The date picker opened; closing it chooses no time, so the order
      // keeps the next medication round rather than a missing time.
      await tapVisible(tester, find.text('Cancel').last);
      await tapVisible(tester, find.byKey(const Key('order-add')));
      expect(work.previewDrafts.single.firstDose, FirstDose.nextRound);
      expect(work.previewDrafts.single.firstDoseAt, isNull);
    });

    testWidgets('plan checkboxes are light on the teal card (finding 2)', (
      tester,
    ) async {
      await pumpAdmission(tester, status: 'Discharge Initiated');
      final box = tester.widget<CheckboxListTile>(
        find.byType(CheckboxListTile).first,
      );
      final side = box.side! as WidgetStateBorderSide;
      expect(side.resolve(const {})!.color, AppColors.onCard);
      expect(
        side.resolve(const {WidgetState.disabled})!.color,
        AppColors.onCardMuted,
      );
      expect(
        box.fillColor!.resolve(const {WidgetState.selected}),
        AppColors.onCard,
      );
      expect(box.fillColor!.resolve(const {}), Colors.transparent);
      expect(box.checkColor, AppColors.card);
    });

    testWidgets('the discharge plan and summary are written and finalised', (
      tester,
    ) async {
      final work = await pumpAdmission(
        tester,
        status: 'Discharge Initiated',
        summary: const DischargeSummaryRecord(
          id: 6,
          admissionId: 77,
          summary: 'Draft',
          finalized: false,
        ),
      );

      await typeInto(tester, 'discharge-follow-up', 'Cardiology OPD in 7 days');
      await tapVisible(tester, find.byKey(const Key('discharge-save-plan')));
      expect(work.plan?.instructions, 'Cardiology OPD in 7 days');

      await tapVisible(tester, find.byKey(const Key('discharge-save-summary')));
      expect(
        find.text('Enter the final diagnosis and the condition at discharge.'),
        findsOneWidget,
      );
      await typeInto(tester, 'discharge-diagnosis', 'Synthetic angina');
      await typeInto(tester, 'discharge-condition', 'Stable');
      await tapVisible(tester, find.byKey(const Key('discharge-save-summary')));
      expect(work.summaryText, contains('Final diagnosis: Synthetic angina'));
      expect(work.summaryText, contains('Condition at discharge: Stable'));
      expect(
        work.summaryText,
        contains('Follow-up instructions: Cardiology OPD in 7 days'),
      );

      await tapVisible(tester, find.byKey(const Key('discharge-finalize')));
      await tapVisible(tester, find.text('Finalise summary').last);
      expect(work.calls, contains('finalize:6'));
    });
  });

  testWidgets('billing creates the final bill of a stay being discharged', (
    tester,
  ) async {
    final work = FakeClinicalWork()
      ..stays = const [
        StayAwaitingBill(
          admissionId: 77,
          patientName: 'Synthetic Ward Patient',
          days: 2,
          bedChargeLines: ['Bed charges (general, ₹1500.00/day): 2 day(s)'],
          bedChargeTotal: '3000.00',
        ),
        StayAwaitingBill(
          admissionId: 78,
          patientName: 'Synthetic Unpriced Patient',
          days: 1,
          bedChargeError: 'The price list has no bed charge for: ICU.',
        ),
      ];
    final billing = FakeBillingRepository();
    await pumpApp(
      tester,
      testServices(
        session: staffSession(role: 'Billing Staff'),
        clinicalWork: work,
        billing: billing,
      ),
      location: '/billing',
    );

    // BUG-07: no rate is typed; the bed days come priced from the server.
    expect(find.byKey(const ValueKey('final-rate-77')), findsNothing);
    expect(
      find.text('Bed charges (general, ₹1500.00/day): 2 day(s)'),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('final-beds-77')), findsOneWidget);
    expect(
      find.text('The price list has no bed charge for: ICU.'),
      findsOneWidget,
    );
    await tapVisible(tester, find.byKey(const ValueKey('final-bill-78')));
    expect(work.calls, isEmpty);
    final loadsBefore = billing.statusQueries.length;
    // A confirmation comes first; Cancel creates nothing.
    await tapVisible(tester, find.byKey(const ValueKey('final-bill-77')));
    expect(
      find.text('Create the final bill for Synthetic Ward Patient?'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Bed charges from the price list'),
      findsWidgets,
    );
    await tapVisible(tester, find.text('Cancel').last);
    expect(work.calls, isEmpty);

    await tapVisible(tester, find.byKey(const ValueKey('final-bill-77')));
    await tapVisible(tester, find.text('Create final bill').last);

    expect(work.calls, ['bill:77']);
    // The invoice list reloads, so the new final bill shows without Refresh.
    expect(billing.statusQueries.length, greaterThan(loadsBefore));
  });

  testWidgets('a refused final bill shows an error and can be retried', (
    tester,
  ) async {
    final work = FakeClinicalWork()
      ..billError = const ApiException(
        kind: ApiErrorKind.validation,
        statusCode: 400,
      )
      ..stays = const [
        StayAwaitingBill(
          admissionId: 77,
          patientName: 'Synthetic Ward Patient',
          days: 1,
          bedChargeLines: ['Bed charges (general, ₹1000.00/day): 1 day(s)'],
          bedChargeTotal: '1000.00',
        ),
      ];
    await pumpApp(
      tester,
      testServices(
        session: staffSession(role: 'Billing Staff'),
        clinicalWork: work,
      ),
      location: '/billing',
    );
    await tapVisible(tester, find.byKey(const ValueKey('final-bill-77')));
    await tapVisible(tester, find.text('Create final bill').last);

    expect(work.calls, ['bill:77']);
    expect(find.text('Final bill created.'), findsNothing);
    // The button is usable again for a safe retry.
    final button = tester.widget<HmsButton>(
      find.byKey(const ValueKey('final-bill-77')),
    );
    expect(button.onPressed, isNotNull);
  });

  testWidgets('the patient sees their history, discharge summary included', (
    tester,
  ) async {
    final work = FakeClinicalWork()
      ..events = [
        TimelineEvent(
          kind: 'Discharge',
          title: 'Discharged',
          when: DateTime(2026, 11, 19),
          detail: 'Final diagnosis: synthetic angina',
        ),
        TimelineEvent(
          kind: 'Diagnosis',
          title: 'Provisional: Angina pectoris (I20.9)',
          when: DateTime(2026, 11, 18),
        ),
      ];
    await pumpApp(
      tester,
      testServices(session: patientSession(), clinicalWork: work),
      location: '/patient/documents',
    );

    expect(find.text('My health history'), findsOneWidget);
    expect(
      find.textContaining('Final diagnosis: synthetic angina'),
      findsOneWidget,
    );
    await tapVisible(
      tester,
      find.byKey(const ValueKey('history-kind-Diagnosis')),
    );
    expect(find.textContaining('Final diagnosis'), findsNothing);
    expect(find.textContaining('Angina pectoris'), findsOneWidget);
  });

  group('first-dose wire format', () {
    test('a chosen time is sent as hospital clock time without a zone', () {
      expect(
        hospitalClockIso(DateTime(2026, 11, 20, 8, 5)),
        '2026-11-20T08:05',
      );
    });

    test('the preview is read with its first dose and rounds', () {
      final preview = SchedulePreview.fromJson({
        'first_dose_mode': 'next_round',
        'first_dose_at': '2026-11-20T08:00:00+05:30',
        'doses': ['2026-11-20T08:00:00+05:30', '2026-11-21T08:00:00+05:30'],
        'dose_count': 2,
        'rounds': ['08:00', '20:00'],
        'prn': false,
      });
      expect(preview.mode, FirstDose.nextRound);
      expect(preview.firstDoseAt!.toUtc(), DateTime.utc(2026, 11, 20, 2, 30));
      expect(preview.doses, hasLength(2));
      expect(preview.rounds, ['08:00', '20:00']);
      expect(FirstDose.parse('unknown'), isNull);
    });
  });
}
