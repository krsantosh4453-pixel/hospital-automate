import 'package:flutter/material.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../operations/ops_ui.dart';
import '../data/ipd_models.dart';
import '../data/ipd_repository.dart';

/// Picks a free bed for [admission]: a first bed, or a transfer when it
/// already holds one. Only beds the server lists as Available are offered,
/// and the server re-checks under a row lock; true once it confirmed.
Future<bool> showBedPicker(
  BuildContext context, {
  required IpdRepository repository,
  required int hospitalId,
  required IpdAdmission admission,
}) async =>
    await showHmsModal<bool>(
      context,
      title: admission.canAllocateBed
          ? context.l10n.ipdAllocateBed
          : context.l10n.ipdTransferBed,
      body: _BedPickerBody(
        repository: repository,
        hospitalId: hospitalId,
        admission: admission,
      ),
    ) ??
    false;

class _BedPickerBody extends StatefulWidget {
  const _BedPickerBody({
    required this.repository,
    required this.hospitalId,
    required this.admission,
  });

  final IpdRepository repository;
  final int hospitalId;
  final IpdAdmission admission;

  @override
  State<_BedPickerBody> createState() => _BedPickerBodyState();
}

class _BedPickerBodyState extends State<_BedPickerBody> {
  List<AvailableBed>? _beds;
  Object? _loadError;
  int? _chosen;
  bool _busy = false;
  String? _failure;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loadError = null);
    try {
      final beds = await widget.repository.availableBeds(widget.hospitalId);
      if (!mounted) return;
      setState(() {
        _beds = beds;
        if (beds.every((b) => b.id != _chosen)) _chosen = null;
      });
    } catch (error) {
      if (mounted) setState(() => _loadError = error);
    }
  }

  Future<void> _save() async {
    final bedId = _chosen;
    if (bedId == null || _busy) return;
    setState(() {
      _busy = true;
      _failure = null;
    });
    final t = context.l10n;
    try {
      if (widget.admission.canAllocateBed) {
        await widget.repository.allocateBed(widget.admission.id, bedId);
      } else {
        await widget.repository.transferBed(widget.admission.id, bedId);
      }
      if (mounted) Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) return;
      final refused =
          error is ApiException &&
          (error.kind == ApiErrorKind.validation ||
              error.kind == ApiErrorKind.notFound);
      setState(() {
        _busy = false;
        _failure = refused ? t.ipdBedTaken : stepErrorMessage(t, error);
      });
      // The bed may have been taken meanwhile: show the current free beds.
      if (refused) await _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final beds = _beds;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_loadError != null)
          HmsAlert(
            tone: AlertTone.danger,
            title: apiErrorMessage(t, _loadError!),
          )
        else if (beds == null)
          const HmsLoading()
        else if (beds.isEmpty)
          Text(t.ipdNoFreeBeds, style: AppTypography.small())
        else ...[
          Text(t.ipdChooseBed, style: AppTypography.small()),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 320),
            child: ListView(
              shrinkWrap: true,
              children: [
                for (final bed in beds)
                  ListTile(
                    key: ValueKey('free-bed-${bed.id}'),
                    dense: true,
                    selected: bed.id == _chosen,
                    title: Text(bed.place.label),
                    subtitle: bed.roomType == null ? null : Text(bed.roomType!),
                    trailing: bed.id == _chosen
                        ? const Icon(Icons.check, size: 18)
                        : null,
                    onTap: _busy
                        ? null
                        : () => setState(() => _chosen = bed.id),
                  ),
              ],
            ),
          ),
        ],
        if (_failure != null) ...[
          const SizedBox(height: AppSpacing.x3),
          HmsAlert(tone: AlertTone.danger, title: _failure!),
        ],
        const SizedBox(height: AppSpacing.x3),
        HmsButton(
          key: const Key('ipd-save-bed'),
          label: widget.admission.canAllocateBed
              ? t.ipdAllocateBed
              : t.ipdTransferBed,
          expand: true,
          loading: _busy,
          surface: HmsSurface.card,
          onPressed: _chosen == null || _busy ? null : _save,
        ),
      ],
    );
  }
}
