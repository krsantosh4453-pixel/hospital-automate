import 'package:flutter/foundation.dart';

import '../../patient/data/json_read.dart';

/// The signed-in doctor's own profile: the `doctors/` row whose `user` is
/// this login (DoctorSerializer). Only fields the serializer returns.
@immutable
class DoctorProfile {
  const DoctorProfile({
    required this.id,
    required this.name,
    this.specialization,
    this.department,
    this.registrationNumber,
    this.registrationCouncil,
    this.registrationVerified = false,
    this.phone,
    this.email,
    this.availability,
    this.status,
    this.experience,
  });

  factory DoctorProfile.fromJson(Map<String, Object?> json) => DoctorProfile(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    specialization: readText(json['specialization']),
    department: readText(json['department']),
    registrationNumber: readText(json['registration_number']),
    registrationCouncil: readText(json['registration_council']),
    registrationVerified: json['registration_verified_at'] != null,
    phone: readText(json['phone']),
    email: readText(json['email']),
    availability: readText(json['availability']),
    status: readText(json['status']),
    experience: readText(json['experience']),
  );

  final int id;
  final String name;
  final String? specialization;
  final String? department;
  final String? registrationNumber;
  final String? registrationCouncil;

  /// The hospital Admin has verified the registration (needed to sign where
  /// the hospital requires it).
  final bool registrationVerified;
  final String? phone;
  final String? email;
  final String? availability;
  final String? status;
  final String? experience;
}

/// `encounters/visits/` (VisitSerializer): every clinical record hangs off a visit.
@immutable
class Visit {
  const Visit({
    required this.id,
    required this.status,
    this.patientId,
    this.patientName,
    this.doctorId,
    this.doctorName,
    this.hospitalId,
    this.visitType,
    this.chiefComplaint,
    this.visitDate,
  });

  factory Visit.fromJson(Map<String, Object?> json) => Visit(
    id: readInt(json['id']) ?? 0,
    status: readText(json['status']) ?? '',
    patientId: readInt(json['patient']),
    patientName: readText(json['patient_name']),
    doctorId: readInt(json['doctor']),
    doctorName: readText(json['doctor_name']),
    hospitalId: readInt(json['hospital']),
    visitType: readText(json['visit_type']),
    chiefComplaint: readText(json['chief_complaint']),
    visitDate: readDateTime(json['visit_date']),
  );

  /// `Visit.status` values (web Consultation `VISIT_STATUSES`).
  static const waiting = 'Waiting';
  static const inConsultation = 'In Consultation';
  static const completed = 'Completed';
  static const cancelled = 'Cancelled';

  final int id;
  final String status;
  final int? patientId;
  final String? patientName;
  final int? doctorId;
  final String? doctorName;
  final int? hospitalId;
  final String? visitType;
  final String? chiefComplaint;
  final DateTime? visitDate;

  bool get isOpen => status == waiting || status == inConsultation;
}

/// A vital the app records, with the unit the web form uses and the limits
/// the server enforces (clinical/models.py VitalSign). No "normal range" is
/// applied: the app never judges a reading.
enum VitalField {
  systolicBp('systolic_bp', 'mmHg', isInteger: true),
  diastolicBp('diastolic_bp', 'mmHg', isInteger: true),
  heartRate('heart_rate', 'bpm', isInteger: true),
  respiratoryRate('respiratory_rate', '/min', isInteger: true),
  temperature('temperature', '°C'),
  spo2('spo2', '%', isInteger: true, max: 100),
  weight('weight', 'kg'),
  height('height', 'cm'),
  bloodSugar('blood_sugar', 'mg/dL'),
  painScore('pain_score', '0–10', isInteger: true, max: 10);

  const VitalField(this.key, this.unit, {this.isInteger = false, this.max});

  final String key;
  final String unit;

  /// Stored as a whole number (PositiveIntegerField) on the server.
  final bool isInteger;

  /// The server's (or, for SpO2, the percentage's) upper limit.
  final num? max;

  /// DecimalField(decimal_places=2) holds at most this many decimals.
  static const maxDecimals = 2;

  /// Why [text] cannot be sent, or null when it is a valid reading. Empty
  /// means "not measured" and is allowed.
  VitalError? check(String text) {
    final value = text.trim();
    if (value.isEmpty) return null;
    final number = num.tryParse(value);
    if (number == null || number.isNaN || number.isInfinite) {
      return VitalError.notANumber;
    }
    if (number < 0) return VitalError.negative;
    if (isInteger && number != number.truncate()) return VitalError.wholeNumber;
    final decimals = value.contains('.') ? value.split('.').last.length : 0;
    if (!isInteger && decimals > maxDecimals) return VitalError.tooPrecise;
    if (max != null && number > max!) return VitalError.tooHigh;
    return null;
  }
}

