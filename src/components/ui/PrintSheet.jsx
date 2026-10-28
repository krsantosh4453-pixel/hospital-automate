import { useEffect } from "react"
import { createPortal } from "react-dom"
import { Printer } from "lucide-react"
import Button from "./Button.jsx"
import { Modal } from "./Modal.jsx"

export const PRINTING_CLASS = "hms-printing"

/**
 * Preview of a printable document (invoice, lab report, certificate…).
 * While open, the body carries PRINTING_CLASS so the print stylesheet in
 * index.css prints only the sheet, never the page behind it. The browser's
 * print dialog also saves the sheet as a PDF.
 */
export function PrintSheet({ open, onClose, title, children }) {
  useEffect(() => {
    if (!open) return undefined
    document.body.classList.add(PRINTING_CLASS)
    return () => document.body.classList.remove(PRINTING_CLASS)
  }, [open])

  if (!open) return null

  return (
    <>
      <Modal
        open
        onClose={onClose}
        title={title}
        description="Print it, or choose “Save as PDF” in the print dialog."
        size="xl"
        footer={
          <>
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
            <Button icon={Printer} onClick={() => window.print()}>
              Print / Save PDF
            </Button>
          </>
        }
      >
        <div className="hms-paper rounded-xl p-6">{children}</div>
      </Modal>
      {createPortal(<div className="hms-print-sheet">{children}</div>, document.body)}
    </>
  )
}

/** Letterhead, title and body shared by every printed document. */
export function PrintedDocument({ hospitalName, hospitalAddress, title, reference, date, children, signature }) {
  return (
    <article className="space-y-5 text-sm leading-relaxed text-black">
      <header className="flex items-start justify-between gap-4 border-b-2 border-black pb-3">
        <div>
          <p className="text-xl font-bold">{hospitalName || "Hospital"}</p>
          {hospitalAddress && <p className="whitespace-pre-line text-xs">{hospitalAddress}</p>}
        </div>
        <div className="text-right">
          <p className="text-lg font-bold uppercase tracking-wide">{title}</p>
          {reference && <p className="text-xs">No. {reference}</p>}
          {date && <p className="text-xs">Date: {date}</p>}
        </div>
      </header>
      {children}
      {signature && (
        <footer className="flex justify-end pt-10">
          <div className="min-w-56 border-t border-black pt-1 text-center text-xs">{signature}</div>
        </footer>
      )}
    </article>
  )
}

/** Label/value rows for a printed document; empty values are left out. */
export function PrintedFacts({ rows }) {
  return (
    <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
      {rows
        .filter(([, value]) => value !== undefined && value !== null && value !== "")
        .map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="font-semibold">{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
    </dl>
  )
}
