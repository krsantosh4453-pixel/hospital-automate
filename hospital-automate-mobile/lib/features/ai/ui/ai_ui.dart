import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../data/ai_models.dart';

/// AI pages sit under the web's `/ai-scribe` path, so the sidebar's
/// AIScribe module check covers them.
abstract final class AiRoutes {
  static const home = '/ai-scribe';

  static String visit(int visitId) => '$home/visits/$visitId';
}

/// Spoken-language codes the server accepts (ai_scribe/services/languages.py).
const scribeLanguages = ['en', 'hi', 'hinglish', 'auto'];

String languageLabel(AppLocalizations t, String code) => switch (code) {
  'hi' => t.aiLangHi,
  'hinglish' => t.aiLangHinglish,
  'auto' => t.aiLangAuto,
  _ => t.aiLangEn,
};

String sectionLabel(AppLocalizations t, DraftSection section) =>
    switch (section) {
      DraftSection.chiefComplaint => t.aiSecChiefComplaint,
      DraftSection.symptoms => t.aiSecSymptoms,
      DraftSection.history => t.aiSecHistory,
      DraftSection.allergies => t.aiSecAllergies,
      DraftSection.medications => t.aiSecMedications,
      DraftSection.examination => t.aiSecExamination,
      DraftSection.vitals => t.aiSecVitals,
      DraftSection.assessment => t.aiSecAssessment,
      DraftSection.investigations => t.aiSecInvestigations,
      DraftSection.plan => t.aiSecPlan,
      DraftSection.followUp => t.aiSecFollowUp,
      DraftSection.summary => t.aiSecSummary,
    };

/// "provider · model", or "not configured".
String engineLabel(AppLocalizations t, AiEngine engine) {
  if (!engine.available) return t.aiEngineNotConfigured;
  return [engine.provider, engine.model].where((s) => s.isNotEmpty).join(' · ');
}

/// A safe sentence for a failed scribe step: the provider being down and a
/// doctor who is not the consulting one get their own message.
String scribeErrorMessage(AppLocalizations t, Object error) {
  if (error is ApiException) {
    if (error.kind == ApiErrorKind.unavailable || error.statusCode == 503) {
      return t.aiProviderUnavailable;
    }
    if (error.kind == ApiErrorKind.forbidden) return t.aiNotConsultingDoctor;
  }
  return apiErrorMessage(t, error);
}
