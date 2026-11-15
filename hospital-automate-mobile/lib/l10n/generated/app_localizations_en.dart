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
  String get ageLabel => 'Age';

  @override
  String ageYears(String age) {
    return '$age y';
  }

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
  String get atLeast8Characters => 'At least 8 characters.';

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
  String get authEmailExists =>
      'An account already exists with this email. Sign in instead.';

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
  String get authPhoneExists =>
      'An account already exists with this mobile number. Sign in instead.';

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
  String bedsOccupiedOf(String occupied, String total) {
    return '$occupied occupied of $total';
  }

  @override
  String get billDate => 'Bill date';

  @override
  String get billTotal => 'Total';

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
  String get calledPatients => 'Called';

  @override
  String get cancel => 'Cancel';

  @override
  String get changeNumber => 'Change number';

  @override
  String get checkAgain => 'Check again';

  @override
  String get checkAndSavePrescription => 'Check safety and save prescription';

  @override
  String checkTheseFields(String fields) {
    return 'Please check: $fields';
  }

  @override
  String get checking => 'Checking…';

  @override
  String get checkingConnection => 'Checking connection…';

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
  String get completedToday => 'Completed today';

  @override
  String get confirmBooking => 'Confirm booking';

  @override
  String get confirmPassword => 'Confirm password';

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
  String get deptEmergencyText => 'Triage and emergency care.';

  @override
  String get deptInventoryText => 'Store, suppliers and purchase orders.';

  @override
  String get deptLaboratoryText => 'Samples, results and reports.';

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
  String get draft => 'Draft';

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
  String get hospital => 'Hospital';

  @override
  String get howBookingWorks => 'How booking works';

  @override
  String get howBookingWorksIntro => 'You can see the steps before signing in.';

  @override
  String get icd10Search => 'Search ICD-10 (optional)';

  @override
  String get instructions => 'Instructions';

  @override
  String get interfaceLanguage => 'Interface language';

  @override
  String get invoicesPaidTotal => 'Invoices paid / total';

  @override
  String get jumpTo => 'Jump to…';

  @override
  String get jumpToPage => 'Jump to a page';

  @override
  String get knownCondition => 'Known condition';

  @override
  String get labIntro => 'Results released by the laboratory.';

  @override
  String get labNotADiagnosis =>
      'Values are shown as the laboratory entered them. Please discuss them with your doctor.';

  @override
  String get labOrders => 'Lab orders';

  @override
  String get labReleasedOnly =>
      'Reports appear here after the laboratory has checked and released them.';

  @override
  String get labTestName => 'Test name';

  @override
  String get labTestNameRequired => 'Enter the test name.';

  @override
  String get labTestStatus => 'Lab test status';

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
  String get markReadFailed => 'Could not mark as read';

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
  String get myDoctorProfile => 'My doctor profile';

  @override
  String get myHospitals => 'My hospitals';

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
  String get noDoctorInbox =>
      'Doctor notifications are not available: the hospital system has no inbox for staff yet.';

  @override
  String get noDocumentsYet => 'No documents yet';

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
  String get noMedicinesListed => 'No medicines listed';

  @override
  String get noNotesYet => 'No notes yet';

  @override
  String get noNotifications => 'No notifications';

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
  String get noPrescriptionsYet => 'No prescriptions yet';

  @override
  String get noPrescriptionsYetHint =>
      'Prescriptions from your visits will appear here.';

  @override
  String get noResultValues => 'No values in this report';

  @override
  String get noShowTitle => 'Mark as no-show?';

  @override
  String get noTokenServed => 'No token being served';

  @override
  String get noUpcomingAppointments => 'No upcoming appointments';

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
  String get open => 'Open';

  @override
  String get openConsultation => 'Open consultation';

  @override
  String get openNavigation => 'Open navigation';

  @override
  String get openPatientRecord => 'Open patient record';

  @override
  String get openVisits => 'Open visits';

  @override
  String get operations => 'Operations';

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
  String get payAtHospital => 'Bills are paid at the hospital';

  @override
  String get payAtHospitalBody =>
      'Online payment is not available yet. Payments made at the billing desk appear here.';

  @override
  String get paymentHistory => 'Payment history';

  @override
  String get pickDate => 'Pick a date';

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
  String get prescription => 'Prescription';

  @override
  String get prescriptionFreeTextNote =>
      'Write each medicine as on the web form. Nothing is suggested by the app.';

  @override
  String get prescriptionMaybeSaved =>
      'This prescription may already be saved. Check the list below before saving again.';

  @override
  String prescriptionSaved(String id) {
    return 'Prescription #$id saved by the hospital system.';
  }

  @override
  String get prescriptionsIntro => 'Medicines your doctors have prescribed.';

  @override
  String get priority => 'Priority';

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
  String get quantity => 'Quantity';

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
  String get recentConsultations => 'Recent consultations';

  @override
  String get recentLabReports => 'Recent lab reports';

  @override
  String get recentPrescriptions => 'Recent prescriptions';

  @override
  String get recentlyRegistered => 'Recently registered patients';

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
  String get saveNoteDraft => 'Save note as draft';

  @override
  String get saveVitals => 'Save vitals';

  @override
  String get searchByNameOrCity => 'Search by name or city';

  @override
  String get searchHospitals => 'Search hospitals';

  @override
  String get searchPages => 'Search pages';

  @override
  String get searchPatientName => 'Search by patient name';

  @override
  String get searchPatientsHint => 'Name, mobile number or UHID';

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
  String get staffPortal => 'Staff portal';

  @override
  String get staffSignIn => 'Staff sign in';

  @override
  String get staffSignInIntro => 'Use your hospital staff account.';

  @override
  String get startConsultation => 'Start consultation';

  @override
  String get status => 'Status';

  @override
  String get statusAcknowledged => 'Acknowledged';

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
  String get statusDispensed => 'Dispensed';

  @override
  String get statusInConsultation => 'In consultation';

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
  String get todayAtAGlance => 'Today at a glance';

  @override
  String get todaysAppointments => 'Today\'s appointments';

  @override
  String get todaysPatientFlow => 'Today\'s patient flow';

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
  String get tryAgain => 'Try again';

  @override
  String get typeModuleName => 'Type a module name…';

  @override
  String typeToSearch(int count) {
    return 'Type at least $count letters to search';
  }

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
  String get visits => 'Visits';

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
  String get weWillSendCode => 'We\'ll send a 6-digit verification code';

  @override
  String get welcome => 'Welcome';

  @override
  String get writeInConsultation => 'Write in a consultation';

  @override
  String get yourMobileNumber => 'Your mobile number';
}
