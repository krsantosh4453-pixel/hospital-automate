import { useEffect, useState } from "react"

// MF-010: patient pages pick up changes (a result released, a bill paid, a
// visit completed) without a manual reload. The tick goes up every `everyMs`
// while the page is visible and whenever the patient comes back to the tab;
// pages re-read their data on each tick, quietly (no loading spinner).
export const PATIENT_REFRESH_MS = 60000

export function useRefreshTick(everyMs = PATIENT_REFRESH_MS) {
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const bump = () => {
      if (document.visibilityState === "visible") setTick((n) => n + 1)
    }
    const interval = setInterval(bump, everyMs)
    document.addEventListener("visibilitychange", bump)
    return () => {
      clearInterval(interval)
      document.removeEventListener("visibilitychange", bump)
    }
  }, [everyMs])

  return tick
}