enum VitalError { notANumber, negative, wholeNumber, tooPrecise, tooHigh }

/// One saved reading (VitalSignSerializer). BMI is the server's
/// (kg ÷ m², height in cm), never computed on the phone.
@immutable
class VitalReading {
  const VitalReading({
    required this.id,
    this.visitId,
    this.values = const {},
    this.bmi,
    this.comments,
    this.recordedByName,
    this.recordedAt,
  });

  factory VitalReading.fromJson(Map<String, Object?> json) => VitalReading(
    id: readInt(json['id']) ?? 0,
    visitId: readInt(json['visit']),
    values: {
      for (final field in VitalField.values)
        if (readText(json[field.key]) != null)
          field: readText(json[field.key])!,
    },
    bmi: readMoney(json['bmi']),
    comments: readText(json['comments']),
    recordedByName: readText(json['recorded_by_name']),
    recordedAt: readDateTime(json['recorded_at']),
  );

  final int id;
  final int? visitId;
  final Map<VitalField, String> values;
  final double? bmi;
  final String? comments;
  final String? recordedByName;
  final DateTime? recordedAt;
}

/// Diagnosis.diagnosis_type values the web offers.
const diagnosisTypes = ['Provisional', 'Differential', 'Final', 'Confirmed'];

/// A diagnosis (DiagnosisSerializer). Drafts are edited only by their
/// author; once signed it is final and a correction is a new record.
@immutable
class DiagnosisRecord {
  const DiagnosisRecord({
    required this.id,
    required this.name,
    this.visitId,
    this.icd10Code,
    this.diagnosisType,
    this.remarks,
    this.signedAt,
    this.createdAt,
    this.recordedBy,
  });

  factory DiagnosisRecord.fromJson(Map<String, Object?> json) =>
      DiagnosisRecord(
        id: readInt(json['id']) ?? 0,
        name: readText(json['name']) ?? '',
        visitId: readInt(json['visit']),
        icd10Code: readText(json['icd10_code']),
        diagnosisType: readText(json['diagnosis_type']),
        remarks: readText(json['remarks']),
        signedAt: readDateTime(json['signed_at']),
        createdAt: readDateTime(json['created_at']),
        recordedBy: readInt(json['recorded_by']),
      );

  final int id;
  final String name;
  final int? visitId;
  final String? icd10Code;
  final String? diagnosisType;
  final String? remarks;
  final DateTime? signedAt;
  final DateTime? createdAt;

  /// The author's user id.
  final int? recordedBy;

  bool get isSigned => signedAt != null;
}

/// ClinicalNote.SECTIONS, in the web's display order.
enum NoteSection {
  chiefComplaint('chief_complaint'),
  presentIllness('history_of_present_illness'),
  pastHistory('past_history'),
  currentMedications('current_medications'),
  examination('examination'),
  assessment('assessment'),
  plan('plan'),
  other('note');

  const NoteSection(this.key);

  final String key;
}

/// A structured clinical note (ClinicalNoteSerializer), draft or signed.
@immutable
class ClinicalNoteRecord {
  const ClinicalNoteRecord({
    required this.id,
    this.visitId,
    this.sections = const {},
    this.signedAt,
    this.createdAt,
    this.doctorId,
  });

  factory ClinicalNoteRecord.fromJson(Map<String, Object?> json) =>
      ClinicalNoteRecord(
        id: readInt(json['id']) ?? 0,
        visitId: readInt(json['visit']),
        sections: {
          for (final section in NoteSection.values)
            if (readText(json[section.key]) != null)
              section: readText(json[section.key])!,
        },
        signedAt: readDateTime(json['signed_at']),
        createdAt: readDateTime(json['created_at']),
        doctorId: readInt(json['doctor']),
      );

  final int id;
  final int? visitId;
  final Map<NoteSection, String> sections;
  final DateTime? signedAt;
  final DateTime? createdAt;
  final int? doctorId;

  bool get isSigned => signedAt != null;
}

/// One row of `patients/?search=` (PatientSerializer), as a doctor sees it.
@immutable
class PatientSummary {
  const PatientSummary({
    required this.id,
    required this.name,
    this.uhid,
    this.age,
    this.gender,
    this.phone,
    this.condition,
    this.dateOfBirth,
    this.city,
    this.emergencyContactName,
    this.emergencyContactPhone,
  });

