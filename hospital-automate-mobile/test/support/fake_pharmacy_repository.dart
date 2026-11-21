import 'dart:async';

import 'package:hms_mobile/features/patient/data/record_models.dart';
import 'package:hms_mobile/features/pharmacy/data/pharmacy_models.dart';
import 'package:hms_mobile/features/pharmacy/data/pharmacy_repository.dart';

/// In-memory [PharmacyRepository] for widget tests. Synthetic data only.
/// [dispenseResult] answers a dispense (or set [writeError]); [gate] holds a
/// dispense open so a test can tap again while it is in flight.
class FakePharmacyRepository implements PharmacyRepository {
  FakePharmacyRepository({
    this.summary = const PharmacyStockSummary(
      totalMedicines: 40,
      lowStock: 3,
      outOfStock: 2,
      expiringSoon: 1,
      expired: 1,
    ),
    this.stock = const [],
    this.prescriptionRows = const [],
    this.saleRows = const [],
    this.movementRows = const [],
    this.dispenseResult,
  });

  PharmacyStockSummary summary;
  List<Medicine> stock;
  List<Prescription> prescriptionRows;
  List<PharmacySale> saleRows;
  List<StockMovement> movementRows;
  DispenseResult? dispenseResult;

  Object? readError;
  Object? writeError;
  Completer<void>? gate;

  final List<Map<String, Object?>> dispensed = [];
  final List<List<String>> queueRequests = [];

  Future<T> _read<T>(T value) async {
    if (readError != null) throw readError!;
    return value;
  }

  @override
  Future<PharmacyStockSummary> stockSummary(int hospitalId) => _read(summary);

  @override
  Future<List<Medicine>> medicines({String? search}) => _read([
    for (final m in stock)
      if (search == null ||
          m.name.toLowerCase().contains(search.trim().toLowerCase()))
        m,
  ]);

  @override
  Future<Medicine> medicine(int id) =>
      _read(stock.firstWhere((m) => m.id == id));

  @override
  Future<Counted<Prescription>> prescriptions({
    required List<String> statuses,
    String? search,
    bool oldestFirst = false,
  }) {
    queueRequests.add(statuses);
    final rows = [
      for (final rx in prescriptionRows)
        if (statuses.contains(rx.status)) rx,
    ];
    return _read((rows: rows, count: rows.length));
  }

  @override
  Future<Prescription> prescription(int id) =>
      _read(prescriptionRows.firstWhere((rx) => rx.id == id));

  @override
  Future<List<PharmacySale>> sales({int? prescriptionId}) => _read([
    for (final s in saleRows)
      if (prescriptionId == null || s.prescriptionId == prescriptionId) s,
  ]);

  @override
  Future<List<StockMovement>> stockMovements({
    required int hospitalId,
    int? medicineId,
  }) => _read([
    for (final m in movementRows)
      if (medicineId == null || m.medicineId == medicineId) m,
  ]);

  @override
  Future<DispenseResult> dispense(Map<String, Object?> body) async {
    dispensed.add(body);
    await gate?.future;
    if (writeError != null) throw writeError!;
    return dispenseResult!;
  }
}
