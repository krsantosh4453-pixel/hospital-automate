import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Interface languages, as on the web (English, हिंदी). Only interface text
/// is translated; clinical content is always shown as it was entered.
enum AppLanguage {
  en('EN'),
  hi('हिं');

  const AppLanguage(this.shortLabel);

  /// Label on the header toggle.
  final String shortLabel;

  Locale get locale => Locale(name);

  static AppLanguage parse(String? code) =>
      code == 'hi' ? AppLanguage.hi : AppLanguage.en;
}

/// Where the chosen language is remembered. Not sensitive, so plain
/// preferences are fine (tokens use the secure store).
abstract interface class LanguagePreference {
  Future<AppLanguage> read();
  Future<void> write(AppLanguage language);
}

class SharedPreferencesLanguagePreference implements LanguagePreference {
  /// Same key the web app uses in localStorage.
  static const _key = 'hms_language';

  @override
  Future<AppLanguage> read() async {
    final prefs = await SharedPreferences.getInstance();
    return AppLanguage.parse(prefs.getString(_key));
  }

  @override
  Future<void> write(AppLanguage language) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, language.name);
  }
}

/// Keeps the language in memory only; for tests.
class InMemoryLanguagePreference implements LanguagePreference {
  InMemoryLanguagePreference([this._language = AppLanguage.en]);

  AppLanguage _language;

  @override
  Future<AppLanguage> read() async => _language;

  @override
  Future<void> write(AppLanguage language) async => _language = language;
}

class LocaleController extends ChangeNotifier {
  LocaleController({
    required this._preference,
    AppLanguage initial = AppLanguage.en,
  }) : _language = initial;

  final LanguagePreference _preference;
  AppLanguage _language;

  AppLanguage get language => _language;
  Locale get locale => _language.locale;

  /// Switches the language now; a failed save only means it won't be remembered.
  Future<void> setLanguage(AppLanguage language) async {
    if (language == _language) return;
    _language = language;
    notifyListeners();
    try {
      await _preference.write(language);
    } on Exception {
      // The preference simply won't persist, as on the web in private mode.
    }
  }
}
