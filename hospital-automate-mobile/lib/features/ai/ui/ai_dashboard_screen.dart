import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/ui/doctor_ui.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/ai_models.dart';
import 'ai_ui.dart';

class _Dashboard {
  const _Dashboard(this.capabilities, this.sessions);

  final AiCapabilities capabilities;
  final List<ScribeSession> sessions;
}

/// `/ai-scribe`: what AI the server offers, the image-prediction status and
/// the doctor's scribe sessions (the server lists only their patients').
class AiDashboardScreen extends StatefulWidget {
  const AiDashboardScreen({super.key});

  @override
  State<AiDashboardScreen> createState() => _AiDashboardScreenState();
}

class _AiDashboardScreenState extends State<AiDashboardScreen> {
  late final RecordLoader<_Dashboard> _loader = RecordLoader(_load);

  Future<_Dashboard> _load() async {
    final ai = AppScope.read(context).ai;
    final results = await Future.wait([ai.capabilities(), ai.sessions()]);
    return _Dashboard(
      results[0] as AiCapabilities,
      results[1] as List<ScribeSession>,
    );
  }

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _loader.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.aiTitle, description: t.aiIntro),
        const SizedBox(height: AppSpacing.x4),
        HmsAlert(
          tone: AlertTone.warning,
          title: t.aiSafetyTitle,
          message: t.aiSafetyBody,
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<_Dashboard>(
          loader: _loader,
          builder: (context, data) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _ScribeStatusCard(capabilities: data.capabilities),
              sectionGap,
              _CnnCard(capabilities: data.capabilities),
              sectionGap,
              _SessionsCard(sessions: data.sessions),
            ],
          ),
        ),
      ],
    );
  }
}

class _ScribeStatusCard extends StatelessWidget {
  const _ScribeStatusCard({required this.capabilities});

  final AiCapabilities capabilities;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    Widget row(String label, AiEngine engine) => Padding(
      padding: AppSpacing.cardRow,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppTypography.small()),
          Text(
            engineLabel(t, engine),
            style: AppTypography.body(weight: FontWeight.w600),
          ),
          if (engine.mock)
            Text(t.aiMockEngine, style: AppTypography.caption()),
        ],
      ),
    );
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.aiScribeCardTitle, icon: LucideIcons.mic),
          HmsDividedColumn(
            children: [
              row(t.aiSpeechToText, capabilities.speechToText),
              row(t.aiDrafting, capabilities.drafting),
            ],
          ),
        ],
      ),
    );
  }
}

/// Image prediction is BLOCKED until a validated model, dataset and
/// approved use case exist; the card says so instead of offering anything.
class _CnnCard extends StatelessWidget {
  const _CnnCard({required this.capabilities});

  final AiCapabilities capabilities;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      key: const Key('cnn-status'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: t.aiCnnTitle,
            icon: LucideIcons.scanLine,
            trailing: capabilities.imagePredictionAvailable
                ? null
                : StatusBadge(status: 'Cancelled', label: t.aiCnnBlocked),
          ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x4),
            child: Text(t.aiCnnBlockedBody, style: AppTypography.body()),
          ),
        ],
      ),
    );
  }
}

class _SessionsCard extends StatelessWidget {
  const _SessionsCard({required this.sessions});

  final List<ScribeSession> sessions;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.aiSessionsTitle, icon: LucideIcons.fileText),
          if (sessions.isEmpty)
            HmsEmptyState(
              icon: LucideIcons.stethoscope,
              title: t.aiNoSessions,
              description: t.aiNoSessionsHint,
              action: HmsButton(
                label: t.aiOpenConsultations,
                variant: HmsButtonVariant.secondary,
                surface: HmsSurface.card,
                onPressed: () => context.go(DoctorRoutes.consultation),
              ),
            )
          else
            HmsDividedColumn(
              children: [
                for (final s in sessions)
                  InkWell(
                    onTap: s.visitId == null
                        ? null
                        : () => context.go(AiRoutes.visit(s.visitId!)),
                    child: Padding(
                      padding: AppSpacing.cardRow,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            s.patientName ?? t.patientLabel,
                            style: AppTypography.body(
                              weight: FontWeight.w600,
                            ),
                          ),
                          Text(
                            [
                              languageLabel(t, s.language),
                              formatDateTime(t, s.startedAt),
                            ].join(' · '),
                            style: AppTypography.small(),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}
