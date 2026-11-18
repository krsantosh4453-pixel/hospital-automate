import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';

import 'core/theme/app_scroll_behavior.dart';
import 'core/app_scope.dart';
import 'core/localization/l10n.dart';
import 'core/routing/app_router.dart';
import 'core/routing/app_routes.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/ui/session_gate.dart';

/// The application: HMS theme, English/Hindi, and the routed shell.
class HmsApp extends StatefulWidget {
  const HmsApp({
    super.key,
    required this.services,
    this.initialLocation = AppRoutes.home,
  });

  final AppServices services;

  /// First page to show; tests open a page directly.
  final String initialLocation;

  @override
  State<HmsApp> createState() => _HmsAppState();
}

class _HmsAppState extends State<HmsApp> {
  late final GoRouter _router = buildAppRouter(
    session: widget.services.session,
    initialLocation: widget.initialLocation,
  );

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScope(
      services: widget.services,
      child: ListenableBuilder(
        listenable: widget.services.locale,
        builder: (context, _) => MaterialApp.router(
          onGenerateTitle: (context) =>
              '${context.l10n.appName} — ${context.l10n.appSubtitle}',
          debugShowCheckedModeBanner: false,
          // No stretch overscroll: it scales text at the ends of a scroll.
          scrollBehavior: const HmsScrollBehavior(),
          theme: AppTheme.light(),
          locale: widget.services.locale.locale,
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          routerConfig: _router,
          // Resuming a stored session, or offline while checking it.
          builder: (context, child) =>
              SessionGate(child: child ?? const SizedBox.shrink()),
        ),
      ),
    );
  }
}
