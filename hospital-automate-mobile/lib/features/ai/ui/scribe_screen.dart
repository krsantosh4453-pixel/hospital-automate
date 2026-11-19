import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/polling.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/data/doctor_models.dart';
import '../../doctor/ui/doctor_ui.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/ai_models.dart';
import '../data/ai_repository.dart';
import '../data/scribe_recorder.dart';
import 'ai_ui.dart';
import 'scribe_draft_card.dart';

/// Everything the scribe page shows for one visit.
class _ScribeData {
  const _ScribeData({
    required this.visit,
    required this.doctor,
    this.session,
    this.transcript,
    this.drafts = const [],
  });

  final Visit visit;
  final DoctorProfile? doctor;
  final ScribeSession? session;
  final ScribeTranscript? transcript;
  final List<ScribeDraft> drafts;

  /// Only the visit's own doctor may use the scribe (the server checks too).
  bool get isOwnDoctor =>
      doctor != null &&
      (visit.doctorId == null || visit.doctorId == doctor!.id);
  ScribeDraft? get latestDraft => drafts.isEmpty ? null : drafts.first;

  /// The server is still transcribing or drafting (queued work).
  bool get working =>
      (transcript?.inProgress ?? false) || (latestDraft?.generating ?? false);
}

/// How often the page checks on queued transcription or drafting.
const scribePollInterval = Duration(seconds: 3);

/// `/ai-scribe/visits/:visitId`: consent → record → transcript → AI draft →
/// the doctor's edits → explicit approval, which saves a clinical note
/// through the scribe API. The AI never completes the visit or prescribes.
class ScribeScreen extends StatefulWidget {
  const ScribeScreen({super.key, required this.visitId});

  final int visitId;

  @override
  State<ScribeScreen> createState() => _ScribeScreenState();
}

class _ScribeScreenState extends State<ScribeScreen> {
  late final AppServices _services = AppScope.read(context);
  late final AiRepository _ai = _services.ai;
  late final ScribeRecorder _recorder = _services.newScribeRecorder();
  late final RecordLoader<_ScribeData> _loader = RecordLoader(_load);

  String _language = 'en';
  bool _consent = false;
  bool _recording = false;
  bool _busy = false;
  String? _error;
  String? _notice;
  Poller? _poller;

  /// Polls while the server works on a queued step, and stops after.
  void _followWork() {
    final working = _loader.data?.working ?? false;
    if (working && _poller == null) {
      _poller = Poller(
        interval: scribePollInterval,
        onTick: _loader.load,
        isBusy: () => _loader.loading,
      );
    } else if (!working && _poller != null) {
      _poller!.dispose();
      _poller = null;
    }
  }

  Future<_ScribeData> _load() async {
    final doctors = _services.doctor;
    final visit = await doctors.visit(widget.visitId);
    final userId = _services.session.state.user?.id;
    DoctorProfile? doctor;
    if (visit.hospitalId != null && userId != null) {
      try {
        doctor = await doctors.myProfile(
          hospitalId: visit.hospitalId!,
          userId: userId,
        );
      } on ApiException {
        doctor = null;
      }
    }
    final sessions = await _ai.sessions(visitId: visit.id);
    final session = sessions.isEmpty ? null : sessions.first;
    if (session == null) return _ScribeData(visit: visit, doctor: doctor);
    final results = await Future.wait<Object?>([
      _ai.transcript(session.id),
      _ai.drafts(session.id),
    ]);
    return _ScribeData(
      visit: visit,
      doctor: doctor,
      session: session,
      transcript: results[0] as ScribeTranscript?,
      drafts: results[1]! as List<ScribeDraft>,
    );
  }

  @override
  void initState() {
    super.initState();
    _loader.addListener(_followWork);
    _loader.load().then((_) {
      final session = _loader.data?.session;
      if (mounted && session != null) {
        setState(() => _language = session.language);
      }
    });
  }

  @override
  void dispose() {
    _poller?.dispose();
    _loader.removeListener(_followWork);
    if (_recording) _recorder.cancel();
    _recorder.dispose();
    _loader.dispose();
    super.dispose();
  }

