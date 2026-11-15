/// Patient portal paths. The list pages keep the web's URLs
/// (src/layouts/PatientLayout.jsx); booking, notifications and profile are
/// app pages under the same `/patient/` prefix, so the router's patient-only
/// rule covers them.
abstract final class PatientRoutes {
  static const appointments = '/patient/appointments';
  static const book = '/patient/appointments/book';
  static const queue = '/patient/queue';
  static const documents = '/patient/documents';
  static const prescriptions = '/patient/prescriptions';
  static const labResults = '/patient/lab-results';
  static const bills = '/patient/bills';
  static const notifications = '/patient/notifications';
  static const profile = '/patient/profile';
}

/// The page a notification is about, from its `notification_type` (the
/// backend's `NotificationEvent` values), or null when it has no page.
String? routeForNotification(String type) {
  if (type.startsWith('appointment_')) return PatientRoutes.appointments;
  if (type.startsWith('queue_') ||
      type.startsWith('patient_') ||
      type.startsWith('consultation_')) {
    return PatientRoutes.queue;
  }
  return null;
}
