import 'package:flutter/foundation.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../doctor/data/doctor_models.dart';
import '../../patient/data/json_read.dart';
import 'ipd_models.dart';

/// Prompt 3: the clinical work the web did alone — allergies, admitting,
/// ward medication orders, the discharge plan and summary, the stay's final
/// bill — and the patient's own history. The server checks every request.

/// "Unknown" (not asked) is never "No known allergies" (asked: none).
abstract final class AllergyStatus {
  static const unknown = 'Unknown';
  static const none = 'No known allergies';
  static const recorded = 'Has allergies';
}

@immutable
class AllergyRecord {
  const AllergyRecord({
    required this.id,
    required this.name,
    this.reaction,
    this.severity,
    this.category,
  });

  factory AllergyRecord.fromJson(Map<String, Object?> json) => AllergyRecord(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    reaction: readText(json['reaction']),
    severity: readText(json['severity']),
    category: readText(json['category']),
  );

  final int id;
  final String name;
  final String? reaction;
  final String? severity;
  final String? category;
}

/// A medicine on one of the patient's prescriptions (a ward order source).
@immutable
class PrescribedMedicine {
  const PrescribedMedicine({
    required this.id,
    required this.prescriptionId,
    required this.name,
    this.dosage,
    this.frequency,
  });

  final int id;
  final int prescriptionId;
  final String name;
  final String? dosage;
  final String? frequency;
}

/// `nurses/mar/`: a doctor's ward medication order. Doses are given and
/// recorded by nurses separately; an order is never a dose given.
@immutable
class MedicationOrder {
  const MedicationOrder({
    required this.id,
    required this.medicineName,
    required this.dose,
    required this.route,
    required this.frequency,
    required this.isActive,
    this.admissionId,
    this.startDate,
    this.endDate,
    this.instructions,
    this.orderedByName,
    this.prnMinIntervalMinutes,
    this.prnMaxDosesPer24h,
  });

  factory MedicationOrder.fromJson(Map<String, Object?> json) =>
      MedicationOrder(
        id: readInt(json['id']) ?? 0,
        admissionId: readInt(json['admission']),
        medicineName: readText(json['medicine_name']) ?? '',
        dose: readText(json['dose']) ?? '',
        route: readText(json['route']) ?? '',
        frequency: readText(json['frequency']) ?? '',
        isActive: json['is_active'] == true,
        startDate: readDate(json['start_date']),
        endDate: readDate(json['end_date']),
        instructions: readText(json['instructions']),
        orderedByName: readText(json['ordered_by_name']),
        prnMinIntervalMinutes: readInt(json['prn_min_interval_minutes']),
        prnMaxDosesPer24h: readInt(json['prn_max_doses_per_24h']),
      );

  final int id;
  final int? admissionId;
  final String medicineName;
  final String dose;
  final String route;
  final String frequency;
  final bool isActive;
  final DateTime? startDate;
  final DateTime? endDate;
  final String? instructions;
  final String? orderedByName;

  /// H-10: limits on an as-needed order; null means no limit.
  final int? prnMinIntervalMinutes;
  final int? prnMaxDosesPer24h;
}

/// A new ward order from one prescribed medicine.
@immutable
class MedicationOrderDraft {
  const MedicationOrderDraft({
    required this.medicine,
    required this.dose,
    required this.route,
    required this.frequency,
    required this.startDate,
    this.endDate,
    this.instructions = '',
    this.firstDose,
    this.firstDoseAt,
    this.prnMinIntervalMinutes,
    this.prnMaxDosesPer24h,
  });

  final PrescribedMedicine medicine;
  final String dose;
  final String route;
  final String frequency;
  final DateTime startDate;
  final DateTime? endDate;
  final String instructions;

  /// When the first dose falls; null lets the server apply its safe default
  /// (the next medication round for once-daily orders).
  final FirstDose? firstDose;

  /// The hospital-clock time for [FirstDose.at].
  final DateTime? firstDoseAt;

  /// H-10: optional limits, sent only for an as-needed (PRN/SOS) order.
  final int? prnMinIntervalMinutes;
  final int? prnMaxDosesPer24h;
}

/// How the first dose of a ward order is placed (nurses/scheduling.py).
enum FirstDose {
  nextRound('next_round'),
  now('now'),
  at('at');

  const FirstDose(this.wire);
  final String wire;

  static FirstDose? parse(Object? value) {
    for (final mode in values) {
      if (mode.wire == value) return mode;
    }
    return null;
  }
}

