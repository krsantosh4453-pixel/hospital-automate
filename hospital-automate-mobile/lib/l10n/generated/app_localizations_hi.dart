// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Hindi (`hi`).
class AppLocalizationsHi extends AppLocalizations {
  AppLocalizationsHi([String locale = 'hi']) : super(locale);

  @override
  String get accountFamily => 'परिवार सदस्य (केवल देखें)';

  @override
  String get accountPatient => 'मरीज़';

  @override
  String actingAs(String role) {
    return '$role के रूप में काम कर रहे हैं';
  }

  @override
  String get actionAiScribe => 'एआई स्क्राइब';

  @override
  String get actionBloodStock => 'रक्त स्टॉक और अनुरोध';

  @override
  String get actionCompounding => 'कंपाउंडिंग';

  @override
  String get actionCreateInvoice => 'बिल बनाएँ';

  @override
  String get actionDispenseMedicines => 'दवा दें';

  @override
  String get actionFindPatient => 'मरीज़ खोजें';

  @override
  String get actionLabResults => 'लैब रिपोर्ट';

  @override
  String get actionLabWorklist => 'लैब कार्यसूची';

  @override
  String get actionMedicineStock => 'दवा स्टॉक';

  @override
  String get actionNewAppointment => 'नया अपॉइंटमेंट';

  @override
  String get actionOpenQueue => 'कतार खोलें';

  @override
  String get actionPrescriptions => 'पर्चे';

  @override
  String get actionRegisterPatient => 'मरीज़ पंजीकृत करें';

  @override
  String get actionStartConsultation => 'परामर्श शुरू करें';

  @override
  String get actionVitalsNursing => 'वाइटल्स और नर्सिंग';

  @override
  String get actionWardBeds => 'वार्ड और बेड';

  @override
  String get addDiagnosis => 'निदान जोड़ें';

  @override
  String get addMedicine => 'दवा जोड़ें';

  @override
  String get addOneMedicine => 'कम से कम एक दवा जोड़ें।';

  @override
  String get ageLabel => 'आयु';

  @override
  String ageYears(String age) {
    return '$age y';
  }

  @override
  String get amountPaid => 'भुगतान किया';

  @override
  String get anotherDoctorsVisit =>
      'यह किसी दूसरे डॉक्टर की विज़िट है। आप इसे पढ़ सकते हैं, पर इसमें जोड़ नहीं सकते।';

  @override
  String get appName => 'HMS';

  @override
  String get appSettingsIntro => 'इस डिवाइस की सेटिंग्स।';

  @override
  String get appSubtitle => 'अस्पताल प्रबंधन';

  @override
  String get appointmentChangesAtHospital =>
      'अपॉइंटमेंट रद्द करने या बदलने के लिए कृपया अस्पताल के रिसेप्शन से संपर्क करें।';

  @override
  String get appointmentDetails => 'अपॉइंटमेंट विवरण';

  @override
  String get appointmentId => 'अपॉइंटमेंट आईडी';

  @override
  String get appointmentStatus => 'अपॉइंटमेंट की स्थिति';

  @override
  String get appointmentsIntro => 'चुने गए अस्पताल में आपकी बुकिंग।';

  @override
  String get atLeast8Characters => 'कम से कम 8 अक्षर।';

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
      'यह खाता बंद है। अपने अस्पताल प्रशासक से संपर्क करें।';

  @override
  String get authChallengeExpired =>
      'साइन इन का चरण समाप्त हो गया। फिर से पासवर्ड दर्ज करें।';

  @override
  String get authEmailExists => 'इस ईमेल से खाता पहले से है। साइन इन करें।';

  @override
  String get authEmailNotVerified =>
      'आपका ईमेल अभी सत्यापित नहीं है। सत्यापन के लिए ईमेल OTP भेजें।';

  @override
  String get authEmailSendFailed =>
      'सत्यापन ईमेल नहीं भेजा जा सका। बाद में फिर कोशिश करें।';

  @override
  String get authFamilyNotAvailable =>
      'आपके मोबाइल नंबर के लिए यह परिवार की पहुँच उपलब्ध नहीं है।';

  @override
  String get authFamilyTicketExpired =>
      'आपका साइन-इन समाप्त हो गया है। नया कोड मँगाएँ।';

  @override
  String get authFieldsRequired =>
      'अपना यूज़रनेम या ईमेल और पासवर्ड दर्ज करें।';

  @override
  String get authGoogleFailed =>
      'Google से साइन-इन नहीं हुआ। फिर से कोशिश करें, या साइन-इन का दूसरा तरीका अपनाएँ।';

  @override
  String get authGoogleNotSetUp =>
      'इस ऐप में Google साइन-इन अभी सेट नहीं है। साइन-इन का दूसरा तरीका अपनाएँ।';

  @override
  String get authInvalidCredentials => 'यूज़रनेम, ईमेल या पासवर्ड सही नहीं है।';

  @override
  String get authInvalidDob => 'जन्म तिथि सही नहीं है।';

  @override
  String get authInvalidEmail => 'सही ईमेल पता दर्ज करें।';

  @override
  String get authInvalidOtp => 'कोड सही नहीं है।';

  @override
  String get authInvalidPhone => 'सही 10 अंकों का मोबाइल नंबर दर्ज करें।';

  @override
  String get authLockedOut =>
      'बहुत अधिक असफल प्रयास। 15 मिनट बाद फिर कोशिश करें या पासवर्ड रीसेट करें।';

  @override
  String get authNameRequired => 'अपना पूरा नाम दर्ज करें।';

  @override
  String get authNotAllowed => 'इस खाते के लिए यह साइन इन मान्य नहीं है।';

  @override
  String get authNotStaff =>
      'यह सक्रिय स्टाफ़ खाता नहीं है। मरीज़ मरीज़ पोर्टल पर साइन इन करते हैं।';

  @override
  String get authOtpCooldown => 'नया कोड मँगाने से पहले एक मिनट रुकें।';

  @override
  String get authOtpExpired => 'कोड की समय-सीमा खत्म हो गई। नया कोड मँगाएँ।';

  @override
  String get authOtpLocked =>
      'बहुत अधिक गलत कोड। 15 मिनट बाद फिर से साइन इन करें।';

  @override
  String get authOtpRequiredUnavailable =>
      'इस सर्वर पर एसएमएस कोड ज़रूरी है, पर एसएमएस सेट नहीं है। अपने अस्पताल प्रशासक से संपर्क करें।';

  @override
  String get authPasswordMismatch => 'पासवर्ड और पुष्टि पासवर्ड मेल नहीं खाते।';

  @override
  String get authPasswordRejected =>
      'यह पासवर्ड स्वीकार नहीं हुआ। लंबा और कम सामान्य पासवर्ड चुनें।';

  @override
  String get authPasswordTooShort =>
      'पासवर्ड कम से कम 8 अक्षरों का होना चाहिए।';

  @override
  String get authPhoneExists =>
      'इस मोबाइल नंबर से खाता पहले से है। साइन इन करें।';

  @override
  String get authResetCodeInvalid =>
      'कोड सही नहीं है या उसकी समय-सीमा खत्म हो गई है।';

  @override
  String get authResetUnavailable =>
      'इस सर्वर पर एसएमएस से पासवर्ड रीसेट सेट नहीं है। अपने अस्पताल प्रशासक से संपर्क करें।';

  @override
  String get authSmsUnavailable =>
      'इस सर्वर पर एसएमएस कोड सेट नहीं है। साइन इन का दूसरा तरीका अपनाएँ या अस्पताल से संपर्क करें।';

  @override
  String get authStaffInviteOnly =>
      'स्टाफ़ खाते आपका अस्पताल बनाता है। उसके प्रशासक से निमंत्रण माँगें।';

  @override
  String get authStaffUseStaffLogin =>
      'स्टाफ़ खाते स्टाफ़ पोर्टल पर साइन इन करते हैं।';

  @override
  String get authTooManyRequests =>
      'बहुत अधिक प्रयास। कृपया बाद में फिर कोशिश करें।';

  @override
  String get authUnsupportedAccount =>
      'यह खाता मोबाइल ऐप में नहीं चल सकता। वेब ऐप का उपयोग करें।';

  @override
  String get back => 'वापस';

  @override
  String get backToEmailLogin => 'ईमेल लॉगिन पर वापस';

  @override
  String get backToHome => 'होम पर वापस जाएँ';

  @override
  String get backToSignIn => 'साइन इन पर वापस';

  @override
  String get backend => 'बैकएंड';

  @override
  String get balanceDue => 'बकाया';

  @override
  String bedsOccupiedOf(String occupied, String total) {
    return '$total में से $occupied भरे';
  }

  @override
  String get billDate => 'बिल की तारीख';

  @override
  String get billTotal => 'कुल';

  @override
  String get billingAmount => 'राशि';

  @override
  String get billingAmountInvalid =>
      'रुपये में राशि लिखें, जैसे 500 या 499.50।';

  @override
  String get billingAmountRefused =>
      'अस्पताल प्रणाली ने यह राशि स्वीकार नहीं की। बकाया जाँचें और फिर कोशिश करें।';

  @override
  String billingAmountTooHigh(String limit) {
    return 'राशि बकाया ($limit) से अधिक है।';
  }

  @override
  String get billingAnyDate => 'कोई भी तारीख';

  @override
  String get billingBackToDesk => 'बिलिंग पर वापस';

  @override
  String get billingBackToInvoice => 'बिल पर वापस';

  @override
  String get billingChargeConsultation => 'परामर्श';

  @override
  String get billingChargeLaboratory => 'प्रयोगशाला';

