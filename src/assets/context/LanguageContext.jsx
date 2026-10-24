import { createContext, useCallback, useContext, useEffect, useState } from "react"

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
  // AI
  "AI Draft — Pending Review": "एआई ड्राफ्ट — डॉक्टर की समीक्षा बाकी",
  "Approved by clinician": "डॉक्टर द्वारा स्वीकृत",
}

const DICTIONARIES = { en: {}, hi: HI }

const LanguageContext = createContext({ language: "en", setLanguage: () => {}, t: (text) => text })

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

  // Unknown text falls back to the English original.
  const t = useCallback((text) => DICTIONARIES[language][text] || text, [language])

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  return useContext(LanguageContext)
}
