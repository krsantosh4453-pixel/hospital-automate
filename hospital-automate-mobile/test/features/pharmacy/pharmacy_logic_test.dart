import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';
import 'package:hms_mobile/features/pharmacy/data/dispense_plan.dart';
import 'package:hms_mobile/features/pharmacy/data/pharmacy_models.dart';
import 'package:hms_mobile/features/pharmacy/data/pharmacy_repository.dart';
import 'package:hms_mobile/features/pharmacy/ui/pharmacy_screen.dart';
import 'package:hms_mobile/features/pharmacy/ui/pharmacy_ui.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';

import '../../support/test_app.dart';

({ApiPharmacyRepository repo, FakeAdapter adapter}) pharmacyRepo(
  Map<String, (Object, int)> routes,
) {
  final adapter = FakeAdapter((options) async {
    final answer = routes['${options.method} ${options.uri.path}'];
    if (answer == null) return jsonBody('{"detail":"Not found."}', 404);
    return jsonBody(jsonEncode(answer.$1), answer.$2);
  });
  final api = ApiClient(
    config: testConfig,
    accessToken: () async => 'pharmacist-token',
    hospitalId: () => 7,
    adapter: adapter,
    log: (_) {},
  );
  return (repo: ApiPharmacyRepository(api), adapter: adapter);
}

const base = '/api/v1/';
final today = DateTime(2026, 11, 15);

Medicine batch(
  int id,
  String name,
  int qty, {
  DateTime? expiry,
  String? generic,
  int reorder = 10,
}) => Medicine(
  id: id,
  name: name,
  quantity: qty,
  expiryDate: expiry,
  genericName: generic,
  reorderLevel: reorder,
);

