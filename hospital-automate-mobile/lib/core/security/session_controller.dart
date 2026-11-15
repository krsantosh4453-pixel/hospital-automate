import 'package:flutter/foundation.dart';

import 'token_store.dart';

/// One hospital the signed-in person may act in, as `/auth/me/contexts/`
/// returns it: the role there and its permissions (`<Module>.<Action>`,
/// already narrowed by the hospital's restrictions on the server).
@immutable
class HospitalContext {
  const HospitalContext({
    required this.id,
    required this.name,
    this.role,
    this.department,
    this.permissions = const {},
  });

  final int id;
  final String name;
  final String? role;
  final String? department;
  final Set<String> permissions;
}

/// `account_type` from `/auth/me/contexts/`.
enum AccountType {
  staff,
  patient,

  /// A family member with view-only access to a patient.
  proxy;

  static AccountType? parse(Object? value) => switch (value) {
    'staff' => AccountType.staff,
    'patient' => AccountType.patient,
    'proxy' => AccountType.proxy,
    _ => null,
  };
}

/// What `/auth/patient/me/` says about a signed-in patient.
@immutable
class PatientProfile {
  const PatientProfile({
    required this.id,
    required this.name,
    this.age,
    this.gender,
    this.phone,
    this.email,
    this.emailVerified = false,
    this.phoneVerified = false,
  });

  final int id;
  final String name;
  final int? age;
  final String? gender;
  final String? phone;
  final String? email;
  final bool emailVerified;
  final bool phoneVerified;
}

/// The signed-in person, shown in the header and greeting.
@immutable
class SessionUser {
  const SessionUser({
    required this.displayName,
    this.id,
    this.username,
    this.firstName,
    this.accountType = AccountType.staff,
    this.patient,
  });

  final int? id;
  final String? username;
  final String displayName;
  final String? firstName;
  final AccountType accountType;

  /// Set for patients and family members.
  final PatientProfile? patient;

  bool get isStaff => accountType == AccountType.staff;
}

/// Who is using the app and in which hospital. The server stays the
/// authority: [canView] only hides navigation the server would refuse.
@immutable
class SessionState {
  const SessionState({
    this.user,
    this.hospitals = const [],
    this.activeHospitalId,
  });

  static const signedOut = SessionState();

  final SessionUser? user;
  final List<HospitalContext> hospitals;
  final int? activeHospitalId;

  bool get isSignedIn => user != null;
  bool get isStaff => user?.isStaff ?? false;
  bool get isPatient => isSignedIn && !isStaff;

  HospitalContext? get activeHospital {
    for (final hospital in hospitals) {
      if (hospital.id == activeHospitalId) return hospital;
    }
    return null;
  }

  String? get activeRole => activeHospital?.role;

  /// Whether the active role may view [module]; `null` means any signed-in staff.
  bool canView(String? module) {
    if (!isStaff) return false;
    if (module == null) return true;
    return activeHospital?.permissions.contains('$module.View') ?? false;
  }

  SessionState copyWith({int? activeHospitalId}) => SessionState(
    user: user,
    hospitals: hospitals,
    activeHospitalId: activeHospitalId ?? this.activeHospitalId,
  );
}

enum SessionStatus {
  /// Reading the stored session at start-up.
  restoring,
  signedOut,
  signedIn,

  /// A stored session exists but the server could not be reached to check it.
  restoreFailed,
}

/// Work to undo at sign-out, e.g. clearing a cached patient list.
typedef SessionCleanup = Future<void> Function();

/// Owns the session: who is signed in, the chosen hospital and sign-out
/// cleanup. `AuthService` signs people in and calls [start].
class SessionController extends ChangeNotifier {
  SessionController({
    required this._tokenStore,
    SessionState initial = SessionState.signedOut,
  }) : _state = initial,
       _status = initial.isSignedIn
           ? SessionStatus.signedIn
           : SessionStatus.signedOut;

  final TokenStore _tokenStore;
  final List<SessionCleanup> _cleanups = [];
  SessionState _state;
  SessionStatus _status;
  bool _expired = false;

  SessionState get state => _state;
  SessionStatus get status => _status;

  /// True after the server ended the session (refresh refused) until the
  /// next sign-in, so the sign-in screen can say why.
  bool get sessionExpired => _expired;

  /// Hospital sent as `X-Hospital-ID` on staff requests.
  int? get activeHospitalId => _state.activeHospital?.id;

  Future<String?> accessToken() => _tokenStore.readAccessToken();

  void setStatus(SessionStatus status) {
    if (status == _status) return;
    _status = status;
    notifyListeners();
  }

  /// Begins a signed-in session. Keeps [preferredHospitalId] when the
  /// person still belongs to it, otherwise the first hospital.
  Future<void> start(SessionState state, {int? preferredHospitalId}) async {
    final ids = state.hospitals.map((h) => h.id).toList();
    final active = ids.contains(preferredHospitalId)
        ? preferredHospitalId
        : (ids.isEmpty ? null : ids.first);
    _state = SessionState(
      user: state.user,
      hospitals: state.hospitals,
      activeHospitalId: active,
    );
    _status = SessionStatus.signedIn;
    _expired = false;
    await _tokenStore.saveHospitalId(active);
    notifyListeners();
  }

  /// Switches the hospital the app acts in; ignored for hospitals the
  /// person does not belong to. The server re-checks membership anyway.
  Future<void> selectHospital(int hospitalId) async {
    if (_state.hospitals.every((h) => h.id != hospitalId) ||
        hospitalId == _state.activeHospitalId) {
      return;
    }
    _state = _state.copyWith(activeHospitalId: hospitalId);
    notifyListeners();
    await _tokenStore.saveHospitalId(hospitalId);
  }

  /// Registers [cleanup] to run at every sign-out. Returns a function that unregisters it.
  VoidCallback onSignOut(SessionCleanup cleanup) {
    _cleanups.add(cleanup);
    return () => _cleanups.remove(cleanup);
  }

  /// Forgets tokens, the hospital, the session and every cached record,
  /// even if a cleanup fails. [expired]: the server ended the session.
  Future<void> signOut({bool expired = false}) async {
    _state = SessionState.signedOut;
    _status = SessionStatus.signedOut;
    _expired = expired;
    notifyListeners();
    final failures = <Object>[];
    for (final cleanup in [..._cleanups]) {
      try {
        await cleanup();
      } catch (error) {
        failures.add(error);
      }
    }
    await _tokenStore.clear();
    if (failures.isNotEmpty) {
      throw StateError('${failures.length} sign-out cleanup step(s) failed');
    }
  }
}
