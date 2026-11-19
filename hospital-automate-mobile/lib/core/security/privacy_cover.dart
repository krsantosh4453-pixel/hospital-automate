import 'package:flutter/material.dart';

/// Hides the app's content whenever it is not in the foreground, so the
/// app-switcher snapshot (iOS) and the recents thumbnail never show patient
/// records.
///
/// On Android, release builds also set `FLAG_SECURE` on the window
/// (MainActivity.kt), which blocks screenshots, screen recording and the
/// recents thumbnail at the OS level. iOS has no equivalent screenshot block;
/// there this cover is what keeps PHI out of the switcher snapshot, which
/// iOS takes after the app becomes inactive.
class PrivacyCover extends StatefulWidget {
  const PrivacyCover({super.key, required this.child});

  final Widget child;

  @override
  State<PrivacyCover> createState() => _PrivacyCoverState();
}

class _PrivacyCoverState extends State<PrivacyCover> {
  late final AppLifecycleListener _listener;
  bool _covered = false;

  @override
  void initState() {
    super.initState();
    _covered = _shouldCover(WidgetsBinding.instance.lifecycleState);
    _listener = AppLifecycleListener(onStateChange: _onStateChange);
  }

  static bool _shouldCover(AppLifecycleState? state) =>
      state != null && state != AppLifecycleState.resumed;

  void _onStateChange(AppLifecycleState state) {
    final covered = _shouldCover(state);
    if (covered != _covered) setState(() => _covered = covered);
  }

  @override
  void dispose() {
    _listener.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      textDirection: TextDirection.ltr,
      children: [
        // Kept mounted (no state loss) but excluded from semantics while covered.
        ExcludeSemantics(excluding: _covered, child: widget.child),
        if (_covered)
          const Positioned.fill(
            child: ColoredBox(
              key: Key('privacy-cover'),
              color: Color(0xFFFFFFFF),
              child: Center(
                child: Icon(
                  Icons.lock_outline,
                  size: 48,
                  color: Color(0xFF64748B),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
