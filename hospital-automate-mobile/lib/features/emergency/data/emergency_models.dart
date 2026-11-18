import 'package:flutter/foundation.dart';

import '../../patient/data/json_read.dart';

/// EmergencyVisit.STATUS_CHOICES (emergency/models.py), as the server sends them.
abstract final class ErStatus {
  static const registered = 'Registered';
  static const triage = 'Triage';
  static const waiting = 'Waiting';
  static const underConsultation = 'Under Consultation';
  static const investigations = 'Investigations';
  static const treatment = 'Treatment';
  static const observation = 'Observation';
  static const admitted = 'Admitted';
  static const discharged = 'Discharged';
  static const referred = 'Referred';
  static const leftAgainstAdvice = 'Left Against Advice';
  static const expired = 'Expired';

  static const all = [
    registered,
    triage,
    waiting,
    underConsultation,
    investigations,
    treatment,
    observation,
    admitted,
    discharged,
    referred,
    leftAgainstAdvice,
    expired,
  ];

  /// Statuses the dashboard does not count as active (views.py `dashboard`).
  static const closed = {
    admitted,
    discharged,
    referred,
    leftAgainstAdvice,
    expired,
  };
}

/// EmergencyVisit.TRIAGE_LEVELS, most to least urgent. The app offers only
/// these values; it never derives a level itself.
const triageLevels = [
  'Critical',
  'Emergency',
  'Urgent',
  'Semi-Urgent',
  'Non-Urgent',
];

/// The model's default level for a new visit.
const defaultTriageLevel = 'Non-Urgent';

/// Moves the server accepts, with the statuses each one is allowed from
/// (emergency/views.py). The server re-checks and answers 400 otherwise.
enum ErAction {
  startTriage,
  completeTriage,
  startConsultation,
  discharge,
  refer;

  bool allowedFrom(String status) => switch (this) {
    ErAction.startTriage => status == ErStatus.registered,
    ErAction.completeTriage => status == ErStatus.triage,
    ErAction.startConsultation =>
      status == ErStatus.waiting || status == ErStatus.triage,
    ErAction.discharge || ErAction.refer => !ErStatus.closed.contains(status),
  };
}

List<ErAction> erActionsFor(String status) => [
  for (final action in ErAction.values)
    if (action.allowedFrom(status)) action,
];

/// `GET emergency/emergency-visits/dashboard/`: counts of the visits this
/// login may see at the acting hospital.
@immutable
class ErDashboard {
  const ErDashboard({
    required this.statusCounts,
    required this.triageCounts,
    required this.totalActive,
  });

  factory ErDashboard.fromJson(Map<String, Object?> json) => ErDashboard(
    statusCounts: _counts(json['status_counts']),
    triageCounts: _counts(json['triage_counts']),
    totalActive: readInt(json['total_active']) ?? 0,
  );

  final Map<String, int> statusCounts;
  final Map<String, int> triageCounts;
  final int totalActive;

  int status(String name) => statusCounts[name] ?? 0;
  int triage(String name) => triageCounts[name] ?? 0;
}

Map<String, int> _counts(Object? value) => Map.unmodifiable({
  for (final entry in asMap(value).entries)
    entry.key: readInt(entry.value) ?? 0,
});

@immutable
class ErTriage {
  const ErTriage({
    this.chiefComplaint,
    this.painScore,
    this.glasgowComaScale,
    this.notes,
    this.triagedByName,
    this.triagedAt,
  });

  factory ErTriage.fromJson(Map<String, Object?> json) => ErTriage(
    chiefComplaint: readText(json['chief_complaint']),
    painScore: readInt(json['pain_score']),
    glasgowComaScale: readInt(json['glasgow_coma_scale']),
    notes: readText(json['triage_notes']),
    triagedByName: readText(json['triaged_by_name']),
    triagedAt: readDateTime(json['triaged_at']),
  );

  final String? chiefComplaint;
  final int? painScore;
  final int? glasgowComaScale;
  final String? notes;
  final String? triagedByName;
  final DateTime? triagedAt;
}

/// One ER vitals reading. Decimals stay as the server's text ("37.20").
@immutable
class ErVitals {
  const ErVitals({
    required this.id,
    this.temperature,
    this.systolic,
    this.diastolic,
    this.heartRate,
    this.respiratoryRate,
    this.spo2,
    this.bloodSugar,
    this.recordedByName,
    this.recordedAt,
  });

  factory ErVitals.fromJson(Map<String, Object?> json) => ErVitals(
    id: readInt(json['id']) ?? 0,
    temperature: readText(json['temperature']),
    systolic: readInt(json['systolic_bp']),
    diastolic: readInt(json['diastolic_bp']),
    heartRate: readInt(json['heart_rate']),
    respiratoryRate: readInt(json['respiratory_rate']),
    spo2: readInt(json['spo2']),
    bloodSugar: readText(json['blood_sugar']),
    recordedByName: readText(json['recorded_by_name']),
    recordedAt: readDateTime(json['recorded_at']),
  );

