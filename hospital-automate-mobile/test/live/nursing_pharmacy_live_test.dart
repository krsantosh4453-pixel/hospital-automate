// Opt-in end-to-end check of the nursing and pharmacy modules against a REAL
// backend, using the app's own API client and repositories (no fakes).
//
// Only for a throwaway test server with synthetic data: seed_demo, then a
// fixture script that gives the Ward A patient a doctor's medication order
// with one due dose and a Confirmed prescription of a stocked medicine, and
// writes {hospital, patient, other_patient, prescription, item, medicine,
// dose} to HMS_LIVE_WARD_SEED. Run:
//   HMS_LIVE_ORIGIN=http://127.0.0.1:8137 HMS_LIVE_PASSWORD=… \
//   HMS_LIVE_WARD_SEED=…/ward.json flutter test test/live/nursing_pharmacy_live_test.dart
// It writes vitals, a nursing note, one dose outcome and one dispense.
// Never point it at a server with real patients.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/config/api_config.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/auth/auth_repository.dart';
import 'package:hms_mobile/features/doctor/data/doctor_repository.dart';
import 'package:hms_mobile/features/nursing/data/nursing_models.dart';
import 'package:hms_mobile/features/nursing/data/nursing_repository.dart';
import 'package:hms_mobile/features/pharmacy/data/dispense_plan.dart';
import 'package:hms_mobile/features/pharmacy/data/pharmacy_repository.dart';

final _env = Platform.environment;
final _origin = _env['HMS_LIVE_ORIGIN'];
final _password = _env['HMS_LIVE_PASSWORD'];
final _seedPath = _env['HMS_LIVE_WARD_SEED'];

const _nurseDevice = DeviceInfo(
  deviceId: 'live-test-nurse',
  platform: 'other',
  appVersion: 'live-test',
);
const _pharmacyDevice = DeviceInfo(
  deviceId: 'live-test-pharmacist',
  platform: 'other',
  appVersion: 'live-test',
);

Matcher _apiError(ApiErrorKind kind) =>
    throwsA(isA<ApiException>().having((e) => e.kind, 'kind', kind));

