import { useEffect, useId, useRef } from "react"
import { createPortal } from "react-dom"
import { TriangleAlert, X } from "lucide-react"
import Button from "./Button.jsx"

const WIDTHS = { sm: "max-w-md", md: "max-w-lg", lg: "max-w-2xl", xl: "max-w-4xl" }

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Accessible dialog: focus moves in and is trapped, Escape and the backdrop
 * close it, and focus returns to the opener on close.
 */
export function Modal({ open, onClose, title, description, size = "md", footer, children, dismissible = true }) {
  const titleId = useId()
  const descId = useId()
  const panelRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const opener = document.activeElement
    const panel = panelRef.current
    const first = panel?.querySelector(FOCUSABLE)
    ;(first || panel)?.focus()

    const onKey = (e) => {
      if (e.key === "Escape" && dismissible) {
        e.stopPropagation()
        onClose?.()
      }
      if (e.key === "Tab" && panel) {
        const items = [...panel.querySelectorAll(FOCUSABLE)]
        if (items.length === 0) return
        const firstEl = items[0]
        const lastEl = items[items.length - 1]
        if (e.shiftKey && document.activeElement === firstEl) {
          e.preventDefault()
          lastEl.focus()
        } else if (!e.shiftKey && document.activeElement === lastEl) {
          e.preventDefault()
          firstEl.focus()
        }
      }
    }
    document.addEventListener("keydown", onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", onKey)
      document.body.style.overflow = prevOverflow
      if (opener && typeof opener.focus === "function") opener.focus()
    }
  }, [open, onClose, dismissible])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-[60] flex items-end justify-center p-0 sm:items-center sm:p-4">
      <div
        className="absolute inset-0 bg-ink-950/45 animate-fade-in"
        onClick={dismissible ? onClose : undefined}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        tabIndex={-1}
        className={`relative flex max-h-[92vh] w-full ${WIDTHS[size] || WIDTHS.md} flex-col rounded-t-2xl bg-white shadow-2xl outline-none animate-rise-in sm:rounded-2xl`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-base font-semibold text-ink-900">
              {title}
            </h2>
            {description && (
              <p id={descId} className="mt-0.5 text-[13px] text-ink-500">
                {description}
              </p>
            )}
          </div>
          {dismissible && (
            <button
              type="button"
              onClick={onClose}
              className="-mr-1.5 rounded-lg p-1.5 text-ink-500 hover:bg-ink-100 hover:text-ink-800"
              aria-label="Close dialog"
            >
              <X size={18} aria-hidden="true" />
            </button>
          )}
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-line bg-ink-50/60 px-5 py-3 sm:rounded-b-2xl">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}

/** Confirmation for consequential actions (delete, cancel, discharge, revoke…). */
export function ConfirmDialog({
  open,
  onCancel,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  loading = false,
}) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={destructive ? "danger" : "primary"} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="flex gap-3">
        {destructive && (
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-50 text-red-600">
            <TriangleAlert size={18} aria-hidden="true" />
          </span>
        )}
        <div className="text-sm leading-6 text-ink-700">{message}</div>
      </div>
    </Modal>
  )
}

export default Modal
