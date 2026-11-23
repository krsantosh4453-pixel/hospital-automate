import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/security/session_controller.dart';
import '../../patient/ui/patient_ui.dart' show statusLabel;

/// Nursing pages keep the web's `/nurses` path; a patient's ward record
/// sits below it, so breadcrumbs and the router's module check still apply.
abstract final class NursingRoutes {
  static const ward = '/nurses';

  static String patient(int id) => '$ward/patients/$id';
}

/// The role these screens are for. Other roles keep the placeholder; the
/// server checks every request anyway.
const nurseRole = 'Nurse';

bool isNurse(SessionState session) =>
    session.isStaff && session.activeRole == nurseRole;

String noteTypeLabel(AppLocalizations t, String type) => switch (type) {
  'Progress' => t.noteTypeProgress,
  'Incident' => t.noteTypeIncident,
  'Communication' => t.noteTypeCommunication,
  'Education' => t.noteTypeEducation,
  'Handoff' => t.noteTypeHandoff,
  _ => type,
};

String doseStatusLabel(AppLocalizations t, String status) => switch (status) {
  'Scheduled' => t.doseDue,
  'Administered' => t.doseGiven,
  'Held' => t.doseHeld,
  'Refused' => t.doseRefused,
  'Missed' => t.doseMissed,
  'Vomited' => t.doseVomited,
  'Excluded' => t.doseExcluded,
  _ => status,
};

String wardStatusLabel(AppLocalizations t, String status) => switch (status) {
  'Admitted' => t.statusAdmitted,
  'Discharge Initiated' => t.statusDischargeInitiated,
  'Discharged' => t.statusDischarged,
  'In Progress' => t.statusInProgress,
  'Deferred' => t.statusDeferred,
  _ => statusLabel(t, status),
};

String taskPriorityLabel(AppLocalizations t, String priority) =>
    switch (priority) {
      'Routine' => t.priorityRoutine,
      'Urgent' => t.statusUrgent,
      'Stat' => t.priorityStat,
      _ => priority,
    };

String shiftLabel(AppLocalizations t, String shift) => switch (shift) {
  'Morning' => t.shiftMorning,
  'Evening' => t.shiftEvening,
  'Night' => t.shiftNight,
  _ => shift,
};

/// Label of a key in an assessment's `vitals` JSON (as the web writes it).
String wardVitalLabel(AppLocalizations t, String key) => switch (key) {
  'bp' => t.vitalBloodPressure,
  'pulse' => t.vitalPulse,
  'spo2' => t.vitalSpo2,
  'temperature' => t.vitalTemperature,
  'respiratory_rate' => t.vitalRespiratoryRate,
  _ => key,
};

/// A safe sentence for a refused dose. The server answers 400 when the dose
/// was already recorded (perhaps by another nurse) or its order is no longer
/// in force; the raw server text is never shown.
String doseErrorMessage(AppLocalizations t, Object error) {
  if (error is ApiException && error.kind == ApiErrorKind.validation) {
    return t.doseNotRecorded;
  }
  if (error is ApiException &&
      (error.kind == ApiErrorKind.network ||
          error.kind == ApiErrorKind.timeout)) {
    return t.doseOutcomeUnknown;
  }
  return apiErrorMessage(t, error);
}
