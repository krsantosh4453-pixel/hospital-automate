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

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'HMS'**
  String get appName;

  /// No description provided for @appSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Hospital Management'**
  String get appSubtitle;

  /// No description provided for @navMain.
  ///
  /// In en, this message translates to:
  /// **'Main'**
  String get navMain;

  /// No description provided for @navigation.
  ///
  /// In en, this message translates to:
  /// **'Navigation'**
  String get navigation;

  /// No description provided for @openNavigation.
  ///
  /// In en, this message translates to:
  /// **'Open navigation'**
  String get openNavigation;

  /// No description provided for @closeNavigation.
  ///
  /// In en, this message translates to:
  /// **'Close navigation'**
  String get closeNavigation;

  /// No description provided for @collapseSidebar.
  ///
  /// In en, this message translates to:
  /// **'Collapse sidebar'**
  String get collapseSidebar;

  /// No description provided for @expandSidebar.
  ///
  /// In en, this message translates to:
  /// **'Expand sidebar'**
  String get expandSidebar;

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

  /// No description provided for @typeModuleName.
  ///
  /// In en, this message translates to:
  /// **'Type a module name…'**
  String get typeModuleName;

  /// No description provided for @searchPages.
  ///
  /// In en, this message translates to:
  /// **'Search pages'**
  String get searchPages;

  /// No description provided for @noPageMatches.
  ///
  /// In en, this message translates to:
  /// **'No page matches “{query}”.'**
  String noPageMatches(String query);

  /// No description provided for @hospital.
  ///
  /// In en, this message translates to:
  /// **'Hospital'**
  String get hospital;

  /// No description provided for @selectHospitalTitle.
  ///
  /// In en, this message translates to:
  /// **'Select Hospital'**
  String get selectHospitalTitle;

  /// No description provided for @selectHospital.
  ///
  /// In en, this message translates to:
  /// **'Select hospital'**
  String get selectHospital;

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

  /// No description provided for @notMemberOfAnyHospital.
  ///
  /// In en, this message translates to:
  /// **'You are not a member of any hospital yet.'**
  String get notMemberOfAnyHospital;

  /// No description provided for @noHospitalMatches.
  ///
  /// In en, this message translates to:
  /// **'No hospital matches your search.'**
  String get noHospitalMatches;

  /// No description provided for @switchingHospitalNote.
  ///
  /// In en, this message translates to:
  /// **'Switching hospital changes every list you see to that hospital\'s records.'**
  String get switchingHospitalNote;

  /// No description provided for @interfaceLanguage.
  ///
  /// In en, this message translates to:
  /// **'Interface language'**
  String get interfaceLanguage;

  /// No description provided for @notifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get notifications;

  /// No description provided for @patientSignIn.
  ///
  /// In en, this message translates to:
  /// **'Patient sign in'**
  String get patientSignIn;

  /// No description provided for @staffSignIn.
  ///
  /// In en, this message translates to:
  /// **'Staff sign in'**
  String get staffSignIn;

  /// No description provided for @signIn.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get signIn;

  /// No description provided for @notSignedInSignIn.
  ///
  /// In en, this message translates to:
  /// **'Not signed in · Sign in'**
  String get notSignedInSignIn;

  /// No description provided for @signedInAs.
  ///
  /// In en, this message translates to:
  /// **'Signed in as {name}'**
  String signedInAs(String name);

  /// No description provided for @profileMenuFor.
  ///
  /// In en, this message translates to:
  /// **'Profile menu for {name}'**
  String profileMenuFor(String name);

  /// No description provided for @settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// No description provided for @logout.
  ///
  /// In en, this message translates to:
  /// **'Logout'**
  String get logout;

  /// No description provided for @groupOverview.
  ///
  /// In en, this message translates to:
  /// **'Overview'**
  String get groupOverview;

  /// No description provided for @groupFrontDesk.
  ///
  /// In en, this message translates to:
  /// **'Front desk'**
  String get groupFrontDesk;

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

  /// No description provided for @groupOperations.
  ///
  /// In en, this message translates to:
  /// **'Finance & operations'**
  String get groupOperations;

  /// No description provided for @groupStaff.
  ///
  /// In en, this message translates to:
  /// **'Staff'**
  String get groupStaff;

  /// No description provided for @groupAdministration.
  ///
  /// In en, this message translates to:
  /// **'Administration'**
  String get groupAdministration;

  /// No description provided for @groupSystem.
  ///
  /// In en, this message translates to:
  /// **'System'**
  String get groupSystem;

  /// No description provided for @navHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get navHome;

  /// No description provided for @navPatients.
  ///
  /// In en, this message translates to:
  /// **'Patients'**
  String get navPatients;

  /// No description provided for @navAppointments.
  ///
  /// In en, this message translates to:
  /// **'Appointments'**
  String get navAppointments;

  /// No description provided for @navQueue.
  ///
  /// In en, this message translates to:
  /// **'Queue'**
  String get navQueue;

  /// No description provided for @navConsultation.
  ///
  /// In en, this message translates to:
  /// **'Consultation'**
  String get navConsultation;

  /// No description provided for @navPrescription.
  ///
  /// In en, this message translates to:
  /// **'Prescription'**
  String get navPrescription;

  /// No description provided for @navNurses.
  ///
  /// In en, this message translates to:
  /// **'Nurses / Vitals'**
  String get navNurses;

  /// No description provided for @navIpd.
  ///
  /// In en, this message translates to:
  /// **'IPD / Ward / Beds'**
  String get navIpd;

  /// No description provided for @navEmergency.
  ///
  /// In en, this message translates to:
  /// **'Emergency'**
  String get navEmergency;

  /// No description provided for @navAiScribe.
  ///
  /// In en, this message translates to:
  /// **'AI Scribe'**
  String get navAiScribe;

  /// No description provided for @navLaboratory.
  ///
  /// In en, this message translates to:
  /// **'Laboratory'**
  String get navLaboratory;

  /// No description provided for @navRadiology.
  ///
  /// In en, this message translates to:
  /// **'Radiology'**
  String get navRadiology;

  /// No description provided for @navPharmacy.
  ///
  /// In en, this message translates to:
  /// **'Pharmacy'**
  String get navPharmacy;

  /// No description provided for @navCompounder.
  ///
  /// In en, this message translates to:
  /// **'Compounder'**
  String get navCompounder;

  /// No description provided for @navBloodBank.
  ///
  /// In en, this message translates to:
  /// **'Blood Bank'**
  String get navBloodBank;

  /// No description provided for @navBilling.
  ///
  /// In en, this message translates to:
  /// **'Billing'**
  String get navBilling;

  /// No description provided for @navInventory.
  ///
  /// In en, this message translates to:
  /// **'Inventory'**
  String get navInventory;

  /// No description provided for @navHospitalServices.
  ///
  /// In en, this message translates to:
  /// **'Hospital services'**
  String get navHospitalServices;

  /// No description provided for @navReports.
  ///
  /// In en, this message translates to:
  /// **'Reports'**
  String get navReports;

  /// No description provided for @navDoctors.
  ///
  /// In en, this message translates to:
  /// **'Doctors'**
  String get navDoctors;

  /// No description provided for @navAdminDashboard.
  ///
  /// In en, this message translates to:
  /// **'Admin Dashboard'**
  String get navAdminDashboard;

  /// No description provided for @navUsers.
  ///
  /// In en, this message translates to:
  /// **'Users'**
  String get navUsers;

  /// No description provided for @navRoles.
  ///
  /// In en, this message translates to:
  /// **'Roles'**
  String get navRoles;

  /// No description provided for @navHospitals.
  ///
  /// In en, this message translates to:
  /// **'Hospitals'**
  String get navHospitals;

  /// No description provided for @navDepartments.
  ///
  /// In en, this message translates to:
  /// **'Departments'**
  String get navDepartments;

  /// No description provided for @navNurseDuty.
  ///
  /// In en, this message translates to:
  /// **'Nurse duty'**
  String get navNurseDuty;

  /// No description provided for @navPermissions.
  ///
  /// In en, this message translates to:
  /// **'Permissions'**
  String get navPermissions;

  /// No description provided for @navAuditLog.
  ///
  /// In en, this message translates to:
  /// **'Audit log'**
  String get navAuditLog;

  /// No description provided for @navEmergencyAccess.
  ///
  /// In en, this message translates to:
  /// **'Emergency access'**
  String get navEmergencyAccess;

  /// No description provided for @navSecuritySettings.
  ///
  /// In en, this message translates to:
  /// **'Security settings'**
  String get navSecuritySettings;

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

  /// No description provided for @guestBody.
  ///
  /// In en, this message translates to:
  /// **'Book an appointment, then sign in to follow your visits, prescriptions, reports and bills.'**
  String get guestBody;

  /// No description provided for @bookAppointment.
  ///
  /// In en, this message translates to:
  /// **'Book appointment'**
  String get bookAppointment;

  /// No description provided for @todayAtAGlance.
  ///
  /// In en, this message translates to:
  /// **'Today at a glance'**
  String get todayAtAGlance;

  /// No description provided for @tilePatientsToday.
  ///
  /// In en, this message translates to:
  /// **'Patients registered today'**
  String get tilePatientsToday;

  /// No description provided for @tileAppointmentsToday.
  ///
  /// In en, this message translates to:
  /// **'Appointments today'**
  String get tileAppointmentsToday;

  /// No description provided for @tileWaitingInQueue.
  ///
  /// In en, this message translates to:
  /// **'Waiting in queue'**
  String get tileWaitingInQueue;

  /// No description provided for @tileBedsAvailable.
  ///
  /// In en, this message translates to:
  /// **'Beds available'**
  String get tileBedsAvailable;

  /// No description provided for @tileCurrentAdmissions.
  ///
  /// In en, this message translates to:
  /// **'Current admissions'**
  String get tileCurrentAdmissions;

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

  /// No description provided for @tileLabCompleted.
  ///
  /// In en, this message translates to:
  /// **'Lab tests completed'**
  String get tileLabCompleted;

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

  /// No description provided for @signInToSee.
  ///
  /// In en, this message translates to:
  /// **'Sign in to see'**
  String get signInToSee;

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

  /// No description provided for @deptPatientsText.
  ///
  /// In en, this message translates to:
  /// **'Registration and patient records.'**
  String get deptPatientsText;

  /// No description provided for @deptAppointmentsText.
  ///
  /// In en, this message translates to:
  /// **'Bookings and the daily schedule.'**
  String get deptAppointmentsText;

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

  /// No description provided for @deptConsultationText.
  ///
  /// In en, this message translates to:
  /// **'Doctors\' clinical work.'**
  String get deptConsultationText;

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

  /// No description provided for @deptEmergencyText.
  ///
  /// In en, this message translates to:
  /// **'Triage and emergency care.'**
  String get deptEmergencyText;

  /// No description provided for @deptLaboratoryText.
  ///
  /// In en, this message translates to:
  /// **'Samples, results and reports.'**
  String get deptLaboratoryText;

  /// No description provided for @deptPharmacyText.
  ///
  /// In en, this message translates to:
  /// **'Dispensing and medicine stock.'**
  String get deptPharmacyText;

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

  /// No description provided for @deptBillingText.
  ///
  /// In en, this message translates to:
  /// **'Invoices and payments.'**
  String get deptBillingText;

  /// No description provided for @deptInventoryText.
  ///
  /// In en, this message translates to:
  /// **'Store, suppliers and purchase orders.'**
  String get deptInventoryText;

  /// No description provided for @deptReportsText.
  ///
  /// In en, this message translates to:
  /// **'Hospital statistics.'**
  String get deptReportsText;

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

  /// No description provided for @stepSelectHospitalText.
  ///
  /// In en, this message translates to:
  /// **'Pick where you want to be seen.'**
  String get stepSelectHospitalText;

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

  /// No description provided for @notEligibleTitle.
  ///
  /// In en, this message translates to:
  /// **'You are not eligible for this work'**
  String get notEligibleTitle;

  /// No description provided for @notEligibleBody.
  ///
  /// In en, this message translates to:
  /// **'{department} work is only for {roles}. Please sign in with an account that has one of these roles.'**
  String notEligibleBody(String department, String roles);

  /// No description provided for @close.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get close;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @signInRequired.
  ///
  /// In en, this message translates to:
  /// **'Sign-in required'**
  String get signInRequired;

  /// No description provided for @goodMorning.
  ///
  /// In en, this message translates to:
  /// **'Good morning'**
  String get goodMorning;

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

  /// No description provided for @greetingWithName.
  ///
  /// In en, this message translates to:
  /// **'{greeting}, {name}'**
  String greetingWithName(String greeting, String name);

  /// No description provided for @dashboardLoadFailed.
  ///
  /// In en, this message translates to:
  /// **'Dashboard figures could not be loaded'**
  String get dashboardLoadFailed;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// No description provided for @todaysPatientFlow.
  ///
  /// In en, this message translates to:
  /// **'Today\'s patient flow'**
  String get todaysPatientFlow;

  /// No description provided for @liveCounts.
  ///
  /// In en, this message translates to:
  /// **'Live counts for the selected hospital.'**
  String get liveCounts;

  /// No description provided for @open.
  ///
  /// In en, this message translates to:
  /// **'Open'**
  String get open;

  /// No description provided for @queueStatus.
  ///
  /// In en, this message translates to:
  /// **'Queue status'**
  String get queueStatus;

  /// No description provided for @statusWaiting.
  ///
  /// In en, this message translates to:
  /// **'Waiting'**
  String get statusWaiting;

  /// No description provided for @statusInConsultation.
  ///
  /// In en, this message translates to:
  /// **'In consultation'**
  String get statusInConsultation;

  /// No description provided for @statusCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get statusCompleted;

  /// No description provided for @appointmentStatus.
  ///
  /// In en, this message translates to:
  /// **'Appointment status'**
  String get appointmentStatus;

  /// No description provided for @statusPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get statusPending;

  /// No description provided for @labTestStatus.
  ///
  /// In en, this message translates to:
  /// **'Lab test status'**
  String get labTestStatus;

  /// No description provided for @statusUrgent.
  ///
  /// In en, this message translates to:
  /// **'Urgent'**
  String get statusUrgent;

  /// No description provided for @recentlyRegistered.
  ///
  /// In en, this message translates to:
  /// **'Recently registered patients'**
  String get recentlyRegistered;

  /// No description provided for @viewAll.
  ///
  /// In en, this message translates to:
  /// **'View all'**
  String get viewAll;

  /// No description provided for @loading.
  ///
  /// In en, this message translates to:
  /// **'Loading…'**
  String get loading;

  /// No description provided for @noPatientsYet.
  ///
  /// In en, this message translates to:
  /// **'No patients registered yet'**
  String get noPatientsYet;

  /// No description provided for @needsAttention.
  ///
  /// In en, this message translates to:
  /// **'Needs attention'**
  String get needsAttention;

  /// No description provided for @checking.
  ///
  /// In en, this message translates to:
  /// **'Checking…'**
  String get checking;

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

  /// No description provided for @quickActions.
  ///
  /// In en, this message translates to:
  /// **'Quick actions'**
  String get quickActions;

  /// No description provided for @actionRegisterPatient.
  ///
  /// In en, this message translates to:
  /// **'Register patient'**
  String get actionRegisterPatient;

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

  /// No description provided for @actionStartConsultation.
  ///
  /// In en, this message translates to:
  /// **'Start consultation'**
  String get actionStartConsultation;

  /// No description provided for @actionDispenseMedicines.
  ///
  /// In en, this message translates to:
  /// **'Dispense medicines'**
  String get actionDispenseMedicines;

  /// No description provided for @actionLabWorklist.
  ///
  /// In en, this message translates to:
  /// **'Lab worklist'**
  String get actionLabWorklist;

  /// No description provided for @actionCreateInvoice.
  ///
  /// In en, this message translates to:
  /// **'Create invoice'**
  String get actionCreateInvoice;

  /// No description provided for @actionFindPatient.
  ///
  /// In en, this message translates to:
  /// **'Find a patient'**
  String get actionFindPatient;

  /// No description provided for @actionPrescriptions.
  ///
  /// In en, this message translates to:
  /// **'Prescriptions'**
  String get actionPrescriptions;

  /// No description provided for @actionAiScribe.
  ///
  /// In en, this message translates to:
  /// **'AI scribe'**
  String get actionAiScribe;

  /// No description provided for @actionLabResults.
  ///
  /// In en, this message translates to:
  /// **'Lab results'**
  String get actionLabResults;

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

  /// No description provided for @actionCompounding.
  ///
  /// In en, this message translates to:
  /// **'Compounding'**
  String get actionCompounding;

  /// No description provided for @actionMedicineStock.
  ///
  /// In en, this message translates to:
  /// **'Medicine stock'**
  String get actionMedicineStock;

  /// No description provided for @actionBloodStock.
  ///
  /// In en, this message translates to:
  /// **'Blood stock and requests'**
  String get actionBloodStock;

  /// No description provided for @operations.
  ///
  /// In en, this message translates to:
  /// **'Operations'**
  String get operations;

  /// No description provided for @emergencyVisitsToday.
  ///
  /// In en, this message translates to:
  /// **'Emergency visits today'**
  String get emergencyVisitsToday;

  /// No description provided for @invoicesPaidTotal.
  ///
  /// In en, this message translates to:
  /// **'Invoices paid / total'**
  String get invoicesPaidTotal;

  /// No description provided for @registeredInTotal.
  ///
  /// In en, this message translates to:
  /// **'{count} registered in total'**
  String registeredInTotal(String count);

  /// No description provided for @countPending.
  ///
  /// In en, this message translates to:
  /// **'{count} pending'**
  String countPending(String count);

  /// No description provided for @nowServingToken.
  ///
  /// In en, this message translates to:
  /// **'Now serving token {token}'**
  String nowServingToken(String token);

  /// No description provided for @noTokenServed.
  ///
  /// In en, this message translates to:
  /// **'No token being served'**
  String get noTokenServed;

  /// No description provided for @bedsOccupiedOf.
  ///
  /// In en, this message translates to:
  /// **'{occupied} occupied of {total}'**
  String bedsOccupiedOf(String occupied, String total);

  /// No description provided for @noBedsAvailable.
  ///
  /// In en, this message translates to:
  /// **'No beds available'**
  String get noBedsAvailable;

  /// No description provided for @attentionEmergency.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 active emergency case} other{{count} active emergency cases}}'**
  String attentionEmergency(int count);

  /// No description provided for @attentionUrgentLab.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 urgent lab test} other{{count} urgent lab tests}}'**
  String attentionUrgentLab(int count);

  /// No description provided for @attentionQueue.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 patient waiting in the queue} other{{count} patients waiting in the queue}}'**
  String attentionQueue(int count);

  /// No description provided for @attentionLabPending.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 lab test pending} other{{count} lab tests pending}}'**
  String attentionLabPending(int count);

  /// No description provided for @attentionBilling.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 invoice awaiting payment} other{{count} invoices awaiting payment}}'**
  String attentionBilling(int count);

  /// No description provided for @ageYears.
  ///
  /// In en, this message translates to:
  /// **'{age} y'**
  String ageYears(String age);

  /// No description provided for @welcome.
  ///
  /// In en, this message translates to:
  /// **'Welcome'**
  String get welcome;

  /// No description provided for @selectHospitalForDashboard.
  ///
  /// In en, this message translates to:
  /// **'Select a hospital from the header to see its dashboard.'**
  String get selectHospitalForDashboard;

  /// No description provided for @roleHomeDoctor.
  ///
  /// In en, this message translates to:
  /// **'Your clinic today'**
  String get roleHomeDoctor;

  /// No description provided for @roleHomeNurse.
  ///
  /// In en, this message translates to:
  /// **'Your ward today'**
  String get roleHomeNurse;

  /// No description provided for @roleHomeReceptionist.
  ///
  /// In en, this message translates to:
  /// **'Front desk today'**
  String get roleHomeReceptionist;

  /// No description provided for @roleHomePharmacy.
  ///
  /// In en, this message translates to:
  /// **'Pharmacy today'**
  String get roleHomePharmacy;

  /// No description provided for @roleHomeLaboratory.
  ///
  /// In en, this message translates to:
  /// **'Laboratory today'**
  String get roleHomeLaboratory;

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

  /// No description provided for @roleHomeStore.
  ///
  /// In en, this message translates to:
  /// **'Store today'**
  String get roleHomeStore;

  /// No description provided for @roleAdmin.
  ///
  /// In en, this message translates to:
  /// **'Admin'**
  String get roleAdmin;

  /// No description provided for @roleDoctor.
  ///
  /// In en, this message translates to:
  /// **'Doctor'**
  String get roleDoctor;

  /// No description provided for @roleNurse.
  ///
  /// In en, this message translates to:
  /// **'Nurse'**
  String get roleNurse;

  /// No description provided for @roleCompounder.
  ///
  /// In en, this message translates to:
  /// **'Compounder'**
  String get roleCompounder;

  /// No description provided for @roleReceptionist.
  ///
  /// In en, this message translates to:
  /// **'Receptionist'**
  String get roleReceptionist;

  /// No description provided for @rolePharmacist.
  ///
  /// In en, this message translates to:
  /// **'Pharmacist'**
  String get rolePharmacist;

  /// No description provided for @roleLabStaff.
  ///
  /// In en, this message translates to:
  /// **'Lab Staff'**
  String get roleLabStaff;

  /// No description provided for @roleBloodBankStaff.
  ///
  /// In en, this message translates to:
  /// **'Blood Bank Staff'**
  String get roleBloodBankStaff;

  /// No description provided for @roleBillingStaff.
  ///
  /// In en, this message translates to:
  /// **'Billing Staff'**
  String get roleBillingStaff;

  /// No description provided for @roleInventoryStaff.
  ///
  /// In en, this message translates to:
  /// **'Inventory Staff'**
  String get roleInventoryStaff;

  /// No description provided for @roleHospitalManager.
  ///
  /// In en, this message translates to:
  /// **'Hospital Manager'**
  String get roleHospitalManager;

  /// No description provided for @tryAgain.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get tryAgain;

  /// No description provided for @noAccessTitle.
  ///
  /// In en, this message translates to:
  /// **'You don\'t have access'**
  String get noAccessTitle;

  /// No description provided for @somethingWentWrong.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong'**
  String get somethingWentWrong;

  /// No description provided for @signInToOpen.
  ///
  /// In en, this message translates to:
  /// **'Sign in with a staff account that may open {module}.'**
  String signInToOpen(String module);

  /// No description provided for @signInUnavailableTitle.
  ///
  /// In en, this message translates to:
  /// **'Sign-in is not in this app version yet'**
  String get signInUnavailableTitle;

  /// No description provided for @signInUnavailableBody.
  ///
  /// In en, this message translates to:
  /// **'Staff and patient sign-in come with the next app update. Until then, use the web app to sign in.'**
  String get signInUnavailableBody;

  /// No description provided for @moduleNotOnMobileTitle.
  ///
  /// In en, this message translates to:
  /// **'{module} is not in the mobile app yet'**
  String moduleNotOnMobileTitle(String module);

  /// No description provided for @moduleNotOnMobileBody.
  ///
  /// In en, this message translates to:
  /// **'This module will be added in a later app update. Use the web app for this work until then.'**
  String get moduleNotOnMobileBody;

  /// No description provided for @backToHome.
  ///
  /// In en, this message translates to:
  /// **'Back to home'**
  String get backToHome;

  /// No description provided for @appSettingsIntro.
  ///
  /// In en, this message translates to:
  /// **'Settings for this device.'**
  String get appSettingsIntro;

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

  /// No description provided for @backend.
  ///
  /// In en, this message translates to:
  /// **'Backend'**
  String get backend;

  /// No description provided for @checkingConnection.
  ///
  /// In en, this message translates to:
  /// **'Checking connection…'**
  String get checkingConnection;

  /// No description provided for @checkAgain.
  ///
  /// In en, this message translates to:
  /// **'Check again'**
  String get checkAgain;

  /// No description provided for @errorNetwork.
  ///
  /// In en, this message translates to:
  /// **'Cannot reach the server. Check the connection and try again.'**
  String get errorNetwork;

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

  /// No description provided for @errorForbidden.
  ///
  /// In en, this message translates to:
  /// **'Your role does not have access to this in the selected hospital.'**
  String get errorForbidden;

  /// No description provided for @errorNotFound.
  ///
  /// In en, this message translates to:
  /// **'This record was not found in the selected hospital.'**
  String get errorNotFound;

  /// No description provided for @errorValidation.
  ///
  /// In en, this message translates to:
  /// **'Some details are not valid. Check the form and try again.'**
  String get errorValidation;

  /// No description provided for @errorConflict.
  ///
  /// In en, this message translates to:
  /// **'This record changed or already exists. Refresh and try again.'**
  String get errorConflict;

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

  /// No description provided for @staffPortal.
  ///
  /// In en, this message translates to:
  /// **'Staff portal'**
  String get staffPortal;

  /// No description provided for @patientPortal.
  ///
  /// In en, this message translates to:
  /// **'Patient portal'**
  String get patientPortal;

  /// No description provided for @signInTitle.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get signInTitle;

  /// No description provided for @staffSignInIntro.
  ///
  /// In en, this message translates to:
  /// **'Use your hospital staff account.'**
  String get staffSignInIntro;

  /// No description provided for @usernameOrEmail.
  ///
  /// In en, this message translates to:
  /// **'Username or email'**
  String get usernameOrEmail;

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @continueAction.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueAction;

  /// No description provided for @forgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get forgotPassword;

  /// No description provided for @enterTheCode.
  ///
  /// In en, this message translates to:
  /// **'Enter the code'**
  String get enterTheCode;

  /// No description provided for @codeSentToMobile.
  ///
  /// In en, this message translates to:
  /// **'We sent a 6-digit code to your mobile ({maskedPhone}).'**
  String codeSentToMobile(String maskedPhone);

  /// No description provided for @sixDigitCode.
  ///
  /// In en, this message translates to:
  /// **'6-digit code'**
  String get sixDigitCode;

  /// No description provided for @verifyAndContinue.
  ///
  /// In en, this message translates to:
  /// **'Verify and continue'**
  String get verifyAndContinue;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get back;

  /// No description provided for @resendCode.
  ///
  /// In en, this message translates to:
  /// **'Resend code'**
  String get resendCode;

  /// No description provided for @codeResent.
  ///
  /// In en, this message translates to:
  /// **'A new code was sent.'**
  String get codeResent;

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

  /// No description provided for @resetConfirmIntro.
  ///
  /// In en, this message translates to:
  /// **'Enter the code from the SMS and choose a new password.'**
  String get resetConfirmIntro;

  /// No description provided for @codeFromSms.
  ///
  /// In en, this message translates to:
  /// **'Code from SMS'**
  String get codeFromSms;

  /// No description provided for @newPassword.
  ///
  /// In en, this message translates to:
  /// **'New password'**
  String get newPassword;

  /// No description provided for @atLeast8Characters.
  ///
  /// In en, this message translates to:
  /// **'At least 8 characters.'**
  String get atLeast8Characters;

  /// No description provided for @sendResetCode.
  ///
  /// In en, this message translates to:
  /// **'Send reset code'**
  String get sendResetCode;

  /// No description provided for @setNewPassword.
  ///
  /// In en, this message translates to:
  /// **'Set new password'**
  String get setNewPassword;

  /// No description provided for @backToSignIn.
  ///
  /// In en, this message translates to:
  /// **'Back to sign in'**
  String get backToSignIn;

  /// No description provided for @resetCodeSent.
  ///
  /// In en, this message translates to:
  /// **'If an active staff account matches, a code was sent to its registered mobile number.'**
  String get resetCodeSent;

  /// No description provided for @passwordUpdated.
  ///
  /// In en, this message translates to:
  /// **'Password updated. Sign in with your new password.'**
  String get passwordUpdated;

  /// No description provided for @patientSignInIntro.
  ///
  /// In en, this message translates to:
  /// **'Patients see their own appointments, prescriptions, reports and bills.'**
  String get patientSignInIntro;

  /// No description provided for @signInMethod.
  ///
  /// In en, this message translates to:
  /// **'Sign-in method'**
  String get signInMethod;

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

  /// No description provided for @tabEmail.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get tabEmail;

  /// No description provided for @loginWithMobile.
  ///
  /// In en, this message translates to:
  /// **'Login with Mobile'**
  String get loginWithMobile;

  /// No description provided for @weWillSendCode.
  ///
  /// In en, this message translates to:
  /// **'We\'ll send a 6-digit verification code'**
  String get weWillSendCode;

  /// No description provided for @mobileNumber.
  ///
  /// In en, this message translates to:
  /// **'Mobile number'**
  String get mobileNumber;

  /// No description provided for @enter10DigitNumber.
  ///
  /// In en, this message translates to:
  /// **'Enter 10-digit number'**
  String get enter10DigitNumber;

  /// No description provided for @sendOtp.
  ///
  /// In en, this message translates to:
  /// **'Send OTP'**
  String get sendOtp;

  /// No description provided for @verifyOtp.
  ///
  /// In en, this message translates to:
  /// **'Verify OTP'**
  String get verifyOtp;

  /// No description provided for @otpSentTo.
  ///
  /// In en, this message translates to:
  /// **'Enter the 6-digit OTP sent to {phone}'**
  String otpSentTo(String phone);

  /// No description provided for @verifyAndContinueShort.
  ///
  /// In en, this message translates to:
  /// **'Verify & Continue'**
  String get verifyAndContinueShort;

  /// No description provided for @changeNumber.
  ///
  /// In en, this message translates to:
  /// **'Change number'**
  String get changeNumber;

  /// No description provided for @otpPrintedOnServer.
  ///
  /// In en, this message translates to:
  /// **'Development server: the code is printed in the server log, not sent by SMS.'**
  String get otpPrintedOnServer;

  /// No description provided for @loginWithEmail.
  ///
  /// In en, this message translates to:
  /// **'Login with Email'**
  String get loginWithEmail;

  /// No description provided for @emailLoginIntro.
  ///
  /// In en, this message translates to:
  /// **'Use the email and password from your patient account.'**
  String get emailLoginIntro;

  /// No description provided for @email.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @emailNotVerifiedSendOtp.
  ///
  /// In en, this message translates to:
  /// **'Email not verified? Send email OTP'**
  String get emailNotVerifiedSendOtp;

  /// No description provided for @sendEmailOtp.
  ///
  /// In en, this message translates to:
  /// **'Send Email OTP'**
  String get sendEmailOtp;

  /// No description provided for @otpLabel.
  ///
  /// In en, this message translates to:
  /// **'OTP'**
  String get otpLabel;

  /// No description provided for @backToEmailLogin.
  ///
  /// In en, this message translates to:
  /// **'Back to email login'**
  String get backToEmailLogin;

  /// No description provided for @emailVerifiedSignIn.
  ///
  /// In en, this message translates to:
  /// **'Email verified. You can now sign in with your email and password.'**
  String get emailVerifiedSignIn;

  /// No description provided for @loginWithTokenId.
  ///
  /// In en, this message translates to:
  /// **'Login with Token / ID'**
  String get loginWithTokenId;

  /// No description provided for @tokenIdIntro.
  ///
  /// In en, this message translates to:
  /// **'Enter your token number or hospital patient ID'**
  String get tokenIdIntro;

  /// No description provided for @tokenOrPatientId.
  ///
  /// In en, this message translates to:
  /// **'Token Number / Patient ID'**
  String get tokenOrPatientId;

  /// No description provided for @tokenIdHint.
  ///
  /// In en, this message translates to:
  /// **'Use the patient ID from registration together with your account password.'**
  String get tokenIdHint;

  /// No description provided for @lookupAndLogin.
  ///
  /// In en, this message translates to:
  /// **'Lookup & Login'**
  String get lookupAndLogin;

  /// No description provided for @newToHms.
  ///
  /// In en, this message translates to:
  /// **'New to the Hospital Management System?'**
  String get newToHms;

  /// No description provided for @createAccount.
  ///
  /// In en, this message translates to:
  /// **'Create Account'**
  String get createAccount;

  /// No description provided for @registerTitle.
  ///
  /// In en, this message translates to:
  /// **'Create your patient account'**
  String get registerTitle;

  /// No description provided for @registerIntro.
  ///
  /// In en, this message translates to:
  /// **'Staff accounts are created by invitation from your hospital.'**
  String get registerIntro;

  /// No description provided for @fullName.
  ///
  /// In en, this message translates to:
  /// **'Full name'**
  String get fullName;

  /// No description provided for @confirmPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm password'**
  String get confirmPassword;

  /// No description provided for @gender.
  ///
  /// In en, this message translates to:
  /// **'Gender'**
  String get gender;

  /// No description provided for @genderMale.
  ///
  /// In en, this message translates to:
  /// **'Male'**
  String get genderMale;

  /// No description provided for @genderFemale.
  ///
  /// In en, this message translates to:
  /// **'Female'**
  String get genderFemale;

  /// No description provided for @genderOther.
  ///
  /// In en, this message translates to:
  /// **'Other'**
  String get genderOther;

  /// No description provided for @verifyYourEmail.
  ///
  /// In en, this message translates to:
  /// **'Verify your email'**
  String get verifyYourEmail;

  /// No description provided for @verifyEmailIntro.
  ///
  /// In en, this message translates to:
  /// **'Enter the code sent to {email}. Then sign in with your email and password.'**
  String verifyEmailIntro(String email);

  /// No description provided for @emailCodeNotSent.
  ///
  /// In en, this message translates to:
  /// **'The verification email could not be sent. Ask the hospital to check its email settings.'**
  String get emailCodeNotSent;

  /// No description provided for @haveAccountSignIn.
  ///
  /// In en, this message translates to:
  /// **'Already have an account? Sign in'**
  String get haveAccountSignIn;

  /// No description provided for @restoringSession.
  ///
  /// In en, this message translates to:
  /// **'Opening your session…'**
  String get restoringSession;

  /// No description provided for @restoreFailedTitle.
  ///
  /// In en, this message translates to:
  /// **'Could not reach the hospital server'**
  String get restoreFailedTitle;

  /// No description provided for @restoreFailedBody.
  ///
  /// In en, this message translates to:
  /// **'Your sign-in is kept on this device. Check the connection and try again, or sign out.'**
  String get restoreFailedBody;

  /// No description provided for @sessionEndedNotice.
  ///
  /// In en, this message translates to:
  /// **'Your session has ended. Please sign in again.'**
  String get sessionEndedNotice;

  /// No description provided for @signOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get signOut;

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

  /// No description provided for @thisDevice.
  ///
  /// In en, this message translates to:
  /// **'This device'**
  String get thisDevice;

  /// No description provided for @lastActive.
  ///
  /// In en, this message translates to:
  /// **'Last active {time}'**
  String lastActive(String time);

  /// No description provided for @signOutDevice.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get signOutDevice;

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

  /// No description provided for @signOutDeviceConfirm.
  ///
  /// In en, this message translates to:
  /// **'Sign this device out?'**
  String get signOutDeviceConfirm;

  /// No description provided for @noOtherDevices.
  ///
  /// In en, this message translates to:
  /// **'No signed-in devices.'**
  String get noOtherDevices;

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

  /// No description provided for @platformWeb.
  ///
  /// In en, this message translates to:
  /// **'Web browser'**
  String get platformWeb;

  /// No description provided for @platformOther.
  ///
  /// In en, this message translates to:
  /// **'Other device'**
  String get platformOther;

  /// No description provided for @actingAs.
  ///
  /// In en, this message translates to:
  /// **'Acting as {role}'**
  String actingAs(String role);

  /// No description provided for @accountPatient.
  ///
  /// In en, this message translates to:
  /// **'Patient'**
  String get accountPatient;

  /// No description provided for @accountFamily.
  ///
  /// In en, this message translates to:
  /// **'Family member (view only)'**
  String get accountFamily;

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

  /// No description provided for @noHospitalAccess.
  ///
  /// In en, this message translates to:
  /// **'Your account is not active in any hospital yet. Ask your hospital administrator.'**
  String get noHospitalAccess;

  /// No description provided for @patientHomeIntro.
  ///
  /// In en, this message translates to:
  /// **'Your hospitals and profile. Appointments, prescriptions, reports and bills open in later app updates.'**
  String get patientHomeIntro;

  /// No description provided for @myProfile.
  ///
  /// In en, this message translates to:
  /// **'My profile'**
  String get myProfile;

  /// No description provided for @myHospitals.
  ///
  /// In en, this message translates to:
  /// **'My hospitals'**
  String get myHospitals;

  /// No description provided for @verified.
  ///
  /// In en, this message translates to:
  /// **'Verified'**
  String get verified;

  /// No description provided for @notVerified.
  ///
  /// In en, this message translates to:
  /// **'Not verified'**
  String get notVerified;

  /// No description provided for @patientNavHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get patientNavHome;

  /// No description provided for @patientNavAppointments.
  ///
  /// In en, this message translates to:
  /// **'My Appointments'**
  String get patientNavAppointments;

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

  /// No description provided for @patientNavPrescriptions.
  ///
  /// In en, this message translates to:
  /// **'My Prescriptions'**
  String get patientNavPrescriptions;

  /// No description provided for @patientNavLab.
  ///
  /// In en, this message translates to:
  /// **'My Lab Reports'**
  String get patientNavLab;

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

  /// No description provided for @groupPatientPortal.
  ///
  /// In en, this message translates to:
  /// **'My health'**
  String get groupPatientPortal;

  /// No description provided for @authFieldsRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your username or email and password.'**
  String get authFieldsRequired;

  /// No description provided for @authInvalidCredentials.
  ///
  /// In en, this message translates to:
  /// **'The username, email or password is not correct.'**
  String get authInvalidCredentials;

  /// No description provided for @authAccountDisabled.
  ///
  /// In en, this message translates to:
  /// **'This account is disabled. Contact your hospital administrator.'**
  String get authAccountDisabled;

  /// No description provided for @authNotStaff.
  ///
  /// In en, this message translates to:
  /// **'This account is not an active staff account. Patients sign in on the patient portal.'**
  String get authNotStaff;

  /// No description provided for @authLockedOut.
  ///
  /// In en, this message translates to:
  /// **'Too many failed sign-in attempts. Try again in 15 minutes or reset your password.'**
  String get authLockedOut;

  /// No description provided for @authOtpRequiredUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This server requires an SMS code, but SMS is not set up. Contact your hospital administrator.'**
  String get authOtpRequiredUnavailable;

  /// No description provided for @authChallengeExpired.
  ///
  /// In en, this message translates to:
  /// **'Your sign-in step expired. Enter your password again.'**
  String get authChallengeExpired;

  /// No description provided for @authInvalidOtp.
  ///
  /// In en, this message translates to:
  /// **'The code is not correct.'**
  String get authInvalidOtp;

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

  /// No description provided for @authOtpCooldown.
  ///
  /// In en, this message translates to:
  /// **'Please wait a minute before asking for another code.'**
  String get authOtpCooldown;

  /// No description provided for @authTooManyRequests.
  ///
  /// In en, this message translates to:
  /// **'Too many attempts. Please try again later.'**
  String get authTooManyRequests;

  /// No description provided for @authInvalidPhone.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid 10-digit mobile number.'**
  String get authInvalidPhone;

  /// No description provided for @authInvalidEmail.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid email address.'**
  String get authInvalidEmail;

  /// No description provided for @authEmailNotVerified.
  ///
  /// In en, this message translates to:
  /// **'Your email is not verified yet. Send an email OTP to verify it.'**
  String get authEmailNotVerified;

  /// No description provided for @authStaffUseStaffLogin.
  ///
  /// In en, this message translates to:
  /// **'Staff accounts sign in on the staff portal.'**
  String get authStaffUseStaffLogin;

  /// No description provided for @authSmsUnavailable.
  ///
  /// In en, this message translates to:
  /// **'SMS codes are not set up on this server. Use another sign-in method or contact the hospital.'**
  String get authSmsUnavailable;

  /// No description provided for @authResetUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Password reset by SMS is not set up on this server. Contact your hospital administrator.'**
  String get authResetUnavailable;

  /// No description provided for @authResetCodeInvalid.
  ///
  /// In en, this message translates to:
  /// **'The code is not correct or has expired.'**
  String get authResetCodeInvalid;

  /// No description provided for @authPasswordTooShort.
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 8 characters.'**
  String get authPasswordTooShort;

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

  /// No description provided for @authNameRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your full name.'**
  String get authNameRequired;

  /// No description provided for @authInvalidDob.
  ///
  /// In en, this message translates to:
  /// **'The date of birth is not valid.'**
  String get authInvalidDob;

  /// No description provided for @authEmailExists.
  ///
  /// In en, this message translates to:
  /// **'An account already exists with this email. Sign in instead.'**
  String get authEmailExists;

  /// No description provided for @authPhoneExists.
  ///
  /// In en, this message translates to:
  /// **'An account already exists with this mobile number. Sign in instead.'**
  String get authPhoneExists;

  /// No description provided for @authStaffInviteOnly.
  ///
  /// In en, this message translates to:
  /// **'Staff accounts are created by your hospital. Ask its administrator for an invitation.'**
  String get authStaffInviteOnly;

  /// No description provided for @authNotAllowed.
  ///
  /// In en, this message translates to:
  /// **'This sign-in is not allowed for this account.'**
  String get authNotAllowed;

  /// No description provided for @authUnsupportedAccount.
  ///
  /// In en, this message translates to:
  /// **'This account cannot use the mobile app. Use the web app.'**
  String get authUnsupportedAccount;

  /// No description provided for @authEmailSendFailed.
  ///
  /// In en, this message translates to:
  /// **'The verification email could not be sent. Try again later.'**
  String get authEmailSendFailed;

  /// No description provided for @fieldRequired.
  ///
  /// In en, this message translates to:
  /// **'Required'**
  String get fieldRequired;

  /// No description provided for @refreshFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not refresh'**
  String get refreshFailed;

  /// No description provided for @statusScheduled.
  ///
  /// In en, this message translates to:
  /// **'Scheduled'**
  String get statusScheduled;

  /// No description provided for @statusCheckedIn.
  ///
  /// In en, this message translates to:
  /// **'Checked in'**
  String get statusCheckedIn;

  /// No description provided for @statusCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get statusCancelled;

  /// No description provided for @statusNoShow.
  ///
  /// In en, this message translates to:
  /// **'No show'**
  String get statusNoShow;

  /// No description provided for @statusCalled.
  ///
  /// In en, this message translates to:
  /// **'Called'**
  String get statusCalled;

  /// No description provided for @statusAcknowledged.
  ///
  /// In en, this message translates to:
  /// **'Acknowledged'**
  String get statusAcknowledged;

  /// No description provided for @statusReady.
  ///
  /// In en, this message translates to:
  /// **'Ready'**
  String get statusReady;

  /// No description provided for @statusConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Confirmed'**
  String get statusConfirmed;

  /// No description provided for @statusDispensed.
  ///
  /// In en, this message translates to:
  /// **'Dispensed'**
  String get statusDispensed;

  /// No description provided for @statusPartiallyDispensed.
  ///
  /// In en, this message translates to:
  /// **'Partly dispensed'**
  String get statusPartiallyDispensed;

  /// No description provided for @statusReleased.
  ///
  /// In en, this message translates to:
  /// **'Released'**
  String get statusReleased;

  /// No description provided for @statusUnpaid.
  ///
  /// In en, this message translates to:
  /// **'Unpaid'**
  String get statusUnpaid;

  /// No description provided for @statusPartiallyPaid.
  ///
  /// In en, this message translates to:
  /// **'Partly paid'**
  String get statusPartiallyPaid;

  /// No description provided for @statusPaid.
  ///
  /// In en, this message translates to:
  /// **'Paid'**
  String get statusPaid;

  /// No description provided for @bookAppointmentIntro.
  ///
  /// In en, this message translates to:
  /// **'Choose a doctor, a date and a free time.'**
  String get bookAppointmentIntro;

  /// No description provided for @bookingNoHospital.
  ///
  /// In en, this message translates to:
  /// **'You are not registered at any hospital yet. Please register at the reception first.'**
  String get bookingNoHospital;

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

  /// No description provided for @bookingRejected.
  ///
  /// In en, this message translates to:
  /// **'The hospital could not accept this booking. Check the details and try again.'**
  String get bookingRejected;

  /// No description provided for @doctor.
  ///
  /// In en, this message translates to:
  /// **'Doctor'**
  String get doctor;

  /// No description provided for @selectDoctor.
  ///
  /// In en, this message translates to:
  /// **'Select doctor'**
  String get selectDoctor;

  /// No description provided for @date.
  ///
  /// In en, this message translates to:
  /// **'Date'**
  String get date;

  /// No description provided for @chooseDoctorFirst.
  ///
  /// In en, this message translates to:
  /// **'Choose a doctor to see free times.'**
  String get chooseDoctorFirst;

  /// No description provided for @noFreeSlots.
  ///
  /// In en, this message translates to:
  /// **'No free time on this day. Try another date.'**
  String get noFreeSlots;

  /// No description provided for @reasonForVisit.
  ///
  /// In en, this message translates to:
  /// **'Reason for visit'**
  String get reasonForVisit;

  /// No description provided for @confirmBooking.
  ///
  /// In en, this message translates to:
  /// **'Confirm booking'**
  String get confirmBooking;

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

  /// No description provided for @appointmentId.
  ///
  /// In en, this message translates to:
  /// **'Appointment ID'**
  String get appointmentId;

  /// No description provided for @status.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get status;

  /// No description provided for @viewMyAppointments.
  ///
  /// In en, this message translates to:
  /// **'View my appointments'**
  String get viewMyAppointments;

  /// No description provided for @filterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get filterAll;

  /// No description provided for @filterUpcoming.
  ///
  /// In en, this message translates to:
  /// **'Upcoming'**
  String get filterUpcoming;

  /// No description provided for @filterPast.
  ///
  /// In en, this message translates to:
  /// **'Past'**
  String get filterPast;

  /// No description provided for @filterCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get filterCancelled;

  /// No description provided for @appointmentsIntro.
  ///
  /// In en, this message translates to:
  /// **'Your bookings at the selected hospital.'**
  String get appointmentsIntro;

  /// No description provided for @appointmentChangesAtHospital.
  ///
  /// In en, this message translates to:
  /// **'To cancel or change an appointment, please contact the hospital reception.'**
  String get appointmentChangesAtHospital;

  /// No description provided for @noAppointmentsYet.
  ///
  /// In en, this message translates to:
  /// **'No appointments yet'**
  String get noAppointmentsYet;

  /// No description provided for @noAppointmentsMatch.
  ///
  /// In en, this message translates to:
  /// **'No appointments match this filter'**
  String get noAppointmentsMatch;

  /// No description provided for @noAppointmentsYetHint.
  ///
  /// In en, this message translates to:
  /// **'Use Book appointment to choose a doctor and a time.'**
  String get noAppointmentsYetHint;

  /// No description provided for @appointmentDetails.
  ///
  /// In en, this message translates to:
  /// **'Appointment details'**
  String get appointmentDetails;

  /// No description provided for @queueIntro.
  ///
  /// In en, this message translates to:
  /// **'Your place in today\'s consultation queue. This page checks again every 30 seconds while it is open.'**
  String get queueIntro;

  /// No description provided for @lastChecked.
  ///
  /// In en, this message translates to:
  /// **'Last checked at {time}'**
  String lastChecked(String time);

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

  /// No description provided for @tokenNumber.
  ///
  /// In en, this message translates to:
  /// **'Token {number}'**
  String tokenNumber(String number);

  /// No description provided for @queuePosition.
  ///
  /// In en, this message translates to:
  /// **'Position in queue'**
  String get queuePosition;

  /// No description provided for @estimatedWait.
  ///
  /// In en, this message translates to:
  /// **'Estimated wait'**
  String get estimatedWait;

  /// No description provided for @minutesShort.
  ///
  /// In en, this message translates to:
  /// **'{minutes} min'**
  String minutesShort(String minutes);

  /// No description provided for @expectedAround.
  ///
  /// In en, this message translates to:
  /// **'Expected around'**
  String get expectedAround;

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

  /// No description provided for @tokenNext.
  ///
  /// In en, this message translates to:
  /// **'You are next. The doctor will see you shortly.'**
  String get tokenNext;

  /// No description provided for @estimatesAreApproximate.
  ///
  /// In en, this message translates to:
  /// **'Wait times are estimates, not appointment times. Please stay nearby so you don\'t miss your call.'**
  String get estimatesAreApproximate;

  /// No description provided for @prescriptionsIntro.
  ///
  /// In en, this message translates to:
  /// **'Medicines your doctors have prescribed.'**
  String get prescriptionsIntro;

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

  /// No description provided for @noMedicinesListed.
  ///
  /// In en, this message translates to:
  /// **'No medicines listed'**
  String get noMedicinesListed;

  /// No description provided for @dosage.
  ///
  /// In en, this message translates to:
  /// **'Dosage'**
  String get dosage;

  /// No description provided for @frequency.
  ///
  /// In en, this message translates to:
  /// **'Frequency'**
  String get frequency;

  /// No description provided for @duration.
  ///
  /// In en, this message translates to:
  /// **'Duration'**
  String get duration;

  /// No description provided for @quantity.
  ///
  /// In en, this message translates to:
  /// **'Quantity'**
  String get quantity;

  /// No description provided for @instructions.
  ///
  /// In en, this message translates to:
  /// **'Instructions'**
  String get instructions;

  /// No description provided for @labIntro.
  ///
  /// In en, this message translates to:
  /// **'Results released by the laboratory.'**
  String get labIntro;

  /// No description provided for @labReleasedOnly.
  ///
  /// In en, this message translates to:
  /// **'Reports appear here after the laboratory has checked and released them.'**
  String get labReleasedOnly;

  /// No description provided for @labNotADiagnosis.
  ///
  /// In en, this message translates to:
  /// **'Values are shown as the laboratory entered them. Please discuss them with your doctor.'**
  String get labNotADiagnosis;

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

  /// No description provided for @orderedBy.
  ///
  /// In en, this message translates to:
  /// **'Ordered by'**
  String get orderedBy;

  /// No description provided for @laboratory.
  ///
  /// In en, this message translates to:
  /// **'Laboratory'**
  String get laboratory;

  /// No description provided for @testDate.
  ///
  /// In en, this message translates to:
  /// **'Test date'**
  String get testDate;

  /// No description provided for @releasedOn.
  ///
  /// In en, this message translates to:
  /// **'Released on'**
  String get releasedOn;

  /// No description provided for @results.
  ///
  /// In en, this message translates to:
  /// **'Results'**
  String get results;

  /// No description provided for @noResultValues.
  ///
  /// In en, this message translates to:
  /// **'No values in this report'**
  String get noResultValues;

  /// No description provided for @referenceRange.
  ///
  /// In en, this message translates to:
  /// **'Reference range'**
  String get referenceRange;

  /// No description provided for @reportNotes.
  ///
  /// In en, this message translates to:
  /// **'Report notes'**
  String get reportNotes;

  /// No description provided for @billsIntro.
  ///
  /// In en, this message translates to:
  /// **'Invoices and the payments recorded against them.'**
  String get billsIntro;

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

  /// No description provided for @noBillsYet.
  ///
  /// In en, this message translates to:
  /// **'No bills yet'**
  String get noBillsYet;

  /// No description provided for @outstandingBalance.
  ///
  /// In en, this message translates to:
  /// **'Outstanding balance'**
  String get outstandingBalance;

  /// No description provided for @billsWithBalance.
  ///
  /// In en, this message translates to:
  /// **'Bills with balance due'**
  String get billsWithBalance;

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

  /// No description provided for @amountPaid.
  ///
  /// In en, this message translates to:
  /// **'Paid'**
  String get amountPaid;

  /// No description provided for @balanceDue.
  ///
  /// In en, this message translates to:
  /// **'Balance due'**
  String get balanceDue;

  /// No description provided for @paymentHistory.
  ///
  /// In en, this message translates to:
  /// **'Payment history'**
  String get paymentHistory;

  /// No description provided for @noPaymentsYet.
  ///
  /// In en, this message translates to:
  /// **'No payments recorded'**
  String get noPaymentsYet;

  /// No description provided for @refund.
  ///
  /// In en, this message translates to:
  /// **'Refund'**
  String get refund;

  /// No description provided for @patientNavNotifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get patientNavNotifications;

  /// No description provided for @notificationsIntro.
  ///
  /// In en, this message translates to:
  /// **'Messages from your hospital. Open one to see the page it is about.'**
  String get notificationsIntro;

  /// No description provided for @markReadFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not mark as read'**
  String get markReadFailed;

  /// No description provided for @noNotifications.
  ///
  /// In en, this message translates to:
  /// **'No notifications'**
  String get noNotifications;

  /// No description provided for @unread.
  ///
  /// In en, this message translates to:
  /// **'Unread'**
  String get unread;

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

  /// No description provided for @noDocumentsYet.
  ///
  /// In en, this message translates to:
  /// **'No documents yet'**
  String get noDocumentsYet;

  /// No description provided for @profileIntro.
  ///
  /// In en, this message translates to:
  /// **'Your details as the hospital has recorded them.'**
  String get profileIntro;

  /// No description provided for @refresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get refresh;

  /// No description provided for @profileChangesAtHospital.
  ///
  /// In en, this message translates to:
  /// **'To change your details, please contact the hospital reception.'**
  String get profileChangesAtHospital;

  /// No description provided for @patientId.
  ///
  /// In en, this message translates to:
  /// **'Patient ID'**
  String get patientId;

  /// No description provided for @selectedHospital.
  ///
  /// In en, this message translates to:
  /// **'Selected hospital'**
  String get selectedHospital;

  /// No description provided for @viewingHospital.
  ///
  /// In en, this message translates to:
  /// **'Showing records at {name}'**
  String viewingHospital(String name);

  /// No description provided for @patientDataUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Your records could not be loaded. Check your connection and try again.'**
  String get patientDataUnavailable;

  /// No description provided for @somePatientDataUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Some of your records could not be loaded.'**
  String get somePatientDataUnavailable;

  /// No description provided for @upcomingAppointments.
  ///
  /// In en, this message translates to:
  /// **'Upcoming appointments'**
  String get upcomingAppointments;

  /// No description provided for @pastVisits.
  ///
  /// In en, this message translates to:
  /// **'Past visits'**
  String get pastVisits;

  /// No description provided for @currentPrescriptions.
  ///
  /// In en, this message translates to:
  /// **'Current prescriptions'**
  String get currentPrescriptions;

  /// No description provided for @noUpcomingAppointments.
  ///
  /// In en, this message translates to:
  /// **'No upcoming appointments'**
  String get noUpcomingAppointments;

  /// No description provided for @recentPrescriptions.
  ///
  /// In en, this message translates to:
  /// **'Recent prescriptions'**
  String get recentPrescriptions;

  /// No description provided for @recentLabReports.
  ///
  /// In en, this message translates to:
  /// **'Recent lab reports'**
  String get recentLabReports;

  /// No description provided for @notAvailableNow.
  ///
  /// In en, this message translates to:
  /// **'Not available right now'**
  String get notAvailableNow;

  /// No description provided for @medicineCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 medicine} other{{count} medicines}}'**
  String medicineCount(int count);

  /// No description provided for @unreadNotifications.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{You have 1 unread notification} other{You have {count} unread notifications}}'**
  String unreadNotifications(int count);

  /// No description provided for @ageLabel.
  ///
  /// In en, this message translates to:
  /// **'Age'**
  String get ageLabel;

  /// No description provided for @timeLabel.
  ///
  /// In en, this message translates to:
  /// **'Time'**
  String get timeLabel;

  /// No description provided for @tokenLabel.
  ///
  /// In en, this message translates to:
  /// **'Token'**
  String get tokenLabel;

  /// No description provided for @viewProfile.
  ///
  /// In en, this message translates to:
  /// **'View profile'**
  String get viewProfile;

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

  /// No description provided for @anotherDoctorsVisit.
  ///
  /// In en, this message translates to:
  /// **'This is another doctor\'s visit. You can read it but not add to it.'**
  String get anotherDoctorsVisit;

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

  /// No description provided for @calledPatients.
  ///
  /// In en, this message translates to:
  /// **'Called'**
  String get calledPatients;

  /// No description provided for @checkAndSavePrescription.
  ///
  /// In en, this message translates to:
  /// **'Check safety and save prescription'**
  String get checkAndSavePrescription;

  /// No description provided for @checkTheseFields.
  ///
  /// In en, this message translates to:
  /// **'Please check: {fields}'**
  String checkTheseFields(String fields);

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

  /// No description provided for @completedToday.
  ///
  /// In en, this message translates to:
  /// **'Completed today'**
  String get completedToday;

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

  /// No description provided for @continueSaving.
  ///
  /// In en, this message translates to:
  /// **'Continue and save'**
  String get continueSaving;

  /// No description provided for @dateOfBirth.
  ///
  /// In en, this message translates to:
  /// **'Date of birth'**
  String get dateOfBirth;

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

  /// No description provided for @draft.
  ///
  /// In en, this message translates to:
  /// **'Draft'**
  String get draft;

  /// No description provided for @emergencyContact.
  ///
  /// In en, this message translates to:
  /// **'Emergency contact'**
  String get emergencyContact;

  /// No description provided for @enterAtLeastOneVital.
  ///
  /// In en, this message translates to:
  /// **'Enter at least one reading.'**
  String get enterAtLeastOneVital;

  /// No description provided for @estimatedWaitShort.
  ///
  /// In en, this message translates to:
  /// **'about {minutes} min (estimate)'**
  String estimatedWaitShort(String minutes);

  /// No description provided for @filterToday.
  ///
  /// In en, this message translates to:
  /// **'Today'**
  String get filterToday;

  /// No description provided for @fixHighlightedFields.
  ///
  /// In en, this message translates to:
  /// **'Fix the highlighted readings.'**
  String get fixHighlightedFields;

  /// No description provided for @goBack.
  ///
  /// In en, this message translates to:
  /// **'Go back'**
  String get goBack;

  /// No description provided for @icd10Search.
  ///
  /// In en, this message translates to:
  /// **'Search ICD-10 (optional)'**
  String get icd10Search;

  /// No description provided for @knownCondition.
  ///
  /// In en, this message translates to:
  /// **'Known condition'**
  String get knownCondition;

  /// No description provided for @labOrders.
  ///
  /// In en, this message translates to:
  /// **'Lab orders'**
  String get labOrders;

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

  /// No description provided for @medicationSafetyAlerts.
  ///
  /// In en, this message translates to:
  /// **'Medication safety alerts'**
  String get medicationSafetyAlerts;

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

  /// No description provided for @medicines.
  ///
  /// In en, this message translates to:
  /// **'Medicines'**
  String get medicines;

  /// No description provided for @myDoctorProfile.
  ///
  /// In en, this message translates to:
  /// **'My doctor profile'**
  String get myDoctorProfile;

  /// No description provided for @name.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get name;

  /// No description provided for @noAppointmentsToday.
  ///
  /// In en, this message translates to:
  /// **'No appointments today'**
  String get noAppointmentsToday;

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

  /// No description provided for @noDoctorInbox.
  ///
  /// In en, this message translates to:
  /// **'Doctor notifications are not available: the hospital system has no inbox for staff yet.'**
  String get noDoctorInbox;

  /// No description provided for @noHistoryYet.
  ///
  /// In en, this message translates to:
  /// **'No history recorded'**
  String get noHistoryYet;

  /// No description provided for @noLabOrdersForVisit.
  ///
  /// In en, this message translates to:
  /// **'No lab tests ordered on this visit'**
  String get noLabOrdersForVisit;

  /// No description provided for @none.
  ///
  /// In en, this message translates to:
  /// **'None'**
  String get none;

  /// No description provided for @noNotesYet.
  ///
  /// In en, this message translates to:
  /// **'No notes yet'**
  String get noNotesYet;

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

  /// No description provided for @noPrescriptionsForVisit.
  ///
  /// In en, this message translates to:
  /// **'No prescription on this visit yet'**
  String get noPrescriptionsForVisit;

  /// No description provided for @noShowTitle.
  ///
  /// In en, this message translates to:
  /// **'Mark as no-show?'**
  String get noShowTitle;

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

  /// No description provided for @nowServing.
  ///
  /// In en, this message translates to:
  /// **'Now serving'**
  String get nowServing;

  /// No description provided for @openConsultation.
  ///
  /// In en, this message translates to:
  /// **'Open consultation'**
  String get openConsultation;

  /// No description provided for @openPatientRecord.
  ///
  /// In en, this message translates to:
  /// **'Open patient record'**
  String get openPatientRecord;

  /// No description provided for @openVisits.
  ///
  /// In en, this message translates to:
  /// **'Open visits'**
  String get openVisits;

  /// No description provided for @orderLabTest.
  ///
  /// In en, this message translates to:
  /// **'Order lab test'**
  String get orderLabTest;

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

  /// No description provided for @patientLabel.
  ///
  /// In en, this message translates to:
  /// **'Patient'**
  String get patientLabel;

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

  /// No description provided for @patientProfile.
  ///
  /// In en, this message translates to:
  /// **'Patient profile'**
  String get patientProfile;

  /// No description provided for @pickDate.
  ///
  /// In en, this message translates to:
  /// **'Pick a date'**
  String get pickDate;

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

  /// No description provided for @prescription.
  ///
  /// In en, this message translates to:
  /// **'Prescription'**
  String get prescription;

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

  /// No description provided for @prescriptionSaved.
  ///
  /// In en, this message translates to:
  /// **'Prescription #{id} saved by the hospital system.'**
  String prescriptionSaved(String id);

  /// No description provided for @priority.
  ///
  /// In en, this message translates to:
  /// **'Priority'**
  String get priority;

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

  /// No description provided for @queueFinishedToday.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =0{No token finished today} =1{1 token finished today} other{{count} tokens finished today}}'**
  String queueFinishedToday(int count);

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

  /// No description provided for @recentConsultations.
  ///
  /// In en, this message translates to:
  /// **'Recent consultations'**
  String get recentConsultations;

  /// No description provided for @recordSignedNoChange.
  ///
  /// In en, this message translates to:
  /// **'This record is signed and cannot be changed. Add a new record instead.'**
  String get recordSignedNoChange;

  /// No description provided for @registration.
  ///
  /// In en, this message translates to:
  /// **'Registration'**
  String get registration;

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

  /// No description provided for @resultNotReleased.
  ///
  /// In en, this message translates to:
  /// **'Result not released yet'**
  String get resultNotReleased;

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

  /// No description provided for @signedOn.
  ///
  /// In en, this message translates to:
  /// **'Signed {date}'**
  String signedOn(String date);

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

  /// No description provided for @skipTokenTitle.
  ///
  /// In en, this message translates to:
  /// **'Skip this token?'**
  String get skipTokenTitle;

  /// No description provided for @specialization.
  ///
  /// In en, this message translates to:
  /// **'Specialisation'**
  String get specialization;

  /// No description provided for @startConsultation.
  ///
  /// In en, this message translates to:
  /// **'Start consultation'**
  String get startConsultation;

  /// No description provided for @todaysAppointments.
  ///
  /// In en, this message translates to:
  /// **'Today\'s appointments'**
  String get todaysAppointments;

  /// No description provided for @typeToSearch.
  ///
  /// In en, this message translates to:
  /// **'Type at least {count} letters to search'**
  String typeToSearch(int count);

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

  /// No description provided for @vitals.
  ///
  /// In en, this message translates to:
  /// **'Vitals'**
  String get vitals;

  /// No description provided for @vitalSpo2.
  ///
  /// In en, this message translates to:
  /// **'SpO₂'**
  String get vitalSpo2;

  /// No description provided for @vitalsSaved.
  ///
  /// In en, this message translates to:
  /// **'Vitals saved by the hospital system.'**
  String get vitalsSaved;

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

  /// No description provided for @waitingPatients.
  ///
  /// In en, this message translates to:
  /// **'Waiting'**
  String get waitingPatients;

  /// No description provided for @writeInConsultation.
  ///
  /// In en, this message translates to:
  /// **'Write in a consultation'**
  String get writeInConsultation;
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
