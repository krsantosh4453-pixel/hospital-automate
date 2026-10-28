import { PrintedDocument, PrintedFacts } from "../ui"
import { formatPrintDate } from "../../utils/printDate.js"

// Printable layouts for documents a patient takes away. Each takes the row
// exactly as the API returns it; render them inside <PrintSheet>.

const rupees = (value) => `₹${Number(value || 0).toFixed(2)}`

function patientLine(record) {
  return [record.patient_name, record.patient_age && `${record.patient_age} y`, record.patient_gender]
    .filter(Boolean)
    .join(", ")
}

/** Medical certificate (requirement D10). */
export function CertificateDocument({ certificate }) {
  const period = certificate.end_date
    ? `${formatPrintDate(certificate.start_date)} to ${formatPrintDate(certificate.end_date)}`
    : `from ${formatPrintDate(certificate.start_date)}`
  const statement =
    certificate.kind === "Fitness"
      ? `This is to certify that I have examined the patient and found them fit to resume normal duties ${period}.`
      : certificate.kind === "Sick leave"
        ? `This is to certify that the patient was under my treatment and is advised rest ${period}.`
        : `This certificate is issued for the period ${period}.`

  return (
    <PrintedDocument
      hospitalName={certificate.hospital_name}
      hospitalAddress={certificate.hospital_address}
      title={`Medical certificate (${certificate.kind})`}
      reference={`CERT-${certificate.id}`}
      date={formatPrintDate(certificate.issued_at)}
      signature={
        <>
          {certificate.doctor_name}
          {certificate.doctor_specialization && <><br />{certificate.doctor_specialization}</>}
        </>
      }
    >
      <PrintedFacts rows={[["Patient", patientLine(certificate)], ["Diagnosis", certificate.diagnosis]]} />
      <p>{statement}</p>
      {certificate.remarks && <p className="whitespace-pre-line">{certificate.remarks}</p>}
    </PrintedDocument>
  )
}

/** Referral letter (requirement D11). */
export function ReferralDocument({ referral }) {
  return (
    <PrintedDocument
      hospitalName={referral.hospital_name}
      hospitalAddress={referral.hospital_address}
      title="Referral"
      reference={`REF-${referral.id}`}
      date={formatPrintDate(referral.created_at)}
      signature={referral.referring_doctor_name}
    >
      <PrintedFacts
        rows={[
          ["To", referral.referred_to_doctor_name || referral.referred_to_external],
          ["Specialty", referral.specialty],
          ["Urgency", referral.urgency],
          ["Patient", patientLine(referral)],
        ]}
      />
      <section>
        <p className="font-semibold">Reason for referral</p>
        <p className="whitespace-pre-line">{referral.reason}</p>
      </section>
    </PrintedDocument>
  )
}

/** Patient copy of an invoice with its payments (requirement H7). */
export function InvoiceDocument({ invoice, hospitalAddress }) {
  const items = invoice.items || []
  const payments = invoice.payments || []
  return (
    <PrintedDocument
      hospitalName={invoice.hospital_name}
      hospitalAddress={hospitalAddress}
      title="Invoice"
      reference={invoice.invoice_number || invoice.id}
      date={formatPrintDate(invoice.created_at)}
    >
      <PrintedFacts rows={[["Patient", invoice.patient_name], ["Status", invoice.status]]} />
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-black">
            <th className="py-1">Description</th>
            <th className="py-1 text-right">Qty</th>
            <th className="py-1 text-right">Rate</th>
            <th className="py-1 text-right">Amount</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-b border-gray-300">
              <td className="py-1">{item.description}</td>
              <td className="py-1 text-right">{item.quantity}</td>
              <td className="py-1 text-right">{rupees(item.unit_price)}</td>
              <td className="py-1 text-right">{rupees(item.subtotal)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="ml-auto w-64">
        <PrintedFacts
          rows={[
            ["Subtotal", rupees(invoice.subtotal)],
            ["Discount", Number(invoice.discount) ? `− ${rupees(invoice.discount)}` : ""],
            ["Tax", Number(invoice.tax_amount) ? rupees(invoice.tax_amount) : ""],
            ["Total", rupees(invoice.total_amount)],
            ["Paid", rupees(invoice.total_paid)],
            ["Balance due", rupees(invoice.balance_due)],
          ]}
        />
      </div>
      {payments.length > 0 && (
        <section>
          <p className="font-semibold">Payments</p>
          <ul>
            {payments.map((payment) => (
              <li key={payment.id}>
                {formatPrintDate(payment.paid_at)} · {payment.kind === "refund" ? "Refund" : payment.payment_method} ·{" "}
                {rupees(payment.amount)}
                {payment.receipt_number && ` · Receipt ${payment.receipt_number}`}
              </li>
            ))}
          </ul>
        </section>
      )}
    </PrintedDocument>
  )
}

/** Released lab result (requirement G3). Unreleased results are never printed. */
export function LabReportDocument({ test }) {
  if (test.status !== "Released") {
    return <p>This result has not been released by the laboratory yet, so it cannot be printed.</p>
  }

  const result = test.lab_result || {}
  const values = Object.entries(result.result_data || {})
  const ranges = result.reference_ranges || {}
  const abnormal = new Set(result.abnormal_flags || [])

  return (
    <PrintedDocument
      hospitalName={test.hospital_name}
      title="Laboratory report"
      reference={`LAB-${test.id}`}
      date={formatPrintDate(test.released_at)}
      signature={result.verified_by_name ? `Verified by ${result.verified_by_name}` : "Verified"}
    >
      <PrintedFacts
        rows={[
          ["Patient", test.patient_name],
          ["Test", test.name],
          ["Ordered by", test.doctor_name],
          ["Collected", formatPrintDate(test.collected_at)],
        ]}
      />
      {values.length > 0 && (
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-black">
              <th className="py-1">Parameter</th>
              <th className="py-1">Result</th>
              <th className="py-1">Reference range</th>
            </tr>
          </thead>
          <tbody>
            {values.map(([name, value]) => (
              <tr key={name} className="border-b border-gray-300">
                <td className="py-1">{name}</td>
                <td className={`py-1 ${abnormal.has(name) ? "font-bold" : ""}`}>
                  {String(value)}
                  {abnormal.has(name) && " (abnormal)"}
                </td>
                <td className="py-1">{ranges[name] ? String(ranges[name]) : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {(result.result_text || test.result) && (
        <p className="whitespace-pre-line">{result.result_text || test.result}</p>
      )}
    </PrintedDocument>
  )
}
