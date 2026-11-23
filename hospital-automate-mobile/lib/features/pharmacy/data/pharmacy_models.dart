import 'package:flutter/foundation.dart';

import '../../patient/data/json_read.dart';

/// One stock batch of a medicine (`pharmacy/`, MedicineSerializer). Each
/// batch is its own row; the quantity is the server's, never computed here.
@immutable
class Medicine {
  const Medicine({
    required this.id,
    required this.name,
    required this.quantity,
    this.genericName,
    this.category,
    this.batch,
    this.price,
    this.mrp,
    this.expiryDate,
    this.status,
    this.manufacturer,
    this.unit,
    this.reorderLevel,
    this.drugSchedule,
    this.supplierName,
  });

  factory Medicine.fromJson(Map<String, Object?> json) => Medicine(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    quantity: readInt(json['quantity']) ?? 0,
    genericName: readText(json['generic_name']),
    category: readText(json['category']),
    batch: readText(json['batch']),
    price: readMoney(json['price']),
    mrp: readMoney(json['mrp']),
    expiryDate: readDate(json['expiry_date']),
    status: readText(json['status']),
    manufacturer: readText(json['manufacturer']),
    unit: readText(json['unit']),
    reorderLevel: readInt(json['reorder_level']),
    drugSchedule: readText(json['drug_schedule']),
    supplierName: readText(json['supplier_name']),
  );

  final int id;
  final String name;
  final int quantity;
  final String? genericName;
  final String? category;
  final String? batch;
  final double? price;
  final double? mrp;
  final DateTime? expiryDate;
  final String? status;
  final String? manufacturer;
  final String? unit;
  final int? reorderLevel;

  /// "", H, H1, X or NDPS (Drugs and Cosmetics Rules).
  final String? drugSchedule;
  final String? supplierName;

  /// The server refuses to dispense a batch that expired before [today].
  bool isExpired(DateTime today) =>
      expiryDate != null && expiryDate!.isBefore(today);

  bool get isOutOfStock => quantity == 0;

  /// The same rule as the pharmacy KPIs (reports/services.py): at or below
  /// the reorder level, but not empty.
  bool get isLowStock =>
      quantity > 0 && reorderLevel != null && quantity <= reorderLevel!;
}

/// Stock levels the pharmacy KPI endpoint counts (`reports/analytics/pharmacy/`).
@immutable
class PharmacyStockSummary {
  const PharmacyStockSummary({
    this.totalMedicines,
    this.lowStock,
    this.outOfStock,
    this.expiringSoon,
    this.expired,
  });

  factory PharmacyStockSummary.fromJson(Map<String, Object?> json) =>
      PharmacyStockSummary(
        totalMedicines: readInt(json['total_medicines']),
        lowStock: readInt(json['low_stock']),
        outOfStock: readInt(json['out_of_stock']),
        expiringSoon: readInt(json['expiring_soon']),
        expired: readInt(json['expired']),
      );

  /// Medicine batches on record at this hospital.
  final int? totalMedicines;
  final int? lowStock;
  final int? outOfStock;

  /// In stock and expiring within 30 days.
  final int? expiringSoon;

  /// Expired but still holding stock.
  final int? expired;

  int? get inStock => totalMedicines == null || outOfStock == null
      ? null
      : totalMedicines! - outOfStock!;
}

/// A pharmacy sale (`pharmacy-sales/`, SaleSerializer): one batch issued.
@immutable
class PharmacySale {
  const PharmacySale({
    required this.id,
    required this.quantity,
    this.medicineId,
    this.medicineName,
    this.patientName,
    this.prescriptionId,
    this.prescriptionItemId,
    this.total,
    this.substitutedFor,
    this.returnedQuantity,
    this.invoiceNumber,
    this.createdAt,
  });

  factory PharmacySale.fromJson(Map<String, Object?> json) => PharmacySale(
    id: readInt(json['id']) ?? 0,
    quantity: readInt(json['quantity']) ?? 0,
    medicineId: readInt(json['medicine']),
    medicineName: readText(json['medicine_name']),
    patientName: readText(json['patient_name']),
    prescriptionId: readInt(json['prescription']),
    prescriptionItemId: readInt(json['prescription_item']),
    total: readMoney(json['total']),
    substitutedFor: readText(json['substituted_for']),
    returnedQuantity: readInt(json['returned_quantity']),
    invoiceNumber: readText(json['invoice_number']),
    createdAt: readDateTime(json['created_at']),
  );

  final int id;
  final int quantity;
  final int? medicineId;
  final String? medicineName;
  final String? patientName;
  final int? prescriptionId;
  final int? prescriptionItemId;
  final double? total;

  /// Set when a same-salt brand was given instead of the prescribed one.
  final String? substitutedFor;
  final int? returnedQuantity;
  final String? invoiceNumber;
  final DateTime? createdAt;
}

/// One row of the append-only stock ledger (`procurement/stock-transactions/`).
@immutable
class StockMovement {
  const StockMovement({
    required this.id,
    required this.type,
    required this.quantity,
    this.medicineId,
    this.medicineName,
    this.reason,
    this.reference,
    this.createdAt,
  });

  factory StockMovement.fromJson(Map<String, Object?> json) => StockMovement(
    id: readInt(json['id']) ?? 0,
    type: readText(json['transaction_type']) ?? '',
    quantity: readInt(json['quantity']) ?? 0,
    medicineId: readInt(json['medicine']),
    medicineName: readText(json['medicine_name']),
    reason: readText(json['reason']),
    reference: readText(json['reference']),
    createdAt: readDateTime(json['created_at']),
  );

  /// IN, OUT or ADJUST (StockTransaction.TYPE_CHOICES).
  final String type;
  final int id;
  final int quantity;
  final int? medicineId;
  final String? medicineName;
  final String? reason;
  final String? reference;
  final DateTime? createdAt;
}

/// What the server answered to `pharmacy-sales/dispense-prescription/`.
@immutable
class DispenseResult {
  const DispenseResult({
    required this.prescriptionId,
    required this.status,
    required this.remaining,
    required this.sales,
    this.invoiceNumber,
    this.invoiceTotal,
  });

  factory DispenseResult.fromJson(Map<String, Object?> json) {
    final invoice = asMap(json['invoice']);
    return DispenseResult(
      prescriptionId: readInt(json['prescription']) ?? 0,
      status: readText(json['status']) ?? '',
      remaining: {
        for (final entry in asMap(json['remaining']).entries)
          if (int.tryParse(entry.key) != null)
            int.parse(entry.key): readInt(entry.value) ?? 0,
      },
      sales: [
        for (final row in readRows(json['sales'])) PharmacySale.fromJson(row),
      ],
      invoiceNumber: readText(invoice['invoice_number']),
      invoiceTotal: readMoney(invoice['total']),
    );
  }

  final int prescriptionId;
  final String status;

  /// Prescription item id → quantity still to be issued.
  final Map<int, int> remaining;
  final List<PharmacySale> sales;

  /// The patient bill the medicines were charged on, when there is one.
  final String? invoiceNumber;
  final double? invoiceTotal;

  bool get isComplete => remaining.values.every((left) => left == 0);
}

/// Prescription statuses on the pharmacy queue (web PrescriptionQueue.jsx).
abstract final class PharmacyQueue {
  static const toDispense = ['Confirmed', 'Pending', 'Partially Dispensed'];
  static const awaitingVerification = ['Pending Verification'];
  static const dispensed = ['Dispensed'];

  /// Statuses the server refuses to dispense (pharmacy/dispensing.py).
  static const blocked = {'Cancelled', 'Pending Verification'};
}
