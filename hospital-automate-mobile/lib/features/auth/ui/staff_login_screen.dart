import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_text_field.dart';
import '../auth_errors.dart';
import '../auth_models.dart';
import '../auth_service.dart';
import 'auth_card.dart';

enum _Step { credentials, code, resetRequest, resetConfirm }

/// StaffLogin.jsx: username/email + password, then the SMS code when the
/// server uses OTP (password sign-in when it reports OTP unavailable), and
/// the SMS password reset. Secrets stay in the text fields only and are
/// cleared as soon as a step finishes.
class StaffLoginScreen extends StatefulWidget {
  const StaffLoginScreen({super.key, required this.location});

  final String location;

  @override
  State<StaffLoginScreen> createState() => _StaffLoginScreenState();
}

class _StaffLoginScreenState extends State<StaffLoginScreen> {
  final _username = TextEditingController();
  final _password = TextEditingController();
  final _code = TextEditingController();
  final _newPassword = TextEditingController();

  _Step _step = _Step.credentials;
  StaffOtpChallenge? _challenge;
  bool _busy = false;
  String? _error;
  String? _notice;

  @override
  void dispose() {
    for (final c in [_username, _password, _code, _newPassword]) {
      c.dispose();
    }
    super.dispose();
  }

  AuthService get _auth => AppScope.of(context).auth;

  Future<void> _run(AuthStep step, Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      await action();
    } catch (error) {
      if (mounted) {
        setState(() => _error = authErrorMessage(context.l10n, error, step));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _signIn() => _run(AuthStep.credentials, () async {
    final username = _username.text.trim();
    final password = _password.text;
    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = context.l10n.authFieldsRequired);
      return;
    }
    final result = await _auth.staffSignIn(username, password);
    _password.clear();
    if (!mounted) return;
    switch (result) {
      case StaffSignedIn():
        context.go(AppRoutes.home);
      case StaffOtpNeeded(:final challenge):
        setState(() {
          _challenge = challenge;
          _step = _Step.code;
        });
    }
  });

  Future<void> _verify() => _run(AuthStep.code, () async {
    final challenge = _challenge;
    if (challenge == null) return;
    await _auth.staffVerifyOtp(challenge, _code.text.trim());
    _code.clear();
    _challenge = null;
    if (mounted) context.go(AppRoutes.home);
  });

  Future<void> _resend() => _run(AuthStep.code, () async {
    final challenge = _challenge;
    if (challenge == null) return;
    await _auth.staffResendOtp(challenge);
    if (mounted) setState(() => _notice = context.l10n.codeResent);
  });

  Future<void> _requestReset() => _run(AuthStep.request, () async {
    await _auth.requestPasswordReset(_username.text.trim());
    if (!mounted) return;
    setState(() {
      _step = _Step.resetConfirm;
      _notice = context.l10n.resetCodeSent;
    });
  });

  Future<void> _confirmReset() => _run(AuthStep.newPassword, () async {
    await _auth.confirmPasswordReset(
      _username.text.trim(),
      _code.text.trim(),
      _newPassword.text,
    );
    _code.clear();
    _newPassword.clear();
    if (!mounted) return;
    setState(() {
      _step = _Step.credentials;
      _notice = context.l10n.passwordUpdated;
    });
  });

