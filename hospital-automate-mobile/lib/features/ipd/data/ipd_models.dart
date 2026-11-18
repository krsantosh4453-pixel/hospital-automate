import 'package:flutter/foundation.dart';

import '../../patient/data/json_read.dart';

/// Admission.STATUS_CHOICES (ipd/models.py).
abstract final class AdmissionStatus {
  static const admitted = 'Admitted';
  static const dischargeInitiated = 'Discharge Initiated';
  static const discharged = 'Discharged';
  static const transferred = 'Transferred';
  static const cancelled = 'Cancelled';

  static const all = [
    admitted,
    dischargeInitiated,
    discharged,
    transferred,
    cancelled,
  ];
}

/// Bed states the server accepts (hospital/serializers.py BED_STATUSES).
abstract final class BedStatus {
  static const available = 'Available';
  static const occupied = 'Occupied';
  static const reserved = 'Reserved';
  static const cleaning = 'Cleaning';
  static const maintenance = 'Maintenance';

  static const all = [available, occupied, reserved, cleaning, maintenance];
}

/// Where a bed is: ward, room and bed number.
@immutable
class BedPlace {
  const BedPlace({this.ward, this.room, this.bed});

  final String? ward;
  final String? room;
  final String? bed;

  String get label => [
    ward,
    room,
    bed,
  ].whereType<String>().where((s) => s.isNotEmpty).join(' · ');
}

/// One `BedAllocationSerializer` row: a bed an admission held or holds.
@immutable
class BedAllocationRecord {
  const BedAllocationRecord({
    required this.id,
    required this.place,
    required this.isActive,
    this.bedId,
    this.allocatedAt,
    this.releasedAt,
  });

  factory BedAllocationRecord.fromJson(Map<String, Object?> json) =>
      BedAllocationRecord(
        id: readInt(json['id']) ?? 0,
        bedId: readInt(json['bed']),
        isActive: json['is_active'] == true,
        allocatedAt: readDateTime(json['allocated_at']),
        releasedAt: readDateTime(json['released_at']),
        place: BedPlace(
          ward: readText(json['ward_name']),
          room: readText(json['room_number']),
          bed: readText(json['bed_number']),
        ),
      );

  final int id;
  final int? bedId;
  final BedPlace place;
  final bool isActive;
  final DateTime? allocatedAt;
  final DateTime? releasedAt;
}

/// An inpatient stay as `AdmissionSerializer` sends it, with its bed history.
@immutable
class IpdAdmission {
  const IpdAdmission({
    required this.id,
    required this.status,
    this.patientId,
    this.patientName,
    this.admissionDate,
    this.dischargeDate,
    this.reason,
    this.admittingDoctorName,
    this.currentBed,
    this.bedHistory = const [],
  });

  factory IpdAdmission.fromJson(Map<String, Object?> json) {
    final current = json['current_bed'];
    return IpdAdmission(
      id: readInt(json['id']) ?? 0,
      status: readText(json['status']) ?? '',
      patientId: readInt(json['patient']),
      patientName: readText(json['patient_name']),
      admissionDate: readDateTime(json['admission_date']),
      dischargeDate: readDateTime(json['discharge_date']),
      reason: readText(json['reason']),
      admittingDoctorName: readText(json['admitting_doctor_name']),
      currentBed: current is Map
          ? BedAllocationRecord.fromJson(asMap(current))
          : null,
      bedHistory: List.unmodifiable(
        readRows(json['bed_allocations']).map(BedAllocationRecord.fromJson),
      ),
    );
  }

  final int id;
  final String status;
  final int? patientId;
  final String? patientName;
  final DateTime? admissionDate;
  final DateTime? dischargeDate;
  final String? reason;
  final String? admittingDoctorName;
  final BedAllocationRecord? currentBed;
  final List<BedAllocationRecord> bedHistory;

  bool get isAdmitted => status == AdmissionStatus.admitted;
  bool get isDischarging => status == AdmissionStatus.dischargeInitiated;

  /// Bed moves the server allows (ipd/views.py): a first bed only while
  /// Admitted (`allocate_bed`); a transfer whenever a bed is held.
  bool get canAllocateBed => isAdmitted && currentBed == null;
  bool get canTransferBed =>
      currentBed != null && (isAdmitted || isDischarging);
  bool get canInitiateDischarge => isAdmitted;
}

/// A bed the server lists as free (`available_beds`).
@immutable
class AvailableBed {
  const AvailableBed({required this.id, required this.place, this.roomType});

  factory AvailableBed.fromJson(Map<String, Object?> json) => AvailableBed(
    id: readInt(json['id']) ?? 0,
    roomType: readText(json['room_type']),
    place: BedPlace(
      ward: readText(json['ward']),
      room: readText(json['room']),
      bed: readText(json['bed_number']),
    ),
  );

  final int id;
  final BedPlace place;
  final String? roomType;
}

/// A bed of the hospital (`hospital/beds/`) with whoever holds it.
@immutable
class HospitalBed {
  const HospitalBed({
    required this.id,
    required this.status,
    required this.place,
    this.wardId,
    this.bedType,
    this.currentPatient,
  });

