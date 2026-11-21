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
import 'auth_card.dart';
import '../../patient/data/json_read.dart' show isoDay;
import '../../patient/ui/patient_ui.dart' show formatDay;

/// Register.jsx (patients only): the server creates the account and emails
/// a code; the email is verified here, then the patient signs in. Staff
/// join by hospital invitation, so there is no staff option.
class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key, required this.location});

  final String location;

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  final _code = TextEditingController();

  String _gender = 'Other';
  // BUG-04: the date of birth is asked for, never guessed. BUG-01: the
  // hospital chosen here gets the account's UHID at once.
  DateTime? _dob;
  int? _hospitalId;
  Future<List<PublicHospital>>? _hospitals;
  RegistrationResult? _registered;
  bool _busy = false;
  String? _error;
  String? _notice;

  @override
  void dispose() {
    for (final c in [_name, _email, _phone, _password, _confirm, _code]) {
      c.dispose();
    }
    super.dispose();
  }

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

  Future<void> _register() => _run(AuthStep.registration, () async {
    final t = context.l10n;
    // Checked here for a quick answer; the server checks every rule again.
    if (_name.text.trim().isEmpty) {
      setState(() => _error = t.authNameRequired);
      return;
    }
    if (_password.text.length < 8) {
      setState(() => _error = t.authPasswordTooShort);
      return;
    }
    if (_password.text != _confirm.text) {
      setState(() => _error = t.authPasswordMismatch);
      return;
    }
    final dob = _dob;
    if (dob == null) {
      setState(() => _error = t.authDobRequired);
      return;
    }
    if (_hospitalId == null) {
      setState(() => _error = t.authHospitalRequired);
      return;
    }
    final result = await AppScope.of(context).auth.registerPatient(
      PatientRegistration(
        fullName: _name.text.trim(),
        email: _email.text.trim().toLowerCase(),
        phone: _phone.text.trim(),
        password: _password.text,
        confirmPassword: _confirm.text,
        gender: _gender,
        dateOfBirth: isoDay(dob),
        hospitalId: _hospitalId,
      ),
    );
    _password.clear();
    _confirm.clear();
    if (!mounted) return;
    setState(() {
      _registered = result;
      if (result.delivery.printedOnServer) {
        _notice = context.l10n.otpPrintedOnServer;
      }
    });
  });

  Future<void> _verify() => _run(AuthStep.code, () async {
    final email = _registered!.email;
    await AppScope.of(context).auth.verifyEmailOtp(email, _code.text.trim());
    _code.clear();
    if (mounted) context.go(AppRoutes.patientLogin);
  });

  Future<void> _resend() => _run(AuthStep.request, () async {
    final delivery = await AppScope.of(context).auth
        .requestEmailOtp(_registered!.email);
    if (!mounted) return;
    setState(
      () => _notice = delivery.printedOnServer
          ? context.l10n.otpPrintedOnServer
          : context.l10n.codeResent,
    );
  });

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final registered = _registered;
    return AuthPage(
      location: widget.location,
      eyebrow: t.patientPortal,
      title: registered == null ? t.registerTitle : t.verifyYourEmail,
      subtitle: registered == null
          ? t.registerIntro
          : t.verifyEmailIntro(registered.email),
      footer: [
        Center(
          child: HmsButton(
            label: t.haveAccountSignIn,
            variant: HmsButtonVariant.ghost,
            onPressed: () => context.go(AppRoutes.patientLogin),
          ),
        ),
      ],
      children: [
        if (_error != null) AuthNotice(message: _error!),
        if (_error == null && _notice != null)
          AuthNotice(message: _notice!, tone: AuthNoticeTone.info),
        ...registered == null ? _form(t) : _verifyStep(t),
      ],
    );
  }

  Future<void> _pickDob() async {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final picked = await showDatePicker(
      context: context,
      initialDate: _dob ?? DateTime(today.year - 30, today.month, today.day),
      firstDate: DateTime(today.year - 120),
      lastDate: today,
      initialEntryMode: DatePickerEntryMode.input,
      helpText: context.l10n.dateOfBirth,
    );
    if (picked != null && mounted) setState(() => _dob = picked);
  }

  Widget _hospitalChoice(AppLocalizations t) {
    final hospitals = _hospitals ??= AppScope.of(context).auth
        .patientHospitals();
    return FutureBuilder<List<PublicHospital>>(
      future: hospitals,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return Row(
            children: [
              Expanded(
                child: Text(
                  t.hospitalsUnavailable,
                  style: AppTypography.small(),
                ),
              ),
              HmsButton(
                label: t.retry,
                variant: HmsButtonVariant.ghost,
                onPressed: () => setState(() => _hospitals = null),
              ),
            ],
          );
        }
        final rows = snapshot.data;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${t.registerAtHospital} *',
              style: AppTypography.small(weight: FontWeight.w500),
            ),
            const SizedBox(height: AppSpacing.x1_5),
            DropdownButtonFormField<int>(
              key: const Key('register-hospital'),
              initialValue: _hospitalId,
              isExpanded: true,

              hint: Text(rows == null ? t.loading : t.selectHospital),
              items: [
                for (final h in rows ?? const <PublicHospital>[])
                  DropdownMenuItem(
                    value: h.id,
                    child: Text(h.label, overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: _busy
                  ? null
                  : (id) => setState(() => _hospitalId = id),
            ),
          ],
        );
      },
    );
  }

  List<Widget> _form(AppLocalizations t) => [
    HmsTextField(
      label: t.fullName,
      controller: _name,
      required: true,
      autofillHints: const [AutofillHints.name],
    ),
    const SizedBox(height: AppSpacing.x4),
    HmsTextField(
      label: t.email,
      controller: _email,
      required: true,
      keyboardType: TextInputType.emailAddress,
      autofillHints: const [AutofillHints.email],
    ),
    const SizedBox(height: AppSpacing.x4),
    HmsTextField(
      label: t.mobileNumber,
      controller: _phone,
      required: true,
      prefixText: '+91 ',
      keyboardType: TextInputType.phone,
      maxLength: 10,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      autofillHints: const [AutofillHints.telephoneNumberNational],
    ),
    const SizedBox(height: AppSpacing.x4),
    _GenderChoice(
      value: _gender,
      onChanged: (value) => setState(() => _gender = value),
    ),
    const SizedBox(height: AppSpacing.x4),
    Text(
      '${t.dateOfBirth} *',
      style: AppTypography.small(weight: FontWeight.w500),
    ),
    const SizedBox(height: AppSpacing.x1_5),
    HmsButton(
      key: const Key('register-dob'),
      label: _dob == null ? t.chooseDateOfBirth : formatDay(t, _dob),
      icon: LucideIcons.calendarDays,
      variant: HmsButtonVariant.secondary,
      surface: HmsSurface.card,
      onPressed: _busy ? null : _pickDob,
    ),
    const SizedBox(height: AppSpacing.x4),
    _hospitalChoice(t),
    const SizedBox(height: AppSpacing.x4),
    HmsTextField(
      label: t.password,
      controller: _password,
      required: true,
      obscure: true,
      hint: t.atLeast8Characters,
      autofillHints: const [AutofillHints.newPassword],
    ),
    const SizedBox(height: AppSpacing.x4),
    HmsTextField(
      label: t.confirmPassword,
      controller: _confirm,
      required: true,
      obscure: true,
      autofillHints: const [AutofillHints.newPassword],
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _register(),
    ),
    const SizedBox(height: AppSpacing.x5),
    HmsButton(
      label: t.createAccount,
      size: HmsButtonSize.large,
      surface: HmsSurface.card,
      expand: true,
      loading: _busy,
      onPressed: _register,
    ),
  ];

  List<Widget> _verifyStep(AppLocalizations t) => [
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
      label: t.verifyOtp,
      size: HmsButtonSize.large,
      surface: HmsSurface.card,
      expand: true,
      loading: _busy,
      onPressed: _verify,
    ),
    const SizedBox(height: AppSpacing.x3),
    Align(
      alignment: Alignment.centerLeft,
      child: AuthLink(
        label: t.resendCode,
        icon: LucideIcons.mail,
        onTap: _busy ? null : _resend,
      ),
    ),
  ];
}

class _GenderChoice extends StatelessWidget {
  const _GenderChoice({required this.value, required this.onChanged});

  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final options = [
      ('Male', t.genderMale),
      ('Female', t.genderFemale),
      ('Other', t.genderOther),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(t.gender, style: AppTypography.small(weight: FontWeight.w500)),
        const SizedBox(height: AppSpacing.x1_5),
        Wrap(
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            for (final (key, label) in options)
              Semantics(
                inMutuallyExclusiveGroup: true,
                checked: key == value,
                button: true,
                label: label,
                excludeSemantics: true,
                child: Material(
                  color: key == value
                      ? AppColors.cardButton
                      : AppColors.cardRaised,
                  shape: const RoundedRectangleBorder(
                    borderRadius: AppRadii.button,
                    side: BorderSide(color: AppColors.onCardLineStrong),
                  ),
                  child: InkWell(
                    onTap: () => onChanged(key),
                    borderRadius: AppRadii.button,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.x4,
                        vertical: AppSpacing.x2_5,
                      ),
                      child: Text(
                        label,
                        style: AppTypography.small(weight: FontWeight.w500),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ],
    );
  }
}
