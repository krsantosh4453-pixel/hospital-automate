import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { AppointmentProvider } from "./assets/context/AppointmentContext.jsx"

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AppointmentProvider>
      <App />
    </AppointmentProvider>
  </StrictMode>,
)
