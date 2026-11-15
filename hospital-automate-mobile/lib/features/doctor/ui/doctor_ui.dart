import 'package:flutter/material.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/security/session_controller.dart';

/// Doctor pages keep the web's paths (src/config/navigation.js); the record
/// and consultation pages add an id below them, so breadcrumbs and the
/// router's module check still apply.
abstract final class DoctorRoutes {
  static const appointments = '/appointments';
  static const queue = '/queue';
  static const patients = '/patients';
  static const consultation = '/consultation';
  static const prescriptions = '/prescription';
  static const laboratory = '/laboratory';

  static String patient(int id) => '$patients/$id';
  static String visit(int id) => '$consultation/$id';
}

/// The role these screens are for. Other roles keep the placeholder until
/// their own module is built; the server checks every request anyway.
const doctorRole = 'Doctor';

bool isDoctor(SessionState session) =>
    session.isStaff && session.activeRole == doctorRole;

/// A safe sentence for a refused clinical write. Validation errors name the
/// fields at fault (never the server's raw text); a signed record and an
/// invalid queue move get their own message.
String clinicalErrorMessage(
  AppLocalizations t,
  Object error, {
  Map<String, String> fieldLabels = const {},
}) {
  if (error is! ApiException) return t.errorUnknown;
  if (error.kind == ApiErrorKind.conflict) return t.recordSignedNoChange;
  if (error.kind == ApiErrorKind.validation && error.fieldErrors.isNotEmpty) {
    final fields = [
      for (final key in error.fieldErrors.keys) fieldLabels[key] ?? key,
    ];
    return t.checkTheseFields(fields.join(', '));
  }
  return apiErrorMessage(t, error);
}

/// Today as a calendar day in the phone's time zone.
DateTime today([DateTime Function()? now]) {
  final clock = (now ?? DateTime.now)();
  return DateTime(clock.year, clock.month, clock.day);
}

/// Spacing between stacked sections of a doctor page.
const sectionGap = SizedBox(height: 24);
