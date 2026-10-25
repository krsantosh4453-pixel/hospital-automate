import { useCallback, useRef, useState } from "react"
import { ConfirmDialog } from "./Modal.jsx"

/**
 * Promise-based replacement for window.confirm that renders the accessible
 * ConfirmDialog.
 *
 *   const [confirm, confirmDialog] = useConfirm()
 *   if (!(await confirm({ title, message, confirmLabel, destructive }))) return
 *   ...
 *   return <>{page}{confirmDialog}</>
 *
 * A plain string is accepted too: confirm("Delete this record?").
 */
export function useConfirm() {
  const [state, setState] = useState(null)
  const resolver = useRef(null)

  const confirm = useCallback((options) => {
    const opts = typeof options === "string" ? { message: options } : options || {}
    return new Promise((resolve) => {
      resolver.current = resolve
      setState(opts)
    })
  }, [])

  const close = (answer) => {
    resolver.current?.(answer)
    resolver.current = null
    setState(null)
  }

  const destructive =
    state?.destructive ?? /delete|remove|discharge|cancel|revoke|reject|deactivate/i.test(`${state?.title || ""} ${state?.message || ""}`)

  const dialog = (
    <ConfirmDialog
      open={Boolean(state)}
      title={state?.title || "Please confirm"}
      message={state?.message}
      confirmLabel={state?.confirmLabel || "Confirm"}
      cancelLabel={state?.cancelLabel || "Cancel"}
      destructive={destructive}
      onCancel={() => close(false)}
      onConfirm={() => close(true)}
    />
  )

  return [confirm, dialog]
}

export default useConfirm
