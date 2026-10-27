import { useEffect, useRef } from "react"
import "./AppBackground.css"

/**
 * Decorative backdrop behind every page: slow drifting colour washes, a fine
 * dot grid, and a soft glow that follows the pointer and lights up the grid
 * near it. Fixed, aria-hidden and pointer-events: none, so it never takes
 * focus or clicks. The pointer glow only runs on mouse/trackpad devices, and
 * all motion stops under prefers-reduced-motion (see AppBackground.css).
 */
export default function AppBackground() {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el || !window.matchMedia?.("(pointer: fine)").matches) return

    let frame = 0
    let x = 0
    let y = 0
    // One style write per animation frame, however fast the pointer events arrive.
    const apply = () => {
      frame = 0
      el.style.setProperty("--pointer-x", `${x}px`)
      el.style.setProperty("--pointer-y", `${y}px`)
      el.style.setProperty("--pointer-on", "1")
    }
    const onMove = (event) => {
      x = event.clientX
      y = event.clientY
      if (!frame) frame = requestAnimationFrame(apply)
    }
    const onLeave = () => el.style.setProperty("--pointer-on", "0")

    window.addEventListener("pointermove", onMove, { passive: true })
    document.documentElement.addEventListener("pointerleave", onLeave)
    window.addEventListener("blur", onLeave)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener("pointermove", onMove)
      document.documentElement.removeEventListener("pointerleave", onLeave)
      window.removeEventListener("blur", onLeave)
    }
  }, [])

  return (
    <div ref={ref} className="hms-backdrop" aria-hidden="true">
      <div className="hms-backdrop__wash hms-backdrop__wash--brand" />
      <div className="hms-backdrop__wash hms-backdrop__wash--accent" />
      <div className="hms-backdrop__wash hms-backdrop__wash--mint" />
      <div className="hms-backdrop__grid" />
      <div className="hms-backdrop__grid hms-backdrop__grid--lit" />
      <div className="hms-backdrop__glow" />
      <div className="hms-backdrop__grain" />
    </div>
  )
}
