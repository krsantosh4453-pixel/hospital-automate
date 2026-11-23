// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get accountFamily => 'Family member (view only)';

  @override
  String get accountPatient => 'Patient';

  @override
  String actingAs(String role) {
    return 'Acting as $role';
  }

  @override
  String get actionAiScribe => 'AI scribe';

  @override
  String get actionBloodStock => 'Blood stock and requests';

  @override
  String get actionCompounding => 'Compounding';

  @override
  String get actionCreateInvoice => 'Create invoice';

  @override
  String get actionDispenseMedicines => 'Dispense medicines';

  @override
  String get actionFindPatient => 'Find a patient';

  @override
  String get actionLabResults => 'Lab results';

  @override
  String get actionLabWorklist => 'Lab worklist';

  @override
  String get actionMedicineStock => 'Medicine stock';

  @override
  String get actionNewAppointment => 'New appointment';

  @override
  String get actionOpenQueue => 'Open queue';

  @override
  String get actionPrescriptions => 'Prescriptions';

  @override
  String get actionRegisterPatient => 'Register patient';

  @override
  String get actionStartConsultation => 'Start consultation';

  @override
  String get actionVitalsNursing => 'Vitals and nursing';

  @override
  String get actionWardBeds => 'Ward and beds';

  @override
  String get addDiagnosis => 'Add diagnosis';

  @override
  String get addMedicine => 'Add medicine';

  @override
  String get addOneMedicine => 'Add at least one medicine.';

  @override
  String get admissionAndVisits => 'Admission and visits';

  @override
  String get admissionReason => 'Reason for admission';

  @override
  String get admitAlreadyActive =>
      'This patient already has an active admission here.';

  @override
  String get admitBed => 'Free bed';

  @override
  String get admitConfirm => 'Confirm admission';

  @override
  String get admitIntro =>
      'Admit this patient under your care. Choose a ward to see its free beds.';

  @override
  String get admitNoBedNow => 'No bed now (allocate later)';

  @override
  String get admitNoFreeBeds =>
      'No free bed in this hospital now. You can admit and allocate a bed later.';

  @override
  String get admitPatient => 'Admit patient';

  @override
  String get admitReason => 'Reason for admission';

  @override
  String get admitReasonRequired => 'Enter the reason for admission.';

  @override
  String get admittedOn => 'Admitted on';

  @override
  String get admittingDoctor => 'Admitting doctor';

  @override
  String get admitWard => 'Ward';

  @override
  String get ageLabel => 'Age';

  @override
  String ageYears(String age) {
    return '$age y';
  }

  @override
  String get aiApprove => 'Approve and save';

  @override
  String get aiApproveBody =>
      'You confirm you have read and corrected every section. It is saved as your clinical note for this visit. No prescription is created.';

  @override
  String get aiApproveTitle => 'Save this draft to the medical record?';

  @override
  String get aiAudioUploaded => 'Audio uploaded';

  @override
  String get aiCnnBlocked => 'Blocked';

  @override
  String get aiCnnBlockedBody =>
      'No validated imaging model, dataset or approved medical use case is set up, so the app makes no image predictions. Any future prediction will need review by a qualified clinician and will never be a diagnosis.';

  @override
  String get aiCnnTitle => 'Image prediction (CNN)';

  @override
  String get aiConsentLabel =>
      'The patient agrees to this consultation being recorded';

  @override
  String get aiConsentRecorded => 'Patient consent recorded';

  @override
  String get aiDraftApproved => 'Approved and saved to the record';

  @override
  String get aiDraftFailed =>
      'The last draft attempt failed. Try again or document manually.';

  @override
  String aiDraftPending(int version) {
    return 'AI draft v$version: pending your review';
  }

  @override
  String get aiDraftRejected => 'Rejected: nothing was saved';

  @override
  String get aiDrafting => 'Clinical draft';

  @override
  String get aiEditHint =>
      'One item per line. Leave it empty if it was not discussed.';

  @override
  String get aiEditSection => 'Edit';

  @override
  String get aiEngineNotConfigured => 'Not configured on this server';

  @override
  String get aiGenerateDraft => 'Generate draft';

  @override
  String get aiIntro =>
      'Drafts that a qualified clinician reviews before anything is saved.';

  @override
  String get aiLangAuto => 'Detect';

  @override
  String get aiLangEn => 'English';

  @override
  String get aiLangHi => 'Hindi';

  @override
  String get aiLangHinglish => 'Hinglish';

  @override
  String get aiMicDenied => 'Microphone permission is needed to record.';

  @override
  String get aiMockDraftWarning =>
      'This draft came from the development mock and cannot be approved into a record.';

  @override
  String get aiMockEngine =>
      'Development mock: its text can never be approved into a record';

  @override
  String get aiNoDraftYet => 'Transcribe the audio, then generate a draft.';

  @override
  String get aiNoSessions => 'No scribe sessions yet';

  @override
  String get aiNoSessionsHint =>
      'Open one of your consultations and choose AI scribe.';

  @override
  String get aiNoTranscriptYet => 'Upload the audio, then transcribe it.';

  @override
  String get aiNotConsultingDoctor =>
      'Only the consulting doctor of this visit can use the scribe.';

  @override
  String get aiNotRecorded => 'Not recorded in this consultation';

  @override
  String get aiNothingRecorded => 'Nothing was recorded. Try again.';

  @override
  String get aiOpenConsultations => 'Open consultations';

  @override
  String get aiProviderUnavailable =>
      'The AI service is not available. Document the consultation manually.';

  @override
  String get aiReadOnly =>
      'You can view this scribe session but not change it.';

  @override
  String get aiRecordAgain => 'Record again';

  @override
  String get aiRecordingNow => 'Recording… speak normally.';

  @override
  String get aiRegenerate => 'New draft';

  @override
  String get aiReject => 'Reject draft';

  @override
  String get aiRejectBody => 'Nothing from it is saved to the record.';

  @override
  String get aiRejectTitle => 'Reject this draft?';

  @override
  String get aiSafetyBody =>
      'Every AI suggestion needs review by a qualified doctor. AI never completes a consultation or writes a prescription.';

  @override
  String get aiSafetyTitle => 'AI output is a draft, not a diagnosis';

  @override
  String get aiSaveSection => 'Save section';

  @override
  String get aiScribeCardTitle => 'Medical scribe';

  @override
  String get aiScribeTitle => 'AI scribe';

  @override
  String get aiSecAllergies => 'Allergies';

  @override
  String get aiSecAssessment => 'Assessment';

  @override
  String get aiSecChiefComplaint => 'Chief complaint';

  @override
  String get aiSecExamination => 'Examination';

  @override
  String get aiSecFollowUp => 'Follow-up';

  @override
  String get aiSecHistory => 'History';

  @override
  String get aiSecInvestigations => 'Investigations';

  @override
  String get aiSecMedications => 'Current medications';

  @override
  String get aiSecPlan => 'Plan';

  @override
  String get aiSecSummary => 'Summary';

  @override
  String get aiSecSymptoms => 'Symptoms';

  @override
  String get aiSecVitals => 'Vital signs';

  @override
  String get aiSessionsTitle => 'Your scribe sessions';

  @override
  String get aiSpeechToText => 'Speech to text';

  @override
  String get aiSpokenLanguage => 'Spoken language';

  @override
  String get aiStartRecording => 'Start recording';

  @override
  String get aiStepApprove => '4. Approve and save';

  @override
  String get aiStepDraft => '3. Review and edit the draft';

  @override
  String get aiStepRecord => '1. Record the consultation';

  @override
  String get aiStepTranscript => '2. Review the transcript';

  @override
  String get aiStopRecording => 'Stop and upload';

  @override
  String get aiTitle => 'AI assist';

  @override
  String get aiTranscribe => 'Transcribe';

  @override
  String get aiTranscriptFailed =>
      'Transcription failed. Try again or document manually.';

  @override
  String get aiWorking =>
      'Working on it… this can take up to a minute. You can leave this page; the result is saved.';

  @override
  String get allergiesTitle => 'Allergies';

  @override
  String get allergyAdd => 'Add allergy';

  @override
  String get allergyCategory => 'Type';

  @override
  String get allergyCategoryDrug => 'Drug';

  @override
  String get allergyCategoryEnvironmental => 'Environmental';

  @override
  String get allergyCategoryFood => 'Food';

  @override
  String get allergyCategoryOther => 'Other';

  @override
  String get allergyMarkNone => 'Record: no known allergies';

  @override
  String get allergyMarkUnknown => 'Record: not known';

  @override
  String get allergyName => 'Allergic to (medicine, food…)';

  @override
  String get allergyNameRequired => 'Enter what the patient is allergic to.';

  @override
  String get allergyNoneBlocked =>
      'An allergy is on record, so no known allergies cannot be recorded.';

  @override
  String get allergyReaction => 'Reaction';

  @override
  String get allergySeverity => 'Severity';

  @override
  String get allergyStatusNone => 'No known allergies';

  @override
  String get allergyStatusRecorded => 'Has allergies';

  @override
  String get allergyStatusUnknown => 'Not known (not asked yet)';

  @override
  String get alreadyDispensed =>
      'This prescription has already been dispensed.';

  @override
  String get amountPaid => 'Paid';

  @override
  String get anotherDoctorsVisit =>
      'This is another doctor\'s visit. You can read it but not add to it.';

  @override
  String get appName => 'HMS';

  @override
  String get appSettingsIntro => 'Settings for this device.';

  @override
  String get appSubtitle => 'Hospital Management';

  @override
  String get appointmentChangesAtHospital =>
      'To cancel or change an appointment, please contact the hospital reception.';

  @override
  String get appointmentDetails => 'Appointment details';

  @override
  String get appointmentId => 'Appointment ID';

  @override
  String get appointmentStatus => 'Appointment status';

  @override
  String get appointmentsIntro => 'Your bookings at the selected hospital.';

  @override
  String assignedForShift(String shift) {
    return 'Assigned to you · $shift';
  }

  @override
  String get assignedToMe => 'Assigned to me';

  @override
  String get atLeast8Characters => 'At least 8 characters.';

  @override
  String atMost(int count) {
    return 'At most $count';
  }

  @override
  String attentionBilling(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count invoices awaiting payment',
      one: '1 invoice awaiting payment',
    );
    return '$_temp0';
  }

  @override
  String attentionEmergency(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count active emergency cases',
      one: '1 active emergency case',
    );
    return '$_temp0';
  }

  @override
  String attentionLabPending(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count lab tests pending',
      one: '1 lab test pending',
    );
    return '$_temp0';
  }

  @override
  String attentionQueue(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count patients waiting in the queue',
      one: '1 patient waiting in the queue',
    );
    return '$_temp0';
  }

  @override
  String attentionUrgentLab(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count urgent lab tests',
      one: '1 urgent lab test',
    );
    return '$_temp0';
  }

  @override
  String get authAccountDisabled =>
      'This account is disabled. Contact your hospital administrator.';

  @override
  String get authChallengeExpired =>
      'Your sign-in step expired. Enter your password again.';

  @override
  String get authDobRequired => 'Enter your date of birth.';

  @override
  String get authHospitalRequired =>
      'Choose the hospital you want to register at.';

  @override
  String get authRegistrationUnavailable =>
      'We could not create an account with these details. If you already have an account, sign in or reset your password.';

  @override
  String get authEmailNotVerified =>
      'Your email is not verified yet. Send an email OTP to verify it.';

  @override
  String get authEmailSendFailed =>
      'The verification email could not be sent. Try again later.';

  @override
  String get authFamilyNotAvailable =>
      'This family access is not available for your mobile number.';

  @override
  String get authFamilyTicketExpired =>
      'Your sign-in has expired. Request a new code.';

  @override
  String get authFieldsRequired => 'Enter your username or email and password.';

  @override
  String get authGoogleFailed =>
      'Google sign-in failed. Try again, or use another sign-in method.';

  @override
  String get authGoogleNotSetUp =>
      'Google sign-in is not set up for this app yet. Use another sign-in method.';

  @override
  String get authInvalidCredentials =>
      'The username, email or password is not correct.';

  @override
  String get authInvalidDob => 'The date of birth is not valid.';

  @override
  String get authInvalidEmail => 'Enter a valid email address.';

  @override
  String get authInvalidOtp => 'The code is not correct.';

  @override
  String get authInvalidPhone => 'Enter a valid 10-digit mobile number.';

  @override
  String get authLockedOut =>
      'Too many failed sign-in attempts. Try again in 15 minutes or reset your password.';

  @override
  String get authNameRequired => 'Enter your full name.';

  @override
  String get authNotAllowed => 'This sign-in is not allowed for this account.';

  @override
  String get authNotStaff =>
      'This account is not an active staff account. Patients sign in on the patient portal.';

  @override
  String get authOtpCooldown =>
      'Please wait a minute before asking for another code.';

  @override
  String get authOtpExpired => 'The code has expired. Ask for a new one.';

  @override
  String get authOtpLocked =>
      'Too many wrong codes. Sign in again in 15 minutes.';

  @override
  String get authOtpRequiredUnavailable =>
      'This server requires an SMS code, but SMS is not set up. Contact your hospital administrator.';

  @override
  String get authPasswordMismatch =>
      'Password and confirm password do not match.';

  @override
  String get authPasswordRejected =>
      'This password was not accepted. Choose a longer, less common password.';

  @override
  String get authPasswordTooShort => 'Password must be at least 8 characters.';

  @override
  String get authResetCodeInvalid => 'The code is not correct or has expired.';

  @override
  String get authResetUnavailable =>
      'Password reset by SMS is not set up on this server. Contact your hospital administrator.';

  @override
  String get authSmsUnavailable =>
      'SMS codes are not set up on this server. Use another sign-in method or contact the hospital.';

  @override
  String get authStaffInviteOnly =>
      'Staff accounts are created by your hospital. Ask its administrator for an invitation.';

  @override
  String get authStaffUseStaffLogin =>
      'Staff accounts sign in on the staff portal.';

  @override
  String get authTooManyRequests =>
      'Too many attempts. Please try again later.';

  @override
  String get authUnsupportedAccount =>
      'This account cannot use the mobile app. Use the web app.';

  @override
  String get authorNotRecorded => 'Author not recorded';

  @override
  String get availabilityDone => 'Fully issued';

  @override
  String get availabilityInStock => 'In stock';

  @override
  String get availabilityNone => 'Not in stock';

  @override
  String get availabilityShort => 'Not enough stock';

  @override
  String get availabilitySplit => 'Needs several batches';

  @override
  String get awaitingBed => 'Awaiting bed';

  @override
  String get awaitingVerification => 'Awaiting verification';

  @override
  String get back => 'Back';

  @override
  String get backToEmailLogin => 'Back to email login';

  @override
  String get backToHome => 'Back to home';

  @override
  String get backToSignIn => 'Back to sign in';

  @override
  String get backend => 'Backend';

  @override
  String get balanceDue => 'Balance due';

  @override
  String get batch => 'Batch';

  @override
  String batchCode(String batch) {
    return 'Batch $batch';
  }

  @override
  String get bedAvailable => 'Available';

  @override
  String get bedCleaning => 'Cleaning';

  @override
  String get bedMaintenance => 'Maintenance';

  @override
  String bedNumber(String bed) {
    return 'Bed $bed';
  }

  @override
  String get bedOccupied => 'Occupied';

  @override
  String get bedReserved => 'Reserved';

  @override
  String bedsOccupiedOf(String occupied, String total) {
    return '$occupied occupied of $total';
  }

  @override
  String get billDate => 'Bill date';

  @override
  String get billTotal => 'Total';

  @override
  String get billingAmount => 'Amount';

  @override
  String get billingAmountInvalid =>
      'Enter an amount in rupees, like 500 or 499.50.';

  @override
  String get billingAmountRefused =>
      'The hospital system did not accept this amount. Check the balance and try again.';

  @override
  String billingAmountTooHigh(String limit) {
    return 'The amount is more than the balance due ($limit).';
  }

  @override
  String get billingAnyDate => 'Any date';

  @override
  String get billingBackToDesk => 'Back to billing';

  @override
  String get billingBackToInvoice => 'Back to invoice';

  @override
  String get billingChargeConsultation => 'Consultation';

  @override
  String get billingChargeLaboratory => 'Laboratory';

  @override
  String get billingChargeOther => 'Other charge';

  @override
  String get billingChargePharmacy => 'Pharmacy';

  @override
  String get billingChoosePatient =>
      'Choose the patient by searching their name, phone or UHID.';

  @override
  String get billingClearDates => 'Clear dates';

  @override
  String billingConfirmPayment(
    String amount,
    String method,
    String invoice,
    String patient,
  ) {
    return 'Record $amount received by $method for invoice $invoice ($patient)? This records money already received at the desk; it does not charge anyone.';
  }

  @override
  String get billingConfirmPaymentTitle => 'Record this payment?';

  @override
  String billingConfirmRefund(String amount, String method, String invoice) {
    return 'Record a refund of $amount by $method on invoice $invoice? A refund cannot be edited or deleted later.';
  }

  @override
  String get billingConfirmRefundTitle => 'Record this refund?';

  @override
  String get billingCountsUnavailable => 'Billing figures could not be loaded';

  @override
  String get billingCreateInvoice => 'Create invoice';

  @override
  String get billingCreateNotAllowed =>
      'Your role at this hospital cannot create invoices.';

  @override
  String get billingDeskIntro =>
      'Invoices and payments of the selected hospital. Totals and balances come from the hospital system.';

  @override
  String get billingDiscount => 'Discount';

  @override
  String get billingDiscountHint =>
      'Taken off before GST, as the hospital system calculates it.';

  @override
  String get billingDiscountRefused =>
      'The discount cannot be negative or more than the bill before tax.';

  @override
  String billingDue(String amount) {
    return 'Due $amount';
  }

  @override
  String get billingFromPharmacy => 'from pharmacy';

  @override
  String get billingGstPercent => 'GST %';

  @override
  String billingGstRate(String rate) {
    return 'GST $rate%';
  }

  @override
  String get billingInvoiceClosed =>
      'This invoice is cancelled or closed, so no money can be recorded on it.';

  @override
  String get billingInvoiceMaybeCreated =>
      'No answer came from the hospital system, so the invoice may have been created. Check the invoice list before creating it again.';

  @override
  String get billingInvoiceTitle => 'Invoice';

  @override
  String get billingInvoices => 'Invoices';

  @override
  String get billingItems => 'Items';

  @override
  String get billingKeyReused =>
      'This request was already used for another record. Go back to the invoice and start again.';

  @override
  String billingLatestRecords(int count) {
    return 'Latest $count records';
  }

  @override
  String get billingLineDescription => 'Description';

  @override
  String get billingLineDescriptionRequired => 'Describe the charge.';

  @override
  String billingLineNumber(int number) {
    return 'Item $number';
  }

  @override
  String get billingNetOfRefunds => 'After refunds';

  @override
  String get billingNewInvoice => 'New invoice';

  @override
  String get billingNewInvoiceIntro =>
      'Choose the patient and add the charges. The hospital system works out tax, the total and the invoice number.';

  @override
  String get billingNoGateway => 'Payments are recorded at the desk';

  @override
  String get billingNoGatewayBody =>
      'There is no online payment gateway. Record cash, UPI, card or bank transfer only after the money has been received. Nothing here is pending or failed: every record is a confirmed receipt.';

  @override
  String get billingNoInvoicesMatch => 'No invoices match these filters';

  @override
  String get billingNoItems => 'This invoice has no items.';

  @override
  String get billingOpenInvoiceList => 'Open invoice list';

  @override
  String get billingPatientSearchHint =>
      'Search patient by name, phone or UHID';

  @override
  String get billingPaymentIntro =>
      'Money received at the desk against this invoice.';

  @override
  String get billingPaymentKind => 'Payment';

  @override
  String get billingPaymentMethod => 'Payment method';

  @override
  String get billingPaymentNotAllowed =>
      'A payment cannot be recorded on this invoice by your role.';

  @override
  String get billingPaymentRecorded =>
      'Payment recorded by the hospital system';

  @override
  String get billingPayments => 'Payments';

  @override
  String get billingPaymentsRecorded => 'Payments recorded';

  @override
  String get billingPharmacyAutomatic =>
      'Medicines sold by the pharmacy are billed automatically, so they are not added here.';

  @override
  String get billingPrintOnWeb =>
      'Printed bills and PDFs are made from the web app; the hospital system has no invoice PDF for the phone.';

  @override
  String get billingQuantityInvalid =>
      'Quantity must be a whole number of at least 1.';

  @override
  String get billingReceipt => 'Receipt number';

  @override
  String get billingRecordPayment => 'Record payment';

  @override
  String get billingRecordRefund => 'Record refund';

  @override
  String get billingReference => 'Transaction reference';

  @override
  String get billingReferenceHint =>
      'UPI transaction ID, card slip or transfer number. Never a card number, CVV or PIN.';

  @override
  String get billingRefundIntro =>
      'Money paid back to the patient on this invoice.';

  @override
  String get billingRefundNotAllowed =>
      'A refund cannot be recorded on this invoice by your role.';

  @override
  String get billingRefundReason => 'Reason for the refund';

  @override
  String get billingRefundReasonRequired => 'Give the reason for the refund.';

  @override
  String get billingRefundRecorded => 'Refund recorded by the hospital system';

  @override
  String billingRefundTooHigh(String limit) {
    return 'A refund cannot be more than the amount received ($limit).';
  }

  @override
  String get billingRefunds => 'Refunds';

  @override
  String get billingRefused =>
      'The hospital system did not accept this. Refresh and try again.';

  @override
  String get billingRemoveLine => 'Remove item';

  @override
  String get billingSearchHint => 'Search invoice number, patient or UHID';

  @override
  String get billingServerTotals =>
      'Tax, the total and the invoice number are calculated by the hospital system when you create the invoice.';

  @override
  String get billingSubtotal => 'Subtotal';

  @override
  String get billingTax => 'Tax (GST)';

  @override
  String get billingTaxRateInvalid => 'GST must be between 0 and 100 percent.';

  @override
  String get billingTotalInvoices => 'Invoices';

  @override
  String get billingUnitPrice => 'Unit price';

  @override
  String get billsIntro => 'Invoices and the payments recorded against them.';

  @override
  String get billsWithBalance => 'Bills with balance due';

  @override
  String get bmi => 'BMI';

  @override
  String get bmiByServer =>
      'BMI is calculated by the hospital system from weight (kg) and height (cm): kg ÷ m².';

  @override
  String get bookAppointment => 'Book appointment';

  @override
  String get bookAppointmentIntro => 'Choose a doctor, a date and a free time.';

  @override
  String get bookingConfirmed => 'Appointment booked';

  @override
  String get bookingConfirmedBody =>
      'The hospital has recorded your booking. Please arrive a little before your time.';

  @override
  String get bookingDateInvalid =>
      'This date cannot be booked. Choose a date within the booking window.';

  @override
  String get bookingDoctorUnavailable =>
      'This doctor is not taking online bookings. Choose another doctor.';

  @override
  String get bookingLimitReached =>
      'You already have the most upcoming appointments allowed. Attend or cancel one at the hospital first.';

  @override
  String get bookingNoHospital =>
      'You are not registered at any hospital yet. Please register at the reception first.';

  @override
  String get bookingRejected =>
      'The hospital could not accept this booking. Check the details and try again.';

  @override
  String get bookingSlotTaken =>
      'This time was just booked by someone else. Please choose another time.';

  @override
  String get bookingSlotUnavailable =>
      'This time is no longer available. Please choose another time.';

  @override
  String get bpNeedsBoth =>
      'Enter both systolic and diastolic blood pressure, or neither.';

  @override
  String get calledPatients => 'Called';

  @override
  String get cancel => 'Cancel';

  @override
  String get careTasks => 'Care tasks';

  @override
  String get category => 'Category';

  @override
  String get changeNumber => 'Change number';

  @override
  String chargedOnBill(String invoice, String total) {
    return 'Charged on bill $invoice ($total).';
  }

  @override
  String get checkAgain => 'Check again';

  @override
  String get checkAndSavePrescription => 'Check safety and save prescription';

  @override
  String get checkDispenseLines => 'Check these lines before dispensing';

  @override
  String get checkPatientBeforeDose =>
      'Check the patient\'s name and ID, the medicine, dose and route against the patient before you confirm.';

  @override
  String checkTheseFields(String fields) {
    return 'Please check: $fields';
  }

  @override
  String get checking => 'Checking…';

  @override
  String get checkingConnection => 'Checking connection…';

  @override
  String get chooseDateOfBirth => 'Choose date of birth';

  @override
  String get chooseDoctorFirst => 'Choose a doctor to see free times.';

  @override
  String get clinicalHistory => 'Clinical history';

  @override
  String get clinicalNotes => 'Clinical notes';

  @override
  String get close => 'Close';

  @override
  String get closeNavigation => 'Close navigation';

  @override
  String get codeFromSms => 'Code from SMS';

  @override
  String get codeResent => 'A new code was sent.';

  @override
  String codeSentToMobile(String maskedPhone) {
    return 'We sent a 6-digit code to your mobile ($maskedPhone).';
  }

  @override
  String get collapseSidebar => 'Collapse sidebar';

  @override
  String get comments => 'Comments';

  @override
  String get completeConsultation => 'Complete consultation';

  @override
  String get completeConsultationBody =>
      'The visit will be marked Completed. Records already saved stay as they are.';

  @override
  String get completeConsultationTitle => 'Complete this consultation?';

  @override
  String get completeTask => 'Complete';

  @override
  String get completeTaskTitle => 'Mark this task complete?';

  @override
  String get completedToday => 'Completed today';

  @override
  String get confirm => 'Confirm';

  @override
  String get confirmBooking => 'Confirm booking';

  @override
  String get confirmDispenseTitle => 'Dispense these medicines?';

  @override
  String get confirmGiveTitle => 'Record this dose as given?';

  @override
  String get confirmHoldTitle => 'Hold this dose?';

  @override
  String get confirmMissedTitle => 'Record this dose as missed?';

  @override
  String get confirmPassword => 'Confirm password';

  @override
  String get confirmRefuseTitle => 'Record that the patient refused this dose?';

  @override
  String get consultationIntro =>
      'Your visits. Open one to record vitals, notes, diagnoses, prescriptions and lab orders.';

  @override
  String get consultationQueueHint =>
      'Queue tokens are moved on the Queue page.';

  @override
  String get continueAction => 'Continue';

  @override
  String get continueSaving => 'Continue and save';

  @override
  String get continueWithGoogle => 'Continue with Google';

  @override
  String countPending(String count) {
    return '$count pending';
  }

  @override
  String get createAccount => 'Create Account';

  @override
  String get currentPrescriptions => 'Current prescriptions';

  @override
  String get dashboardLoadFailed => 'Dashboard figures could not be loaded';

  @override
  String get date => 'Date';

  @override
  String get dateOfBirth => 'Date of birth';

  @override
  String get department => 'Department';

  @override
  String get departments => 'Departments';

  @override
  String get departmentsIntro =>
      'Work in each department opens after the right staff member signs in.';

  @override
  String get deptAppointmentsText => 'Bookings and the daily schedule.';

  @override
  String get deptBillingText => 'Invoices and payments.';

  @override
  String get deptBloodBank => 'Blood bank';

  @override
  String get deptBloodBankText => 'Blood stock and requests.';

  @override
  String get deptConsultationText => 'Doctors\' clinical work.';

  @override
  String get deptDescription => 'Description';

  @override
  String get deptEmergencyText => 'Triage and emergency care.';

  @override
  String get deptHead => 'Head of department';

  @override
  String get deptIntro => 'Departments of this hospital.';

  @override
  String get deptInventoryText => 'Store, suppliers and purchase orders.';

  @override
  String get deptLaboratoryText => 'Samples, results and reports.';

  @override
  String get deptNone => 'No departments set up yet.';

  @override
  String get deptNursing => 'Nursing';

  @override
  String get deptNursingText => 'Vitals, nursing notes and medication rounds.';

  @override
  String get deptPatientsText => 'Registration and patient records.';

  @override
  String get deptPharmacyText => 'Dispensing and medicine stock.';

  @override
  String get deptQueue => 'OPD queue';

  @override
  String get deptQueueText => 'Tokens and consultation flow.';

  @override
  String get deptReportsText => 'Hospital statistics.';

  @override
  String get deptWards => 'Wards and beds';

  @override
  String get deptWardsText => 'Admissions, beds and discharge.';

  @override
  String get diagnoses => 'Diagnoses';

  @override
  String get diagnosisName => 'Diagnosis';

  @override
  String get diagnosisNameRequired => 'Enter the diagnosis.';

  @override
  String get diagnosisType => 'Type';

  @override
  String get dischargeCondition => 'Condition at discharge';

  @override
  String get dischargeFinalDiagnosis => 'Final diagnosis';

  @override
  String get dischargeFinalize => 'Finalise summary';

  @override
  String get dischargeFinalizeBody =>
      'After this the summary cannot be changed, and the patient sees it in their history.';

  @override
  String get dischargeFinalizeTitle => 'Finalise the discharge summary?';

  @override
  String get dischargeFollowUp => 'Follow-up instructions';

  @override
  String get dischargeMedications => 'Discharge medications';

  @override
  String get dischargeNotes => 'Hospital course and other notes';

  @override
  String get dischargePlanTitle => 'Discharge plan';

  @override
  String get dischargeSaved => 'Saved by the hospital system.';

  @override
  String get dischargeSavePlan => 'Save plan';

  @override
  String get dischargeSaveSummary => 'Save summary draft';

  @override
  String get dischargeSummaryFinalized =>
      'Finalised by a doctor. It can no longer be changed.';

  @override
  String get dischargeSummaryRequired =>
      'Enter the final diagnosis and the condition at discharge.';

  @override
  String get dischargeSummaryTitle => 'Write the discharge summary';

  @override
  String get dispense => 'Dispense';

  @override
  String dispenseNoBatch(String medicine) {
    return '$medicine: choose a stock batch';
  }

  @override
  String dispenseNoReason(String medicine) {
    return '$medicine: give the reason for the substitute';
  }

  @override
  String get dispenseNothingChosen =>
      'Enter a quantity for at least one medicine.';

  @override
  String get dispenseOutcomeUnknown =>
      'The hospital system could not be reached, so it is not known whether the medicines were issued. The prescription has been reloaded: check the dispensing history before trying again.';

  @override
  String get dispenseRefused =>
      'The hospital system refused this dispense (stock, quantity, expiry or substitute check). Nothing was issued; the stock has been reloaded.';

  @override
  String dispenseTooMany(String medicine, int count) {
    return '$medicine: at most $count can still be issued';
  }

  @override
  String get dispensedInFull =>
      'Dispensed in full. Stock was updated by the hospital system.';

  @override
  String get dispensedInPart =>
      'Part of the prescription was dispensed; the rest can be given later.';

  @override
  String get dispensingHistory => 'Dispensing history';

  @override
  String get doctor => 'Doctor';

  @override
  String get doctorAppointmentsIntro =>
      'Bookings with you at the selected hospital.';

  @override
  String get doctorLabIntro =>
      'Lab tests of patients in your care. Values appear once the laboratory releases them.';

  @override
  String get doctorPatientsIntro =>
      'Find a patient in your care by name, mobile number or UHID.';

  @override
  String get doctorPrescriptionsIntro =>
      'Prescriptions of patients in your care.';

  @override
  String get doctorProfileMissing =>
      'No doctor profile is linked to your account at this hospital. Ask the hospital Admin.';

  @override
  String get doctorQueueIntro =>
      'Today\'s patients for you. This page checks again every 30 seconds while it is open.';

  @override
  String get documentsIntro => 'Documents the hospital has shared with you.';

  @override
  String get documentsViewOnWeb =>
      'Opening files in the app is not available yet. Use the patient portal on the web to open them.';

  @override
  String get dosage => 'Dosage';

  @override
  String get doseDue => 'Due';

  @override
  String doseDueAt(String time) {
    return 'Due $time';
  }

  @override
  String get doseExcluded => 'Excluded by doctor';

  @override
  String get doseGiven => 'Given';

  @override
  String get doseHeld => 'Held';

  @override
  String get doseMissed => 'Missed';

  @override
  String get doseNotRecorded =>
      'This dose was not recorded: it was already recorded (perhaps by another nurse) or the doctor\'s order is no longer in force. The list has been refreshed.';

  @override
  String get doseOutcomeUnknown =>
      'The hospital system could not be reached, so it is not known whether the dose was recorded. The list has been refreshed: check it before trying again.';

  @override
  String doseOverdueAt(String time) {
    return 'Overdue since $time';
  }

  @override
  String doseRecorded(String medicine, String status, String time) {
    return '$medicine: $status at $time, confirmed by the hospital system.';
  }

  @override
  String get doseRefused => 'Refused';

  @override
  String get doseVomited => 'Vomited';

  @override
  String get dosesDue => 'Doses due';

  @override
  String get dosesOverdue => 'Overdue';

  @override
  String get draft => 'Draft';

  @override
  String get drugSchedule => 'Drug schedule';

  @override
  String get duration => 'Duration';

  @override
  String get email => 'Email';

  @override
  String get emailCodeNotSent =>
      'The verification email could not be sent. Ask the hospital to check its email settings.';

  @override
  String get emailCodeSent =>
      'If this email has a patient account, a verification code was sent to it.';

  @override
  String get emailLoginIntro =>
      'Use the email and password from your patient account.';

  @override
  String get emailNotVerifiedSendOtp => 'Email not verified? Send email OTP';

  @override
  String get emailOtpIntro =>
      'We will send a verification code to your registered email.';

  @override
  String get emailVerifiedSignIn =>
      'Email verified. You can now sign in with your email and password.';

  @override
  String get emergencyContact => 'Emergency contact';

  @override
  String get emergencyVisitsToday => 'Emergency visits today';

  @override
  String get enter10DigitNumber => 'Enter 10-digit number';

  @override
  String get enterAtLeastOneVital => 'Enter at least one reading.';

  @override
  String get enterTheCode => 'Enter the code';

  @override
  String get erActiveNow => 'In the ER now';

  @override
  String get erAddNote => 'Add note';

  @override
  String get erAdmitHint =>
      'The server allocates the bed and closes the ER visit as Admitted.';

  @override
  String get erAdmitToIpd => 'Admit to IPD';

  @override
  String get erAdmitted => 'Admission created by the hospital system.';

  @override
  String get erAlreadyAdmitted => 'This patient already has an open admission:';

  @override
  String get erArrival => 'Arrival';

  @override
  String get erAttendingDoctor => 'Attending doctor';

  @override
  String get erBp => 'BP';

  @override
  String get erChiefComplaint => 'Chief complaint';

  @override
  String get erChiefComplaintRequired => 'Enter the chief complaint.';

  @override
  String get erCompleteTriage => 'Complete triage';

  @override
  String get erConsultationStarted => 'Consultation started';

  @override
  String get erDetails => 'Visit details';

  @override
  String get erDischarge => 'Discharge from ER';

  @override
  String get erDischargeDiagnosis => 'Discharge diagnosis';

  @override
  String get erDischargeWarning =>
      'The visit is closed after discharge and cannot be reopened here.';

  @override
  String get erDischarged => 'Discharge saved by the hospital system.';

  @override
  String get erFilterActive => 'Active';

  @override
  String get erFilterClosed => 'Closed';

  @override
  String get erFollowUp => 'Follow-up instructions';

  @override
  String get erGcs => 'Glasgow Coma Scale';

  @override
  String get erGiven => 'Given';

  @override
  String get erIntro =>
      'Patients in the emergency department, most urgent first.';

  @override
  String erKeepDoctor(String name) {
    return 'Keep $name';
  }

  @override
  String get erLeftEr => 'Left the ER';

  @override
  String get erMedicationsSection => 'Medicines';

  @override
  String get erNextSteps => 'Next steps';

  @override
  String get erNoActiveVisits => 'No patients in the emergency department now.';

  @override
  String get erNoDoctorYet => 'No doctor assigned';

  @override
  String get erNoMedications => 'No medicines recorded.';

  @override
  String get erNoNotes => 'No notes yet.';

  @override
  String get erNoOrders => 'No orders.';

  @override
  String get erNoPatientMatch => 'No patient found at this hospital.';

  @override
  String get erNoVisits => 'No emergency visits.';

  @override
  String get erNoVitals => 'No vitals recorded.';

  @override
  String get erNotGiven => 'Not given yet';

  @override
  String get erNotTriaged => 'Not triaged yet.';

  @override
  String get erNote => 'Note';

  @override
  String get erNoteHint => 'Notes are kept permanently and cannot be edited.';

  @override
  String get erNoteRequired => 'Write the note.';

  @override
  String get erNoteSaved => 'Note saved by the hospital system.';

  @override
  String get erNotes => 'Notes';

  @override
  String get erOpenAdmission => 'Open the admission';

  @override
  String get erOrdersSection => 'Orders';

  @override
  String get erPainScore => 'Pain score';

  @override
  String get erReadOnly =>
      'You can view emergency visits. Changes need a doctor or nurse role at this hospital.';

  @override
  String get erRecordVitals => 'Record vitals';

  @override
  String get erRefer => 'Refer out';

  @override
  String get erReferWarning =>
      'The visit is closed after referral and cannot be reopened here.';

  @override
  String get erReferred => 'Referral saved by the hospital system.';

  @override
  String get erReferredTo => 'Referred to (facility)';

  @override
  String get erReferredToRequired => 'Enter where the patient is referred.';

  @override
  String get erRegister => 'Register';

  @override
  String get erRegisterHint =>
      'Only patients already registered at this hospital can be chosen.';

  @override
  String get erRegisterPatient => 'Register ER patient';

  @override
  String get erRegistered =>
      'Emergency visit registered by the hospital system.';

  @override
  String get erRemarks => 'Remarks';

  @override
  String get erRr => 'Resp.';

  @override
  String get erSearchPatient => 'Name, UHID or phone';

  @override
  String get erStartConsultation => 'Start consultation';

  @override
  String get erStartTriage => 'Start triage';

  @override
  String get erStartTriageConfirm => 'Move this patient to triage?';

  @override
  String get erStatusAdmitted => 'Admitted to IPD';

  @override
  String get erStatusDischarged => 'Discharged';

  @override
  String get erStatusExpired => 'Expired';

  @override
  String get erStatusInvestigations => 'Investigations';

  @override
  String get erStatusLeftAgainstAdvice => 'Left against advice';

  @override
  String get erStatusObservation => 'Observation';

  @override
  String get erStatusReferred => 'Referred';

  @override
  String get erStatusRegistered => 'Registered';

  @override
  String get erStatusTreatment => 'Treatment';

  @override
  String get erStatusTriage => 'In triage';

  @override
  String get erStatusUnderConsultation => 'Under consultation';

  @override
  String get erSugar => 'Sugar';

  @override
  String get erTriageLevel => 'Triage level';

  @override
  String get erTriageNotes => 'Triage notes';

  @override
  String get erTriageSection => 'Triage';

  @override
  String get erTriageStarted => 'Triage started';

  @override
  String get erTriagedBy => 'Triaged by';

  @override
  String get erVisitClosed => 'This visit is closed; only notes can be added.';

  @override
  String get erVitalsEmpty => 'Enter at least one reading.';

  @override
  String get erVitalsSection => 'Vitals';

  @override
  String get errorConflict =>
      'This record changed or already exists. Refresh and try again.';

  @override
  String get errorForbidden =>
      'Your role does not have access to this in the selected hospital.';

  @override
  String get errorNetwork =>
      'Cannot reach the server. Check the connection and try again.';

  @override
  String get errorNotFound =>
      'This record was not found in the selected hospital.';

  @override
  String get errorRateLimited =>
      'Too many attempts. Wait a few minutes and try again.';

  @override
  String get errorServer => 'The server had a problem. Try again shortly.';

  @override
  String get errorTimeout => 'The server did not answer in time. Try again.';

  @override
  String get errorUnauthorized =>
      'Your session has ended. Please sign in again.';

  @override
  String get errorUnavailable => 'This service is not set up on the server.';

  @override
  String get errorUnknown => 'Something went wrong. Try again.';

  @override
  String get errorValidation =>
      'Some details are not valid. Check the form and try again.';

  @override
  String get estimatedWait => 'Estimated wait';

  @override
  String estimatedWaitShort(String minutes) {
    return 'about $minutes min (estimate)';
  }

  @override
  String get estimatesAreApproximate =>
      'Wait times are estimates, not appointment times. Please stay nearby so you don\'t miss your call.';

  @override
  String get expandSidebar => 'Expand sidebar';

  @override
  String get expectedAround => 'Expected around';

  @override
  String get expiredInStock => 'Expired';

  @override
  String expiresOn(String date) {
    return 'Expires $date';
  }

  @override
  String expiringSoonCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count batches in stock expire within 30 days',
      one: '1 batch in stock expires within 30 days',
    );
    return '$_temp0';
  }

  @override
  String get expiryDate => 'Expiry date';

  @override
  String get familyChoosePatient => 'Whose records do you want to view?';

  @override
  String familyCodeSentIfAccess(String phone) {
    return 'If $phone has family access, a 6-digit code was sent to it.';
  }

  @override
  String get familyIntro =>
      'View a relative\'s records with the access they gave you. Use your own mobile number. View only: you cannot change anything.';

  @override
  String get familyNoAccessHint =>
      'No access yet? Ask the patient to add you under Consent & Sharing → Family access in their portal.';

  @override
  String get familyTitle => 'Family member or caregiver';

  @override
  String familyYouAre(String relationship) {
    return 'You: $relationship';
  }

  @override
  String get fieldRequired => 'Required';

  @override
  String get filterAll => 'All';

  @override
  String get filterCancelled => 'Cancelled';

  @override
  String get filterPast => 'Past';

  @override
  String get filterToday => 'Today';

  @override
  String get filterUpcoming => 'Upcoming';

  @override
  String finalBillBedCharges(String amount) {
    return 'Bed charges from the price list: $amount';
  }

  @override
  String get finalBillCreate => 'Create final bill';

  @override
  String finalBillDays(String days) {
    return 'Days in hospital: $days';
  }

  @override
  String get finalBillDone => 'Final bill created.';

  @override
  String get finalBillNoBedPrice => 'Bed days cannot be priced yet';

  @override
  String get finalBillNone => 'No stay is waiting for its final bill.';

  @override
  String get finalBillTitle => 'Stays awaiting the final bill';

  @override
  String get fixHighlightedFields => 'Fix the highlighted readings.';

  @override
  String get forgotPassword => 'Forgot password?';

  @override
  String get frequency => 'Frequency';

  @override
  String get fullName => 'Full name';

  @override
  String get gender => 'Gender';

  @override
  String get genderFemale => 'Female';

  @override
  String get genderMale => 'Male';

  @override
  String get genderOther => 'Other';

  @override
  String get goBack => 'Go back';

  @override
  String get goodAfternoon => 'Good afternoon';

  @override
  String get goodEvening => 'Good evening';

  @override
  String get goodMorning => 'Good morning';

  @override
  String greetingWithName(String greeting, String name) {
    return '$greeting, $name';
  }

  @override
  String get groupAdministration => 'Administration';

  @override
  String get groupClinical => 'Clinical care';

  @override
  String get groupDiagnostics => 'Diagnostics & pharmacy';

  @override
  String get groupFrontDesk => 'Front desk';

  @override
  String get groupOperations => 'Finance & operations';

  @override
  String get groupOverview => 'Overview';

  @override
  String get groupPatientPortal => 'My health';

  @override
  String get groupStaff => 'Staff';

  @override
  String get groupSystem => 'System';

  @override
  String get guestBody =>
      'Book an appointment, then sign in to follow your visits, prescriptions, reports and bills.';

  @override
  String get guestEyebrow => 'Hospital services';

  @override
  String get guestTitle => 'Your care, organised in one place';

  @override
  String get haveAccountSignIn => 'Already have an account? Sign in';

  @override
  String get historyAll => 'All';

  @override
  String get historyEmpty => 'Nothing in your history yet.';

  @override
  String get historyIntro =>
      'Visits, diagnoses, prescriptions, reports, vitals, admissions and discharges at your hospitals, newest first.';

  @override
  String get historyTitle => 'My health history';

  @override
  String get hospActive => 'Active';

  @override
  String get hospAddress => 'Address';

  @override
  String get hospCode => 'Code';

  @override
  String get hospCurrent => 'Current';

  @override
  String get hospDepartments => 'Departments';

  @override
  String get hospDoctors => 'Doctors';

  @override
  String get hospEmail => 'Email';

  @override
  String get hospGrievanceOfficer => 'Grievance officer';

  @override
  String get hospInactive => 'Inactive';

  @override
  String get hospIntro => 'The hospital you are working in now.';

  @override
  String get hospitalsUnavailable =>
      'The list of hospitals could not be loaded. Try again.';

  @override
  String get hospNoWards => 'No wards set up yet.';

  @override
  String get hospNurses => 'Nurses';

  @override
  String get hospPhone => 'Phone';

  @override
  String get hospSwitch => 'Switch';

  @override
  String get hospType => 'Type';

  @override
  String get hospWards => 'Wards';

  @override
  String get hospYourHospitals => 'Your hospitals';

  @override
  String get hospital => 'Hospital';

  @override
  String get howBookingWorks => 'How booking works';

  @override
  String get howBookingWorksIntro => 'You can see the steps before signing in.';

  @override
  String get icd10Search => 'Search ICD-10 (optional)';

  @override
  String get inStock => 'In stock';

  @override
  String inStockCount(int count, String unit) {
    return '$count $unit in stock';
  }

  @override
  String get inStockMedicines => 'In stock';

  @override
  String get instructions => 'Instructions';

  @override
  String get interfaceLanguage => 'Interface language';

  @override
  String get invoicesPaidTotal => 'Invoices paid / total';

  @override
  String get ipdAdmitted => 'Admitted';

  @override
  String get ipdAdmittedOn => 'Admitted on';

  @override
  String get ipdAdmittingDoctor => 'Admitting doctor';

  @override
  String get ipdAllocateBed => 'Allocate bed';

  @override
  String get ipdAvailableBeds => 'Free beds';

  @override
  String ipdBedReleased(String bed, String day) {
    return 'Bed $bed · released $day';
  }

  @override
  String get ipdAwaitingBed => 'Waiting for a bed';

  @override
  String get ipdBalanceDue => 'Balance due';

  @override
  String get ipdBedHistory => 'Bed history';

  @override
  String get ipdBedSaved => 'Bed saved by the hospital system.';

  @override
  String get ipdBedTaken =>
      'That bed is no longer free. The list has been refreshed.';

  @override
  String ipdBedsPartial(int count) {
    return 'Showing the first $count beds; the counts may be incomplete.';
  }

  @override
  String get ipdBillDue => 'The final bill still has money due.';

  @override
  String get ipdBillTotal => 'Total';

  @override
  String get ipdCheckCounselled => 'Patient and family counselled';

  @override
  String get ipdCheckDocuments => 'Documents handed over';

  @override
  String get ipdCheckFollowUp => 'Follow-up arranged';

  @override
  String get ipdCheckMedications => 'Medications reconciled';

  @override
  String get ipdChecklist => 'Discharge checklist';

  @override
  String get ipdChooseBed => 'Choose a free bed:';

  @override
  String get ipdCompleteDischarge => 'Complete discharge';

  @override
  String get ipdConfirmComplete =>
      'Complete the discharge? The bed is released and the stay is closed.';

  @override
  String get ipdConfirmInitiate =>
      'Start the discharge? The checklist, summary and final bill must still be finished.';

  @override
  String get ipdCurrentBed => 'Bed';

  @override
  String get ipdDaysBilled => 'Days billed';

  @override
  String get ipdDischarge => 'Discharge';

  @override
  String get ipdDischargeDone => 'Discharge completed by the hospital system.';

  @override
  String get ipdDischargeInitiated => 'Discharge started';

  @override
  String get ipdDischargeReady => 'Ready: every discharge step is done.';

  @override
  String get ipdDischargeStepsOnWeb =>
      'The doctor writes the plan and the summary here; the billing desk creates the final bill.';

  @override
  String get ipdDischarged => 'Discharged';

  @override
  String get ipdDischargedOn => 'Discharged on';

  @override
  String get ipdFilterCurrent => 'In hospital';

  @override
  String get ipdFinalBill => 'Final bill';

  @override
  String get ipdInitiateDischarge => 'Start discharge';

  @override
  String get ipdIntro => 'Admitted patients, their beds and discharges.';

  @override
  String get ipdNoAdmissions => 'No admissions.';

  @override
  String get ipdNoBedHistory => 'No bed allocated yet.';

  @override
  String get ipdNoBeds => 'No beds set up at this hospital.';

  @override
  String get ipdNoFinalBill => 'The final bill has not been created.';

  @override
  String get ipdNoFreeBeds => 'No free beds at this hospital right now.';

  @override
  String get ipdNoPlan => 'No discharge plan written yet.';

  @override
  String get ipdNoSummary => 'No discharge summary written yet.';

  @override
  String get ipdNotStarted => 'Discharge has not been started.';

  @override
  String get ipdReadOnly =>
      'You can view admissions. Bed and discharge changes need a doctor or nurse role at this hospital.';

  @override
  String get ipdReason => 'Reason for admission';

  @override
  String get ipdSince => 'Since';

  @override
  String get ipdStay => 'Stay';

  @override
  String get ipdStillToDo => 'Still to do before discharge';

  @override
  String get ipdSummary => 'Discharge summary';

  @override
  String get ipdSummaryDoctorsOnly =>
      'Only doctors and hospital managers can read discharge summaries.';

  @override
  String get ipdSummaryDraft => 'Draft, not finalised';

  @override
  String get ipdSummaryFinalized => 'Finalised by a doctor';

  @override
  String get ipdSummaryNotFinalized =>
      'A doctor must finalise the discharge summary.';

  @override
  String get ipdTabAdmissions => 'Admissions';

  @override
  String get ipdTabBeds => 'Beds';

  @override
  String get ipdTransferBed => 'Transfer bed';

  @override
  String get ipdTransferred => 'Transferred';

  @override
  String get joinHospital => 'Register at this hospital';

  @override
  String get joinHospitalIntro =>
      'Choose a hospital to register at. It gives you a patient ID (UHID) there, then you can book.';

  @override
  String get jumpTo => 'Jump to…';

  @override
  String get jumpToPage => 'Jump to a page';

  @override
  String get knownCondition => 'Known condition';

  @override
  String get labBackToWorklist => 'Back to worklist';

  @override
  String labCancelConfirm(String test) {
    return 'Cancel the order for $test? It stays in the record as cancelled.';
  }

  @override
  String get labCancelOrder => 'Cancel order';

  @override
  String get labChoosePatient => 'Choose the patient first.';

  @override
  String get labCollectedAt => 'Collected at';

  @override
  String get labCollectedBy => 'Collected by';

  @override
  String get labCollectionNotes => 'Collection notes';

  @override
  String get labCommonTestsNote =>
      'Common tests (names only; the hospital system has no test catalogue with prices):';

  @override
  String get labContainerType => 'Container';

  @override
  String get labCountsUnavailable => 'Laboratory counts could not be loaded';

  @override
  String get labDeskIntro =>
      'Orders of the selected hospital, from sample collection to released result.';

  @override
  String get labDispatchNotes => 'Dispatch notes';

  @override
  String get labDispatchedBy => 'Dispatched by';

  @override
  String get labEnteredAt => 'Entered at';

  @override
  String get labEnteredBy => 'Entered by';

  @override
  String get labExternalLab => 'External laboratory';

  @override
  String get labExternalLabHint =>
      'Leave empty when the sample goes to this hospital\'s laboratory.';

  @override
  String get labFindSample => 'Find a sample';

  @override
  String get labFindSampleHint =>
      'Scan or type a sample number, then press enter';

  @override
  String get labIntro => 'Results released by the laboratory.';

  @override
  String get labNewOrder => 'New lab order';

  @override
  String get labNewOrderIntro =>
      'A walk-in order from the laboratory desk. Doctors order from the consultation, linked to the visit.';

  @override
  String labNextStepByOthers(String step) {
    return 'Next step: $step. Your role at this hospital cannot do it.';
  }

  @override
  String get labNoOrdersMatch => 'No orders match these filters';

  @override
  String get labNoOrdersYet => 'No laboratory orders yet';

  @override
  String get labNoResultYet => 'No result has been entered yet.';

  @override
  String get labNotADiagnosis =>
      'Values are shown as the laboratory entered them. Please discuss them with your doctor.';

  @override
  String get labOpenWorklist => 'Open worklist';

  @override
  String get labOrderCancelled => 'Order cancelled by the hospital system.';

  @override
  String get labOrderMaybeCreated =>
      'No answer came from the hospital system, so the order may have been placed. Check the worklist before ordering again.';

  @override
  String get labOrderNotAllowed =>
      'Your role at this hospital cannot place laboratory orders.';

  @override
  String get labOrderTitle => 'Laboratory order';

  @override
  String get labOrders => 'Lab orders';

  @override
  String get labPatientSearchHint =>
      'Type at least 3 letters of the name, phone or UHID';

  @override
  String get labPlaceOrder => 'Place order';

  @override
  String get labPriorityNormal => 'Normal';

  @override
  String labProgressLabel(int stage, int total) {
    return 'Stage $stage of $total';
  }

  @override
  String get labQueueAwaitingCollection => 'To collect';

  @override
  String get labQueueAwaitingRelease => 'To release';

  @override
  String get labQueueCancelled => 'Cancelled';

  @override
  String get labQueueInProgress => 'In progress';

  @override
  String get labQueueReleased => 'Released';

  @override
  String get labQueueSampleCollected => 'Sample collected';

  @override
  String get labReceivedBy => 'Received by';

  @override
  String labReleaseConfirm(String test) {
    return 'Release the verified result of $test? The doctor and the patient will then see it.';
  }

  @override
  String get labReleasedOnly =>
      'Reports appear here after the laboratory has checked and released them.';

  @override
  String get labResultAwaitingVerification => 'Awaiting verification';

  @override
  String get labResultNotVerifiedYet =>
      'Type the result as the laboratory reports it. It stays unverified until it is verified as a separate step.';

  @override
  String get labResultRequired => 'Enter the result.';

  @override
  String get labResultText => 'Result';

  @override
  String get labResultVerified => 'Verified';

  @override
  String get labReviewOrder => 'Review order';

  @override
  String get labReviewOrderHint =>
      'Check the patient and the test. The order is placed only when the hospital system confirms it.';

  @override
  String get labSample => 'Sample';

  @override
  String get labSampleNumber => 'Sample number';

  @override
  String get labSampleNumberHint =>
      'Scan the label, or leave empty and the hospital system numbers the sample.';

  @override
  String get labSampleType => 'Sample type';

  @override
  String get labSearchHint => 'Search test, patient or sample number';

  @override
  String get labStatusCollected => 'Sample collected';

  @override
  String get labStatusDispatched => 'Dispatched';

  @override
  String get labStatusOrdered => 'Ordered';

  @override
  String get labStatusProcessing => 'Processing';

  @override
  String get labStatusReceived => 'Received in lab';

  @override
  String get labStatusResultEntered => 'Result entered';

  @override
  String get labStatusSamplePending => 'Sample pending';

  @override
  String get labStatusVerified => 'Verified';

  @override
  String get labStepCollect => 'Collect sample';

  @override
  String labStepConfirm(String step, String test) {
    return '$step for $test?';
  }

  @override
  String get labStepDispatch => 'Dispatch sample';

  @override
  String labStepDone(String step) {
    return '$step: saved by the hospital system.';
  }

  @override
  String get labStepEnterResult => 'Enter result';

  @override
  String get labStepReceive => 'Receive in lab';

  @override
  String get labStepRefused =>
      'The hospital system refused this step: the order has probably moved on. It has been reloaded.';

  @override
  String get labStepRelease => 'Release result';

  @override
  String get labStepStartProcessing => 'Start processing';

  @override
  String get labStepVerify => 'Verify result';

  @override
  String get labTestName => 'Test name';

  @override
  String get labTestNameRequired => 'Enter the test name.';

  @override
  String labTestNameTooLong(int max) {
    return 'Use at most $max characters.';
  }

  @override
  String get labTestStatus => 'Lab test status';

  @override
  String get labTimeline => 'Timeline';

  @override
  String get labTotalOrders => 'Lab orders';

  @override
  String get labVerifiedBy => 'Verified by';

  @override
  String get labVerifySameUser =>
      'You entered this result, so a different authorised person must verify it.';

  @override
  String labVerifyConfirm(String test) {
    return 'Verify the result of $test? Verify only after checking the entered result against the sample and the instrument report.';
  }

  @override
  String get labWorklist => 'Worklist';

  @override
  String get labWorklistNewestFirst => 'Newest orders first';

  @override
  String get laboratory => 'Laboratory';

  @override
  String get language => 'Language';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageHindi => 'हिंदी';

  @override
  String lastActive(String time) {
    return 'Last active $time';
  }

  @override
  String lastChecked(String time) {
    return 'Last checked at $time';
  }

  @override
  String get liveCounts => 'Live counts for the selected hospital.';

  @override
  String get loading => 'Loading…';

  @override
  String get loginWithEmail => 'Login with Email';

  @override
  String get loginWithMobile => 'Login with Mobile';

  @override
  String get loginWithTokenId => 'Login with Token / ID';

  @override
  String get logout => 'Logout';

  @override
  String get lookupAndLogin => 'Lookup & Login';

  @override
  String get lowStock => 'Low stock';

  @override
  String get manufacturer => 'Manufacturer';

  @override
  String get markGiven => 'Given';

  @override
  String get markHeld => 'Hold';

  @override
  String get markMissed => 'Missed';

  @override
  String get markReadFailed => 'Could not mark as read';

  @override
  String get markRefused => 'Refused';

  @override
  String get medicationAdministration => 'Medication administration';

  @override
  String get medicationOrdersByDoctor =>
      'Medication orders are written by the doctor. Nurses record the doses given under them.';

  @override
  String get medicationSafetyAlerts => 'Medication safety alerts';

  @override
  String medicineCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count medicines',
      one: '1 medicine',
    );
    return '$_temp0';
  }

  @override
  String get medicineName => 'Medicine';

  @override
  String medicineNameRequired(int number) {
    return 'Medicine $number: enter the name.';
  }

  @override
  String medicineNumber(int number) {
    return 'Medicine $number';
  }

  @override
  String medicineQuantityInvalid(int number) {
    return 'Medicine $number: quantity must be at least 1.';
  }

  @override
  String get medicineStock => 'Medicines';

  @override
  String get medicines => 'Medicines';

  @override
  String minutesShort(String minutes) {
    return '$minutes min';
  }

  @override
  String get mobileNumber => 'Mobile number';

  @override
  String get moduleNotOnMobileBody =>
      'This module will be added in a later app update. Use the web app for this work until then.';

  @override
  String moduleNotOnMobileTitle(String module) {
    return '$module is not in the mobile app yet';
  }

  @override
  String get mrp => 'MRP';

  @override
  String get myDoctorProfile => 'My doctor profile';

  @override
  String get myHospitals => 'My hospitals';

  @override
  String get myNurseProfile => 'My nurse profile';

  @override
  String get myProfile => 'My profile';

  @override
  String get name => 'Name';

  @override
  String get navAdminDashboard => 'Admin Dashboard';

  @override
  String get navAiScribe => 'AI Scribe';

  @override
  String get navAppointments => 'Appointments';

  @override
  String get navAuditLog => 'Audit log';

  @override
  String get navBilling => 'Billing';

  @override
  String get navBloodBank => 'Blood Bank';

  @override
  String get navCompounder => 'Compounder';

  @override
  String get navConsultation => 'Consultation';

  @override
  String get navDepartments => 'Departments';

  @override
  String get navDoctors => 'Doctors';

  @override
  String get navEmergency => 'Emergency';

  @override
  String get navEmergencyAccess => 'Emergency access';

  @override
  String get navHome => 'Home';

  @override
  String get navHospitalServices => 'Hospital services';

  @override
  String get navHospitals => 'Hospitals';

  @override
  String get navInventory => 'Inventory';

  @override
  String get navIpd => 'IPD / Ward / Beds';

  @override
  String get navLaboratory => 'Laboratory';

  @override
  String get navMain => 'Main';

  @override
  String get navNurseDuty => 'Nurse duty';

  @override
  String get navNurses => 'Nurses / Vitals';

  @override
  String get navPatients => 'Patients';

  @override
  String get navPermissions => 'Permissions';

  @override
  String get navPharmacy => 'Pharmacy';

  @override
  String get navPrescription => 'Prescription';

  @override
  String get navQueue => 'Queue';

  @override
  String get navRadiology => 'Radiology';

  @override
  String get navReports => 'Reports';

  @override
  String get navRoles => 'Roles';

  @override
  String get navSecuritySettings => 'Security settings';

  @override
  String get navUsers => 'Users';

  @override
  String get navigation => 'Navigation';

  @override
  String get needsAttention => 'Needs attention';

  @override
  String get newPassword => 'New password';

  @override
  String get newToHms => 'New to the Hospital Management System?';

  @override
  String get noAccessTitle => 'You don\'t have access';

  @override
  String get noActiveStay => 'No current admission or open visit';

  @override
  String get noActiveToken => 'No active token';

  @override
  String get noActiveTokenHint =>
      'You don\'t have a consultation waiting at the moment.';

  @override
  String get noAppointmentsMatch => 'No appointments match this filter';

  @override
  String get noAppointmentsToday => 'No appointments today';

  @override
  String get noAppointmentsYet => 'No appointments yet';

  @override
  String get noAppointmentsYetHint =>
      'Use Book appointment to choose a doctor and a time.';

  @override
  String get noBedsAvailable => 'No beds available';

  @override
  String get noBillsYet => 'No bills yet';

  @override
  String get noConsultationsYet => 'No completed consultations yet';

  @override
  String get noDiagnosesYet => 'No diagnoses yet';

  @override
  String get noDispensingYet => 'Nothing dispensed yet';

  @override
  String get noDoctorInbox =>
      'Doctor notifications are not available: the hospital system has no inbox for staff yet.';

  @override
  String get noDocumentsYet => 'No documents yet';

  @override
  String get noDosesDue => 'No doses due';

  @override
  String get noDutyToday => 'No duty assigned for today';

  @override
  String get noEncounterForVitals =>
      'Vitals are recorded on an admission or an open OPD visit; this patient has neither.';

  @override
  String get noFreeSlots => 'No free time on this day. Try another date.';

  @override
  String get noHistoryYet => 'No history recorded';

  @override
  String get noHospitalAccess =>
      'Your account is not active in any hospital yet. Ask your hospital administrator.';

  @override
  String get noHospitalMatches => 'No hospital matches your search.';

  @override
  String get noLabOrdersForVisit => 'No lab tests ordered on this visit';

  @override
  String get noLabReportsYet => 'No lab reports yet';

  @override
  String get noLabReportsYetHint =>
      'Reports for tests in progress appear once they are released.';

  @override
  String get noMedicationOrders => 'No active medication orders';

  @override
  String get noMedicinesFound => 'No medicines found';

  @override
  String get noMedicinesListed => 'No medicines listed';

  @override
  String get noNotesYet => 'No notes yet';

  @override
  String get noNotifications => 'No notifications';

  @override
  String get noOpenTasks => 'No open tasks';

  @override
  String get noOtherDevices => 'No signed-in devices.';

  @override
  String noPageMatches(String query) {
    return 'No page matches “$query”.';
  }

  @override
  String get noPatientsFound => 'No patient found';

  @override
  String get noPatientsFoundHint => 'Only patients in your care are shown.';

  @override
  String get noPatientsYet => 'No patients registered yet';

  @override
  String get noPaymentsYet => 'No payments recorded';

  @override
  String get noPrescriptionsForVisit => 'No prescription on this visit yet';

  @override
  String get noPrescriptionsInQueue => 'No prescriptions here';

  @override
  String get noPrescriptionsYet => 'No prescriptions yet';

  @override
  String get noPrescriptionsYetHint =>
      'Prescriptions from your visits will appear here.';

  @override
  String get noReadingsYet => 'No readings recorded yet';

  @override
  String get noResultValues => 'No values in this report';

  @override
  String get noShowTitle => 'Mark as no-show?';

  @override
  String get noStaffInbox =>
      'Notifications are not available: the hospital system has no inbox for staff yet.';

  @override
  String get noStockMovements => 'No stock movements yet';

  @override
  String get noTokenServed => 'No token being served';

  @override
  String get noUpcomingAppointments => 'No upcoming appointments';

  @override
  String get noUsableBatch =>
      'No unexpired batch of this medicine is in stock.';

  @override
  String get noVisitsToShow => 'No visits to show';

  @override
  String get noVisitsToShowHint =>
      'Visits are created at the reception when a patient arrives.';

  @override
  String get noVisitsYet => 'No visits yet';

  @override
  String get noVitalsYet => 'No vitals recorded on this visit';

  @override
  String get noWardPatients => 'No patients on your duty';

  @override
  String get noWardPatientsHint =>
      'Patients appear here when they are in a ward you are on duty in, or assigned to you for today\'s shift.';

  @override
  String get nobodyCalled => 'Nobody called';

  @override
  String get nobodyInConsultation => 'Nobody in consultation';

  @override
  String get nobodyWaiting => 'Nobody waiting';

  @override
  String get none => 'None';

  @override
  String get notAvailableNow => 'Not available right now';

  @override
  String notEligibleBody(String department, String roles) {
    return '$department work is only for $roles. Please sign in with an account that has one of these roles.';
  }

  @override
  String get notEligibleForPage => 'You are not eligible for that page';

  @override
  String notEligibleForPageBody(String module) {
    return '$module is not open to your role in this hospital.';
  }

  @override
  String get notEligibleTitle => 'You are not eligible for this work';

  @override
  String get notMemberOfAnyHospital =>
      'You are not a member of any hospital yet.';

  @override
  String get notScheduled => 'Not scheduled';

  @override
  String get notSignedInSignIn => 'Not signed in · Sign in';

  @override
  String get notVerified => 'Not verified';

  @override
  String get noteAssessment => 'Assessment';

  @override
  String get noteChiefComplaint => 'Chief complaint';

  @override
  String get noteCurrentMedications => 'Current medications';

  @override
  String get noteExamination => 'Examination';

  @override
  String get noteNeedsOneSection => 'Write at least one part of the note.';

  @override
  String get noteOther => 'Other notes';

  @override
  String get notePastHistory => 'Past history';

  @override
  String get notePlan => 'Plan';

  @override
  String get notePresentIllness => 'History of present illness';

  @override
  String get noteSaved => 'Note saved by the hospital system.';

  @override
  String get noteText => 'Note';

  @override
  String get noteTextRequired => 'Write the note first.';

  @override
  String noteTooLong(int count) {
    return 'Keep the note under $count characters.';
  }

  @override
  String get noteType => 'Note type';

  @override
  String get noteTypeCommunication => 'Communication';

  @override
  String get noteTypeEducation => 'Patient education';

  @override
  String get noteTypeHandoff => 'Shift handoff';

  @override
  String get noteTypeIncident => 'Incident report';

  @override
  String get noteTypeProgress => 'Progress note';

  @override
  String get notesAreFinal =>
      'Saved notes cannot be edited. To correct one, add a new note.';

  @override
  String get nothingLeftToDispense =>
      'Nothing is left to dispense on this prescription.';

  @override
  String get nothingNeedsAttention => 'Nothing needs attention';

  @override
  String get nothingNeedsAttentionText =>
      'No waiting patients, urgent tests or active emergencies right now.';

  @override
  String get notifications => 'Notifications';

  @override
  String get notificationsIntro =>
      'Messages from your hospital. Open one to see the page it is about.';

  @override
  String get nowServing => 'Now serving';

  @override
  String nowServingToken(String token) {
    return 'Now serving token $token';
  }

  @override
  String get nurseProfileMissing =>
      'No nurse profile is linked to your login at this hospital. Ask the hospital Admin to link it.';

  @override
  String get nursingNotes => 'Nursing notes';

  @override
  String get onThisStay => 'This admission';

  @override
  String opdVisitOn(String date) {
    return 'OPD visit · $date';
  }

  @override
  String get open => 'Open';

  @override
  String get openConsultation => 'Open consultation';

  @override
  String get openNavigation => 'Open navigation';

  @override
  String get openPatientRecord => 'Open patient record';

  @override
  String get openTasks => 'Open tasks';

  @override
  String get openVisits => 'Open visits';

  @override
  String get operations => 'Operations';

  @override
  String get opsBackToList => 'Back to list';

  @override
  String get opsSaved => 'Saved by the hospital system.';

  @override
  String get opsSearch => 'Search';

  @override
  String get opsStepRefused =>
      'The hospital system did not allow this step for the record as it is now. Refresh to see its current state.';

  @override
  String get orDivider => 'OR';

  @override
  String get orderLabTest => 'Order lab test';

  @override
  String get orderedBy => 'Ordered by';

  @override
  String get otpLabel => 'OTP';

  @override
  String get otpPrintedOnServer =>
      'Development server: the code is printed in the server log, not sent by SMS.';

  @override
  String otpSentTo(String phone) {
    return 'Enter the 6-digit OTP sent to $phone';
  }

  @override
  String get outOfStock => 'Out of stock';

  @override
  String get outstandingBalance => 'Outstanding balance';

  @override
  String get overrideReason => 'Reason to prescribe anyway';

  @override
  String overrideReasonHint(int count) {
    return 'At least $count characters. It is recorded with the prescription.';
  }

  @override
  String get password => 'Password';

  @override
  String get passwordUpdated =>
      'Password updated. Sign in with your new password.';

  @override
  String get pastVisits => 'Past visits';

  @override
  String get patientDataUnavailable =>
      'Your records could not be loaded. Check your connection and try again.';

  @override
  String get patientHomeIntro =>
      'Your queue token, appointments, prescriptions, reports and bills in one place.';

  @override
  String get patientId => 'Patient ID';

  @override
  String get patientLabel => 'Patient';

  @override
  String get patientNavAppointments => 'My Appointments';

  @override
  String get patientNavBills => 'My Bills';

  @override
  String get patientNavConsent => 'Notifications / Consent';

  @override
  String get patientNavHome => 'Home';

  @override
  String get patientNavLab => 'My Lab Reports';

  @override
  String get patientNavNotifications => 'Notifications';

  @override
  String get patientNavPrescriptions => 'My Prescriptions';

  @override
  String get patientNavQueue => 'My Queue / Token';

  @override
  String get patientNavRecords => 'My Medical Records';

  @override
  String get patientNotInCare => 'You cannot open this record';

  @override
  String get patientNotInCareHint =>
      'The hospital system shows a doctor only the patients in their care at this hospital.';

  @override
  String get patientPortal => 'Patient portal';

  @override
  String get patientProfile => 'Patient profile';

  @override
  String get patientSignIn => 'Patient sign in';

  @override
  String get patientSignInIntro =>
      'Patients see their own appointments, prescriptions, reports and bills.';

  @override
  String get patientsInCare => 'Patients in care';

  @override
  String get payAtHospital => 'Bills are paid at the hospital';

  @override
  String get payAtHospitalBody =>
      'Online payment is not available yet. Payments made at the billing desk appear here.';

  @override
  String get paymentBankTransfer => 'Bank transfer';

  @override
  String get paymentCard => 'Card';

  @override
  String get paymentCash => 'Cash';

  @override
  String get paymentHistory => 'Payment history';

  @override
  String get paymentUpi => 'UPI';

  @override
  String get pendingPrescriptions => 'Prescriptions to dispense';

  @override
  String get pendingTasks => 'Pending tasks';

  @override
  String get pharmacyActivity => 'Activity';

  @override
  String get pharmacyIntro =>
      'Prescriptions to dispense, medicine stock and recent activity at this hospital.';

  @override
  String get pickDate => 'Pick a date';

  @override
  String get pickerChange => 'Change';

  @override
  String pickerTypeMore(int count) {
    return 'Type at least $count characters.';
  }

  @override
  String get platformAndroid => 'Android';

  @override
  String get platformIos => 'iPhone / iPad';

  @override
  String get platformOther => 'Other device';

  @override
  String get platformWeb => 'Web browser';

  @override
  String positionShort(String position) {
    return 'position $position';
  }

  @override
  String get prescribeAnyway => 'Prescribe anyway';

  @override
  String prescribedIssuedLeft(int prescribed, int issued, int left) {
    return 'Prescribed $prescribed · Issued $issued · Left $left';
  }

  @override
  String get prescription => 'Prescription';

  @override
  String get prescriptionCancelledNoDispense =>
      'This prescription was cancelled; it cannot be dispensed.';

  @override
  String prescriptionCode(int id) {
    return 'RX-$id';
  }

  @override
  String get prescriptionFreeTextNote =>
      'Write each medicine as on the web form. Nothing is suggested by the app.';

  @override
  String get prescriptionMaybeSaved =>
      'This prescription may already be saved. Check the list below before saving again.';

  @override
  String get prescriptionNeedsVerification =>
      'This paper prescription must be verified by a second pharmacist or an Admin before it is dispensed.';

  @override
  String get prescriptionQueue => 'Prescriptions';

  @override
  String prescriptionSaved(String id) {
    return 'Prescription #$id saved by the hospital system.';
  }

  @override
  String get prescriptionsIntro => 'Medicines your doctors have prescribed.';

  @override
  String get priority => 'Priority';

  @override
  String get priorityRoutine => 'Routine';

  @override
  String get priorityStat => 'STAT';

  @override
  String get profileChangesAtHospital =>
      'To change your details, please contact the hospital reception.';

  @override
  String get profileIntro => 'Your details as the hospital has recorded them.';

  @override
  String profileMenuFor(String name) {
    return 'Profile menu for $name';
  }

  @override
  String get qualification => 'Qualification';

  @override
  String get quantity => 'Quantity';

  @override
  String get quantityNow => 'Quantity to issue now';

  @override
  String get queueCall => 'Call';

  @override
  String get queueComplete => 'Complete';

  @override
  String get queueDoctorBusy =>
      'This doctor already has a patient in consultation. Complete that one first.';

  @override
  String queueFinishedToday(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count tokens finished today',
      one: '1 token finished today',
      zero: 'No token finished today',
    );
    return '$_temp0';
  }

  @override
  String get queueIntro =>
      'Your place in today\'s consultation queue. This page checks again every 30 seconds while it is open.';

  @override
  String queueMoveConfirm(String token) {
    return 'Token #$token will leave the queue. The patient may be notified by the hospital system.';
  }

  @override
  String get queueMoveFailed => 'The queue could not be updated';

  @override
  String get queueNoShow => 'No-show';

  @override
  String get queuePosition => 'Position in queue';

  @override
  String get queueSkip => 'Skip';

  @override
  String get queueStartConsultation => 'Start consultation';

  @override
  String get queueStatus => 'Queue status';

  @override
  String get quickActions => 'Quick actions';

  @override
  String get reasonForVisit => 'Reason for visit';

  @override
  String get reasonRequired => 'Reason (required)';

  @override
  String get recentConsultations => 'Recent consultations';

  @override
  String get recentDispensing => 'Recent dispensing';

  @override
  String get recentLabReports => 'Recent lab reports';

  @override
  String get recentNursingActivity => 'Recent nursing activity';

  @override
  String get recentPrescriptions => 'Recent prescriptions';

  @override
  String get recentStockMovements => 'Recent stock movements';

  @override
  String get recentlyRegistered => 'Recently registered patients';

  @override
  String get receptionAppointmentsIntro =>
      'Bookings at this hospital. Check patients in to give them a queue token.';

  @override
  String receptionCheckedIn(String name, String token) {
    return '$name is checked in. Token #$token.';
  }

  @override
  String get receptionCheckIn => 'Check in';

  @override
  String get receptionLink => 'Register at this hospital';

  @override
  String receptionLinked(String name, String uhid) {
    return '$name is now registered here. Patient ID: $uhid';
  }

  @override
  String get receptionLinkIntro =>
      'For a patient who already has an account, for example from the patient app. Ask for their mobile number and date of birth.';

  @override
  String get receptionLinkTitle => 'Register an existing patient here';

  @override
  String get receptionMultipleMatch =>
      'More than one patient has this mobile number and date of birth. Ask the patient to join from the patient app.';

  @override
  String get receptionNoAppointments => 'No bookings on this day.';

  @override
  String get receptionNoMatch =>
      'No patient has this mobile number and date of birth. Register them as new.';

  @override
  String get receptionNoResults => 'No patient found.';

  @override
  String get receptionPatientsIntro =>
      'Find a patient, register a new one, or register an existing patient at this hospital.';

  @override
  String get receptionPhoneInvalid => 'Enter the 10-digit mobile number.';

  @override
  String get receptionPortalAccount =>
      'This mobile number already has a patient app account. Register that patient here with their date of birth below.';

  @override
  String get receptionPossibleDuplicate =>
      'A patient with this mobile number is already registered here. Check the list, or register anyway if this is a different person.';

  @override
  String get receptionQueueIntro =>
      'Today\'s queue at this hospital. Doctors call and see patients from their own queue.';

  @override
  String get receptionRegister => 'Register patient';

  @override
  String get receptionRegisterAnyway => 'Register anyway';

  @override
  String receptionRegistered(String name, String uhid) {
    return '$name is registered. Patient ID: $uhid';
  }

  @override
  String get receptionRegisterTitle => 'Register a new patient';

  @override
  String get receptionSearch => 'Search';

  @override
  String get receptionSearchHint => 'Name, mobile number or patient ID';

  @override
  String get recordOn => 'Record on';

  @override
  String get recordSignedNoChange =>
      'This record is signed and cannot be changed. Add a new record instead.';

  @override
  String get referenceRange => 'Reference range';

  @override
  String get refresh => 'Refresh';

  @override
  String get refreshFailed => 'Could not refresh';

  @override
  String get refund => 'Refund';

  @override
  String get registerAtHospital => 'Hospital to register at';

  @override
  String get registerIntro =>
      'Staff accounts are created by invitation from your hospital.';

  @override
  String get registerTitle => 'Create your patient account';

  @override
  String registeredInTotal(String count) {
    return '$count registered in total';
  }

  @override
  String get registration => 'Registration';

  @override
  String get releasedOn => 'Released on';

  @override
  String get releasedResults => 'Released results';

  @override
  String get remarks => 'Remarks';

  @override
  String get removeMedicine => 'Remove medicine';

  @override
  String get reorderLevel => 'Reorder level';

  @override
  String get reportNotes => 'Report notes';

  @override
  String get resendCode => 'Resend code';

  @override
  String get resetCodeSent =>
      'If an active staff account matches, a code was sent to its registered mobile number.';

  @override
  String get resetConfirmIntro =>
      'Enter the code from the SMS and choose a new password.';

  @override
  String get resetPasswordTitle => 'Reset your password';

  @override
  String get resetRequestIntro =>
      'A code is sent to the mobile number registered on your staff account.';

  @override
  String get restoreFailedBody =>
      'Your sign-in is kept on this device. Check the connection and try again, or sign out.';

  @override
  String get restoreFailedTitle => 'Could not reach the hospital server';

  @override
  String get restoringSession => 'Opening your session…';

  @override
  String get resultNotReleased => 'Result not released yet';

  @override
  String get results => 'Results';

  @override
  String get retry => 'Retry';

  @override
  String get roleAdmin => 'Admin';

  @override
  String get roleBillingStaff => 'Billing Staff';

  @override
  String get roleBloodBankStaff => 'Blood Bank Staff';

  @override
  String get roleCompounder => 'Compounder';

  @override
  String get roleDoctor => 'Doctor';

  @override
  String get roleHomeBilling => 'Billing today';

  @override
  String get roleHomeBloodBank => 'Blood bank today';

  @override
  String get roleHomeDoctor => 'Your clinic today';

  @override
  String get roleHomeLaboratory => 'Laboratory today';

  @override
  String get roleHomeNurse => 'Your ward today';

  @override
  String get roleHomePharmacy => 'Pharmacy today';

  @override
  String get roleHomeReceptionist => 'Front desk today';

  @override
  String get roleHomeStore => 'Store today';

  @override
  String get roleHospitalManager => 'Hospital Manager';

  @override
  String get roleInventoryStaff => 'Inventory Staff';

  @override
  String get roleLabStaff => 'Lab Staff';

  @override
  String get roleNurse => 'Nurse';

  @override
  String get rolePharmacist => 'Pharmacist';

  @override
  String get roleReceptionist => 'Receptionist';

  @override
  String roomNumber(String room) {
    return 'Room $room';
  }

  @override
  String get route => 'Route';

  @override
  String get saveNote => 'Save note';

  @override
  String get saveNoteDraft => 'Save note as draft';

  @override
  String get saveVitals => 'Save vitals';

  @override
  String get scheduledFor => 'Scheduled for';

  @override
  String get searchByNameOrCity => 'Search by name or city';

  @override
  String get searchHospitals => 'Search hospitals';

  @override
  String get searchMedicinesHint => 'Search medicines by name';

  @override
  String get searchPages => 'Search pages';

  @override
  String get searchPatientName => 'Search by patient name';

  @override
  String get searchPatientsHint => 'Name, mobile number or UHID';

  @override
  String get searchPrescriptionsHint => 'RX number, patient name or UHID';

  @override
  String get searchWardPatients => 'Search by name, ward or bed';

  @override
  String get selectDoctor => 'Select doctor';

  @override
  String get selectHospital => 'Select hospital';

  @override
  String get selectHospitalForDashboard =>
      'Select a hospital from the header to see its dashboard.';

  @override
  String get selectHospitalTitle => 'Select Hospital';

  @override
  String get selectedHospital => 'Selected hospital';

  @override
  String get sendEmailOtp => 'Send Email OTP';

  @override
  String get sendOtp => 'Send OTP';

  @override
  String get sendResetCode => 'Send reset code';

  @override
  String get serverConnection => 'Server connection';

  @override
  String get serverConnectionText =>
      'Check that this device can reach the hospital server.';

  @override
  String get sessionEndedNotice =>
      'Your session has ended. Please sign in again.';

  @override
  String get setNewPassword => 'Set new password';

  @override
  String get settings => 'Settings';

  @override
  String get shiftEvening => 'Evening';

  @override
  String get shiftMorning => 'Morning';

  @override
  String get shiftNight => 'Night';

  @override
  String showingFirstOf(int shown, int total) {
    return 'Showing the first $shown of $total. Search to narrow the list.';
  }

  @override
  String get signIn => 'Sign in';

  @override
  String get signInMethod => 'Sign-in method';

  @override
  String get signInRequired => 'Sign-in required';

  @override
  String get signInTitle => 'Sign in';

  @override
  String signInToOpen(String module) {
    return 'Sign in with a staff account that may open $module.';
  }

  @override
  String get signInToSee => 'Sign in to see';

  @override
  String get signInUnavailableBody =>
      'Staff and patient sign-in come with the next app update. Until then, use the web app to sign in.';

  @override
  String get signInUnavailableTitle => 'Sign-in is not in this app version yet';

  @override
  String get signOut => 'Sign out';

  @override
  String get signOutDevice => 'Sign out';

  @override
  String get signOutDeviceConfirm => 'Sign this device out?';

  @override
  String get signOutEverywhere => 'Sign out everywhere';

  @override
  String get signOutEverywhereConfirm =>
      'Sign out of every device, including this one?';

  @override
  String get signRecord => 'Sign';

  @override
  String get signRecordBody =>
      'A signed record is final. Corrections are added as new records.';

  @override
  String get signRecordTitle => 'Sign this record?';

  @override
  String signedInAs(String name) {
    return 'Signed in as $name';
  }

  @override
  String get signedInDevices => 'Signed-in devices';

  @override
  String get signedInDevicesIntro =>
      'Devices where your account is signed in. Sign out any you don\'t recognise.';

  @override
  String signedOn(String date) {
    return 'Signed $date';
  }

  @override
  String get sixDigitCode => '6-digit code';

  @override
  String get skipTokenTitle => 'Skip this token?';

  @override
  String get somePatientDataUnavailable =>
      'Some of your records could not be loaded.';

  @override
  String get somethingWentWrong => 'Something went wrong';

  @override
  String get specialization => 'Specialisation';

  @override
  String get staffAccessEnded => 'Access ended';

  @override
  String get staffIntro => 'Staff with access to this hospital.';

  @override
  String get staffInvitePending => 'Invite pending';

  @override
  String get staffManagersOnly =>
      'Only this hospital\'s Admin or Hospital Manager can see the staff list.';

  @override
  String get staffNone => 'No staff found.';

  @override
  String get staffPortal => 'Staff portal';

  @override
  String get staffSearch => 'Search staff by name or employee ID';

  @override
  String get staffSignIn => 'Staff sign in';

  @override
  String get staffSignInIntro => 'Use your hospital staff account.';

  @override
  String get startConsultation => 'Start consultation';

  @override
  String get startTask => 'Start';

  @override
  String get status => 'Status';

  @override
  String get statusAcknowledged => 'Acknowledged';

  @override
  String get statusAdmitted => 'Admitted';

  @override
  String get statusCalled => 'Called';

  @override
  String get statusCancelled => 'Cancelled';

  @override
  String get statusCheckedIn => 'Checked in';

  @override
  String get statusCompleted => 'Completed';

  @override
  String get statusConfirmed => 'Confirmed';

  @override
  String get statusDeferred => 'Deferred';

  @override
  String get statusDischargeInitiated => 'Discharge initiated';

  @override
  String get statusDischarged => 'Discharged';

  @override
  String get statusDispensed => 'Dispensed';

  @override
  String get statusInConsultation => 'In consultation';

  @override
  String get statusInProgress => 'In progress';

  @override
  String get statusNoShow => 'No show';

  @override
  String get statusPaid => 'Paid';

  @override
  String get statusPartiallyDispensed => 'Partly dispensed';

  @override
  String get statusPartiallyPaid => 'Partly paid';

  @override
  String get statusPending => 'Pending';

  @override
  String get statusReady => 'Ready';

  @override
  String get statusReleased => 'Released';

  @override
  String get statusScheduled => 'Scheduled';

  @override
  String get statusUnpaid => 'Unpaid';

  @override
  String get statusUrgent => 'Urgent';

  @override
  String get statusWaiting => 'Waiting';

  @override
  String get stepChooseSlot => 'Choose a slot';

  @override
  String get stepChooseSlotText => 'Pick a date and an available time.';

  @override
  String get stepConfirm => 'Confirm';

  @override
  String get stepConfirmText => 'Sign in to confirm the booking.';

  @override
  String get stepSelectDoctor => 'Select doctor';

  @override
  String get stepSelectDoctorText => 'Choose a department and doctor.';

  @override
  String get stepSelectHospitalText => 'Pick where you want to be seen.';

  @override
  String get stockAdjust => 'Adjusted';

  @override
  String get stockBatch => 'Stock batch';

  @override
  String get stockChangedByStore =>
      'Stock is read-only here. It changes only when medicines are dispensed or received, or when the store (Admin, Hospital Manager or Inventory Staff) corrects it.';

  @override
  String get stockIn => 'In';

  @override
  String get stockMovements => 'Stock movements';

  @override
  String get stockOut => 'Out';

  @override
  String get substitute => 'Substitute';

  @override
  String substituteFor(String medicine) {
    return 'instead of $medicine';
  }

  @override
  String get substituteReason => 'Why is a substitute given?';

  @override
  String get supplier => 'Supplier';

  @override
  String get switchingHospitalNote =>
      'Switching hospital changes every list you see to that hospital\'s records.';

  @override
  String get tabEmail => 'Email';

  @override
  String get tabFamily => 'Family';

  @override
  String get tabMobileOtp => 'Mobile OTP';

  @override
  String get tabTokenId => 'Token / ID';

  @override
  String get testDate => 'Test date';

  @override
  String get thisDevice => 'This device';

  @override
  String get tileAppointmentsToday => 'Appointments today';

  @override
  String get tileBedsAvailable => 'Beds available';

  @override
  String get tileBillingPending => 'Invoices awaiting payment';

  @override
  String get tileCollectedToday => 'Collected today';

  @override
  String get tileCurrentAdmissions => 'Current admissions';

  @override
  String get tileLabCompleted => 'Lab tests completed';

  @override
  String get tileLabPending => 'Lab tests pending';

  @override
  String get tileLabUrgent => 'Urgent lab tests';

  @override
  String get tilePatientsToday => 'Patients registered today';

  @override
  String get tileWaitingInQueue => 'Waiting in queue';

  @override
  String get timeLabel => 'Time';

  @override
  String get toDispense => 'To dispense';

  @override
  String get todayAtAGlance => 'Today at a glance';

  @override
  String get todaysAppointments => 'Today\'s appointments';

  @override
  String get todaysPatientFlow => 'Today\'s patient flow';

  @override
  String get todaysShift => 'Today\'s duty';

  @override
  String get tokenCalled => 'Your token has been called';

  @override
  String get tokenCalledBody => 'Please go to the consultation area now.';

  @override
  String get tokenIdHint =>
      'Use the patient ID from registration together with your account password.';

  @override
  String get tokenIdIntro => 'Enter your token number or hospital patient ID';

  @override
  String get tokenInConsultation =>
      'You are with the doctor now. Your consultation is in progress.';

  @override
  String get tokenLabel => 'Token';

  @override
  String get tokenNext => 'You are next. The doctor will see you shortly.';

  @override
  String tokenNumber(String number) {
    return 'Token $number';
  }

  @override
  String get tokenOrPatientId => 'Token Number / Patient ID';

  @override
  String get totalMedicines => 'Medicine batches';

  @override
  String get triageCritical => 'Critical';

  @override
  String get triageEmergency => 'Emergency';

  @override
  String get triageNonUrgent => 'Non-urgent';

  @override
  String get triageSemiUrgent => 'Semi-urgent';

  @override
  String get triageUrgent => 'Urgent';

  @override
  String get tryAgain => 'Try again';

  @override
  String get typeModuleName => 'Type a module name…';

  @override
  String typeToSearch(int count) {
    return 'Type at least $count letters to search';
  }

  @override
  String get unitPrice => 'Unit price';

  @override
  String get unread => 'Unread';

  @override
  String unreadNotifications(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'You have $count unread notifications',
      one: 'You have 1 unread notification',
    );
    return '$_temp0';
  }

  @override
  String get upcomingAppointments => 'Upcoming appointments';

  @override
  String get useDifferentNumber => 'Use a different number';

  @override
  String get usernameOrEmail => 'Username or email';

  @override
  String get verified => 'Verified';

  @override
  String get verifyAndContinue => 'Verify and continue';

  @override
  String get verifyAndContinueShort => 'Verify & Continue';

  @override
  String verifyEmailIntro(String email) {
    return 'Enter the code sent to $email. Then sign in with your email and password.';
  }

  @override
  String get verifyOtp => 'Verify OTP';

  @override
  String get verifyUsingEmail => 'Verify using Email';

  @override
  String get verifyYourEmail => 'Verify your email';

  @override
  String get viewAll => 'View all';

  @override
  String get viewMyAppointments => 'View my appointments';

  @override
  String get viewProfile => 'View profile';

  @override
  String viewingHospital(String name) {
    return 'Showing records at $name';
  }

  @override
  String get visitClosedReadOnly =>
      'This visit is closed. Its records are shown read-only.';

  @override
  String get visitNotYourPatient =>
      'Only this visit\'s doctor can start or complete the consultation.';

  @override
  String get visitPatientNotCalled =>
      'This patient has not been called yet. Call them from the Queue first.';

  @override
  String get visits => 'Visits';

  @override
  String get visitStatusMovedOn =>
      'This visit has already moved on, so its status was not changed. The page now shows its current status.';

  @override
  String get vitalBloodPressure => 'Blood pressure';

  @override
  String get vitalBloodSugar => 'Blood sugar';

  @override
  String get vitalDiastolic => 'Diastolic BP';

  @override
  String get vitalHeight => 'Height';

  @override
  String get vitalNegative => 'Cannot be negative.';

  @override
  String get vitalNotANumber => 'Enter a number.';

  @override
  String get vitalPainScore => 'Pain score';

  @override
  String get vitalPulse => 'Pulse';

  @override
  String get vitalRespiratoryRate => 'Respiratory rate';

  @override
  String get vitalSpo2 => 'SpO₂';

  @override
  String get vitalSystolic => 'Systolic BP';

  @override
  String get vitalTemperature => 'Temperature';

  @override
  String get vitalTooHigh => 'Above the allowed maximum.';

  @override
  String get vitalTooPrecise => 'Use at most 2 decimal places.';

  @override
  String get vitalWeight => 'Weight';

  @override
  String get vitalWholeNumber => 'Enter a whole number.';

  @override
  String get vitals => 'Vitals';

  @override
  String get vitalsSaved => 'Vitals saved by the hospital system.';

  @override
  String get waitingPatients => 'Waiting';

  @override
  String get wardAndBed => 'Ward and bed';

  @override
  String get wardAttention => 'Needs attention on the ward';

  @override
  String get wardOrderAdd => 'Order medicine';

  @override
  String get wardOrderDose => 'Dose (with strength)';

  @override
  String get wardOrderEndDate => 'Last day (optional)';

  @override
  String get wardOrderFieldsRequired =>
      'Choose a medicine and fill in dose, route and frequency.';

  @override
  String get wardOrderMedicine =>
      'Medicine (from the patient\'s prescriptions)';

  @override
  String get wardOrderNoMedicines =>
      'No prescribed medicine to order. Write a prescription in the consultation first.';

  @override
  String get wardOrderNone => 'No medication orders yet.';

  @override
  String get wardOrdersIntro =>
      'Orders for the nurses. A dose counts as given only when a nurse records it.';

  @override
  String get wardOrdersTitle => 'Ward medication orders';

  @override
  String get wardOrderStop => 'Stop';

  @override
  String get wardOrderStopped => 'Stopped';

  @override
  String get wardPatients => 'Ward patients';

  @override
  String get wardPatientsIntro =>
      'Patients of your duty today: in your wards, or assigned to you.';

  @override
  String get weWillSendCode => 'We\'ll send a 6-digit verification code';

  @override
  String get welcome => 'Welcome';

  @override
  String get writeInConsultation => 'Write in a consultation';

  @override
  String get yourMobileNumber => 'Your mobile number';

  @override
  String get firstDoseLabel => 'First dose';

  @override
  String get firstDoseNextRound => 'Next medication round';

  @override
  String get firstDoseNow => 'Start now';

  @override
  String get firstDoseAt => 'Specific time';

  @override
  String get firstDosePickTime => 'Choose the date and time of the first dose';

  @override
  String get firstDoseReviewTitle => 'Review the dose schedule';

  @override
  String firstDoseReviewFirst(String when) {
    return 'First dose: $when';
  }

  @override
  String firstDoseReviewNext(String times) {
    return 'Then: $times';
  }

  @override
  String firstDoseReviewCount(int count) {
    return '$count doses scheduled';
  }

  @override
  String get firstDosePrn =>
      'As needed (PRN): no doses are scheduled. Nurses record each dose when it is given.';

  @override
  String get firstDoseChoose =>
      'The first dose cannot be set automatically: this hospital has no medication rounds for this order. Choose Start now or a specific time.';

  @override
  String get firstDoseRefused =>
      'This first-dose time cannot be used: it is in the past or outside the order\'s dates. Choose another time.';

  @override
  String finalBillConfirmTitle(String patient) {
    return 'Create the final bill for $patient?';
  }

  @override
  String get finalBillConfirmBody =>
      'The final bill brings together the bed days above and the charges already captured for this stay. Once created it can be cancelled only by an Admin or Hospital Manager, with a reason.';

  @override
  String get prnGiveDose => 'Give dose';

  @override
  String get prnAsNeededHint =>
      'As needed (PRN): give when the patient needs it, within the doctor\'s limits.';

  @override
  String prnLimitInterval(String hours) {
    return 'At least $hours h between doses';
  }

  @override
  String prnLimitDaily(int count) {
    return 'At most $count doses in 24 h';
  }

  @override
  String get prnNoLimits => 'No dose limits set by the doctor';

  @override
  String get prnConfirmTitle => 'Give this as-needed dose now?';

  @override
  String get prnNoteLabel => 'Reason or note (optional)';

  @override
  String prnTooSoon(String hours) {
    return 'Not recorded: too soon after the last dose. This order allows one dose every $hours h. Ask the doctor if the patient needs it sooner.';
  }

  @override
  String prnDailyLimitReached(int count) {
    return 'Not recorded: this order allows at most $count doses in 24 hours, and that many have been given. Ask the doctor before giving more.';
  }

  @override
  String get prnIntervalField => 'Minimum hours between doses (optional)';

  @override
  String get prnMaxDosesField => 'Most doses in 24 hours (optional)';

  @override
  String get prnLimitsInvalid =>
      'Enter the dose limits as numbers (hours above 0, doses 1 to 48), or leave them empty.';
}
