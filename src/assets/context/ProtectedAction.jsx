import { useAuth } from "./AuthContext.jsx"
import { useOpenSignIn } from "../../components/auth/SignInDialog.jsx"

function ProtectedAction({ children, onAction }) {
  const { isLoggedIn } = useAuth()
  const openSignIn = useOpenSignIn()

  const handleAction = () => {
    if (isLoggedIn) {
      // Already logged in
      if (onAction) {
        onAction()
      }
      return
    }

    // Not logged in
    openSignIn("/patient-login")
  }

  return (
    <div onClick={handleAction}>
      {children}
    </div>
  )
}

export default ProtectedAction