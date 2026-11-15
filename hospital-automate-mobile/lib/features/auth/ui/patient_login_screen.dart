import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/network/api_exception.dart';
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
import 'family_login_panel.dart';

enum _Method { mobile, tokenId, email, family }

/// PatientLogin.jsx: Mobile OTP, Token / ID, Email and Family tabs. The code
/// is checked by the server only; the app never decides a code is right.
/// When SMS cannot be sent, "Verify using Email" opens the email code step.
/// Under the form, "Continue with Google" (patients only, as on the web).
class PatientLoginScreen extends StatefulWidget {
  const PatientLoginScreen({super.key, required this.location});

  final String location;

  @override
  State<PatientLoginScreen> createState() => _PatientLoginScreenState();
}

class _PatientLoginScreenState extends State<PatientLoginScreen> {
  final _phone = TextEditingController();
  final _code = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _identifier = TextEditingController();

  _Method _method = _Method.mobile;
  bool _codeSent = false;
  bool _emailVerifying = false;
  bool _busy = false;
  bool _familyBusy = false;
  bool _smsFailed = false;
  String? _error;
  String? _notice;

  @override
  void dispose() {
    for (final c in [_phone, _code, _email, _password, _identifier]) {
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

  void _signedIn() {
    for (final c in [_code, _password]) {
      c.clear();
    }
    if (mounted) context.go(AppRoutes.home);
  }

  Future<void> _sendOtp() => _run(AuthStep.request, () async {
    final OtpDelivery delivery;
    try {
      delivery = await _auth.patientRequestOtp(_phone.text.trim());
    } on ApiException catch (error) {
      // As on the web: SMS could not be sent, so offer the email code.
      if (error.kind == ApiErrorKind.unavailable) _smsFailed = true;
      rethrow;
    }
    if (!mounted) return;
    setState(() {
      _codeSent = true;
      _smsFailed = false;
      if (delivery.printedOnServer) _notice = context.l10n.otpPrintedOnServer;
    });
  });

  Future<void> _verifyOtp() => _run(AuthStep.code, () async {
    await _auth.patientVerifyOtp(_phone.text.trim(), _code.text.trim());
    _signedIn();
  });

  Future<void> _emailLogin() => _run(AuthStep.credentials, () async {
    await _auth.patientEmailLogin(_email.text.trim(), _password.text);
    _signedIn();
  });

  Future<void> _sendEmailOtp() => _run(AuthStep.request, () async {
    final delivery = await _auth.requestEmailOtp(_email.text.trim());
    if (!mounted) return;
    setState(() {
      _emailVerifying = true;
      _notice = delivery.printedOnServer
          ? context.l10n.otpPrintedOnServer
          : context.l10n.emailCodeSent;
    });
  });

  Future<void> _verifyEmailOtp() => _run(AuthStep.code, () async {
    await _auth.verifyEmailOtp(_email.text.trim(), _code.text.trim());
    _code.clear();
    if (!mounted) return;
    setState(() {
      _emailVerifying = false;
      _notice = context.l10n.emailVerifiedSignIn;
    });
  });

  Future<void> _googleSignIn() => _run(AuthStep.credentials, () async {
    if (await _auth.googleSignIn()) _signedIn();
  });

  Future<void> _idLogin() => _run(AuthStep.credentials, () async {
    await _auth.patientIdLogin(_identifier.text.trim(), _password.text);
    _signedIn();
  });

  void _switchTo(_Method method) => setState(() {
    _method = method;
    _error = null;
    _notice = null;
    _codeSent = false;
    _smsFailed = false;
    _emailVerifying = false;
    _code.clear();
    _password.clear();
  });

  /// "Verify using Email": the email tab, straight at its code step.
  void _verifyByEmail() {
    _switchTo(_Method.email);
    setState(() => _emailVerifying = true);
  }

  Widget _emailFallback(AppLocalizations t) => HmsButton(
    label: t.verifyUsingEmail,
    variant: HmsButtonVariant.secondary,
    expand: true,
    onPressed: _busy ? null : _verifyByEmail,
  );

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final expired = AppScope.of(context).session.sessionExpired;
    return AuthPage(
      location: widget.location,
      eyebrow: t.patientPortal,
      title: t.signInTitle,
      subtitle: t.patientSignInIntro,
      footer: [
        Text(
          t.newToHms,
          textAlign: TextAlign.center,
          style: AppTypography.small(color: AppColors.ink500),
        ),
        Center(
          child: HmsButton(
            label: t.createAccount,
            variant: HmsButtonVariant.secondary,
            onPressed: () => context.go(AppRoutes.register),
          ),
        ),
        Center(
          child: HmsButton(
            label: t.staffSignIn,
            variant: HmsButtonVariant.ghost,
            onPressed: () => context.go(AppRoutes.staffLogin),
          ),
        ),
      ],
      children: [
        _MethodTabs(
          selected: _method,
          onSelect: _busy || _familyBusy ? null : _switchTo,
        ),
        const SizedBox(height: AppSpacing.x5),
        if (_error != null) AuthNotice(message: _error!),
        if (_error == null && _notice != null)
          AuthNotice(message: _notice!, tone: AuthNoticeTone.info),
        if (_error == null && _notice == null && expired)
          AuthNotice(message: t.sessionEndedNotice, tone: AuthNoticeTone.info),
        ...switch (_method) {
          _Method.mobile => _mobile(t),
          _Method.tokenId => _tokenId(t),
          _Method.email => _emailForm(t),
          _Method.family => [
            FamilyLoginPanel(
              onBusyChanged: (busy) => setState(() => _familyBusy = busy),
            ),
          ],
        },
        // Google signs in a patient, never a family member, so it is not
        // offered on the Family tab.
        if (_method != _Method.family && _auth.googleAvailable) ..._google(t),
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

  HmsTextField _codeField(AppLocalizations t, VoidCallback onSubmit) =>
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
        onSubmitted: (_) => onSubmit(),
      );

  List<Widget> _mobile(AppLocalizations t) {
    if (!_codeSent) {
      return [
        HmsTextField(
          label: t.mobileNumber,
          controller: _phone,
          required: true,
          placeholder: t.enter10DigitNumber,
          prefixText: '+91 ',
          keyboardType: TextInputType.phone,
          maxLength: 10,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          autofillHints: const [AutofillHints.telephoneNumberNational],
          hint: t.weWillSendCode,
          textInputAction: TextInputAction.done,
          onSubmitted: (_) => _sendOtp(),
        ),
        const SizedBox(height: AppSpacing.x5),
        _primary(t.sendOtp, _sendOtp),
        if (_smsFailed) ...[
          const SizedBox(height: AppSpacing.x3),
          _emailFallback(t),
        ],
      ];
    }
    return [
      Text(
        t.otpSentTo('+91 ${_phone.text.trim()}'),
        style: AppTypography.small(),
      ),
      const SizedBox(height: AppSpacing.x3),
      _codeField(t, _verifyOtp),
      const SizedBox(height: AppSpacing.x5),
      _primary(t.verifyAndContinueShort, _verifyOtp),
      const SizedBox(height: AppSpacing.x3),
      Wrap(
        alignment: WrapAlignment.spaceBetween,
        children: [
          AuthLink(
            label: t.changeNumber,
            icon: LucideIcons.arrowLeft,
            onTap: _busy ? null : () => _switchTo(_Method.mobile),
          ),
          AuthLink(label: t.resendCode, onTap: _busy ? null : _sendOtp),
        ],
      ),
      const SizedBox(height: AppSpacing.x3),
      _emailFallback(t),
    ];
  }

  List<Widget> _emailForm(AppLocalizations t) {
    final emailField = HmsTextField(
      label: t.email,
      controller: _email,
      required: true,
      keyboardType: TextInputType.emailAddress,
      autofillHints: const [AutofillHints.email],
    );
    if (_emailVerifying) {
      return [
        Text(t.emailOtpIntro, style: AppTypography.small()),
        const SizedBox(height: AppSpacing.x4),
        emailField,
        const SizedBox(height: AppSpacing.x3),
        HmsButton(
          label: t.sendEmailOtp,
          variant: HmsButtonVariant.secondary,
          expand: true,
          onPressed: _busy ? null : _sendEmailOtp,
        ),
        const SizedBox(height: AppSpacing.x4),
        _codeField(t, _verifyEmailOtp),
        const SizedBox(height: AppSpacing.x5),
        _primary(t.verifyOtp, _verifyEmailOtp),
        const SizedBox(height: AppSpacing.x3),
        Align(
          alignment: Alignment.centerLeft,
          child: AuthLink(
            label: t.backToEmailLogin,
            icon: LucideIcons.arrowLeft,
            onTap: _busy ? null : () => setState(() => _emailVerifying = false),
          ),
        ),
      ];
    }
    return [
      Text(t.emailLoginIntro, style: AppTypography.small()),
      const SizedBox(height: AppSpacing.x4),
      emailField,
      const SizedBox(height: AppSpacing.x4),
      HmsTextField(
        label: t.password,
        controller: _password,
        required: true,
        obscure: true,
        autofillHints: const [AutofillHints.password],
        textInputAction: TextInputAction.done,
        onSubmitted: (_) => _emailLogin(),
      ),
      const SizedBox(height: AppSpacing.x5),
      _primary(t.signInTitle, _emailLogin),
      const SizedBox(height: AppSpacing.x3),
      Align(
        alignment: Alignment.centerLeft,
        child: AuthLink(
          label: t.emailNotVerifiedSendOtp,
          icon: LucideIcons.mail,
          onTap: _busy ? null : _sendEmailOtp,
        ),
      ),
    ];
  }

  List<Widget> _google(AppLocalizations t) => [
    const SizedBox(height: AppSpacing.x6),
    Row(
      children: [
        const Expanded(child: Divider(color: AppColors.onCardFill)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.x3),
          child: Text(t.orDivider, style: AppTypography.caption()),
        ),
        const Expanded(child: Divider(color: AppColors.onCardFill)),
      ],
    ),
    const SizedBox(height: AppSpacing.x5),
    HmsButton(
      label: t.continueWithGoogle,
      icon: LucideIcons.circleUserRound,
      variant: HmsButtonVariant.secondary,
      size: HmsButtonSize.large,
      expand: true,
      onPressed: _busy ? null : _googleSignIn,
    ),
  ];

  List<Widget> _tokenId(AppLocalizations t) => [
    Text(t.tokenIdIntro, style: AppTypography.small()),
    const SizedBox(height: AppSpacing.x4),
    HmsTextField(
      label: t.tokenOrPatientId,
      controller: _identifier,
      required: true,
      hint: t.tokenIdHint,
    ),
    const SizedBox(height: AppSpacing.x4),
    HmsTextField(
      label: t.password,
      controller: _password,
      required: true,
      obscure: true,
      autofillHints: const [AutofillHints.password],
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _idLogin(),
    ),
    const SizedBox(height: AppSpacing.x5),
    _primary(t.lookupAndLogin, _idLogin),
  ];
}

/// The web's sign-in method switch (`rounded-lg bg-ink-100 p-0.5`).
class _MethodTabs extends StatelessWidget {
  const _MethodTabs({required this.selected, required this.onSelect});

  final _Method selected;
  final ValueChanged<_Method>? onSelect;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final tabs = [
      (_Method.mobile, LucideIcons.smartphone, t.tabMobileOtp),
      (_Method.tokenId, LucideIcons.ticket, t.tabTokenId),
      (_Method.email, LucideIcons.mail, t.tabEmail),
      (_Method.family, LucideIcons.users, t.tabFamily),
    ];
    return Semantics(
      label: t.signInMethod,
      container: true,
      child: Container(
        padding: const EdgeInsets.all(2),
        decoration: const BoxDecoration(
          color: AppColors.onCardFill,
          borderRadius: AppRadii.button,
        ),
        child: Row(
          children: [
            for (final (method, icon, label) in tabs)
              Expanded(
                child: Semantics(
                  selected: method == selected,
                  button: true,
                  label: label,
                  excludeSemantics: true,
                  child: Material(
                    color: method == selected
                        ? AppColors.cardRaised
                        : Colors.transparent,
                    borderRadius: const BorderRadius.all(
                      Radius.circular(AppRadii.md),
                    ),
                    child: InkWell(
                      onTap: onSelect == null ? null : () => onSelect!(method),
                      borderRadius: const BorderRadius.all(
                        Radius.circular(AppRadii.md),
                      ),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(minHeight: 40),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppSpacing.x1,
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(icon, size: 14, color: AppColors.onCard),
                              const SizedBox(width: AppSpacing.x1),
                              Flexible(
                                child: Text(
                                  label,
                                  overflow: TextOverflow.ellipsis,
                                  style: AppTypography.caption(
                                    weight: FontWeight.w600,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
