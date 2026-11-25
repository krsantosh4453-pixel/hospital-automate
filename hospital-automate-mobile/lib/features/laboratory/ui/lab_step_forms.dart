import 'package:flutter/material.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/hms_text_field.dart';
import '../../patient/data/record_models.dart';
import '../data/lab_repository.dart';
import '../data/lab_workflow.dart';
import 'lab_ui.dart';

/// Asks for what [step] records and confirms it. Resolves to the request
/// body to send, or null when the person backs out. Nothing is sent here.
Future<Map<String, Object?>?> askForLabStep(
  BuildContext context,
  LabTest test,
  LabStep step,
) {
  final t = context.l10n;
  final title = labStepLabel(t, step);
  return switch (step) {
    LabStep.collect => showHmsModal<Map<String, Object?>>(
      context,
      title: title,
      description: '${test.name} · ${test.patientName ?? ''}',
      body: const _CollectForm(),
    ),
    LabStep.dispatch => showHmsModal<Map<String, Object?>>(
      context,
      title: title,
      description: test.sample?.sampleId,
      body: const _DispatchForm(),
    ),
    LabStep.enterResult => showHmsModal<Map<String, Object?>>(
      context,
      title: title,
      description: '${test.name} · ${test.patientName ?? ''}',
      body: const _ResultForm(),
    ),
    LabStep.reject => showHmsModal<Map<String, Object?>>(
      context,
      title: title,
      description: '${test.name} · ${test.patientName ?? ''}',
      body: const _RejectForm(),
    ),
    _ => _confirmStep(context, test, step),
  };
}

Future<Map<String, Object?>?> _confirmStep(
  BuildContext context,
  LabTest test,
  LabStep step,
) async {
  final t = context.l10n;
  final message = switch (step) {
    LabStep.verify => t.labVerifyConfirm(test.name),
    LabStep.release => t.labReleaseConfirm(test.name),
    _ => t.labStepConfirm(labStepLabel(t, step), test.name),
  };
  final ok = await showHmsConfirm(
    context,
    title: labStepLabel(t, step),
    message: message,
    confirmLabel: labStepLabel(t, step),
  );
  return ok ? const <String, Object?>{} : null;
}

/// Footer buttons shared by the step forms.
class _FormButtons extends StatelessWidget {
  const _FormButtons({required this.submitLabel, required this.onSubmit});

  final String submitLabel;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: AppSpacing.x4),
    child: Wrap(
      alignment: WrapAlignment.end,
      spacing: AppSpacing.x2,
      runSpacing: AppSpacing.x2,
      children: [
        HmsButton(
          label: context.l10n.cancel,
          variant: HmsButtonVariant.secondary,
          surface: HmsSurface.card,
          onPressed: () => Navigator.of(context).pop(),
        ),
        HmsButton(
          key: const Key('lab-step-submit'),
          label: submitLabel,
          surface: HmsSurface.card,
          onPressed: onSubmit,
        ),
      ],
    ),
  );
}

Widget _dropdown({
  required Key key,
  required String label,
  required String value,
  required List<String> options,
  required ValueChanged<String> onChanged,
}) => DropdownButtonFormField<String>(
  key: key,
  initialValue: value,
  isExpanded: true,
  decoration: InputDecoration(labelText: label),
  items: [
    for (final option in options)
      DropdownMenuItem(value: option, child: Text(option)),
  ],
  onChanged: (v) => onChanged(v ?? value),
);

class _CollectForm extends StatefulWidget {
  const _CollectForm();

  @override
  State<_CollectForm> createState() => _CollectFormState();
}

class _CollectFormState extends State<_CollectForm> {
  String _type = labSampleTypes.first;
  String _container = labContainerTypes.first;
  final _sampleId = TextEditingController();
  final _notes = TextEditingController();

