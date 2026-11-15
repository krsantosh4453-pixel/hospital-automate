import 'package:flutter/foundation.dart';

import '../../core/security/session_controller.dart';

/// Sent with every sign-in so the server's session list names this device.
@immutable
class DeviceInfo {
  const DeviceInfo({
    required this.deviceId,
    required this.platform,
    required this.appVersion,
  });

  final String deviceId;

  /// `android`, `ios` or `other` (DeviceSession.Platform on the server).
  final String platform;
  final String appVersion;

  Map<String, String> toJson() => {
    'device_id': deviceId,
    'platform': platform,
    'app_version': appVersion,
  };
}

/// `staff/login/otp/start/`: a code was sent; [challenge] proves the
/// password step and is held in memory only until the code is entered.
@immutable
class StaffOtpChallenge {
  const StaffOtpChallenge({required this.challenge, this.maskedPhone});

  factory StaffOtpChallenge.fromJson(Object? json) {
    if (json is! Map || json['challenge'] is! String) {
      throw const FormatException('OTP start: no challenge');
    }
    final message = json['message'];
    final masked = message is String
        ? RegExp(r'\(([^)]*)\)').firstMatch(message)?.group(1)
        : null;
    return StaffOtpChallenge(
      challenge: json['challenge'] as String,
      maskedPhone: masked,
    );
  }

  final String challenge;

  /// e.g. `******3210`, from the server's message.
  final String? maskedPhone;

  @override
  String toString() => 'StaffOtpChallenge(<redacted>)';
}

/// How a one-time code was (or would be) delivered: `sms`, `email` or
/// `console` (development server: printed to its log, never sent).
@immutable
class OtpDelivery {
  const OtpDelivery({this.channel});

  factory OtpDelivery.fromJson(Object? json) =>
      OtpDelivery(channel: json is Map ? json['delivery'] as String? : null);

  final String? channel;

  bool get printedOnServer => channel == 'console';
}

/// A patient registration (`auth/register/`, role Patient).
@immutable
class PatientRegistration {
  const PatientRegistration({
    required this.fullName,
    required this.email,
    required this.phone,
    required this.password,
    required this.confirmPassword,
    this.gender,
    this.dateOfBirth,
  });

  final String fullName;
  final String email;
  final String phone;
  final String password;
  final String confirmPassword;
  final String? gender;

  /// `YYYY-MM-DD`.
  final String? dateOfBirth;

  Map<String, String> toJson() => {
    'role': 'Patient',
    'full_name': fullName,
    'email': email,
    'phone': phone,
    'password': password,
    'confirm_password': confirmPassword,
    'gender': ?gender,
    'date_of_birth': ?dateOfBirth,
  };

  @override
  String toString() => 'PatientRegistration(<redacted>)';
}

/// `auth/register/` answered 201: the email still has to be verified.
@immutable
class RegistrationResult {
  const RegistrationResult({required this.email, required this.delivery});

  factory RegistrationResult.fromJson(Object? json, String email) {
    final verification = json is Map ? json['verification'] : null;
    return RegistrationResult(
      email: email,
      delivery: OtpDelivery.fromJson(verification),
    );
  }

  final String email;
  final OtpDelivery delivery;
}

/// `GET auth/me/contexts/`.
@immutable
class MeContexts {
  const MeContexts({required this.accountType, required this.hospitals});

  factory MeContexts.fromJson(Object? json) {
    if (json is! Map) throw const FormatException('me/contexts: not an object');
    final contexts = json['contexts'];
    return MeContexts(
      accountType: AccountType.parse(json['account_type']),
      hospitals: [
        if (contexts is List)
          for (final context in contexts)
            if (context is Map && context['hospital'] is Map)
              _hospitalFrom(Map<String, Object?>.from(context)),
      ],
    );
  }

  /// Null for platform staff and accounts with nothing to act as; the app
  /// does not support those.
  final AccountType? accountType;
  final List<HospitalContext> hospitals;

  static HospitalContext _hospitalFrom(Map<String, Object?> context) {
    final hospital = context['hospital']! as Map;
    final permissions = context['permissions'];
    return HospitalContext(
      id: (hospital['id'] as num).toInt(),
      name: '${hospital['name'] ?? ''}',
      role: context['role'] as String?,
      department: context['department'] as String?,
      permissions: {
        if (permissions is List)
          for (final p in permissions) '$p',
      },
    );
  }
}