void main() {
  final t = AppLocalizationsEn();

  group('stock batches', () {
    final stock = [
      batch(1, 'Paracip 500', 50, expiry: DateTime(2027, 6, 1), generic: 'Paracetamol'),
      batch(2, 'paracip 500 ', 5, expiry: DateTime(2026, 12, 1), generic: 'Paracetamol'),
      batch(3, 'Paracip 500', 99, expiry: DateTime(2026, 11, 1), generic: 'Paracetamol'),
      batch(4, 'Paracip 500', 20, generic: 'Paracetamol'),
      batch(5, 'Calpol 500', 30, expiry: DateTime(2027, 1, 1), generic: 'paracetamol'),
      batch(6, 'Dolo 650', 30, generic: 'Paracetamol 650'),
    ];

    test('usable batches: same name, unexpired, earliest expiry first', () {
      expect(usableBatches(stock, 'PARACIP 500', today).map((m) => m.id), [2, 1, 4]);
    });

    test('substitutes share the prescribed salt and exclude the brand itself',
        () {
      expect(substituteBatches(stock, 'Paracip 500', today).map((m) => m.id), [5]);
      expect(substituteBatches(stock, 'Unknown Brand', today), isEmpty);
    });

    test('availability: in stock, split across batches, short, none, done', () {
      PrescriptionItem item(int qty, {int issued = 0}) => PrescriptionItem(
        id: 1,
        name: 'Paracip 500',
        quantity: qty,
        dispensedQuantity: issued,
      );
      expect(availabilityOf(item(10), stock, today), Availability.inStock);
      expect(availabilityOf(item(60), stock, today), Availability.split);
      expect(availabilityOf(item(500), stock, today), Availability.short);
      expect(
        availabilityOf(
          const PrescriptionItem(id: 2, name: 'Nothing', quantity: 1),
          stock,
          today,
        ),
        Availability.none,
      );
      expect(availabilityOf(item(10, issued: 10), stock, today), Availability.done);
    });

    test('defaults pick the first batch covering what is still owed', () {
      final lines = defaultLines(
        const [
          PrescriptionItem(id: 7, name: 'Paracip 500', quantity: 10, dispensedQuantity: 4),
        ],
        stock,
        today,
      );
      expect(lines[7]?.batchId, 1);
      expect(lines[7]?.quantity, 6);
    });

    test('stock filters follow the KPI rules', () {
      final low = batch(10, 'A', 3);
      final empty = batch(11, 'B', 0);
      final expired = batch(12, 'C', 4, expiry: DateTime(2026, 1, 1), reorder: 1);
      expect(matchesStockFilter(low, StockFilter.lowStock, today), isTrue);
      expect(matchesStockFilter(empty, StockFilter.lowStock, today), isFalse);
      expect(matchesStockFilter(empty, StockFilter.outOfStock, today), isTrue);
      expect(matchesStockFilter(expired, StockFilter.expired, today), isTrue);
    });
  });

  group('dispense request (web buildDispenseRequest)', () {
    final stock = [
      batch(1, 'Paracip 500', 50),
      batch(5, 'Calpol 500', 30),
    ];
    const items = [
      PrescriptionItem(id: 7, name: 'Paracip 500', quantity: 10),
      PrescriptionItem(id: 8, name: 'Calpol 500', quantity: 5, dispensedQuantity: 5),
    ];

    test('the whole remaining quantity is a full dispense', () {
      final r = DispenseRequest.build(
        prescriptionId: 3,
        items: items,
        lines: {7: const DispenseLine(batchId: 1, quantity: 10)},
        stock: stock,
      );
      expect(r.body, {
        'prescription': 3,
        'partial': false,
        'lines': [
          {'item': 7, 'medicine': 1, 'quantity': 10},
        ],
      });
    });

    test('less than owed is partial; zero lines are left for later', () {
      final r = DispenseRequest.build(
        prescriptionId: 3,
        items: const [
          PrescriptionItem(id: 7, name: 'Paracip 500', quantity: 10),
          PrescriptionItem(id: 9, name: 'Calpol 500', quantity: 2),
        ],
        lines: {
          7: const DispenseLine(batchId: 1, quantity: 4),
          9: const DispenseLine(batchId: 5, quantity: 0),
        },
        stock: stock,
      );
      expect(r.body?['partial'], isTrue);
      expect((r.body?['lines'] as List).length, 1);
    });

    test('more than owed, no batch, or nothing chosen is refused locally', () {
      final over = DispenseRequest.build(
        prescriptionId: 3,
        items: items,
        lines: {7: const DispenseLine(batchId: 1, quantity: 11)},
        stock: stock,
      );
      expect(over.isValid, isFalse);
      expect(
        over.problems,
        contains(const DispenseProblem(DispenseProblemKind.tooMany, medicine: 'Paracip 500', limit: 10)),
      );
      final noBatch = DispenseRequest.build(
        prescriptionId: 3,
        items: items,
        lines: {7: const DispenseLine(quantity: 10)},
        stock: stock,
      );
      expect(noBatch.problems.single.kind, DispenseProblemKind.noBatch);
      final nothing = DispenseRequest.build(
        prescriptionId: 3,
        items: items,
        lines: {7: const DispenseLine(batchId: 1)},
        stock: stock,
      );
      expect(nothing.problems.single.kind, DispenseProblemKind.nothingChosen);
    });

    test('a substitute needs a reason, which is sent', () {
      final missing = DispenseRequest.build(
        prescriptionId: 3,
        items: items,
        lines: {7: const DispenseLine(batchId: 5, quantity: 10)},
        stock: stock,
      );
      expect(missing.problems.single.kind, DispenseProblemKind.noReason);
      final given = DispenseRequest.build(
        prescriptionId: 3,
        items: items,
        lines: {7: const DispenseLine(batchId: 5, quantity: 10, reason: ' brand out ')},
        stock: stock,
      );
      expect((given.body?['lines'] as List).single, {
        'item': 7,
        'medicine': 5,
        'quantity': 10,
        'substitute_reason': 'brand out',
      });
    });
  });

  group('models and messages', () {
    test('a dispense result reads remaining quantities and the bill', () {
      final r = DispenseResult.fromJson({
        'prescription': 3,
        'status': 'Partially Dispensed',
        'remaining': {'7': 6, '8': 0},
        'sales': [
          {'id': 1, 'quantity': 4, 'prescription_item': 7},
        ],
        'invoice': {'invoice_number': 'INV-1', 'total': '40.00'},
      });
      expect(r.remaining, {7: 6, 8: 0});
      expect(r.isComplete, isFalse);
      expect(r.invoiceNumber, 'INV-1');
      expect(r.invoiceTotal, 40.0);
    });

    test('prescription items carry ids and what is still owed', () {
      final rx = Prescription.fromJson({
        'id': 3,
        'status': 'Confirmed',
        'patient_uhid': 'UH-1',
        'items': [
          {'id': 7, 'name': 'X', 'quantity': 10, 'dispensed_quantity': 4},
          {'id': 8, 'name': 'Y', 'quantity': 1, 'dispensed_quantity': 3},
        ],
      });
      expect(rx.patientUhid, 'UH-1');
      expect(rx.items.map((i) => (i.id, i.remaining)), [(7, 6), (8, 0)]);
    });

    test('stock summary derives in-stock from the server counts', () {
      const s = PharmacyStockSummary(totalMedicines: 40, outOfStock: 2);
      expect(s.inStock, 38);
      expect(const PharmacyStockSummary().inStock, isNull);
    });

    test('dispense errors never show the server text', () {
      expect(dispenseErrorMessage(t, const ApiException(kind: ApiErrorKind.conflict)), t.alreadyDispensed);
      expect(dispenseErrorMessage(t, const ApiException(kind: ApiErrorKind.validation)), t.dispenseRefused);
      expect(dispenseErrorMessage(t, const ApiException(kind: ApiErrorKind.network)), t.dispenseOutcomeUnknown);
    });
  });

  group('ApiPharmacyRepository', () {
    test('the queue asks for its statuses in one request, oldest first', () async {
      final s = pharmacyRepo({
        'GET ${base}clinical/prescriptions/': (
          {'count': 12, 'next': 'more', 'results': [{'id': 1, 'status': 'Confirmed'}]},
          200,
        ),
      });
      final page = await s.repo.prescriptions(
        statuses: PharmacyQueue.toDispense,
        search: ' UH-1 ',
        oldestFirst: true,
      );
      expect(page.count, 12);
      expect(page.rows.single.id, 1);
      expect(s.adapter.requests.single.uri.queryParameters, {
        'status': 'Confirmed,Pending,Partially Dispensed',
        'search': 'UH-1',
        'order': 'oldest',
      });
    });

    test('the stock ledger always names the hospital', () async {
      final s = pharmacyRepo({
        'GET ${base}procurement/stock-transactions/': (
          {'count': 0, 'next': null, 'results': []},
          200,
        ),
      });
      await s.repo.stockMovements(hospitalId: 7, medicineId: 4);
      expect(s.adapter.requests.single.uri.queryParameters, {'hospital': '7', 'medicine': '4'});
    });

    test('a dispense posts the built body once, with no retry', () async {
      final s = pharmacyRepo({
        'POST ${base}pharmacy-sales/dispense-prescription/': (
          {'detail': 'This prescription has already been dispensed.'},
          409,
        ),
      });
      await expectLater(
        s.repo.dispense({'prescription': 3, 'partial': false, 'lines': []}),
        throwsA(isA<ApiException>().having((e) => e.kind, 'kind', ApiErrorKind.conflict)),
      );
      expect(s.adapter.requests, hasLength(1));
    });

    test('stock counts come from the pharmacy KPI endpoint', () async {
      final s = pharmacyRepo({
        'GET ${base}reports/analytics/pharmacy/': (
          {'total_medicines': 40, 'low_stock': 3, 'out_of_stock': 2, 'expiring_soon': 1, 'expired': 1},
          200,
        ),
      });
      final summary = await s.repo.stockSummary(7);
      expect([summary.totalMedicines, summary.lowStock, summary.outOfStock, summary.expired], [40, 3, 2, 1]);
      expect(s.adapter.requests.single.uri.queryParameters['hospital'], '7');
    });
  });
}
