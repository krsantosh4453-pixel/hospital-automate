import { useState } from "react"
import { Check, Minus } from "lucide-react"
import { useRole, ALL_MODULES } from "../../assets/context/RoleContext.jsx"
import { Alert, Card, PageHeader, TableWrap, Tabs } from "../../components/ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

const ACTIONS = ["View", "Add", "Edit", "Delete"]

/**
 * What each built-in role can see and do. Read-only: roles are part of the
 * application and the server checks every request against them. Staff get
 * roles per hospital under Users.
 */
function Permissions() {
  const { t } = useLanguage()
  const { roles, activeRoleName } = useRole()
  const staffRoles = roles.filter((role) => role.name !== "Patient")
  const [selectedName, setSelectedName] = useState(activeRoleName && staffRoles.some((r) => r.name === activeRoleName) ? activeRoleName : staffRoles[0]?.name)
  const selectedRole = staffRoles.find((role) => role.name === selectedName) || staffRoles[0]
  const isAdmin = selectedRole?.name === "Admin"

  const allowed = (module, action) => isAdmin || (selectedRole?.permissions?.[module] || []).includes(action)
  const modules = ALL_MODULES.filter((module) => ACTIONS.some((action) => allowed(module, action)))

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("Permissions")}
        description="What each role can see and do in this hospital system."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Administration", to: "/admin" }, { label: "Permissions" }]}
      />

      <Alert tone="info" title={t("Roles are built in")}>
        {t("These rules are part of the application, and the server checks every request against them. They cannot be edited here. To change what a person can do, give them a different role for that hospital under Users.")}
      </Alert>

      <Card className="overflow-hidden">
        <div className="px-4 pt-3">
          <Tabs
            label="Role"
            value={selectedRole?.name}
            onChange={setSelectedName}
            tabs={staffRoles.map((role) => ({ id: role.name, label: role.name }))}
          />
          {selectedRole?.description && <p className="py-3 text-[13px] text-ink-500">{selectedRole.description}</p>}
        </div>
        <TableWrap>
          <table className="hms-table">
            <caption className="sr-only">{t("Permissions of the")}{" "}{selectedRole?.name}{" "}{t("role")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("Module")}</th>
                {ACTIONS.map((action) => <th key={action} scope="col" className="text-center">{action}</th>)}
              </tr>
            </thead>
            <tbody>
              {modules.map((module) => (
                <tr key={module}>
                  <td className="font-medium text-ink-900">{module}</td>
                  {ACTIONS.map((action) => (
                    <td key={action} className="text-center">
                      {allowed(module, action) ? (
                        <Check size={16} className="inline text-emerald-600" aria-label={t("Allowed")} />
                      ) : (
                        <Minus size={16} className="inline text-ink-300" aria-label={t("Not allowed")} />
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
        <p className="border-t border-line px-4 py-3 text-xs text-ink-500">
          {isAdmin ? "Admin has full access to every module of their hospital." : t("Modules not listed are not available to {name}.", { name: selectedRole?.name })}
        </p>
      </Card>
    </div>
  )
}

export default Permissions