  factory HospitalBed.fromJson(Map<String, Object?> json) => HospitalBed(
    id: readInt(json['id']) ?? 0,
    status: readText(json['status']) ?? '',
    wardId: readInt(json['ward']),
    bedType: readText(json['bed_type']),
    currentPatient: readText(json['current_patient']),
    place: BedPlace(
      ward: readText(json['ward_name']),
      room: readText(json['room_number']),
      bed: readText(json['bed_number']),
    ),
  );

  final int id;
  final String status;
  final BedPlace place;
  final int? wardId;
  final String? bedType;
  final String? currentPatient;
}

/// The bed list, and whether it was read to the end (the app stops after a
/// bounded number of pages and then says the counts are partial).
@immutable
class BedBoard {
  const BedBoard({required this.beds, required this.complete});

  final List<HospitalBed> beds;
  final bool complete;

  int count(String status) => beds.where((b) => b.status == status).length;

  /// Beds grouped by ward name, in the order the server listed them.
  Map<String, List<HospitalBed>> byWard() {
    final groups = <String, List<HospitalBed>>{};
    for (final bed in beds) {
      groups.putIfAbsent(bed.place.ward ?? '—', () => []).add(bed);
    }
    return Map.unmodifiable({
      for (final entry in groups.entries)
        entry.key: List<HospitalBed>.unmodifiable(entry.value),
    });
  }
}

/// The final bill of a stay, as `discharge.invoice_brief` sends it.
@immutable
class FinalBill {
  const FinalBill({
    required this.id,
    this.number,
    this.status,
    this.total,
    this.balanceDue,
  });

  factory FinalBill.fromJson(Map<String, Object?> json) => FinalBill(
    id: readInt(json['id']) ?? 0,
    number: readText(json['invoice_number']),
    status: readText(json['status']),
    total: readMoney(json['total']),
    balanceDue: readMoney(json['balance_due']),
  );

  final int id;
  final String? number;
  final String? status;
  final double? total;
  final double? balanceDue;
}

/// One discharge checklist item (ipd/discharge.py CHECKLIST).
@immutable
class ChecklistItem {
  const ChecklistItem({
    required this.field,
    required this.label,
    required this.done,
  });

  factory ChecklistItem.fromJson(Map<String, Object?> json) => ChecklistItem(
    field: readText(json['field']) ?? '',
    label: readText(json['label']) ?? '',
    done: json['done'] == true,
  );

  final String field;
  final String label;
  final bool done;
}

/// What still stands between an admission and a completed discharge
/// (`GET ipd/admissions/{id}/readiness/`). [ready] is the server's verdict;
/// the app only offers "Complete discharge" when it is true.
@immutable
class DischargeReadiness {
  const DischargeReadiness({
    required this.ready,
    this.serverBlockers = const [],
    this.checklist = const [],
    this.hasPlan = false,
    this.summaryFinalized = false,
    this.finalBill,
    this.days,
  });

  factory DischargeReadiness.fromJson(Map<String, Object?> json) {
    final bill = json['final_invoice'];
    final blockers = json['blockers'];
    return DischargeReadiness(
      ready: json['ready'] == true,
      serverBlockers: List.unmodifiable([
        if (blockers is List)
          for (final item in blockers)
            if (readText(item) != null) readText(item)!,
      ]),
      checklist: List.unmodifiable(
        readRows(json['checklist']).map(ChecklistItem.fromJson),
      ),
      hasPlan: json['plan'] != null,
      summaryFinalized: json['summary_finalized'] == true,
      finalBill: bill is Map ? FinalBill.fromJson(asMap(bill)) : null,
      days: readInt(json['days']),
    );
  }

  final bool ready;

  /// The server's own sentences (English). Shown only when the structured
  /// fields explain nothing, e.g. a blocker this app does not know yet.
  final List<String> serverBlockers;
  final List<ChecklistItem> checklist;
  final bool hasPlan;
  final bool summaryFinalized;
  final FinalBill? finalBill;
  final int? days;

  bool get billPaid {
    final due = finalBill?.balanceDue;
    return due != null && due <= 0;
  }
}

/// A doctor's discharge summary; locked once [finalized].
@immutable
class DischargeSummaryRecord {
  const DischargeSummaryRecord({
    required this.id,
    required this.admissionId,
    required this.summary,
    required this.finalized,
    this.doctorName,
    this.finalizedAt,
  });

  factory DischargeSummaryRecord.fromJson(Map<String, Object?> json) =>
      DischargeSummaryRecord(
        id: readInt(json['id']) ?? 0,
        admissionId: readInt(json['admission']) ?? 0,
        summary: readText(json['summary']) ?? '',
        finalized: json['finalized'] == true,
        doctorName: readText(json['authorized_doctor_name']),
        finalizedAt: readDateTime(json['finalized_at']),
      );

  final int id;
  final int admissionId;
  final String summary;
  final bool finalized;
  final String? doctorName;
  final DateTime? finalizedAt;
}

/// Totals for the IPD dashboard: the server's own `count` per status (only
/// stays this login may see). Null when that count could not be read.
@immutable
class IpdOverview {
  const IpdOverview({
    this.admitted,
    this.dischargeInitiated,
    this.discharged,
    this.availableBeds,
  });

  final int? admitted;
  final int? dischargeInitiated;
  final int? discharged;
  final int? availableBeds;
}
