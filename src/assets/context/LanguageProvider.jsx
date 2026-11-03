import { useCallback, useEffect, useState } from "react"
import HI_PAGES from "../i18n/hiPages.js"
import { LanguageContext, fillPlaceholders } from "./LanguageContext.jsx"

// Interface language (English / Hindi). Only interface text is translated;
// clinical content is always shown exactly as it was entered.
const STORAGE_KEY = "hms_language"

const HI = {
  // Shell
  "HMS Portal": "एचएमएस पोर्टल",
  "Hospital Management": "अस्पताल प्रबंधन",
  "Select Hospital": "अस्पताल चुनें",
  "Search patients": "मरीज़ खोजें",
  Notifications: "सूचनाएँ",
  Logout: "लॉग आउट",
  Loading: "लोड हो रहा है",
  // Staff navigation groups
  Overview: "सारांश",
  "Front desk": "रिसेप्शन",
  "Clinical care": "क्लिनिकल देखभाल",
  "Diagnostics & pharmacy": "जाँच और फ़ार्मेसी",
  "Finance & operations": "वित्त और संचालन",
  Staff: "स्टाफ़",
  Administration: "प्रशासन",
  System: "सिस्टम",
  // Staff navigation
  Home: "होम",
  Patients: "मरीज़",
  Appointments: "अपॉइंटमेंट",
  Queue: "कतार",
  Consultation: "परामर्श",
  Prescription: "पर्चा",
  Doctors: "डॉक्टर",
  "Nurses / Vitals": "नर्स / वाइटल्स",
  Compounder: "कंपाउंडर",
  Pharmacy: "फ़ार्मेसी",
  Laboratory: "प्रयोगशाला",
  Billing: "बिलिंग",
  Inventory: "भंडार",
  Reports: "रिपोर्ट",
  Emergency: "आपातकाल",
  "Blood Bank": "ब्लड बैंक",
  "IPD / Ward / Beds": "आईपीडी / वार्ड / बेड",
  "AI Scribe": "एआई स्क्राइब",
  "Admin Dashboard": "एडमिन डैशबोर्ड",
  Users: "उपयोगकर्ता",
  Roles: "भूमिकाएँ",
  Hospitals: "अस्पताल",
  Departments: "विभाग",
  Permissions: "अनुमतियाँ",
  Settings: "सेटिंग्स",
  // Patient portal navigation
  "My Appointments": "मेरे अपॉइंटमेंट",
  "My Queue / Token": "मेरा टोकन / कतार",
  "My Medical Records": "मेरे मेडिकल रिकॉर्ड",
  "My Prescriptions": "मेरे पर्चे",
  "My Lab Reports": "मेरी लैब रिपोर्ट",
  "My Bills": "मेरे बिल",
  "Notifications / Consent": "सूचनाएँ / सहमति",
  // Consent page
  "Consent Forms": "सहमति फ़ॉर्म",
  "Share My Records": "मेरे रिकॉर्ड साझा करें",
  "Stop Sharing": "साझा करना बंद करें",
  "Review & Sign": "पढ़ें और हस्ताक्षर करें",
  Withdraw: "सहमति वापस लें",
  // Shell: skip link, search, sign-in footer
  "Skip to main content": "मुख्य सामग्री पर जाएँ",
  "Jump to…": "पेज पर जाएँ…",
  "Sign in": "साइन इन करें",
  "Not signed in · Sign in": "साइन इन नहीं · साइन इन करें",
  "Signed in as {name}": "{name} के रूप में साइन इन",
  "Role: {name}": "भूमिका: {name}",
  // Roles and what each may do
  Admin: "एडमिन",
  Receptionist: "रिसेप्शनिस्ट",
  Pharmacist: "फ़ार्मासिस्ट",
  "Lab Staff": "लैब स्टाफ़",
  "Blood Bank Staff": "ब्लड बैंक स्टाफ़",
  "Billing Staff": "बिलिंग स्टाफ़",
  "Inventory Staff": "भंडार स्टाफ़",
  "Hospital Manager": "अस्पताल प्रबंधक",
  "Full system access to all modules and administration": "सभी मॉड्यूल और प्रशासन तक पूरी पहुँच",
  "Access to patients, consultations, appointments, lab results and prescriptions":
    "मरीज़, परामर्श, अपॉइंटमेंट, लैब रिपोर्ट और पर्चों तक पहुँच",
  "Manage patient vitals, queue triage, and view appointments": "मरीज़ों के वाइटल्स, कतार ट्राइएज और अपॉइंटमेंट देखना",
  "Dispense medicines, manage stock and pharmacy orders": "दवा देना, स्टॉक और फ़ार्मेसी ऑर्डर संभालना",
  "Patient registration, token generation, appointments, and billing": "मरीज़ पंजीकरण, टोकन, अपॉइंटमेंट और बिलिंग",
  "Manage pharmacy inventory, sales, and dispensing": "फ़ार्मेसी स्टॉक, बिक्री और दवा वितरण संभालना",
  "Manage laboratory tests and results": "लैब जाँच और रिपोर्ट संभालना",
  "Manage blood inventory, requests, and transactions": "रक्त भंडार, अनुरोध और लेन-देन संभालना",
  "Manage invoices, payments, and insurance claims": "बिल, भुगतान और बीमा दावे संभालना",
  "Manage procurement and stock": "खरीद और स्टॉक संभालना",
  "Hospital-level administration and oversight": "अस्पताल स्तर का प्रशासन और निगरानी",
  "View personal appointments, queue status, lab tests and invoices": "अपने अपॉइंटमेंट, कतार, लैब जाँच और बिल देखना",
  // AI
  "AI Draft — Pending Review": "एआई ड्राफ्ट — डॉक्टर की समीक्षा बाकी",
  "Approved by clinician": "डॉक्टर द्वारा स्वीकृत",
}

// Page text (A17) first; the shell entries above win where both define a string.
const DICTIONARIES = { en: {}, hi: { ...HI_PAGES, ...HI } }



const readStored = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved === "hi" ? "hi" : "en"
  } catch {
    return "en"
  }
}

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(readStored)

  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  const setLanguage = useCallback((next) => {
    const value = next === "hi" ? "hi" : "en"
    setLanguageState(value)
    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch {
      // Preference simply won't persist (private mode).
    }
  }, [])

  // Unknown text falls back to the English original. Sentences carrying names
  // or numbers are keyed with {placeholders}, filled after lookup so Hindi can
  // put them where its word order needs them.
  const t = useCallback(
    (text, vars) => fillPlaceholders(DICTIONARIES[language][text] || text, vars),
    [language],
  )

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}