  @override
  String get billingChargeOther => 'अन्य शुल्क';

  @override
  String get billingChargePharmacy => 'फार्मेसी';

  @override
  String get billingChoosePatient => 'नाम, फ़ोन या UHID से खोजकर मरीज़ चुनें।';

  @override
  String get billingClearDates => 'तारीखें हटाएँ';

  @override
  String billingConfirmPayment(
    String amount,
    String method,
    String invoice,
    String patient,
  ) {
    return 'बिल $invoice ($patient) के लिए $method से प्राप्त $amount दर्ज करें? यह काउंटर पर पहले से मिली राशि दर्ज करता है; इससे किसी से पैसा नहीं लिया जाता।';
  }

  @override
  String get billingConfirmPaymentTitle => 'यह भुगतान दर्ज करें?';

  @override
  String billingConfirmRefund(String amount, String method, String invoice) {
    return 'बिल $invoice पर $method से $amount की वापसी दर्ज करें? वापसी बाद में बदली या हटाई नहीं जा सकती।';
  }

  @override
  String get billingConfirmRefundTitle => 'यह वापसी दर्ज करें?';

  @override
  String get billingCountsUnavailable => 'बिलिंग आँकड़े लोड नहीं हो सके';

  @override
  String get billingCreateInvoice => 'बिल बनाएँ';

  @override
  String get billingCreateNotAllowed =>
      'इस अस्पताल में आपकी भूमिका बिल नहीं बना सकती।';

  @override
  String get billingDeskIntro =>
      'चुने गए अस्पताल के बिल और भुगतान। कुल और बकाया अस्पताल प्रणाली से आते हैं।';

  @override
  String get billingDiscount => 'छूट';

  @override
  String get billingDiscountHint =>
      'GST से पहले घटाई जाती है, जैसा अस्पताल प्रणाली गणना करती है।';

  @override
  String get billingDiscountRefused =>
      'छूट ऋणात्मक या कर से पहले के बिल से अधिक नहीं हो सकती।';

  @override
  String billingDue(String amount) {
    return 'बकाया $amount';
  }

  @override
  String get billingFromPharmacy => 'फार्मेसी से';

  @override
  String get billingGstPercent => 'GST %';

  @override
  String billingGstRate(String rate) {
    return 'GST $rate%';
  }

  @override
  String get billingInvoiceClosed =>
      'यह बिल रद्द या बंद है, इसलिए इस पर कोई राशि दर्ज नहीं हो सकती।';

  @override
  String get billingInvoiceMaybeCreated =>
      'अस्पताल प्रणाली से जवाब नहीं आया, इसलिए बिल शायद बन गया हो। दोबारा बनाने से पहले बिल सूची देखें।';

  @override
  String get billingInvoiceTitle => 'बिल';

  @override
  String get billingInvoices => 'बिल';

  @override
  String get billingItems => 'मदें';

  @override
  String get billingKeyReused =>
      'यह अनुरोध पहले ही किसी और रिकॉर्ड के लिए उपयोग हो चुका है। बिल पर वापस जाकर फिर से शुरू करें।';

  @override
  String billingLatestRecords(int count) {
    return 'नवीनतम $count रिकॉर्ड';
  }

  @override
  String get billingLineDescription => 'विवरण';

  @override
  String get billingLineDescriptionRequired => 'शुल्क का विवरण लिखें।';

  @override
  String billingLineNumber(int number) {
    return 'मद $number';
  }

  @override
  String get billingNetOfRefunds => 'वापसी के बाद';

  @override
  String get billingNewInvoice => 'नया बिल';

  @override
  String get billingNewInvoiceIntro =>
      'मरीज़ चुनें और शुल्क जोड़ें। कर, कुल और बिल संख्या अस्पताल प्रणाली तय करती है।';

  @override
  String get billingNoGateway => 'भुगतान काउंटर पर दर्ज होते हैं';

  @override
  String get billingNoGatewayBody =>
      'कोई ऑनलाइन भुगतान गेटवे नहीं है। नकद, UPI, कार्ड या बैंक ट्रांसफ़र राशि मिलने के बाद ही दर्ज करें। यहाँ कुछ भी लंबित या विफल नहीं है: हर रिकॉर्ड एक पुष्ट रसीद है।';

  @override
  String get billingNoInvoicesMatch => 'इन फ़िल्टर से कोई बिल मेल नहीं खाता';

  @override
  String get billingNoItems => 'इस बिल में कोई मद नहीं है।';

  @override
  String get billingOpenInvoiceList => 'बिल सूची खोलें';

  @override
  String get billingPatientSearchHint => 'नाम, फ़ोन या UHID से मरीज़ खोजें';

  @override
  String get billingPaymentIntro => 'इस बिल के लिए काउंटर पर प्राप्त राशि।';

  @override
  String get billingPaymentKind => 'भुगतान';

  @override
  String get billingPaymentMethod => 'भुगतान का तरीका';

  @override
  String get billingPaymentNotAllowed =>
      'आपकी भूमिका इस बिल पर भुगतान दर्ज नहीं कर सकती।';

  @override
  String get billingPaymentRecorded => 'अस्पताल प्रणाली ने भुगतान दर्ज किया';

  @override
  String get billingPayments => 'भुगतान';

  @override
  String get billingPaymentsRecorded => 'दर्ज भुगतान';

  @override
  String get billingPharmacyAutomatic =>
      'फार्मेसी द्वारा बेची गई दवाओं का बिल अपने आप बनता है, इसलिए वे यहाँ नहीं जोड़ी जातीं।';

  @override
  String get billingPrintOnWeb =>
      'छपे बिल और PDF वेब ऐप से बनते हैं; फ़ोन के लिए अस्पताल प्रणाली में बिल PDF नहीं है।';

  @override
  String get billingQuantityInvalid =>
      'मात्रा कम से कम 1 की पूर्ण संख्या होनी चाहिए।';

  @override
  String get billingReceipt => 'रसीद संख्या';

  @override
  String get billingRecordPayment => 'भुगतान दर्ज करें';

  @override
  String get billingRecordRefund => 'वापसी दर्ज करें';

  @override
  String get billingReference => 'लेन-देन संदर्भ';

  @override
  String get billingReferenceHint =>
      'UPI लेन-देन ID, कार्ड पर्ची या ट्रांसफ़र संख्या। कभी कार्ड नंबर, CVV या PIN नहीं।';

  @override
  String get billingRefundIntro => 'इस बिल पर मरीज़ को लौटाई गई राशि।';

  @override
  String get billingRefundNotAllowed =>
      'आपकी भूमिका इस बिल पर वापसी दर्ज नहीं कर सकती।';

  @override
  String get billingRefundReason => 'वापसी का कारण';

  @override
  String get billingRefundReasonRequired => 'वापसी का कारण लिखें।';

  @override
  String get billingRefundRecorded => 'अस्पताल प्रणाली ने वापसी दर्ज की';

  @override
  String billingRefundTooHigh(String limit) {
    return 'वापसी प्राप्त राशि ($limit) से अधिक नहीं हो सकती।';
  }

  @override
  String get billingRefunds => 'वापसियाँ';

  @override
  String get billingRefused =>
      'अस्पताल प्रणाली ने इसे स्वीकार नहीं किया। रीफ़्रेश करके फिर कोशिश करें।';

  @override
  String get billingRemoveLine => 'मद हटाएँ';

  @override
  String get billingSearchHint => 'बिल संख्या, मरीज़ या UHID खोजें';

  @override
  String get billingServerTotals =>
      'बिल बनाते समय कर, कुल और बिल संख्या अस्पताल प्रणाली गणना करती है।';

  @override
  String get billingSubtotal => 'उप-योग';

  @override
  String get billingTax => 'कर (GST)';

  @override
  String get billingTaxRateInvalid => 'GST 0 से 100 प्रतिशत के बीच होना चाहिए।';

  @override
  String get billingTotalInvoices => 'बिल';

  @override
  String get billingUnitPrice => 'इकाई मूल्य';

  @override
  String get billsIntro => 'बिल और उन पर दर्ज भुगतान।';

  @override
  String get billsWithBalance => 'बकाया वाले बिल';

  @override
  String get bmi => 'बीएमआई';

  @override
  String get bmiByServer =>
      'बीएमआई अस्पताल प्रणाली वज़न (किग्रा) और ऊँचाई (सेमी) से निकालती है: किग्रा ÷ मी²।';

  @override
  String get bookAppointment => 'अपॉइंटमेंट बुक करें';

  @override
  String get bookAppointmentIntro => 'डॉक्टर, तारीख और खाली समय चुनें।';

  @override
  String get bookingConfirmed => 'अपॉइंटमेंट बुक हो गया';

  @override
  String get bookingConfirmedBody =>
      'अस्पताल ने आपकी बुकिंग दर्ज कर ली है। कृपया अपने समय से थोड़ा पहले पहुँचें।';

  @override
  String get bookingDateInvalid =>
      'यह तारीख बुक नहीं हो सकती। बुकिंग अवधि के भीतर की तारीख चुनें।';

  @override
  String get bookingDoctorUnavailable =>
      'यह डॉक्टर ऑनलाइन बुकिंग नहीं ले रहे। दूसरे डॉक्टर चुनें।';

  @override
  String get bookingLimitReached =>
      'आपके पास पहले से अधिकतम आगामी अपॉइंटमेंट हैं। पहले अस्पताल में किसी एक में जाएँ या रद्द कराएँ।';

  @override
  String get bookingNoHospital =>
      'आप अभी किसी अस्पताल में पंजीकृत नहीं हैं। पहले रिसेप्शन पर पंजीकरण कराएँ।';

