import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it } from "vitest"
import { PRINTING_CLASS, PrintSheet } from "../components/ui/PrintSheet.jsx"
import { CertificateDocument, LabReportDocument } from "../components/documents/ClinicalDocuments.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe("PrintSheet", () => {
  let root
  let host

  const render = (element) => {
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    act(() => root.render(element))
  }

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  const printedSheet = () => document.querySelector("body > .hms-print-sheet")

  it("marks the body for printing only while open, with the document as a direct child of body", () => {
    render(<PrintSheet open title="Invoice" onClose={() => {}}><p>Invoice body</p></PrintSheet>)

    expect(document.body.classList.contains(PRINTING_CLASS)).toBe(true)
    expect(printedSheet()?.textContent).toBe("Invoice body")

    act(() => root.render(<PrintSheet open={false} title="Invoice" onClose={() => {}}><p>Invoice body</p></PrintSheet>))

    expect(document.body.classList.contains(PRINTING_CLASS)).toBe(false)
    expect(printedSheet()).toBeNull()
  })

  it("never prints a lab result the laboratory has not released", () => {
    const test = { id: 7, status: "Verified", name: "CBC", lab_result: { result_data: { Hb: "9.1" } } }

    render(<PrintSheet open title="Lab report" onClose={() => {}}><LabReportDocument test={test} /></PrintSheet>)

    expect(printedSheet().textContent).toContain("not been released")
    expect(printedSheet().textContent).not.toContain("9.1")
  })

  it("prints released lab values and flags abnormal ones", () => {
    const test = {
      id: 7,
      status: "Released",
      name: "CBC",
      patient_name: "Asha",
      lab_result: { result_data: { Hb: "9.1", WBC: "7000" }, reference_ranges: { Hb: "12-16" }, abnormal_flags: ["Hb"] },
    }

    render(<PrintSheet open title="Lab report" onClose={() => {}}><LabReportDocument test={test} /></PrintSheet>)

    const text = printedSheet().textContent
    expect(text).toContain("9.1 (abnormal)")
    expect(text).toContain("12-16")
    expect(text).not.toContain("7000 (abnormal)")
  })

  it("states the sick-leave period on a certificate", () => {
    const certificate = {
      id: 3, kind: "Sick leave", start_date: "2026-10-20", end_date: "2026-10-22",
      patient_name: "Asha", doctor_name: "Dr. Rao", hospital_name: "City Hospital",
    }

    render(<PrintSheet open title="Certificate" onClose={() => {}}><CertificateDocument certificate={certificate} /></PrintSheet>)

    const text = printedSheet().textContent
    expect(text).toContain("advised rest 20 Oct 2026 to 22 Oct 2026")
    expect(text).toContain("CERT-3")
    expect(text).toContain("Dr. Rao")
  })
})
