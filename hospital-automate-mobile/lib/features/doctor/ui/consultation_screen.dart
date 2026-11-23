import 'package:flutter/material.dart';

import '../../ipd/ui/ipd_ui.dart' show IpdRoutes;
import '../../ipd/ui/clinical_work_sections.dart';

import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../ai/ui/ai_ui.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/doctor_models.dart';
import '../data/doctor_repository.dart';
import 'consultation_sections.dart';
import 'doctor_ui.dart';
import 'order_sections.dart';

/// `/consultation`: the doctor's visits, open ones first (the server returns
/// only visits of patients in their care).
class ConsultationListScreen extends StatefulWidget {
  const ConsultationListScreen({super.key});

  @override
  State<ConsultationListScreen> createState() => _ConsultationListScreenState();
}

class _ConsultationListScreenState extends State<ConsultationListScreen> {
  late final RecordLoader<List<Visit>> _loader = RecordLoader(
    AppScope.read(context).doctor.visits,
  );
  bool _openOnly = true;

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
        PageHeader(title: t.navConsultation, description: t.consultationIntro),
        const SizedBox(height: AppSpacing.x4),
        Wrap(
          spacing: AppSpacing.x2,
          children: [
            ChoiceChip(
              label: Text(t.openVisits),
              selected: _openOnly,
              onSelected: (_) => setState(() => _openOnly = true),
            ),
            ChoiceChip(
              label: Text(t.filterAll),
              selected: !_openOnly,
              onSelected: (_) => setState(() => _openOnly = false),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<Visit>>(
          loader: _loader,
          builder: (context, visits) {
            final shown = [
              for (final v in visits)
                if (!_openOnly || v.isOpen) v,
            ];
            if (shown.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.stethoscope,
                  title: t.noVisitsToShow,
                  description: t.noVisitsToShowHint,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [
                  for (final v in shown)
                    InkWell(
                      onTap: () => context.go(DoctorRoutes.visit(v.id)),
                      child: Padding(
                        padding: AppSpacing.cardRow,
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    v.patientName ?? t.patientLabel,
                                    style: AppTypography.body(
                                      weight: FontWeight.w600,
                                    ),
                                  ),
                                  Text(
                                    [
                                      ?v.visitType,
                                      formatDateTime(t, v.visitDate),
                                    ].join(' · '),
                                    style: AppTypography.small(),
                                  ),
                                  if (v.chiefComplaint != null)
                                    Text(
                                      v.chiefComplaint!,
                                      style: AppTypography.caption(),
                                    ),
                                  // Under the text so a long status never squeezes the name.
                                  const SizedBox(height: AppSpacing.x1),
                                  StatusBadge(status: v.status),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

/// Why the server refused a Start or Complete (flags set by the visit
/// lifecycle, `encounters/services/visit_lifecycle.py`).
String _statusErrorMessage(AppLocalizations t, Object error) {
  if (error is ApiException) {
    if (error.hasFlag('patient_not_called')) return t.visitPatientNotCalled;
    if (error.hasFlag('doctor_busy')) return t.queueDoctorBusy;
    if (error.hasFlag('invalid_transition')) return t.visitStatusMovedOn;
    if (error.hasFlag('not_visit_doctor')) return t.visitNotYourPatient;
  }
  return clinicalErrorMessage(t, error);
}

/// The visit, and the doctor's own profile at its hospital.
class _VisitData {
  const _VisitData(this.visit, this.doctor);

  final Visit visit;
  final DoctorProfile? doctor;
}

/// `/consultation/:visitId`: one consultation. Records are added while the
/// visit is open and the doctor's own; others are shown read-only.
class ConsultationScreen extends StatefulWidget {
  const ConsultationScreen({super.key, required this.visitId});

  final int visitId;

  @override
  State<ConsultationScreen> createState() => _ConsultationScreenState();
}

class _ConsultationScreenState extends State<ConsultationScreen> {
  late final DoctorRepository _repository = AppScope.read(context).doctor;
  late final int? _userId = AppScope.read(context).session.state.user?.id;
  late final RecordLoader<_VisitData> _loader = RecordLoader(_load);
  bool _changingStatus = false;
  String? _statusError;

  Future<_VisitData> _load() async {
    final visit = await _repository.visit(widget.visitId);
    final hospital = visit.hospitalId;
    final userId = _userId;
    DoctorProfile? doctor;
    if (hospital != null && userId != null) {
      try {
        doctor = await _repository.myProfile(
          hospitalId: hospital,
          userId: userId,
        );
      } on ApiException {
        doctor = null;
      }
    }
    return _VisitData(visit, doctor);
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

  Future<void> _setStatus(_VisitData data, String status) async {
    if (_changingStatus) return;
    final t = context.l10n;
    if (status == Visit.completed) {
      final ok = await showHmsConfirm(
        context,
        title: t.completeConsultationTitle,
        message: t.completeConsultationBody,
        confirmLabel: t.completeConsultation,
      );
      if (!ok || !mounted) return;
    }
    setState(() {
      _changingStatus = true;
      _statusError = null;
    });
    try {
      // The server moves the queue token and appointment with the visit.
      final visit = await _repository.setVisitStatus(data.visit.id, status);
      _loader.replace(_VisitData(visit, data.doctor));
    } catch (error) {
      if (mounted) {
        setState(() => _statusError = _statusErrorMessage(t, error));
        // Refused because the visit moved on (another device, a double tap):
        // show it as the server holds it now.
        if (error is ApiException && error.hasFlag('invalid_transition')) {
          await _loader.load();
        }
      }
    } finally {
      if (mounted) setState(() => _changingStatus = false);
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
        return RecordSection<_VisitData>(
          loader: _loader,
          builder: (context, data) => _body(t, data),
        );
      },
    );
  }

  Widget _body(AppLocalizations t, _VisitData data) {
    final visit = data.visit;
    final own = visit.doctorId == null || visit.doctorId == data.doctor?.id;
    final canWrite = visit.isOpen && own && data.doctor != null;
    final sectionContext = ConsultationContext(
      repository: _repository,
      visit: visit,
      userId: _userId,
      canWrite: canWrite,
      doctor: data.doctor,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: visit.patientName ?? t.patientLabel,
          description: [
            ?visit.visitType,
            formatDateTime(t, visit.visitDate),
            ?visit.doctorName,
          ].join(' · '),
          actions: [
            if (visit.patientId != null)
              HmsButton(
                label: t.openPatientRecord,
                variant: HmsButtonVariant.secondary,
                onPressed: () =>
                    context.go(DoctorRoutes.patient(visit.patientId!)),
              ),
            if (own && data.doctor != null && visit.patientId != null)
              HmsButton(
                key: const Key('admit-patient'),
                label: t.admitPatient,
                icon: LucideIcons.bedDouble,
                variant: HmsButtonVariant.secondary,
                onPressed: () =>
                    context.go('${IpdRoutes.list}/admit/${visit.patientId}'),
              ),
            if (own && data.doctor != null)
              HmsButton(
                key: const Key('open-ai-scribe'),
                label: t.aiScribeTitle,
                icon: LucideIcons.mic,
                variant: HmsButtonVariant.secondary,
                onPressed: () => context.go(AiRoutes.visit(visit.id)),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsCard(
          padding: const EdgeInsets.all(AppSpacing.x4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Wrap(
                spacing: AppSpacing.x2,
                runSpacing: AppSpacing.x1,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(t.status, style: AppTypography.small()),
                  StatusBadge(status: visit.status),
                ],
              ),
              if (visit.chiefComplaint != null) ...[
                const SizedBox(height: AppSpacing.x2),
                Text(
                  '${t.noteChiefComplaint}: ${visit.chiefComplaint}',
                  style: AppTypography.body(),
                ),
              ],
              if (_statusError != null) ...[
                const SizedBox(height: AppSpacing.x3),
                HmsAlert(tone: AlertTone.danger, title: _statusError!),
              ],
              if (own && data.doctor != null && visit.isOpen) ...[
                const SizedBox(height: AppSpacing.x3),
                if (visit.status == Visit.waiting)
                  HmsButton(
                    key: const Key('start-visit'),
                    label: t.startConsultation,
                    surface: HmsSurface.card,
                    loading: _changingStatus,
                    onPressed: _changingStatus
                        ? null
                        : () => _setStatus(data, Visit.inConsultation),
                  )
                else
                  HmsButton(
                    key: const Key('complete-visit'),
                    label: t.completeConsultation,
                    surface: HmsSurface.card,
                    loading: _changingStatus,
                    onPressed: _changingStatus
                        ? null
                        : () => _setStatus(data, Visit.completed),
                  ),
              ],
            ],
          ),
        ),
        if (!canWrite) ...[
          const SizedBox(height: AppSpacing.x4),
          HmsAlert(
            title: !own
                ? t.anotherDoctorsVisit
                : (data.doctor == null
                      ? t.doctorProfileMissing
                      : t.visitClosedReadOnly),
          ),
        ],
        if (visit.patientId != null) ...[
          sectionGap,
          AllergiesSection(patientId: visit.patientId!, canWrite: canWrite),
        ],
        sectionGap,
        VitalsSection(context: sectionContext),
        sectionGap,
        NotesSection(context: sectionContext),
        sectionGap,
        DiagnosisSection(context: sectionContext),
        sectionGap,
        PrescriptionSection(context: sectionContext),
        sectionGap,
        LabOrderSection(context: sectionContext),
        const SizedBox(height: AppSpacing.x4),
        Text(t.consultationQueueHint, style: AppTypography.caption()),
      ],
    );
  }
}
