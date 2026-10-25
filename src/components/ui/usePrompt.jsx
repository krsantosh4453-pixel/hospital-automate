import { useCallback, useRef, useState } from "react"
import { Modal } from "./Modal.jsx"
import Button from "./Button.jsx"

/**
 * Promise-based replacement for window.prompt with a labelled, multi-line
 * field. Resolves to the entered text, or null when cancelled (same contract
 * as window.prompt).
 *
 *   const [promptText, promptDialog] = usePrompt()
 *   const value = await promptText("Discharge diagnosis:")
 */
export function usePrompt() {
  const [state, setState] = useState(null)
  const [value, setValue] = useState("")
  const resolver = useRef(null)

  const promptText = useCallback((options, defaultValue = "") => {
    const opts = typeof options === "string" ? { label: options } : options || {}
    return new Promise((resolve) => {
      resolver.current = resolve
      setValue(opts.defaultValue ?? defaultValue ?? "")
      setState(opts)
    })
  }, [])

  const close = (answer) => {
    resolver.current?.(answer)
    resolver.current = null
    setState(null)
  }

  const label = String(state?.label || "").replace(/:\s*$/, "")

  const dialog = (
    <Modal
      open={Boolean(state)}
      onClose={() => close(null)}
      title={state?.title || label || "Enter a value"}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={() => close(null)}>Cancel</Button>
          <Button type="submit" form="hms-prompt-form">{state?.confirmLabel || "Save"}</Button>
        </>
      }
    >
      <form
        id="hms-prompt-form"
        onSubmit={(e) => {
          e.preventDefault()
          close(value)
        }}
      >
        <label htmlFor="hms-prompt-input" className="hms-label">{label}</label>
        <textarea
          id="hms-prompt-input"
          autoFocus
          rows={state?.rows || 3}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault()
              close(value)
            }
          }}
          className="hms-input w-full min-h-[5rem]"
        />
        {state?.hint && <p className="mt-1.5 text-xs text-ink-500">{state.hint}</p>}
      </form>
    </Modal>
  )

  return [promptText, dialog]
}

export default usePrompt