  /// Runs one step: shows progress, reports a safe error, then reloads.
  Future<void> _step(Future<void> Function() work, {String? done}) async {
    if (_busy) return;
    final t = context.l10n;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      await work();
      if (mounted && done != null) setState(() => _notice = done);
    } catch (error) {
      if (mounted) setState(() => _error = scribeErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _busy = false);
      await _loader.load();
    }
  }

  Future<void> _startRecording(_ScribeData data) async {
    final t = context.l10n;
    if (!await _recorder.requestPermission()) {
      setState(() => _error = t.aiMicDenied);
      return;
    }
    await _step(() async {
      var session = data.session;
      session ??= await _ai.createSession(
        visitId: data.visit.id,
        hospitalId: data.visit.hospitalId!,
        patientId: data.visit.patientId!,
        doctorId: data.doctor!.id,
        language: _language,
      );
      await _ai.startRecording(session.id, patientConsent: _consent);
      await _recorder.start();
      if (mounted) setState(() => _recording = true);
    });
  }

  Future<void> _stopRecording(_ScribeData data) async {
    final t = context.l10n;
    final audio = await _recorder.stop();
    if (!mounted) return;
    setState(() => _recording = false);
    if (audio == null || audio.duration == Duration.zero) {
      setState(() => _error = t.aiNothingRecorded);
      return;
    }
    try {
      await _step(
        () => _ai.stopRecording(data.session!.id, audio),
        done: t.aiAudioUploaded,
      );
    } finally {
      // The server keeps the uploaded copy; never leave PHI audio in the cache.
      await _recorder.discard(audio);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return ListenableBuilder(
      listenable: _loader,
      builder: (context, _) {
        final error = _loader.error;
        if (_loader.data == null &&
            error is ApiException &&
            (error.kind == ApiErrorKind.notFound ||
                error.kind == ApiErrorKind.forbidden)) {
          return HmsCard(
            child: HmsEmptyState(
              icon: LucideIcons.shieldAlert,
              title: t.patientNotInCare,
              description: t.patientNotInCareHint,
            ),
          );
        }
        return RecordSection<_ScribeData>(
          loader: _loader,
          builder: (context, data) => _body(t, data),
        );
      },
    );
  }

  Widget _body(AppLocalizations t, _ScribeData data) {
    final visit = data.visit;
    final canWrite = data.isOwnDoctor;
    final draft = data.latestDraft;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.aiScribeTitle,
          description: [
            visit.patientName ?? t.patientLabel,
            formatDateTime(t, visit.visitDate),
          ].join(' · '),
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsAlert(
          tone: AlertTone.warning,
          title: t.aiSafetyTitle,
          message: t.aiSafetyBody,
        ),
        if (!canWrite) ...[
          const SizedBox(height: AppSpacing.x3),
          HmsAlert(title: t.aiReadOnly),
        ],
        if (_error != null) ...[
          const SizedBox(height: AppSpacing.x3),
          HmsAlert(
            key: const Key('scribe-error'),
            tone: AlertTone.danger,
            title: _error!,
          ),
        ],
        if (_notice != null) ...[
          const SizedBox(height: AppSpacing.x3),
          HmsAlert(tone: AlertTone.success, title: _notice!),
        ],
        sectionGap,
        _recordCard(t, data, canWrite: canWrite && visit.isOpen),
        sectionGap,
        _transcriptCard(t, data, canWrite: canWrite),
        sectionGap,
        ScribeDraftCard(
          draft: draft,
          canWrite: canWrite,
          transcriptReady: data.transcript?.isReady ?? false,
          busy: _busy,
          actions: DraftActions(
            generate: () => _step(() => _ai.generate(draft!.id)),
            saveSection: (section, text) => _step(
              () => _ai.editSection(
                draft!.id,
                section: section,
                aiValue: draft.extraction[section.key] ?? '',
                doctorValue: ScribeDraft.sectionValue(section, text),
              ),
            ),
            approve: () =>
                _step(() => _ai.approve(draft!.id), done: t.aiDraftApproved),
            reject: () => _step(() => _ai.reject(draft!.id)),
            regenerate: () => _step(() => _ai.regenerate(draft!.id)),
          ),
        ),
      ],
    );
  }

  Widget _recordCard(
    AppLocalizations t,
    _ScribeData data, {
    required bool canWrite,
  }) {
    final session = data.session;
    final consentOnFile = session?.consentRecorded ?? false;
    final mayStart = canWrite && (_consent || consentOnFile) && !_busy;
    return HmsCard(
      key: const Key('scribe-record'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.aiStepRecord, icon: LucideIcons.mic),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(t.aiSpokenLanguage, style: AppTypography.small()),
                const SizedBox(height: AppSpacing.x2),
                Wrap(
                  spacing: AppSpacing.x2,
                  children: [
                    for (final code in scribeLanguages)
                      ChoiceChip(
                        label: Text(languageLabel(t, code)),
                        selected: _language == code,
                        onSelected: canWrite && !_recording
                            ? (_) => setState(() => _language = code)
                            : null,
                      ),
                  ],
                ),
                const SizedBox(height: AppSpacing.x3),
                if (consentOnFile)
                  Text(t.aiConsentRecorded, style: AppTypography.small())
                else
                  CheckboxListTile(
                    key: const Key('scribe-consent'),
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    value: _consent,
                    onChanged: canWrite && !_recording
                        ? (value) => setState(() => _consent = value ?? false)
                        : null,
                    title: Text(t.aiConsentLabel, style: AppTypography.body()),
                  ),
                if (session?.hasAudio ?? false) ...[
                  const SizedBox(height: AppSpacing.x2),
                  Text(t.aiAudioUploaded, style: AppTypography.small()),
                ],
                const SizedBox(height: AppSpacing.x3),
                if (_recording) ...[
                  Text(t.aiRecordingNow, style: AppTypography.body()),
                  const SizedBox(height: AppSpacing.x2),
                  HmsButton(
                    key: const Key('stop-recording'),
                    label: t.aiStopRecording,
                    icon: LucideIcons.square,
                    surface: HmsSurface.card,
                    loading: _busy,
                    onPressed: _busy ? null : () => _stopRecording(data),
                  ),
                ] else if (canWrite)
                  HmsButton(
                    key: const Key('start-recording'),
                    label: (session?.hasAudio ?? false)
                        ? t.aiRecordAgain
                        : t.aiStartRecording,
                    icon: LucideIcons.mic,
                    surface: HmsSurface.card,
                    onPressed: mayStart ? () => _startRecording(data) : null,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _transcriptCard(
    AppLocalizations t,
    _ScribeData data, {
    required bool canWrite,
  }) {
    final session = data.session;
    final transcript = data.transcript;
    final canTranscribe =
        canWrite && (session?.hasAudio ?? false) && !_recording && !_busy;
    return HmsCard(
      key: const Key('scribe-transcript'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.aiStepTranscript, icon: LucideIcons.text),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (transcript?.inProgress ?? false)
                  const _Working(key: Key('transcript-working'))
                else if (transcript?.isReady ?? false)
                  SelectableText(
                    transcript!.text,
                    key: const Key('transcript-text'),
                    style: AppTypography.body(),
                  )
                else if (transcript?.status == TranscriptStatus.failed)
                  HmsAlert(tone: AlertTone.danger, title: t.aiTranscriptFailed)
                else
                  Text(t.aiNoTranscriptYet, style: AppTypography.small()),
                if (canWrite &&
                    !(transcript?.isReady ?? false) &&
                    !(transcript?.inProgress ?? false)) ...[
                  const SizedBox(height: AppSpacing.x3),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: HmsButton(
                      key: const Key('transcribe'),
                      label: t.aiTranscribe,
                      surface: HmsSurface.card,
                      loading: _busy,
                      onPressed: canTranscribe
                          ? () => _step(
                              () => _ai.transcribe(
                                session!.id,
                                language: _language,
                              ),
                            )
                          : null,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// "The server is working on it" row for queued transcription or drafting.
class _Working extends StatelessWidget {
  const _Working({super.key});

  @override
  Widget build(BuildContext context) => Row(
    children: [
      const SizedBox.square(
        dimension: 16,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
      const SizedBox(width: AppSpacing.x3),
      Expanded(
        child: Text(context.l10n.aiWorking, style: AppTypography.small()),
      ),
    ],
  );
}
