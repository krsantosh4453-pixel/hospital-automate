import 'dart:async';

import 'package:flutter/widgets.dart';

/// Calls [onTick] every [interval] while the app is in front. Pauses when the
/// app is hidden (no requests, no battery use in the background) and, on
/// return, refreshes at once and resumes. [isBusy] skips a tick while the
/// previous request is still running, so polls never overlap.
class Poller {
  Poller({
    required this.interval,
    required this.onTick,
    bool Function()? isBusy,
  }) : _isBusy = isBusy ?? _never {
    _lifecycle = AppLifecycleListener(
      onResume: () {
        _tick();
        _start();
      },
      onHide: _stop,
    );
    _start();
  }

  final Duration interval;
  final Future<void> Function() onTick;
  final bool Function() _isBusy;
  late final AppLifecycleListener _lifecycle;
  Timer? _timer;

  static bool _never() => false;

  /// Whether the timer is running (false while the app is hidden).
  bool get isRunning => _timer != null;

  void _start() {
    _timer?.cancel();
    _timer = Timer.periodic(interval, (_) => _tick());
  }

  void _stop() {
    _timer?.cancel();
    _timer = null;
  }

  void _tick() {
    if (_isBusy()) return;
    unawaited(onTick());
  }

  void dispose() {
    _stop();
    _lifecycle.dispose();
  }
}
