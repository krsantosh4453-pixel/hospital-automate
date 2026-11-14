import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_scope.dart';
import '../../core/routing/app_routes.dart';
import '../../core/theme/app_spacing.dart';
import '../../shared/widgets/app_backdrop.dart';
import 'app_header.dart';
import 'nav_config.dart';
import 'sidebar.dart';

/// layout.jsx: sidebar + header + page, adapted by width:
/// * phones (< 768): drawer from the left, opened from the header;
/// * tablets (768–1023): persistent icon rail, drawer for the full menu;
/// * wide screens (≥ 1024): full sidebar that collapses to the rail.
class AppShell extends StatefulWidget {
  const AppShell({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  final _scaffoldKey = GlobalKey<ScaffoldState>();
  bool _collapsed = false;

  @override
  Widget build(BuildContext context) {
    final services = AppScope.of(context);
    return ListenableBuilder(
      listenable: Listenable.merge([services.session, services.locale]),
      builder: (context, _) {
        final session = services.session.state;
        final groups = session.isStaff
            ? visibleStaffNav(session.canView)
            : session.isPatient
            ? patientNav
            : guestStaffNav();
        final width = MediaQuery.sizeOf(context).width;
        final mode = width >= AppBreakpoints.lg
            ? _SidebarMode.full
            : width >= AppBreakpoints.md
            ? _SidebarMode.rail
            : _SidebarMode.drawer;

        Widget sidebar({
          required bool collapsed,
          VoidCallback? onToggle,
          VoidCallback? onClose,
        }) => Sidebar(
          groups: groups,
          location: widget.location,
          session: session,
          collapsed: collapsed,
          onToggleCollapsed: onToggle,
          onClose: onClose,
          onNavigate: (item) => _go(item.path, closeDrawer: onClose != null),
          onSignIn: () =>
              _go(AppRoutes.staffLogin, closeDrawer: onClose != null),
        );

        final drawerWidth = (width * AppDimensions.drawerViewportFraction)
            .clamp(0.0, AppDimensions.drawerMaxWidth);
        final header = AppHeader(
          session: session,
          locale: services.locale,
          groups: groups,
          onOpenNavigation: mode == _SidebarMode.full
              ? null
              : () => _scaffoldKey.currentState?.openDrawer(),
          onNavigate: (item) => _go(item.path),
          onSignIn: (staff) =>
              _go(staff ? AppRoutes.staffLogin : AppRoutes.patientLogin),
          onSignOut: services.auth.signOut,
          onOpenSettings: () => _go(AppRoutes.settings),
          onSelectHospital: services.session.selectHospital,
        );

        final railCollapsed = mode == _SidebarMode.rail || _collapsed;
        return Scaffold(
          key: _scaffoldKey,
          drawer: mode == _SidebarMode.full
              ? null
              : SizedBox(
                  width: drawerWidth,
                  child: sidebar(
                    collapsed: false,
                    onClose: () => _scaffoldKey.currentState?.closeDrawer(),
                  ),
                ),
          drawerScrimColor: Theme.of(context).colorScheme.scrim,
          body: Row(
            children: [
              if (mode != _SidebarMode.drawer)
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  // In landscape a camera cutout adds a left inset; the
                  // sidebar pads itself by it, so it must also be wider.
                  width:
                      (railCollapsed
                          ? AppDimensions.sidebarRailWidth
                          : AppDimensions.sidebarWidth) +
                      MediaQuery.paddingOf(context).left,
                  child: sidebar(
                    collapsed: railCollapsed,
                    onToggle: mode == _SidebarMode.full
                        ? () => setState(() => _collapsed = !_collapsed)
                        : () => _scaffoldKey.currentState?.openDrawer(),
                  ),
                ),
              Expanded(
                // The sidebar already covers the left inset; don't pad twice.
                child: MediaQuery.removePadding(
                  context: context,
                  removeLeft: mode != _SidebarMode.drawer,
                  child: Column(
                    children: [
                      header,
                      Expanded(child: AppBackdrop(child: widget.child)),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _go(String path, {bool closeDrawer = false}) {
    if (closeDrawer) _scaffoldKey.currentState?.closeDrawer();
    if (path != widget.location) context.go(path);
  }
}

enum _SidebarMode { drawer, rail, full }
