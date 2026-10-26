import { useState } from "react"
import { Link } from "react-router-dom"
import {
  BedDouble,
  CalendarCheck,
  CalendarDays,
  CalendarPlus,
  ChartColumn,
  Droplet,
  FlaskConical,
  Hospital,
  ListOrdered,
  Lock,
  LogIn,
  Package,
  Pill,
  ReceiptIndianRupee,
  ShieldCheck,
  Siren,
  Stethoscope,
  UserRound,
  UsersRound,
} from "lucide-react"
import { Card, CardHeader, Modal, StatTile } from "../components/ui"
import { eligibleRolesFor } from "../assets/context/RoleContext.jsx"

/*
 * Home page for visitors who have not signed in. It mirrors the staff home
 * layout so the hospital's services are visible, but it shows no figures
 * and offers no create/add actions: the only action is booking an
 * appointment. Every department tile explains who may work there.
 */

const GLANCE = [
  { icon: UsersRound, label: "Patients registered today" },
  { icon: CalendarDays, label: "Appointments today", tone: "accent" },
  { icon: ListOrdered, label: "Waiting in queue", tone: "warning" },
  { icon: BedDouble, label: "Beds available", tone: "success" },
]

export const GUEST_DEPARTMENTS = [
  { module: "Patients", icon: UsersRound, title: "Patients", text: "Registration and patient records." },
  { module: "Appointments", icon: CalendarDays, title: "Appointments", text: "Bookings and the daily schedule." },
  { module: "Queue", icon: ListOrdered, title: "OPD queue", text: "Tokens and consultation flow." },
  { module: "Doctors", icon: Stethoscope, title: "Consultation", text: "Doctors' clinical work." },
  { module: "Nurses", icon: UserRound, title: "Nursing", text: "Vitals, nursing notes and medication rounds." },
  { module: "IPD", icon: BedDouble, title: "Wards and beds", text: "Admissions, beds and discharge." },
  { module: "Emergency", icon: Siren, title: "Emergency", text: "Triage and emergency care." },
  { module: "Laboratory", icon: FlaskConical, title: "Laboratory", text: "Samples, results and reports." },
  { module: "Pharmacy", icon: Pill, title: "Pharmacy", text: "Dispensing and medicine stock." },
  { module: "BloodBank", icon: Droplet, title: "Blood bank", text: "Blood stock and requests." },
  { module: "Billing", icon: ReceiptIndianRupee, title: "Billing", text: "Invoices and payments." },
  { module: "Inventory", icon: Package, title: "Inventory", text: "Store, suppliers and purchase orders." },
  { module: "Reports", icon: ChartColumn, title: "Reports", text: "Hospital statistics." },
]

const STEPS = [
  { icon: Hospital, title: "Select hospital", text: "Pick where you want to be seen." },
  { icon: Stethoscope, title: "Select doctor", text: "Choose a department and doctor." },
  { icon: CalendarCheck, title: "Choose a slot", text: "Pick a date and an available time." },
  { icon: ShieldCheck, title: "Confirm", text: "Sign in to confirm the booking." },
]

const primaryLink =
  "inline-flex h-11 items-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-brand-800 hover:bg-brand-50"
const outlineLink =
  "inline-flex h-11 items-center gap-2 rounded-lg border border-white/30 px-5 text-sm font-semibold text-white hover:bg-white/10"

function GuestHome() {
  const [locked, setLocked] = useState(null)
  const roles = locked ? eligibleRolesFor(locked.module) : []

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-8 px-4 py-6 sm:px-6 lg:px-8">
      <section className="overflow-hidden rounded-2xl bg-brand-900 px-6 py-10 text-white sm:px-10 sm:py-14">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand-200">Hospital services</p>
        <h1 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          Your care, organised in one place
        </h1>
        <p className="mt-4 max-w-xl text-[15px] leading-7 text-brand-100/90">
          Book an appointment, then sign in to follow your visits, prescriptions, reports and bills.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link to="/patient-login?next=book" className={primaryLink}>
            <CalendarPlus size={17} aria-hidden="true" /> Book appointment
          </Link>
          <Link to="/patient-login" className={outlineLink}>
            <LogIn size={17} aria-hidden="true" /> Patient sign in
          </Link>
          <Link to="/staff-login" className={outlineLink}>
            <LogIn size={17} aria-hidden="true" /> Staff sign in
          </Link>
        </div>
      </section>

      <section aria-label="Today at a glance" className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {GLANCE.map((tile) => (
          <StatTile key={tile.label} icon={tile.icon} tone={tile.tone} label={tile.label} value="—" hint="Sign in to see" />
        ))}
      </section>

      <section aria-labelledby="guest-departments">
        <h2 id="guest-departments" className="mb-1 text-base font-semibold text-ink-900">
          Departments
        </h2>
        <p className="mb-4 text-sm text-ink-500">Work in each department opens after the right staff member signs in.</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {GUEST_DEPARTMENTS.map((dept) => (
            <button
              key={dept.module}
              type="button"
              onClick={() => setLocked(dept)}
              className="group flex items-start gap-3 rounded-2xl border border-line bg-white p-5 text-left transition-colors hover:border-brand-300"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                <dept.icon size={20} aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5 font-semibold text-ink-900 group-hover:text-brand-800">
                  {dept.title} <Lock size={13} className="text-ink-400" aria-label="Sign-in required" />
                </span>
                <span className="mt-1 block text-sm text-ink-500">{dept.text}</span>
              </span>
            </button>
          ))}
        </div>
      </section>

      <Card>
        <CardHeader title="How booking works" description="You can see the steps before signing in." />
        <ol className="grid grid-cols-1 gap-6 px-5 py-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ icon: Icon, title, text }, i) => (
            <li key={title} className="flex gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                {i + 1}
              </span>
              <div>
                <p className="flex items-center gap-1.5 font-medium text-ink-900">
                  <Icon size={15} className="text-ink-400" aria-hidden="true" /> {title}
                </p>
                <p className="mt-0.5 text-sm text-ink-500">{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </Card>

      <Modal
        open={Boolean(locked)}
        onClose={() => setLocked(null)}
        title="You are not eligible for this work"
        description={locked?.title}
        size="sm"
        footer={
          <>
            <button
              type="button"
              onClick={() => setLocked(null)}
              className="inline-flex h-10 items-center rounded-lg border border-line-strong bg-white px-4 text-sm font-medium text-ink-800 hover:bg-ink-50"
            >
              Close
            </button>
            <Link
              to="/staff-login"
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700"
            >
              <LogIn size={16} aria-hidden="true" /> Staff sign in
            </Link>
          </>
        }
      >
        <p className="text-sm leading-6 text-ink-700">
          {locked?.title} work is only for <strong>{roles.join(", ")}</strong>. Please sign in with an account that has
          one of these roles.
        </p>
      </Modal>
    </div>
  )
}

export default GuestHome
