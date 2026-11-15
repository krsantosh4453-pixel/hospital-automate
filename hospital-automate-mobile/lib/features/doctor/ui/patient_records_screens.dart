import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/clinical_records_screens.dart' show PrescriptionCard;
import '../../patient/ui/patient_ui.dart';
import '../data/doctor_models.dart';
import '../data/doctor_repository.dart';
import 'doctor_ui.dart';

/// Searches shorter than this are not sent (the server would return the
/// whole list in care, which is not a search).
const minSearchLength = 2;

/// Waits this long after the last keystroke before searching.
const searchDebounce = Duration(milliseconds: 400);

/// `/patients` for a doctor: search among the patients in their care (the
/// server decides who that is; nobody else is ever returned).
class PatientSearchScreen extends StatefulWidget {
  const PatientSearchScreen({super.key});

  @override
  State<PatientSearchScreen> createState() => _PatientSearchScreenState();
}

class _PatientSearchScreenState extends State<PatientSearchScreen> {
  late final DoctorRepository _repository = AppScope.read(context).doctor;
  final _query = TextEditingController();
  RecordLoader<List<PatientSummary>>? _loader;
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    _query.dispose();
    _loader?.dispose();
    super.dispose();
  }

  void _changed(String text) {
    _debounce?.cancel();
    _debounce = Timer(searchDebounce, () {
      final query = text.trim();
      if (!mounted) return;
      setState(() {
        _loader?.dispose();
        _loader = query.length < minSearchLength
            ? null
            : (RecordLoader(() => _repository.searchPatients(query))..load());
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final loader = _loader;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.navPatients, description: t.doctorPatientsIntro),
        const SizedBox(height: AppSpacing.x4),
        TextField(
          key: const Key('patient-search'),
          controller: _query,
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            prefixIcon: const Icon(LucideIcons.search, size: 18),
            hintText: t.searchPatientsHint,
          ),
          onChanged: _changed,
        ),
        const SizedBox(height: AppSpacing.x4),
        if (loader == null)
          HmsCard(
            child: HmsEmptyState(
              icon: LucideIcons.search,
              title: t.typeToSearch(minSearchLength),
            ),
          )
        else
          RecordSection<List<PatientSummary>>(
            loader: loader,
            builder: (context, patients) => patients.isEmpty
                ? HmsCard(
                    child: HmsEmptyState(
                      icon: LucideIcons.userRoundSearch,
                      title: t.noPatientsFound,
                      description: t.noPatientsFoundHint,
                    ),
                  )
                : HmsCard(
                    child: HmsDividedColumn(
                      children: [
                        for (final p in patients)
                          InkWell(
                            onTap: () => context.go(DoctorRoutes.patient(p.id)),
                            child: Padding(
                              padding: AppSpacing.cardRow,
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          p.name,
                                          style: AppTypography.body(
                                            weight: FontWeight.w600,
                                          ),
                                        ),
                                        Text(
                                          [
                                            ?p.uhid,
                                            ?p.gender,
                                            if (p.age != null)
                                              t.ageYears('${p.age}'),
                                          ].join(' · '),
                                          style: AppTypography.small(),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const Icon(
                                    LucideIcons.chevronRight,
                                    size: 16,
                                  ),
                                ],
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
          ),
      ],
    );
  }
}

/// Everything about one patient the doctor may see, loaded side by side.
class PatientRecord {
  const PatientRecord({
    required this.patient,
    this.timeline,
    this.visits,
    this.prescriptions,
    this.labTests,
  });

  static Future<PatientRecord> load(DoctorRepository repository, int id) async {
    // The profile decides access: a 403/404 here means "not in your care".
    final patient = await repository.patient(id);
    Future<T?> settle<T>(Future<T> future) async {
      try {
        return await future;
      } on ApiException {
        return null;
      }
    }

    final results = await Future.wait<Object?>([
      settle(repository.timeline(id)),
      settle(repository.visits(patientId: id)),
      settle(repository.prescriptions(patientId: id)),
      settle(repository.labTests(patientId: id)),
    ]);
    return PatientRecord(
      patient: patient,
      timeline: results[0] as List<TimelineEvent>?,
      visits: results[1] as List<Visit>?,
      prescriptions: results[2] as List<Prescription>?,
      labTests: results[3] as List<LabTest>?,
    );
  }

  final PatientSummary patient;
  final List<TimelineEvent>? timeline;
  final List<Visit>? visits;
  final List<Prescription>? prescriptions;
  final List<LabTest>? labTests;
}

/// `/patients/:id`: the patient's record, if the server says they are in
/// this doctor's care. Nothing is cached on the phone.
class PatientRecordScreen extends StatefulWidget {
  const PatientRecordScreen({super.key, required this.patientId});

  final int patientId;

  @override
  State<PatientRecordScreen> createState() => _PatientRecordScreenState();
}

class _PatientRecordScreenState extends State<PatientRecordScreen> {
  late final RecordLoader<PatientRecord> _loader = RecordLoader(
    () => PatientRecord.load(AppScope.read(context).doctor, widget.patientId),
  );

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
    return ListenableBuilder(
      listenable: _loader,
      builder: (context, _) {
        final error = _loader.error;
        final denied =
            error is ApiException &&
            (error.kind == ApiErrorKind.forbidden ||
                error.kind == ApiErrorKind.notFound);
        if (_loader.data == null && denied) {
          return HmsCard(
            child: HmsEmptyState(
              icon: LucideIcons.shieldAlert,
              title: t.patientNotInCare,
              description: t.patientNotInCareHint,
            ),
          );
        }
        return RecordSection<PatientRecord>(
          loader: _loader,
          builder: (context, record) => _RecordBody(record: record),
        );
      },
    );
  }
}

class _RecordBody extends StatelessWidget {
  const _RecordBody({required this.record});

  final PatientRecord record;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final p = record.patient;
    Widget unavailable() =>
        HmsEmptyState(compact: true, title: t.notAvailableNow);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: p.name,
          description: [
            ?p.uhid,
            ?p.gender,
            if (p.age != null) t.ageYears('${p.age}'),
          ].join(' · '),
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.patientProfile,
                icon: LucideIcons.userRound,
              ),
              HmsDividedColumn(
                children: [
                  DetailRow(label: t.patientId, value: p.uhid ?? '${p.id}'),
                  DetailRow(
                    label: t.dateOfBirth,
                    value: formatDay(t, p.dateOfBirth),
                  ),
                  DetailRow(label: t.mobileNumber, value: p.phone),
                  DetailRow(label: t.knownCondition, value: p.condition),
                  DetailRow(
                    label: t.emergencyContact,
                    value: [
                      ?p.emergencyContactName,
                      ?p.emergencyContactPhone,
                    ].join(' · '),
                  ),
                ],
              ),
            ],
          ),
        ),
        sectionGap,
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(title: t.visits, icon: LucideIcons.stethoscope),
              if (record.visits == null)
                unavailable()
              else if (record.visits!.isEmpty)
                HmsEmptyState(compact: true, title: t.noVisitsYet)
              else
                HmsDividedColumn(
                  children: [
                    for (final v in record.visits!)
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
                                      [
                                        ?v.visitType,
                                        formatDateTime(t, v.visitDate),
                                      ].join(' · '),
                                      style: AppTypography.body(
                                        weight: FontWeight.w600,
                                      ),
                                    ),
                                    if (v.chiefComplaint != null)
                                      Text(
                                        v.chiefComplaint!,
                                        style: AppTypography.small(),
                                      ),
                                    if (v.doctorName != null)
                                      Text(
                                        v.doctorName!,
                                        style: AppTypography.caption(),
                                      ),
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
            ],
          ),
        ),
        sectionGap,
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.clinicalHistory,
                icon: LucideIcons.history,
              ),
              if (record.timeline == null)
                unavailable()
              else if (record.timeline!.isEmpty)
                HmsEmptyState(compact: true, title: t.noHistoryYet)
              else
                HmsDividedColumn(
                  children: [
                    for (final event in record.timeline!.take(30))
                      DetailRow(
                        label: formatDateTime(t, event.when),
                        value: [
                          event.title,
                          ?event.detail,
                          ?event.hospital,
                        ].join(' · '),
                      ),
                  ],
                ),
            ],
          ),
        ),
        sectionGap,
        Text(
          t.patientNavPrescriptions,
          style: AppTypography.style(16, weight: FontWeight.w600),
        ),
        const SizedBox(height: AppSpacing.x3),
        if (record.prescriptions == null)
          HmsCard(child: unavailable())
        else if (record.prescriptions!.isEmpty)
          HmsCard(
            child: HmsEmptyState(compact: true, title: t.noPrescriptionsYet),
          )
        else
          for (final rx in record.prescriptions!) ...[
            PrescriptionCard(prescription: rx),
            const SizedBox(height: AppSpacing.x3),
          ],
        sectionGap,
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.navLaboratory,
                icon: LucideIcons.flaskConical,
              ),
              if (record.labTests == null)
                unavailable()
              else if (record.labTests!.isEmpty)
                HmsEmptyState(compact: true, title: t.noLabReportsYet)
              else
                HmsDividedColumn(
                  children: [
                    for (final test in record.labTests!) LabTestRow(test: test),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }
}

/// One lab test for staff: name, status and the released values, never
/// interpreted. Results show only once the laboratory has released them.
class LabTestRow extends StatelessWidget {
  const LabTestRow({super.key, required this.test});

  final LabTest test;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final released = test.status == 'Released';
    final result = test.result;
    return Padding(
      padding: AppSpacing.cardRow,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  test.name,
                  style: AppTypography.body(weight: FontWeight.w600),
                ),
              ),
              StatusBadge(status: test.status),
            ],
          ),
          Text(
            [
              ?test.patientName,
              formatDay(t, test.releasedAt ?? test.testDate),
              ?test.priority,
            ].join(' · '),
            style: AppTypography.small(),
          ),
          if (released && result != null)
            for (final entry in result.values.entries)
              Text(
                [
                  '${entry.key}: ${entry.value}',
                  if (result.flags[entry.key] != null)
                    '(${result.flags[entry.key]})',
                  if (result.referenceRanges[entry.key] != null)
                    '· ${t.referenceRange}: ${result.referenceRanges[entry.key]}',
                ].join(' '),
                style: AppTypography.small(),
              ),
          if (!released)
            Text(t.resultNotReleased, style: AppTypography.caption()),
        ],
      ),
    );
  }
}
