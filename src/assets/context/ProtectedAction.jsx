import { useAuth } from "./AuthContext.jsx"
import { useNavigate } from "react-router-dom"

function ProtectedAction({ children, onAction }) {
  const { isLoggedIn } = useAuth()
  const navigate = useNavigate()

  const handleAction = () => {
    if (isLoggedIn) {
      // Already logged in
      if (onAction) {
        onAction()
      }
      return
    }

    // Not logged in
    navigate("/patient-login")
  }

  return (
    <div onClick={handleAction}>
      {children}
    </div>
  )
}

export default ProtectedAction