import 'package:flutter/material.dart';

import '../../core/app_scope.dart';
import '../../core/localization/l10n.dart';
import '../../core/network/api_exception.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import '../../shared/widgets/page_body.dart';
import '../../shared/widgets/states.dart';
import '../../shared/widgets/tone.dart';
import '../doctor/ui/doctor_ui.dart' show clinicalErrorMessage;

/// Reloads a page registers so pull-to-refresh can run them.
typedef PageReload = Future<void> Function();

/// Collects the reloads of the sections on one page.
class RefreshHub {
  final Set<PageReload> _reloads = {};

  void add(PageReload reload) => _reloads.add(reload);
  void remove(PageReload reload) => _reloads.remove(reload);

  Future<void> refreshAll() => Future.wait([for (final r in _reloads) r()]);
}

class _RefreshScope extends InheritedWidget {
  const _RefreshScope({required this.hub, required super.child});

  final RefreshHub hub;

  @override
  bool updateShouldNotify(_RefreshScope oldWidget) => hub != oldWidget.hub;
}

/// The [RefreshHub] of the page around [context], if any.
RefreshHub? refreshHubOf(BuildContext context) =>
    context.getInheritedWidgetOfExactType<_RefreshScope>()?.hub;

/// A staff module page (Emergency, IPD, Hospital): the page body with
/// pull-to-refresh, rebuilt from scratch when the user switches hospital so
/// no record of the previous hospital stays on screen and every list is
/// fetched again for the new one.
class StaffModulePage extends StatelessWidget {
  const StaffModulePage({
    super.key,
    required this.location,
    required this.child,
  });

  final String location;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final session = AppScope.of(context).session;
    return ListenableBuilder(
      listenable: session,
      builder: (context, _) => _HubHolder(
        key: ValueKey('hospital-${session.activeHospitalId}'),
        location: location,
        child: child,
      ),
    );
  }
}

class _HubHolder extends StatefulWidget {
  const _HubHolder({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  @override
  State<_HubHolder> createState() => _HubHolderState();
}

class _HubHolderState extends State<_HubHolder> {
  final RefreshHub _hub = RefreshHub();

  @override
  Widget build(BuildContext context) {
    return _RefreshScope(
      hub: _hub,
      child: RefreshIndicator(
        onRefresh: _hub.refreshAll,
        child: PageBody(location: widget.location, children: [widget.child]),
      ),
    );
  }
}

/// Registers [reload] with the page's [RefreshHub] for the widget's life.
mixin PullToRefresh<T extends StatefulWidget> on State<T> {
  RefreshHub? _hub;

  Future<void> reload();

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final hub = refreshHubOf(context);
    if (!identical(hub, _hub)) {
      _hub?.remove(reload);
      _hub = hub?..add(reload);
    }
  }

  @override
  void dispose() {
    _hub?.remove(reload);
    super.dispose();
  }
}

/// A small rounded label in [tone] (for statuses this app translates itself).
class ToneBadge extends StatelessWidget {
  const ToneBadge({super.key, required this.label, required this.tone});

  final String label;
  final AlertTone tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.x2,
        vertical: 2,
      ),
      decoration: BoxDecoration(
        color: tone.fill,
        border: Border.all(color: tone.border),
        borderRadius: const BorderRadius.all(Radius.circular(999)),
      ),
      child: Text(
        label,
        style: AppTypography.caption(weight: FontWeight.w600, color: tone.text),
      ),
    );
  }
}

/// A safe sentence for a refused step. A 400 without field errors is a move
/// the record's current state does not allow (the server's own text is not
/// shown); field errors name the fields; anything else is the usual message.
String stepErrorMessage(
  AppLocalizations t,
  Object error, {
  Map<String, String> fieldLabels = const {},
}) {
  if (error is ApiException &&
      error.kind == ApiErrorKind.validation &&
      error.fieldErrors.isEmpty) {
    return t.opsStepRefused;
  }
  return clinicalErrorMessage(t, error, fieldLabels: fieldLabels);
}

/// A line explaining that the role may look but not change.
class ReadOnlyNotice extends StatelessWidget {
  const ReadOnlyNotice({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.x4),
    child: HmsAlert(title: message),
  );
}

/// A confirmed outcome or a refusal shown above a page's content.
class OutcomeBanner extends StatelessWidget {
  const OutcomeBanner({super.key, this.success, this.error});

  final String? success;
  final String? error;

  @override
  Widget build(BuildContext context) {
    if (error == null && success == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.x4),
      child: HmsAlert(
        tone: error != null ? AlertTone.danger : AlertTone.success,
        title: error ?? success!,
      ),
    );
  }
}