/// `nurses/mar/schedule-preview/`: what the doctor reviews before ordering.
@immutable
class SchedulePreview {
  const SchedulePreview({
    this.mode,
    this.firstDoseAt,
    this.doses = const [],
    this.doseCount = 0,
    this.rounds = const [],
    this.prn = false,
  });

  factory SchedulePreview.fromJson(Map<String, Object?> json) =>
      SchedulePreview(
        mode: FirstDose.parse(json['first_dose_mode']),
        firstDoseAt: readDateTime(json['first_dose_at']),
        doses: List.unmodifiable([
          for (final d
              in json['doses'] is List ? json['doses']! as List : const [])
            ?readDateTime(d),
        ]),
        doseCount: readInt(json['dose_count']) ?? 0,
        rounds: List.unmodifiable([
          for (final r
              in json['rounds'] is List ? json['rounds']! as List : const [])
            '$r',
        ]),
        prn: json['prn'] == true,
      );

  final FirstDose? mode;
  final DateTime? firstDoseAt;
  final List<DateTime> doses;
  final int doseCount;

  /// The hospital's configured round times, e.g. `08:00`.
  final List<String> rounds;

  /// As needed: nothing is scheduled.
  final bool prn;
}

/// `YYYY-MM-DDTHH:MM` without a zone: the server reads it as hospital time.
String hospitalClockIso(DateTime value) =>
    '${isoDay(value)}T${value.hour.toString().padLeft(2, '0')}:'
    '${value.minute.toString().padLeft(2, '0')}';

Map<String, Object?> _firstDoseBody(MedicationOrderDraft draft) => {
  'first_dose': draft.firstDose?.wire,
  if (draft.firstDose == FirstDose.at && draft.firstDoseAt != null)
    'first_dose_at': hospitalClockIso(draft.firstDoseAt!),
};

@immutable
class DischargePlanRecord {
  const DischargePlanRecord({
    required this.id,
    this.instructions = '',
    this.medicationsReconciled = false,
    this.patientCounselled = false,
    this.followUpArranged = false,
    this.documentsHandedOver = false,
  });

  factory DischargePlanRecord.fromJson(Map<String, Object?> json) =>
      DischargePlanRecord(
        id: readInt(json['id']) ?? 0,
        instructions: readText(json['instructions']) ?? '',
        medicationsReconciled: json['medications_reconciled'] == true,
        patientCounselled: json['patient_counselled'] == true,
        followUpArranged: json['follow_up_arranged'] == true,
        documentsHandedOver: json['documents_handed_over'] == true,
      );

  final int id;
  final String instructions;
  final bool medicationsReconciled;
  final bool patientCounselled;
  final bool followUpArranged;
  final bool documentsHandedOver;

  Map<String, Object?> toJson(int admissionId) => {
    'admission': admissionId,
    'instructions': instructions,
    'medications_reconciled': medicationsReconciled,
    'patient_counselled': patientCounselled,
    'follow_up_arranged': followUpArranged,
    'documents_handed_over': documentsHandedOver,
  };
}

/// A stay being discharged, as billing sees it (`awaiting_final_bill`).
///
/// BUG-07: the bed charges come priced from the hospital price list
/// (`bed_charges`); the app never asks for a rate.
@immutable
class StayAwaitingBill {
  const StayAwaitingBill({
    required this.admissionId,
    required this.patientName,
    this.days,
    this.finalInvoiceNumber,
    this.bedChargeLines = const [],
    this.bedChargeTotal,
    this.bedChargeError,
  });

  factory StayAwaitingBill.fromJson(Map<String, Object?> json) {
    final invoice = asMap(json['final_invoice']);
    final beds = asMap(json['bed_charges']);
    final lines = beds['lines'];
    final error = readText(beds['error']);
    return StayAwaitingBill(
      admissionId: readInt(json['admission']) ?? 0,
      patientName: readText(json['patient_name']) ?? '',
      days: readInt(json['days']),
      finalInvoiceNumber: readText(invoice['invoice_number']),
      bedChargeLines: [
        for (final line in lines is List ? lines : const [])
          readText(asMap(line)['description']) ?? '',
      ],
      bedChargeTotal: readText(beds['total']),
      bedChargeError: (error == null || error.isEmpty) ? null : error,
    );
  }

  final int admissionId;
  final String patientName;
  final int? days;
  final String? finalInvoiceNumber;

  /// One line per bed rate, e.g. "Bed charges (ICU, ₹5000.00/day): 2 day(s)".
  final List<String> bedChargeLines;

  /// What the bed days come to before GST, as a decimal string.
  final String? bedChargeTotal;

