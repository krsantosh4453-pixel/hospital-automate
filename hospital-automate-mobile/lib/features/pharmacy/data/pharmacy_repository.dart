import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../patient/data/json_read.dart';
import '../../patient/data/record_models.dart';
import 'pharmacy_models.dart';

/// A page of rows and the server's total count.
typedef Counted<T> = ({List<T> rows, int? count});

/// Pharmacy work at the acting hospital (`X-Hospital-ID`). Stock is only
/// read here: the server changes it, in the same transaction as each sale,
/// and records every change in the stock ledger. Stock corrections are the
/// store's (Admin, Hospital Manager, Inventory Staff), not the pharmacy's.
abstract interface class PharmacyRepository {
  /// Stock counts from `reports/analytics/pharmacy/`.
  Future<PharmacyStockSummary> stockSummary(int hospitalId);

  /// Every batch, optionally narrowed by name.
  Future<List<Medicine>> medicines({String? search});
  Future<Medicine> medicine(int id);

  /// The first page of the queue in [statuses], with the total count.
  Future<Counted<Prescription>> prescriptions({
    required List<String> statuses,
    String? search,
    bool oldestFirst = false,
  });
  Future<Prescription> prescription(int id);

  /// Sales of one prescription, or the most recent sales.
  Future<List<PharmacySale>> sales({int? prescriptionId});

  /// The stock ledger, newest first; for one medicine when [medicineId].
  Future<List<StockMovement>> stockMovements({
    required int hospitalId,
    int? medicineId,
  });

  /// Issues medicines in one server transaction: every line, or none.
  Future<DispenseResult> dispense(Map<String, Object?> body);
}

class ApiPharmacyRepository implements PharmacyRepository {
  ApiPharmacyRepository(this._api);

  final ApiClient _api;

  @override
  Future<PharmacyStockSummary> stockSummary(int hospitalId) => _api.get(
    'reports/analytics/pharmacy/',
    query: {'hospital': hospitalId},
    decode: (json) => PharmacyStockSummary.fromJson(asMap(json)),
  );

  @override
  Future<List<Medicine>> medicines({String? search}) async => [
    for (final row in await getAllRows(
      _api,
      'pharmacy/',
      query: {
        if (search != null && search.trim().isNotEmpty) 'search': search.trim(),
      },
    ))
      Medicine.fromJson(row),
  ];

  @override
  Future<Medicine> medicine(int id) => _api.get(
    'pharmacy/$id/',
    decode: (json) => Medicine.fromJson(asMap(json)),
  );

  @override
  Future<Counted<Prescription>> prescriptions({
    required List<String> statuses,
    String? search,
    bool oldestFirst = false,
  }) async {
    final page = await getFirstPage(
      _api,
      'clinical/prescriptions/',
      query: {
        'status': statuses.join(','),
        if (search != null && search.trim().isNotEmpty) 'search': search.trim(),
        if (oldestFirst) 'order': 'oldest',
      },
    );
    return (
      rows: [for (final row in page.rows) Prescription.fromJson(row)],
      count: page.count,
    );
  }

  @override
  Future<Prescription> prescription(int id) => _api.get(
    'clinical/prescriptions/$id/',
    decode: (json) => Prescription.fromJson(asMap(json)),
  );

  @override
  Future<List<PharmacySale>> sales({int? prescriptionId}) async {
    final page = await getFirstPage(
      _api,
      'pharmacy-sales/',
      query: {'prescription': ?prescriptionId},
    );
    return [for (final row in page.rows) PharmacySale.fromJson(row)];
  }

  @override
  Future<List<StockMovement>> stockMovements({
    required int hospitalId,
    int? medicineId,
  }) async {
    // The ledger answers only with an explicit ?hospital= (procurement/views.py).
    final page = await getFirstPage(
      _api,
      'procurement/stock-transactions/',
      query: {'hospital': hospitalId, 'medicine': ?medicineId},
    );
    final rows = [for (final row in page.rows) StockMovement.fromJson(row)];
    rows.sort(
      (a, b) =>
          (b.createdAt ?? DateTime(0)).compareTo(a.createdAt ?? DateTime(0)),
    );
    return rows;
  }

  @override
  Future<DispenseResult> dispense(Map<String, Object?> body) => _api.post(
    'pharmacy-sales/dispense-prescription/',
    body: body,
    decode: (json) => DispenseResult.fromJson(asMap(json)),
  );
}
