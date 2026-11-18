import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_hi.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('hi'),
  ];

  /// No description provided for @accountFamily.
  ///
  /// In en, this message translates to:
  /// **'Family member (view only)'**
  String get accountFamily;

  /// No description provided for @accountPatient.
  ///
  /// In en, this message translates to:
  /// **'Patient'**
  String get accountPatient;

  /// No description provided for @actingAs.
  ///
  /// In en, this message translates to:
  /// **'Acting as {role}'**
  String actingAs(String role);

  /// No description provided for @actionAiScribe.
  ///
  /// In en, this message translates to:
  /// **'AI scribe'**
  String get actionAiScribe;

  /// No description provided for @actionBloodStock.
  ///
  /// In en, this message translates to:
  /// **'Blood stock and requests'**
  String get actionBloodStock;

  /// No description provided for @actionCompounding.
  ///
  /// In en, this message translates to:
  /// **'Compounding'**
  String get actionCompounding;

  /// No description provided for @actionCreateInvoice.
  ///
  /// In en, this message translates to:
  /// **'Create invoice'**
  String get actionCreateInvoice;

  /// No description provided for @actionDispenseMedicines.
  ///
  /// In en, this message translates to:
  /// **'Dispense medicines'**
  String get actionDispenseMedicines;

  /// No description provided for @actionFindPatient.
  ///
  /// In en, this message translates to:
  /// **'Find a patient'**
  String get actionFindPatient;

  /// No description provided for @actionLabResults.
  ///
  /// In en, this message translates to:
  /// **'Lab results'**
  String get actionLabResults;

  /// No description provided for @actionLabWorklist.
  ///
  /// In en, this message translates to:
  /// **'Lab worklist'**
  String get actionLabWorklist;

  /// No description provided for @actionMedicineStock.
  ///
  /// In en, this message translates to:
  /// **'Medicine stock'**
  String get actionMedicineStock;

  /// No description provided for @actionNewAppointment.
  ///
  /// In en, this message translates to:
  /// **'New appointment'**
  String get actionNewAppointment;

  /// No description provided for @actionOpenQueue.
  ///
  /// In en, this message translates to:
  /// **'Open queue'**
  String get actionOpenQueue;

  /// No description provided for @actionPrescriptions.
  ///
  /// In en, this message translates to:
  /// **'Prescriptions'**
  String get actionPrescriptions;

  /// No description provided for @actionRegisterPatient.
  ///
  /// In en, this message translates to:
  /// **'Register patient'**
  String get actionRegisterPatient;

  /// No description provided for @actionStartConsultation.
  ///
  /// In en, this message translates to:
  /// **'Start consultation'**
  String get actionStartConsultation;

  /// No description provided for @actionVitalsNursing.
  ///
  /// In en, this message translates to:
  /// **'Vitals and nursing'**
  String get actionVitalsNursing;

  /// No description provided for @actionWardBeds.
  ///
  /// In en, this message translates to:
  /// **'Ward and beds'**
  String get actionWardBeds;

  /// No description provided for @addDiagnosis.
  ///
  /// In en, this message translates to:
  /// **'Add diagnosis'**
  String get addDiagnosis;

  /// No description provided for @addMedicine.
  ///
  /// In en, this message translates to:
  /// **'Add medicine'**
  String get addMedicine;

  /// No description provided for @addOneMedicine.
  ///
  /// In en, this message translates to:
  /// **'Add at least one medicine.'**
  String get addOneMedicine;

  /// No description provided for @admissionAndVisits.
  ///
  /// In en, this message translates to:
  /// **'Admission and visits'**
  String get admissionAndVisits;

  /// No description provided for @admissionReason.
  ///
  /// In en, this message translates to:
  /// **'Reason for admission'**
  String get admissionReason;

  /// No description provided for @admittedOn.
  ///
  /// In en, this message translates to:
  /// **'Admitted on'**
  String get admittedOn;

  /// No description provided for @admittingDoctor.
  ///
  /// In en, this message translates to:
  /// **'Admitting doctor'**
  String get admittingDoctor;

  /// No description provided for @ageLabel.
  ///
  /// In en, this message translates to:
  /// **'Age'**
  String get ageLabel;

  /// No description provided for @ageYears.
  ///
  /// In en, this message translates to:
  /// **'{age} y'**
  String ageYears(String age);

  /// No description provided for @alreadyDispensed.
  ///
  /// In en, this message translates to:
  /// **'This prescription has already been dispensed.'**
  String get alreadyDispensed;

  /// No description provided for @amountPaid.
  ///
  /// In en, this message translates to:
  /// **'Paid'**
  String get amountPaid;

  /// No description provided for @anotherDoctorsVisit.
  ///
  /// In en, this message translates to:
  /// **'This is another doctor\'s visit. You can read it but not add to it.'**
  String get anotherDoctorsVisit;

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'HMS'**
  String get appName;

  /// No description provided for @appSettingsIntro.
  ///
  /// In en, this message translates to:
  /// **'Settings for this device.'**
  String get appSettingsIntro;

  /// No description provided for @appSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Hospital Management'**
  String get appSubtitle;

  /// No description provided for @appointmentChangesAtHospital.
  ///
  /// In en, this message translates to:
  /// **'To cancel or change an appointment, please contact the hospital reception.'**
  String get appointmentChangesAtHospital;

  /// No description provided for @appointmentDetails.
  ///
  /// In en, this message translates to:
  /// **'Appointment details'**
  String get appointmentDetails;

  /// No description provided for @appointmentId.
  ///
  /// In en, this message translates to:
  /// **'Appointment ID'**
  String get appointmentId;

  /// No description provided for @appointmentStatus.
  ///
  /// In en, this message translates to:
  /// **'Appointment status'**
  String get appointmentStatus;

  /// No description provided for @appointmentsIntro.
  ///
  /// In en, this message translates to:
  /// **'Your bookings at the selected hospital.'**
  String get appointmentsIntro;

  /// No description provided for @assignedForShift.
  ///
  /// In en, this message translates to:
  /// **'Assigned to you · {shift}'**
  String assignedForShift(String shift);

  /// No description provided for @assignedToMe.
  ///
  /// In en, this message translates to:
  /// **'Assigned to me'**
  String get assignedToMe;

  /// No description provided for @atLeast8Characters.
  ///
  /// In en, this message translates to:
  /// **'At least 8 characters.'**
  String get atLeast8Characters;

  /// No description provided for @atMost.
  ///
  /// In en, this message translates to:
  /// **'At most {count}'**
  String atMost(int count);

  /// No description provided for @attentionBilling.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 invoice awaiting payment} other{{count} invoices awaiting payment}}'**
  String attentionBilling(int count);

  /// No description provided for @attentionEmergency.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 active emergency case} other{{count} active emergency cases}}'**
  String attentionEmergency(int count);

  /// No description provided for @attentionLabPending.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 lab test pending} other{{count} lab tests pending}}'**
  String attentionLabPending(int count);

  /// No description provided for @attentionQueue.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 patient waiting in the queue} other{{count} patients waiting in the queue}}'**
  String attentionQueue(int count);

  /// No description provided for @attentionUrgentLab.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 urgent lab test} other{{count} urgent lab tests}}'**
  String attentionUrgentLab(int count);

  /// No description provided for @authAccountDisabled.
  ///
  /// In en, this message translates to:
  /// **'This account is disabled. Contact your hospital administrator.'**
  String get authAccountDisabled;

  /// No description provided for @authChallengeExpired.
  ///
  /// In en, this message translates to:
  /// **'Your sign-in step expired. Enter your password again.'**
  String get authChallengeExpired;

  /// No description provided for @authEmailExists.
  ///
  /// In en, this message translates to:
  /// **'An account already exists with this email. Sign in instead.'**
  String get authEmailExists;

  /// No description provided for @authEmailNotVerified.
  ///
  /// In en, this message translates to:
  /// **'Your email is not verified yet. Send an email OTP to verify it.'**
  String get authEmailNotVerified;

  /// No description provided for @authEmailSendFailed.
  ///
  /// In en, this message translates to:
  /// **'The verification email could not be sent. Try again later.'**
  String get authEmailSendFailed;

  /// No description provided for @authFamilyNotAvailable.
  ///
  /// In en, this message translates to:
  /// **'This family access is not available for your mobile number.'**
  String get authFamilyNotAvailable;

  /// No description provided for @authFamilyTicketExpired.
  ///
  /// In en, this message translates to:
  /// **'Your sign-in has expired. Request a new code.'**
  String get authFamilyTicketExpired;

  /// No description provided for @authFieldsRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your username or email and password.'**
  String get authFieldsRequired;

  /// No description provided for @authGoogleFailed.
  ///
  /// In en, this message translates to:
  /// **'Google sign-in failed. Try again, or use another sign-in method.'**
  String get authGoogleFailed;

  /// No description provided for @authGoogleNotSetUp.
  ///
  /// In en, this message translates to:
  /// **'Google sign-in is not set up for this app yet. Use another sign-in method.'**
  String get authGoogleNotSetUp;

  /// No description provided for @authInvalidCredentials.
  ///
  /// In en, this message translates to:
  /// **'The username, email or password is not correct.'**
  String get authInvalidCredentials;

  /// No description provided for @authInvalidDob.
  ///
  /// In en, this message translates to:
  /// **'The date of birth is not valid.'**
  String get authInvalidDob;

  /// No description provided for @authInvalidEmail.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid email address.'**
  String get authInvalidEmail;

  /// No description provided for @authInvalidOtp.
  ///
  /// In en, this message translates to:
  /// **'The code is not correct.'**
  String get authInvalidOtp;

  /// No description provided for @authInvalidPhone.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid 10-digit mobile number.'**
  String get authInvalidPhone;

  /// No description provided for @authLockedOut.
  ///
  /// In en, this message translates to:
  /// **'Too many failed sign-in attempts. Try again in 15 minutes or reset your password.'**
  String get authLockedOut;

  /// No description provided for @authNameRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your full name.'**
  String get authNameRequired;

  /// No description provided for @authNotAllowed.
  ///
  /// In en, this message translates to:
  /// **'This sign-in is not allowed for this account.'**
  String get authNotAllowed;

  /// No description provided for @authNotStaff.
  ///
  /// In en, this message translates to:
  /// **'This account is not an active staff account. Patients sign in on the patient portal.'**
  String get authNotStaff;

  /// No description provided for @authOtpCooldown.
  ///
  /// In en, this message translates to:
  /// **'Please wait a minute before asking for another code.'**
  String get authOtpCooldown;

  /// No description provided for @authOtpExpired.
  ///
  /// In en, this message translates to:
  /// **'The code has expired. Ask for a new one.'**
  String get authOtpExpired;

  /// No description provided for @authOtpLocked.
  ///
  /// In en, this message translates to:
  /// **'Too many wrong codes. Sign in again in 15 minutes.'**
  String get authOtpLocked;

  /// No description provided for @authOtpRequiredUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This server requires an SMS code, but SMS is not set up. Contact your hospital administrator.'**
  String get authOtpRequiredUnavailable;

  /// No description provided for @authPasswordMismatch.
  ///
  /// In en, this message translates to:
  /// **'Password and confirm password do not match.'**
  String get authPasswordMismatch;

  /// No description provided for @authPasswordRejected.
  ///
  /// In en, this message translates to:
  /// **'This password was not accepted. Choose a longer, less common password.'**
  String get authPasswordRejected;

  /// No description provided for @authPasswordTooShort.
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 8 characters.'**
  String get authPasswordTooShort;

  /// No description provided for @authPhoneExists.
  ///
  /// In en, this message translates to:
  /// **'An account already exists with this mobile number. Sign in instead.'**
  String get authPhoneExists;

  /// No description provided for @authResetCodeInvalid.
  ///
  /// In en, this message translates to:
  /// **'The code is not correct or has expired.'**
  String get authResetCodeInvalid;

  /// No description provided for @authResetUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Password reset by SMS is not set up on this server. Contact your hospital administrator.'**
  String get authResetUnavailable;

  /// No description provided for @authSmsUnavailable.
  ///
  /// In en, this message translates to:
  /// **'SMS codes are not set up on this server. Use another sign-in method or contact the hospital.'**
  String get authSmsUnavailable;

  /// No description provided for @authStaffInviteOnly.
  ///
  /// In en, this message translates to:
  /// **'Staff accounts are created by your hospital. Ask its administrator for an invitation.'**
  String get authStaffInviteOnly;

  /// No description provided for @authStaffUseStaffLogin.
  ///
  /// In en, this message translates to:
  /// **'Staff accounts sign in on the staff portal.'**
  String get authStaffUseStaffLogin;

  /// No description provided for @authTooManyRequests.
  ///
  /// In en, this message translates to:
  /// **'Too many attempts. Please try again later.'**
  String get authTooManyRequests;

  /// No description provided for @authUnsupportedAccount.
  ///
  /// In en, this message translates to:
  /// **'This account cannot use the mobile app. Use the web app.'**
  String get authUnsupportedAccount;

  /// No description provided for @authorNotRecorded.
  ///
  /// In en, this message translates to:
  /// **'Author not recorded'**
  String get authorNotRecorded;

  /// No description provided for @availabilityDone.
  ///
  /// In en, this message translates to:
  /// **'Fully issued'**
  String get availabilityDone;

  /// No description provided for @availabilityInStock.
  ///
  /// In en, this message translates to:
  /// **'In stock'**
  String get availabilityInStock;

  /// No description provided for @availabilityNone.
  ///
  /// In en, this message translates to:
  /// **'Not in stock'**
  String get availabilityNone;

  /// No description provided for @availabilityShort.
  ///
  /// In en, this message translates to:
  /// **'Not enough stock'**
  String get availabilityShort;

  /// No description provided for @availabilitySplit.
  ///
  /// In en, this message translates to:
  /// **'Needs several batches'**
  String get availabilitySplit;

  /// No description provided for @awaitingBed.
  ///
  /// In en, this message translates to:
  /// **'Awaiting bed'**
  String get awaitingBed;

  /// No description provided for @awaitingVerification.
  ///
  /// In en, this message translates to:
  /// **'Awaiting verification'**
  String get awaitingVerification;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get back;

  /// No description provided for @backToEmailLogin.
  ///
  /// In en, this message translates to:
  /// **'Back to email login'**
  String get backToEmailLogin;

  /// No description provided for @backToHome.
  ///
  /// In en, this message translates to:
  /// **'Back to home'**
  String get backToHome;

  /// No description provided for @backToSignIn.
  ///
  /// In en, this message translates to:
  /// **'Back to sign in'**
  String get backToSignIn;

  /// No description provided for @backend.
  ///
  /// In en, this message translates to:
  /// **'Backend'**
  String get backend;

  /// No description provided for @balanceDue.
  ///
  /// In en, this message translates to:
  /// **'Balance due'**
  String get balanceDue;

  /// No description provided for @batch.
  ///
  /// In en, this message translates to:
  /// **'Batch'**
  String get batch;

  /// No description provided for @batchCode.
  ///
  /// In en, this message translates to:
  /// **'Batch {batch}'**
  String batchCode(String batch);

  /// No description provided for @bedAvailable.
  ///
  /// In en, this message translates to:
  /// **'Available'**
  String get bedAvailable;

  /// No description provided for @bedCleaning.
  ///
  /// In en, this message translates to:
  /// **'Cleaning'**
  String get bedCleaning;

  /// No description provided for @bedMaintenance.
  ///
  /// In en, this message translates to:
  /// **'Maintenance'**
  String get bedMaintenance;

  /// No description provided for @bedNumber.
  ///
  /// In en, this message translates to:
  /// **'Bed {bed}'**
  String bedNumber(String bed);

  /// No description provided for @bedOccupied.
  ///
  /// In en, this message translates to:
  /// **'Occupied'**
  String get bedOccupied;

  /// No description provided for @bedReserved.
  ///
  /// In en, this message translates to:
  /// **'Reserved'**
  String get bedReserved;

  /// No description provided for @bedsOccupiedOf.
  ///
  /// In en, this message translates to:
  /// **'{occupied} occupied of {total}'**
  String bedsOccupiedOf(String occupied, String total);

  /// No description provided for @billDate.
  ///
  /// In en, this message translates to:
  /// **'Bill date'**
  String get billDate;

  /// No description provided for @billTotal.
  ///
  /// In en, this message translates to:
  /// **'Total'**
  String get billTotal;

  /// No description provided for @billingAmount.
  ///
  /// In en, this message translates to:
  /// **'Amount'**
  String get billingAmount;

  /// No description provided for @billingAmountInvalid.
  ///
  /// In en, this message translates to:
  /// **'Enter an amount in rupees, like 500 or 499.50.'**
  String get billingAmountInvalid;

  /// No description provided for @billingAmountRefused.
  ///
  /// In en, this message translates to:
  /// **'The hospital system did not accept this amount. Check the balance and try again.'**
  String get billingAmountRefused;

  /// No description provided for @billingAmountTooHigh.
  ///
  /// In en, this message translates to:
  /// **'The amount is more than the balance due ({limit}).'**
  String billingAmountTooHigh(String limit);

  /// No description provided for @billingAnyDate.
  ///
  /// In en, this message translates to:
  /// **'Any date'**
  String get billingAnyDate;

  /// No description provided for @billingBackToDesk.
  ///
  /// In en, this message translates to:
  /// **'Back to billing'**
  String get billingBackToDesk;

  /// No description provided for @billingBackToInvoice.
  ///
  /// In en, this message translates to:
  /// **'Back to invoice'**
  String get billingBackToInvoice;

  /// No description provided for @billingChargeConsultation.
  ///
  /// In en, this message translates to:
  /// **'Consultation'**
  String get billingChargeConsultation;

  /// No description provided for @billingChargeLaboratory.
  ///
  /// In en, this message translates to:
  /// **'Laboratory'**
  String get billingChargeLaboratory;

  /// No description provided for @billingChargeOther.
  ///
  /// In en, this message translates to:
  /// **'Other charge'**
  String get billingChargeOther;

  /// No description provided for @billingChargePharmacy.
  ///
  /// In en, this message translates to:
  /// **'Pharmacy'**
  String get billingChargePharmacy;

  /// No description provided for @billingChoosePatient.
  ///
  /// In en, this message translates to:
  /// **'Choose the patient by searching their name, phone or UHID.'**
  String get billingChoosePatient;

  /// No description provided for @billingClearDates.
  ///
  /// In en, this message translates to:
  /// **'Clear dates'**
  String get billingClearDates;

  /// No description provided for @billingConfirmPayment.
  ///
  /// In en, this message translates to:
  /// **'Record {amount} received by {method} for invoice {invoice} ({patient})? This records money already received at the desk; it does not charge anyone.'**
  String billingConfirmPayment(
    String amount,
    String method,
    String invoice,
    String patient,
  );

  /// No description provided for @billingConfirmPaymentTitle.
  ///
  /// In en, this message translates to:
  /// **'Record this payment?'**
  String get billingConfirmPaymentTitle;

  /// No description provided for @billingConfirmRefund.
  ///
  /// In en, this message translates to:
  /// **'Record a refund of {amount} by {method} on invoice {invoice}? A refund cannot be edited or deleted later.'**
  String billingConfirmRefund(String amount, String method, String invoice);

  /// No description provided for @billingConfirmRefundTitle.
  ///
  /// In en, this message translates to:
  /// **'Record this refund?'**
  String get billingConfirmRefundTitle;

  /// No description provided for @billingCountsUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Billing figures could not be loaded'**
  String get billingCountsUnavailable;

  /// No description provided for @billingCreateInvoice.
  ///
  /// In en, this message translates to:
  /// **'Create invoice'**
  String get billingCreateInvoice;

  /// No description provided for @billingCreateNotAllowed.
  ///
  /// In en, this message translates to:
  /// **'Your role at this hospital cannot create invoices.'**
  String get billingCreateNotAllowed;

  /// No description provided for @billingDeskIntro.
  ///
  /// In en, this message translates to:
  /// **'Invoices and payments of the selected hospital. Totals and balances come from the hospital system.'**
  String get billingDeskIntro;

  /// No description provided for @billingDiscount.
  ///
  /// In en, this message translates to:
  /// **'Discount'**
  String get billingDiscount;

  /// No description provided for @billingDiscountHint.
  ///
  /// In en, this message translates to:
  /// **'Taken off before GST, as the hospital system calculates it.'**
  String get billingDiscountHint;

  /// No description provided for @billingDiscountRefused.
  ///
  /// In en, this message translates to:
  /// **'The discount cannot be negative or more than the bill before tax.'**
  String get billingDiscountRefused;

  /// No description provided for @billingDue.
  ///
  /// In en, this message translates to:
  /// **'Due {amount}'**
  String billingDue(String amount);

  /// No description provided for @billingFromPharmacy.
  ///
  /// In en, this message translates to:
  /// **'from pharmacy'**
  String get billingFromPharmacy;

  /// No description provided for @billingGstPercent.
  ///
  /// In en, this message translates to:
  /// **'GST %'**
  String get billingGstPercent;

  /// No description provided for @billingGstRate.
  ///
  /// In en, this message translates to:
  /// **'GST {rate}%'**
  String billingGstRate(String rate);

  /// No description provided for @billingInvoiceClosed.
  ///
  /// In en, this message translates to:
  /// **'This invoice is cancelled or closed, so no money can be recorded on it.'**
  String get billingInvoiceClosed;

  /// No description provided for @billingInvoiceMaybeCreated.
  ///
  /// In en, this message translates to:
  /// **'No answer came from the hospital system, so the invoice may have been created. Check the invoice list before creating it again.'**
  String get billingInvoiceMaybeCreated;

  /// No description provided for @billingInvoiceTitle.
  ///
  /// In en, this message translates to:
  /// **'Invoice'**
  String get billingInvoiceTitle;

  /// No description provided for @billingInvoices.
  ///
  /// In en, this message translates to:
  /// **'Invoices'**
  String get billingInvoices;

  /// No description provided for @billingItems.
  ///
  /// In en, this message translates to:
  /// **'Items'**
  String get billingItems;

  /// No description provided for @billingKeyReused.
  ///
  /// In en, this message translates to:
  /// **'This request was already used for another record. Go back to the invoice and start again.'**
  String get billingKeyReused;

  /// No description provided for @billingLatestRecords.
  ///
  /// In en, this message translates to:
  /// **'Latest {count} records'**
  String billingLatestRecords(int count);

  /// No description provided for @billingLineDescription.
  ///
  /// In en, this message translates to:
  /// **'Description'**
  String get billingLineDescription;

  /// No description provided for @billingLineDescriptionRequired.
  ///
  /// In en, this message translates to:
  /// **'Describe the charge.'**
  String get billingLineDescriptionRequired;

  /// No description provided for @billingLineNumber.
  ///
  /// In en, this message translates to:
  /// **'Item {number}'**
  String billingLineNumber(int number);

  /// No description provided for @billingNetOfRefunds.
  ///
  /// In en, this message translates to:
  /// **'After refunds'**
  String get billingNetOfRefunds;

  /// No description provided for @billingNewInvoice.
  ///
  /// In en, this message translates to:
  /// **'New invoice'**
  String get billingNewInvoice;

  /// No description provided for @billingNewInvoiceIntro.
  ///
  /// In en, this message translates to:
  /// **'Choose the patient and add the charges. The hospital system works out tax, the total and the invoice number.'**
  String get billingNewInvoiceIntro;

  /// No description provided for @billingNoGateway.
  ///
  /// In en, this message translates to:
  /// **'Payments are recorded at the desk'**
  String get billingNoGateway;

  /// No description provided for @billingNoGatewayBody.
  ///
  /// In en, this message translates to:
  /// **'There is no online payment gateway. Record cash, UPI, card or bank transfer only after the money has been received. Nothing here is pending or failed: every record is a confirmed receipt.'**
  String get billingNoGatewayBody;

  /// No description provided for @billingNoInvoicesMatch.
  ///
  /// In en, this message translates to:
  /// **'No invoices match these filters'**
  String get billingNoInvoicesMatch;

  /// No description provided for @billingNoItems.
  ///
  /// In en, this message translates to:
  /// **'This invoice has no items.'**
  String get billingNoItems;

  /// No description provided for @billingOpenInvoiceList.
  ///
  /// In en, this message translates to:
  /// **'Open invoice list'**
  String get billingOpenInvoiceList;

  /// No description provided for @billingPatientSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search patient by name, phone or UHID'**
  String get billingPatientSearchHint;

  /// No description provided for @billingPaymentIntro.
  ///
  /// In en, this message translates to:
  /// **'Money received at the desk against this invoice.'**
  String get billingPaymentIntro;

  /// No description provided for @billingPaymentKind.
  ///
  /// In en, this message translates to:
  /// **'Payment'**
  String get billingPaymentKind;

  /// No description provided for @billingPaymentMethod.
  ///
  /// In en, this message translates to:
  /// **'Payment method'**
  String get billingPaymentMethod;

  /// No description provided for @billingPaymentNotAllowed.
  ///
  /// In en, this message translates to:
  /// **'A payment cannot be recorded on this invoice by your role.'**
  String get billingPaymentNotAllowed;

  /// No description provided for @billingPaymentRecorded.
  ///
  /// In en, this message translates to:
  /// **'Payment recorded by the hospital system'**
  String get billingPaymentRecorded;

  /// No description provided for @billingPayments.
  ///
  /// In en, this message translates to:
  /// **'Payments'**
  String get billingPayments;

  /// No description provided for @billingPaymentsRecorded.
  ///
  /// In en, this message translates to:
  /// **'Payments recorded'**
  String get billingPaymentsRecorded;

  /// No description provided for @billingPharmacyAutomatic.
  ///
  /// In en, this message translates to:
  /// **'Medicines sold by the pharmacy are billed automatically, so they are not added here.'**
  String get billingPharmacyAutomatic;

  /// No description provided for @billingPrintOnWeb.
  ///
  /// In en, this message translates to:
  /// **'Printed bills and PDFs are made from the web app; the hospital system has no invoice PDF for the phone.'**
  String get billingPrintOnWeb;

  /// No description provided for @billingQuantityInvalid.
  ///
  /// In en, this message translates to:
  /// **'Quantity must be a whole number of at least 1.'**
  String get billingQuantityInvalid;

  /// No description provided for @billingReceipt.
  ///
  /// In en, this message translates to:
  /// **'Receipt number'**
  String get billingReceipt;

  /// No description provided for @billingRecordPayment.
  ///
  /// In en, this message translates to:
  /// **'Record payment'**
  String get billingRecordPayment;

  /// No description provided for @billingRecordRefund.
  ///
  /// In en, this message translates to:
  /// **'Record refund'**
  String get billingRecordRefund;

  /// No description provided for @billingReference.
  ///
  /// In en, this message translates to:
  /// **'Transaction reference'**
  String get billingReference;

  /// No description provided for @billingReferenceHint.
  ///
  /// In en, this message translates to:
  /// **'UPI transaction ID, card slip or transfer number. Never a card number, CVV or PIN.'**
  String get billingReferenceHint;

  /// No description provided for @billingRefundIntro.
  ///
  /// In en, this message translates to:
  /// **'Money paid back to the patient on this invoice.'**
  String get billingRefundIntro;

  /// No description provided for @billingRefundNotAllowed.
  ///
  /// In en, this message translates to:
  /// **'A refund cannot be recorded on this invoice by your role.'**
  String get billingRefundNotAllowed;

  /// No description provided for @billingRefundReason.
  ///
  /// In en, this message translates to:
  /// **'Reason for the refund'**
  String get billingRefundReason;

  /// No description provided for @billingRefundReasonRequired.
  ///
  /// In en, this message translates to:
  /// **'Give the reason for the refund.'**
  String get billingRefundReasonRequired;

  /// No description provided for @billingRefundRecorded.
  ///
  /// In en, this message translates to:
  /// **'Refund recorded by the hospital system'**
  String get billingRefundRecorded;

  /// No description provided for @billingRefundTooHigh.
  ///
  /// In en, this message translates to:
  /// **'A refund cannot be more than the amount received ({limit}).'**
  String billingRefundTooHigh(String limit);

  /// No description provided for @billingRefunds.
  ///
  /// In en, this message translates to:
  /// **'Refunds'**
  String get billingRefunds;

  /// No description provided for @billingRefused.
  ///
  /// In en, this message translates to:
  /// **'The hospital system did not accept this. Refresh and try again.'**
  String get billingRefused;

  /// No description provided for @billingRemoveLine.
  ///
  /// In en, this message translates to:
  /// **'Remove item'**
  String get billingRemoveLine;

  /// No description provided for @billingSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search invoice number, patient or UHID'**
  String get billingSearchHint;

  /// No description provided for @billingServerTotals.
  ///
  /// In en, this message translates to:
  /// **'Tax, the total and the invoice number are calculated by the hospital system when you create the invoice.'**
  String get billingServerTotals;

  /// No description provided for @billingSubtotal.
  ///
  /// In en, this message translates to:
  /// **'Subtotal'**
  String get billingSubtotal;

  /// No description provided for @billingTax.
  ///
  /// In en, this message translates to:
  /// **'Tax (GST)'**
  String get billingTax;

  /// No description provided for @billingTaxRateInvalid.
  ///
  /// In en, this message translates to:
  /// **'GST must be between 0 and 100 percent.'**
  String get billingTaxRateInvalid;

  /// No description provided for @billingTotalInvoices.
  ///
  /// In en, this message translates to:
  /// **'Invoices'**
  String get billingTotalInvoices;

  /// No description provided for @billingUnitPrice.
  ///
  /// In en, this message translates to:
  /// **'Unit price'**
  String get billingUnitPrice;

  /// No description provided for @billsIntro.
  ///
  /// In en, this message translates to:
  /// **'Invoices and the payments recorded against them.'**
  String get billsIntro;

  /// No description provided for @billsWithBalance.
  ///
  /// In en, this message translates to:
  /// **'Bills with balance due'**
  String get billsWithBalance;

  /// No description provided for @bmi.
  ///
  /// In en, this message translates to:
  /// **'BMI'**
  String get bmi;

  /// No description provided for @bmiByServer.
  ///
  /// In en, this message translates to:
  /// **'BMI is calculated by the hospital system from weight (kg) and height (cm): kg ÷ m².'**
  String get bmiByServer;

  /// No description provided for @bookAppointment.
  ///
  /// In en, this message translates to:
  /// **'Book appointment'**
  String get bookAppointment;

  /// No description provided for @bookAppointmentIntro.
  ///
  /// In en, this message translates to:
  /// **'Choose a doctor, a date and a free time.'**
  String get bookAppointmentIntro;

  /// No description provided for @bookingConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Appointment booked'**
  String get bookingConfirmed;

  /// No description provided for @bookingConfirmedBody.
  ///
  /// In en, this message translates to:
  /// **'The hospital has recorded your booking. Please arrive a little before your time.'**
  String get bookingConfirmedBody;

  /// No description provided for @bookingDateInvalid.
  ///
  /// In en, this message translates to:
  /// **'This date cannot be booked. Choose a date within the booking window.'**
  String get bookingDateInvalid;

  /// No description provided for @bookingDoctorUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This doctor is not taking online bookings. Choose another doctor.'**
  String get bookingDoctorUnavailable;

  /// No description provided for @bookingLimitReached.
  ///
  /// In en, this message translates to:
  /// **'You already have the most upcoming appointments allowed. Attend or cancel one at the hospital first.'**
  String get bookingLimitReached;

  /// No description provided for @bookingNoHospital.
  ///
  /// In en, this message translates to:
  /// **'You are not registered at any hospital yet. Please register at the reception first.'**
  String get bookingNoHospital;

  /// No description provided for @bookingRejected.
  ///
  /// In en, this message translates to:
  /// **'The hospital could not accept this booking. Check the details and try again.'**
  String get bookingRejected;

  /// No description provided for @bookingSlotTaken.
  ///
  /// In en, this message translates to:
  /// **'This time was just booked by someone else. Please choose another time.'**
  String get bookingSlotTaken;

  /// No description provided for @bookingSlotUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This time is no longer available. Please choose another time.'**
  String get bookingSlotUnavailable;

  /// No description provided for @bpNeedsBoth.
  ///
  /// In en, this message translates to:
  /// **'Enter both systolic and diastolic blood pressure, or neither.'**
  String get bpNeedsBoth;

  /// No description provided for @calledPatients.
  ///
  /// In en, this message translates to:
  /// **'Called'**
  String get calledPatients;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @careTasks.
  ///
  /// In en, this message translates to:
  /// **'Care tasks'**
  String get careTasks;

  /// No description provided for @category.
  ///
  /// In en, this message translates to:
  /// **'Category'**
  String get category;

  /// No description provided for @changeNumber.
  ///
  /// In en, this message translates to:
  /// **'Change number'**
  String get changeNumber;

  /// No description provided for @chargedOnBill.
  ///
  /// In en, this message translates to:
  /// **'Charged on bill {invoice} ({total}).'**
  String chargedOnBill(String invoice, String total);

  /// No description provided for @checkAgain.
  ///
  /// In en, this message translates to:
  /// **'Check again'**
  String get checkAgain;

  /// No description provided for @checkAndSavePrescription.
  ///
  /// In en, this message translates to:
  /// **'Check safety and save prescription'**
  String get checkAndSavePrescription;

  /// No description provided for @checkDispenseLines.
  ///
  /// In en, this message translates to:
  /// **'Check these lines before dispensing'**
  String get checkDispenseLines;

  /// No description provided for @checkPatientBeforeDose.
  ///
  /// In en, this message translates to:
  /// **'Check the patient\'s name and ID, the medicine, dose and route against the patient before you confirm.'**
  String get checkPatientBeforeDose;

  /// No description provided for @checkTheseFields.
  ///
  /// In en, this message translates to:
  /// **'Please check: {fields}'**
  String checkTheseFields(String fields);

  /// No description provided for @checking.
  ///
  /// In en, this message translates to:
  /// **'Checking…'**
  String get checking;

  /// No description provided for @checkingConnection.
  ///
  /// In en, this message translates to:
  /// **'Checking connection…'**
  String get checkingConnection;

  /// No description provided for @chooseDoctorFirst.
  ///
  /// In en, this message translates to:
  /// **'Choose a doctor to see free times.'**
  String get chooseDoctorFirst;

  /// No description provided for @clinicalHistory.
  ///
  /// In en, this message translates to:
  /// **'Clinical history'**
  String get clinicalHistory;

  /// No description provided for @clinicalNotes.
  ///
  /// In en, this message translates to:
  /// **'Clinical notes'**
  String get clinicalNotes;

  /// No description provided for @close.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get close;

  /// No description provided for @closeNavigation.
  ///
  /// In en, this message translates to:
  /// **'Close navigation'**
  String get closeNavigation;

  /// No description provided for @codeFromSms.
  ///
  /// In en, this message translates to:
  /// **'Code from SMS'**
  String get codeFromSms;

  /// No description provided for @codeResent.
  ///
  /// In en, this message translates to:
  /// **'A new code was sent.'**
  String get codeResent;

  /// No description provided for @codeSentToMobile.
  ///
  /// In en, this message translates to:
  /// **'We sent a 6-digit code to your mobile ({maskedPhone}).'**
  String codeSentToMobile(String maskedPhone);

  /// No description provided for @collapseSidebar.
  ///
  /// In en, this message translates to:
  /// **'Collapse sidebar'**
  String get collapseSidebar;

  /// No description provided for @comments.
  ///
  /// In en, this message translates to:
  /// **'Comments'**
  String get comments;

  /// No description provided for @completeConsultation.
  ///
  /// In en, this message translates to:
  /// **'Complete consultation'**
  String get completeConsultation;

  /// No description provided for @completeConsultationBody.
  ///
  /// In en, this message translates to:
  /// **'The visit will be marked Completed. Records already saved stay as they are.'**
  String get completeConsultationBody;

  /// No description provided for @completeConsultationTitle.
  ///
  /// In en, this message translates to:
  /// **'Complete this consultation?'**
  String get completeConsultationTitle;

  /// No description provided for @completeTask.
  ///
  /// In en, this message translates to:
  /// **'Complete'**
  String get completeTask;

  /// No description provided for @completeTaskTitle.
  ///
  /// In en, this message translates to:
  /// **'Mark this task complete?'**
  String get completeTaskTitle;

  /// No description provided for @completedToday.
  ///
  /// In en, this message translates to:
  /// **'Completed today'**
  String get completedToday;

  /// No description provided for @confirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get confirm;

  /// No description provided for @confirmBooking.
  ///
  /// In en, this message translates to:
  /// **'Confirm booking'**
  String get confirmBooking;

  /// No description provided for @confirmDispenseTitle.
  ///
  /// In en, this message translates to:
  /// **'Dispense these medicines?'**
  String get confirmDispenseTitle;

  /// No description provided for @confirmGiveTitle.
  ///
  /// In en, this message translates to:
  /// **'Record this dose as given?'**
  String get confirmGiveTitle;

  /// No description provided for @confirmHoldTitle.
  ///
  /// In en, this message translates to:
  /// **'Hold this dose?'**
  String get confirmHoldTitle;

  /// No description provided for @confirmMissedTitle.
  ///
  /// In en, this message translates to:
  /// **'Record this dose as missed?'**
  String get confirmMissedTitle;

  /// No description provided for @confirmPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm password'**
  String get confirmPassword;

  /// No description provided for @confirmRefuseTitle.
  ///
  /// In en, this message translates to:
  /// **'Record that the patient refused this dose?'**
  String get confirmRefuseTitle;

  /// No description provided for @consultationIntro.
  ///
  /// In en, this message translates to:
  /// **'Your visits. Open one to record vitals, notes, diagnoses, prescriptions and lab orders.'**
  String get consultationIntro;

  /// No description provided for @consultationQueueHint.
  ///
  /// In en, this message translates to:
  /// **'Queue tokens are moved on the Queue page.'**
  String get consultationQueueHint;

  /// No description provided for @continueAction.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueAction;

  /// No description provided for @continueSaving.
  ///
  /// In en, this message translates to:
  /// **'Continue and save'**
  String get continueSaving;

  /// No description provided for @continueWithGoogle.
  ///
  /// In en, this message translates to:
  /// **'Continue with Google'**
  String get continueWithGoogle;

  /// No description provided for @countPending.
  ///
  /// In en, this message translates to:
  /// **'{count} pending'**
  String countPending(String count);

  /// No description provided for @createAccount.
  ///
  /// In en, this message translates to:
  /// **'Create Account'**
  String get createAccount;

  /// No description provided for @currentPrescriptions.
  ///
  /// In en, this message translates to:
  /// **'Current prescriptions'**
  String get currentPrescriptions;

  /// No description provided for @dashboardLoadFailed.
  ///
  /// In en, this message translates to:
  /// **'Dashboard figures could not be loaded'**
  String get dashboardLoadFailed;

  /// No description provided for @date.
  ///
  /// In en, this message translates to:
  /// **'Date'**
  String get date;

  /// No description provided for @dateOfBirth.
  ///
  /// In en, this message translates to:
  /// **'Date of birth'**
  String get dateOfBirth;

  /// No description provided for @department.
  ///
  /// In en, this message translates to:
  /// **'Department'**
  String get department;

  /// No description provided for @departments.
  ///
  /// In en, this message translates to:
  /// **'Departments'**
  String get departments;

  /// No description provided for @departmentsIntro.
  ///
  /// In en, this message translates to:
  /// **'Work in each department opens after the right staff member signs in.'**
  String get departmentsIntro;

  /// No description provided for @deptAppointmentsText.
  ///
  /// In en, this message translates to:
  /// **'Bookings and the daily schedule.'**
  String get deptAppointmentsText;

  /// No description provided for @deptBillingText.
  ///
  /// In en, this message translates to:
  /// **'Invoices and payments.'**
  String get deptBillingText;

  /// No description provided for @deptBloodBank.
  ///
  /// In en, this message translates to:
  /// **'Blood bank'**
  String get deptBloodBank;

  /// No description provided for @deptBloodBankText.
  ///
  /// In en, this message translates to:
  /// **'Blood stock and requests.'**
  String get deptBloodBankText;

  /// No description provided for @deptConsultationText.
  ///
  /// In en, this message translates to:
  /// **'Doctors\' clinical work.'**
  String get deptConsultationText;

  /// No description provided for @deptDescription.
  ///
  /// In en, this message translates to:
  /// **'Description'**
  String get deptDescription;

  /// No description provided for @deptEmergencyText.
  ///
  /// In en, this message translates to:
  /// **'Triage and emergency care.'**
  String get deptEmergencyText;

  /// No description provided for @deptHead.
  ///
  /// In en, this message translates to:
  /// **'Head of department'**
  String get deptHead;

  /// No description provided for @deptIntro.
  ///
  /// In en, this message translates to:
  /// **'Departments of this hospital.'**
  String get deptIntro;

  /// No description provided for @deptInventoryText.
  ///
  /// In en, this message translates to:
  /// **'Store, suppliers and purchase orders.'**
  String get deptInventoryText;

  /// No description provided for @deptLaboratoryText.
  ///
  /// In en, this message translates to:
  /// **'Samples, results and reports.'**
  String get deptLaboratoryText;

  /// No description provided for @deptNone.
  ///
  /// In en, this message translates to:
  /// **'No departments set up yet.'**
  String get deptNone;

  /// No description provided for @deptNursing.
  ///
  /// In en, this message translates to:
  /// **'Nursing'**
  String get deptNursing;

  /// No description provided for @deptNursingText.
  ///
  /// In en, this message translates to:
  /// **'Vitals, nursing notes and medication rounds.'**
  String get deptNursingText;

  /// No description provided for @deptPatientsText.
  ///
  /// In en, this message translates to:
  /// **'Registration and patient records.'**
  String get deptPatientsText;

  /// No description provided for @deptPharmacyText.
  ///
  /// In en, this message translates to:
  /// **'Dispensing and medicine stock.'**
  String get deptPharmacyText;

  /// No description provided for @deptQueue.
  ///
  /// In en, this message translates to:
  /// **'OPD queue'**
  String get deptQueue;

  /// No description provided for @deptQueueText.
  ///
  /// In en, this message translates to:
  /// **'Tokens and consultation flow.'**
  String get deptQueueText;

  /// No description provided for @deptReportsText.
  ///
  /// In en, this message translates to:
  /// **'Hospital statistics.'**
  String get deptReportsText;

  /// No description provided for @deptWards.
  ///
  /// In en, this message translates to:
  /// **'Wards and beds'**
  String get deptWards;

  /// No description provided for @deptWardsText.
  ///
  /// In en, this message translates to:
  /// **'Admissions, beds and discharge.'**
  String get deptWardsText;

  /// No description provided for @diagnoses.
  ///
  /// In en, this message translates to:
  /// **'Diagnoses'**
  String get diagnoses;

  /// No description provided for @diagnosisName.
  ///
  /// In en, this message translates to:
  /// **'Diagnosis'**
  String get diagnosisName;

  /// No description provided for @diagnosisNameRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter the diagnosis.'**
  String get diagnosisNameRequired;

  /// No description provided for @diagnosisType.
  ///
  /// In en, this message translates to:
  /// **'Type'**
  String get diagnosisType;

  /// No description provided for @dispense.
  ///
  /// In en, this message translates to:
  /// **'Dispense'**
  String get dispense;

  /// No description provided for @dispenseNoBatch.
  ///
  /// In en, this message translates to:
  /// **'{medicine}: choose a stock batch'**
  String dispenseNoBatch(String medicine);

  /// No description provided for @dispenseNoReason.
  ///
  /// In en, this message translates to:
  /// **'{medicine}: give the reason for the substitute'**
  String dispenseNoReason(String medicine);

  /// No description provided for @dispenseNothingChosen.
  ///
  /// In en, this message translates to:
  /// **'Enter a quantity for at least one medicine.'**
  String get dispenseNothingChosen;

  /// No description provided for @dispenseOutcomeUnknown.
  ///
  /// In en, this message translates to:
  /// **'The hospital system could not be reached, so it is not known whether the medicines were issued. The prescription has been reloaded: check the dispensing history before trying again.'**
  String get dispenseOutcomeUnknown;

  /// No description provided for @dispenseRefused.
  ///
  /// In en, this message translates to:
  /// **'The hospital system refused this dispense (stock, quantity, expiry or substitute check). Nothing was issued; the stock has been reloaded.'**
  String get dispenseRefused;

  /// No description provided for @dispenseTooMany.
  ///
  /// In en, this message translates to:
  /// **'{medicine}: at most {count} can still be issued'**
  String dispenseTooMany(String medicine, int count);

  /// No description provided for @dispensedInFull.
  ///
  /// In en, this message translates to:
  /// **'Dispensed in full. Stock was updated by the hospital system.'**
  String get dispensedInFull;

  /// No description provided for @dispensedInPart.
  ///
  /// In en, this message translates to:
  /// **'Part of the prescription was dispensed; the rest can be given later.'**
  String get dispensedInPart;

  /// No description provided for @dispensingHistory.
  ///
  /// In en, this message translates to:
  /// **'Dispensing history'**
  String get dispensingHistory;

  /// No description provided for @doctor.
  ///
  /// In en, this message translates to:
  /// **'Doctor'**
  String get doctor;

  /// No description provided for @doctorAppointmentsIntro.
  ///
  /// In en, this message translates to:
  /// **'Bookings with you at the selected hospital.'**
  String get doctorAppointmentsIntro;

  /// No description provided for @doctorLabIntro.
  ///
  /// In en, this message translates to:
  /// **'Lab tests of patients in your care. Values appear once the laboratory releases them.'**
  String get doctorLabIntro;

  /// No description provided for @doctorPatientsIntro.
  ///
  /// In en, this message translates to:
  /// **'Find a patient in your care by name, mobile number or UHID.'**
  String get doctorPatientsIntro;

  /// No description provided for @doctorPrescriptionsIntro.
  ///
  /// In en, this message translates to:
  /// **'Prescriptions of patients in your care.'**
  String get doctorPrescriptionsIntro;

  /// No description provided for @doctorProfileMissing.
  ///
  /// In en, this message translates to:
  /// **'No doctor profile is linked to your account at this hospital. Ask the hospital Admin.'**
  String get doctorProfileMissing;

  /// No description provided for @doctorQueueIntro.
  ///
  /// In en, this message translates to:
  /// **'Today\'s patients for you. This page checks again every 30 seconds while it is open.'**
  String get doctorQueueIntro;

  /// No description provided for @documentsIntro.
  ///
  /// In en, this message translates to:
  /// **'Documents the hospital has shared with you.'**
  String get documentsIntro;

  /// No description provided for @documentsViewOnWeb.
  ///
  /// In en, this message translates to:
  /// **'Opening files in the app is not available yet. Use the patient portal on the web to open them.'**
  String get documentsViewOnWeb;

  /// No description provided for @dosage.
  ///
  /// In en, this message translates to:
  /// **'Dosage'**
  String get dosage;

  /// No description provided for @doseDue.
  ///
  /// In en, this message translates to:
  /// **'Due'**
  String get doseDue;

  /// No description provided for @doseDueAt.
  ///
  /// In en, this message translates to:
  /// **'Due {time}'**
  String doseDueAt(String time);

  /// No description provided for @doseExcluded.
  ///
  /// In en, this message translates to:
  /// **'Excluded by doctor'**
  String get doseExcluded;

  /// No description provided for @doseGiven.
  ///
  /// In en, this message translates to:
  /// **'Given'**
  String get doseGiven;

  /// No description provided for @doseHeld.
  ///
  /// In en, this message translates to:
  /// **'Held'**
  String get doseHeld;

  /// No description provided for @doseMissed.
  ///
  /// In en, this message translates to:
  /// **'Missed'**
  String get doseMissed;

  /// No description provided for @doseNotRecorded.
  ///
  /// In en, this message translates to:
  /// **'This dose was not recorded: it was already recorded (perhaps by another nurse) or the doctor\'s order is no longer in force. The list has been refreshed.'**
  String get doseNotRecorded;

  /// No description provided for @doseOutcomeUnknown.
  ///
  /// In en, this message translates to:
  /// **'The hospital system could not be reached, so it is not known whether the dose was recorded. The list has been refreshed: check it before trying again.'**
  String get doseOutcomeUnknown;

  /// No description provided for @doseOverdueAt.
  ///
  /// In en, this message translates to:
  /// **'Overdue since {time}'**
  String doseOverdueAt(String time);

  /// No description provided for @doseRecorded.
  ///
  /// In en, this message translates to:
  /// **'{medicine}: {status} at {time}, confirmed by the hospital system.'**
  String doseRecorded(String medicine, String status, String time);

  /// No description provided for @doseRefused.
  ///
  /// In en, this message translates to:
  /// **'Refused'**
  String get doseRefused;

  /// No description provided for @doseVomited.
  ///
  /// In en, this message translates to:
  /// **'Vomited'**
  String get doseVomited;

  /// No description provided for @dosesDue.
  ///
  /// In en, this message translates to:
  /// **'Doses due'**
  String get dosesDue;

  /// No description provided for @dosesOverdue.
  ///
  /// In en, this message translates to:
  /// **'Overdue'**
  String get dosesOverdue;

  /// No description provided for @draft.
  ///
  /// In en, this message translates to:
  /// **'Draft'**
  String get draft;

  /// No description provided for @drugSchedule.
  ///
  /// In en, this message translates to:
  /// **'Drug schedule'**
  String get drugSchedule;

  /// No description provided for @duration.
  ///
  /// In en, this message translates to:
  /// **'Duration'**
  String get duration;

  /// No description provided for @email.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @emailCodeNotSent.
  ///
  /// In en, this message translates to:
  /// **'The verification email could not be sent. Ask the hospital to check its email settings.'**
  String get emailCodeNotSent;

  /// No description provided for @emailCodeSent.
  ///
  /// In en, this message translates to:
  /// **'If this email has a patient account, a verification code was sent to it.'**
  String get emailCodeSent;

  /// No description provided for @emailLoginIntro.
  ///
  /// In en, this message translates to:
  /// **'Use the email and password from your patient account.'**
  String get emailLoginIntro;

  /// No description provided for @emailNotVerifiedSendOtp.
  ///
  /// In en, this message translates to:
  /// **'Email not verified? Send email OTP'**
  String get emailNotVerifiedSendOtp;

  /// No description provided for @emailOtpIntro.
  ///
  /// In en, this message translates to:
  /// **'We will send a verification code to your registered email.'**
  String get emailOtpIntro;

  /// No description provided for @emailVerifiedSignIn.
  ///
  /// In en, this message translates to:
  /// **'Email verified. You can now sign in with your email and password.'**
  String get emailVerifiedSignIn;

  /// No description provided for @emergencyContact.
  ///
  /// In en, this message translates to:
  /// **'Emergency contact'**
  String get emergencyContact;

  /// No description provided for @emergencyVisitsToday.
  ///
  /// In en, this message translates to:
  /// **'Emergency visits today'**
  String get emergencyVisitsToday;

  /// No description provided for @enter10DigitNumber.
  ///
  /// In en, this message translates to:
  /// **'Enter 10-digit number'**
  String get enter10DigitNumber;

  /// No description provided for @enterAtLeastOneVital.
  ///
  /// In en, this message translates to:
  /// **'Enter at least one reading.'**
  String get enterAtLeastOneVital;

  /// No description provided for @enterTheCode.
  ///
  /// In en, this message translates to:
  /// **'Enter the code'**
  String get enterTheCode;

  /// No description provided for @erActiveNow.
  ///
  /// In en, this message translates to:
  /// **'In the ER now'**
  String get erActiveNow;

  /// No description provided for @erAddNote.
  ///
  /// In en, this message translates to:
  /// **'Add note'**
  String get erAddNote;

  /// No description provided for @erAdmitHint.
  ///
  /// In en, this message translates to:
  /// **'The server allocates the bed and closes the ER visit as Admitted.'**
  String get erAdmitHint;

  /// No description provided for @erAdmitToIpd.
  ///
  /// In en, this message translates to:
  /// **'Admit to IPD'**
  String get erAdmitToIpd;

  /// No description provided for @erAdmitted.
  ///
  /// In en, this message translates to:
  /// **'Admission created by the hospital system.'**
  String get erAdmitted;

  /// No description provided for @erAlreadyAdmitted.
  ///
  /// In en, this message translates to:
  /// **'This patient already has an open admission:'**
  String get erAlreadyAdmitted;

  /// No description provided for @erArrival.
  ///
  /// In en, this message translates to:
  /// **'Arrival'**
  String get erArrival;

  /// No description provided for @erAttendingDoctor.
  ///
  /// In en, this message translates to:
  /// **'Attending doctor'**
  String get erAttendingDoctor;

  /// No description provided for @erBp.
  ///
  /// In en, this message translates to:
  /// **'BP'**
  String get erBp;

  /// No description provided for @erChiefComplaint.
  ///
  /// In en, this message translates to:
  /// **'Chief complaint'**
  String get erChiefComplaint;

  /// No description provided for @erChiefComplaintRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter the chief complaint.'**
  String get erChiefComplaintRequired;

  /// No description provided for @erCompleteTriage.
  ///
  /// In en, this message translates to:
  /// **'Complete triage'**
  String get erCompleteTriage;

  /// No description provided for @erConsultationStarted.
  ///
  /// In en, this message translates to:
  /// **'Consultation started'**
  String get erConsultationStarted;

  /// No description provided for @erDetails.
  ///
  /// In en, this message translates to:
  /// **'Visit details'**
  String get erDetails;

  /// No description provided for @erDischarge.
  ///
  /// In en, this message translates to:
  /// **'Discharge from ER'**
  String get erDischarge;

  /// No description provided for @erDischargeDiagnosis.
  ///
  /// In en, this message translates to:
  /// **'Discharge diagnosis'**
  String get erDischargeDiagnosis;

  /// No description provided for @erDischargeWarning.
  ///
  /// In en, this message translates to:
  /// **'The visit is closed after discharge and cannot be reopened here.'**
  String get erDischargeWarning;

  /// No description provided for @erDischarged.
  ///
  /// In en, this message translates to:
  /// **'Discharge saved by the hospital system.'**
  String get erDischarged;

  /// No description provided for @erFilterActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get erFilterActive;

  /// No description provided for @erFilterClosed.
  ///
  /// In en, this message translates to:
  /// **'Closed'**
  String get erFilterClosed;

  /// No description provided for @erFollowUp.
  ///
  /// In en, this message translates to:
  /// **'Follow-up instructions'**
  String get erFollowUp;

  /// No description provided for @erGcs.
  ///
  /// In en, this message translates to:
  /// **'Glasgow Coma Scale'**
  String get erGcs;

  /// No description provided for @erGiven.
  ///
  /// In en, this message translates to:
  /// **'Given'**
  String get erGiven;

  /// No description provided for @erIntro.
  ///
  /// In en, this message translates to:
  /// **'Patients in the emergency department, most urgent first.'**
  String get erIntro;

  /// No description provided for @erKeepDoctor.
  ///
  /// In en, this message translates to:
  /// **'Keep {name}'**
  String erKeepDoctor(String name);

  /// No description provided for @erLeftEr.
  ///
  /// In en, this message translates to:
  /// **'Left the ER'**
  String get erLeftEr;

  /// No description provided for @erMedicationsSection.
  ///
  /// In en, this message translates to:
  /// **'Medicines'**
  String get erMedicationsSection;

  /// No description provided for @erNextSteps.
  ///
  /// In en, this message translates to:
  /// **'Next steps'**
  String get erNextSteps;

  /// No description provided for @erNoActiveVisits.
  ///
  /// In en, this message translates to:
  /// **'No patients in the emergency department now.'**
  String get erNoActiveVisits;

  /// No description provided for @erNoDoctorYet.
  ///
  /// In en, this message translates to:
  /// **'No doctor assigned'**
  String get erNoDoctorYet;

  /// No description provided for @erNoMedications.
  ///
  /// In en, this message translates to:
  /// **'No medicines recorded.'**
  String get erNoMedications;

  /// No description provided for @erNoNotes.
  ///
  /// In en, this message translates to:
  /// **'No notes yet.'**
  String get erNoNotes;

  /// No description provided for @erNoOrders.
  ///
  /// In en, this message translates to:
  /// **'No orders.'**
  String get erNoOrders;

  /// No description provided for @erNoPatientMatch.
  ///
  /// In en, this message translates to:
  /// **'No patient found at this hospital.'**
  String get erNoPatientMatch;

  /// No description provided for @erNoVisits.
  ///
  /// In en, this message translates to:
  /// **'No emergency visits.'**
  String get erNoVisits;

  /// No description provided for @erNoVitals.
  ///
  /// In en, this message translates to:
  /// **'No vitals recorded.'**
  String get erNoVitals;

  /// No description provided for @erNotGiven.
  ///
  /// In en, this message translates to:
  /// **'Not given yet'**
  String get erNotGiven;

  /// No description provided for @erNotTriaged.
  ///
  /// In en, this message translates to:
  /// **'Not triaged yet.'**
  String get erNotTriaged;

  /// No description provided for @erNote.
  ///
  /// In en, this message translates to:
  /// **'Note'**
  String get erNote;

  /// No description provided for @erNoteHint.
  ///
  /// In en, this message translates to:
  /// **'Notes are kept permanently and cannot be edited.'**
  String get erNoteHint;

  /// No description provided for @erNoteRequired.
  ///
  /// In en, this message translates to:
  /// **'Write the note.'**
  String get erNoteRequired;

  /// No description provided for @erNoteSaved.
  ///
  /// In en, this message translates to:
  /// **'Note saved by the hospital system.'**
  String get erNoteSaved;

  /// No description provided for @erNotes.
  ///
  /// In en, this message translates to:
  /// **'Notes'**
  String get erNotes;

  /// No description provided for @erOpenAdmission.
  ///
  /// In en, this message translates to:
  /// **'Open the admission'**
  String get erOpenAdmission;

  /// No description provided for @erOrdersSection.
  ///
  /// In en, this message translates to:
  /// **'Orders'**
  String get erOrdersSection;

  /// No description provided for @erPainScore.
  ///
  /// In en, this message translates to:
  /// **'Pain score'**
  String get erPainScore;

  /// No description provided for @erReadOnly.
  ///
  /// In en, this message translates to:
  /// **'You can view emergency visits. Changes need a doctor or nurse role at this hospital.'**
  String get erReadOnly;

  /// No description provided for @erRecordVitals.
  ///
  /// In en, this message translates to:
  /// **'Record vitals'**
  String get erRecordVitals;

  /// No description provided for @erRefer.
  ///
  /// In en, this message translates to:
  /// **'Refer out'**
  String get erRefer;

  /// No description provided for @erReferWarning.
  ///
  /// In en, this message translates to:
  /// **'The visit is closed after referral and cannot be reopened here.'**
  String get erReferWarning;

  /// No description provided for @erReferred.
  ///
  /// In en, this message translates to:
  /// **'Referral saved by the hospital system.'**
  String get erReferred;

  /// No description provided for @erReferredTo.
  ///
  /// In en, this message translates to:
  /// **'Referred to (facility)'**
  String get erReferredTo;

  /// No description provided for @erReferredToRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter where the patient is referred.'**
  String get erReferredToRequired;

  /// No description provided for @erRegister.
  ///
  /// In en, this message translates to:
  /// **'Register'**
  String get erRegister;

  /// No description provided for @erRegisterHint.
  ///
  /// In en, this message translates to:
  /// **'Only patients already registered at this hospital can be chosen.'**
  String get erRegisterHint;

  /// No description provided for @erRegisterPatient.
  ///
  /// In en, this message translates to:
  /// **'Register ER patient'**
  String get erRegisterPatient;

  /// No description provided for @erRegistered.
  ///
  /// In en, this message translates to:
  /// **'Emergency visit registered by the hospital system.'**
  String get erRegistered;

  /// No description provided for @erRemarks.
  ///
  /// In en, this message translates to:
  /// **'Remarks'**
  String get erRemarks;

  /// No description provided for @erRr.
  ///
  /// In en, this message translates to:
  /// **'Resp.'**
  String get erRr;

  /// No description provided for @erSearchPatient.
  ///
  /// In en, this message translates to:
  /// **'Name, UHID or phone'**
  String get erSearchPatient;

  /// No description provided for @erStartConsultation.
  ///
  /// In en, this message translates to:
  /// **'Start consultation'**
  String get erStartConsultation;

  /// No description provided for @erStartTriage.
  ///
  /// In en, this message translates to:
  /// **'Start triage'**
  String get erStartTriage;

  /// No description provided for @erStartTriageConfirm.
  ///
  /// In en, this message translates to:
  /// **'Move this patient to triage?'**
  String get erStartTriageConfirm;

  /// No description provided for @erStatusAdmitted.
  ///
  /// In en, this message translates to:
  /// **'Admitted to IPD'**
  String get erStatusAdmitted;

  /// No description provided for @erStatusDischarged.
  ///
  /// In en, this message translates to:
  /// **'Discharged'**
  String get erStatusDischarged;

  /// No description provided for @erStatusExpired.
  ///
  /// In en, this message translates to:
  /// **'Expired'**
  String get erStatusExpired;

  /// No description provided for @erStatusInvestigations.
  ///
  /// In en, this message translates to:
  /// **'Investigations'**
  String get erStatusInvestigations;

  /// No description provided for @erStatusLeftAgainstAdvice.
  ///
  /// In en, this message translates to:
  /// **'Left against advice'**
  String get erStatusLeftAgainstAdvice;

  /// No description provided for @erStatusObservation.
  ///
  /// In en, this message translates to:
  /// **'Observation'**
  String get erStatusObservation;

  /// No description provided for @erStatusReferred.
  ///
  /// In en, this message translates to:
  /// **'Referred'**
  String get erStatusReferred;

  /// No description provided for @erStatusRegistered.
  ///
  /// In en, this message translates to:
  /// **'Registered'**
  String get erStatusRegistered;

  /// No description provided for @erStatusTreatment.
  ///
  /// In en, this message translates to:
  /// **'Treatment'**
  String get erStatusTreatment;

  /// No description provided for @erStatusTriage.
  ///
  /// In en, this message translates to:
  /// **'In triage'**
  String get erStatusTriage;

  /// No description provided for @erStatusUnderConsultation.
  ///
  /// In en, this message translates to:
  /// **'Under consultation'**
  String get erStatusUnderConsultation;

  /// No description provided for @erSugar.
  ///
  /// In en, this message translates to:
  /// **'Sugar'**
  String get erSugar;

  /// No description provided for @erTriageLevel.
  ///
  /// In en, this message translates to:
  /// **'Triage level'**
  String get erTriageLevel;

  /// No description provided for @erTriageNotes.
  ///
  /// In en, this message translates to:
  /// **'Triage notes'**
  String get erTriageNotes;

  /// No description provided for @erTriageSection.
  ///
  /// In en, this message translates to:
  /// **'Triage'**
  String get erTriageSection;

  /// No description provided for @erTriageStarted.
  ///
  /// In en, this message translates to:
  /// **'Triage started'**
  String get erTriageStarted;

  /// No description provided for @erTriagedBy.
  ///
  /// In en, this message translates to:
  /// **'Triaged by'**
  String get erTriagedBy;

  /// No description provided for @erVisitClosed.
  ///
  /// In en, this message translates to:
  /// **'This visit is closed; only notes can be added.'**
  String get erVisitClosed;

  /// No description provided for @erVitalsEmpty.
  ///
  /// In en, this message translates to:
  /// **'Enter at least one reading.'**
  String get erVitalsEmpty;

  /// No description provided for @erVitalsSection.
  ///
  /// In en, this message translates to:
  /// **'Vitals'**
  String get erVitalsSection;

  /// No description provided for @errorConflict.
  ///
  /// In en, this message translates to:
  /// **'This record changed or already exists. Refresh and try again.'**
  String get errorConflict;

  /// No description provided for @errorForbidden.
  ///
  /// In en, this message translates to:
  /// **'Your role does not have access to this in the selected hospital.'**
  String get errorForbidden;

  /// No description provided for @errorNetwork.
  ///
  /// In en, this message translates to:
  /// **'Cannot reach the server. Check the connection and try again.'**
  String get errorNetwork;

  /// No description provided for @errorNotFound.
  ///
  /// In en, this message translates to:
  /// **'This record was not found in the selected hospital.'**
  String get errorNotFound;

  /// No description provided for @errorRateLimited.
  ///
  /// In en, this message translates to:
  /// **'Too many attempts. Wait a few minutes and try again.'**
  String get errorRateLimited;

  /// No description provided for @errorServer.
  ///
  /// In en, this message translates to:
  /// **'The server had a problem. Try again shortly.'**
  String get errorServer;

  /// No description provided for @errorTimeout.
  ///
  /// In en, this message translates to:
  /// **'The server did not answer in time. Try again.'**
  String get errorTimeout;

  /// No description provided for @errorUnauthorized.
  ///
  /// In en, this message translates to:
  /// **'Your session has ended. Please sign in again.'**
  String get errorUnauthorized;

  /// No description provided for @errorUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This service is not set up on the server.'**
  String get errorUnavailable;

  /// No description provided for @errorUnknown.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Try again.'**
  String get errorUnknown;

  /// No description provided for @errorValidation.
  ///
  /// In en, this message translates to:
  /// **'Some details are not valid. Check the form and try again.'**
  String get errorValidation;

  /// No description provided for @estimatedWait.
  ///
  /// In en, this message translates to:
  /// **'Estimated wait'**
  String get estimatedWait;

  /// No description provided for @estimatedWaitShort.
  ///
  /// In en, this message translates to:
  /// **'about {minutes} min (estimate)'**
  String estimatedWaitShort(String minutes);

  /// No description provided for @estimatesAreApproximate.
  ///
  /// In en, this message translates to:
  /// **'Wait times are estimates, not appointment times. Please stay nearby so you don\'t miss your call.'**
  String get estimatesAreApproximate;

  /// No description provided for @expandSidebar.
  ///
  /// In en, this message translates to:
  /// **'Expand sidebar'**
  String get expandSidebar;

  /// No description provided for @expectedAround.
  ///
  /// In en, this message translates to:
  /// **'Expected around'**
  String get expectedAround;

  /// No description provided for @expiredInStock.
  ///
  /// In en, this message translates to:
  /// **'Expired'**
  String get expiredInStock;

  /// No description provided for @expiresOn.
  ///
  /// In en, this message translates to:
  /// **'Expires {date}'**
  String expiresOn(String date);

  /// No description provided for @expiringSoonCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 batch in stock expires within 30 days} other{{count} batches in stock expire within 30 days}}'**
  String expiringSoonCount(int count);

  /// No description provided for @expiryDate.
  ///
  /// In en, this message translates to:
  /// **'Expiry date'**
  String get expiryDate;

  /// No description provided for @familyChoosePatient.
  ///
  /// In en, this message translates to:
  /// **'Whose records do you want to view?'**
  String get familyChoosePatient;

  /// No description provided for @familyCodeSentIfAccess.
  ///
  /// In en, this message translates to:
  /// **'If {phone} has family access, a 6-digit code was sent to it.'**
  String familyCodeSentIfAccess(String phone);

  /// No description provided for @familyIntro.
  ///
  /// In en, this message translates to:
  /// **'View a relative\'s records with the access they gave you. Use your own mobile number. View only: you cannot change anything.'**
  String get familyIntro;

  /// No description provided for @familyNoAccessHint.
  ///
  /// In en, this message translates to:
  /// **'No access yet? Ask the patient to add you under Consent & Sharing → Family access in their portal.'**
  String get familyNoAccessHint;

  /// No description provided for @familyTitle.
  ///
  /// In en, this message translates to:
  /// **'Family member or caregiver'**
  String get familyTitle;

  /// No description provided for @familyYouAre.
  ///
  /// In en, this message translates to:
  /// **'You: {relationship}'**
  String familyYouAre(String relationship);

  /// No description provided for @fieldRequired.
  ///
  /// In en, this message translates to:
  /// **'Required'**
  String get fieldRequired;

  /// No description provided for @filterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get filterAll;

  /// No description provided for @filterCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get filterCancelled;

  /// No description provided for @filterPast.
  ///
  /// In en, this message translates to:
  /// **'Past'**
  String get filterPast;

  /// No description provided for @filterToday.
  ///
  /// In en, this message translates to:
  /// **'Today'**
  String get filterToday;

  /// No description provided for @filterUpcoming.
  ///
  /// In en, this message translates to:
  /// **'Upcoming'**
  String get filterUpcoming;

  /// No description provided for @fixHighlightedFields.
  ///
  /// In en, this message translates to:
  /// **'Fix the highlighted readings.'**
  String get fixHighlightedFields;

  /// No description provided for @forgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get forgotPassword;

  /// No description provided for @frequency.
  ///
  /// In en, this message translates to:
  /// **'Frequency'**
  String get frequency;

  /// No description provided for @fullName.
  ///
  /// In en, this message translates to:
  /// **'Full name'**
  String get fullName;

  /// No description provided for @gender.
  ///
  /// In en, this message translates to:
  /// **'Gender'**
  String get gender;

  /// No description provided for @genderFemale.
  ///
  /// In en, this message translates to:
  /// **'Female'**
  String get genderFemale;

  /// No description provided for @genderMale.
  ///
  /// In en, this message translates to:
  /// **'Male'**
  String get genderMale;

  /// No description provided for @genderOther.
  ///
  /// In en, this message translates to:
  /// **'Other'**
  String get genderOther;

  /// No description provided for @goBack.
  ///
  /// In en, this message translates to:
  /// **'Go back'**
  String get goBack;

  /// No description provided for @goodAfternoon.
  ///
  /// In en, this message translates to:
  /// **'Good afternoon'**
  String get goodAfternoon;

  /// No description provided for @goodEvening.
  ///
  /// In en, this message translates to:
  /// **'Good evening'**
  String get goodEvening;

  /// No description provided for @goodMorning.
  ///
  /// In en, this message translates to:
  /// **'Good morning'**
  String get goodMorning;

  /// No description provided for @greetingWithName.
  ///
  /// In en, this message translates to:
  /// **'{greeting}, {name}'**
  String greetingWithName(String greeting, String name);

  /// No description provided for @groupAdministration.
  ///
  /// In en, this message translates to:
  /// **'Administration'**
  String get groupAdministration;

  /// No description provided for @groupClinical.
  ///
  /// In en, this message translates to:
  /// **'Clinical care'**
  String get groupClinical;

  /// No description provided for @groupDiagnostics.
  ///
  /// In en, this message translates to:
  /// **'Diagnostics & pharmacy'**
  String get groupDiagnostics;

  /// No description provided for @groupFrontDesk.
  ///
  /// In en, this message translates to:
  /// **'Front desk'**
  String get groupFrontDesk;

  /// No description provided for @groupOperations.
  ///
  /// In en, this message translates to:
  /// **'Finance & operations'**
  String get groupOperations;

  /// No description provided for @groupOverview.
  ///
  /// In en, this message translates to:
  /// **'Overview'**
  String get groupOverview;

  /// No description provided for @groupPatientPortal.
  ///
  /// In en, this message translates to:
  /// **'My health'**
  String get groupPatientPortal;

  /// No description provided for @groupStaff.
  ///
  /// In en, this message translates to:
  /// **'Staff'**
  String get groupStaff;

  /// No description provided for @groupSystem.
  ///
  /// In en, this message translates to:
  /// **'System'**
  String get groupSystem;

  /// No description provided for @guestBody.
  ///
  /// In en, this message translates to:
  /// **'Book an appointment, then sign in to follow your visits, prescriptions, reports and bills.'**
  String get guestBody;

  /// No description provided for @guestEyebrow.
  ///
  /// In en, this message translates to:
  /// **'Hospital services'**
  String get guestEyebrow;

  /// No description provided for @guestTitle.
  ///
  /// In en, this message translates to:
  /// **'Your care, organised in one place'**
  String get guestTitle;

  /// No description provided for @haveAccountSignIn.
  ///
  /// In en, this message translates to:
  /// **'Already have an account? Sign in'**
  String get haveAccountSignIn;

  /// No description provided for @hospActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get hospActive;

  /// No description provided for @hospAddress.
  ///
  /// In en, this message translates to:
  /// **'Address'**
  String get hospAddress;

  /// No description provided for @hospCode.
  ///
  /// In en, this message translates to:
  /// **'Code'**
  String get hospCode;

  /// No description provided for @hospCurrent.
  ///
  /// In en, this message translates to:
  /// **'Current'**
  String get hospCurrent;

  /// No description provided for @hospDepartments.
  ///
  /// In en, this message translates to:
  /// **'Departments'**
  String get hospDepartments;

  /// No description provided for @hospDoctors.
  ///
  /// In en, this message translates to:
  /// **'Doctors'**
  String get hospDoctors;

  /// No description provided for @hospEmail.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get hospEmail;

  /// No description provided for @hospGrievanceOfficer.
  ///
  /// In en, this message translates to:
  /// **'Grievance officer'**
  String get hospGrievanceOfficer;

  /// No description provided for @hospInactive.
  ///
  /// In en, this message translates to:
  /// **'Inactive'**
  String get hospInactive;

  /// No description provided for @hospIntro.
  ///
  /// In en, this message translates to:
  /// **'The hospital you are working in now.'**
  String get hospIntro;

  /// No description provided for @hospNoWards.
  ///
  /// In en, this message translates to:
  /// **'No wards set up yet.'**
  String get hospNoWards;

  /// No description provided for @hospNurses.
  ///
  /// In en, this message translates to:
  /// **'Nurses'**
  String get hospNurses;

  /// No description provided for @hospPhone.
  ///
  /// In en, this message translates to:
  /// **'Phone'**
  String get hospPhone;

  /// No description provided for @hospSwitch.
  ///
  /// In en, this message translates to:
  /// **'Switch'**
  String get hospSwitch;

  /// No description provided for @hospType.
  ///
  /// In en, this message translates to:
  /// **'Type'**
  String get hospType;

  /// No description provided for @hospWards.
  ///
  /// In en, this message translates to:
  /// **'Wards'**
  String get hospWards;

  /// No description provided for @hospYourHospitals.
  ///
  /// In en, this message translates to:
  /// **'Your hospitals'**
  String get hospYourHospitals;

  /// No description provided for @hospital.
  ///
  /// In en, this message translates to:
  /// **'Hospital'**
  String get hospital;

  /// No description provided for @howBookingWorks.
  ///
  /// In en, this message translates to:
  /// **'How booking works'**
  String get howBookingWorks;

  /// No description provided for @howBookingWorksIntro.
  ///
  /// In en, this message translates to:
  /// **'You can see the steps before signing in.'**
  String get howBookingWorksIntro;

  /// No description provided for @icd10Search.
  ///
  /// In en, this message translates to:
  /// **'Search ICD-10 (optional)'**
  String get icd10Search;

  /// No description provided for @inStock.
  ///
  /// In en, this message translates to:
  /// **'In stock'**
  String get inStock;

  /// No description provided for @inStockCount.
  ///
  /// In en, this message translates to:
  /// **'{count} {unit} in stock'**
  String inStockCount(int count, String unit);

  /// No description provided for @inStockMedicines.
  ///
  /// In en, this message translates to:
  /// **'In stock'**
  String get inStockMedicines;

  /// No description provided for @instructions.
  ///
  /// In en, this message translates to:
  /// **'Instructions'**
  String get instructions;

  /// No description provided for @interfaceLanguage.
  ///
  /// In en, this message translates to:
  /// **'Interface language'**
  String get interfaceLanguage;

  /// No description provided for @invoicesPaidTotal.
  ///
  /// In en, this message translates to:
  /// **'Invoices paid / total'**
  String get invoicesPaidTotal;

  /// No description provided for @ipdAdmitted.
  ///
  /// In en, this message translates to:
  /// **'Admitted'**
  String get ipdAdmitted;

  /// No description provided for @ipdAdmittedOn.
  ///
  /// In en, this message translates to:
  /// **'Admitted on'**
  String get ipdAdmittedOn;

  /// No description provided for @ipdAdmittingDoctor.
  ///
  /// In en, this message translates to:
  /// **'Admitting doctor'**
  String get ipdAdmittingDoctor;

  /// No description provided for @ipdAllocateBed.
  ///
  /// In en, this message translates to:
  /// **'Allocate bed'**
  String get ipdAllocateBed;

  /// No description provided for @ipdAvailableBeds.
  ///
  /// In en, this message translates to:
  /// **'Free beds'**
  String get ipdAvailableBeds;

  /// No description provided for @ipdAwaitingBed.
  ///
  /// In en, this message translates to:
  /// **'Waiting for a bed'**
  String get ipdAwaitingBed;

  /// No description provided for @ipdBalanceDue.
  ///
  /// In en, this message translates to:
  /// **'Balance due'**
  String get ipdBalanceDue;

  /// No description provided for @ipdBedHistory.
  ///
  /// In en, this message translates to:
  /// **'Bed history'**
  String get ipdBedHistory;

  /// No description provided for @ipdBedSaved.
  ///
  /// In en, this message translates to:
  /// **'Bed saved by the hospital system.'**
  String get ipdBedSaved;

  /// No description provided for @ipdBedTaken.
  ///
  /// In en, this message translates to:
  /// **'That bed is no longer free. The list has been refreshed.'**
  String get ipdBedTaken;

  /// No description provided for @ipdBedsPartial.
  ///
  /// In en, this message translates to:
  /// **'Showing the first {count} beds; the counts may be incomplete.'**
  String ipdBedsPartial(int count);

  /// No description provided for @ipdBillDue.
  ///
  /// In en, this message translates to:
  /// **'The final bill still has money due.'**
  String get ipdBillDue;

  /// No description provided for @ipdBillTotal.
  ///
  /// In en, this message translates to:
  /// **'Total'**
  String get ipdBillTotal;

  /// No description provided for @ipdCheckCounselled.
  ///
  /// In en, this message translates to:
  /// **'Patient and family counselled'**
  String get ipdCheckCounselled;

  /// No description provided for @ipdCheckDocuments.
  ///
  /// In en, this message translates to:
  /// **'Documents handed over'**
  String get ipdCheckDocuments;

  /// No description provided for @ipdCheckFollowUp.
  ///
  /// In en, this message translates to:
  /// **'Follow-up arranged'**
  String get ipdCheckFollowUp;

  /// No description provided for @ipdCheckMedications.
  ///
  /// In en, this message translates to:
  /// **'Medications reconciled'**
  String get ipdCheckMedications;

  /// No description provided for @ipdChecklist.
  ///
  /// In en, this message translates to:
  /// **'Discharge checklist'**
  String get ipdChecklist;

  /// No description provided for @ipdChooseBed.
  ///
  /// In en, this message translates to:
  /// **'Choose a free bed:'**
  String get ipdChooseBed;

  /// No description provided for @ipdCompleteDischarge.
  ///
  /// In en, this message translates to:
  /// **'Complete discharge'**
  String get ipdCompleteDischarge;

  /// No description provided for @ipdConfirmComplete.
  ///
  /// In en, this message translates to:
  /// **'Complete the discharge? The bed is released and the stay is closed.'**
  String get ipdConfirmComplete;

  /// No description provided for @ipdConfirmInitiate.
  ///
  /// In en, this message translates to:
  /// **'Start the discharge? The checklist, summary and final bill must still be finished.'**
  String get ipdConfirmInitiate;

  /// No description provided for @ipdCurrentBed.
  ///
  /// In en, this message translates to:
  /// **'Bed'**
  String get ipdCurrentBed;

  /// No description provided for @ipdDaysBilled.
  ///
  /// In en, this message translates to:
  /// **'Days billed'**
  String get ipdDaysBilled;

  /// No description provided for @ipdDischarge.
  ///
  /// In en, this message translates to:
  /// **'Discharge'**
  String get ipdDischarge;

  /// No description provided for @ipdDischargeDone.
  ///
  /// In en, this message translates to:
  /// **'Discharge completed by the hospital system.'**
  String get ipdDischargeDone;

  /// No description provided for @ipdDischargeInitiated.
  ///
  /// In en, this message translates to:
  /// **'Discharge started'**
  String get ipdDischargeInitiated;

  /// No description provided for @ipdDischargeReady.
  ///
  /// In en, this message translates to:
  /// **'Ready: every discharge step is done.'**
  String get ipdDischargeReady;

  /// No description provided for @ipdDischargeStepsOnWeb.
  ///
  /// In en, this message translates to:
  /// **'The plan, checklist, summary and final bill are completed on the web app.'**
  String get ipdDischargeStepsOnWeb;

  /// No description provided for @ipdDischarged.
  ///
  /// In en, this message translates to:
  /// **'Discharged'**
  String get ipdDischarged;

  /// No description provided for @ipdDischargedOn.
  ///
  /// In en, this message translates to:
  /// **'Discharged on'**
  String get ipdDischargedOn;

  /// No description provided for @ipdFilterCurrent.
  ///
  /// In en, this message translates to:
  /// **'In hospital'**
  String get ipdFilterCurrent;

  /// No description provided for @ipdFinalBill.
  ///
  /// In en, this message translates to:
  /// **'Final bill'**
  String get ipdFinalBill;

  /// No description provided for @ipdInitiateDischarge.
  ///
  /// In en, this message translates to:
  /// **'Start discharge'**
  String get ipdInitiateDischarge;

  /// No description provided for @ipdIntro.
  ///
  /// In en, this message translates to:
  /// **'Admitted patients, their beds and discharges.'**
  String get ipdIntro;

  /// No description provided for @ipdNoAdmissions.
  ///
  /// In en, this message translates to:
  /// **'No admissions.'**
  String get ipdNoAdmissions;

  /// No description provided for @ipdNoBedHistory.
  ///
  /// In en, this message translates to:
  /// **'No bed allocated yet.'**
  String get ipdNoBedHistory;

  /// No description provided for @ipdNoBeds.
  ///
  /// In en, this message translates to:
  /// **'No beds set up at this hospital.'**
  String get ipdNoBeds;

  /// No description provided for @ipdNoFinalBill.
  ///
  /// In en, this message translates to:
  /// **'The final bill has not been created.'**
  String get ipdNoFinalBill;

  /// No description provided for @ipdNoFreeBeds.
  ///
  /// In en, this message translates to:
  /// **'No free beds at this hospital right now.'**
  String get ipdNoFreeBeds;

  /// No description provided for @ipdNoPlan.
  ///
  /// In en, this message translates to:
  /// **'No discharge plan written yet.'**
  String get ipdNoPlan;

  /// No description provided for @ipdNoSummary.
  ///
  /// In en, this message translates to:
  /// **'No discharge summary written yet.'**
  String get ipdNoSummary;

  /// No description provided for @ipdNotStarted.
  ///
  /// In en, this message translates to:
  /// **'Discharge has not been started.'**
  String get ipdNotStarted;

  /// No description provided for @ipdReadOnly.
  ///
  /// In en, this message translates to:
  /// **'You can view admissions. Bed and discharge changes need a doctor or nurse role at this hospital.'**
  String get ipdReadOnly;

  /// No description provided for @ipdReason.
  ///
  /// In en, this message translates to:
  /// **'Reason for admission'**
  String get ipdReason;

  /// No description provided for @ipdSince.
  ///
  /// In en, this message translates to:
  /// **'Since'**
  String get ipdSince;

  /// No description provided for @ipdStay.
  ///
  /// In en, this message translates to:
  /// **'Stay'**
  String get ipdStay;

  /// No description provided for @ipdStillToDo.
  ///
  /// In en, this message translates to:
  /// **'Still to do before discharge'**
  String get ipdStillToDo;

  /// No description provided for @ipdSummary.
  ///
  /// In en, this message translates to:
  /// **'Discharge summary'**
  String get ipdSummary;

  /// No description provided for @ipdSummaryDoctorsOnly.
  ///
  /// In en, this message translates to:
  /// **'Only doctors and hospital managers can read discharge summaries.'**
  String get ipdSummaryDoctorsOnly;

  /// No description provided for @ipdSummaryDraft.
  ///
  /// In en, this message translates to:
  /// **'Draft, not finalised'**
  String get ipdSummaryDraft;

  /// No description provided for @ipdSummaryFinalized.
  ///
  /// In en, this message translates to:
  /// **'Finalised by a doctor'**
  String get ipdSummaryFinalized;

  /// No description provided for @ipdSummaryNotFinalized.
  ///
  /// In en, this message translates to:
  /// **'A doctor must finalise the discharge summary.'**
  String get ipdSummaryNotFinalized;

  /// No description provided for @ipdTabAdmissions.
  ///
  /// In en, this message translates to:
  /// **'Admissions'**
  String get ipdTabAdmissions;

  /// No description provided for @ipdTabBeds.
  ///
  /// In en, this message translates to:
  /// **'Beds'**
  String get ipdTabBeds;

  /// No description provided for @ipdTransferBed.
  ///
  /// In en, this message translates to:
  /// **'Transfer bed'**
  String get ipdTransferBed;

  /// No description provided for @ipdTransferred.
  ///
  /// In en, this message translates to:
  /// **'Transferred'**
  String get ipdTransferred;

  /// No description provided for @jumpTo.
  ///
  /// In en, this message translates to:
  /// **'Jump to…'**
  String get jumpTo;

  /// No description provided for @jumpToPage.
  ///
  /// In en, this message translates to:
  /// **'Jump to a page'**
  String get jumpToPage;

  /// No description provided for @knownCondition.
  ///
  /// In en, this message translates to:
  /// **'Known condition'**
  String get knownCondition;

  /// No description provided for @labBackToWorklist.
  ///
  /// In en, this message translates to:
  /// **'Back to worklist'**
  String get labBackToWorklist;

  /// No description provided for @labCancelConfirm.
  ///
  /// In en, this message translates to:
  /// **'Cancel the order for {test}? It stays in the record as cancelled.'**
  String labCancelConfirm(String test);

  /// No description provided for @labCancelOrder.
  ///
  /// In en, this message translates to:
  /// **'Cancel order'**
  String get labCancelOrder;

  /// No description provided for @labChoosePatient.
  ///
  /// In en, this message translates to:
  /// **'Choose the patient first.'**
  String get labChoosePatient;

  /// No description provided for @labCollectedAt.
  ///
  /// In en, this message translates to:
  /// **'Collected at'**
  String get labCollectedAt;

  /// No description provided for @labCollectedBy.
  ///
  /// In en, this message translates to:
  /// **'Collected by'**
  String get labCollectedBy;

  /// No description provided for @labCollectionNotes.
  ///
  /// In en, this message translates to:
  /// **'Collection notes'**
  String get labCollectionNotes;

  /// No description provided for @labCommonTestsNote.
  ///
  /// In en, this message translates to:
  /// **'Common tests (names only; the hospital system has no test catalogue with prices):'**
  String get labCommonTestsNote;

  /// No description provided for @labContainerType.
  ///
  /// In en, this message translates to:
  /// **'Container'**
  String get labContainerType;

  /// No description provided for @labCountsUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Laboratory counts could not be loaded'**
  String get labCountsUnavailable;

  /// No description provided for @labDeskIntro.
  ///
  /// In en, this message translates to:
  /// **'Orders of the selected hospital, from sample collection to released result.'**
  String get labDeskIntro;

  /// No description provided for @labDispatchNotes.
  ///
  /// In en, this message translates to:
  /// **'Dispatch notes'**
  String get labDispatchNotes;

  /// No description provided for @labDispatchedBy.
  ///
  /// In en, this message translates to:
  /// **'Dispatched by'**
  String get labDispatchedBy;

  /// No description provided for @labEnteredAt.
  ///
  /// In en, this message translates to:
  /// **'Entered at'**
  String get labEnteredAt;

  /// No description provided for @labEnteredBy.
  ///
  /// In en, this message translates to:
  /// **'Entered by'**
  String get labEnteredBy;

  /// No description provided for @labExternalLab.
  ///
  /// In en, this message translates to:
  /// **'External laboratory'**
  String get labExternalLab;

  /// No description provided for @labExternalLabHint.
  ///
  /// In en, this message translates to:
  /// **'Leave empty when the sample goes to this hospital\'s laboratory.'**
  String get labExternalLabHint;

  /// No description provided for @labFindSample.
  ///
  /// In en, this message translates to:
  /// **'Find a sample'**
  String get labFindSample;

  /// No description provided for @labFindSampleHint.
  ///
  /// In en, this message translates to:
  /// **'Scan or type a sample number, then press enter'**
  String get labFindSampleHint;

  /// No description provided for @labIntro.
  ///
  /// In en, this message translates to:
  /// **'Results released by the laboratory.'**
  String get labIntro;

  /// No description provided for @labNewOrder.
  ///
  /// In en, this message translates to:
  /// **'New lab order'**
  String get labNewOrder;

  /// No description provided for @labNewOrderIntro.
  ///
  /// In en, this message translates to:
  /// **'A walk-in order from the laboratory desk. Doctors order from the consultation, linked to the visit.'**
  String get labNewOrderIntro;

  /// No description provided for @labNextStepByOthers.
  ///
  /// In en, this message translates to:
  /// **'Next step: {step}. Your role at this hospital cannot do it.'**
  String labNextStepByOthers(String step);

  /// No description provided for @labNoOrdersMatch.
  ///
  /// In en, this message translates to:
  /// **'No orders match these filters'**
  String get labNoOrdersMatch;

  /// No description provided for @labNoOrdersYet.
  ///
  /// In en, this message translates to:
  /// **'No laboratory orders yet'**
  String get labNoOrdersYet;

  /// No description provided for @labNoResultYet.
  ///
  /// In en, this message translates to:
  /// **'No result has been entered yet.'**
  String get labNoResultYet;

  /// No description provided for @labNotADiagnosis.
  ///
  /// In en, this message translates to:
  /// **'Values are shown as the laboratory entered them. Please discuss them with your doctor.'**
  String get labNotADiagnosis;

  /// No description provided for @labOpenWorklist.
  ///
  /// In en, this message translates to:
  /// **'Open worklist'**
  String get labOpenWorklist;

  /// No description provided for @labOrderCancelled.
  ///
  /// In en, this message translates to:
  /// **'Order cancelled by the hospital system.'**
  String get labOrderCancelled;

  /// No description provided for @labOrderMaybeCreated.
  ///
  /// In en, this message translates to:
  /// **'No answer came from the hospital system, so the order may have been placed. Check the worklist before ordering again.'**
  String get labOrderMaybeCreated;

  /// No description provided for @labOrderNotAllowed.
  ///
  /// In en, this message translates to:
  /// **'Your role at this hospital cannot place laboratory orders.'**
  String get labOrderNotAllowed;

  /// No description provided for @labOrderTitle.
  ///
  /// In en, this message translates to:
  /// **'Laboratory order'**
  String get labOrderTitle;

  /// No description provided for @labOrders.
  ///
  /// In en, this message translates to:
  /// **'Lab orders'**
  String get labOrders;

  /// No description provided for @labPatientSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Type at least 3 letters of the name, phone or UHID'**
  String get labPatientSearchHint;

  /// No description provided for @labPlaceOrder.
  ///
  /// In en, this message translates to:
  /// **'Place order'**
  String get labPlaceOrder;

  /// No description provided for @labPriorityNormal.
  ///
  /// In en, this message translates to:
  /// **'Normal'**
  String get labPriorityNormal;

  /// No description provided for @labProgressLabel.
  ///
  /// In en, this message translates to:
  /// **'Stage {stage} of {total}'**
  String labProgressLabel(int stage, int total);

  /// No description provided for @labQueueAwaitingCollection.
  ///
  /// In en, this message translates to:
  /// **'To collect'**
  String get labQueueAwaitingCollection;

  /// No description provided for @labQueueAwaitingRelease.
  ///
  /// In en, this message translates to:
  /// **'To release'**
  String get labQueueAwaitingRelease;

  /// No description provided for @labQueueCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get labQueueCancelled;

  /// No description provided for @labQueueInProgress.
  ///
  /// In en, this message translates to:
  /// **'In progress'**
  String get labQueueInProgress;

  /// No description provided for @labQueueReleased.
  ///
  /// In en, this message translates to:
  /// **'Released'**
  String get labQueueReleased;

  /// No description provided for @labQueueSampleCollected.
  ///
  /// In en, this message translates to:
  /// **'Sample collected'**
  String get labQueueSampleCollected;

  /// No description provided for @labReceivedBy.
  ///
  /// In en, this message translates to:
  /// **'Received by'**
  String get labReceivedBy;

  /// No description provided for @labReleaseConfirm.
  ///
  /// In en, this message translates to:
  /// **'Release the verified result of {test}? The doctor and the patient will then see it.'**
  String labReleaseConfirm(String test);

  /// No description provided for @labReleasedOnly.
  ///
  /// In en, this message translates to:
  /// **'Reports appear here after the laboratory has checked and released them.'**
  String get labReleasedOnly;

  /// No description provided for @labResultAwaitingVerification.
  ///
  /// In en, this message translates to:
  /// **'Awaiting verification'**
  String get labResultAwaitingVerification;

  /// No description provided for @labResultNotVerifiedYet.
  ///
  /// In en, this message translates to:
  /// **'Type the result as the laboratory reports it. It stays unverified until it is verified as a separate step.'**
  String get labResultNotVerifiedYet;

  /// No description provided for @labResultRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter the result.'**
  String get labResultRequired;

  /// No description provided for @labResultText.
  ///
  /// In en, this message translates to:
  /// **'Result'**
  String get labResultText;

  /// No description provided for @labResultVerified.
  ///
  /// In en, this message translates to:
  /// **'Verified'**
  String get labResultVerified;

  /// No description provided for @labReviewOrder.
  ///
  /// In en, this message translates to:
  /// **'Review order'**
  String get labReviewOrder;

  /// No description provided for @labReviewOrderHint.
  ///
  /// In en, this message translates to:
  /// **'Check the patient and the test. The order is placed only when the hospital system confirms it.'**
  String get labReviewOrderHint;

  /// No description provided for @labSample.
  ///
  /// In en, this message translates to:
  /// **'Sample'**
  String get labSample;

  /// No description provided for @labSampleNumber.
  ///
  /// In en, this message translates to:
  /// **'Sample number'**
  String get labSampleNumber;

  /// No description provided for @labSampleNumberHint.
  ///
  /// In en, this message translates to:
  /// **'Scan the label, or leave empty and the hospital system numbers the sample.'**
  String get labSampleNumberHint;

  /// No description provided for @labSampleType.
  ///
  /// In en, this message translates to:
  /// **'Sample type'**
  String get labSampleType;

  /// No description provided for @labSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search test, patient or sample number'**
  String get labSearchHint;

  /// No description provided for @labStatusCollected.
  ///
  /// In en, this message translates to:
  /// **'Sample collected'**
  String get labStatusCollected;

  /// No description provided for @labStatusDispatched.
  ///
  /// In en, this message translates to:
  /// **'Dispatched'**
  String get labStatusDispatched;

  /// No description provided for @labStatusOrdered.
  ///
  /// In en, this message translates to:
  /// **'Ordered'**
  String get labStatusOrdered;

  /// No description provided for @labStatusProcessing.
  ///
  /// In en, this message translates to:
  /// **'Processing'**
  String get labStatusProcessing;

  /// No description provided for @labStatusReceived.
  ///
  /// In en, this message translates to:
  /// **'Received in lab'**
  String get labStatusReceived;

  /// No description provided for @labStatusResultEntered.
  ///
  /// In en, this message translates to:
  /// **'Result entered'**
  String get labStatusResultEntered;

  /// No description provided for @labStatusSamplePending.
  ///
  /// In en, this message translates to:
  /// **'Sample pending'**
  String get labStatusSamplePending;

  /// No description provided for @labStatusVerified.
  ///
  /// In en, this message translates to:
  /// **'Verified'**
  String get labStatusVerified;

  /// No description provided for @labStepCollect.
  ///
  /// In en, this message translates to:
  /// **'Collect sample'**
  String get labStepCollect;

  /// No description provided for @labStepConfirm.
  ///
  /// In en, this message translates to:
  /// **'{step} for {test}?'**
  String labStepConfirm(String step, String test);

  /// No description provided for @labStepDispatch.
  ///
  /// In en, this message translates to:
  /// **'Dispatch sample'**
  String get labStepDispatch;

  /// No description provided for @labStepDone.
  ///
  /// In en, this message translates to:
  /// **'{step}: saved by the hospital system.'**
  String labStepDone(String step);

  /// No description provided for @labStepEnterResult.
  ///
  /// In en, this message translates to:
  /// **'Enter result'**
  String get labStepEnterResult;

  /// No description provided for @labStepReceive.
  ///
  /// In en, this message translates to:
  /// **'Receive in lab'**
  String get labStepReceive;

  /// No description provided for @labStepRefused.
  ///
  /// In en, this message translates to:
  /// **'The hospital system refused this step: the order has probably moved on. It has been reloaded.'**
  String get labStepRefused;

  /// No description provided for @labStepRelease.
  ///
  /// In en, this message translates to:
  /// **'Release result'**
  String get labStepRelease;

  /// No description provided for @labStepStartProcessing.
  ///
  /// In en, this message translates to:
  /// **'Start processing'**
  String get labStepStartProcessing;

  /// No description provided for @labStepVerify.
  ///
  /// In en, this message translates to:
  /// **'Verify result'**
  String get labStepVerify;

  /// No description provided for @labTestName.
  ///
  /// In en, this message translates to:
  /// **'Test name'**
  String get labTestName;

  /// No description provided for @labTestNameRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter the test name.'**
  String get labTestNameRequired;

  /// No description provided for @labTestNameTooLong.
  ///
  /// In en, this message translates to:
  /// **'Use at most {max} characters.'**
  String labTestNameTooLong(int max);

  /// No description provided for @labTestStatus.
  ///
  /// In en, this message translates to:
  /// **'Lab test status'**
  String get labTestStatus;

  /// No description provided for @labTimeline.
  ///
  /// In en, this message translates to:
  /// **'Timeline'**
  String get labTimeline;

  /// No description provided for @labTotalOrders.
  ///
  /// In en, this message translates to:
  /// **'Lab orders'**
  String get labTotalOrders;

  /// No description provided for @labVerifiedBy.
  ///
  /// In en, this message translates to:
  /// **'Verified by'**
  String get labVerifiedBy;

  /// No description provided for @labVerifyConfirm.
  ///
  /// In en, this message translates to:
  /// **'Verify the result of {test}? Verify only after checking the entered result against the sample and the instrument report.'**
  String labVerifyConfirm(String test);

  /// No description provided for @labWorklist.
  ///
  /// In en, this message translates to:
  /// **'Worklist'**
  String get labWorklist;

  /// No description provided for @labWorklistNewestFirst.
  ///
  /// In en, this message translates to:
  /// **'Newest orders first'**
  String get labWorklistNewestFirst;

  /// No description provided for @laboratory.
  ///
  /// In en, this message translates to:
  /// **'Laboratory'**
  String get laboratory;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @languageEnglish.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get languageEnglish;

  /// No description provided for @languageHindi.
  ///
  /// In en, this message translates to:
  /// **'हिंदी'**
  String get languageHindi;

  /// No description provided for @lastActive.
  ///
  /// In en, this message translates to:
  /// **'Last active {time}'**
  String lastActive(String time);

  /// No description provided for @lastChecked.
  ///
  /// In en, this message translates to:
  /// **'Last checked at {time}'**
  String lastChecked(String time);

  /// No description provided for @liveCounts.
  ///
  /// In en, this message translates to:
  /// **'Live counts for the selected hospital.'**
  String get liveCounts;

  /// No description provided for @loading.
  ///
  /// In en, this message translates to:
  /// **'Loading…'**
  String get loading;

  /// No description provided for @loginWithEmail.
  ///
  /// In en, this message translates to:
  /// **'Login with Email'**
  String get loginWithEmail;

  /// No description provided for @loginWithMobile.
  ///
  /// In en, this message translates to:
  /// **'Login with Mobile'**
  String get loginWithMobile;

  /// No description provided for @loginWithTokenId.
  ///
  /// In en, this message translates to:
  /// **'Login with Token / ID'**
  String get loginWithTokenId;

  /// No description provided for @logout.
  ///
  /// In en, this message translates to:
  /// **'Logout'**
  String get logout;

  /// No description provided for @lookupAndLogin.
  ///
  /// In en, this message translates to:
  /// **'Lookup & Login'**
  String get lookupAndLogin;

  /// No description provided for @lowStock.
  ///
  /// In en, this message translates to:
  /// **'Low stock'**
  String get lowStock;

  /// No description provided for @manufacturer.
  ///
  /// In en, this message translates to:
  /// **'Manufacturer'**
  String get manufacturer;

  /// No description provided for @markGiven.
  ///
  /// In en, this message translates to:
  /// **'Given'**
  String get markGiven;

  /// No description provided for @markHeld.
  ///
  /// In en, this message translates to:
  /// **'Hold'**
  String get markHeld;

  /// No description provided for @markMissed.
  ///
  /// In en, this message translates to:
  /// **'Missed'**
  String get markMissed;

  /// No description provided for @markReadFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not mark as read'**
  String get markReadFailed;

  /// No description provided for @markRefused.
  ///
  /// In en, this message translates to:
  /// **'Refused'**
  String get markRefused;

  /// No description provided for @medicationAdministration.
  ///
  /// In en, this message translates to:
  /// **'Medication administration'**
  String get medicationAdministration;

  /// No description provided for @medicationOrdersByDoctor.
  ///
  /// In en, this message translates to:
  /// **'Medication orders are written by the doctor. Nurses record the doses given under them.'**
  String get medicationOrdersByDoctor;

  /// No description provided for @medicationSafetyAlerts.
  ///
  /// In en, this message translates to:
  /// **'Medication safety alerts'**
  String get medicationSafetyAlerts;

  /// No description provided for @medicineCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 medicine} other{{count} medicines}}'**
  String medicineCount(int count);

  /// No description provided for @medicineName.
  ///
  /// In en, this message translates to:
  /// **'Medicine'**
  String get medicineName;

  /// No description provided for @medicineNameRequired.
  ///
  /// In en, this message translates to:
  /// **'Medicine {number}: enter the name.'**
  String medicineNameRequired(int number);

  /// No description provided for @medicineNumber.
  ///
  /// In en, this message translates to:
  /// **'Medicine {number}'**
  String medicineNumber(int number);

  /// No description provided for @medicineQuantityInvalid.
  ///
  /// In en, this message translates to:
  /// **'Medicine {number}: quantity must be at least 1.'**
  String medicineQuantityInvalid(int number);

  /// No description provided for @medicineStock.
  ///
  /// In en, this message translates to:
  /// **'Medicines'**
  String get medicineStock;

  /// No description provided for @medicines.
  ///
  /// In en, this message translates to:
  /// **'Medicines'**
  String get medicines;

  /// No description provided for @minutesShort.
  ///
  /// In en, this message translates to:
  /// **'{minutes} min'**
  String minutesShort(String minutes);

  /// No description provided for @mobileNumber.
  ///
  /// In en, this message translates to:
  /// **'Mobile number'**
  String get mobileNumber;

  /// No description provided for @moduleNotOnMobileBody.
  ///
  /// In en, this message translates to:
  /// **'This module will be added in a later app update. Use the web app for this work until then.'**
  String get moduleNotOnMobileBody;

  /// No description provided for @moduleNotOnMobileTitle.
  ///
  /// In en, this message translates to:
  /// **'{module} is not in the mobile app yet'**
  String moduleNotOnMobileTitle(String module);

  /// No description provided for @mrp.
  ///
  /// In en, this message translates to:
  /// **'MRP'**
  String get mrp;

  /// No description provided for @myDoctorProfile.
  ///
  /// In en, this message translates to:
  /// **'My doctor profile'**
  String get myDoctorProfile;

  /// No description provided for @myHospitals.
  ///
  /// In en, this message translates to:
  /// **'My hospitals'**
  String get myHospitals;

  /// No description provided for @myNurseProfile.
  ///
  /// In en, this message translates to:
  /// **'My nurse profile'**
  String get myNurseProfile;

  /// No description provided for @myProfile.
  ///
  /// In en, this message translates to:
  /// **'My profile'**
  String get myProfile;

  /// No description provided for @name.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get name;

  /// No description provided for @navAdminDashboard.
  ///
  /// In en, this message translates to:
  /// **'Admin Dashboard'**
  String get navAdminDashboard;

  /// No description provided for @navAiScribe.
  ///
  /// In en, this message translates to:
  /// **'AI Scribe'**
  String get navAiScribe;

  /// No description provided for @navAppointments.
  ///
  /// In en, this message translates to:
  /// **'Appointments'**
  String get navAppointments;

  /// No description provided for @navAuditLog.
  ///
  /// In en, this message translates to:
  /// **'Audit log'**
  String get navAuditLog;

  /// No description provided for @navBilling.
  ///
  /// In en, this message translates to:
  /// **'Billing'**
  String get navBilling;

  /// No description provided for @navBloodBank.
  ///
  /// In en, this message translates to:
  /// **'Blood Bank'**
  String get navBloodBank;

  /// No description provided for @navCompounder.
  ///
  /// In en, this message translates to:
  /// **'Compounder'**
  String get navCompounder;

  /// No description provided for @navConsultation.
  ///
  /// In en, this message translates to:
  /// **'Consultation'**
  String get navConsultation;

  /// No description provided for @navDepartments.
  ///
  /// In en, this message translates to:
  /// **'Departments'**
  String get navDepartments;

  /// No description provided for @navDoctors.
  ///
  /// In en, this message translates to:
  /// **'Doctors'**
  String get navDoctors;

  /// No description provided for @navEmergency.
  ///
  /// In en, this message translates to:
  /// **'Emergency'**
  String get navEmergency;

  /// No description provided for @navEmergencyAccess.
  ///
  /// In en, this message translates to:
  /// **'Emergency access'**
  String get navEmergencyAccess;

  /// No description provided for @navHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get navHome;

  /// No description provided for @navHospitalServices.
  ///
  /// In en, this message translates to:
  /// **'Hospital services'**
  String get navHospitalServices;

  /// No description provided for @navHospitals.
  ///
  /// In en, this message translates to:
  /// **'Hospitals'**
  String get navHospitals;

  /// No description provided for @navInventory.
  ///
  /// In en, this message translates to:
  /// **'Inventory'**
  String get navInventory;

  /// No description provided for @navIpd.
  ///
  /// In en, this message translates to:
  /// **'IPD / Ward / Beds'**
  String get navIpd;

  /// No description provided for @navLaboratory.
  ///
  /// In en, this message translates to:
  /// **'Laboratory'**
  String get navLaboratory;

  /// No description provided for @navMain.
  ///
  /// In en, this message translates to:
  /// **'Main'**
  String get navMain;

  /// No description provided for @navNurseDuty.
  ///
  /// In en, this message translates to:
  /// **'Nurse duty'**
  String get navNurseDuty;

  /// No description provided for @navNurses.
  ///
  /// In en, this message translates to:
  /// **'Nurses / Vitals'**
  String get navNurses;

  /// No description provided for @navPatients.
  ///
  /// In en, this message translates to:
  /// **'Patients'**
  String get navPatients;

  /// No description provided for @navPermissions.
  ///
  /// In en, this message translates to:
  /// **'Permissions'**
  String get navPermissions;

  /// No description provided for @navPharmacy.
  ///
  /// In en, this message translates to:
  /// **'Pharmacy'**
  String get navPharmacy;

  /// No description provided for @navPrescription.
  ///
  /// In en, this message translates to:
  /// **'Prescription'**
  String get navPrescription;

  /// No description provided for @navQueue.
  ///
  /// In en, this message translates to:
  /// **'Queue'**
  String get navQueue;

  /// No description provided for @navRadiology.
  ///
  /// In en, this message translates to:
  /// **'Radiology'**
  String get navRadiology;

  /// No description provided for @navReports.
  ///
  /// In en, this message translates to:
  /// **'Reports'**
  String get navReports;

  /// No description provided for @navRoles.
  ///
  /// In en, this message translates to:
  /// **'Roles'**
  String get navRoles;

  /// No description provided for @navSecuritySettings.
  ///
  /// In en, this message translates to:
  /// **'Security settings'**
  String get navSecuritySettings;

  /// No description provided for @navUsers.
  ///
  /// In en, this message translates to:
  /// **'Users'**
  String get navUsers;

  /// No description provided for @navigation.
  ///
  /// In en, this message translates to:
  /// **'Navigation'**
  String get navigation;

  /// No description provided for @needsAttention.
  ///
  /// In en, this message translates to:
  /// **'Needs attention'**
  String get needsAttention;

  /// No description provided for @newPassword.
  ///
  /// In en, this message translates to:
  /// **'New password'**
  String get newPassword;

  /// No description provided for @newToHms.
  ///
  /// In en, this message translates to:
  /// **'New to the Hospital Management System?'**
  String get newToHms;

  /// No description provided for @noAccessTitle.
  ///
  /// In en, this message translates to:
  /// **'You don\'t have access'**
  String get noAccessTitle;

  /// No description provided for @noActiveStay.
  ///
  /// In en, this message translates to:
  /// **'No current admission or open visit'**
  String get noActiveStay;

  /// No description provided for @noActiveToken.
  ///
  /// In en, this message translates to:
  /// **'No active token'**
  String get noActiveToken;

  /// No description provided for @noActiveTokenHint.
  ///
  /// In en, this message translates to:
  /// **'You don\'t have a consultation waiting at the moment.'**
  String get noActiveTokenHint;

  /// No description provided for @noAppointmentsMatch.
  ///
  /// In en, this message translates to:
  /// **'No appointments match this filter'**
  String get noAppointmentsMatch;

  /// No description provided for @noAppointmentsToday.
  ///
  /// In en, this message translates to:
  /// **'No appointments today'**
  String get noAppointmentsToday;

  /// No description provided for @noAppointmentsYet.
  ///
  /// In en, this message translates to:
  /// **'No appointments yet'**
  String get noAppointmentsYet;

  /// No description provided for @noAppointmentsYetHint.
  ///
  /// In en, this message translates to:
  /// **'Use Book appointment to choose a doctor and a time.'**
  String get noAppointmentsYetHint;

  /// No description provided for @noBedsAvailable.
  ///
  /// In en, this message translates to:
  /// **'No beds available'**
  String get noBedsAvailable;

  /// No description provided for @noBillsYet.
  ///
  /// In en, this message translates to:
  /// **'No bills yet'**
  String get noBillsYet;

  /// No description provided for @noConsultationsYet.
  ///
  /// In en, this message translates to:
  /// **'No completed consultations yet'**
  String get noConsultationsYet;

  /// No description provided for @noDiagnosesYet.
  ///
  /// In en, this message translates to:
  /// **'No diagnoses yet'**
  String get noDiagnosesYet;

  /// No description provided for @noDispensingYet.
  ///
  /// In en, this message translates to:
  /// **'Nothing dispensed yet'**
  String get noDispensingYet;

  /// No description provided for @noDoctorInbox.
  ///
  /// In en, this message translates to:
  /// **'Doctor notifications are not available: the hospital system has no inbox for staff yet.'**
  String get noDoctorInbox;

  /// No description provided for @noDocumentsYet.
  ///
  /// In en, this message translates to:
  /// **'No documents yet'**
  String get noDocumentsYet;

  /// No description provided for @noDosesDue.
  ///
  /// In en, this message translates to:
  /// **'No doses due'**
  String get noDosesDue;

  /// No description provided for @noDutyToday.
  ///
  /// In en, this message translates to:
  /// **'No duty assigned for today'**
  String get noDutyToday;

  /// No description provided for @noEncounterForVitals.
  ///
  /// In en, this message translates to:
  /// **'Vitals are recorded on an admission or an open OPD visit; this patient has neither.'**
  String get noEncounterForVitals;

  /// No description provided for @noFreeSlots.
  ///
  /// In en, this message translates to:
  /// **'No free time on this day. Try another date.'**
  String get noFreeSlots;

  /// No description provided for @noHistoryYet.
  ///
  /// In en, this message translates to:
  /// **'No history recorded'**
  String get noHistoryYet;

  /// No description provided for @noHospitalAccess.
  ///
  /// In en, this message translates to:
  /// **'Your account is not active in any hospital yet. Ask your hospital administrator.'**
  String get noHospitalAccess;

  /// No description provided for @noHospitalMatches.
  ///
  /// In en, this message translates to:
  /// **'No hospital matches your search.'**
  String get noHospitalMatches;

  /// No description provided for @noLabOrdersForVisit.
  ///
  /// In en, this message translates to:
  /// **'No lab tests ordered on this visit'**
  String get noLabOrdersForVisit;

  /// No description provided for @noLabReportsYet.
  ///
  /// In en, this message translates to:
  /// **'No lab reports yet'**
  String get noLabReportsYet;

  /// No description provided for @noLabReportsYetHint.
  ///
  /// In en, this message translates to:
  /// **'Reports for tests in progress appear once they are released.'**
  String get noLabReportsYetHint;

  /// No description provided for @noMedicationOrders.
  ///
  /// In en, this message translates to:
  /// **'No active medication orders'**
  String get noMedicationOrders;

  /// No description provided for @noMedicinesFound.
  ///
  /// In en, this message translates to:
  /// **'No medicines found'**
  String get noMedicinesFound;

  /// No description provided for @noMedicinesListed.
  ///
  /// In en, this message translates to:
  /// **'No medicines listed'**
  String get noMedicinesListed;

  /// No description provided for @noNotesYet.
  ///
  /// In en, this message translates to:
  /// **'No notes yet'**
  String get noNotesYet;

  /// No description provided for @noNotifications.
  ///
  /// In en, this message translates to:
  /// **'No notifications'**
  String get noNotifications;

  /// No description provided for @noOpenTasks.
  ///
  /// In en, this message translates to:
  /// **'No open tasks'**
  String get noOpenTasks;

  /// No description provided for @noOtherDevices.
  ///
  /// In en, this message translates to:
  /// **'No signed-in devices.'**
  String get noOtherDevices;

  /// No description provided for @noPageMatches.
  ///
  /// In en, this message translates to:
  /// **'No page matches “{query}”.'**
  String noPageMatches(String query);

  /// No description provided for @noPatientsFound.
  ///
  /// In en, this message translates to:
  /// **'No patient found'**
  String get noPatientsFound;

  /// No description provided for @noPatientsFoundHint.
  ///
  /// In en, this message translates to:
  /// **'Only patients in your care are shown.'**
  String get noPatientsFoundHint;

  /// No description provided for @noPatientsYet.
  ///
  /// In en, this message translates to:
  /// **'No patients registered yet'**
  String get noPatientsYet;

  /// No description provided for @noPaymentsYet.
  ///
  /// In en, this message translates to:
  /// **'No payments recorded'**
  String get noPaymentsYet;

  /// No description provided for @noPrescriptionsForVisit.
  ///
  /// In en, this message translates to:
  /// **'No prescription on this visit yet'**
  String get noPrescriptionsForVisit;

  /// No description provided for @noPrescriptionsInQueue.
  ///
  /// In en, this message translates to:
  /// **'No prescriptions here'**
  String get noPrescriptionsInQueue;

  /// No description provided for @noPrescriptionsYet.
  ///
  /// In en, this message translates to:
  /// **'No prescriptions yet'**
  String get noPrescriptionsYet;

  /// No description provided for @noPrescriptionsYetHint.
  ///
  /// In en, this message translates to:
  /// **'Prescriptions from your visits will appear here.'**
  String get noPrescriptionsYetHint;

  /// No description provided for @noReadingsYet.
  ///
  /// In en, this message translates to:
  /// **'No readings recorded yet'**
  String get noReadingsYet;

  /// No description provided for @noResultValues.
  ///
  /// In en, this message translates to:
  /// **'No values in this report'**
  String get noResultValues;

  /// No description provided for @noShowTitle.
  ///
  /// In en, this message translates to:
  /// **'Mark as no-show?'**
  String get noShowTitle;

  /// No description provided for @noStaffInbox.
  ///
  /// In en, this message translates to:
  /// **'Notifications are not available: the hospital system has no inbox for staff yet.'**
  String get noStaffInbox;

  /// No description provided for @noStockMovements.
  ///
  /// In en, this message translates to:
  /// **'No stock movements yet'**
  String get noStockMovements;

  /// No description provided for @noTokenServed.
  ///
  /// In en, this message translates to:
  /// **'No token being served'**
  String get noTokenServed;

  /// No description provided for @noUpcomingAppointments.
  ///
  /// In en, this message translates to:
  /// **'No upcoming appointments'**
  String get noUpcomingAppointments;

  /// No description provided for @noUsableBatch.
  ///
  /// In en, this message translates to:
  /// **'No unexpired batch of this medicine is in stock.'**
  String get noUsableBatch;

  /// No description provided for @noVisitsToShow.
  ///
  /// In en, this message translates to:
  /// **'No visits to show'**
  String get noVisitsToShow;

  /// No description provided for @noVisitsToShowHint.
  ///
  /// In en, this message translates to:
  /// **'Visits are created at the reception when a patient arrives.'**
  String get noVisitsToShowHint;

  /// No description provided for @noVisitsYet.
  ///
  /// In en, this message translates to:
  /// **'No visits yet'**
  String get noVisitsYet;

  /// No description provided for @noVitalsYet.
  ///
  /// In en, this message translates to:
  /// **'No vitals recorded on this visit'**
  String get noVitalsYet;

  /// No description provided for @noWardPatients.
  ///
  /// In en, this message translates to:
  /// **'No patients on your duty'**
  String get noWardPatients;

  /// No description provided for @noWardPatientsHint.
  ///
  /// In en, this message translates to:
  /// **'Patients appear here when they are in a ward you are on duty in, or assigned to you for today\'s shift.'**
  String get noWardPatientsHint;

  /// No description provided for @nobodyCalled.
  ///
  /// In en, this message translates to:
  /// **'Nobody called'**
  String get nobodyCalled;

  /// No description provided for @nobodyInConsultation.
  ///
  /// In en, this message translates to:
  /// **'Nobody in consultation'**
  String get nobodyInConsultation;

  /// No description provided for @nobodyWaiting.
  ///
  /// In en, this message translates to:
  /// **'Nobody waiting'**
  String get nobodyWaiting;

  /// No description provided for @none.
  ///
  /// In en, this message translates to:
  /// **'None'**
  String get none;

  /// No description provided for @notAvailableNow.
  ///
  /// In en, this message translates to:
  /// **'Not available right now'**
  String get notAvailableNow;

  /// No description provided for @notEligibleBody.
  ///
  /// In en, this message translates to:
  /// **'{department} work is only for {roles}. Please sign in with an account that has one of these roles.'**
  String notEligibleBody(String department, String roles);

  /// No description provided for @notEligibleForPage.
  ///
  /// In en, this message translates to:
  /// **'You are not eligible for that page'**
  String get notEligibleForPage;

  /// No description provided for @notEligibleForPageBody.
  ///
  /// In en, this message translates to:
  /// **'{module} is not open to your role in this hospital.'**
  String notEligibleForPageBody(String module);

  /// No description provided for @notEligibleTitle.
  ///
  /// In en, this message translates to:
  /// **'You are not eligible for this work'**
  String get notEligibleTitle;

  /// No description provided for @notMemberOfAnyHospital.
  ///
  /// In en, this message translates to:
  /// **'You are not a member of any hospital yet.'**
  String get notMemberOfAnyHospital;

  /// No description provided for @notScheduled.
  ///
  /// In en, this message translates to:
  /// **'Not scheduled'**
  String get notScheduled;

  /// No description provided for @notSignedInSignIn.
  ///
  /// In en, this message translates to:
  /// **'Not signed in · Sign in'**
  String get notSignedInSignIn;

  /// No description provided for @notVerified.
  ///
  /// In en, this message translates to:
  /// **'Not verified'**
  String get notVerified;

  /// No description provided for @noteAssessment.
  ///
  /// In en, this message translates to:
  /// **'Assessment'**
  String get noteAssessment;

  /// No description provided for @noteChiefComplaint.
  ///
  /// In en, this message translates to:
  /// **'Chief complaint'**
  String get noteChiefComplaint;

  /// No description provided for @noteCurrentMedications.
  ///
  /// In en, this message translates to:
  /// **'Current medications'**
  String get noteCurrentMedications;

  /// No description provided for @noteExamination.
  ///
  /// In en, this message translates to:
  /// **'Examination'**
  String get noteExamination;

  /// No description provided for @noteNeedsOneSection.
  ///
  /// In en, this message translates to:
  /// **'Write at least one part of the note.'**
  String get noteNeedsOneSection;

  /// No description provided for @noteOther.
  ///
  /// In en, this message translates to:
  /// **'Other notes'**
  String get noteOther;

  /// No description provided for @notePastHistory.
  ///
  /// In en, this message translates to:
  /// **'Past history'**
  String get notePastHistory;

  /// No description provided for @notePlan.
  ///
  /// In en, this message translates to:
  /// **'Plan'**
  String get notePlan;

  /// No description provided for @notePresentIllness.
  ///
  /// In en, this message translates to:
  /// **'History of present illness'**
  String get notePresentIllness;

  /// No description provided for @noteSaved.
  ///
  /// In en, this message translates to:
  /// **'Note saved by the hospital system.'**
  String get noteSaved;

  /// No description provided for @noteText.
  ///
  /// In en, this message translates to:
  /// **'Note'**
  String get noteText;

  /// No description provided for @noteTextRequired.
  ///
  /// In en, this message translates to:
  /// **'Write the note first.'**
  String get noteTextRequired;

  /// No description provided for @noteTooLong.
  ///
  /// In en, this message translates to:
  /// **'Keep the note under {count} characters.'**
  String noteTooLong(int count);

  /// No description provided for @noteType.
  ///
  /// In en, this message translates to:
  /// **'Note type'**
  String get noteType;

  /// No description provided for @noteTypeCommunication.
  ///
  /// In en, this message translates to:
  /// **'Communication'**
  String get noteTypeCommunication;

  /// No description provided for @noteTypeEducation.
  ///
  /// In en, this message translates to:
  /// **'Patient education'**
  String get noteTypeEducation;

  /// No description provided for @noteTypeHandoff.
  ///
  /// In en, this message translates to:
  /// **'Shift handoff'**
  String get noteTypeHandoff;

  /// No description provided for @noteTypeIncident.
  ///
  /// In en, this message translates to:
  /// **'Incident report'**
  String get noteTypeIncident;

  /// No description provided for @noteTypeProgress.
  ///
  /// In en, this message translates to:
  /// **'Progress note'**
  String get noteTypeProgress;

  /// No description provided for @notesAreFinal.
  ///
  /// In en, this message translates to:
  /// **'Saved notes cannot be edited. To correct one, add a new note.'**
  String get notesAreFinal;

  /// No description provided for @nothingLeftToDispense.
  ///
  /// In en, this message translates to:
  /// **'Nothing is left to dispense on this prescription.'**
  String get nothingLeftToDispense;

  /// No description provided for @nothingNeedsAttention.
  ///
  /// In en, this message translates to:
  /// **'Nothing needs attention'**
  String get nothingNeedsAttention;

  /// No description provided for @nothingNeedsAttentionText.
  ///
  /// In en, this message translates to:
  /// **'No waiting patients, urgent tests or active emergencies right now.'**
  String get nothingNeedsAttentionText;

  /// No description provided for @notifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get notifications;

  /// No description provided for @notificationsIntro.
  ///
  /// In en, this message translates to:
  /// **'Messages from your hospital. Open one to see the page it is about.'**
  String get notificationsIntro;

  /// No description provided for @nowServing.
  ///
  /// In en, this message translates to:
  /// **'Now serving'**
  String get nowServing;

  /// No description provided for @nowServingToken.
  ///
  /// In en, this message translates to:
  /// **'Now serving token {token}'**
  String nowServingToken(String token);

  /// No description provided for @nurseProfileMissing.
  ///
  /// In en, this message translates to:
  /// **'No nurse profile is linked to your login at this hospital. Ask the hospital Admin to link it.'**
  String get nurseProfileMissing;

  /// No description provided for @nursingNotes.
  ///
  /// In en, this message translates to:
  /// **'Nursing notes'**
  String get nursingNotes;

  /// No description provided for @onThisStay.
  ///
  /// In en, this message translates to:
  /// **'This admission'**
  String get onThisStay;

  /// No description provided for @opdVisitOn.
  ///
  /// In en, this message translates to:
  /// **'OPD visit · {date}'**
  String opdVisitOn(String date);

  /// No description provided for @open.
  ///
  /// In en, this message translates to:
  /// **'Open'**
  String get open;

  /// No description provided for @openConsultation.
  ///
  /// In en, this message translates to:
  /// **'Open consultation'**
  String get openConsultation;

  /// No description provided for @openNavigation.
  ///
  /// In en, this message translates to:
  /// **'Open navigation'**
  String get openNavigation;

  /// No description provided for @openPatientRecord.
  ///
  /// In en, this message translates to:
  /// **'Open patient record'**
  String get openPatientRecord;

  /// No description provided for @openTasks.
  ///
  /// In en, this message translates to:
  /// **'Open tasks'**
  String get openTasks;

  /// No description provided for @openVisits.
  ///
  /// In en, this message translates to:
  /// **'Open visits'**
  String get openVisits;

  /// No description provided for @operations.
  ///
  /// In en, this message translates to:
  /// **'Operations'**
  String get operations;

  /// No description provided for @opsBackToList.
  ///
  /// In en, this message translates to:
  /// **'Back to list'**
  String get opsBackToList;

  /// No description provided for @opsSaved.
  ///
  /// In en, this message translates to:
  /// **'Saved by the hospital system.'**
  String get opsSaved;

  /// No description provided for @opsSearch.
  ///
  /// In en, this message translates to:
  /// **'Search'**
  String get opsSearch;

  /// No description provided for @opsStepRefused.
  ///
  /// In en, this message translates to:
  /// **'The hospital system did not allow this step for the record as it is now. Refresh to see its current state.'**
  String get opsStepRefused;

  /// No description provided for @orDivider.
  ///
  /// In en, this message translates to:
  /// **'OR'**
  String get orDivider;

  /// No description provided for @orderLabTest.
  ///
  /// In en, this message translates to:
  /// **'Order lab test'**
  String get orderLabTest;

  /// No description provided for @orderedBy.
  ///
  /// In en, this message translates to:
  /// **'Ordered by'**
  String get orderedBy;

  /// No description provided for @otpLabel.
  ///
  /// In en, this message translates to:
  /// **'OTP'**
  String get otpLabel;

  /// No description provided for @otpPrintedOnServer.
  ///
  /// In en, this message translates to:
  /// **'Development server: the code is printed in the server log, not sent by SMS.'**
  String get otpPrintedOnServer;

  /// No description provided for @otpSentTo.
  ///
  /// In en, this message translates to:
  /// **'Enter the 6-digit OTP sent to {phone}'**
  String otpSentTo(String phone);

  /// No description provided for @outOfStock.
  ///
  /// In en, this message translates to:
  /// **'Out of stock'**
  String get outOfStock;

  /// No description provided for @outstandingBalance.
  ///
  /// In en, this message translates to:
  /// **'Outstanding balance'**
  String get outstandingBalance;

  /// No description provided for @overrideReason.
  ///
  /// In en, this message translates to:
  /// **'Reason to prescribe anyway'**
  String get overrideReason;

  /// No description provided for @overrideReasonHint.
  ///
  /// In en, this message translates to:
  /// **'At least {count} characters. It is recorded with the prescription.'**
  String overrideReasonHint(int count);

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @passwordUpdated.
  ///
  /// In en, this message translates to:
  /// **'Password updated. Sign in with your new password.'**
  String get passwordUpdated;

  /// No description provided for @pastVisits.
  ///
  /// In en, this message translates to:
  /// **'Past visits'**
  String get pastVisits;

  /// No description provided for @patientDataUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Your records could not be loaded. Check your connection and try again.'**
  String get patientDataUnavailable;

  /// No description provided for @patientHomeIntro.
  ///
  /// In en, this message translates to:
  /// **'Your queue token, appointments, prescriptions, reports and bills in one place.'**
  String get patientHomeIntro;

  /// No description provided for @patientId.
  ///
  /// In en, this message translates to:
  /// **'Patient ID'**
  String get patientId;

  /// No description provided for @patientLabel.
  ///
  /// In en, this message translates to:
  /// **'Patient'**
  String get patientLabel;

  /// No description provided for @patientNavAppointments.
  ///
  /// In en, this message translates to:
  /// **'My Appointments'**
  String get patientNavAppointments;

  /// No description provided for @patientNavBills.
  ///
  /// In en, this message translates to:
  /// **'My Bills'**
  String get patientNavBills;

  /// No description provided for @patientNavConsent.
  ///
  /// In en, this message translates to:
  /// **'Notifications / Consent'**
  String get patientNavConsent;

  /// No description provided for @patientNavHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get patientNavHome;

  /// No description provided for @patientNavLab.
  ///
  /// In en, this message translates to:
  /// **'My Lab Reports'**
  String get patientNavLab;

  /// No description provided for @patientNavNotifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get patientNavNotifications;

  /// No description provided for @patientNavPrescriptions.
  ///
  /// In en, this message translates to:
  /// **'My Prescriptions'**
  String get patientNavPrescriptions;

  /// No description provided for @patientNavQueue.
  ///
  /// In en, this message translates to:
  /// **'My Queue / Token'**
  String get patientNavQueue;

  /// No description provided for @patientNavRecords.
  ///
  /// In en, this message translates to:
  /// **'My Medical Records'**
  String get patientNavRecords;

  /// No description provided for @patientNotInCare.
  ///
  /// In en, this message translates to:
  /// **'You cannot open this record'**
  String get patientNotInCare;

  /// No description provided for @patientNotInCareHint.
  ///
  /// In en, this message translates to:
  /// **'The hospital system shows a doctor only the patients in their care at this hospital.'**
  String get patientNotInCareHint;

  /// No description provided for @patientPortal.
  ///
  /// In en, this message translates to:
  /// **'Patient portal'**
  String get patientPortal;

  /// No description provided for @patientProfile.
  ///
  /// In en, this message translates to:
  /// **'Patient profile'**
  String get patientProfile;

  /// No description provided for @patientSignIn.
  ///
  /// In en, this message translates to:
  /// **'Patient sign in'**
  String get patientSignIn;

  /// No description provided for @patientSignInIntro.
  ///
  /// In en, this message translates to:
  /// **'Patients see their own appointments, prescriptions, reports and bills.'**
  String get patientSignInIntro;

  /// No description provided for @patientsInCare.
  ///
  /// In en, this message translates to:
  /// **'Patients in care'**
  String get patientsInCare;

  /// No description provided for @payAtHospital.
  ///
  /// In en, this message translates to:
  /// **'Bills are paid at the hospital'**
  String get payAtHospital;

  /// No description provided for @payAtHospitalBody.
  ///
  /// In en, this message translates to:
  /// **'Online payment is not available yet. Payments made at the billing desk appear here.'**
  String get payAtHospitalBody;

  /// No description provided for @paymentBankTransfer.
  ///
  /// In en, this message translates to:
  /// **'Bank transfer'**
  String get paymentBankTransfer;

  /// No description provided for @paymentCard.
  ///
  /// In en, this message translates to:
  /// **'Card'**
  String get paymentCard;

  /// No description provided for @paymentCash.
  ///
  /// In en, this message translates to:
  /// **'Cash'**
  String get paymentCash;

  /// No description provided for @paymentHistory.
  ///
  /// In en, this message translates to:
  /// **'Payment history'**
  String get paymentHistory;

  /// No description provided for @paymentUpi.
  ///
  /// In en, this message translates to:
  /// **'UPI'**
  String get paymentUpi;

  /// No description provided for @pendingPrescriptions.
  ///
  /// In en, this message translates to:
  /// **'Prescriptions to dispense'**
  String get pendingPrescriptions;

  /// No description provided for @pendingTasks.
  ///
  /// In en, this message translates to:
  /// **'Pending tasks'**
  String get pendingTasks;

  /// No description provided for @pharmacyActivity.
  ///
  /// In en, this message translates to:
  /// **'Activity'**
  String get pharmacyActivity;

  /// No description provided for @pharmacyIntro.
  ///
  /// In en, this message translates to:
  /// **'Prescriptions to dispense, medicine stock and recent activity at this hospital.'**
  String get pharmacyIntro;

  /// No description provided for @pickDate.
  ///
  /// In en, this message translates to:
  /// **'Pick a date'**
  String get pickDate;

  /// No description provided for @pickerChange.
  ///
  /// In en, this message translates to:
  /// **'Change'**
  String get pickerChange;

  /// No description provided for @pickerTypeMore.
  ///
  /// In en, this message translates to:
  /// **'Type at least {count} characters.'**
  String pickerTypeMore(int count);

  /// No description provided for @platformAndroid.
  ///
  /// In en, this message translates to:
  /// **'Android'**
  String get platformAndroid;

  /// No description provided for @platformIos.
  ///
  /// In en, this message translates to:
  /// **'iPhone / iPad'**
  String get platformIos;

  /// No description provided for @platformOther.
  ///
  /// In en, this message translates to:
  /// **'Other device'**
  String get platformOther;

  /// No description provided for @platformWeb.
  ///
  /// In en, this message translates to:
  /// **'Web browser'**
  String get platformWeb;

  /// No description provided for @positionShort.
  ///
  /// In en, this message translates to:
  /// **'position {position}'**
  String positionShort(String position);

  /// No description provided for @prescribeAnyway.
  ///
  /// In en, this message translates to:
  /// **'Prescribe anyway'**
  String get prescribeAnyway;

  /// No description provided for @prescribedIssuedLeft.
  ///
  /// In en, this message translates to:
  /// **'Prescribed {prescribed} · Issued {issued} · Left {left}'**
  String prescribedIssuedLeft(int prescribed, int issued, int left);

  /// No description provided for @prescription.
  ///
  /// In en, this message translates to:
  /// **'Prescription'**
  String get prescription;

  /// No description provided for @prescriptionCancelledNoDispense.
  ///
  /// In en, this message translates to:
  /// **'This prescription was cancelled; it cannot be dispensed.'**
  String get prescriptionCancelledNoDispense;

  /// No description provided for @prescriptionCode.
  ///
  /// In en, this message translates to:
  /// **'RX-{id}'**
  String prescriptionCode(int id);

  /// No description provided for @prescriptionFreeTextNote.
  ///
  /// In en, this message translates to:
  /// **'Write each medicine as on the web form. Nothing is suggested by the app.'**
  String get prescriptionFreeTextNote;

  /// No description provided for @prescriptionMaybeSaved.
  ///
  /// In en, this message translates to:
  /// **'This prescription may already be saved. Check the list below before saving again.'**
  String get prescriptionMaybeSaved;

  /// No description provided for @prescriptionNeedsVerification.
  ///
  /// In en, this message translates to:
  /// **'This paper prescription must be verified by a second pharmacist or an Admin before it is dispensed.'**
  String get prescriptionNeedsVerification;

  /// No description provided for @prescriptionQueue.
  ///
  /// In en, this message translates to:
  /// **'Prescriptions'**
  String get prescriptionQueue;

  /// No description provided for @prescriptionSaved.
  ///
  /// In en, this message translates to:
  /// **'Prescription #{id} saved by the hospital system.'**
  String prescriptionSaved(String id);

  /// No description provided for @prescriptionsIntro.
  ///
  /// In en, this message translates to:
  /// **'Medicines your doctors have prescribed.'**
  String get prescriptionsIntro;

  /// No description provided for @priority.
  ///
  /// In en, this message translates to:
  /// **'Priority'**
  String get priority;

  /// No description provided for @priorityRoutine.
  ///
  /// In en, this message translates to:
  /// **'Routine'**
  String get priorityRoutine;

  /// No description provided for @priorityStat.
  ///
  /// In en, this message translates to:
  /// **'STAT'**
  String get priorityStat;

  /// No description provided for @profileChangesAtHospital.
  ///
  /// In en, this message translates to:
  /// **'To change your details, please contact the hospital reception.'**
  String get profileChangesAtHospital;

  /// No description provided for @profileIntro.
  ///
  /// In en, this message translates to:
  /// **'Your details as the hospital has recorded them.'**
  String get profileIntro;

  /// No description provided for @profileMenuFor.
  ///
  /// In en, this message translates to:
  /// **'Profile menu for {name}'**
  String profileMenuFor(String name);

  /// No description provided for @qualification.
  ///
  /// In en, this message translates to:
  /// **'Qualification'**
  String get qualification;

  /// No description provided for @quantity.
  ///
  /// In en, this message translates to:
  /// **'Quantity'**
  String get quantity;

  /// No description provided for @quantityNow.
  ///
  /// In en, this message translates to:
  /// **'Quantity to issue now'**
  String get quantityNow;

  /// No description provided for @queueCall.
  ///
  /// In en, this message translates to:
  /// **'Call'**
  String get queueCall;

  /// No description provided for @queueComplete.
  ///
  /// In en, this message translates to:
  /// **'Complete'**
  String get queueComplete;

  /// No description provided for @queueDoctorBusy.
  ///
  /// In en, this message translates to:
  /// **'This doctor already has a patient in consultation. Complete that one first.'**
  String get queueDoctorBusy;

  /// No description provided for @queueFinishedToday.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =0{No token finished today} =1{1 token finished today} other{{count} tokens finished today}}'**
  String queueFinishedToday(int count);

  /// No description provided for @queueIntro.
  ///
  /// In en, this message translates to:
  /// **'Your place in today\'s consultation queue. This page checks again every 30 seconds while it is open.'**
  String get queueIntro;

  /// No description provided for @queueMoveConfirm.
  ///
  /// In en, this message translates to:
  /// **'Token #{token} will leave the queue. The patient may be notified by the hospital system.'**
  String queueMoveConfirm(String token);

  /// No description provided for @queueMoveFailed.
  ///
  /// In en, this message translates to:
  /// **'The queue could not be updated'**
  String get queueMoveFailed;

  /// No description provided for @queueNoShow.
  ///
  /// In en, this message translates to:
  /// **'No-show'**
  String get queueNoShow;

  /// No description provided for @queuePosition.
  ///
  /// In en, this message translates to:
  /// **'Position in queue'**
  String get queuePosition;

  /// No description provided for @queueSkip.
  ///
  /// In en, this message translates to:
  /// **'Skip'**
  String get queueSkip;

  /// No description provided for @queueStartConsultation.
  ///
  /// In en, this message translates to:
  /// **'Start consultation'**
  String get queueStartConsultation;

  /// No description provided for @queueStatus.
  ///
  /// In en, this message translates to:
  /// **'Queue status'**
  String get queueStatus;

  /// No description provided for @quickActions.
  ///
  /// In en, this message translates to:
  /// **'Quick actions'**
  String get quickActions;

  /// No description provided for @reasonForVisit.
  ///
  /// In en, this message translates to:
  /// **'Reason for visit'**
  String get reasonForVisit;

  /// No description provided for @reasonRequired.
  ///
  /// In en, this message translates to:
  /// **'Reason (required)'**
  String get reasonRequired;

  /// No description provided for @recentConsultations.
  ///
  /// In en, this message translates to:
  /// **'Recent consultations'**
  String get recentConsultations;

  /// No description provided for @recentDispensing.
  ///
  /// In en, this message translates to:
  /// **'Recent dispensing'**
  String get recentDispensing;

  /// No description provided for @recentLabReports.
  ///
  /// In en, this message translates to:
  /// **'Recent lab reports'**
  String get recentLabReports;

  /// No description provided for @recentNursingActivity.
  ///
  /// In en, this message translates to:
  /// **'Recent nursing activity'**
  String get recentNursingActivity;

  /// No description provided for @recentPrescriptions.
  ///
  /// In en, this message translates to:
  /// **'Recent prescriptions'**
  String get recentPrescriptions;

  /// No description provided for @recentStockMovements.
  ///
  /// In en, this message translates to:
  /// **'Recent stock movements'**
  String get recentStockMovements;

  /// No description provided for @recentlyRegistered.
  ///
  /// In en, this message translates to:
  /// **'Recently registered patients'**
  String get recentlyRegistered;

  /// No description provided for @recordOn.
  ///
  /// In en, this message translates to:
  /// **'Record on'**
  String get recordOn;

  /// No description provided for @recordSignedNoChange.
  ///
  /// In en, this message translates to:
  /// **'This record is signed and cannot be changed. Add a new record instead.'**
  String get recordSignedNoChange;

  /// No description provided for @referenceRange.
  ///
  /// In en, this message translates to:
  /// **'Reference range'**
  String get referenceRange;

  /// No description provided for @refresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get refresh;

  /// No description provided for @refreshFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not refresh'**
  String get refreshFailed;

  /// No description provided for @refund.
  ///
  /// In en, this message translates to:
  /// **'Refund'**
  String get refund;

  /// No description provided for @registerIntro.
  ///
  /// In en, this message translates to:
  /// **'Staff accounts are created by invitation from your hospital.'**
  String get registerIntro;

  /// No description provided for @registerTitle.
  ///
  /// In en, this message translates to:
  /// **'Create your patient account'**
  String get registerTitle;

  /// No description provided for @registeredInTotal.
  ///
  /// In en, this message translates to:
  /// **'{count} registered in total'**
  String registeredInTotal(String count);

  /// No description provided for @registration.
  ///
  /// In en, this message translates to:
  /// **'Registration'**
  String get registration;

  /// No description provided for @releasedOn.
  ///
  /// In en, this message translates to:
  /// **'Released on'**
  String get releasedOn;

  /// No description provided for @releasedResults.
  ///
  /// In en, this message translates to:
  /// **'Released results'**
  String get releasedResults;

  /// No description provided for @remarks.
  ///
  /// In en, this message translates to:
  /// **'Remarks'**
  String get remarks;

  /// No description provided for @removeMedicine.
  ///
  /// In en, this message translates to:
  /// **'Remove medicine'**
  String get removeMedicine;

  /// No description provided for @reorderLevel.
  ///
  /// In en, this message translates to:
  /// **'Reorder level'**
  String get reorderLevel;

  /// No description provided for @reportNotes.
  ///
  /// In en, this message translates to:
  /// **'Report notes'**
  String get reportNotes;

  /// No description provided for @resendCode.
  ///
  /// In en, this message translates to:
  /// **'Resend code'**
  String get resendCode;

  /// No description provided for @resetCodeSent.
  ///
  /// In en, this message translates to:
  /// **'If an active staff account matches, a code was sent to its registered mobile number.'**
  String get resetCodeSent;

  /// No description provided for @resetConfirmIntro.
  ///
  /// In en, this message translates to:
  /// **'Enter the code from the SMS and choose a new password.'**
  String get resetConfirmIntro;

  /// No description provided for @resetPasswordTitle.
  ///
  /// In en, this message translates to:
  /// **'Reset your password'**
  String get resetPasswordTitle;

  /// No description provided for @resetRequestIntro.
  ///
  /// In en, this message translates to:
  /// **'A code is sent to the mobile number registered on your staff account.'**
  String get resetRequestIntro;

  /// No description provided for @restoreFailedBody.
  ///
  /// In en, this message translates to:
  /// **'Your sign-in is kept on this device. Check the connection and try again, or sign out.'**
  String get restoreFailedBody;

  /// No description provided for @restoreFailedTitle.
  ///
  /// In en, this message translates to:
  /// **'Could not reach the hospital server'**
  String get restoreFailedTitle;

  /// No description provided for @restoringSession.
  ///
  /// In en, this message translates to:
  /// **'Opening your session…'**
  String get restoringSession;

  /// No description provided for @resultNotReleased.
  ///
  /// In en, this message translates to:
  /// **'Result not released yet'**
  String get resultNotReleased;

  /// No description provided for @results.
  ///
  /// In en, this message translates to:
  /// **'Results'**
  String get results;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// No description provided for @roleAdmin.
  ///
  /// In en, this message translates to:
  /// **'Admin'**
  String get roleAdmin;

  /// No description provided for @roleBillingStaff.
  ///
  /// In en, this message translates to:
  /// **'Billing Staff'**
  String get roleBillingStaff;

  /// No description provided for @roleBloodBankStaff.
  ///
  /// In en, this message translates to:
  /// **'Blood Bank Staff'**
  String get roleBloodBankStaff;

  /// No description provided for @roleCompounder.
  ///
  /// In en, this message translates to:
  /// **'Compounder'**
  String get roleCompounder;

  /// No description provided for @roleDoctor.
  ///
  /// In en, this message translates to:
  /// **'Doctor'**
  String get roleDoctor;

  /// No description provided for @roleHomeBilling.
  ///
  /// In en, this message translates to:
  /// **'Billing today'**
  String get roleHomeBilling;

  /// No description provided for @roleHomeBloodBank.
  ///
  /// In en, this message translates to:
  /// **'Blood bank today'**
  String get roleHomeBloodBank;

  /// No description provided for @roleHomeDoctor.
  ///
  /// In en, this message translates to:
  /// **'Your clinic today'**
  String get roleHomeDoctor;

  /// No description provided for @roleHomeLaboratory.
  ///
  /// In en, this message translates to:
  /// **'Laboratory today'**
  String get roleHomeLaboratory;

  /// No description provided for @roleHomeNurse.
  ///
  /// In en, this message translates to:
  /// **'Your ward today'**
  String get roleHomeNurse;

  /// No description provided for @roleHomePharmacy.
  ///
  /// In en, this message translates to:
  /// **'Pharmacy today'**
  String get roleHomePharmacy;

  /// No description provided for @roleHomeReceptionist.
  ///
  /// In en, this message translates to:
  /// **'Front desk today'**
  String get roleHomeReceptionist;

  /// No description provided for @roleHomeStore.
  ///
  /// In en, this message translates to:
  /// **'Store today'**
  String get roleHomeStore;

  /// No description provided for @roleHospitalManager.
  ///
  /// In en, this message translates to:
  /// **'Hospital Manager'**
  String get roleHospitalManager;

  /// No description provided for @roleInventoryStaff.
  ///
  /// In en, this message translates to:
  /// **'Inventory Staff'**
  String get roleInventoryStaff;

  /// No description provided for @roleLabStaff.
  ///
  /// In en, this message translates to:
  /// **'Lab Staff'**
  String get roleLabStaff;

  /// No description provided for @roleNurse.
  ///
  /// In en, this message translates to:
  /// **'Nurse'**
  String get roleNurse;

  /// No description provided for @rolePharmacist.
  ///
  /// In en, this message translates to:
  /// **'Pharmacist'**
  String get rolePharmacist;

  /// No description provided for @roleReceptionist.
  ///
  /// In en, this message translates to:
  /// **'Receptionist'**
  String get roleReceptionist;

  /// No description provided for @roomNumber.
  ///
  /// In en, this message translates to:
  /// **'Room {room}'**
  String roomNumber(String room);

  /// No description provided for @route.
  ///
  /// In en, this message translates to:
  /// **'Route'**
  String get route;

  /// No description provided for @saveNote.
  ///
  /// In en, this message translates to:
  /// **'Save note'**
  String get saveNote;

  /// No description provided for @saveNoteDraft.
  ///
  /// In en, this message translates to:
  /// **'Save note as draft'**
  String get saveNoteDraft;

  /// No description provided for @saveVitals.
  ///
  /// In en, this message translates to:
  /// **'Save vitals'**
  String get saveVitals;

  /// No description provided for @scheduledFor.
  ///
  /// In en, this message translates to:
  /// **'Scheduled for'**
  String get scheduledFor;

  /// No description provided for @searchByNameOrCity.
  ///
  /// In en, this message translates to:
  /// **'Search by name or city'**
  String get searchByNameOrCity;

  /// No description provided for @searchHospitals.
  ///
  /// In en, this message translates to:
  /// **'Search hospitals'**
  String get searchHospitals;

  /// No description provided for @searchMedicinesHint.
  ///
  /// In en, this message translates to:
  /// **'Search medicines by name'**
  String get searchMedicinesHint;

  /// No description provided for @searchPages.
  ///
  /// In en, this message translates to:
  /// **'Search pages'**
  String get searchPages;

  /// No description provided for @searchPatientName.
  ///
  /// In en, this message translates to:
  /// **'Search by patient name'**
  String get searchPatientName;

  /// No description provided for @searchPatientsHint.
  ///
  /// In en, this message translates to:
  /// **'Name, mobile number or UHID'**
  String get searchPatientsHint;

  /// No description provided for @searchPrescriptionsHint.
  ///
  /// In en, this message translates to:
  /// **'RX number, patient name or UHID'**
  String get searchPrescriptionsHint;

  /// No description provided for @searchWardPatients.
  ///
  /// In en, this message translates to:
  /// **'Search by name, ward or bed'**
  String get searchWardPatients;

  /// No description provided for @selectDoctor.
  ///
  /// In en, this message translates to:
  /// **'Select doctor'**
  String get selectDoctor;

  /// No description provided for @selectHospital.
  ///
  /// In en, this message translates to:
  /// **'Select hospital'**
  String get selectHospital;

  /// No description provided for @selectHospitalForDashboard.
  ///
  /// In en, this message translates to:
  /// **'Select a hospital from the header to see its dashboard.'**
  String get selectHospitalForDashboard;

  /// No description provided for @selectHospitalTitle.
  ///
  /// In en, this message translates to:
  /// **'Select Hospital'**
  String get selectHospitalTitle;

  /// No description provided for @selectedHospital.
  ///
  /// In en, this message translates to:
  /// **'Selected hospital'**
  String get selectedHospital;

  /// No description provided for @sendEmailOtp.
  ///
  /// In en, this message translates to:
  /// **'Send Email OTP'**
  String get sendEmailOtp;

  /// No description provided for @sendOtp.
  ///
  /// In en, this message translates to:
  /// **'Send OTP'**
  String get sendOtp;

  /// No description provided for @sendResetCode.
  ///
  /// In en, this message translates to:
  /// **'Send reset code'**
  String get sendResetCode;

  /// No description provided for @serverConnection.
  ///
  /// In en, this message translates to:
  /// **'Server connection'**
  String get serverConnection;

  /// No description provided for @serverConnectionText.
  ///
  /// In en, this message translates to:
  /// **'Check that this device can reach the hospital server.'**
  String get serverConnectionText;

  /// No description provided for @sessionEndedNotice.
  ///
  /// In en, this message translates to:
  /// **'Your session has ended. Please sign in again.'**
  String get sessionEndedNotice;

  /// No description provided for @setNewPassword.
  ///
  /// In en, this message translates to:
  /// **'Set new password'**
  String get setNewPassword;

  /// No description provided for @settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// No description provided for @shiftEvening.
  ///
  /// In en, this message translates to:
  /// **'Evening'**
  String get shiftEvening;

  /// No description provided for @shiftMorning.
  ///
  /// In en, this message translates to:
  /// **'Morning'**
  String get shiftMorning;

  /// No description provided for @shiftNight.
  ///
  /// In en, this message translates to:
  /// **'Night'**
  String get shiftNight;

  /// No description provided for @showingFirstOf.
  ///
  /// In en, this message translates to:
  /// **'Showing the first {shown} of {total}. Search to narrow the list.'**
  String showingFirstOf(int shown, int total);

  /// No description provided for @signIn.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get signIn;

  /// No description provided for @signInMethod.
  ///
  /// In en, this message translates to:
  /// **'Sign-in method'**
  String get signInMethod;

  /// No description provided for @signInRequired.
  ///
  /// In en, this message translates to:
  /// **'Sign-in required'**
  String get signInRequired;

  /// No description provided for @signInTitle.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get signInTitle;

  /// No description provided for @signInToOpen.
  ///
  /// In en, this message translates to:
  /// **'Sign in with a staff account that may open {module}.'**
  String signInToOpen(String module);

  /// No description provided for @signInToSee.
  ///
  /// In en, this message translates to:
  /// **'Sign in to see'**
  String get signInToSee;

  /// No description provided for @signInUnavailableBody.
  ///
  /// In en, this message translates to:
  /// **'Staff and patient sign-in come with the next app update. Until then, use the web app to sign in.'**
  String get signInUnavailableBody;

  /// No description provided for @signInUnavailableTitle.
  ///
  /// In en, this message translates to:
  /// **'Sign-in is not in this app version yet'**
  String get signInUnavailableTitle;

  /// No description provided for @signOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get signOut;

  /// No description provided for @signOutDevice.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get signOutDevice;

  /// No description provided for @signOutDeviceConfirm.
  ///
  /// In en, this message translates to:
  /// **'Sign this device out?'**
  String get signOutDeviceConfirm;

  /// No description provided for @signOutEverywhere.
  ///
  /// In en, this message translates to:
  /// **'Sign out everywhere'**
  String get signOutEverywhere;

  /// No description provided for @signOutEverywhereConfirm.
  ///
  /// In en, this message translates to:
  /// **'Sign out of every device, including this one?'**
  String get signOutEverywhereConfirm;

  /// No description provided for @signRecord.
  ///
  /// In en, this message translates to:
  /// **'Sign'**
  String get signRecord;

  /// No description provided for @signRecordBody.
  ///
  /// In en, this message translates to:
  /// **'A signed record is final. Corrections are added as new records.'**
  String get signRecordBody;

  /// No description provided for @signRecordTitle.
  ///
  /// In en, this message translates to:
  /// **'Sign this record?'**
  String get signRecordTitle;

  /// No description provided for @signedInAs.
  ///
  /// In en, this message translates to:
  /// **'Signed in as {name}'**
  String signedInAs(String name);

  /// No description provided for @signedInDevices.
  ///
  /// In en, this message translates to:
  /// **'Signed-in devices'**
  String get signedInDevices;

  /// No description provided for @signedInDevicesIntro.
  ///
  /// In en, this message translates to:
  /// **'Devices where your account is signed in. Sign out any you don\'t recognise.'**
  String get signedInDevicesIntro;

  /// No description provided for @signedOn.
  ///
  /// In en, this message translates to:
  /// **'Signed {date}'**
  String signedOn(String date);

  /// No description provided for @sixDigitCode.
  ///
  /// In en, this message translates to:
  /// **'6-digit code'**
  String get sixDigitCode;

  /// No description provided for @skipTokenTitle.
  ///
  /// In en, this message translates to:
  /// **'Skip this token?'**
  String get skipTokenTitle;

  /// No description provided for @somePatientDataUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Some of your records could not be loaded.'**
  String get somePatientDataUnavailable;

  /// No description provided for @somethingWentWrong.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong'**
  String get somethingWentWrong;

  /// No description provided for @specialization.
  ///
  /// In en, this message translates to:
  /// **'Specialisation'**
  String get specialization;

  /// No description provided for @staffAccessEnded.
  ///
  /// In en, this message translates to:
  /// **'Access ended'**
  String get staffAccessEnded;

  /// No description provided for @staffIntro.
  ///
  /// In en, this message translates to:
  /// **'Staff with access to this hospital.'**
  String get staffIntro;

  /// No description provided for @staffInvitePending.
  ///
  /// In en, this message translates to:
  /// **'Invite pending'**
  String get staffInvitePending;

  /// No description provided for @staffManagersOnly.
  ///
  /// In en, this message translates to:
  /// **'Only this hospital\'s Admin or Hospital Manager can see the staff list.'**
  String get staffManagersOnly;

  /// No description provided for @staffNone.
  ///
  /// In en, this message translates to:
  /// **'No staff found.'**
  String get staffNone;

  /// No description provided for @staffPortal.
  ///
  /// In en, this message translates to:
  /// **'Staff portal'**
  String get staffPortal;

  /// No description provided for @staffSearch.
  ///
  /// In en, this message translates to:
  /// **'Search staff by name or employee ID'**
  String get staffSearch;

  /// No description provided for @staffSignIn.
  ///
  /// In en, this message translates to:
  /// **'Staff sign in'**
  String get staffSignIn;

  /// No description provided for @staffSignInIntro.
  ///
  /// In en, this message translates to:
  /// **'Use your hospital staff account.'**
  String get staffSignInIntro;

  /// No description provided for @startConsultation.
  ///
  /// In en, this message translates to:
  /// **'Start consultation'**
  String get startConsultation;

  /// No description provided for @startTask.
  ///
  /// In en, this message translates to:
  /// **'Start'**
  String get startTask;

  /// No description provided for @status.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get status;

  /// No description provided for @statusAcknowledged.
  ///
  /// In en, this message translates to:
  /// **'Acknowledged'**
  String get statusAcknowledged;

  /// No description provided for @statusAdmitted.
  ///
  /// In en, this message translates to:
  /// **'Admitted'**
  String get statusAdmitted;

  /// No description provided for @statusCalled.
  ///
  /// In en, this message translates to:
  /// **'Called'**
  String get statusCalled;

  /// No description provided for @statusCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get statusCancelled;

  /// No description provided for @statusCheckedIn.
  ///
  /// In en, this message translates to:
  /// **'Checked in'**
  String get statusCheckedIn;

  /// No description provided for @statusCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get statusCompleted;

  /// No description provided for @statusConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Confirmed'**
  String get statusConfirmed;

  /// No description provided for @statusDeferred.
  ///
  /// In en, this message translates to:
  /// **'Deferred'**
  String get statusDeferred;

  /// No description provided for @statusDischargeInitiated.
  ///
  /// In en, this message translates to:
  /// **'Discharge initiated'**
  String get statusDischargeInitiated;

  /// No description provided for @statusDischarged.
  ///
  /// In en, this message translates to:
  /// **'Discharged'**
  String get statusDischarged;

  /// No description provided for @statusDispensed.
  ///
  /// In en, this message translates to:
  /// **'Dispensed'**
  String get statusDispensed;

  /// No description provided for @statusInConsultation.
  ///
  /// In en, this message translates to:
  /// **'In consultation'**
  String get statusInConsultation;

  /// No description provided for @statusInProgress.
  ///
  /// In en, this message translates to:
  /// **'In progress'**
  String get statusInProgress;

  /// No description provided for @statusNoShow.
  ///
  /// In en, this message translates to:
  /// **'No show'**
  String get statusNoShow;

  /// No description provided for @statusPaid.
  ///
  /// In en, this message translates to:
  /// **'Paid'**
  String get statusPaid;

  /// No description provided for @statusPartiallyDispensed.
  ///
  /// In en, this message translates to:
  /// **'Partly dispensed'**
  String get statusPartiallyDispensed;

  /// No description provided for @statusPartiallyPaid.
  ///
  /// In en, this message translates to:
  /// **'Partly paid'**
  String get statusPartiallyPaid;

  /// No description provided for @statusPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get statusPending;

  /// No description provided for @statusReady.
  ///
  /// In en, this message translates to:
  /// **'Ready'**
  String get statusReady;

  /// No description provided for @statusReleased.
  ///
  /// In en, this message translates to:
  /// **'Released'**
  String get statusReleased;

  /// No description provided for @statusScheduled.
  ///
  /// In en, this message translates to:
  /// **'Scheduled'**
  String get statusScheduled;

  /// No description provided for @statusUnpaid.
  ///
  /// In en, this message translates to:
  /// **'Unpaid'**
  String get statusUnpaid;

  /// No description provided for @statusUrgent.
  ///
  /// In en, this message translates to:
  /// **'Urgent'**
  String get statusUrgent;

  /// No description provided for @statusWaiting.
  ///
  /// In en, this message translates to:
  /// **'Waiting'**
  String get statusWaiting;

  /// No description provided for @stepChooseSlot.
  ///
  /// In en, this message translates to:
  /// **'Choose a slot'**
  String get stepChooseSlot;

  /// No description provided for @stepChooseSlotText.
  ///
  /// In en, this message translates to:
  /// **'Pick a date and an available time.'**
  String get stepChooseSlotText;

  /// No description provided for @stepConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get stepConfirm;

  /// No description provided for @stepConfirmText.
  ///
  /// In en, this message translates to:
  /// **'Sign in to confirm the booking.'**
  String get stepConfirmText;

  /// No description provided for @stepSelectDoctor.
  ///
  /// In en, this message translates to:
  /// **'Select doctor'**
  String get stepSelectDoctor;

  /// No description provided for @stepSelectDoctorText.
  ///
  /// In en, this message translates to:
  /// **'Choose a department and doctor.'**
  String get stepSelectDoctorText;

  /// No description provided for @stepSelectHospitalText.
  ///
  /// In en, this message translates to:
  /// **'Pick where you want to be seen.'**
  String get stepSelectHospitalText;

  /// No description provided for @stockAdjust.
  ///
  /// In en, this message translates to:
  /// **'Adjusted'**
  String get stockAdjust;

  /// No description provided for @stockBatch.
  ///
  /// In en, this message translates to:
  /// **'Stock batch'**
  String get stockBatch;

  /// No description provided for @stockChangedByStore.
  ///
  /// In en, this message translates to:
  /// **'Stock is read-only here. It changes only when medicines are dispensed or received, or when the store (Admin, Hospital Manager or Inventory Staff) corrects it.'**
  String get stockChangedByStore;

  /// No description provided for @stockIn.
  ///
  /// In en, this message translates to:
  /// **'In'**
  String get stockIn;

  /// No description provided for @stockMovements.
  ///
  /// In en, this message translates to:
  /// **'Stock movements'**
  String get stockMovements;

  /// No description provided for @stockOut.
  ///
  /// In en, this message translates to:
  /// **'Out'**
  String get stockOut;

  /// No description provided for @substitute.
  ///
  /// In en, this message translates to:
  /// **'Substitute'**
  String get substitute;

  /// No description provided for @substituteFor.
  ///
  /// In en, this message translates to:
  /// **'instead of {medicine}'**
  String substituteFor(String medicine);

  /// No description provided for @substituteReason.
  ///
  /// In en, this message translates to:
  /// **'Why is a substitute given?'**
  String get substituteReason;

  /// No description provided for @supplier.
  ///
  /// In en, this message translates to:
  /// **'Supplier'**
  String get supplier;

  /// No description provided for @switchingHospitalNote.
  ///
  /// In en, this message translates to:
  /// **'Switching hospital changes every list you see to that hospital\'s records.'**
  String get switchingHospitalNote;

  /// No description provided for @tabEmail.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get tabEmail;

  /// No description provided for @tabFamily.
  ///
  /// In en, this message translates to:
  /// **'Family'**
  String get tabFamily;

  /// No description provided for @tabMobileOtp.
  ///
  /// In en, this message translates to:
  /// **'Mobile OTP'**
  String get tabMobileOtp;

  /// No description provided for @tabTokenId.
  ///
  /// In en, this message translates to:
  /// **'Token / ID'**
  String get tabTokenId;

  /// No description provided for @testDate.
  ///
  /// In en, this message translates to:
  /// **'Test date'**
  String get testDate;

  /// No description provided for @thisDevice.
  ///
  /// In en, this message translates to:
  /// **'This device'**
  String get thisDevice;

  /// No description provided for @tileAppointmentsToday.
  ///
  /// In en, this message translates to:
  /// **'Appointments today'**
  String get tileAppointmentsToday;

  /// No description provided for @tileBedsAvailable.
  ///
  /// In en, this message translates to:
  /// **'Beds available'**
  String get tileBedsAvailable;

  /// No description provided for @tileBillingPending.
  ///
  /// In en, this message translates to:
  /// **'Invoices awaiting payment'**
  String get tileBillingPending;

  /// No description provided for @tileCollectedToday.
  ///
  /// In en, this message translates to:
  /// **'Collected today'**
  String get tileCollectedToday;

  /// No description provided for @tileCurrentAdmissions.
  ///
  /// In en, this message translates to:
  /// **'Current admissions'**
  String get tileCurrentAdmissions;

  /// No description provided for @tileLabCompleted.
  ///
  /// In en, this message translates to:
  /// **'Lab tests completed'**
  String get tileLabCompleted;

  /// No description provided for @tileLabPending.
  ///
  /// In en, this message translates to:
  /// **'Lab tests pending'**
  String get tileLabPending;

  /// No description provided for @tileLabUrgent.
  ///
  /// In en, this message translates to:
  /// **'Urgent lab tests'**
  String get tileLabUrgent;

  /// No description provided for @tilePatientsToday.
  ///
  /// In en, this message translates to:
  /// **'Patients registered today'**
  String get tilePatientsToday;

  /// No description provided for @tileWaitingInQueue.
  ///
  /// In en, this message translates to:
  /// **'Waiting in queue'**
  String get tileWaitingInQueue;

  /// No description provided for @timeLabel.
  ///
  /// In en, this message translates to:
  /// **'Time'**
  String get timeLabel;

  /// No description provided for @toDispense.
  ///
  /// In en, this message translates to:
  /// **'To dispense'**
  String get toDispense;

  /// No description provided for @todayAtAGlance.
  ///
  /// In en, this message translates to:
  /// **'Today at a glance'**
  String get todayAtAGlance;

  /// No description provided for @todaysAppointments.
  ///
  /// In en, this message translates to:
  /// **'Today\'s appointments'**
  String get todaysAppointments;

  /// No description provided for @todaysPatientFlow.
  ///
  /// In en, this message translates to:
  /// **'Today\'s patient flow'**
  String get todaysPatientFlow;

  /// No description provided for @todaysShift.
  ///
  /// In en, this message translates to:
  /// **'Today\'s duty'**
  String get todaysShift;

  /// No description provided for @tokenCalled.
  ///
  /// In en, this message translates to:
  /// **'Your token has been called'**
  String get tokenCalled;

  /// No description provided for @tokenCalledBody.
  ///
  /// In en, this message translates to:
  /// **'Please go to the consultation area now.'**
  String get tokenCalledBody;

  /// No description provided for @tokenIdHint.
  ///
  /// In en, this message translates to:
  /// **'Use the patient ID from registration together with your account password.'**
  String get tokenIdHint;

  /// No description provided for @tokenIdIntro.
  ///
  /// In en, this message translates to:
  /// **'Enter your token number or hospital patient ID'**
  String get tokenIdIntro;

  /// No description provided for @tokenLabel.
  ///
  /// In en, this message translates to:
  /// **'Token'**
  String get tokenLabel;

  /// No description provided for @tokenNext.
  ///
  /// In en, this message translates to:
  /// **'You are next. The doctor will see you shortly.'**
  String get tokenNext;

  /// No description provided for @tokenNumber.
  ///
  /// In en, this message translates to:
  /// **'Token {number}'**
  String tokenNumber(String number);

  /// No description provided for @tokenOrPatientId.
  ///
  /// In en, this message translates to:
  /// **'Token Number / Patient ID'**
  String get tokenOrPatientId;

  /// No description provided for @totalMedicines.
  ///
  /// In en, this message translates to:
  /// **'Medicine batches'**
  String get totalMedicines;

  /// No description provided for @triageCritical.
  ///
  /// In en, this message translates to:
  /// **'Critical'**
  String get triageCritical;

  /// No description provided for @triageEmergency.
  ///
  /// In en, this message translates to:
  /// **'Emergency'**
  String get triageEmergency;

  /// No description provided for @triageNonUrgent.
  ///
  /// In en, this message translates to:
  /// **'Non-urgent'**
  String get triageNonUrgent;

  /// No description provided for @triageSemiUrgent.
  ///
  /// In en, this message translates to:
  /// **'Semi-urgent'**
  String get triageSemiUrgent;

  /// No description provided for @triageUrgent.
  ///
  /// In en, this message translates to:
  /// **'Urgent'**
  String get triageUrgent;

  /// No description provided for @tryAgain.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get tryAgain;

  /// No description provided for @typeModuleName.
  ///
  /// In en, this message translates to:
  /// **'Type a module name…'**
  String get typeModuleName;

  /// No description provided for @typeToSearch.
  ///
  /// In en, this message translates to:
  /// **'Type at least {count} letters to search'**
  String typeToSearch(int count);

  /// No description provided for @unitPrice.
  ///
  /// In en, this message translates to:
  /// **'Unit price'**
  String get unitPrice;

  /// No description provided for @unread.
  ///
  /// In en, this message translates to:
  /// **'Unread'**
  String get unread;

  /// No description provided for @unreadNotifications.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{You have 1 unread notification} other{You have {count} unread notifications}}'**
  String unreadNotifications(int count);

  /// No description provided for @upcomingAppointments.
  ///
  /// In en, this message translates to:
  /// **'Upcoming appointments'**
  String get upcomingAppointments;

  /// No description provided for @useDifferentNumber.
  ///
  /// In en, this message translates to:
  /// **'Use a different number'**
  String get useDifferentNumber;

  /// No description provided for @usernameOrEmail.
  ///
  /// In en, this message translates to:
  /// **'Username or email'**
  String get usernameOrEmail;

  /// No description provided for @verified.
  ///
  /// In en, this message translates to:
  /// **'Verified'**
  String get verified;

  /// No description provided for @verifyAndContinue.
  ///
  /// In en, this message translates to:
  /// **'Verify and continue'**
  String get verifyAndContinue;

  /// No description provided for @verifyAndContinueShort.
  ///
  /// In en, this message translates to:
  /// **'Verify & Continue'**
  String get verifyAndContinueShort;

  /// No description provided for @verifyEmailIntro.
  ///
  /// In en, this message translates to:
  /// **'Enter the code sent to {email}. Then sign in with your email and password.'**
  String verifyEmailIntro(String email);

  /// No description provided for @verifyOtp.
  ///
  /// In en, this message translates to:
  /// **'Verify OTP'**
  String get verifyOtp;

  /// No description provided for @verifyUsingEmail.
  ///
  /// In en, this message translates to:
  /// **'Verify using Email'**
  String get verifyUsingEmail;

  /// No description provided for @verifyYourEmail.
  ///
  /// In en, this message translates to:
  /// **'Verify your email'**
  String get verifyYourEmail;

  /// No description provided for @viewAll.
  ///
  /// In en, this message translates to:
  /// **'View all'**
  String get viewAll;

  /// No description provided for @viewMyAppointments.
  ///
  /// In en, this message translates to:
  /// **'View my appointments'**
  String get viewMyAppointments;

  /// No description provided for @viewProfile.
  ///
  /// In en, this message translates to:
  /// **'View profile'**
  String get viewProfile;

  /// No description provided for @viewingHospital.
  ///
  /// In en, this message translates to:
  /// **'Showing records at {name}'**
  String viewingHospital(String name);

  /// No description provided for @visitClosedReadOnly.
  ///
  /// In en, this message translates to:
  /// **'This visit is closed. Its records are shown read-only.'**
  String get visitClosedReadOnly;

  /// No description provided for @visits.
  ///
  /// In en, this message translates to:
  /// **'Visits'**
  String get visits;

  /// No description provided for @vitalBloodPressure.
  ///
  /// In en, this message translates to:
  /// **'Blood pressure'**
  String get vitalBloodPressure;

  /// No description provided for @vitalBloodSugar.
  ///
  /// In en, this message translates to:
  /// **'Blood sugar'**
  String get vitalBloodSugar;

  /// No description provided for @vitalDiastolic.
  ///
  /// In en, this message translates to:
  /// **'Diastolic BP'**
  String get vitalDiastolic;

  /// No description provided for @vitalHeight.
  ///
  /// In en, this message translates to:
  /// **'Height'**
  String get vitalHeight;

  /// No description provided for @vitalNegative.
  ///
  /// In en, this message translates to:
  /// **'Cannot be negative.'**
  String get vitalNegative;

  /// No description provided for @vitalNotANumber.
  ///
  /// In en, this message translates to:
  /// **'Enter a number.'**
  String get vitalNotANumber;

  /// No description provided for @vitalPainScore.
  ///
  /// In en, this message translates to:
  /// **'Pain score'**
  String get vitalPainScore;

  /// No description provided for @vitalPulse.
  ///
  /// In en, this message translates to:
  /// **'Pulse'**
  String get vitalPulse;

  /// No description provided for @vitalRespiratoryRate.
  ///
  /// In en, this message translates to:
  /// **'Respiratory rate'**
  String get vitalRespiratoryRate;

  /// No description provided for @vitalSpo2.
  ///
  /// In en, this message translates to:
  /// **'SpO₂'**
  String get vitalSpo2;

  /// No description provided for @vitalSystolic.
  ///
  /// In en, this message translates to:
  /// **'Systolic BP'**
  String get vitalSystolic;

  /// No description provided for @vitalTemperature.
  ///
  /// In en, this message translates to:
  /// **'Temperature'**
  String get vitalTemperature;

  /// No description provided for @vitalTooHigh.
  ///
  /// In en, this message translates to:
  /// **'Above the allowed maximum.'**
  String get vitalTooHigh;

  /// No description provided for @vitalTooPrecise.
  ///
  /// In en, this message translates to:
  /// **'Use at most 2 decimal places.'**
  String get vitalTooPrecise;

  /// No description provided for @vitalWeight.
  ///
  /// In en, this message translates to:
  /// **'Weight'**
  String get vitalWeight;

  /// No description provided for @vitalWholeNumber.
  ///
  /// In en, this message translates to:
  /// **'Enter a whole number.'**
  String get vitalWholeNumber;

  /// No description provided for @vitals.
  ///
  /// In en, this message translates to:
  /// **'Vitals'**
  String get vitals;

  /// No description provided for @vitalsSaved.
  ///
  /// In en, this message translates to:
  /// **'Vitals saved by the hospital system.'**
  String get vitalsSaved;

  /// No description provided for @waitingPatients.
  ///
  /// In en, this message translates to:
  /// **'Waiting'**
  String get waitingPatients;

  /// No description provided for @wardAndBed.
  ///
  /// In en, this message translates to:
  /// **'Ward and bed'**
  String get wardAndBed;

  /// No description provided for @wardAttention.
  ///
  /// In en, this message translates to:
  /// **'Needs attention on the ward'**
  String get wardAttention;

  /// No description provided for @wardPatients.
  ///
  /// In en, this message translates to:
  /// **'Ward patients'**
  String get wardPatients;

  /// No description provided for @wardPatientsIntro.
  ///
  /// In en, this message translates to:
  /// **'Patients of your duty today: in your wards, or assigned to you.'**
  String get wardPatientsIntro;

  /// No description provided for @weWillSendCode.
  ///
  /// In en, this message translates to:
  /// **'We\'ll send a 6-digit verification code'**
  String get weWillSendCode;

  /// No description provided for @welcome.
  ///
  /// In en, this message translates to:
  /// **'Welcome'**
  String get welcome;

  /// No description provided for @writeInConsultation.
  ///
  /// In en, this message translates to:
  /// **'Write in a consultation'**
  String get writeInConsultation;

  /// No description provided for @yourMobileNumber.
  ///
  /// In en, this message translates to:
  /// **'Your mobile number'**
  String get yourMobileNumber;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'hi'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'hi':
      return AppLocalizationsHi();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
