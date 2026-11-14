import 'package:flutter/foundation.dart';

import 'json_read.dart';

/// One medicine line (PrescriptionItemSerializer). Written by the doctor;
/// the app only displays it.
@immutable
class PrescriptionItem {
  const PrescriptionItem({
    required this.name,
    this.dosage,
    this.frequency,
    this.duration,
    this.quantity,
    this.instructions,
  });

  factory PrescriptionItem.fromJson(Map<String, Object?> json) =>
      PrescriptionItem(
        name: readText(json['name']) ?? '',
        dosage: readText(json['dosage']),
        frequency: readText(json['frequency']),
        duration: readText(json['duration']),
        quantity: readInt(json['quantity']),
        instructions: readText(json['instructions']),
      );

  final String name;
  final String? dosage;
  final String? frequency;
  final String? duration;
  final int? quantity;
  final String? instructions;
}

/// `GET clinical/prescriptions/` (PrescriptionSerializer). The serializer has
/// no diagnosis field, so none is shown.
@immutable
class Prescription {
  const Prescription({
    required this.id,
    required this.status,
    this.createdAt,
    this.dispensedAt,
    this.doctorName,
    this.hospitalName,
    this.visitLabel,
    this.items = const [],
    this.patientId,
    this.patientName,
    this.visitId,
  });

  factory Prescription.fromJson(Map<String, Object?> json) => Prescription(
    id: readInt(json['id']) ?? 0,
    status: readText(json['status']) ?? '',
    patientId: readInt(json['patient']),
    patientName: readText(json['patient_name']),
    visitId: readInt(json['visit']),
    createdAt: readDateTime(json['created_at']),
    dispensedAt: readDateTime(json['dispensed_at']),
    doctorName:
        readText(json['doctor_name']) ??
        readText(json['original_prescriber_name']),
    hospitalName: readText(json['hospital_name']),
    visitLabel: readText(json['visit_label']),
    items: [
      for (final row in readRows(json['items'])) PrescriptionItem.fromJson(row),
    ],
  );

  /// Statuses the web portal counts as current.
  static const currentStatuses = {'Confirmed', 'Pending'};

  final int id;

  /// Staff-side links; a patient sees only their own prescriptions.
  final int? patientId;
  final String? patientName;
  final int? visitId;
  final String status;
  final DateTime? createdAt;
  final DateTime? dispensedAt;
  final String? doctorName;
  final String? hospitalName;
  final String? visitLabel;
  final List<PrescriptionItem> items;

  bool get isCurrent => currentStatuses.contains(status);
}

/// The released result of a lab test (LabResultSerializer).
@immutable
class LabResultData {
  const LabResultData({
    this.values = const {},
    this.text,
    this.referenceRanges = const {},
    this.flags = const {},
    this.releasedAt,
  });

  factory LabResultData.fromJson(Map<String, Object?> json) => LabResultData(
    values: _stringMap(json['result_data']),
    text: readText(json['result_text']),
    referenceRanges: _stringMap(json['reference_ranges']),
    flags: _stringMap(json['abnormal_flags']),
    releasedAt: readDateTime(json['released_at']),
  );

  /// Parameter → value, as the laboratory entered it.
  final Map<String, String> values;
  final String? text;
  final Map<String, String> referenceRanges;

  /// Parameter → the laboratory's own flag (e.g. "H", "L"); never interpreted here.
  final Map<String, String> flags;
  final DateTime? releasedAt;

  bool get isEmpty => values.isEmpty && text == null;

  static Map<String, String> _stringMap(Object? value) => {
    if (value is Map)
      for (final entry in value.entries)
        if (entry.value != null && '${entry.value}'.trim().isNotEmpty)
          '${entry.key}': _display(entry.value),
  };

  static String _display(Object? value) => switch (value) {
    final Map m => m.values.where((v) => v != null).join(' '),
    final List l => l.join(', '),
    _ => '$value',
  };
}

