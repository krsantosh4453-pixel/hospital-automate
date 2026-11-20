import 'package:flutter/foundation.dart';

import 'json_read.dart';

/// One medicine line (PrescriptionItemSerializer). Written by the doctor;
/// the app never changes it. [id] and [dispensedQuantity] are for the
/// pharmacy, which issues lines against the item id.
@immutable
class PrescriptionItem {
  const PrescriptionItem({
    required this.name,
    this.id,
    this.dispensedQuantity,
    this.dosage,
    this.frequency,
    this.duration,
    this.quantity,
    this.instructions,
  });

  factory PrescriptionItem.fromJson(Map<String, Object?> json) =>
      PrescriptionItem(
        id: readInt(json['id']),
        name: readText(json['name']) ?? '',
        dispensedQuantity: readInt(json['dispensed_quantity']),
        dosage: readText(json['dosage']),
        frequency: readText(json['frequency']),
        duration: readText(json['duration']),
        quantity: readInt(json['quantity']),
        instructions: readText(json['instructions']),
      );

  final int? id;
  final String name;
  final String? dosage;
  final String? frequency;
  final String? duration;
  final int? quantity;
  final String? instructions;

  /// Issued so far by the pharmacy (server-counted from its sales).
  final int? dispensedQuantity;

  /// Still to be issued: prescribed minus dispensed, never below zero.
  int get remaining {
    final owed = (quantity ?? 0) - (dispensedQuantity ?? 0);
    return owed < 0 ? 0 : owed;
  }
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
    this.patientUhid,
    this.visitId,
  });

  factory Prescription.fromJson(Map<String, Object?> json) => Prescription(
    id: readInt(json['id']) ?? 0,
    status: readText(json['status']) ?? '',
    patientId: readInt(json['patient']),
    patientName: readText(json['patient_name']),
    patientUhid: readText(json['patient_uhid']),
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

  /// Statuses counted as current: still (partly) to be collected (BUG-05).
  static const currentStatuses = {
    'Confirmed',
    'Pending',
    'Partially Dispensed',
  };

  final int id;

  /// Staff-side links; a patient sees only their own prescriptions.
  final int? patientId;
  final String? patientName;

  /// UHID at the prescription's own hospital (shown in the pharmacy queue).
  final String? patientUhid;
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
    this.enteredAt,
    this.enteredByName,
    this.verifiedAt,
    this.verifiedByName,
    this.isVerified = false,
  });

  factory LabResultData.fromJson(Map<String, Object?> json) => LabResultData(
    values: _stringMap(json['result_data']),
    text: readText(json['result_text']),
    referenceRanges: _stringMap(json['reference_ranges']),
    flags: _stringMap(json['abnormal_flags']),
    releasedAt: readDateTime(json['released_at']),
    enteredAt: readDateTime(json['entered_at']),
    enteredByName: readText(json['entered_by_name']),
    verifiedAt: readDateTime(json['verified_at']),
    verifiedByName: readText(json['verified_by_name']),
    isVerified: json['is_verified'] == true,
  );

  /// Parameter → value, as the laboratory entered it.
  final Map<String, String> values;
  final String? text;
  final Map<String, String> referenceRanges;

  /// Parameter → the laboratory's own flag (e.g. "H", "L"); never interpreted here.
  final Map<String, String> flags;
  final DateTime? releasedAt;

  /// Audit trail the laboratory keeps (staff views only).
  final DateTime? enteredAt;
  final String? enteredByName;
  final DateTime? verifiedAt;
  final String? verifiedByName;
  final bool isVerified;

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

/// How and when the sample was taken (SampleCollectionSerializer). Written
/// once by the collect step; the server never edits it afterwards.
@immutable
class LabSample {
  const LabSample({
    required this.sampleId,
    this.sampleType,
    this.containerType,
    this.collectedAt,
    this.collectedByName,
    this.notes,
    this.barcoded = false,
  });

  factory LabSample.fromJson(Map<String, Object?> json) => LabSample(
    sampleId: readText(json['sample_id']) ?? '',
    sampleType: readText(json['sample_type']),
    containerType: readText(json['container_type']),
    collectedAt: readDateTime(json['collected_at']),
    collectedByName: readText(json['collected_by_name']),
    notes: readText(json['collection_notes']),
    barcoded: json['barcoded'] == true,
  );

  final String sampleId;
  final String? sampleType;
  final String? containerType;
  final DateTime? collectedAt;
  final String? collectedByName;
  final String? notes;
  final bool barcoded;
}

/// The sample's trip to the laboratory (SampleDispatchSerializer).
@immutable
class LabDispatch {
  const LabDispatch({
    required this.status,
    this.dispatchedAt,
    this.dispatchedByName,
    this.receivedAt,
    this.receivedByName,
    this.notes,
    this.externalLab,
  });

