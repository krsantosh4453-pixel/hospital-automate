import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/localization/l10n.dart';
import 'package:hms_mobile/core/localization/locale_controller.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_hi.dart';

class _FailingPreference implements LanguagePreference {
  @override
  Future<AppLanguage> read() async => AppLanguage.en;

  @override
  Future<void> write(AppLanguage language) async =>
      throw Exception('disk full');
}

void main() {
  test('switching language notifies and remembers the choice', () async {
    final preference = InMemoryLanguagePreference();
    final controller = LocaleController(preference: preference);
    var notified = 0;
    controller.addListener(() => notified++);

    await controller.setLanguage(AppLanguage.hi);

    expect(controller.locale.languageCode, 'hi');
    expect(notified, 1);
    expect(await preference.read(), AppLanguage.hi);
  });

  test('a failed save still switches the language', () async {
    final controller = LocaleController(preference: _FailingPreference());

    await controller.setLanguage(AppLanguage.hi);

    expect(controller.language, AppLanguage.hi);
  });

  test('unknown stored codes fall back to English, as on the web', () {
    expect(AppLanguage.parse('fr'), AppLanguage.en);
    expect(AppLanguage.parse(null), AppLanguage.en);
  });

  test('Hindi uses the same translations as the web app', () {
    final hi = AppLocalizationsHi();

    expect(hi.navPatients, 'मरीज़');
    expect(hi.groupFrontDesk, 'रिसेप्शन');
    expect(hi.staffSignIn, 'स्टाफ़ साइन इन');
  });

  test('API errors become safe, translated messages', () {
    final en = AppLocalizationsEn();

    expect(
      apiErrorMessage(en, const ApiException(kind: ApiErrorKind.forbidden)),
      en.errorForbidden,
    );
    expect(apiErrorMessage(en, StateError('internal detail')), en.errorUnknown);
  });
}