  void _goTo(_Step step) => setState(() {
    _step = step;
    _error = null;
    _notice = null;
    _code.clear();
    if (step == _Step.credentials) _challenge = null;
  });

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final expired = AppScope.of(context).session.sessionExpired;
    final (title, subtitle) = switch (_step) {
      _Step.credentials => (t.signInTitle, t.staffSignInIntro),
      _Step.code => (
        t.enterTheCode,
        t.codeSentToMobile(_challenge?.maskedPhone ?? '******'),
      ),
      _Step.resetRequest => (t.resetPasswordTitle, t.resetRequestIntro),
      _Step.resetConfirm => (t.resetPasswordTitle, t.resetConfirmIntro),
    };
    return AuthPage(
      location: widget.location,
      eyebrow: t.staffPortal,
      title: title,
      subtitle: subtitle,
      footer: [
        if (_step == _Step.credentials)
          Center(
            child: HmsButton(
              label: t.patientSignIn,
              variant: HmsButtonVariant.ghost,
              onPressed: () => context.go(AppRoutes.patientLogin),
            ),
          ),
      ],
      children: [
        if (_error != null) AuthNotice(message: _error!),
        if (_error == null && _notice != null)
          AuthNotice(message: _notice!, tone: AuthNoticeTone.info),
        if (_error == null &&
            _notice == null &&
            expired &&
            _step == _Step.credentials)
          AuthNotice(message: t.sessionEndedNotice, tone: AuthNoticeTone.info),
        ...switch (_step) {
          _Step.credentials => _credentials(t),
          _Step.code => _codeStep(t),
          _Step.resetRequest => _resetRequest(t),
          _Step.resetConfirm => _resetConfirm(t),
        },
      ],
    );
  }

  List<Widget> _credentials(AppLocalizations t) => [
    HmsTextField(
      label: t.usernameOrEmail,
      controller: _username,
      required: true,
      keyboardType: TextInputType.emailAddress,
      autofillHints: const [AutofillHints.username],
    ),
    const SizedBox(height: AppSpacing.x4),
    HmsTextField(
      label: t.password,
      controller: _password,
      required: true,
      obscure: true,
      textInputAction: TextInputAction.done,
      autofillHints: const [AutofillHints.password],
      onSubmitted: (_) => _signIn(),
    ),
    const SizedBox(height: AppSpacing.x5),
    HmsButton(
      label: t.continueAction,
      size: HmsButtonSize.large,
      surface: HmsSurface.card,
      expand: true,
      loading: _busy,
      onPressed: _signIn,
    ),
    const SizedBox(height: AppSpacing.x3),
    Align(
      alignment: Alignment.centerLeft,
      child: AuthLink(
        label: t.forgotPassword,
        icon: LucideIcons.keyRound,
        onTap: _busy ? null : () => _goTo(_Step.resetRequest),
      ),
    ),
  ];

  List<Widget> _codeStep(AppLocalizations t) => [
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
    HmsButton(
      label: t.verifyAndContinue,
      size: HmsButtonSize.large,
      surface: HmsSurface.card,
      expand: true,
      loading: _busy,
      onPressed: _verify,
    ),
    const SizedBox(height: AppSpacing.x3),
    Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        AuthLink(
          label: t.back,
          icon: LucideIcons.arrowLeft,
          onTap: _busy ? null : () => _goTo(_Step.credentials),
        ),
        AuthLink(label: t.resendCode, onTap: _busy ? null : _resend),
      ],
    ),
  ];

  List<Widget> _resetRequest(AppLocalizations t) => [
    HmsTextField(
      label: t.usernameOrEmail,
      controller: _username,
      required: true,
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _requestReset(),
    ),
    const SizedBox(height: AppSpacing.x5),
    HmsButton(
      label: t.sendResetCode,
      size: HmsButtonSize.large,
      surface: HmsSurface.card,
      expand: true,
      loading: _busy,
      onPressed: _requestReset,
    ),
    const SizedBox(height: AppSpacing.x3),
    Align(
      alignment: Alignment.centerLeft,
      child: AuthLink(
        label: t.backToSignIn,
        icon: LucideIcons.arrowLeft,
        onTap: _busy ? null : () => _goTo(_Step.credentials),
      ),
    ),
  ];

  List<Widget> _resetConfirm(AppLocalizations t) => [
    HmsTextField(
      label: t.codeFromSms,
      controller: _code,
      required: true,
      keyboardType: TextInputType.number,
      maxLength: 8,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      autofillHints: const [AutofillHints.oneTimeCode],
    ),
    const SizedBox(height: AppSpacing.x4),
    HmsTextField(
      label: t.newPassword,
      controller: _newPassword,
      required: true,
      obscure: true,
      hint: t.atLeast8Characters,
      autofillHints: const [AutofillHints.newPassword],
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _confirmReset(),
    ),
    const SizedBox(height: AppSpacing.x5),
    HmsButton(
      label: t.setNewPassword,
      size: HmsButtonSize.large,
      surface: HmsSurface.card,
      expand: true,
      loading: _busy,
      onPressed: _confirmReset,
    ),
    const SizedBox(height: AppSpacing.x3),
    Align(
      alignment: Alignment.centerLeft,
      child: AuthLink(
        label: t.backToSignIn,
        icon: LucideIcons.arrowLeft,
        onTap: _busy ? null : () => _goTo(_Step.credentials),
      ),
    ),
  ];
}