void main() {
  final skip = _origin == null || _password == null || _seedPath == null
      ? 'Set HMS_LIVE_ORIGIN, HMS_LIVE_PASSWORD and HMS_LIVE_WARD_SEED to run'
      : null;

  late Map<String, Object?> seed;
  String? token;
  int? hospitalId;
  late ApiClient api;
  late ApiNursingRepository nursing;
  late ApiPharmacyRepository pharmacy;
  int seedId(String key) => seed[key]! as int;

  setUpAll(() {
    if (skip != null) return;
    seed = Map<String, Object?>.from(
      jsonDecode(File(_seedPath!).readAsStringSync()) as Map,
    );
    hospitalId = seedId('hospital');
    api = ApiClient(
      config: ApiConfig(origin: _origin!),
      accessToken: () async => token,
      hospitalId: () => hospitalId,
      log: (_) {},
    );
    nursing = ApiNursingRepository(api, ApiDoctorRepository(api));
    pharmacy = ApiPharmacyRepository(api);
  });

  Future<int> signIn(String username, DeviceInfo device, String role) async {
    final auth = ApiAuthRepository(api);
    token = (await auth.staffPasswordLogin(
      username,
      _password!,
      device,
    )).access;
    final contexts = await auth.meContexts();
    expect(contexts.accountType, AccountType.staff);
    final context = contexts.hospitals.single;
    expect(context.role, role);
    hospitalId = context.id;
    return (await auth.staffMe()).id!;
  }

  group('nurse', () {
    late NurseProfile me;

    test('1. signs in, finds own profile and today\'s ward duty', () async {
      final userId = await signIn('demo.nurse', _nurseDevice, 'Nurse');
      me = (await nursing.myProfile(hospitalId: hospitalId!, userId: userId))!;
      final duties = await nursing.wardDuties(
        nurseId: me.id,
        day: DateTime.now(),
      );
      expect(duties.map((d) => d.wardName), contains('Ward A'));
    }, skip: skip);

    test('2. sees the Ward A patient, not the Ward B one', () async {
      final admissions = await nursing.admissions();
      final patients = {for (final a in admissions) a.patientId};
      expect(patients, contains(seedId('patient')));
      expect(patients, isNot(contains(seedId('other_patient'))));
      await expectLater(
        nursing.patient(seedId('other_patient')),
        _apiError(ApiErrorKind.notFound),
      );
    }, skip: skip);

    test('3. records vitals and a note, read back from the server', () async {
      final stay = (await nursing.admissions(patientId: seedId('patient')))
          .firstWhere((a) => a.inWard);
      await nursing.addWardVitals(
        hospitalId: hospitalId!,
        patientId: seedId('patient'),
        admissionId: stay.id,
        vitals: {'bp': '118/76', 'pulse': '74', 'spo2': '98'},
      );
      final note = await nursing.addNote(
        hospitalId: hospitalId!,
        patientId: seedId('patient'),
        admissionId: stay.id,
        type: 'Progress',
        text: 'E2E live nursing note',
      );
      expect(note.nurseName, me.name, reason: 'the server sets the author');
      final assessments = await nursing.assessments(seedId('patient'));
      expect(
        assessments.any(
          (a) => a.vitals['bp'] == '118/76' && a.nurseName == me.name,
        ),
        isTrue,
      );
      final notes = await nursing.notes(patientId: seedId('patient'));
      expect(notes.any((n) => n.text == 'E2E live nursing note'), isTrue);
    }, skip: skip);

    test('4. gives the due dose once; a second attempt is refused', () async {
      final given = await nursing.recordDose(
        seedId('dose'),
        DoseAction.administer,
      );
      expect(given.status, 'Administered');
      expect(given.givenByName, me.name);
      await expectLater(
        nursing.recordDose(seedId('dose'), DoseAction.administer),
        _apiError(ApiErrorKind.validation),
      );
    }, skip: skip);
  });

  group('pharmacist', () {
    test('5. opens the prescription and sees the stock', () async {
      await signIn('demo.pharmacist', _pharmacyDevice, 'Pharmacist');
      final summary = await pharmacy.stockSummary(hospitalId!);
      expect(summary.totalMedicines, greaterThan(0));
      final queue = await pharmacy.prescriptions(
        statuses: ['Confirmed', 'Pending', 'Partially Dispensed'],
      );
      expect(queue.rows.map((rx) => rx.id), contains(seedId('prescription')));
    }, skip: skip);

    test('6. dispenses, stock drops, history and ledger record it', () async {
      final rx = await pharmacy.prescription(seedId('prescription'));
      final before = await pharmacy.medicine(seedId('medicine'));
      final item = rx.items.firstWhere((i) => i.id == seedId('item'));
      final request = DispenseRequest.build(
        prescriptionId: rx.id,
        items: rx.items,
        lines: {
          item.id!: DispenseLine(batchId: before.id, quantity: item.remaining),
        },
        stock: [before],
      );
      expect(request.isValid, isTrue);
      final result = await pharmacy.dispense(request.body!);
      expect(result.isComplete, isTrue);
      final after = await pharmacy.medicine(before.id);
      expect(after.quantity, before.quantity - item.remaining);
      final sales = await pharmacy.sales(prescriptionId: rx.id);
      expect(sales.single.quantity, item.remaining);
      final ledger = await pharmacy.stockMovements(
        hospitalId: hospitalId!,
        medicineId: before.id,
      );
      expect(ledger.first.type, 'OUT');
      // The same prescription cannot be dispensed twice.
      await expectLater(
        pharmacy.dispense(request.body!),
        _apiError(ApiErrorKind.conflict),
      );
    }, skip: skip);
  });
}
