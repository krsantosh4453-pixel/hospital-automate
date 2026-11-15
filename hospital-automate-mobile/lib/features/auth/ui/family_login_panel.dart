import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_text_field.dart';
import '../auth_errors.dart';
import '../auth_models.dart';
import '../auth_service.dart';
import 'auth_card.dart';

enum _Step { mobile, code, choose }

/// ProxyLoginPanel.jsx: a family member or caregiver signs in with a code
/// sent to their own mobile, then picks whose records to view. The session
/// is view-only (the server refuses every write for it). The ticket lives
/// in this widget's memory only.
class FamilyLoginPanel extends StatefulWidget {
  const FamilyLoginPanel({super.key, this.onBusyChanged});

  /// Lets the parent lock its method tabs while a request runs.
  final ValueChanged<bool>? onBusyChanged;

  @override
  State<FamilyLoginPanel> createState() => _FamilyLoginPanelState();
}

class _FamilyLoginPanelState extends State<FamilyLoginPanel> {
  final _phone = TextEditingController();
  final _code = TextEditingController();

  _Step _step = _Step.mobile;
  String? _ticket;
  List<ProxyGrantChoice> _grants = const [];
  bool _busy = false;
  String? _error;
  String? _notice;

  @override
  void dispose() {
    _phone.dispose();
    _code.dispose();
    super.dispose();
  }

  AuthService get _auth => AppScope.of(context).auth;

  void _setBusy(bool busy) {
    setState(() => _busy = busy);
    widget.onBusyChanged?.call(busy);
  }

  Future<void> _run(AuthStep step, Future<void> Function() action) async {
    if (_busy) return;
    setState(() => _error = null);
    _setBusy(true);
    try {
      await action();
    } catch (error) {
      if (mounted) {
        setState(() => _error = authErrorMessage(context.l10n, error, step));
      }
    } finally {
      if (mounted) _setBusy(false);
    }
  }

  Future<void> _sendOtp() => _run(AuthStep.request, () async {
    final delivery = await _auth.proxyRequestOtp(_phone.text.trim());
    if (!mounted) return;
    setState(() {
      _step = _Step.code;
      _notice = delivery.printedOnServer
          ? context.l10n.otpPrintedOnServer
          : null;
    });
  });

  Future<void> _verify() => _run(AuthStep.code, () async {
    final result = await _auth.proxyVerifyOtp(
      _phone.text.trim(),
      _code.text.trim(),
    );
    _code.clear();
    if (result.grants.length == 1) {
      await _open(result.ticket, result.grants.single);
      return;
    }
    if (!mounted) return;
    setState(() {
      _ticket = result.ticket;
      _grants = result.grants;
      _step = _Step.choose;
      if (result.grants.isEmpty) _error = context.l10n.authFamilyNotAvailable;
    });
  });

  Future<void> _choose(ProxyGrantChoice grant) => _run(AuthStep.code, () async {
    final ticket = _ticket;
    if (ticket == null) return;
    await _open(ticket, grant);
  });

  Future<void> _open(String ticket, ProxyGrantChoice grant) async {
    await _auth.proxySignIn(ticket, grant);
    _ticket = null;
    if (mounted) context.go(AppRoutes.home);
  }

  void _restart() => setState(() {
    _step = _Step.mobile;
    _code.clear();
    _ticket = null;
    _grants = const [];
    _error = null;
    _notice = null;
  });

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Icon(LucideIcons.users, size: 18, color: AppColors.onCard),
            const SizedBox(width: AppSpacing.x2),
            Expanded(
              child: Text(
                t.familyTitle,
                style: AppTypography.body(weight: FontWeight.w600),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x1),
        Text(t.familyIntro, style: AppTypography.small()),
        const SizedBox(height: AppSpacing.x4),
        if (_error != null) AuthNotice(message: _error!),
        ...switch (_step) {
          _Step.mobile => _mobile(t),
          _Step.code => _codeStep(t),
          _Step.choose => _chooseStep(t),
        },
      ],
    );
  }

  Widget _primary(String label, VoidCallback onPressed) => HmsButton(
    label: label,
    size: HmsButtonSize.large,
    surface: HmsSurface.card,
    expand: true,
    loading: _busy,
    onPressed: onPressed,
  );

  List<Widget> _mobile(AppLocalizations t) => [
    HmsTextField(
      label: t.yourMobileNumber,
      controller: _phone,
      required: true,
      placeholder: t.enter10DigitNumber,
      prefixText: '+91 ',
      keyboardType: TextInputType.phone,
      maxLength: 10,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      autofillHints: const [AutofillHints.telephoneNumberNational],
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _sendOtp(),
    ),
    const SizedBox(height: AppSpacing.x5),
    _primary(t.sendOtp, _sendOtp),
    const SizedBox(height: AppSpacing.x3),
    Text(t.familyNoAccessHint, style: AppTypography.caption()),
  ];

  List<Widget> _codeStep(AppLocalizations t) => [
    Text(
      _notice ?? t.familyCodeSentIfAccess('+91 ${_phone.text.trim()}'),
      style: AppTypography.small(),
    ),
    const SizedBox(height: AppSpacing.x3),
    HmsTextField(
      label: t.sixDigitCode,
      controller: _code,
      required: true,
      autofocus: true,
      keyboardType: TextInputType.number,
      maxLength: 6,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      autofillHints: const [AutofillHints.oneTimeCode],
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _verify(),
    ),
    const SizedBox(height: AppSpacing.x5),
    _primary(t.verifyAndContinueShort, _verify),
    const SizedBox(height: AppSpacing.x3),
    Wrap(
      alignment: WrapAlignment.spaceBetween,
      children: [
        AuthLink(
          label: t.changeNumber,
          icon: LucideIcons.arrowLeft,
          onTap: _busy ? null : _restart,
        ),
        AuthLink(label: t.resendCode, onTap: _busy ? null : _sendOtp),
      ],
    ),
  ];

  List<Widget> _chooseStep(AppLocalizations t) => [
    Text(t.familyChoosePatient, style: AppTypography.small()),
    const SizedBox(height: AppSpacing.x3),
    for (final grant in _grants) ...[
      _GrantTile(grant: grant, onTap: _busy ? null : () => _choose(grant)),
      const SizedBox(height: AppSpacing.x2),
    ],
    const SizedBox(height: AppSpacing.x2),
    Align(
      alignment: Alignment.centerLeft,
      child: AuthLink(
        label: t.useDifferentNumber,
        icon: LucideIcons.arrowLeft,
        onTap: _busy ? null : _restart,
      ),
    ),
  ];
}

/// One patient the family member may open (name left, relationship right).
class _GrantTile extends StatelessWidget {
  const _GrantTile({required this.grant, required this.onTap});

  final ProxyGrantChoice grant;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Semantics(
      button: true,
      child: Material(
        color: AppColors.cardRaised,
        shape: const RoundedRectangleBorder(
          borderRadius: AppRadii.button,
          side: BorderSide(color: AppColors.onCardFill),
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: AppRadii.button,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.x4,
                vertical: AppSpacing.x3,
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      grant.patientName,
                      style: AppTypography.small(weight: FontWeight.w600),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.x2),
                  Text(
                    t.familyYouAre(grant.relationship),
                    style: AppTypography.caption(),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