  factory LabDispatch.fromJson(Map<String, Object?> json) => LabDispatch(
    status: readText(json['status']) ?? '',
    dispatchedAt: readDateTime(json['dispatched_at']),
    dispatchedByName: readText(json['dispatched_by_name']),
    receivedAt: readDateTime(json['received_at']),
    receivedByName: readText(json['received_by_name']),
    notes: readText(json['dispatch_notes']),
    externalLab: readText(json['external_lab']),
  );

  final String status;
  final DateTime? dispatchedAt;
  final String? dispatchedByName;
  final DateTime? receivedAt;
  final String? receivedByName;
  final String? notes;
  final String? externalLab;
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
    this.hospitalId,
    this.doctorId,
    this.collectedAt,
    this.dispatchedAt,
    this.receivedAt,
    this.processedAt,
    this.verifiedAt,
    this.sample,
    this.dispatch,
  });

  factory LabTest.fromJson(Map<String, Object?> json) {
    final result = json['lab_result'];
    final sample = json['sample_collection'];
    final dispatch = json['sample_dispatch'];
    return LabTest(
      hospitalId: readInt(json['hospital']),
      doctorId: readInt(json['doctor']),
      collectedAt: readDateTime(json['collected_at']),
      dispatchedAt: readDateTime(json['dispatched_at']),
      receivedAt: readDateTime(json['received_at']),
      processedAt: readDateTime(json['processed_at']),
      verifiedAt: readDateTime(json['verified_at']),
      sample: sample is Map
          ? LabSample.fromJson(Map<String, Object?>.from(sample))
          : null,
      dispatch: dispatch is Map
          ? LabDispatch.fromJson(Map<String, Object?>.from(dispatch))
          : null,
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

  /// Staff-side workflow detail (the laboratory pages).
  final int? hospitalId;
  final int? doctorId;
  final DateTime? collectedAt;
  final DateTime? dispatchedAt;
  final DateTime? receivedAt;
  final DateTime? processedAt;
  final DateTime? verifiedAt;
  final LabSample? sample;
  final LabDispatch? dispatch;
}

@immutable
class InvoiceLine {
  const InvoiceLine({
    required this.description,
    this.quantity,
    this.unitPrice,
    this.subtotal,
    this.taxRate,
    this.fromPharmacy = false,
  });

  factory InvoiceLine.fromJson(Map<String, Object?> json) => InvoiceLine(
    description: readText(json['description']) ?? '',
    quantity: readInt(json['quantity']),
    unitPrice: readMoney(json['unit_price']),
    subtotal: readMoney(json['subtotal']),
    taxRate: readMoney(json['tax_rate']),
    fromPharmacy: json['pharmacy_sale'] != null,
  );

  final String description;
  final int? quantity;
  final double? unitPrice;
  final double? subtotal;

  /// GST percent on this line, as the server stored it.
  final double? taxRate;

  /// A medicine line billed by the pharmacy (changes only through a return there).
  final bool fromPharmacy;
}

/// A payment or refund recorded at the hospital desk (PaymentSerializer).
@immutable
class InvoicePayment {
  const InvoicePayment({
    required this.kind,
    this.id,
    this.invoiceId,
    this.amount,
    this.method,
    this.receiptNumber,
    this.reference,
    this.paidAt,
  });

  factory InvoicePayment.fromJson(Map<String, Object?> json) => InvoicePayment(
    id: readInt(json['id']),
    invoiceId: readInt(json['invoice']),
    kind: readText(json['kind']) ?? '',
    amount: readMoney(json['amount']),
    method: readText(json['payment_method']),
    receiptNumber: readText(json['receipt_number']),
    reference: readText(json['reference']),
    paidAt: readDateTime(json['paid_at']),
  );

  static const refundKind = 'refund';

  final int? id;
  final int? invoiceId;

  /// Transaction reference typed at the desk (UPI/card slip), or a refund's reason.
  final String? reference;
  bool get isRefund => kind == refundKind;

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
    this.patientId,
    this.patientName,
    this.patientUhid,
    this.hospitalId,
    this.subtotal,
    this.discount,
    this.taxAmount,
  });

  factory Invoice.fromJson(Map<String, Object?> json) => Invoice(
    id: readInt(json['id']) ?? 0,
    patientId: readInt(json['patient']),
    patientName: readText(json['patient_name']),
    patientUhid: readText(json['patient_uhid']),
    hospitalId: readInt(json['hospital']),
    subtotal: readMoney(json['subtotal']),
    discount: readMoney(json['discount']),
    taxAmount: readMoney(json['tax_amount']) ?? readMoney(json['tax']),
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

  /// Every `Invoice.Status` value, in the order the desk filters them.
  static const statuses = ['Unpaid', 'Partially Paid', 'Paid', 'Cancelled'];
  static const cancelledStatus = 'Cancelled';

  /// Staff-side fields; all amounts are the server's.
  final int? patientId;
  final String? patientName;
  final String? patientUhid;
  final int? hospitalId;
  final double? subtotal;
  final double? discount;
  final double? taxAmount;

  bool get isCancelled => status == cancelledStatus;

  /// Net money received on this bill (payments less refunds), per the server.
  bool get hasMoneyReceived => (totalPaid ?? 0) > 0;

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