  @override
  String get bookingRejected =>
      'अस्पताल यह बुकिंग स्वीकार नहीं कर सका। विवरण जाँचकर फिर कोशिश करें।';

  @override
  String get bookingSlotTaken =>
      'यह समय अभी किसी और ने बुक कर लिया। कृपया दूसरा समय चुनें।';

  @override
  String get bookingSlotUnavailable =>
      'यह समय अब उपलब्ध नहीं है। कृपया दूसरा समय चुनें।';

  @override
  String get calledPatients => 'बुलाए गए';

  @override
  String get cancel => 'रद्द करें';

  @override
  String get changeNumber => 'नंबर बदलें';

  @override
  String get checkAgain => 'फिर से जाँचें';

  @override
  String get checkAndSavePrescription => 'सुरक्षा जाँचें और पर्चा सहेजें';

  @override
  String checkTheseFields(String fields) {
    return 'कृपया जाँचें: $fields';
  }

  @override
  String get checking => 'जाँच हो रही है…';

  @override
  String get checkingConnection => 'कनेक्शन जाँचा जा रहा है…';

  @override
  String get chooseDoctorFirst => 'खाली समय देखने के लिए डॉक्टर चुनें।';

  @override
  String get clinicalHistory => 'नैदानिक इतिहास';

  @override
  String get clinicalNotes => 'नैदानिक नोट्स';

  @override
  String get close => 'बंद करें';

  @override
  String get closeNavigation => 'मेन्यू बंद करें';

  @override
  String get codeFromSms => 'एसएमएस से आया कोड';

  @override
  String get codeResent => 'नया कोड भेजा गया।';

  @override
  String codeSentToMobile(String maskedPhone) {
    return 'हमने आपके मोबाइल ($maskedPhone) पर 6 अंकों का कोड भेजा है।';
  }

  @override
  String get collapseSidebar => 'साइडबार छोटा करें';

  @override
  String get comments => 'टिप्पणी';

  @override
  String get completeConsultation => 'परामर्श पूरा करें';

  @override
  String get completeConsultationBody =>
      'विज़िट पूरी के रूप में दर्ज होगी। सहेजे गए रिकॉर्ड वैसे ही रहेंगे।';

  @override
  String get completeConsultationTitle => 'यह परामर्श पूरा करें?';

  @override
  String get completedToday => 'आज पूरे हुए';

  @override
  String get confirmBooking => 'बुकिंग पक्की करें';

  @override
  String get confirmPassword => 'पासवर्ड की पुष्टि करें';

  @override
  String get consultationIntro =>
      'आपकी विज़िट। वाइटल्स, नोट्स, निदान, पर्चे और लैब ऑर्डर दर्ज करने के लिए कोई विज़िट खोलें।';

  @override
  String get consultationQueueHint =>
      'कतार टोकन कतार पेज पर आगे बढ़ाए जाते हैं।';

  @override
  String get continueAction => 'आगे बढ़ें';

  @override
  String get continueSaving => 'जारी रखें और सहेजें';

  @override
  String get continueWithGoogle => 'Google से जारी रखें';

  @override
  String countPending(String count) {
    return '$count बाकी';
  }

  @override
  String get createAccount => 'खाता बनाएँ';

  @override
  String get currentPrescriptions => 'चालू पर्चे';

  @override
  String get dashboardLoadFailed => 'डैशबोर्ड के आँकड़े लोड नहीं हो सके';

  @override
  String get date => 'तारीख';

  @override
  String get dateOfBirth => 'जन्म तिथि';

  @override
  String get departments => 'विभाग';

  @override
  String get departmentsIntro =>
      'हर विभाग का काम सही स्टाफ़ सदस्य के साइन इन करने पर खुलता है।';

  @override
  String get deptAppointmentsText => 'Bookings and the daily schedule.';

  @override
  String get deptBillingText => 'Invoices and payments.';

  @override
  String get deptBloodBank => 'ब्लड बैंक';

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
  String get deptNursing => 'नर्सिंग';

  @override
  String get deptNursingText => 'Vitals, nursing notes and medication rounds.';

  @override
  String get deptPatientsText => 'Registration and patient records.';

  @override
  String get deptPharmacyText => 'Dispensing and medicine stock.';

  @override
  String get deptQueue => 'ओपीडी कतार';

  @override
  String get deptQueueText => 'Tokens and consultation flow.';

  @override
  String get deptReportsText => 'Hospital statistics.';

  @override
  String get deptWards => 'Wards and beds';

  @override
  String get deptWardsText => 'Admissions, beds and discharge.';

  @override
  String get diagnoses => 'निदान';

  @override
  String get diagnosisName => 'निदान';

  @override
  String get diagnosisNameRequired => 'निदान दर्ज करें।';

  @override
  String get diagnosisType => 'प्रकार';

  @override
  String get doctor => 'डॉक्टर';

  @override
  String get doctorAppointmentsIntro =>
      'चुने गए अस्पताल में आपके साथ की बुकिंग।';

  @override
  String get doctorLabIntro =>
      'आपकी देखरेख वाले मरीज़ों की लैब जाँचें। मान प्रयोगशाला के जारी करने के बाद दिखते हैं।';

  @override
  String get doctorPatientsIntro =>
      'नाम, मोबाइल नंबर या यूएचआईडी से अपनी देखरेख वाले मरीज़ को खोजें।';

  @override
  String get doctorPrescriptionsIntro => 'आपकी देखरेख वाले मरीज़ों के पर्चे।';

  @override
  String get doctorProfileMissing =>
      'इस अस्पताल में आपके खाते से कोई डॉक्टर प्रोफ़ाइल जुड़ी नहीं है। अस्पताल प्रशासक से पूछें।';

  @override
  String get doctorQueueIntro =>
      'आज आपके मरीज़। यह पेज खुला रहने पर हर 30 सेकंड में फिर जाँचता है।';

  @override
  String get documentsIntro => 'अस्पताल द्वारा आपके साथ साझा किए गए दस्तावेज़।';

  @override
  String get documentsViewOnWeb =>
      'ऐप में फ़ाइल खोलना अभी उपलब्ध नहीं है। उन्हें खोलने के लिए वेब पर मरीज़ पोर्टल का उपयोग करें।';

  @override
  String get dosage => 'खुराक';

  @override
  String get draft => 'मसौदा';

  @override
  String get duration => 'अवधि';

  @override
  String get email => 'ईमेल';

  @override
  String get emailCodeNotSent =>
      'सत्यापन ईमेल नहीं भेजा जा सका। अस्पताल से ईमेल सेटिंग जाँचने को कहें।';

  @override
  String get emailCodeSent =>
      'अगर इस ईमेल से मरीज़ खाता है, तो उस पर सत्यापन कोड भेजा गया है।';

  @override
  String get emailLoginIntro =>
      'अपने मरीज़ खाते का ईमेल और पासवर्ड उपयोग करें।';

  @override
  String get emailNotVerifiedSendOtp => 'ईमेल सत्यापित नहीं? ईमेल OTP भेजें';

  @override
  String get emailOtpIntro => 'हम आपके पंजीकृत ईमेल पर सत्यापन कोड भेजेंगे।';

  @override
  String get emailVerifiedSignIn =>
      'ईमेल सत्यापित हो गया। अब अपने ईमेल और पासवर्ड से साइन इन करें।';

  @override
  String get emergencyContact => 'आपातकालीन संपर्क';

  @override
  String get emergencyVisitsToday => 'आज की आपातकालीन विज़िट';

  @override
  String get enter10DigitNumber => '10 अंकों का नंबर लिखें';

  @override
  String get enterAtLeastOneVital => 'कम से कम एक माप दर्ज करें।';

  @override
  String get enterTheCode => 'कोड दर्ज करें';

  @override
  String get errorConflict =>
      'यह रिकॉर्ड बदल गया है या पहले से मौजूद है। रीफ़्रेश करके फिर कोशिश करें।';

  @override
  String get errorForbidden =>
      'चुने गए अस्पताल में आपकी भूमिका को इसकी पहुँच नहीं है।';

  @override
  String get errorNetwork =>
      'सर्वर तक नहीं पहुँच सके। कनेक्शन जाँचकर फिर कोशिश करें।';

  @override
  String get errorNotFound => 'चुने गए अस्पताल में यह रिकॉर्ड नहीं मिला।';

  @override
  String get errorRateLimited =>
      'बहुत अधिक प्रयास। कुछ मिनट रुककर फिर कोशिश करें।';

  @override
  String get errorServer =>
      'सर्वर में समस्या है। थोड़ी देर में फिर कोशिश करें।';

  @override
  String get errorTimeout => 'सर्वर ने समय पर जवाब नहीं दिया। फिर कोशिश करें।';

  @override
  String get errorUnauthorized =>
      'आपका सत्र समाप्त हो गया। कृपया फिर से साइन इन करें।';

  @override
  String get errorUnavailable => 'यह सेवा सर्वर पर सेट नहीं है।';

  @override
  String get errorUnknown => 'कुछ गलत हो गया। फिर कोशिश करें।';

  @override
  String get errorValidation =>
      'कुछ जानकारी सही नहीं है। फ़ॉर्म जाँचकर फिर कोशिश करें।';

  @override
  String get estimatedWait => 'अनुमानित प्रतीक्षा';

  @override
  String estimatedWaitShort(String minutes) {
    return 'लगभग $minutes मिनट (अनुमान)';
  }

  @override
  String get estimatesAreApproximate =>
      'प्रतीक्षा समय अनुमान है, अपॉइंटमेंट का समय नहीं। कृपया पास ही रहें ताकि आपकी बारी न छूटे।';

