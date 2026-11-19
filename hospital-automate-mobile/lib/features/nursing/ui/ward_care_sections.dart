import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/ui/consultation_sections.dart'
    show ClinicalField, formError;
import '../../doctor/ui/doctor_ui.dart' show clinicalErrorMessage;
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/nursing_models.dart';
import 'nursing_ui.dart';
import 'ward_patient_screen.dart';
import 'ward_widgets.dart';

/// Longest note the form accepts (the server's TextField has no limit; this
/// keeps one note readable on a phone).
const maxNoteLength = 4000;

/// Why a note cannot be sent, or null.
String? checkNote(AppLocalizations t, String text) {
  final value = text.trim();
  if (value.isEmpty) return t.noteTextRequired;
  if (value.length > maxNoteLength) return t.noteTooLong(maxNoteLength);
  return null;
}

/// Nursing notes of the patient, newest first, and a form for a new one.
/// Saved notes are never edited or deleted here: a correction is a new note.
class WardNotesSection extends StatefulWidget {
  const WardNotesSection({super.key, required this.ward});

  final WardContext ward;

  @override
  State<WardNotesSection> createState() => _WardNotesSectionState();
}

class _WardNotesSectionState extends State<WardNotesSection> {
  WardContext get _w => widget.ward;
  late final RecordLoader<List<NursingNote>> _loader = RecordLoader(
    () => _w.repository.notes(patientId: _w.patient.id),
  );
  final _text = TextEditingController();
  String _type = nursingNoteTypes.first;
  bool _saving = false;
  String? _error;
  String? _saved;

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _text.dispose();
    _loader.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving) return;
    final t = context.l10n;
    final problem = checkNote(t, _text.text);
    setState(() {
      _error = problem;
      _saved = null;
    });
    if (problem != null) return;
    setState(() => _saving = true);
    try {
      await _w.repository.addNote(
        hospitalId: _w.hospitalId,
        patientId: _w.patient.id,
        admissionId: _w.currentAdmission?.id,
        type: _type,
        text: _text.text,
      );
      _text.clear();
      if (mounted) setState(() => _saved = t.noteSaved);
      await _loader.load();
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = clinicalErrorMessage(
            t,
            error,
            fieldLabels: {'note': t.noteText, 'note_type': t.noteType},
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return WardSectionCard(
      title: t.nursingNotes,
      icon: LucideIcons.notebookPen,
      list: RecordSection<List<NursingNote>>(
        loader: _loader,
        skeletons: 1,
        builder: (context, notes) {
          final sorted = [...notes]
            ..sort(
              (a, b) => (b.createdAt ?? DateTime(0)).compareTo(
                a.createdAt ?? DateTime(0),
              ),
            );
          return sorted.isEmpty
              ? HmsEmptyState(compact: true, title: t.noNotesYet)
              : HmsDividedColumn(
                  children: [
                    for (final note in sorted)
                      WardRecordRow(
                        heading: [
                          formatDateTime(t, note.createdAt),
                          noteTypeLabel(t, note.type),
                          note.nurseName ?? t.authorNotRecorded,
                        ].join(' · '),
                        body: note.text,
                      ),
                  ],
                );
        },
      ),
      form: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          formError(_error),
          if (_saved != null) ...[
            HmsAlert(tone: AlertTone.success, title: _saved!),
            const SizedBox(height: AppSpacing.x3),
          ],
          DropdownButtonFormField<String>(
            key: const Key('note-type'),
            initialValue: _type,
            isExpanded: true,
            decoration: InputDecoration(labelText: t.noteType),
            items: [
              for (final type in nursingNoteTypes)
                DropdownMenuItem(
                  value: type,
                  child: Text(noteTypeLabel(t, type)),
                ),
            ],
            onChanged: _saving
                ? null
                : (value) => setState(() => _type = value ?? _type),
          ),
          const SizedBox(height: AppSpacing.x3),
          ClinicalField(
            key: const Key('note-text'),
            label: t.noteText,
            controller: _text,
            maxLines: 4,
            enabled: !_saving,
          ),
          Text(t.notesAreFinal, style: AppTypography.caption()),
          const SizedBox(height: AppSpacing.x3),
          HmsButton(
            key: const Key('save-nursing-note'),
            label: t.saveNote,
            surface: HmsSurface.card,
            loading: _saving,
            expand: true,
            onPressed: _saving ? null : _save,
          ),
        ],
      ),
    );
  }
}

/// Open care tasks of the patient; a nurse starts and completes them.
class WardTasksSection extends StatefulWidget {
  const WardTasksSection({super.key, required this.ward});

  final WardContext ward;

  @override
  State<WardTasksSection> createState() => _WardTasksSectionState();
}

class _WardTasksSectionState extends State<WardTasksSection> {
  WardContext get _w => widget.ward;
  late final RecordLoader<List<CareTask>> _loader = RecordLoader(
    () => _w.repository.careTasks(patientId: _w.patient.id),
  );
  final Set<int> _sending = {};
  String? _error;

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

  Future<void> _move(CareTask task, {required bool complete}) async {
    if (_sending.contains(task.id)) return;
    final t = context.l10n;
    if (complete) {
      final ok = await showHmsConfirm(
        context,
        title: t.completeTaskTitle,
        message: '${_w.identity(t)}\n${task.description}',
        confirmLabel: t.completeTask,
      );
      if (!ok || !mounted) return;
    }
    setState(() {
      _sending.add(task.id);
      _error = null;
    });
    try {
      if (complete) {
        await _w.repository.completeTask(task.id);
      } else {
        await _w.repository.startTask(task.id);
      }
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _sending.remove(task.id));
      await _loader.load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return WardSectionCard(
      title: t.careTasks,
      icon: LucideIcons.clipboardList,
      list: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(AppSpacing.x4),
              child: HmsAlert(tone: AlertTone.danger, title: _error!),
            ),
          RecordSection<List<CareTask>>(
            loader: _loader,
            skeletons: 1,
            builder: (context, tasks) {
              final open = [
                for (final task in tasks)
                  if (task.isOpen) task,
              ];
              if (open.isEmpty) {
                return HmsEmptyState(compact: true, title: t.noOpenTasks);
              }
              return HmsDividedColumn(
                children: [
                  for (final task in open)
                    WardRecordRow(
                      heading: [
                        formatDateTime(t, task.scheduledAt),
                        taskPriorityLabel(t, task.priority),
                        wardStatusLabel(t, task.status),
                      ].join(' · '),
                      body: task.description,
                      trailing: HmsButton(
                        key: Key('task-${task.id}'),
                        label: task.status == CareTask.pending
                            ? t.startTask
                            : t.completeTask,
                        size: HmsButtonSize.small,
                        surface: HmsSurface.card,
                        variant: HmsButtonVariant.secondary,
                        loading: _sending.contains(task.id),
                        onPressed: _sending.contains(task.id)
                            ? null
                            : () => _move(
                                task,
                                complete: task.status != CareTask.pending,
                              ),
                      ),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
