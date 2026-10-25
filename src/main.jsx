import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter'
import './index.css'
import App from './App.jsx'
import { AppointmentProvider } from "./assets/context/AppointmentContext.jsx"
import { ToastProvider } from "./components/Toast.jsx"

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ToastProvider>
      <AppointmentProvider>
        <App />
      </AppointmentProvider>
    </ToastProvider>
  </StrictMode>,
)