  @override
  String get expandSidebar => 'साइडबार बड़ा करें';

  @override
  String get expectedAround => 'लगभग समय';

  @override
  String get familyChoosePatient => 'आप किसके रिकॉर्ड देखना चाहते हैं?';

  @override
  String familyCodeSentIfAccess(String phone) {
    return 'अगर $phone को परिवार की पहुँच मिली है, तो उस पर 6 अंकों का कोड भेजा गया है।';
  }

  @override
  String get familyIntro =>
      'मरीज़ द्वारा दी गई अनुमति से अपने रिश्तेदार के रिकॉर्ड देखें। अपना मोबाइल नंबर इस्तेमाल करें। केवल देखने की अनुमति: आप कुछ बदल नहीं सकते।';

  @override
  String get familyNoAccessHint =>
      'अभी अनुमति नहीं है? मरीज़ से कहें कि वे अपने पोर्टल में सहमति और साझाकरण → परिवार की पहुँच में आपको जोड़ें।';

  @override
  String get familyTitle => 'परिवार का सदस्य या देखभालकर्ता';

  @override
  String familyYouAre(String relationship) {
    return 'आप: $relationship';
  }

  @override
  String get fieldRequired => 'ज़रूरी';

  @override
  String get filterAll => 'सभी';

  @override
  String get filterCancelled => 'रद्द';

  @override
  String get filterPast => 'पिछले';

  @override
  String get filterToday => 'आज';

  @override
  String get filterUpcoming => 'आगामी';

  @override
  String get fixHighlightedFields => 'चिह्नित मापों को ठीक करें।';

  @override
  String get forgotPassword => 'पासवर्ड भूल गए?';

  @override
  String get frequency => 'कितनी बार';

  @override
  String get fullName => 'पूरा नाम';

  @override
  String get gender => 'लिंग';

  @override
  String get genderFemale => 'महिला';

  @override
  String get genderMale => 'पुरुष';

  @override
  String get genderOther => 'अन्य';

  @override
  String get goBack => 'वापस जाएँ';

  @override
  String get goodAfternoon => 'नमस्कार';

  @override
  String get goodEvening => 'शुभ संध्या';

  @override
  String get goodMorning => 'सुप्रभात';

  @override
  String greetingWithName(String greeting, String name) {
    return '$greeting, $name';
  }

  @override
  String get groupAdministration => 'प्रशासन';

  @override
  String get groupClinical => 'क्लिनिकल देखभाल';

  @override
  String get groupDiagnostics => 'जाँच और फ़ार्मेसी';

  @override
  String get groupFrontDesk => 'रिसेप्शन';

  @override
  String get groupOperations => 'वित्त और संचालन';

  @override
  String get groupOverview => 'सारांश';

  @override
  String get groupPatientPortal => 'मेरा स्वास्थ्य';

  @override
  String get groupStaff => 'स्टाफ़';

  @override
  String get groupSystem => 'सिस्टम';

  @override
  String get guestBody =>
      'अपॉइंटमेंट बुक करें, फिर साइन इन करके अपनी विज़िट, पर्चे, रिपोर्ट और बिल देखें।';

  @override
  String get guestEyebrow => 'अस्पताल सेवाएँ';

  @override
  String get guestTitle => 'आपकी देखभाल, एक ही जगह व्यवस्थित';

  @override
  String get haveAccountSignIn => 'पहले से खाता है? साइन इन करें';

  @override
  String get hospital => 'अस्पताल';

  @override
  String get howBookingWorks => 'बुकिंग कैसे होती है';

  @override
  String get howBookingWorksIntro => 'साइन इन से पहले आप चरण देख सकते हैं।';

  @override
  String get icd10Search => 'आईसीडी-10 खोजें (वैकल्पिक)';

  @override
  String get instructions => 'निर्देश';

  @override
  String get interfaceLanguage => 'इंटरफ़ेस की भाषा';

  @override
  String get invoicesPaidTotal => 'भुगतान किए / कुल बिल';

  @override
  String get jumpTo => 'पेज पर जाएँ…';

  @override
  String get jumpToPage => 'किसी पेज पर जाएँ';

  @override
  String get knownCondition => 'ज्ञात स्थिति';

  @override
  String get labBackToWorklist => 'कार्यसूची पर वापस';

  @override
  String labCancelConfirm(String test) {
    return '$test का ऑर्डर रद्द करें? यह रिकॉर्ड में रद्द के रूप में रहेगा।';
  }

  @override
  String get labCancelOrder => 'ऑर्डर रद्द करें';

  @override
  String get labChoosePatient => 'पहले मरीज़ चुनें।';

  @override
  String get labCollectedAt => 'संग्रह का समय';

  @override
  String get labCollectedBy => 'संग्रह किया';

  @override
  String get labCollectionNotes => 'संग्रह टिप्पणी';

  @override
  String get labCommonTestsNote =>
      'सामान्य जाँचें (केवल नाम; अस्पताल प्रणाली में कीमतों वाली जाँच सूची नहीं है):';

  @override
  String get labContainerType => 'पात्र';

  @override
  String get labCountsUnavailable => 'प्रयोगशाला गिनती लोड नहीं हो सकी';

  @override
  String get labDeskIntro =>
      'चुने गए अस्पताल के ऑर्डर, नमूना संग्रह से जारी परिणाम तक।';

  @override
  String get labDispatchNotes => 'भेजने की टिप्पणी';

  @override
  String get labDispatchedBy => 'भेजा';

  @override
  String get labEnteredAt => 'दर्ज करने का समय';

  @override
  String get labEnteredBy => 'दर्ज किया';

  @override
  String get labExternalLab => 'बाहरी प्रयोगशाला';

  @override
  String get labExternalLabHint =>
      'नमूना इसी अस्पताल की प्रयोगशाला जाए तो खाली छोड़ें।';

  @override
  String get labFindSample => 'नमूना खोजें';

  @override
  String get labFindSampleHint =>
      'नमूना संख्या स्कैन करें या लिखें, फिर एंटर दबाएँ';

  @override
  String get labIntro => 'प्रयोगशाला द्वारा जारी परिणाम।';

  @override
  String get labNewOrder => 'नया लैब ऑर्डर';

  @override
  String get labNewOrderIntro =>
      'प्रयोगशाला काउंटर से वॉक-इन ऑर्डर। डॉक्टर परामर्श से, विज़िट से जुड़ा ऑर्डर देते हैं।';

  @override
  String labNextStepByOthers(String step) {
    return 'अगला चरण: $step। इस अस्पताल में आपकी भूमिका यह नहीं कर सकती।';
  }

  @override
  String get labNoOrdersMatch => 'इन फ़िल्टर से कोई ऑर्डर मेल नहीं खाता';

  @override
  String get labNoOrdersYet => 'अभी कोई प्रयोगशाला ऑर्डर नहीं';

  @override
  String get labNoResultYet => 'अभी कोई परिणाम दर्ज नहीं हुआ।';

  @override
  String get labNotADiagnosis =>
      'मान वैसे ही दिखाए गए हैं जैसे प्रयोगशाला ने दर्ज किए। कृपया अपने डॉक्टर से इन पर बात करें।';

  @override
  String get labOpenWorklist => 'कार्यसूची खोलें';

  @override
  String get labOrderCancelled => 'अस्पताल प्रणाली ने ऑर्डर रद्द किया।';

  @override
  String get labOrderMaybeCreated =>
      'अस्पताल प्रणाली से जवाब नहीं आया, इसलिए ऑर्डर शायद हो गया हो। दोबारा ऑर्डर करने से पहले कार्यसूची देखें।';

  @override
  String get labOrderNotAllowed =>
      'इस अस्पताल में आपकी भूमिका प्रयोगशाला ऑर्डर नहीं दे सकती।';

  @override
  String get labOrderTitle => 'प्रयोगशाला ऑर्डर';

  @override
  String get labOrders => 'लैब ऑर्डर';

  @override
  String get labPatientSearchHint =>
      'नाम, फ़ोन या UHID के कम से कम 3 अक्षर लिखें';

  @override
  String get labPlaceOrder => 'ऑर्डर दें';

  @override
  String get labPriorityNormal => 'सामान्य';

  @override
  String labProgressLabel(int stage, int total) {
    return 'चरण $stage / $total';
  }

  @override
  String get labQueueAwaitingCollection => 'संग्रह बाकी';

  @override
  String get labQueueAwaitingRelease => 'जारी करना बाकी';

  @override
  String get labQueueCancelled => 'रद्द';

  @override
  String get labQueueInProgress => 'प्रगति में';

  @override
  String get labQueueReleased => 'जारी';

  @override
  String get labQueueSampleCollected => 'नमूना लिया गया';

  @override
  String get labReceivedBy => 'प्राप्त किया';

  @override
  String labReleaseConfirm(String test) {
    return '$test का सत्यापित परिणाम जारी करें? इसके बाद डॉक्टर और मरीज़ इसे देखेंगे।';
  }

  @override
  String get labReleasedOnly =>
      'प्रयोगशाला की जाँच और जारी करने के बाद रिपोर्ट यहाँ दिखती हैं।';

  @override
  String get labResultAwaitingVerification => 'सत्यापन बाकी';

  @override
  String get labResultNotVerifiedYet =>
      'परिणाम वैसे लिखें जैसे प्रयोगशाला बताती है। अलग सत्यापन चरण तक यह असत्यापित रहेगा।';

  @override
  String get labResultRequired => 'परिणाम दर्ज करें।';

  @override
  String get labResultText => 'परिणाम';

  @override
  String get labResultVerified => 'सत्यापित';

  @override
  String get labReviewOrder => 'ऑर्डर जाँचें';

