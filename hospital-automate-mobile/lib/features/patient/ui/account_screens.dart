import 'package:flutter/material.dart';

import '../../ipd/ui/clinical_work_sections.dart' show PatientHistorySection;

import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/security/session_controller.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/avatar.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../data/record_models.dart';
import '../record_loader.dart';
import 'patient_routes.dart';
import 'patient_ui.dart';

/// `/patient/notifications`: in-app notifications the hospital sent.
/// Push delivery (FCM/APNs) is not built on the backend; these are fetched.
class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late final _repository = AppScope.read(context).patient;
  late final RecordLoader<List<PatientNotification>> _loader = RecordLoader(
    _repository.notifications,
  );
  final Set<int> _marking = {};
  String? _markError;

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _loader.dispose();
    super.dispose();
  }

  Future<void> _open(PatientNotification note) async {
    final route = routeForNotification(note.type);
    if (!note.isRead && !_marking.contains(note.id)) {
      setState(() {
        _marking.add(note.id);
        _markError = null;
      });
      try {
        await _repository.markNotificationRead(note.id);
        final rows = _loader.data ?? const <PatientNotification>[];
        _loader.replace([
          for (final row in rows) row.id == note.id ? row.markedRead() : row,
        ]);
      } catch (error) {
        if (mounted) {
          setState(() => _markError = apiErrorMessage(context.l10n, error));
        }
      } finally {
        if (mounted) setState(() => _marking.remove(note.id));
      }
    }
    if (route != null && mounted) context.go(route);
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.patientNavNotifications,
          description: t.notificationsIntro,
        ),
        const SizedBox(height: AppSpacing.x6),
        if (_markError != null) ...[
          HmsAlert(
            tone: AlertTone.warning,
            title: t.markReadFailed,
            message: _markError,
          ),
          const SizedBox(height: AppSpacing.x4),
        ],
        RecordSection<List<PatientNotification>>(
          loader: _loader,
          builder: (context, notes) {
            if (notes.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.bell,
                  title: t.noNotifications,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [
                  for (final note in notes)
                    _NotificationRow(
                      note: note,
                      busy: _marking.contains(note.id),
                      onTap: () => _open(note),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _NotificationRow extends StatelessWidget {
  const _NotificationRow({
    required this.note,
    required this.busy,
    required this.onTap,
  });

  final PatientNotification note;
  final bool busy;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final weight = note.isRead ? FontWeight.w400 : FontWeight.w700;
    return Semantics(
      label: note.isRead ? null : t.unread,
      child: InkWell(
        onTap: busy ? null : onTap,
        child: Padding(
          padding: AppSpacing.cardRow,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                note.isRead ? LucideIcons.bell : LucideIcons.bellDot,
                size: 18,
              ),
              const SizedBox(width: AppSpacing.x3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(note.title, style: AppTypography.body(weight: weight)),
                    Text(note.message, style: AppTypography.small()),
                    Text(
                      formatDateTime(t, note.createdAt),
                      style: AppTypography.caption(),
                    ),
                  ],
                ),
              ),
              if (busy)
                const SizedBox.square(
                  dimension: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// `/patient/documents`: the patient's own files (metadata). Opening a file
/// is not offered yet: it would need a viewer that keeps the file in the
/// app's private storage, which is not built.
class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  late final RecordLoader<List<PatientDocument>> _loader = RecordLoader(
    AppScope.read(context).patient.documents,
  );

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _loader.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.patientNavRecords, description: t.documentsIntro),
        if (AppScope.of(context).session.state.user?.patient?.id
            case final patientId?) ...[
          const SizedBox(height: AppSpacing.x4),
          PatientHistorySection(patientId: patientId),
        ],
        const SizedBox(height: AppSpacing.x4),
        HmsAlert(title: t.documentsViewOnWeb),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<PatientDocument>>(
          loader: _loader,
          builder: (context, documents) {
            if (documents.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.fileText,
                  title: t.noDocumentsYet,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [
                  for (final doc in documents)
                    Padding(
                      padding: AppSpacing.cardRow,
                      child: Row(
                        children: [
                          const Icon(LucideIcons.fileText, size: 18),
                          const SizedBox(width: AppSpacing.x3),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  doc.title,
                                  style: AppTypography.body(
                                    weight: FontWeight.w600,
                                  ),
                                ),
                                Text(
                                  [
                                    formatDay(t, doc.uploadedAt),
                                    ?doc.folder,
                                    if (doc.fileSize != null)
                                      _fileSize(doc.fileSize!),
                                  ].join(' · '),
                                  style: AppTypography.small(),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

String _fileSize(int bytes) {
  const kb = 1024;
  if (bytes < kb) return '$bytes B';
  if (bytes < kb * kb) return '${(bytes / kb).toStringAsFixed(0)} KB';
  return '${(bytes / (kb * kb)).toStringAsFixed(1)} MB';
}

/// `/patient/profile`: what `auth/patient/me/` returns, read fresh.
/// Changes are made at the hospital: the backend has no self-edit endpoint.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late final SessionState _session = AppScope.read(context).session.state;
  late final RecordLoader<SessionUser> _loader = RecordLoader(
    () =>
        AppScope.read(context).patient
            .profile(_session.user?.accountType ?? AccountType.patient),
  );

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _loader.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.myProfile,
          description: t.profileIntro,
          actions: [
            HmsButton(
              label: t.refresh,
              icon: LucideIcons.refreshCw,
              variant: HmsButtonVariant.secondary,
              onPressed: _loader.load,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsAlert(title: t.profileChangesAtHospital),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<SessionUser>(
          loader: _loader,
          skeletons: 1,
          builder: (context, user) {
            final p = user.patient;
            if (p == null) {
              return HmsCard(child: HmsEmptyState(title: t.errorUnknown));
            }
            final active = _session.activeHospital;
            return HmsCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: AppSpacing.cardHeader,
                    child: Row(
                      children: [
                        HmsAvatar(name: p.name, size: AvatarSize.large),
                        const SizedBox(width: AppSpacing.x3),
                        Expanded(
                          child: Text(p.name, style: AppTypography.cardTitle()),
                        ),
                      ],
                    ),
                  ),
                  HmsDividedColumn(
                    children: [
                      DetailRow(
                        label: t.patientId,
                        value: p.uhidFor(active?.id),
                      ),
                      DetailRow(label: t.gender, value: p.gender),
                      DetailRow(
                        label: t.ageLabel,
                        value: p.age == null ? null : t.ageYears('${p.age}'),
                      ),
                      DetailRow(
                        label: t.mobileNumber,
                        value: _verified(t, p.phone, p.phoneVerified),
                      ),
                      DetailRow(
                        label: t.email,
                        value: _verified(t, p.email, p.emailVerified),
                      ),
                      DetailRow(label: t.selectedHospital, value: active?.name),
                      DetailRow(
                        label: t.myHospitals,
                        value: _session.hospitals.map((h) => h.name).join(', '),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }

  static String? _verified(AppLocalizations t, String? value, bool verified) =>
      value == null || value.isEmpty
      ? null
      : '$value (${verified ? t.verified : t.notVerified})';
}
