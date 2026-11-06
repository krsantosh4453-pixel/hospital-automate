import { useCallback, useRef, useState } from "react"

/**
 * Wrap a form submit handler so it runs once at a time (RL-04). A second
 * submit while the first is still saving is ignored; the ref, not the state,
 * stops it, because a fast double click arrives before React re-renders.
 *
 * @param {(event: Event) => Promise<void> | void} handler
 * @param {{ onError?: (error: unknown) => void }} [options] errors are passed
 *   here; without it they are re-thrown.
 * @returns {[(event: Event) => Promise<void>, boolean]} the guarded handler and whether it is running
 */
export function useSubmitGuard(handler, { onError } = {}) {
  const running = useRef(false)
  const [submitting, setSubmitting] = useState(false)

  const guarded = useCallback(async (event) => {
    event?.preventDefault?.()
    if (running.current) return
    running.current = true
    setSubmitting(true)
    try {
      await handler(event)
    } catch (error) {
      if (!onError) throw error
      onError(error)
    } finally {
      running.current = false
      setSubmitting(false)
    }
  }, [handler, onError])

  return [guarded, submitting]
}