  /// Why the bed days cannot be priced (no price on the list), from the server.
  final String? bedChargeError;
}

abstract interface class ClinicalWorkRepository {
  Future<String> allergyStatus(int patientId);
  Future<List<AllergyRecord>> allergies(int patientId);
  Future<AllergyRecord> addAllergy(
    int patientId, {
    required String name,
    required String category,
    String reaction,
    String severity,
  });

  /// [AllergyStatus.none] or [AllergyStatus.unknown]. 409 (flag
  /// `allergy_on_record`) when "none" is asked while one is recorded.
  Future<String> setAllergyStatus(int patientId, String status);

  /// Admits [patientId] under the signed-in doctor (409 when the patient
  /// already has an active stay here).
  Future<IpdAdmission> admit(int patientId, int hospitalId, String reason);

  Future<List<MedicationOrder>> medicationOrders(int admissionId);
  Future<List<PrescribedMedicine>> prescribedMedicines(int patientId);
  Future<MedicationOrder> orderMedication(
    int admissionId,
    int patientId,
    int hospitalId,
    MedicationOrderDraft draft,
  );

  /// The first dose and the doses after it, nothing saved. 400 with flag
  /// `first_dose_required` when the doctor must choose the first dose.
  Future<SchedulePreview> previewSchedule(
    int hospitalId,
    MedicationOrderDraft draft,
  );
  Future<void> stopMedication(int orderId);

  Future<DischargePlanRecord?> dischargePlan(int admissionId);
  Future<DischargePlanRecord> saveDischargePlan(
    int admissionId,
    DischargePlanRecord plan, {
    int? existingId,
  });
  Future<void> saveDischargeSummary(
    int admissionId,
    String summary, {
    int? existingId,
  });
  Future<void> finalizeDischargeSummary(int summaryId);

  Future<List<StayAwaitingBill>> staysAwaitingFinalBill();
  Future<void> createFinalBill(int admissionId);

  /// The patient's own history (`patients/{id}/timeline/`), newest first.
  Future<List<TimelineEvent>> history(int patientId);
}

class ApiClinicalWorkRepository implements ClinicalWorkRepository {
  ApiClinicalWorkRepository(this._api);

  final ApiClient _api;

  @override
  Future<String> allergyStatus(int patientId) => _api.get(
    'patients/$patientId/',
    decode: (json) =>
        readText(asMap(json)['allergy_status']) ?? AllergyStatus.unknown,
  );

  @override
  Future<List<AllergyRecord>> allergies(int patientId) async => [
    for (final row in await getAllRows(
      _api,
      'clinical/allergies/',
      query: {'patient': patientId},
    ))
      AllergyRecord.fromJson(row),
  ];

  @override
  Future<AllergyRecord> addAllergy(
    int patientId, {
    required String name,
    required String category,
    String reaction = '',
    String severity = '',
  }) => _api.post(
    'clinical/allergies/',
    body: {
      'patient': patientId,
      'name': name,
      'category': category,
      'reaction': reaction,
      'severity': severity,
    },
    decode: (json) => AllergyRecord.fromJson(asMap(json)),
  );

  @override
  Future<String> setAllergyStatus(int patientId, String status) => _api.post(
    'patients/$patientId/allergy-status/',
    body: {'status': status},
    decode: (json) => readText(asMap(json)['allergy_status']) ?? status,
  );

  @override
  Future<IpdAdmission> admit(int patientId, int hospitalId, String reason) =>
      _api.post(
        'ipd/admissions/',
        body: {'patient': patientId, 'hospital': hospitalId, 'reason': reason},
        decode: (json) => IpdAdmission.fromJson(asMap(json)),
      );

  @override
  Future<List<MedicationOrder>> medicationOrders(int admissionId) async => [
    for (final row in await getAllRows(
      _api,
      'nurses/mar/',
      query: {'admission': admissionId},
    ))
      if (readInt(row['admission']) == admissionId)
        MedicationOrder.fromJson(row),
  ];

  @override
  Future<List<PrescribedMedicine>> prescribedMedicines(int patientId) async {
    final rows = await getAllRows(
      _api,
      'clinical/prescriptions/',
      query: {'patient': patientId},
    );
    return [
      for (final rx in rows)
        if (readInt(rx['patient']) == patientId &&
            readText(rx['status']) != 'Cancelled')
          for (final item in readRows(rx['items']))
            PrescribedMedicine(
              id: readInt(item['id']) ?? 0,
              prescriptionId: readInt(rx['id']) ?? 0,
              name: readText(item['name']) ?? '',
              dosage: readText(item['dosage']),
              frequency: readText(item['frequency']),
            ),
    ];
  }

