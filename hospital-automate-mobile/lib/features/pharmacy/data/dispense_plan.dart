/// Choosing which stock batch issues each medicine on a prescription: the
/// web's `src/utils/dispenseBatches.js`, rule for rule. The server re-checks
/// names, hospital, expiry, stock and the prescribed quantity in one locked
/// transaction; this only pre-selects batches and spots gaps before sending.
library;

import 'package:flutter/foundation.dart';

import '../../patient/data/record_models.dart';
import 'pharmacy_models.dart';

String _norm(String? text) =>
    (text ?? '').trim().toLowerCase().split(RegExp(r'\s+')).join(' ');

bool _sameName(String a, String b) => _norm(a) == _norm(b);

/// Unexpired batches of [name], earliest expiry first (undated last).
List<Medicine> usableBatches(
  List<Medicine> stock,
  String name,
  DateTime today,
) {
  final batches = [
    for (final m in stock)
      if (_sameName(m.name, name) && !m.isExpired(today)) m,
  ];
  batches.sort((a, b) {
    final ea = a.expiryDate, eb = b.expiryDate;
    if (ea == null && eb == null) return 0;
    if (ea == null) return 1;
    if (eb == null) return -1;
    return ea.compareTo(eb);
  });
  return batches;
}

/// Unexpired batches of other brands with the same salt (generic name) as
/// the prescribed one. Empty when the prescribed brand's salt is not on
/// record: the server then refuses any substitute.
List<Medicine> substituteBatches(
  List<Medicine> stock,
  String name,
  DateTime today,
) {
  final salts = {
    for (final m in stock)
      if (_sameName(m.name, name) && _norm(m.genericName).isNotEmpty)
        _norm(m.genericName),
  };
  if (salts.isEmpty) return const [];
  final others = [
    for (final m in stock)
      if (!_sameName(m.name, name) && salts.contains(_norm(m.genericName))) m,
  ];
  final brands = {for (final m in others) _norm(m.name)};
  return [for (final brand in brands) ...usableBatches(others, brand, today)];
}

/// Can what is still owed be given from unexpired stock of the prescribed name?
enum Availability { done, inStock, split, short, none }

Availability availabilityOf(
  PrescriptionItem item,
  List<Medicine> stock,
  DateTime today,
) {
  final owed = item.remaining;
  if (owed == 0) return Availability.done;
  final batches = usableBatches(stock, item.name, today);
  final total = batches.fold<int>(0, (sum, b) => sum + b.quantity);
  if (total == 0) return Availability.none;
  if (batches.any((b) => b.quantity >= owed)) return Availability.inStock;
  return total >= owed ? Availability.split : Availability.short;
}

/// What the pharmacist chose for one prescribed line.
@immutable
class DispenseLine {
  const DispenseLine({this.batchId, this.quantity = 0, this.reason = ''});

  final int? batchId;
  final int quantity;

  /// Why a substitute brand is given (required for a substitute).
  final String reason;

  DispenseLine copyWith({
    int? batchId,
    bool clearBatch = false,
    int? quantity,
    String? reason,
  }) => DispenseLine(
    batchId: clearBatch ? null : (batchId ?? this.batchId),
    quantity: quantity ?? this.quantity,
    reason: reason ?? this.reason,
  );
}

/// Item id → the batch the web would pre-select (first unexpired batch that
/// covers the whole remaining quantity) and the whole remaining quantity.
Map<int, DispenseLine> defaultLines(
  List<PrescriptionItem> items,
  List<Medicine> stock,
  DateTime today,
) => {
  for (final item in items)
    if (item.id != null)
      item.id!: DispenseLine(
        batchId: usableBatches(
          stock,
          item.name,
          today,
        ).where((b) => b.quantity >= item.remaining).firstOrNull?.id,
        quantity: item.remaining,
      ),
};

/// Why a line cannot be sent yet.
enum DispenseProblemKind { tooMany, noBatch, noReason, nothingChosen }

@immutable
class DispenseProblem {
  const DispenseProblem(this.kind, {this.medicine, this.limit});

  final DispenseProblemKind kind;
  final String? medicine;
  final int? limit;

  @override
  bool operator ==(Object other) =>
      other is DispenseProblem &&
      other.kind == kind &&
      other.medicine == medicine &&
      other.limit == limit;

  @override
  int get hashCode => Object.hash(kind, medicine, limit);
}

/// The request body for `dispense-prescription/`, or the problems to show.
@immutable
class DispenseRequest {
  const DispenseRequest._({this.body, this.problems = const []});

  final Map<String, Object?>? body;
  final List<DispenseProblem> problems;

  bool get isValid => body != null;

  /// Lines with quantity 0 are left for later; anything short of the whole
  /// remaining quantity is sent as a partial dispense.
  factory DispenseRequest.build({
    required int prescriptionId,
    required List<PrescriptionItem> items,
    required Map<int, DispenseLine> lines,
    required List<Medicine> stock,
  }) {
    final problems = <DispenseProblem>[];
    final body = <Map<String, Object?>>[];
    var partial = false;
    for (final item in items) {
      final id = item.id;
      final owed = item.remaining;
      if (id == null || owed == 0) continue;
      final line = lines[id] ?? const DispenseLine();
      if (line.quantity < owed) partial = true;
      if (line.quantity <= 0) continue;
      if (line.quantity > owed) {
        problems.add(
          DispenseProblem(
            DispenseProblemKind.tooMany,
            medicine: item.name,
            limit: owed,
          ),
        );
      }
      final chosen = stock.where((m) => m.id == line.batchId).firstOrNull;
      if (chosen == null) {
        problems.add(
          DispenseProblem(DispenseProblemKind.noBatch, medicine: item.name),
        );
      }
      final substitute = chosen != null && !_sameName(chosen.name, item.name);
      if (substitute && line.reason.trim().isEmpty) {
        problems.add(
          DispenseProblem(DispenseProblemKind.noReason, medicine: item.name),
        );
      }
      body.add({
        'item': id,
        'medicine': ?line.batchId,
        'quantity': line.quantity,
        if (substitute) 'substitute_reason': line.reason.trim(),
      });
    }
    if (body.isEmpty) {
      problems.add(const DispenseProblem(DispenseProblemKind.nothingChosen));
    }
    if (problems.isNotEmpty) return DispenseRequest._(problems: problems);
    return DispenseRequest._(
      body: {'prescription': prescriptionId, 'partial': partial, 'lines': body},
    );
  }
}
