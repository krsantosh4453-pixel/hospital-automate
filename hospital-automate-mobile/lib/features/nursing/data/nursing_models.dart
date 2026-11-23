import 'package:flutter/foundation.dart';

import '../../doctor/data/doctor_models.dart' show VitalField;
import '../../patient/data/json_read.dart';

/// The signed-in nurse's own profile: the `nurses/nurses/` row whose `user`
/// is this login (NurseSerializer). Only fields the serializer returns.
@immutable
class NurseProfile {
  const NurseProfile({
    required this.id,
    required this.name,
    this.department,
    this.shift,
    this.qualification,
    this.phone,
    this.status,
  });

  factory NurseProfile.fromJson(Map<String, Object?> json) => NurseProfile(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    department: readText(json['department']),
    shift: readText(json['shift']),
    qualification: readText(json['qualification']),
    phone: readText(json['phone']),
    status: readText(json['status']),
  );

  final int id;
  final String name;
  final String? department;

  /// The profile's usual shift (free text on the server).
  final String? shift;
  final String? qualification;
  final String? phone;
  final String? status;
}

/// One duty: a ward (`ward-assignments/`) or a patient
/// (`patient-assignments/`) for one shift of one day.
@immutable
class DutyAssignment {
  const DutyAssignment({
    required this.id,
    required this.shift,
    this.shiftDate,
    this.wardName,
    this.patientId,
    this.patientName,
    this.admissionId,
  });

  factory DutyAssignment.ward(Map<String, Object?> json) => DutyAssignment(
    id: readInt(json['id']) ?? 0,
    shift: readText(json['shift']) ?? '',
    shiftDate: readDate(json['shift_date']),
    wardName: readText(json['ward_name']),
  );

  factory DutyAssignment.patient(Map<String, Object?> json) => DutyAssignment(
    id: readInt(json['id']) ?? 0,
    shift: readText(json['shift']) ?? '',
    shiftDate: readDate(json['shift_date']),
    patientId: readInt(json['patient']),
    patientName: readText(json['patient_name']),
    admissionId: readInt(json['admission']),
  );

  final int id;
  final String shift;
  final DateTime? shiftDate;
  final String? wardName;
  final int? patientId;
  final String? patientName;
  final int? admissionId;
}

/// An in-patient stay (`ipd/admissions/`, AdmissionSerializer).
@immutable
class Admission {
  const Admission({
    required this.id,
    required this.status,
    this.patientId,
    this.patientName,
    this.admittedAt,
    this.reason,
    this.doctorName,
    this.wardName,
    this.roomNumber,
    this.bedNumber,
  });

  factory Admission.fromJson(Map<String, Object?> json) {
    final bed = asMap(json['current_bed']);
    return Admission(
      id: readInt(json['id']) ?? 0,
      status: readText(json['status']) ?? '',
      patientId: readInt(json['patient']),
      patientName: readText(json['patient_name']),
      admittedAt: readDateTime(json['admission_date']),
      reason: readText(json['reason']),
      doctorName: readText(json['admitting_doctor_name']),
      wardName: readText(bed['ward_name']),
      roomNumber: readText(bed['room_number']),
      bedNumber: readText(bed['bed_number']),
    );
  }

  /// Statuses of a stay the ward still looks after (users/care_scope.py).
  static const inWardStatuses = {'Admitted', 'Discharge Initiated'};

  final int id;
  final String status;
  final int? patientId;
  final String? patientName;
  final DateTime? admittedAt;
  final String? reason;
  final String? doctorName;
  final String? wardName;
  final String? roomNumber;
  final String? bedNumber;

  bool get inWard => inWardStatuses.contains(status);
  bool get awaitingBed => bedNumber == null;
}

/// Vitals a nurse records on an admission: the keys the web's Nurses page
/// writes into `NursingAssessment.vitals` (Nurses.jsx saveVitals). Blood
/// pressure is stored as one "systolic/diastolic" text, as the web does.
const wardVitalFields = [
  VitalField.systolicBp,
  VitalField.diastolicBp,
  VitalField.heartRate,
  VitalField.respiratoryRate,
  VitalField.temperature,
  VitalField.spo2,
];

/// [VitalField] → key in the assessment's `vitals` JSON (blood pressure is
/// joined into `bp`).
const wardVitalKeys = {
  VitalField.heartRate: 'pulse',
  VitalField.respiratoryRate: 'respiratory_rate',
  VitalField.temperature: 'temperature',
  VitalField.spo2: 'spo2',
};

