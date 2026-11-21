import 'package:flutter/material.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../auth/auth_errors.dart';
import '../../auth/auth_models.dart';

/// BUG-01: a patient registered at no hospital chooses one here. The server
/// issues that hospital's UHID (repeating is harmless), then the session is
/// reloaded so the hospital can be selected and booked.
class JoinHospitalPanel extends StatefulWidget {
  const JoinHospitalPanel({super.key, required this.onJoined});

  /// Called after the hospital was joined and the session reloaded.
  final Future<void> Function() onJoined;

  @override
  State<JoinHospitalPanel> createState() => _JoinHospitalPanelState();
}

class _JoinHospitalPanelState extends State<JoinHospitalPanel> {
  Future<List<PublicHospital>>? _hospitals;
  int? _hospitalId;
  bool _busy = false;
  String? _error;

  Future<void> _join() async {
    final id = _hospitalId;
    if (id == null || _busy) return;
    final t = context.l10n;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await AppScope.of(context).auth.joinHospital(id);
      await widget.onJoined();
    } catch (error) {
      if (mounted) {
        setState(() => _error = authErrorMessage(t, error, AuthStep.request));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final hospitals = _hospitals ??= AppScope.of(context).auth
        .patientHospitals();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(t.joinHospitalIntro, style: AppTypography.small()),
        const SizedBox(height: AppSpacing.x3),
        if (_error != null) ...[
          HmsAlert(tone: AlertTone.danger, title: _error!),
          const SizedBox(height: AppSpacing.x3),
        ],
        FutureBuilder<List<PublicHospital>>(
          future: hospitals,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return Row(
                children: [
                  Expanded(
                    child: Text(
                      t.hospitalsUnavailable,
                      style: AppTypography.small(),
                    ),
                  ),
                  HmsButton(
                    label: t.retry,
                    variant: HmsButtonVariant.ghost,
                    onPressed: () => setState(() => _hospitals = null),
                  ),
                ],
              );
            }
            final rows = snapshot.data;
            return DropdownButtonFormField<int>(
              key: const Key('join-hospital'),
              initialValue: _hospitalId,
              isExpanded: true,
              hint: Text(rows == null ? t.loading : t.selectHospital),
              items: [
                for (final h in rows ?? const <PublicHospital>[])
                  DropdownMenuItem(
                    value: h.id,
                    child: Text(h.label, overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: _busy
                  ? null
                  : (id) => setState(() => _hospitalId = id),
            );
          },
        ),
        const SizedBox(height: AppSpacing.x3),
        HmsButton(
          key: const Key('join-hospital-submit'),
          label: t.joinHospital,
          surface: HmsSurface.card,
          loading: _busy,
          onPressed: _hospitalId == null || _busy ? null : _join,
        ),
      ],
    );
  }
}