  factory PatientSummary.fromJson(Map<String, Object?> json) => PatientSummary(
    id: readInt(json['id']) ?? 0,
    name: readText(json['name']) ?? '',
    uhid: readText(json['uhid']),
    age: readInt(json['age']),
    gender: readText(json['gender']),
    phone: readText(json['phone']),
    condition: readText(json['condition']),
    dateOfBirth: readDate(json['date_of_birth']),
    city: readText(json['city']),
    emergencyContactName: readText(json['emergency_contact_name']),
    emergencyContactPhone: readText(json['emergency_contact_phone']),
  );

  final int id;
  final String name;
  final String? uhid;
  final int? age;
  final String? gender;
  final String? phone;
  final String? condition;
  final DateTime? dateOfBirth;
  final String? city;
  final String? emergencyContactName;
  final String? emergencyContactPhone;
}

/// One event of `patients/{id}/timeline/` (patients/timeline.py).
@immutable
class TimelineEvent {
  const TimelineEvent({
    required this.kind,
    required this.title,
    this.when,
    this.detail,
    this.hospital,
  });

  factory TimelineEvent.fromJson(Map<String, Object?> json) => TimelineEvent(
    kind: readText(json['kind']) ?? '',
    title: readText(json['title']) ?? '',
    when: readDateTime(json['when']),
    detail: readText(json['detail']),
    hospital: readText(json['hospital']),
  );

  final String kind;
  final String title;
  final DateTime? when;
  final String? detail;
  final String? hospital;
}

/// `terminology/icd10/?q=` result.
@immutable
class Icd10Code {
  const Icd10Code({required this.code, required this.description});

  factory Icd10Code.fromJson(Map<String, Object?> json) => Icd10Code(
    code: readText(json['code']) ?? '',
    description: readText(json['description']) ?? '',
  );

  final String code;
  final String description;
}

/// A medication safety alert from `clinical/prescriptions/safety-check/`.
@immutable
class SafetyAlert {
  const SafetyAlert({
    required this.type,
    required this.severity,
    required this.message,
    this.medicines = const [],
  });

  factory SafetyAlert.fromJson(Map<String, Object?> json) => SafetyAlert(
    type: readText(json['type']) ?? '',
    severity: readText(json['severity']) ?? '',
    message: readText(json['message']) ?? '',
    medicines: [
      if (json['medicines'] is List)
        for (final m in json['medicines']! as List) '$m',
    ],
  );

  /// `rules.HIGH`: blocks the prescription unless the doctor gives a reason.
  static const high = 'high';

  final String type;
  final String severity;
  final String message;
  final List<String> medicines;

  bool get isBlocking => severity == high;
}

/// The server refuses a high-alert override reason shorter than this
/// (clinical/serializers.py MIN_OVERRIDE_REASON).
const minOverrideReasonLength = 10;

/// One medicine line the doctor writes (PrescriptionItemSerializer input).
@immutable
class MedicineLine {
  const MedicineLine({
    required this.name,
    this.dosage = '',
    this.frequency = '',
    this.duration = '',
    this.quantity = 1,
    this.instructions = '',
  });

  final String name;
  final String dosage;
  final String frequency;
  final String duration;
  final int quantity;
  final String instructions;

  Map<String, Object?> toJson() => {
    'name': name.trim(),
    'dosage': dosage.trim(),
    'frequency': frequency.trim(),
    'duration': duration.trim(),
    'quantity': quantity,
    'instructions': instructions.trim(),
  };
}

/// A new prescription for a visit. The server signs it as the requesting
/// doctor and re-checks medication safety.
@immutable
class PrescriptionDraft {
  const PrescriptionDraft({
    required this.hospitalId,
    required this.patientId,
    required this.visitId,
    required this.lines,
    this.overrideReason = '',
  });

  /// The status the web's doctor form sends for a new prescription.
  static const newStatus = 'Confirmed';

  final int hospitalId;
  final int patientId;
  final int visitId;
  final List<MedicineLine> lines;
  final String overrideReason;

  Map<String, Object?> toJson() => {
    'hospital': hospitalId,
    'patient': patientId,
    'visit': visitId,
    'status': newStatus,
    'items': [for (final line in lines) line.toJson()],
    if (overrideReason.trim().isNotEmpty)
      'safety_override_reason': overrideReason.trim(),
  };
}