/// The `vitals` JSON for an assessment, or null when blood pressure is half
/// filled in (both numbers or neither).
Map<String, String>? wardVitalsJson(Map<VitalField, String> values) {
  String? value(VitalField field) {
    final text = values[field]?.trim() ?? '';
    return text.isEmpty ? null : text;
  }

  final systolic = value(VitalField.systolicBp);
  final diastolic = value(VitalField.diastolicBp);
  if ((systolic == null) != (diastolic == null)) return null;
  return {
    if (systolic != null) 'bp': '$systolic/$diastolic',
    for (final entry in wardVitalKeys.entries)
      if (value(entry.key) != null) entry.value: value(entry.key)!,
  };
}

/// A nursing assessment (NursingAssessmentSerializer). Vitals recorded on
/// an admission are a "Focused" assessment with a `vitals` record.
@immutable
class NursingAssessment {
  const NursingAssessment({
    required this.id,
    required this.type,
    this.patientId,
    this.admissionId,
    this.vitals = const {},
    this.planOfCare,
    this.nurseName,
    this.assessedAt,
  });

  factory NursingAssessment.fromJson(Map<String, Object?> json) =>
      NursingAssessment(
        id: readInt(json['id']) ?? 0,
        type: readText(json['assessment_type']) ?? '',
        patientId: readInt(json['patient']),
        admissionId: readInt(json['admission']),
        vitals: {
          for (final entry in asMap(json['vitals']).entries)
            if (readText(entry.value) != null)
              entry.key: readText(entry.value)!,
        },
        planOfCare: readText(json['plan_of_care']),
        nurseName: readText(json['nurse_name']),
        assessedAt: readDateTime(json['assessed_at']),
      );

  /// `assessment_type` used for a vitals entry (as on the web).
  static const vitalsType = 'Focused';

  final int id;
  final String type;
  final int? patientId;
  final int? admissionId;

  /// Raw `vitals` JSON as stored (`bp`, `pulse`, `spo2`, `temperature`,
  /// `respiratory_rate`); shown as recorded, never re-interpreted.
  final Map<String, String> vitals;
  final String? planOfCare;
  final String? nurseName;
  final DateTime? assessedAt;

  bool get hasVitals => vitals.isNotEmpty;
}

/// NursingNote.NOTE_TYPES on the server.
const nursingNoteTypes = [
  'Progress',
  'Incident',
  'Communication',
  'Education',
  'Handoff',
];

/// A nursing note (NursingNoteSerializer). Notes are never edited or
/// deleted from the app; a correction is a new note.
@immutable
class NursingNote {
  const NursingNote({
    required this.id,
    required this.type,
    required this.text,
    this.patientId,
    this.admissionId,
    this.nurseName,
    this.createdAt,
  });

  factory NursingNote.fromJson(Map<String, Object?> json) => NursingNote(
    id: readInt(json['id']) ?? 0,
    type: readText(json['note_type']) ?? '',
    text: readText(json['note']) ?? '',
    patientId: readInt(json['patient']),
    admissionId: readInt(json['admission']),
    nurseName: readText(json['nurse_name']),
    createdAt: readDateTime(json['created_at']),
  );

  final int id;
  final String type;
  final String text;
  final int? patientId;
  final int? admissionId;
  final String? nurseName;
  final DateTime? createdAt;
}

/// A scheduled nursing task (CareTaskSerializer).
@immutable
class CareTask {
  const CareTask({
    required this.id,
    required this.type,
    required this.description,
    required this.status,
    required this.priority,
    this.patientId,
    this.patientName,
    this.scheduledAt,
    this.completedByName,
  });

  factory CareTask.fromJson(Map<String, Object?> json) => CareTask(
    id: readInt(json['id']) ?? 0,
    type: readText(json['task_type']) ?? '',
    description: readText(json['description']) ?? '',
    status: readText(json['status']) ?? '',
    priority: readText(json['priority']) ?? '',
    patientId: readInt(json['patient']),
    patientName: readText(json['patient_name']),
    scheduledAt: readDateTime(json['scheduled_at']),
    completedByName: readText(json['completed_by_name']),
  );

  static const pending = 'Pending';
  static const inProgress = 'In Progress';

  final int id;
  final String type;
  final String description;
  final String status;
  final String priority;
  final int? patientId;
  final String? patientName;
  final DateTime? scheduledAt;
  final String? completedByName;

  bool get isOpen => status == pending || status == inProgress;
  bool get isUrgent => priority == 'Urgent' || priority == 'Stat';
}

/// One dose on a doctor's medication order (MARAdministrationSerializer).
@immutable
class Dose {
  const Dose({
    required this.id,
    required this.status,
    required this.medicineName,
    this.orderId,
    this.dose,
    this.route,
    this.frequency,
    this.patientId,
    this.patientName,
    this.scheduledAt,
    this.recordedAt,
    this.givenByName,
    this.isDelayed = false,
    this.isPrn = false,
    this.reason,
  });

