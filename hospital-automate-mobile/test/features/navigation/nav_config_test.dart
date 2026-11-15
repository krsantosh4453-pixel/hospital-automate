import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/features/navigation/nav_config.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';

void main() {
  final en = AppLocalizationsEn();

  test('has the web groups in the web order', () {
    expect(staffNav.map((g) => g.id), [
      'overview',
      'front-desk',
      'clinical',
      'diagnostics',
      'operations',
      'people',
      'admin',
      'system',
    ]);
  });

  test('has every web navigation item with its label and path', () {
    final items = [
      for (final g in staffNav)
        for (final i in g.items) '${i.path}=${i.label(en)}',
    ];

    expect(items, [
      '/=Home',
      '/patients=Patients',
      '/appointments=Appointments',
      '/queue=Queue',
      '/consultation=Consultation',
      '/prescription=Prescription',
      '/nurses=Nurses / Vitals',
      '/ipd=IPD / Ward / Beds',
      '/emergency=Emergency',
      '/ai-scribe=AI Scribe',
      '/laboratory=Laboratory',
      '/radiology=Radiology',
      '/pharmacy=Pharmacy',
      '/compounter=Compounder',
      '/blood-bank=Blood Bank',
      '/billing=Billing',
      '/inventory=Inventory',
      '/services=Hospital services',
      '/reports=Reports',
      '/doctors=Doctors',
      '/admin=Admin Dashboard',
      '/admin/users=Users',
      '/admin/roles=Roles',
      '/admin/hospitals=Hospitals',
      '/admin/departments=Departments',
      '/admin/nurse-duty=Nurse duty',
      '/admin/permissions=Permissions',
      '/admin/audit=Audit log',
      '/emergency-access=Emergency access',
      '/admin/security=Security settings',
      '/settings=Settings',
    ]);
  });

  test('visitors see everything except Administration', () {
    expect(guestStaffNav().map((g) => g.id), isNot(contains('admin')));
    expect(guestStaffNav(), hasLength(staffNav.length - 1));
  });

  test(
    'a role sees only the modules it may view, and empty groups disappear',
    () {
      final nav = visibleStaffNav(
        (module) => module == null || module == 'Laboratory',
      );

      final paths = [
        for (final g in nav)
          for (final i in g.items) i.path,
      ];
      expect(paths, [
        '/',
        '/laboratory',
        '/radiology',
        '/services',
        '/settings',
      ]);
      expect(nav.map((g) => g.id), isNot(contains('admin')));
    },
  );

  test('Administration appears once any admin module is viewable', () {
    final nav = visibleStaffNav(
      (module) => module == null || module == 'Users',
    );

    final admin = nav.firstWhere((g) => g.id == 'admin');
    expect(admin.items.map((i) => i.path), [
      '/admin',
      '/admin/users',
      '/emergency-access',
    ]);
  });

  test('Home matches only "/", other items match their sub-paths', () {
    expect(findNavMatch('/')?.item.path, '/');
    expect(findNavMatch('/patients/42')?.item.path, '/patients');
    expect(findNavMatch('/admin')?.item.path, '/admin');
    expect(findNavMatch('/admin/users')?.item.path, '/admin/users');
    expect(findNavMatch('/patients-archive'), isNull);
  });
}