  @override
  String get labReviewOrderHint =>
      'मरीज़ और जाँच की पुष्टि करें। ऑर्डर तभी होगा जब अस्पताल प्रणाली पुष्टि करेगी।';

  @override
  String get labSample => 'नमूना';

  @override
  String get labSampleNumber => 'नमूना संख्या';

  @override
  String get labSampleNumberHint =>
      'लेबल स्कैन करें, या खाली छोड़ें और अस्पताल प्रणाली नमूने को संख्या देगी।';

  @override
  String get labSampleType => 'नमूने का प्रकार';

  @override
  String get labSearchHint => 'जाँच, मरीज़ या नमूना संख्या खोजें';

  @override
  String get labStatusCollected => 'नमूना लिया गया';

  @override
  String get labStatusDispatched => 'भेजा गया';

  @override
  String get labStatusOrdered => 'ऑर्डर किया';

  @override
  String get labStatusProcessing => 'जाँच जारी';

  @override
  String get labStatusReceived => 'लैब में प्राप्त';

  @override
  String get labStatusResultEntered => 'परिणाम दर्ज';

  @override
  String get labStatusSamplePending => 'नमूना बाकी';

  @override
  String get labStatusVerified => 'सत्यापित';

  @override
  String get labStepCollect => 'नमूना लें';

  @override
  String labStepConfirm(String step, String test) {
    return '$test के लिए $step?';
  }

  @override
  String get labStepDispatch => 'नमूना भेजें';

  @override
  String labStepDone(String step) {
    return '$step: अस्पताल प्रणाली ने सहेजा।';
  }

  @override
  String get labStepEnterResult => 'परिणाम दर्ज करें';

  @override
  String get labStepReceive => 'लैब में प्राप्त करें';

  @override
  String get labStepRefused =>
      'अस्पताल प्रणाली ने यह चरण अस्वीकार किया: ऑर्डर शायद आगे बढ़ चुका है। इसे फिर से लोड किया गया।';

  @override
  String get labStepRelease => 'परिणाम जारी करें';

  @override
  String get labStepStartProcessing => 'जाँच शुरू करें';

  @override
  String get labStepVerify => 'परिणाम सत्यापित करें';

  @override
  String get labTestName => 'जाँच का नाम';

  @override
  String get labTestNameRequired => 'जाँच का नाम दर्ज करें।';

  @override
  String labTestNameTooLong(int max) {
    return 'अधिकतम $max अक्षर लिखें।';
  }

  @override
  String get labTestStatus => 'लैब जाँच की स्थिति';

  @override
  String get labTimeline => 'समयरेखा';

  @override
  String get labTotalOrders => 'लैब ऑर्डर';

  @override
  String get labVerifiedBy => 'सत्यापित किया';

  @override
  String labVerifyConfirm(String test) {
    return '$test का परिणाम सत्यापित करें? दर्ज परिणाम को नमूने और उपकरण रिपोर्ट से मिलाने के बाद ही सत्यापित करें।';
  }

  @override
  String get labWorklist => 'कार्यसूची';

  @override
  String get labWorklistNewestFirst => 'नए ऑर्डर पहले';

  @override
  String get laboratory => 'प्रयोगशाला';

  @override
  String get language => 'भाषा';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageHindi => 'हिंदी';

  @override
  String lastActive(String time) {
    return 'अंतिम बार सक्रिय $time';
  }

  @override
  String lastChecked(String time) {
    return 'अंतिम जाँच $time बजे';
  }

  @override
  String get liveCounts => 'चुने गए अस्पताल की ताज़ा गिनती।';

  @override
  String get loading => 'लोड हो रहा है…';

  @override
  String get loginWithEmail => 'ईमेल से लॉगिन करें';

  @override
  String get loginWithMobile => 'मोबाइल से लॉगिन';

  @override
  String get loginWithTokenId => 'टोकन / ID से लॉगिन';

  @override
  String get logout => 'लॉग आउट';

  @override
  String get lookupAndLogin => 'खोजें और लॉगिन करें';

  @override
  String get markReadFailed => 'पढ़ा हुआ चिह्नित नहीं हो सका';

  @override
  String get medicationSafetyAlerts => 'दवा सुरक्षा चेतावनियाँ';