  factory Dose.fromJson(Map<String, Object?> json) => Dose(
    id: readInt(json['id']) ?? 0,
    status: readText(json['status']) ?? '',
    medicineName: readText(json['medicine_name']) ?? '',
    orderId: readInt(json['mar']),
    dose: readText(json['dose']),
    route: readText(json['route']),
    frequency: readText(json['frequency']),
    patientId: readInt(json['patient']),
    patientName: readText(json['patient_name']),
    scheduledAt: readDateTime(json['scheduled_time']),
    recordedAt: readDateTime(json['administered_time']),
    givenByName: readText(json['administered_by_name']),
    isDelayed: json['is_delayed'] == true,
    isPrn: json['is_prn'] == true,
    reason:
        readText(json['reason_held']) ??
        readText(json['reason_refused']) ??
        readText(json['notes']),
  );

  /// Due until a nurse records an outcome (MARAdministration.SCHEDULED).
  static const scheduled = 'Scheduled';

  final int id;
  final String status;
  final String medicineName;
  final int? orderId;

  /// Dose, route and frequency exactly as the doctor ordered them.
  final String? dose;
  final String? route;
  final String? frequency;
  final int? patientId;
  final String? patientName;
  final DateTime? scheduledAt;
  final DateTime? recordedAt;
  final String? givenByName;

  /// Server-computed: still due more than 30 minutes after its time.
  final bool isDelayed;
  final bool isPrn;
  final String? reason;

  bool get isDue => status == scheduled;
}

/// A doctor's medication order (MARSerializer) with its doses.
@immutable
class MedicationOrder {
  const MedicationOrder({
    required this.id,
    required this.medicineName,
    required this.isActive,
    this.prescriptionId,
    this.dose,
    this.route,
    this.frequency,
    this.startDate,
    this.endDate,
    this.orderedByName,
    this.prnMinIntervalMinutes,
    this.prnMaxDosesPer24h,
    this.doses = const [],
  });

  factory MedicationOrder.fromJson(Map<String, Object?> json) =>
      MedicationOrder(
        id: readInt(json['id']) ?? 0,
        medicineName: readText(json['medicine_name']) ?? '',
        isActive: json['is_active'] == true,
        prescriptionId: readInt(json['prescription']),
        dose: readText(json['dose']),
        route: readText(json['route']),
        frequency: readText(json['frequency']),
        startDate: readDate(json['start_date']),
        endDate: readDate(json['end_date']),
        orderedByName: readText(json['ordered_by_name']),
        prnMinIntervalMinutes: readInt(json['prn_min_interval_minutes']),
        prnMaxDosesPer24h: readInt(json['prn_max_doses_per_24h']),
        doses: [
          for (final row in readRows(json['administrations']))
            Dose.fromJson(row),
        ],
      );

  final int id;
  final String medicineName;
  final bool isActive;
  final int? prescriptionId;
  final String? dose;
  final String? route;
  final String? frequency;
  final DateTime? startDate;
  final DateTime? endDate;
  final String? orderedByName;

  /// H-10: the doctor's limits on an as-needed order; null means no limit.
  final int? prnMinIntervalMinutes;
  final int? prnMaxDosesPer24h;
  final List<Dose> doses;

  /// An as-needed order: never scheduled, given with [NursingRepository.givePrnDose].
  bool get isPrn => isPrnFrequency(frequency);
}

/// The same words the server reads as "as needed" (nurses/frequency.py).
final _prnWord = RegExp(
  r'\b(PRN|SOS|AS NEEDED|AS REQUIRED)\b',
  caseSensitive: false,
);

bool isPrnFrequency(String? frequency) =>
    frequency != null && _prnWord.hasMatch(frequency);

/// [minutes] between PRN doses as hours for display, e.g. 240 → "4", 90 → "1.5".
String prnIntervalHours(int minutes) {
  final hours = minutes / 60;
  return hours == hours.roundToDouble()
      ? hours.toInt().toString()
      : hours.toStringAsFixed(2).replaceFirst(RegExp(r'0+$'), '');
}

/// The outcomes a nurse may record for a due dose (dose actions in
/// nurses/views.py). Excluding a dose is the doctor's decision and is not
/// offered here.
enum DoseAction {
  administer('administer', needsReason: false),
  hold('hold', needsReason: true),
  refuse('refuse', needsReason: true),
  missed('mark_missed', needsReason: false);

  const DoseAction(this.path, {required this.needsReason});

  final String path;

  /// The app asks for a reason before sending (the server stores it).
  final bool needsReason;
}