  final int id;
  final String? temperature;
  final int? systolic;
  final int? diastolic;
  final int? heartRate;
  final int? respiratoryRate;
  final int? spo2;
  final String? bloodSugar;
  final String? recordedByName;
  final DateTime? recordedAt;
}

@immutable
class ErOrder {
  const ErOrder({
    required this.id,
    required this.orderType,
    required this.status,
    this.description,
    this.orderedByName,
    this.orderedAt,
    this.result,
  });

  factory ErOrder.fromJson(Map<String, Object?> json) => ErOrder(
    id: readInt(json['id']) ?? 0,
    orderType: readText(json['order_type']) ?? '',
    status: readText(json['status']) ?? '',
    description: readText(json['description']),
    orderedByName: readText(json['ordered_by_name']),
    orderedAt: readDateTime(json['ordered_at']),
    result: readText(json['result']),
  );

  final int id;
  final String orderType;
  final String status;
  final String? description;
  final String? orderedByName;
  final DateTime? orderedAt;
  final String? result;
}

@immutable
class ErMedication {
  const ErMedication({
    required this.id,
    required this.name,
    this.dose,
    this.route,
    this.frequency,
    this.duration,
    this.administered = false,
    this.prescribedByName,
    this.prescribedAt,
    this.administeredAt,
  });

  factory ErMedication.fromJson(Map<String, Object?> json) => ErMedication(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    dose: readText(json['dose']),
    route: readText(json['route']),
    frequency: readText(json['frequency']),
    duration: readText(json['duration']),
    administered: json['administered'] == true,
    prescribedByName: readText(json['prescribed_by_name']),
    prescribedAt: readDateTime(json['prescribed_at']),
    administeredAt: readDateTime(json['administered_at']),
  );

  final int id;
  final String name;
  final String? dose;
  final String? route;
  final String? frequency;
  final String? duration;
  final bool administered;
  final String? prescribedByName;
  final DateTime? prescribedAt;
  final DateTime? administeredAt;
}

@immutable
class ErNote {
  const ErNote({
    required this.id,
    required this.note,
    this.writtenByName,
    this.writtenAt,
  });

  factory ErNote.fromJson(Map<String, Object?> json) => ErNote(
    id: readInt(json['id']) ?? 0,
    note: readText(json['note']) ?? '',
    writtenByName:
        readText(json['written_by_name']) ??
        readText(json['written_by_username']),
    writtenAt: readDateTime(json['written_at']),
  );

  final int id;
  final String note;
  final String? writtenByName;
  final DateTime? writtenAt;
}

/// An emergency visit as `EmergencyVisitSerializer` sends it.
@immutable
class EmergencyVisit {
  const EmergencyVisit({
    required this.id,
    required this.status,
    required this.triageLevel,
    this.visitNumber,
    this.patientId,
    this.patientName,
    this.arrivalTime,
    this.triageTime,
    this.consultationStartTime,
    this.dischargeTime,
    this.remarks,
    this.attendingDoctorId,
    this.attendingDoctorName,
    this.disposition,
    this.dischargeDiagnosis,
    this.followUpInstructions,
    this.triage,
    this.vitals = const [],
    this.orders = const [],
    this.medications = const [],
    this.notes = const [],
  });

  factory EmergencyVisit.fromJson(Map<String, Object?> json) {
    final triage = json['triage'];
    return EmergencyVisit(
      id: readInt(json['id']) ?? 0,
      status: readText(json['status']) ?? '',
      triageLevel: readText(json['triage_level']) ?? '',
      visitNumber: readText(json['visit_number']),
      patientId: readInt(json['patient']),
      patientName: readText(json['patient_name']),
      arrivalTime: readDateTime(json['arrival_time']),
      triageTime: readDateTime(json['triage_time']),
      consultationStartTime: readDateTime(json['consultation_start_time']),
      dischargeTime: readDateTime(json['discharge_time']),
      remarks: readText(json['remarks']),
      attendingDoctorId: readInt(json['attending_doctor']),
      attendingDoctorName: readText(json['attending_doctor_name']),
      disposition: readText(json['disposition']),
      dischargeDiagnosis: readText(json['discharge_diagnosis']),
      followUpInstructions: readText(json['follow_up_instructions']),
      triage: triage is Map ? ErTriage.fromJson(asMap(triage)) : null,
      vitals: List.unmodifiable(
        readRows(json['vitals_records']).map(ErVitals.fromJson),
      ),
      orders: List.unmodifiable(readRows(json['orders']).map(ErOrder.fromJson)),
      medications: List.unmodifiable(
        readRows(json['medications']).map(ErMedication.fromJson),
      ),
      notes: List.unmodifiable(readRows(json['notes']).map(ErNote.fromJson)),
    );
  }

