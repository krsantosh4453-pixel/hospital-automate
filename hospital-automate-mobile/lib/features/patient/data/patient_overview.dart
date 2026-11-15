import 'package:flutter/foundation.dart';

import 'appointment_models.dart';
import 'patient_repository.dart';
import 'record_models.dart';

/// Everything the patient home shows, loaded side by side. Each part is
/// null when its request failed, so one unavailable module shows "—"
/// instead of hiding the rest (the web's `Promise.allSettled`).
@immutable
class PatientOverview {
  const PatientOverview({
    this.appointments,
    this.queueTokens,
    this.prescriptions,
    this.labTests,
    this.invoices,
    this.notifications,
  });

  static Future<PatientOverview> load(PatientRepository repository) async {
    Future<T?> settle<T>(Future<T> Function() fetch) async {
      try {
        return await fetch();
      } catch (_) {
        return null;
      }
    }

    final results = await Future.wait<Object?>([
      settle(repository.appointments),
      settle(repository.queueTokens),
      settle(repository.prescriptions),
      settle(repository.labTests),
      settle(repository.invoices),
      settle(repository.notifications),
    ]);
    return PatientOverview(
      appointments: results[0] as List<Appointment>?,
      queueTokens: results[1] as List<QueueToken>?,
      prescriptions: results[2] as List<Prescription>?,
      labTests: results[3] as List<LabTest>?,
      invoices: results[4] as List<Invoice>?,
      notifications: results[5] as List<PatientNotification>?,
    );
  }

  final List<Appointment>? appointments;
  final List<QueueToken>? queueTokens;
  final List<Prescription>? prescriptions;
  final List<LabTest>? labTests;
  final List<Invoice>? invoices;
  final List<PatientNotification>? notifications;

  bool get isPartial => [
    appointments,
    queueTokens,
    prescriptions,
    labTests,
    invoices,
    notifications,
  ].any((part) => part == null);

  bool get isEmpty => [
    appointments,
    queueTokens,
    prescriptions,
    labTests,
    invoices,
    notifications,
  ].every((part) => part == null);

  /// Upcoming bookings, soonest first.
  List<Appointment> get upcoming => [
    for (final a in appointments ?? const <Appointment>[])
      if (a.isUpcoming) a,
  ]..sort((a, b) => a.sortKey.compareTo(b.sortKey));

  int? get pastVisits => appointments
      ?.where((a) => a.status == AppointmentStatus.completed)
      .length;

  int? get currentPrescriptions =>
      prescriptions?.where((p) => p.isCurrent).length;

  int? get billsWithBalance => invoices?.where((i) => i.hasBalance).length;

  int? get unreadNotifications => notifications?.where((n) => !n.isRead).length;

  List<QueueToken> get activeTokens => [
    for (final token in queueTokens ?? const <QueueToken>[])
      if (token.isActive) token,
  ];

  List<T> _latest<T>(List<T>? rows, DateTime? Function(T) when, int count) {
    final sorted = [...?rows]
      ..sort(
        (a, b) => (when(b) ?? DateTime(0)).compareTo(when(a) ?? DateTime(0)),
      );
    return sorted.take(count).toList();
  }

  List<Prescription> recentPrescriptions(int count) =>
      _latest(prescriptions, (p) => p.createdAt, count);

  List<LabTest> recentLabTests(int count) =>
      _latest(labTests, (l) => l.releasedAt ?? l.testDate, count);
}