  @override
  Future<MedicationOrder> orderMedication(
    int admissionId,
    int patientId,
    int hospitalId,
    MedicationOrderDraft draft,
  ) async {
    final order = await _api.post(
      'nurses/mar/',
      body: {
        'patient': patientId,
        'admission': admissionId,
        'hospital': hospitalId,
        'prescription': draft.medicine.prescriptionId,
        'prescription_item': draft.medicine.id,
        'medicine_name': draft.medicine.name,
        'dose': draft.dose,
        'route': draft.route,
        'frequency': draft.frequency,
        'start_date': isoDay(draft.startDate),
        'end_date': draft.endDate == null ? null : isoDay(draft.endDate!),
        'instructions': draft.instructions,
        if (draft.prnMinIntervalMinutes != null)
          'prn_min_interval_minutes': draft.prnMinIntervalMinutes,
        if (draft.prnMaxDosesPer24h != null)
          'prn_max_doses_per_24h': draft.prnMaxDosesPer24h,
        // The server schedules the doses in the same transaction (PRN gets
        // none). A refused first dose leaves no order behind. Before this the
        // app sent only today's date, which put the first dose at midnight.
        ..._firstDoseBody(draft),
      },
      decode: (json) => MedicationOrder.fromJson(asMap(json)),
    );
    return order;
  }

  @override
  Future<SchedulePreview> previewSchedule(
    int hospitalId,
    MedicationOrderDraft draft,
  ) => _api.post(
    'nurses/mar/schedule-preview/',
    body: {
      'hospital': hospitalId,
      'frequency': draft.frequency,
      'start_date': isoDay(draft.startDate),
      'end_date': draft.endDate == null ? null : isoDay(draft.endDate!),
      ..._firstDoseBody(draft),
    },
    decode: (json) => SchedulePreview.fromJson(asMap(json)),
  );

  @override
  Future<void> stopMedication(int orderId) => _api.patch(
    'nurses/mar/$orderId/',
    body: {'is_active': false},
    decode: (_) {},
  );

  @override
  Future<DischargePlanRecord?> dischargePlan(int admissionId) async {
    for (final row in await getAllRows(_api, 'ipd/discharge-plans/')) {
      if (readInt(row['admission']) == admissionId) {
        return DischargePlanRecord.fromJson(row);
      }
    }
    return null;
  }

  @override
  Future<DischargePlanRecord> saveDischargePlan(
    int admissionId,
    DischargePlanRecord plan, {
    int? existingId,
  }) {
    final body = plan.toJson(admissionId);
    DischargePlanRecord decode(Object? json) =>
        DischargePlanRecord.fromJson(asMap(json));
    return existingId == null
        ? _api.post('ipd/discharge-plans/', body: body, decode: decode)
        : _api.patch(
            'ipd/discharge-plans/$existingId/',
            body: body,
            decode: decode,
          );
  }

  @override
  Future<void> saveDischargeSummary(
    int admissionId,
    String summary, {
    int? existingId,
  }) {
    final body = {'admission': admissionId, 'summary': summary};
    return existingId == null
        ? _api.post('ipd/discharge-summaries/', body: body, decode: (_) {})
        : _api.patch(
            'ipd/discharge-summaries/$existingId/',
            body: body,
            decode: (_) {},
          );
  }

  @override
  Future<void> finalizeDischargeSummary(int summaryId) => _api.post(
    'ipd/discharge-summaries/$summaryId/finalize/',
    body: const <String, Object?>{},
    decode: (_) {},
  );

  @override
  Future<List<StayAwaitingBill>> staysAwaitingFinalBill() => _api.get(
    'ipd/admissions/awaiting_final_bill/',
    decode: (json) => [
      for (final row in json is List ? json : const [])
        StayAwaitingBill.fromJson(asMap(row)),
    ],
  );

  @override
  Future<void> createFinalBill(int admissionId) => _api.post(
    'ipd/admissions/$admissionId/final_bill/',
    body: const {'items': <Object>[]},
    decode: (_) {},
  );

  @override
  Future<List<TimelineEvent>> history(int patientId) => _api.get(
    'patients/$patientId/timeline/',
    decode: (json) {
      final rows = json is Map ? (json['events'] ?? json['results']) : json;
      return [
        for (final row in rows is List ? rows : const [])
          TimelineEvent.fromJson(asMap(row)),
      ]..sort(
        (a, b) => (b.when ?? DateTime(0)).compareTo(a.when ?? DateTime(0)),
      );
    },
  );
}