/// `GET auth/staff/me/` → the signed-in staff member.
SessionUser staffUserFromJson(Object? json) {
  final user = json is Map ? json['user'] : null;
  if (user is! Map) throw const FormatException('staff/me: no user');
  final first = '${user['first_name'] ?? ''}'.trim();
  final last = '${user['last_name'] ?? ''}'.trim();
  final username = '${user['username'] ?? ''}';
  final full = [first, last].where((p) => p.isNotEmpty).join(' ');
  return SessionUser(
    id: (user['id'] as num?)?.toInt(),
    username: username,
    displayName: full.isNotEmpty ? full : username,
    firstName: first.isEmpty ? null : first,
  );
}

/// `GET auth/patient/me/` → the signed-in patient (or family member).
SessionUser patientUserFromJson(Object? json, AccountType accountType) {
  final patient = json is Map ? json['patient'] : null;
  final user = json is Map ? json['user'] : null;
  if (patient is! Map) throw const FormatException('patient/me: no patient');
  final name = '${patient['name'] ?? ''}'.trim();
  final profile = PatientProfile(
    id: (patient['id'] as num).toInt(),
    name: name,
    age: (patient['age'] as num?)?.toInt(),
    gender: patient['gender'] as String?,
    phone: patient['phone'] as String?,
    email: patient['email'] as String?,
    emailVerified: patient['email_verified'] == true,
    phoneVerified: patient['phone_verified'] == true,
  );
  return SessionUser(
    id: user is Map ? (user['id'] as num?)?.toInt() : null,
    username: user is Map ? user['username'] as String? : null,
    displayName: name.isEmpty ? 'Patient' : name,
    firstName: name.isEmpty ? null : name.split(RegExp(r'\s+')).first,
    accountType: accountType,
    patient: profile,
  );
}

/// One signed-in device from `GET auth/sessions/`.
@immutable
class DeviceSessionInfo {
  const DeviceSessionInfo({
    required this.id,
    required this.platform,
    required this.current,
    this.appVersion,
    this.userAgent,
    this.createdAt,
    this.lastUsedAt,
  });

  factory DeviceSessionInfo.fromJson(Map<String, Object?> json) =>
      DeviceSessionInfo(
        id: '${json['id']}',
        platform: '${json['platform'] ?? 'other'}',
        current: json['current'] == true,
        appVersion: json['app_version'] as String?,
        userAgent: json['user_agent'] as String?,
        createdAt: DateTime.tryParse('${json['created_at'] ?? ''}'),
        lastUsedAt: DateTime.tryParse('${json['last_used_at'] ?? ''}'),
      );

  final String id;
  final String platform;
  final bool current;
  final String? appVersion;
  final String? userAgent;
  final DateTime? createdAt;
  final DateTime? lastUsedAt;

  static List<DeviceSessionInfo> listFromJson(Object? json) {
    final sessions = json is Map ? json['sessions'] : null;
    return [
      if (sessions is List)
        for (final s in sessions)
          if (s is Map)
            DeviceSessionInfo.fromJson(Map<String, Object?>.from(s)),
    ];
  }
}

/// One patient whose records a family member may view
/// (`auth/proxy/otp/verify/` → `grants[]`).
@immutable
class ProxyGrantChoice {
  const ProxyGrantChoice({
    required this.id,
    required this.patientName,
    required this.relationship,
  });

  factory ProxyGrantChoice.fromJson(Object? json) {
    if (json is! Map || json['id'] is! int) {
      throw const FormatException('Proxy grant: no id');
    }
    return ProxyGrantChoice(
      id: json['id'] as int,
      patientName: (json['patient_name'] as String?) ?? '',
      relationship: (json['relationship'] as String?) ?? '',
    );
  }

  final int id;
  final String patientName;

  /// The family member's relationship to the patient, e.g. "Son".
  final String relationship;
}

/// A verified family-member code: a short-lived signed [ticket] (kept in
/// memory only) and the patients it may open.
@immutable
class ProxyVerification {
  const ProxyVerification({required this.ticket, required this.grants});

  factory ProxyVerification.fromJson(Object? json) {
    if (json is! Map || json['ticket'] is! String) {
      throw const FormatException('Proxy verify: no ticket');
    }
    final grants = json['grants'];
    return ProxyVerification(
      ticket: json['ticket'] as String,
      grants: List.unmodifiable(
        grants is List ? grants.map(ProxyGrantChoice.fromJson) : const [],
      ),
    );
  }

  final String ticket;
  final List<ProxyGrantChoice> grants;

  @override
  String toString() => 'ProxyVerification(<redacted>, ${grants.length})';
}
