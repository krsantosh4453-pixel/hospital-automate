import 'package:flutter/widgets.dart';

import '../../l10n/generated/app_localizations.dart';
import '../network/api_exception.dart';

export '../../l10n/generated/app_localizations.dart';

extension L10nContext on BuildContext {
  /// Interface strings for the current language: `context.l10n.navHome`.
  AppLocalizations get l10n => AppLocalizations.of(this);
}

/// A safe, translated explanation of [error] for the screen.
String apiErrorMessage(AppLocalizations l10n, Object error) {
  if (error is! ApiException) return l10n.errorUnknown;
  return switch (error.kind) {
    ApiErrorKind.network => l10n.errorNetwork,
    ApiErrorKind.timeout => l10n.errorTimeout,
    ApiErrorKind.unauthorized => l10n.errorUnauthorized,
    ApiErrorKind.forbidden => l10n.errorForbidden,
    ApiErrorKind.notFound => l10n.errorNotFound,
    ApiErrorKind.validation => l10n.errorValidation,
    ApiErrorKind.conflict => l10n.errorConflict,
    ApiErrorKind.rateLimited => l10n.errorRateLimited,
    ApiErrorKind.server => l10n.errorServer,
    ApiErrorKind.unavailable => l10n.errorUnavailable,
    ApiErrorKind.unknown => l10n.errorUnknown,
  };
}
