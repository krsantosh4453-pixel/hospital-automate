import { describe, expect, it } from "vitest"
import { DEFAULT_ROLES, backendRoleCanView } from "../assets/context/RoleContext.jsx"
import { roleHomeFor } from "../config/roleHomes.js"

// The menu of each staff role: only the modules of its own work. The server
// grants the same reads (backend/security_tests/test_role_access_matrix.py).
const EXPECTED_MENUS = {
  Doctor: "Dashboard Patients Appointments Queue Doctors Prescriptions Laboratory Reports IPD Emergency BloodBank AIScribe",
  Nurse: "Dashboard Patients Appointments Queue Nurses Prescriptions Laboratory Reports IPD Emergency BloodBank",
  Compounder: "Dashboard Compounders Prescriptions Pharmacy Inventory Reports",
  Pharmacist: "Dashboard Pharmacy Compounders Prescriptions Inventory Reports",
  Receptionist: "Dashboard Patients Appointments Queue Billing Doctors Reports",
  "Lab Staff": "Dashboard Laboratory Reports",
  "Blood Bank Staff": "Dashboard BloodBank Reports",
  "Billing Staff": "Dashboard Billing Reports",
  "Inventory Staff": "Dashboard Inventory Reports",
  "Hospital Manager":
    "Dashboard Patients Appointments Queue Doctors Nurses Compounders Pharmacy Laboratory Billing Inventory Reports Emergency BloodBank IPD Users Hospitals Departments",
}

const MODULES = Object.keys(DEFAULT_ROLES.find((r) => r.name === "Admin").permissions)

describe("role menus", () => {
  for (const [role, menu] of Object.entries(EXPECTED_MENUS)) {
    it(`${role} sees only its own work`, () => {
      const visible = MODULES.filter((module) => backendRoleCanView(role, module))
      expect(visible.sort()).toEqual(menu.split(" ").sort())
    })
  }

  it("Hospital Manager only views clinical modules", () => {
    const manager = DEFAULT_ROLES.find((r) => r.name === "Hospital Manager").permissions
    for (const module of ["Patients", "Laboratory", "IPD", "Emergency"]) {
      expect(manager[module], module).toEqual(["View"])
    }
  })

  it("Pharmacist has its own home", () => {
    expect(roleHomeFor("Pharmacist").title).toBe("Pharmacy today")
    expect(roleHomeFor("Pharmacist")).not.toBe(roleHomeFor("Compounder"))
  })
})
