import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/security/session_controller.dart';
import '../data/dispense_plan.dart';

/// Pharmacy pages keep the web's `/pharmacy` path; a prescription or a
/// medicine sits below it, so breadcrumbs and the module check still apply.
abstract final class PharmacyRoutes {
  static const home = '/pharmacy';

  static String prescription(int id) => '$home/prescriptions/$id';
  static String medicine(int id) => '$home/medicines/$id';
}

/// Roles that dispense (SaleViewSet). Only a Pharmacist may give a
/// same-salt substitute; the server enforces it.
const pharmacyRoles = {'Pharmacist', 'Compounder'};

bool isPharmacyStaff(SessionState session) =>
    session.isStaff && pharmacyRoles.contains(session.activeRole);

bool maySubstitute(SessionState session) =>
    session.isStaff && session.activeRole == 'Pharmacist';

String availabilityLabel(AppLocalizations t, Availability a) => switch (a) {
  Availability.done => t.availabilityDone,
  Availability.inStock => t.availabilityInStock,
  Availability.split => t.availabilitySplit,
  Availability.short => t.availabilityShort,
  Availability.none => t.availabilityNone,
};

String movementLabel(AppLocalizations t, String type) => switch (type) {
  'IN' => t.stockIn,
  'OUT' => t.stockOut,
  'ADJUST' => t.stockAdjust,
  _ => type,
};

String dispenseProblemText(AppLocalizations t, DispenseProblem p) =>
    switch (p.kind) {
      DispenseProblemKind.tooMany => t.dispenseTooMany(
        p.medicine ?? '',
        p.limit ?? 0,
      ),
      DispenseProblemKind.noBatch => t.dispenseNoBatch(p.medicine ?? ''),
      DispenseProblemKind.noReason => t.dispenseNoReason(p.medicine ?? ''),
      DispenseProblemKind.nothingChosen => t.dispenseNothingChosen,
    };

/// A safe sentence for a refused dispense. 409: already dispensed; 400: the
/// server's stock, quantity, expiry or substitution check failed; a network
/// failure may have dispensed or not, so the screen reloads to show which.
String dispenseErrorMessage(AppLocalizations t, Object error) {
  if (error is! ApiException) return t.errorUnknown;
  return switch (error.kind) {
    ApiErrorKind.conflict => t.alreadyDispensed,
    ApiErrorKind.validation => t.dispenseRefused,
    ApiErrorKind.network || ApiErrorKind.timeout => t.dispenseOutcomeUnknown,
    _ => apiErrorMessage(t, error),
  };
}
