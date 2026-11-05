import { PrintedDocument, PrintedFacts } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { PAPER_SOURCE } from "../../utils/prescriptionRecord.js"

// F8: the slip handed over with the medicine. Dose, frequency, duration and
// instructions are printed exactly as the prescription saved them; a blank
// instruction stays blank (a dash), never a made-up default.
export default function DispensingSlip({ prescription, hospital, printedBy }) {
  const { t } = useLanguage()
  const paper = prescription.source === PAPER_SOURCE
  return (
    <PrintedDocument
      hospitalName={hospital?.name}
      hospitalAddress={hospital?.address}
      title={t("Dispensing slip")}
      reference={prescription.id}
      date={new Date().toLocaleDateString("en-IN")}
      signature={printedBy ? t("Dispensed by {name}", { name: printedBy }) : t("Pharmacist")}
    >
      <PrintedFacts
        rows={[
          [t("Patient"), prescription.patientName],
          [t("UHID"), prescription.patientUhid],
          [t("Prescribed by"), prescription.doctor || prescription.originalPrescriberName],
          [t("Prescribed on"), prescription.createdAt],
          paper && [t("Source"), t("Paper prescription dated {date}", { date: prescription.originalPrescriptionDate })],
        ].filter(Boolean)}
      />
      <table className="w-full border-collapse text-left text-xs">
        <thead>
          <tr className="border-b border-black">
            <th className="py-1 pr-2">{t("Medicine")}</th>
            <th className="py-1 pr-2">{t("Dose")}</th>
            <th className="py-1 pr-2">{t("Frequency")}</th>
            <th className="py-1 pr-2">{t("Duration")}</th>
            <th className="py-1 pr-2 text-right">{t("Qty")}</th>
            <th className="py-1">{t("Instructions")}</th>
          </tr>
        </thead>
        <tbody>
          {prescription.medicines.map((item) => (
            <tr key={item.id} className="border-b border-gray-300 align-top">
              <td className="py-1 pr-2 font-semibold">{item.name}</td>
              <td className="py-1 pr-2">{item.dosage || "—"}</td>
              <td className="py-1 pr-2">{item.frequency || "—"}</td>
              <td className="py-1 pr-2">{item.duration || "—"}</td>
              <td className="py-1 pr-2 text-right tabular-nums">{item.dispensed || item.quantity}</td>
              <td className="py-1">{item.instructions || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </PrintedDocument>
  )
}
