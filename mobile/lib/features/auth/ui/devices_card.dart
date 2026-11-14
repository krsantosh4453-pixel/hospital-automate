import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/states.dart';
import '../auth_errors.dart';
import '../auth_models.dart';

/// Signed-in devices (`auth/sessions/`): sign one out, or every device.
class DevicesCard extends StatefulWidget {
  const DevicesCard({super.key});

  @override
  State<DevicesCard> createState() => _DevicesCardState();
}

class _DevicesCardState extends State<DevicesCard> {
  Future<List<DeviceSessionInfo>>? _devices;
  String? _error;
  bool _busy = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _devices ??= AppScope.of(context).auth.sessions();
  }

  void _reload() => setState(() {
    _error = null;
    _devices = AppScope.of(context).auth.sessions();
  });

  Future<void> _act(
    String confirm,
    String confirmLabel,
    Future<void> Function() action,
  ) async {
    final t = context.l10n;
    final ok = await showHmsConfirm(
      context,
      title: confirmLabel,
      message: confirm,
      confirmLabel: confirmLabel,
      destructive: true,
    );
    if (!ok || !mounted) return;
    setState(() => _busy = true);
    try {
      await action();
      if (mounted) _reload();
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
    final auth = AppScope.of(context).auth;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: t.signedInDevices,
            description: t.signedInDevicesIntro,
            icon: LucideIcons.monitorSmartphone,
          ),
          if (_error != null)
            Padding(
              padding: AppSpacing.cardRow,
              child: Text(_error!, style: AppTypography.small()),
            ),
          FutureBuilder<List<DeviceSessionInfo>>(
            future: _devices,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const HmsLoading();
              }
              if (snapshot.hasError) {
                return HmsErrorState(error: snapshot.error!, onRetry: _reload);
              }
              final devices = snapshot.data ?? const [];
              if (devices.isEmpty) {
                return HmsEmptyState(compact: true, title: t.noOtherDevices);
              }
              return HmsDividedColumn(
                children: [
                  for (final device in devices)
                    _DeviceRow(
                      device: device,
                      onSignOut: _busy
                          ? null
                          : () => _act(
                              t.signOutDeviceConfirm,
                              t.signOutDevice,
                              () => auth.revokeSession(device),
                            ),
                    ),
                ],
              );
            },
          ),
          Padding(
            padding: AppSpacing.cardHeader,
            child: Align(
              alignment: Alignment.centerLeft,
              child: HmsButton(
                label: t.signOutEverywhere,
                icon: LucideIcons.logOut,
                variant: HmsButtonVariant.secondary,
                surface: HmsSurface.card,
                onPressed: _busy
                    ? null
                    : () => _act(
                        t.signOutEverywhereConfirm,
                        t.signOutEverywhere,
                        auth.logoutAll,
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DeviceRow extends StatelessWidget {
  const _DeviceRow({required this.device, required this.onSignOut});

  final DeviceSessionInfo device;
  final VoidCallback? onSignOut;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final name = switch (device.platform) {
      'android' => t.platformAndroid,
      'ios' => t.platformIos,
      'web' => t.platformWeb,
      _ => t.platformOther,
    };
    final when = device.lastUsedAt ?? device.createdAt;
    final detail = [
      if (device.current) t.thisDevice,
      if (when != null)
        t.lastActive(
          DateFormat.yMMMd(t.localeName).add_jm().format(when.toLocal()),
        ),
    ].join(' · ');
    return Padding(
      padding: AppSpacing.cardRow,
      child: Row(
        children: [
          Icon(
            device.platform == 'web'
                ? LucideIcons.monitor
                : LucideIcons.smartphone,
            size: 18,
          ),
          const SizedBox(width: AppSpacing.x3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: AppTypography.body(weight: FontWeight.w500)),
                if (detail.isNotEmpty)
                  Text(detail, style: AppTypography.caption()),
              ],
            ),
          ),
          HmsButton(
            label: t.signOutDevice,
            size: HmsButtonSize.small,
            variant: HmsButtonVariant.ghost,
            surface: HmsSurface.card,
            onPressed: onSignOut,
          ),
        ],
      ),
    );
  }
}
