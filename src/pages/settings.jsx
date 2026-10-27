import { Link } from "react-router-dom"
import { ExternalLink, Hospital, KeyRound, Languages, PanelLeft, ShieldCheck } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { useSidebar } from "../assets/context/SidebarContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import { Card, CardHeader, DescriptionList, EmptyState, PageHeader, SegmentedControl } from "../components/ui"

/**
 * Settings shows only things that really take effect:
 *  - the selected hospital's details (edited by admins in Admin → Hospitals),
 *  - interface preferences stored in this browser.
 * Earlier versions showed module toggles and a "saved" message without
 * saving anything; those were removed rather than kept as a pretend form.
 */
function Settings() {
  const { selectedHospital } = usePatient()
  const { language, setLanguage } = useLanguage()
  const { isSidebarOpen, openSidebar, closeSidebar } = useSidebar()
  const { canView } = useRole()

  const linkCls = "inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:underline"

  return (
    <div className="space-y-5">
      <PageHeader
        title="Settings"
        description="Hospital details and your interface preferences."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Settings" }]}
      />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader
            icon={Hospital}
            title="Hospital details"
            description="From the hospital record. Admins change these in Admin → Hospitals."
            actions={
              canView("Hospitals") && (
                <Link to="/admin/hospitals" className={linkCls}>
                  Edit <ExternalLink size={14} aria-hidden="true" />
                </Link>
              )
            }
          />
          {selectedHospital ? (
            <div className="px-5 py-4">
              <DescriptionList
                items={[
                  { label: "Name", value: selectedHospital.name },
                  { label: "Phone", value: selectedHospital.phone },
                  { label: "Email", value: selectedHospital.email },
                  { label: "City", value: [selectedHospital.city, selectedHospital.state].filter(Boolean).join(", ") },
                  { label: "Address", value: selectedHospital.address },
                ]}
              />
            </div>
          ) : (
            <EmptyState compact icon={Hospital} title="No hospital selected" description="Choose a hospital in the header." />
          )}
        </Card>

        <Card>
          <CardHeader title="Interface" description="Saved in this browser only." />
          <div className="divide-y divide-line">
            <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
              <div className="flex items-start gap-3">
                <Languages size={18} className="mt-0.5 text-ink-400" aria-hidden="true" />
                <div>
                  <p className="text-sm font-medium text-ink-900">Language</p>
                  <p className="text-[13px] text-ink-500">Navigation and labels. Clinical text is shown exactly as entered.</p>
                </div>
              </div>
              <SegmentedControl
                label="Interface language"
                value={language}
                onChange={setLanguage}
                options={[
                  { value: "en", label: "English" },
                  { value: "hi", label: "हिंदी" },
                ]}
              />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
              <div className="flex items-start gap-3">
                <PanelLeft size={18} className="mt-0.5 text-ink-400" aria-hidden="true" />
                <div>
                  <p className="text-sm font-medium text-ink-900">Sidebar on large screens</p>
                  <p className="text-[13px] text-ink-500">A compact icon rail leaves more room for tables.</p>
                </div>
              </div>
              <SegmentedControl
                label="Sidebar"
                value={isSidebarOpen ? "full" : "rail"}
                onChange={(v) => (v === "full" ? openSidebar() : closeSidebar())}
                options={[
                  { value: "full", label: "Full" },
                  { value: "rail", label: "Icons only" },
                ]}
              />
            </div>
          </div>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader icon={ShieldCheck} title="Access and security" />
          <ul className="divide-y divide-line text-sm">
            <li className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
              <span className="text-ink-700">Which modules each role can open is set by roles and permissions.</span>
              {canView("Permissions") ? (
                <Link to="/admin/permissions" className={linkCls}>Roles &amp; permissions <ExternalLink size={14} aria-hidden="true" /></Link>
              ) : (
                <span className="text-[13px] text-ink-500">Ask a hospital administrator.</span>
              )}
            </li>
            <li className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
              <span className="flex items-center gap-2 text-ink-700">
                <KeyRound size={16} className="text-ink-400" aria-hidden="true" />
                To change your password, sign out and use “Forgot password” on the sign-in page (a one-time code is sent to your registered mobile).
              </span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  )
}

export default Settings
