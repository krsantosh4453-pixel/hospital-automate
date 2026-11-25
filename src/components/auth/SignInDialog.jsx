import { Suspense, useCallback, useEffect, useRef } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { Modal } from "../ui"
import { LoadingSpinner } from "../LoadingSpinner.jsx"

/*
 * Sign-in opens as a dialog over the page the visitor is on. Links pass the
 * current location as `backgroundLocation`; App keeps rendering that page
 * underneath and shows the sign-in route in a Modal. Opening /staff-login or
 * /patient-login directly (a bookmark, a reload) still shows the full page.
 */

/** The page to keep showing behind a sign-in dialog opened from `location`. */
function backgroundFor(location) {
  return location.state?.backgroundLocation || location
}

/** A Link to a sign-in route that opens it as a dialog over the current page. */
export function SignInLink({ to, state, ...props }) {
  const location = useLocation()
  return <Link to={to} state={{ ...state, backgroundLocation: backgroundFor(location) }} {...props} />
}

/** navigate() counterpart of SignInLink, for buttons and handlers. */
export function useOpenSignIn() {
  const location = useLocation()
  const navigate = useNavigate()
  return useCallback(
    (to) => navigate(to, { state: { backgroundLocation: backgroundFor(location) } }),
    [location, navigate],
  )
}

/** True while the current route is drawn inside the sign-in dialog. */
export function useInSignInDialog() {
  return Boolean(useLocation().state?.backgroundLocation)
}

/*
 * Links between the auth pages (Sign in <-> Create Account). Inside the dialog
 * they keep the same page underneath, so the dialog only swaps its form; on a
 * full page they stay ordinary page links.
 */
export function AuthLink({ to, ...props }) {
  return useInSignInDialog() ? <SignInLink to={to} {...props} /> : <Link to={to} {...props} />
}

/** navigate() counterpart of AuthLink. */
export function useAuthNavigate() {
  const inDialog = useInSignInDialog()
  const openSignIn = useOpenSignIn()
  const navigate = useNavigate()
  return useCallback((to) => (inDialog ? openSignIn(to) : navigate(to)), [inDialog, openSignIn, navigate])
}

const FIRST_FIELD = 'input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled])'

/*
 * Switching between Sign in and Create Account keeps the same Modal (no
 * re-mount, no flash), so focus is moved into the new form here: the link
 * that had focus has just been removed. Keyed by route and placed inside the
 * Suspense boundary, its effect runs once the new form has rendered.
 */
function FocusFirstField({ containerRef }) {
  useEffect(() => {
    const body = containerRef.current
    if (body && !body.contains(document.activeElement)) body.querySelector(FIRST_FIELD)?.focus()
  }, [containerRef])
  return null
}

/** Wraps a sign-in page in the dialog; closing returns to the page underneath. */
export function SignInDialog({ title, children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const background = location.state?.backgroundLocation
  const close = () => navigate(background || "/", { replace: true })
  const bodyRef = useRef(null)

  return (
    <Modal open onClose={close} title={title} size="md">
      {/* Register is lazy-loaded: wait inside the dialog, not by blanking the page behind it. */}
      <Suspense fallback={<div className="flex justify-center py-10"><LoadingSpinner /></div>}>
        <div ref={bodyRef}>
          {children}
          <FocusFirstField key={location.pathname} containerRef={bodyRef} />
        </div>
      </Suspense>
    </Modal>
  )
}