/// `GET laboratory/tests/`. Patients receive only tests the laboratory has
/// verified and released (laboratory/views.py), never pending ones.
@immutable
class LabTest {
  const LabTest({
    required this.id,
    required this.name,
    required this.status,
    this.priority,
    this.testDate,
    this.releasedAt,
    this.doctorName,
    this.hospitalName,
    this.result,
    this.patientId,
    this.patientName,
    this.visitId,
  });

  factory LabTest.fromJson(Map<String, Object?> json) {
    final result = json['lab_result'];
    return LabTest(
      id: readInt(json['id']) ?? 0,
      patientId: readInt(json['patient']),
      patientName: readText(json['patient_name']),
      visitId: readInt(json['visit']),
      name: readText(json['name']) ?? '',
      status: readText(json['status']) ?? '',
      priority: readText(json['priority']),
      testDate: readDateTime(json['test_date']),
      releasedAt: readDateTime(json['released_at']),
      doctorName: readText(json['doctor_name']),
      hospitalName: readText(json['hospital_name']),
      result: result is Map
          ? LabResultData.fromJson(Map<String, Object?>.from(result))
          : (readText(json['result']) == null
                ? null
                : LabResultData(text: readText(json['result']))),
    );
  }

  final int id;
  final String name;
  final String status;

  /// Staff-side links (the doctor's lab list and orders).
  final int? patientId;
  final String? patientName;
  final int? visitId;
  final String? priority;
  final DateTime? testDate;
  final DateTime? releasedAt;
  final String? doctorName;
  final String? hospitalName;
  final LabResultData? result;
}

@immutable
class InvoiceLine {
  const InvoiceLine({
    required this.description,
    this.quantity,
    this.unitPrice,
    this.subtotal,
  });

  factory InvoiceLine.fromJson(Map<String, Object?> json) => InvoiceLine(
    description: readText(json['description']) ?? '',
    quantity: readInt(json['quantity']),
    unitPrice: readMoney(json['unit_price']),
    subtotal: readMoney(json['subtotal']),
  );

  final String description;
  final int? quantity;
  final double? unitPrice;
  final double? subtotal;
}

/// A payment or refund recorded at the hospital desk (PaymentSerializer).
@immutable
class InvoicePayment {
  const InvoicePayment({
    required this.kind,
    this.amount,
    this.method,
    this.receiptNumber,
    this.paidAt,
  });

  factory InvoicePayment.fromJson(Map<String, Object?> json) => InvoicePayment(
    kind: readText(json['kind']) ?? '',
    amount: readMoney(json['amount']),
    method: readText(json['payment_method']),
    receiptNumber: readText(json['receipt_number']),
    paidAt: readDateTime(json['paid_at']),
  );

  final String kind;
  final double? amount;
  final String? method;
  final String? receiptNumber;
  final DateTime? paidAt;
}

/// `GET billing/invoices/` (InvoiceSerializer). Totals are the server's.
@immutable
class Invoice {
  const Invoice({
    required this.id,
    required this.status,
    this.invoiceNumber,
    this.createdAt,
    this.hospitalName,
    this.totalAmount,
    this.totalPaid,
    this.balanceDue,
    this.items = const [],
    this.payments = const [],
  });

  factory Invoice.fromJson(Map<String, Object?> json) => Invoice(
    id: readInt(json['id']) ?? 0,
    status: readText(json['status']) ?? '',
    invoiceNumber: readText(json['invoice_number']),
    createdAt: readDateTime(json['created_at']),
    hospitalName: readText(json['hospital_name']),
    totalAmount: readMoney(json['total_amount']) ?? readMoney(json['total']),
    totalPaid: readMoney(json['total_paid']),
    balanceDue: readMoney(json['balance_due']),
    items: [
      for (final row in readRows(json['items'])) InvoiceLine.fromJson(row),
    ],
    payments: [
      for (final row in readRows(json['payments']))
        InvoicePayment.fromJson(row),
    ],
  );

  /// `Invoice.Status` values with money still owed.
  static const owingStatuses = {'Unpaid', 'Partially Paid'};

  final int id;
  final String status;
  final String? invoiceNumber;
  final DateTime? createdAt;
  final String? hospitalName;
  final double? totalAmount;
  final double? totalPaid;
  final double? balanceDue;
  final List<InvoiceLine> items;
  final List<InvoicePayment> payments;

