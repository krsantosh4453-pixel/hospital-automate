import { useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import ResourcePanel from "../components/services/ResourcePanel.jsx"
import { SERVICE_TABS } from "../components/services/serviceConfigs.js"
import { Card, EmptyState, PageHeader, Tabs } from "../components/ui"
import { useLanguage } from "../assets/context/LanguageContext.jsx"

// Support services (J5, J6, I6): OT, ambulance, mortuary, CSSD, laundry,
// staff leave, patient feedback and templates, each tab for the roles that use it.
export default function HospitalServices() {
  const { t } = useLanguage()
  const { selectedHospital } = usePatient()
  const { activeRoleName } = useRole()
  const tabs = SERVICE_TABS.filter((tab) => !tab.roles || tab.roles.includes(activeRoleName))
  const [tabId, setTabId] = useState(tabs[0]?.id)
  const tab = tabs.find((item) => item.id === tabId) || tabs[0]

  if (!selectedHospital) {
    return <Card><EmptyState title={t("Select a hospital")} /></Card>
  }
  return (
    <div>
      <PageHeader title={t("Hospital services")} description={t("Theatre, ambulance, mortuary, CSSD, laundry, leave, feedback and templates at {hospital}.", { hospital: selectedHospital.name })} />
      <Tabs label="Hospital services" value={tab?.id} onChange={setTabId} tabs={tabs.map(({ id, label }) => ({ id, label }))} />
      {tab?.panels.map((config) => (
        <Card key={config.resource} className="mb-6 overflow-hidden">
          <ResourcePanel hospitalId={selectedHospital.id} config={config} role={activeRoleName} />
        </Card>
      ))}
    </div>
  )
}
