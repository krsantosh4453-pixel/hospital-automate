import { useCallback } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { Modal } from "../ui"

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

/** Wraps a sign-in page in the dialog; closing returns to the page underneath. */
export function SignInDialog({ title, children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const background = location.state?.backgroundLocation
  const close = () => navigate(background || "/", { replace: true })

  return (
    <Modal open onClose={close} title={title} size="md">
      {children}
    </Modal>
  )
}
