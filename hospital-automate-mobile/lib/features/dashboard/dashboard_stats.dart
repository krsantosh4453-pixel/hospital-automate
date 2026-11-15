import 'package:flutter/foundation.dart';

/// A patient in the dashboard's "Recently registered" list.
@immutable
class RecentPatient {
  const RecentPatient({
    required this.id,
    required this.name,
    this.patientId,
    this.age,
    this.gender,
    this.createdAt,
  });

  factory RecentPatient.fromJson(Map<String, Object?> json) => RecentPatient(
    id: (json['id'] as num?)?.toInt() ?? 0,
    name: '${json['name'] ?? ''}',
    patientId: json['uhid'] as String? ?? json['patient_id'] as String?,
    age: (json['age'] as num?)?.toInt(),
    gender: json['gender'] as String?,
    createdAt: DateTime.tryParse('${json['created_at'] ?? ''}'),
  );

  final int id;
  final String name;
  final String? patientId;
  final int? age;
  final String? gender;
  final DateTime? createdAt;
}

/// `GET /api/v1/home/stats/detail/?hospital=<id>`: live counts for one
/// hospital, scoped by the server to what the caller's role may see.
@immutable
class DashboardStats {
  const DashboardStats({
    required this._statistics,
    this.recentPatients = const [],
  });

  factory DashboardStats.fromJson(Object? json) {
    if (json is! Map) {
      throw const FormatException('dashboard stats: expected an object');
    }
    final raw = json['statistics'];
    final statistics = <String, Map<String, Object?>>{
      if (raw is Map)
        for (final entry in raw.entries)
          if (entry.value is Map)
            '${entry.key}': Map<String, Object?>.from(entry.value as Map),
    };
    final patients = json['recent_patients'];
    return DashboardStats(
      statistics: statistics,
      recentPatients: [
        if (patients is List)
          for (final p in patients)
            if (p is Map) RecentPatient.fromJson(Map<String, Object?>.from(p)),
      ],
    );
  }

  final Map<String, Map<String, Object?>> _statistics;
  final List<RecentPatient> recentPatients;

  /// A count, or 0 when the server left it out.
  int count(String section, String key) =>
      (_statistics[section]?[key] as num?)?.toInt() ?? 0;

  /// A money amount; null when the server withholds it from this role.
  double? money(String section, String key) =>
      (_statistics[section]?[key] as num?)?.toDouble();

  int get bedsTotal => count('beds', 'total');
  int get bedsAvailable => count('beds', 'available');
  int get bedsOccupied {
    final occupied = _statistics['beds']?['occupied'] as num?;
    return occupied?.toInt() ?? (bedsTotal - bedsAvailable).clamp(0, bedsTotal);
  }
}