  final int id;
  final String status;
  final String triageLevel;
  final String? visitNumber;
  final int? patientId;
  final String? patientName;
  final DateTime? arrivalTime;
  final DateTime? triageTime;
  final DateTime? consultationStartTime;
  final DateTime? dischargeTime;
  final String? remarks;
  final int? attendingDoctorId;
  final String? attendingDoctorName;
  final String? disposition;
  final String? dischargeDiagnosis;
  final String? followUpInstructions;
  final ErTriage? triage;
  final List<ErVitals> vitals;
  final List<ErOrder> orders;
  final List<ErMedication> medications;
  final List<ErNote> notes;

  bool get isClosed => ErStatus.closed.contains(status);
}

/// What `complete_triage` stores. Only [chiefComplaint] and [triageLevel]
/// are needed; the scores are sent when entered.
@immutable
class TriageDraft {
  const TriageDraft({
    required this.chiefComplaint,
    required this.triageLevel,
    this.painScore,
    this.glasgowComaScale,
    this.notes = '',
  });

  final String chiefComplaint;
  final String triageLevel;
  final int? painScore;
  final int? glasgowComaScale;
  final String notes;

  Map<String, Object?> toJson() => {
    'chief_complaint': chiefComplaint.trim(),
    'triage_level': triageLevel,
    'pain_score': ?painScore,
    'glasgow_coma_scale': ?glasgowComaScale,
    if (notes.trim().isNotEmpty) 'triage_notes': notes.trim(),
  };
}

/// Statuses from which `admit_to_ipd` admits (emergency/views.py).
const admittableStatuses = {
  ErStatus.underConsultation,
  ErStatus.investigations,
  ErStatus.treatment,
  ErStatus.observation,
};

/// An ER vitals field and the number format its column stores
/// (EmergencyVitals): whole numbers, or decimals with [maxDigits] digits and
/// two decimals. The server checks no clinical range, so neither does the app.
enum ErVitalField {
  systolic('systolic_bp'),
  diastolic('diastolic_bp'),
  heartRate('heart_rate'),
  respiratoryRate('respiratory_rate'),
  spo2('spo2'),
  temperature('temperature', maxDigits: 5),
  bloodSugar('blood_sugar', maxDigits: 6);

  const ErVitalField(this.key, {this.maxDigits});

  final String key;

  /// Null for whole-number fields.
  final int? maxDigits;

  bool get isDecimal => maxDigits != null;
}

/// Why a typed vital cannot be sent.
enum VitalInputError { notANumber, negative, notWhole, tooPrecise, tooLong }

/// Checks [text] against [field]'s column format; null when it is fine.
VitalInputError? checkVital(ErVitalField field, String text) {
  final value = text.trim();
  final number = num.tryParse(value);
  if (number == null || !number.isFinite) return VitalInputError.notANumber;
  if (number < 0) return VitalInputError.negative;
  final maxDigits = field.maxDigits;
  if (maxDigits == null) {
    return int.tryParse(value) == null ? VitalInputError.notWhole : null;
  }
  final parts = value.split('.');
  final decimals = parts.length > 1 ? parts[1].length : 0;
  if (decimals > 2) return VitalInputError.tooPrecise;
  // Digits before the point: the column keeps maxDigits - 2 of them.
  final whole = parts.first.replaceFirst(RegExp(r'^0+(?=\d)'), '');
  if (whole.length > maxDigits - 2) return VitalInputError.tooLong;
  return null;
}

/// The body of `add_vitals`: only entered fields, as numbers.
Map<String, Object?> vitalsBody(
  Map<ErVitalField, String> values, {
  int? recordedBy,
}) => {
  for (final entry in values.entries)
    if (entry.value.trim().isNotEmpty)
      entry.key.key: entry.key.isDecimal
          ? entry.value.trim()
          : int.parse(entry.value.trim()),
  'recorded_by': ?recordedBy,
};

/// What `admit_to_ipd` answers: the new admission and its bed.
@immutable
class ErAdmission {
  const ErAdmission({required this.admissionId, this.bed});

  factory ErAdmission.fromJson(Map<String, Object?> json) {
    final admission = asMap(json['admission']);
    return ErAdmission(
      admissionId: readInt(admission['id']) ?? 0,
      bed: readText(admission['bed']),
    );
  }

  final int admissionId;
  final String? bed;
}

/// A doctor of the acting hospital (`doctors/`), for the attending picker.
@immutable
class DoctorOption {
  const DoctorOption({required this.id, required this.name, this.specialty});

  factory DoctorOption.fromJson(Map<String, Object?> json) => DoctorOption(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    specialty: readText(json['specialization']),
  );

  final int id;
  final String name;
  final String? specialty;
}
