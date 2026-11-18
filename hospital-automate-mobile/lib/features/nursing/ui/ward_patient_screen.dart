import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../doctor/data/doctor_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/nursing_models.dart';
import '../data/nursing_repository.dart';
import 'nursing_ui.dart';
import 'ward_care_sections.dart';
import 'ward_medication_section.dart';
import 'ward_vitals_section.dart';

/// What every section of a ward record needs: the patient, where they are
/// cared for, and the repository. Built once per page load.
@immutable
class WardContext {
  const WardContext({
    required this.repository,
    required this.hospitalId,
    required this.patient,
    required this.admissions,
    required this.openVisits,
  });

  final NursingRepository repository;
  final int hospitalId;
  final PatientSummary patient;

  /// Stays still in the ward (Admitted or Discharge Initiated).
  final List<Admission> admissions;
  final List<Visit> openVisits;

  /// The stay a note or dose belongs to, when the patient is admitted.
  Admission? get currentAdmission =>
      admissions.isEmpty ? null : admissions.first;

  /// "Name · UHID" for confirmations, so the right patient is checked.
  String identity(AppLocalizations t) => [
    patient.name,
    if (patient.uhid != null) '${t.patientId}: ${patient.uhid}',
  ].join(' · ');
}

/// `/nurses/patients/:id`: one patient of the nurse's duty. The server
/// answers 404 for a patient outside the nurse's care at this hospital.
class WardPatientScreen extends StatefulWidget {
  const WardPatientScreen({super.key, required this.patientId});

  final int patientId;

  @override
  State<WardPatientScreen> createState() => _WardPatientScreenState();
}

class _WardPatientScreenState extends State<WardPatientScreen> {
  late final RecordLoader<WardContext> _loader = RecordLoader(_fetch);

  Future<WardContext> _fetch() async {
    final services = AppScope.read(context);
    final repo = services.nursing;
    final hospitalId = services.session.state.activeHospitalId ?? 0;
    final results = await Future.wait<Object>([
      repo.patient(widget.patientId),
      repo.admissions(patientId: widget.patientId),
      repo.openVisits(widget.patientId),
    ]);
    return WardContext(
      repository: repo,
      hospitalId: hospitalId,
      patient: results[0] as PatientSummary,
      admissions: [
        for (final a in results[1] as List<Admission>)
          if (a.inWard && a.patientId == widget.patientId) a,
      ],
      openVisits: results[2] as List<Visit>,
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
        Align(
          alignment: Alignment.centerLeft,
          child: HmsButton(
            label: t.wardPatients,
            icon: LucideIcons.arrowLeft,
            variant: HmsButtonVariant.ghost,
            size: HmsButtonSize.small,
            onPressed: () => context.go(NursingRoutes.ward),
          ),
        ),
        const SizedBox(height: AppSpacing.x2),
        RecordSection<WardContext>(
          loader: _loader,
          builder: (context, ward) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              PageHeader(
                title: ward.patient.name,
                description: [
                  if (ward.patient.uhid != null)
                    '${t.patientId}: ${ward.patient.uhid}',
                  if (ward.patient.age != null)
                    t.ageYears('${ward.patient.age}'),
                  ?ward.patient.gender,
                ].join(' · '),
              ),
              const SizedBox(height: AppSpacing.x4),
              _StayCard(ward: ward),
              const SizedBox(height: AppSpacing.x4),
              WardVitalsSection(
                key: ValueKey('vitals-${ward.patient.id}'),
                ward: ward,
              ),
              const SizedBox(height: AppSpacing.x4),
              WardMedicationSection(
                key: ValueKey('mar-${ward.patient.id}'),
                ward: ward,
              ),
              const SizedBox(height: AppSpacing.x4),
              WardNotesSection(
                key: ValueKey('notes-${ward.patient.id}'),
                ward: ward,
              ),
              const SizedBox(height: AppSpacing.x4),
              WardTasksSection(
                key: ValueKey('tasks-${ward.patient.id}'),
                ward: ward,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Where the patient is cared for: their stay, or open OPD visits.
class _StayCard extends StatelessWidget {
  const _StayCard({required this.ward});

  final WardContext ward;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final stay = ward.currentAdmission;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.admissionAndVisits, icon: LucideIcons.bedDouble),
          if (stay == null && ward.openVisits.isEmpty)
            HmsEmptyState(compact: true, title: t.noActiveStay)
          else
            HmsDividedColumn(
              children: [
                if (stay != null) ...[
                  DetailRow(
                    label: t.status,
                    value: wardStatusLabel(t, stay.status),
                  ),
                  DetailRow(
                    label: t.wardAndBed,
                    value: stay.awaitingBed
                        ? t.awaitingBed
                        : [
                            ?stay.wardName,
                            if (stay.roomNumber != null)
                              t.roomNumber(stay.roomNumber!),
                            if (stay.bedNumber != null)
                              t.bedNumber(stay.bedNumber!),
                          ].join(' · '),
                  ),
                  DetailRow(label: t.admittedOn, value: formatDateTime(t, stay.admittedAt)),
                  DetailRow(label: t.admittingDoctor, value: stay.doctorName),
                  DetailRow(label: t.admissionReason, value: stay.reason),
                ],
                for (final visit in ward.openVisits)
                  DetailRow(
                    label: t.opdVisitOn(formatDay(t, visit.visitDate)),
                    value: [
                      ?visit.doctorName,
                      statusLabel(t, visit.status),
                      ?visit.chiefComplaint,
                    ].join(' · '),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}