  @override
  void dispose() {
    _sampleId.dispose();
    _notes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _dropdown(
          key: const Key('sample-type'),
          label: t.labSampleType,
          value: _type,
          options: labSampleTypes,
          onChanged: (v) => setState(() => _type = v),
        ),
        const SizedBox(height: AppSpacing.x3),
        _dropdown(
          key: const Key('container-type'),
          label: t.labContainerType,
          value: _container,
          options: labContainerTypes,
          onChanged: (v) => setState(() => _container = v),
        ),
        const SizedBox(height: AppSpacing.x3),
        HmsTextField(
          key: const Key('sample-id'),
          label: t.labSampleNumber,
          hint: t.labSampleNumberHint,
          controller: _sampleId,
          maxLength: 50,
        ),
        HmsTextField(
          key: const Key('collection-notes'),
          label: t.labCollectionNotes,
          controller: _notes,
          textInputAction: TextInputAction.done,
        ),
        _FormButtons(
          submitLabel: t.labStepCollect,
          onSubmit: () => Navigator.of(context).pop(
            SampleCollectionInput(
              sampleType: _type,
              containerType: _container,
              sampleId: _sampleId.text,
              notes: _notes.text,
            ).toJson(),
          ),
        ),
      ],
    );
  }
}

class _DispatchForm extends StatefulWidget {
  const _DispatchForm();

  @override
  State<_DispatchForm> createState() => _DispatchFormState();
}

class _DispatchFormState extends State<_DispatchForm> {
  final _notes = TextEditingController();
  final _externalLab = TextEditingController();

  @override
  void dispose() {
    _notes.dispose();
    _externalLab.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsTextField(
          key: const Key('external-lab'),
          label: t.labExternalLab,
          hint: t.labExternalLabHint,
          controller: _externalLab,
          maxLength: 200,
        ),
        HmsTextField(
          key: const Key('dispatch-notes'),
          label: t.labDispatchNotes,
          controller: _notes,
          textInputAction: TextInputAction.done,
        ),
        _FormButtons(
          submitLabel: t.labStepDispatch,
          onSubmit: () => Navigator.of(context).pop({
            if (_notes.text.trim().isNotEmpty)
              'dispatch_notes': _notes.text.trim(),
            if (_externalLab.text.trim().isNotEmpty)
              'external_lab': _externalLab.text.trim(),
          }),
        ),
      ],
    );
  }
}

/// The result as the laboratory reports it, typed by authorised lab staff.
/// It is saved as entered and stays unverified until a separate verify step.
class _ResultForm extends StatefulWidget {
  const _ResultForm();

  @override
  State<_ResultForm> createState() => _ResultFormState();
}

class _ResultFormState extends State<_ResultForm> {
  final _text = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          key: const Key('result-text'),
          controller: _text,
          minLines: 4,
          maxLines: 10,
          decoration: InputDecoration(
            labelText: '${t.labResultText} *',
            helperText: t.labResultNotVerifiedYet,
            helperMaxLines: 3,
            errorText: _error,
          ),
        ),
        _FormButtons(
          submitLabel: t.labStepEnterResult,
          onSubmit: () {
            final text = _text.text.trim();
            if (text.isEmpty) {
              setState(() => _error = t.labResultRequired);
              return;
            }
            Navigator.of(context).pop({'result_text': text});
          },
        ),
      ],
    );
  }
}

/// L-1: why the result is wrong (the server needs at least 5 characters).
class _RejectForm extends StatefulWidget {
  const _RejectForm();

  @override
  State<_RejectForm> createState() => _RejectFormState();
}

class _RejectFormState extends State<_RejectForm> {
  final _reason = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          key: const Key('reject-reason'),
          controller: _reason,
          minLines: 2,
          maxLines: 4,
          decoration: InputDecoration(
            labelText: '${t.labRejectReason} *',
            helperText: t.labRejectHelp,
            helperMaxLines: 3,
            errorText: _error,
          ),
        ),
        _FormButtons(
          submitLabel: t.labStepReject,
          onSubmit: () {
            final reason = _reason.text.trim();
            if (reason.length < 5) {
              setState(() => _error = t.labRejectReasonRequired);
              return;
            }
            Navigator.of(context).pop({'reason': reason});
          },
        ),
      ],
    );
  }
}