  @override
  String medicineCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count दवाएँ',
      one: '1 दवा',
    );
    return '$_temp0';
  }

  @override
  String get medicineName => 'दवा';

  @override
  String medicineNameRequired(int number) {
    return 'दवा $number: नाम दर्ज करें।';
  }

  @override
  String medicineNumber(int number) {
    return 'दवा $number';
  }

  @override
  String medicineQuantityInvalid(int number) {
    return 'दवा $number: मात्रा कम से कम 1 हो।';
  }

  @override
  String get medicines => 'दवाएँ';

  @override
  String minutesShort(String minutes) {
    return '$minutes मिनट';
  }

  @override
  String get mobileNumber => 'मोबाइल नंबर';

  @override
  String get moduleNotOnMobileBody =>
      'यह मॉड्यूल बाद के ऐप अपडेट में जोड़ा जाएगा। तब तक यह काम वेब ऐप पर करें।';

  @override
  String moduleNotOnMobileTitle(String module) {
    return '$module अभी मोबाइल ऐप में नहीं है';
  }

  @override
  String get myDoctorProfile => 'मेरी डॉक्टर प्रोफ़ाइल';

  @override
  String get myHospitals => 'मेरे अस्पताल';

  @override
  String get myProfile => 'मेरी प्रोफ़ाइल';

  @override
  String get name => 'नाम';

  @override
  String get navAdminDashboard => 'एडमिन डैशबोर्ड';

  @override
  String get navAiScribe => 'एआई स्क्राइब';

  @override
  String get navAppointments => 'अपॉइंटमेंट';

  @override
  String get navAuditLog => 'ऑडिट लॉग';

  @override
  String get navBilling => 'बिलिंग';

  @override
  String get navBloodBank => 'ब्लड बैंक';

  @override
  String get navCompounder => 'कंपाउंडर';

  @override
  String get navConsultation => 'परामर्श';

  @override
  String get navDepartments => 'विभाग';

  @override
  String get navDoctors => 'डॉक्टर';

  @override
  String get navEmergency => 'आपातकाल';

  @override
  String get navEmergencyAccess => 'आपातकालीन पहुँच';

  @override
  String get navHome => 'होम';

  @override
  String get navHospitalServices => 'अस्पताल सेवाएँ';

  @override
  String get navHospitals => 'अस्पताल';

  @override
  String get navInventory => 'भंडार';

  @override
  String get navIpd => 'आईपीडी / वार्ड / बेड';

  @override
  String get navLaboratory => 'प्रयोगशाला';

  @override
  String get navMain => 'मुख्य';

  @override
  String get navNurseDuty => 'नर्स ड्यूटी';

  @override
  String get navNurses => 'नर्स / वाइटल्स';

  @override
  String get navPatients => 'मरीज़';

  @override
  String get navPermissions => 'अनुमतियाँ';

  @override
  String get navPharmacy => 'फ़ार्मेसी';

  @override
  String get navPrescription => 'पर्चा';

  @override
  String get navQueue => 'कतार';

  @override
  String get navRadiology => 'रेडियोलॉजी';

  @override
  String get navReports => 'रिपोर्ट';

  @override
  String get navRoles => 'भूमिकाएँ';

  @override
  String get navSecuritySettings => 'सुरक्षा सेटिंग्स';

  @override
  String get navUsers => 'उपयोगकर्ता';

  @override
  String get navigation => 'मेन्यू';

  @override
  String get needsAttention => 'ध्यान दें';

  @override
  String get newPassword => 'नया पासवर्ड';

  @override
  String get newToHms => 'अस्पताल प्रबंधन प्रणाली में नए हैं?';

  @override
  String get noAccessTitle => 'आपको पहुँच नहीं है';

  @override
  String get noActiveToken => 'कोई सक्रिय टोकन नहीं';

  @override
  String get noActiveTokenHint => 'अभी आपका कोई परामर्श प्रतीक्षा में नहीं है।';

  @override
  String get noAppointmentsMatch =>
      'इस फ़िल्टर से कोई अपॉइंटमेंट मेल नहीं खाता';

  @override
  String get noAppointmentsToday => 'आज कोई अपॉइंटमेंट नहीं';

  @override
  String get noAppointmentsYet => 'अभी कोई अपॉइंटमेंट नहीं';

  @override
  String get noAppointmentsYetHint =>
      'डॉक्टर और समय चुनने के लिए अपॉइंटमेंट बुक करें दबाएँ।';

  @override
  String get noBedsAvailable => 'कोई बिस्तर उपलब्ध नहीं';

  @override
  String get noBillsYet => 'अभी कोई बिल नहीं';

  @override
  String get noConsultationsYet => 'अभी कोई पूरा परामर्श नहीं';

  @override
  String get noDiagnosesYet => 'अभी कोई निदान नहीं';

  @override
  String get noDoctorInbox =>
      'डॉक्टर सूचनाएँ उपलब्ध नहीं हैं: अस्पताल प्रणाली में अभी स्टाफ़ के लिए इनबॉक्स नहीं है।';

  @override
  String get noDocumentsYet => 'अभी कोई दस्तावेज़ नहीं';

  @override
  String get noFreeSlots => 'इस दिन कोई खाली समय नहीं। दूसरी तारीख आज़माएँ।';

  @override
  String get noHistoryYet => 'कोई इतिहास दर्ज नहीं';

  @override
  String get noHospitalAccess =>
      'आपका खाता अभी किसी अस्पताल में सक्रिय नहीं है। अपने अस्पताल प्रशासक से पूछें।';

  @override
  String get noHospitalMatches => 'आपकी खोज से कोई अस्पताल मेल नहीं खाता।';

  @override
  String get noLabOrdersForVisit => 'इस विज़िट पर कोई लैब जाँच नहीं लिखी गई';

  @override
  String get noLabReportsYet => 'अभी कोई लैब रिपोर्ट नहीं';

  @override
  String get noLabReportsYetHint =>
      'जाँच जारी होने के बाद उनकी रिपोर्ट यहाँ दिखेगी।';

  @override
  String get noMedicinesListed => 'कोई दवा दर्ज नहीं';

  @override
  String get noNotesYet => 'अभी कोई नोट नहीं';

  @override
  String get noNotifications => 'कोई सूचना नहीं';

  @override
  String get noOtherDevices => 'कोई साइन-इन डिवाइस नहीं।';

  @override
  String noPageMatches(String query) {
    return '“$query” से कोई पेज मेल नहीं खाता।';
  }

  @override
  String get noPatientsFound => 'कोई मरीज़ नहीं मिला';

  @override
  String get noPatientsFoundHint => 'केवल आपकी देखरेख वाले मरीज़ दिखते हैं।';

  @override
  String get noPatientsYet => 'अभी तक कोई मरीज़ पंजीकृत नहीं';

  @override
  String get noPaymentsYet => 'कोई भुगतान दर्ज नहीं';

  @override
  String get noPrescriptionsForVisit => 'इस विज़िट पर अभी कोई पर्चा नहीं';

  @override
  String get noPrescriptionsYet => 'अभी कोई पर्चा नहीं';

  @override
  String get noPrescriptionsYetHint => 'आपकी विज़िट के पर्चे यहाँ दिखेंगे।';

  @override
  String get noResultValues => 'इस रिपोर्ट में कोई मान नहीं';

  @override
  String get noShowTitle => 'नहीं आए के रूप में दर्ज करें?';

  @override
  String get noTokenServed => 'अभी कोई टोकन नहीं चल रहा';

  @override
  String get noUpcomingAppointments => 'कोई आगामी अपॉइंटमेंट नहीं';

  @override
  String get noVisitsToShow => 'दिखाने के लिए कोई विज़िट नहीं';

  @override
  String get noVisitsToShowHint =>
      'मरीज़ के आने पर रिसेप्शन पर विज़िट बनती है।';

  @override
  String get noVisitsYet => 'अभी कोई विज़िट नहीं';

  @override
  String get noVitalsYet => 'इस विज़िट पर कोई वाइटल्स दर्ज नहीं';

  @override
  String get nobodyCalled => 'कोई नहीं बुलाया गया';

  @override
  String get nobodyInConsultation => 'परामर्श में कोई नहीं';

  @override
  String get nobodyWaiting => 'कोई प्रतीक्षा में नहीं';

  @override
  String get none => 'कोई नहीं';

  @override
  String get notAvailableNow => 'अभी उपलब्ध नहीं';

  @override
  String notEligibleBody(String department, String roles) {
    return '$department का काम केवल इनके लिए है: $roles। कृपया इनमें से किसी भूमिका वाले खाते से साइन इन करें।';
  }

  @override
  String get notEligibleForPage => 'आप उस पेज के योग्य नहीं हैं';

  @override
  String notEligibleForPageBody(String module) {
    return 'इस अस्पताल में आपकी भूमिका के लिए $module खुला नहीं है।';
  }

  @override
  String get notEligibleTitle => 'आप यह काम नहीं कर सकते';

  @override
  String get notMemberOfAnyHospital => 'आप अभी किसी अस्पताल के सदस्य नहीं हैं।';

  @override
  String get notSignedInSignIn => 'साइन इन नहीं · साइन इन करें';

  @override
  String get notVerified => 'सत्यापित नहीं';

  @override
  String get noteAssessment => 'आकलन';

  @override
  String get noteChiefComplaint => 'मुख्य शिकायत';

  @override
  String get noteCurrentMedications => 'वर्तमान दवाएँ';

  @override
  String get noteExamination => 'जाँच (परीक्षण)';

  @override
  String get noteNeedsOneSection => 'नोट का कम से कम एक भाग लिखें।';

  @override
  String get noteOther => 'अन्य नोट्स';

  @override
  String get notePastHistory => 'पिछला इतिहास';

  @override
  String get notePlan => 'योजना';

  @override
  String get notePresentIllness => 'वर्तमान बीमारी का इतिहास';

  @override
  String get nothingNeedsAttention => 'अभी कुछ ध्यान देने योग्य नहीं';

  @override
  String get nothingNeedsAttentionText =>
      'अभी न कोई प्रतीक्षारत मरीज़, न अर्जेंट जाँच, न सक्रिय आपातकाल।';

  @override
  String get notifications => 'सूचनाएँ';

  @override
  String get notificationsIntro =>
      'आपके अस्पताल के संदेश। संबंधित पेज देखने के लिए किसी को खोलें।';

  @override
  String get nowServing => 'अभी देख रहे हैं';

  @override
  String nowServingToken(String token) {
    return 'अभी टोकन $token चल रहा है';
  }

  @override
  String get open => 'खोलें';

  @override
  String get openConsultation => 'परामर्श खोलें';

  @override
  String get openNavigation => 'मेन्यू खोलें';

  @override
  String get openPatientRecord => 'मरीज़ का रिकॉर्ड खोलें';

  @override
  String get openVisits => 'खुली विज़िट';

  @override
  String get operations => 'संचालन';

  @override
  String get orDivider => 'या';

  @override
  String get orderLabTest => 'लैब जाँच लिखें';

  @override
  String get orderedBy => 'किसने लिखी';

  @override
  String get otpLabel => 'OTP';

  @override
  String get otpPrintedOnServer =>
      'डेवलपमेंट सर्वर: कोड एसएमएस से नहीं भेजा जाता, सर्वर लॉग में दिखता है।';

  @override
  String otpSentTo(String phone) {
    return '$phone पर भेजा गया 6 अंकों का OTP दर्ज करें';
  }

  @override
  String get outstandingBalance => 'बकाया राशि';

  @override
  String get overrideReason => 'फिर भी लिखने का कारण';

  @override
  String overrideReasonHint(int count) {
    return 'कम से कम $count अक्षर। यह पर्चे के साथ दर्ज होता है।';
  }

  @override
  String get password => 'पासवर्ड';

  @override
  String get passwordUpdated => 'पासवर्ड बदल गया। नए पासवर्ड से साइन इन करें।';

  @override
  String get pastVisits => 'पिछली विज़िट';

  @override
  String get patientDataUnavailable =>
      'आपके रिकॉर्ड लोड नहीं हो सके। कनेक्शन जाँचकर फिर कोशिश करें।';

  @override
  String get patientHomeIntro =>
      'आपका कतार टोकन, अपॉइंटमेंट, पर्चे, रिपोर्ट और बिल एक ही जगह।';

  @override
  String get patientId => 'मरीज़ आईडी';

  @override
  String get patientLabel => 'मरीज़';

  @override
  String get patientNavAppointments => 'मेरे अपॉइंटमेंट';

  @override
  String get patientNavBills => 'मेरे बिल';

  @override
  String get patientNavConsent => 'सूचनाएँ / सहमति';

  @override
  String get patientNavHome => 'होम';

  @override
  String get patientNavLab => 'मेरी लैब रिपोर्ट';

  @override
  String get patientNavNotifications => 'सूचनाएँ';

  @override
  String get patientNavPrescriptions => 'मेरे पर्चे';

  @override
  String get patientNavQueue => 'मेरा टोकन / कतार';

  @override
  String get patientNavRecords => 'मेरे मेडिकल रिकॉर्ड';

  @override
  String get patientNotInCare => 'आप यह रिकॉर्ड नहीं खोल सकते';

  @override
  String get patientNotInCareHint =>
      'अस्पताल प्रणाली डॉक्टर को केवल इस अस्पताल में उनकी देखरेख वाले मरीज़ दिखाती है।';

  @override
  String get patientPortal => 'मरीज़ पोर्टल';

  @override
  String get patientProfile => 'मरीज़ प्रोफ़ाइल';

  @override
  String get patientSignIn => 'मरीज़ साइन इन';

  @override
  String get patientSignInIntro =>
      'मरीज़ अपनी अपॉइंटमेंट, पर्चे, रिपोर्ट और बिल देखते हैं।';

  @override
  String get payAtHospital => 'बिल का भुगतान अस्पताल में होता है';

  @override
  String get payAtHospitalBody =>
      'ऑनलाइन भुगतान अभी उपलब्ध नहीं है। बिलिंग काउंटर पर किए गए भुगतान यहाँ दिखते हैं।';

  @override
  String get paymentBankTransfer => 'बैंक ट्रांसफ़र';

  @override
  String get paymentCard => 'कार्ड';

  @override
  String get paymentCash => 'नकद';

  @override
  String get paymentHistory => 'भुगतान इतिहास';

  @override
  String get paymentUpi => 'UPI';

  @override
  String get pickDate => 'तारीख चुनें';

  @override
  String get pickerChange => 'बदलें';

  @override
  String pickerTypeMore(int count) {
    return 'कम से कम $count अक्षर लिखें।';
  }

  @override
  String get platformAndroid => 'Android';

  @override
  String get platformIos => 'iPhone / iPad';

  @override
  String get platformOther => 'अन्य डिवाइस';

  @override
  String get platformWeb => 'वेब ब्राउज़र';

  @override
  String positionShort(String position) {
    return 'स्थान $position';
  }

  @override
  String get prescribeAnyway => 'फिर भी लिखें';

  @override
  String get prescription => 'पर्चा';

  @override
  String get prescriptionFreeTextNote =>
      'हर दवा वेब फ़ॉर्म की तरह लिखें। ऐप कुछ सुझाता नहीं है।';

  @override
  String get prescriptionMaybeSaved =>
      'यह पर्चा शायद पहले ही सहेजा जा चुका है। दोबारा सहेजने से पहले नीचे की सूची देखें।';

  @override
  String prescriptionSaved(String id) {
    return 'पर्चा #$id अस्पताल प्रणाली में सहेजा गया।';
  }

  @override
  String get prescriptionsIntro => 'आपके डॉक्टरों द्वारा लिखी गई दवाएँ।';

  @override
  String get priority => 'प्राथमिकता';

  @override
  String get profileChangesAtHospital =>
      'अपना विवरण बदलने के लिए कृपया अस्पताल के रिसेप्शन से संपर्क करें।';

  @override
  String get profileIntro => 'अस्पताल में दर्ज आपका विवरण।';

  @override
  String profileMenuFor(String name) {
    return '$name का प्रोफ़ाइल मेन्यू';
  }

  @override
  String get quantity => 'मात्रा';

  @override
  String get queueCall => 'बुलाएँ';

  @override
  String get queueComplete => 'पूरा करें';

  @override
  String get queueDoctorBusy =>
      'इस डॉक्टर के पास पहले से एक मरीज़ परामर्श में है। पहले उसे पूरा करें।';

  @override
  String queueFinishedToday(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'आज $count टोकन पूरे',
      one: 'आज 1 टोकन पूरा',
      zero: 'आज कोई टोकन पूरा नहीं',
    );
    return '$_temp0';
  }

  @override
  String get queueIntro =>
      'आज की परामर्श कतार में आपकी जगह। यह पेज खुला रहने पर हर 30 सेकंड में फिर जाँचता है।';

  @override
  String queueMoveConfirm(String token) {
    return 'टोकन #$token कतार से हटेगा। अस्पताल प्रणाली मरीज़ को सूचित कर सकती है।';
  }

  @override
  String get queueMoveFailed => 'कतार अपडेट नहीं हो सकी';

  @override
  String get queueNoShow => 'नहीं आए';

  @override
  String get queuePosition => 'कतार में स्थान';

  @override
  String get queueSkip => 'छोड़ें';

  @override
  String get queueStartConsultation => 'परामर्श शुरू करें';

  @override
  String get queueStatus => 'कतार की स्थिति';

  @override
  String get quickActions => 'तुरंत करने वाले काम';

  @override
  String get reasonForVisit => 'आने का कारण';

  @override
  String get recentConsultations => 'हाल के परामर्श';

  @override
  String get recentLabReports => 'हाल की लैब रिपोर्ट';

  @override
  String get recentPrescriptions => 'हाल के पर्चे';

  @override
  String get recentlyRegistered => 'हाल में पंजीकृत मरीज़';

  @override
  String get recordSignedNoChange =>
      'यह रिकॉर्ड हस्ताक्षरित है और बदला नहीं जा सकता। इसके बजाय नया रिकॉर्ड जोड़ें।';

  @override
  String get referenceRange => 'संदर्भ सीमा';

  @override
  String get refresh => 'ताज़ा करें';

  @override
  String get refreshFailed => 'ताज़ा नहीं हो सका';

  @override
  String get refund => 'वापसी';

  @override
  String get registerIntro => 'स्टाफ़ खाते अस्पताल के निमंत्रण से बनते हैं।';

  @override
  String get registerTitle => 'अपना मरीज़ खाता बनाएँ';

  @override
  String registeredInTotal(String count) {
    return 'कुल $count पंजीकृत';
  }

  @override
  String get registration => 'पंजीकरण';

  @override
  String get releasedOn => 'जारी होने की तारीख';

  @override
  String get releasedResults => 'जारी परिणाम';

  @override
  String get remarks => 'टिप्पणी';

  @override
  String get removeMedicine => 'दवा हटाएँ';

  @override
  String get reportNotes => 'रिपोर्ट टिप्पणी';

  @override
  String get resendCode => 'कोड दोबारा भेजें';

  @override
  String get resetCodeSent =>
      'यदि कोई सक्रिय स्टाफ़ खाता मेल खाता है, तो उसके दर्ज मोबाइल नंबर पर कोड भेजा गया है।';

  @override
  String get resetConfirmIntro =>
      'एसएमएस से आया कोड दर्ज करें और नया पासवर्ड चुनें।';

  @override
  String get resetPasswordTitle => 'अपना पासवर्ड रीसेट करें';

  @override
  String get resetRequestIntro =>
      'आपके स्टाफ़ खाते में दर्ज मोबाइल नंबर पर एक कोड भेजा जाता है।';

  @override
  String get restoreFailedBody =>
      'आपका साइन इन इस डिवाइस पर सुरक्षित है। कनेक्शन जाँचकर फिर कोशिश करें, या साइन आउट करें।';

  @override
  String get restoreFailedTitle => 'अस्पताल सर्वर तक नहीं पहुँच सके';

  @override
  String get restoringSession => 'आपका सत्र खोला जा रहा है…';

  @override
  String get resultNotReleased => 'परिणाम अभी जारी नहीं';

  @override
  String get results => 'परिणाम';

  @override
  String get retry => 'फिर कोशिश करें';

  @override
  String get roleAdmin => 'एडमिन';

  @override
  String get roleBillingStaff => 'बिलिंग स्टाफ़';

  @override
  String get roleBloodBankStaff => 'ब्लड बैंक स्टाफ़';

  @override
  String get roleCompounder => 'कंपाउंडर';

  @override
  String get roleDoctor => 'डॉक्टर';

  @override
  String get roleHomeBilling => 'आज की बिलिंग';

  @override
  String get roleHomeBloodBank => 'आज ब्लड बैंक';

  @override
  String get roleHomeDoctor => 'आज आपका क्लिनिक';

  @override
  String get roleHomeLaboratory => 'आज प्रयोगशाला';

  @override
  String get roleHomeNurse => 'आज आपका वार्ड';

  @override
  String get roleHomePharmacy => 'आज फ़ार्मेसी';

  @override
  String get roleHomeReceptionist => 'आज रिसेप्शन';

  @override
  String get roleHomeStore => 'आज भंडार';

  @override
  String get roleHospitalManager => 'अस्पताल प्रबंधक';

  @override
  String get roleInventoryStaff => 'भंडार स्टाफ़';

  @override
  String get roleLabStaff => 'लैब स्टाफ़';

  @override
  String get roleNurse => 'नर्स';

  @override
  String get rolePharmacist => 'फ़ार्मासिस्ट';

  @override
  String get roleReceptionist => 'रिसेप्शनिस्ट';

  @override
  String get saveNoteDraft => 'नोट मसौदे के रूप में सहेजें';

  @override
  String get saveVitals => 'वाइटल्स सहेजें';

  @override
  String get searchByNameOrCity => 'नाम या शहर से खोजें';

  @override
  String get searchHospitals => 'अस्पताल खोजें';

  @override
  String get searchPages => 'पेज खोजें';

  @override
  String get searchPatientName => 'मरीज़ के नाम से खोजें';

  @override
  String get searchPatientsHint => 'नाम, मोबाइल नंबर या यूएचआईडी';

  @override
  String get selectDoctor => 'डॉक्टर चुनें';

  @override
  String get selectHospital => 'अस्पताल चुनें';

  @override
  String get selectHospitalForDashboard =>
      'डैशबोर्ड देखने के लिए ऊपर से अस्पताल चुनें।';

  @override
  String get selectHospitalTitle => 'अस्पताल चुनें';

  @override
  String get selectedHospital => 'चुना गया अस्पताल';

  @override
  String get sendEmailOtp => 'ईमेल OTP भेजें';

  @override
  String get sendOtp => 'OTP भेजें';

  @override
  String get sendResetCode => 'रीसेट कोड भेजें';

  @override
  String get serverConnection => 'सर्वर कनेक्शन';

  @override
  String get serverConnectionText =>
      'जाँचें कि यह डिवाइस अस्पताल सर्वर तक पहुँच सकता है।';

  @override
  String get sessionEndedNotice =>
      'आपका सत्र समाप्त हो गया। कृपया फिर से साइन इन करें।';

  @override
  String get setNewPassword => 'नया पासवर्ड सेट करें';

  @override
  String get settings => 'सेटिंग्स';

  @override
  String get signIn => 'साइन इन करें';

  @override
  String get signInMethod => 'साइन इन का तरीका';

  @override
  String get signInRequired => 'साइन इन ज़रूरी है';

  @override
  String get signInTitle => 'साइन इन करें';

  @override
  String signInToOpen(String module) {
    return '$module खोलने के लिए अनुमति वाले स्टाफ़ खाते से साइन इन करें।';
  }

  @override
  String get signInToSee => 'देखने के लिए साइन इन करें';

  @override
  String get signInUnavailableBody =>
      'स्टाफ़ और मरीज़ साइन इन अगले ऐप अपडेट में आएगा। तब तक साइन इन के लिए वेब ऐप का उपयोग करें।';

  @override
  String get signInUnavailableTitle => 'इस ऐप संस्करण में अभी साइन इन नहीं है';

  @override
  String get signOut => 'साइन आउट';

  @override
  String get signOutDevice => 'साइन आउट';

  @override
  String get signOutDeviceConfirm => 'इस डिवाइस को साइन आउट करें?';

  @override
  String get signOutEverywhere => 'हर जगह से साइन आउट';

  @override
  String get signOutEverywhereConfirm =>
      'इस डिवाइस समेत हर डिवाइस से साइन आउट करें?';

  @override
  String get signRecord => 'हस्ताक्षर करें';

  @override
  String get signRecordBody =>
      'हस्ताक्षरित रिकॉर्ड अंतिम होता है। सुधार नए रिकॉर्ड के रूप में जोड़े जाते हैं।';

  @override
  String get signRecordTitle => 'इस रिकॉर्ड पर हस्ताक्षर करें?';

  @override
  String signedInAs(String name) {
    return '$name के रूप में साइन इन';
  }

  @override
  String get signedInDevices => 'साइन-इन डिवाइस';

  @override
  String get signedInDevicesIntro =>
      'जिन डिवाइस पर आपका खाता साइन इन है। जिसे न पहचानें, उसे साइन आउट करें।';

  @override
  String signedOn(String date) {
    return 'हस्ताक्षरित $date';
  }

  @override
  String get sixDigitCode => '6 अंकों का कोड';

  @override
  String get skipTokenTitle => 'यह टोकन छोड़ें?';

  @override
  String get somePatientDataUnavailable => 'आपके कुछ रिकॉर्ड लोड नहीं हो सके।';

  @override
  String get somethingWentWrong => 'कुछ गलत हो गया';

  @override
  String get specialization => 'विशेषज्ञता';

  @override
  String get staffPortal => 'स्टाफ़ पोर्टल';

  @override
  String get staffSignIn => 'स्टाफ़ साइन इन';

  @override
  String get staffSignInIntro => 'अपने अस्पताल स्टाफ़ खाते का उपयोग करें।';

  @override
  String get startConsultation => 'परामर्श शुरू करें';

  @override
  String get status => 'स्थिति';

  @override
  String get statusAcknowledged => 'पुष्टि की';

  @override
  String get statusCalled => 'बुलाया गया';

  @override
  String get statusCancelled => 'रद्द';

  @override
  String get statusCheckedIn => 'चेक-इन हो गया';

  @override
  String get statusCompleted => 'पूरा हुआ';

  @override
  String get statusConfirmed => 'पुष्ट';

  @override
  String get statusDispensed => 'दवा दी गई';

  @override
  String get statusInConsultation => 'परामर्श में';

  @override
  String get statusNoShow => 'नहीं आए';

  @override
  String get statusPaid => 'भुगतान हो गया';

  @override
  String get statusPartiallyDispensed => 'आंशिक दवा दी गई';

  @override
  String get statusPartiallyPaid => 'आंशिक भुगतान';

  @override
  String get statusPending => 'बाकी';

  @override
  String get statusReady => 'तैयार';

  @override
  String get statusReleased => 'जारी';

  @override
  String get statusScheduled => 'निर्धारित';

  @override
  String get statusUnpaid => 'बकाया';

  @override
  String get statusUrgent => 'तत्काल';

  @override
  String get statusWaiting => 'प्रतीक्षा में';

  @override
  String get stepChooseSlot => 'Choose a slot';

  @override
  String get stepChooseSlotText => 'Pick a date and an available time.';

  @override
  String get stepConfirm => 'Confirm';

  @override
  String get stepConfirmText => 'Sign in to confirm the booking.';

  @override
  String get stepSelectDoctor => 'डॉक्टर चुनें';

  @override
  String get stepSelectDoctorText => 'Choose a department and doctor.';

  @override
  String get stepSelectHospitalText => 'Pick where you want to be seen.';

  @override
  String get switchingHospitalNote =>
      'अस्पताल बदलने पर आपकी हर सूची उस अस्पताल के रिकॉर्ड दिखाने लगती है।';

  @override
  String get tabEmail => 'ईमेल';

  @override
  String get tabFamily => 'परिवार';

  @override
  String get tabMobileOtp => 'मोबाइल OTP';

  @override
  String get tabTokenId => 'टोकन / ID';

  @override
  String get testDate => 'जाँच की तारीख';

  @override
  String get thisDevice => 'यह डिवाइस';

  @override
  String get tileAppointmentsToday => 'आज के अपॉइंटमेंट';

  @override
  String get tileBedsAvailable => 'उपलब्ध बिस्तर';

  @override
  String get tileBillingPending => 'भुगतान बाकी बिल';

  @override
  String get tileCollectedToday => 'आज की वसूली';

  @override
  String get tileCurrentAdmissions => 'मौजूदा भर्ती';

  @override
  String get tileLabCompleted => 'पूरी हुई लैब जाँच';

  @override
  String get tileLabPending => 'बाकी लैब जाँच';

  @override
  String get tileLabUrgent => 'अर्जेंट लैब जाँच';

  @override
  String get tilePatientsToday => 'आज पंजीकृत मरीज़';

  @override
  String get tileWaitingInQueue => 'कतार में प्रतीक्षा';

  @override
  String get timeLabel => 'समय';

  @override
  String get todayAtAGlance => 'आज एक नज़र में';

  @override
  String get todaysAppointments => 'आज के अपॉइंटमेंट';

  @override
  String get todaysPatientFlow => 'आज के मरीज़';

  @override
  String get tokenCalled => 'आपका टोकन बुलाया गया है';

  @override
  String get tokenCalledBody => 'कृपया अभी परामर्श क्षेत्र में जाएँ।';

  @override
  String get tokenIdHint =>
      'पंजीकरण की मरीज़ ID अपने खाते के पासवर्ड के साथ उपयोग करें।';

  @override
  String get tokenIdIntro => 'अपना टोकन नंबर या अस्पताल मरीज़ ID दर्ज करें';

  @override
  String get tokenLabel => 'टोकन';

  @override
  String get tokenNext => 'अगला नंबर आपका है। डॉक्टर जल्द ही आपको देखेंगे।';

  @override
  String tokenNumber(String number) {
    return 'टोकन $number';
  }

  @override
  String get tokenOrPatientId => 'टोकन नंबर / मरीज़ ID';

  @override
  String get tryAgain => 'फिर से कोशिश करें';

  @override
  String get typeModuleName => 'मॉड्यूल का नाम लिखें…';

  @override
  String typeToSearch(int count) {
    return 'खोजने के लिए कम से कम $count अक्षर लिखें';
  }

  @override
  String get unread => 'अपठित';

  @override
  String unreadNotifications(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'आपकी $count अपठित सूचनाएँ हैं',
      one: 'आपकी 1 अपठित सूचना है',
    );
    return '$_temp0';
  }

  @override
  String get upcomingAppointments => 'आगामी अपॉइंटमेंट';

  @override
  String get useDifferentNumber => 'दूसरा नंबर इस्तेमाल करें';

  @override
  String get usernameOrEmail => 'यूज़रनेम या ईमेल';

  @override
  String get verified => 'सत्यापित';

  @override
  String get verifyAndContinue => 'पुष्टि करें और आगे बढ़ें';

  @override
  String get verifyAndContinueShort => 'सत्यापित करें और आगे बढ़ें';

  @override
  String verifyEmailIntro(String email) {
    return '$email पर भेजा गया कोड दर्ज करें। फिर अपने ईमेल और पासवर्ड से साइन इन करें।';
  }

  @override
  String get verifyOtp => 'OTP सत्यापित करें';

  @override
  String get verifyUsingEmail => 'ईमेल से सत्यापित करें';

  @override
  String get verifyYourEmail => 'अपना ईमेल सत्यापित करें';

  @override
  String get viewAll => 'सभी देखें';

  @override
  String get viewMyAppointments => 'मेरे अपॉइंटमेंट देखें';

  @override
  String get viewProfile => 'प्रोफ़ाइल देखें';

  @override
  String viewingHospital(String name) {
    return '$name के रिकॉर्ड दिख रहे हैं';
  }

  @override
  String get visitClosedReadOnly =>
      'यह विज़िट बंद है। इसके रिकॉर्ड केवल पढ़ने के लिए हैं।';

  @override
  String get visits => 'विज़िट';

  @override
  String get vitalBloodSugar => 'ब्लड शुगर';

  @override
  String get vitalDiastolic => 'डायस्टोलिक बीपी';

  @override
  String get vitalHeight => 'ऊँचाई';

  @override
  String get vitalNegative => 'ऋणात्मक नहीं हो सकता।';

  @override
  String get vitalNotANumber => 'संख्या दर्ज करें।';

  @override
  String get vitalPainScore => 'दर्द स्कोर';

  @override
  String get vitalPulse => 'नाड़ी';

  @override
  String get vitalRespiratoryRate => 'श्वसन दर';

  @override
  String get vitalSpo2 => 'एसपीओ₂';

  @override
  String get vitalSystolic => 'सिस्टोलिक बीपी';

  @override
  String get vitalTemperature => 'तापमान';

  @override
  String get vitalTooHigh => 'अनुमत अधिकतम से अधिक।';

  @override
  String get vitalTooPrecise => 'अधिकतम 2 दशमलव स्थान।';

  @override
  String get vitalWeight => 'वज़न';

  @override
  String get vitalWholeNumber => 'पूर्ण संख्या दर्ज करें।';

  @override
  String get vitals => 'वाइटल्स';

  @override
  String get vitalsSaved => 'वाइटल्स अस्पताल प्रणाली में सहेजे गए।';

  @override
  String get waitingPatients => 'प्रतीक्षा में';

  @override
  String get weWillSendCode => 'हम 6 अंकों का सत्यापन कोड भेजेंगे';

  @override
  String get welcome => 'स्वागत है';

  @override
  String get writeInConsultation => 'परामर्श में लिखें';

  @override
  String get yourMobileNumber => 'आपका मोबाइल नंबर';
}
