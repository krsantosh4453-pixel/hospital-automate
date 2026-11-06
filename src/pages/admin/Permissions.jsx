import { useState } from "react"
import { Check, Minus } from "lucide-react"
import { useRole, ALL_MODULES } from "../../assets/context/RoleContext.jsx"
import { usePatient } from "../../assets/context/PatientContext.jsx"
import RoleRestrictionSelect from "../../components/admin/RoleRestrictions.jsx"
import { RESTRICTABLE_MODULES } from "../../config/restrictableModules.js"
import { Alert, Card, PageHeader, TableWrap, Tabs } from "../../components/ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

const ACTIONS = ["View", "Add", "Edit", "Delete"]

/**
 * What each built-in role can see and do. Roles are part of the application
 * and the server checks every request against them; an administrator can
 * only narrow a role at their hospital (view only / no access per module),
 * never widen it. Staff get roles per hospital under Users.
 */
function Permissions() {
  const { t } = useLanguage()
  const { roles, activeRoleName, restrictions = [], reloadRestrictions } = useRole()
  const { selectedHospital } = usePatient() || {}
  const canRestrict = activeRoleName === "Admin" && Boolean(selectedHospital)
  const staffRoles = roles.filter((role) => role.name !== "Patient")
  const [selectedName, setSelectedName] = useState(activeRoleName && staffRoles.some((r) => r.name === activeRoleName) ? activeRoleName : staffRoles[0]?.name)
  const selectedRole = staffRoles.find((role) => role.name === selectedName) || staffRoles[0]
  const isAdmin = selectedRole?.name === "Admin"

  const builtIn = (module, action) => isAdmin || (selectedRole?.permissions?.[module] || []).includes(action)
  const ruleFor = (module) => restrictions.find((r) => r.role === selectedRole?.name && r.module === module)
  const allowed = (module, action) => {
    const rule = ruleFor(module)
    if (rule?.access === "none" || (rule?.access === "view" && action !== "View")) return false
    return builtIn(module, action)
  }
  const modules = ALL_MODULES.filter((module) => ACTIONS.some((action) => builtIn(module, action)))
  const editable = (module) => canRestrict && !isAdmin && RESTRICTABLE_MODULES.includes(module)

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("Permissions")}
        description="What each role can see and do in this hospital system."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Administration", to: "/admin" }, { label: "Permissions" }]}
      />

      <Alert tone="info" title={t("Roles are built in")}>
        {canRestrict
          ? t("These rules are part of the application, and the server checks every request against them. At this hospital you can make a module view only or turn it off for a role; you cannot give a role more than it has. To change what one person can do, give them a different role under Users.")
          : t("These rules are part of the application, and the server checks every request against them. They cannot be edited here. To change what a person can do, give them a different role for that hospital under Users.")}
      </Alert>

      <Card className="overflow-hidden">
        <div className="px-4 pt-3">
          <Tabs
            label="Role"
            value={selectedRole?.name}
            onChange={setSelectedName}
            tabs={staffRoles.map((role) => ({ id: role.name, label: role.name }))}
          />
          {selectedRole?.description && <p className="py-3 text-[13px] text-ink-500">{t(selectedRole.description)}</p>}
        </div>
        <TableWrap>
          <table className="hms-table">
            <caption className="sr-only">{t("Permissions of the")}{" "}{selectedRole?.name}{" "}{t("role")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("Module")}</th>
                {ACTIONS.map((action) => <th key={action} scope="col" className="text-center">{action}</th>)}
                {canRestrict && !isAdmin && <th scope="col">{t("At this hospital")}</th>}
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
                  {canRestrict && !isAdmin && (
                    <td>
                      {editable(module) ? (
                        <RoleRestrictionSelect hospitalId={selectedHospital.id} roleName={selectedRole.name} module={module}
                          rule={ruleFor(module)} onSaved={reloadRestrictions} />
                      ) : <span className="text-xs text-ink-400">{t("Built-in")}</span>}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
        <p className="border-t border-line px-4 py-3 text-xs text-ink-500">
          {isAdmin ? t("Admin has full access to every module of their hospital.") : t("Modules not listed are not available to {name}.", { name: selectedRole?.name })}
        </p>
      </Card>
    </div>
  )
}

export default Permissions