  bool get hasBalance =>
      (balanceDue ?? 0) > 0 ||
      (balanceDue == null && owingStatuses.contains(status));
}

/// `GET encounters/queue-tokens/` (QueueTokenSerializer). Wait figures are
/// the server's estimates, never a promised time.
@immutable
class QueueToken {
  const QueueToken({
    required this.id,
    required this.tokenNumber,
    required this.status,
    this.tokenDate,
    this.doctorName,
    this.department,
    this.hospitalName,
    this.queuePosition,
    this.estimatedWaitMinutes,
    this.estimatedStart,
    this.lastUpdated,
    this.patientId,
    this.patientName,
    this.visitId,
    this.appointmentId,
  });

  factory QueueToken.fromJson(Map<String, Object?> json) => QueueToken(
    id: readInt(json['id']) ?? 0,
    tokenNumber: readInt(json['token_number']),
    status: readText(json['status']) ?? '',
    patientId: readInt(json['patient']),
    patientName: readText(json['patient_name']),
    visitId: readInt(json['visit']),
    appointmentId: readInt(json['appointment']),
    tokenDate: readDate(json['token_date']),
    doctorName: readText(json['doctor_name']),
    department: readText(json['department']),
    hospitalName: readText(json['hospital_name']),
    queuePosition: readInt(json['queue_position']),
    estimatedWaitMinutes: readInt(json['estimated_wait_minutes']),
    estimatedStart: readDateTime(json['estimated_start_time']),
    lastUpdated: readDateTime(json['last_updated']),
  );

  /// Tokens still in the queue (web PatientQueue `ACTIVE`).
  static const activeStatuses = {'Waiting', 'Called', 'Acknowledged', 'Ready'};

  /// Tokens that are over.
  static const closedStatuses = {'Completed', 'Cancelled', 'No Show'};

  final int id;
  final int? tokenNumber;
  final String status;

  /// Staff-side links (the doctor's queue opens the patient and the visit).
  final int? patientId;
  final String? patientName;
  final int? visitId;
  final int? appointmentId;
  final DateTime? tokenDate;
  final String? doctorName;
  final String? department;
  final String? hospitalName;
  final int? queuePosition;
  final int? estimatedWaitMinutes;
  final DateTime? estimatedStart;
  final DateTime? lastUpdated;

  bool get isActive => activeStatuses.contains(status);
  bool get isOpen => !closedStatuses.contains(status);
}

/// `GET notifications/notifications/` (NotificationSerializer).
@immutable
class PatientNotification {
  const PatientNotification({
    required this.id,
    required this.title,
    required this.message,
    required this.type,
    required this.isRead,
    this.createdAt,
  });

  factory PatientNotification.fromJson(Map<String, Object?> json) =>
      PatientNotification(
        id: readInt(json['id']) ?? 0,
        title: readText(json['title']) ?? '',
        message: readText(json['message']) ?? '',
        type: readText(json['notification_type']) ?? 'General',
        isRead: json['is_read'] == true,
        createdAt: readDateTime(json['created_at']),
      );

  final int id;
  final String title;
  final String message;

  /// `NotificationEvent` value (e.g. `patient_called`) or `General`.
  final String type;
  final bool isRead;
  final DateTime? createdAt;

  PatientNotification markedRead() => PatientNotification(
    id: id,
    title: title,
    message: message,
    type: type,
    isRead: true,
    createdAt: createdAt,
  );
}

/// `GET documents/` row: metadata only; the file is fetched separately.
@immutable
class PatientDocument {
  const PatientDocument({
    required this.id,
    required this.title,
    this.folder,
    this.fileSize,
    this.uploadedAt,
  });

  factory PatientDocument.fromJson(Map<String, Object?> json) =>
      PatientDocument(
        id: readInt(json['id']) ?? 0,
        title: readText(json['title']) ?? '',
        folder: readText(json['folder']),
        fileSize: readInt(json['file_size']),
        uploadedAt: readDateTime(json['uploaded_at']),
      );

  final int id;
  final String title;
  final String? folder;
  final int? fileSize;
  final DateTime? uploadedAt;
}
