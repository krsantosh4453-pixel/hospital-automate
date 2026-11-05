import { useEffect, useState } from "react"
import { Button, EmptyState, Modal } from "../ui"
import { Ticket } from "lucide-react"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// The desk picks which booked appointment checks in, seeing who it is for,
// when and with which doctor, instead of the earliest one being issued blind.
// The server still gives one token per appointment.

const shortTime = (value) => (value ? String(value).slice(0, 5) : "—")

export default function IssueTokenDialog({ open, appointments, busy, onClose, onIssue }) {
  const { t } = useLanguage()
  const [chosen, setChosen] = useState("")
  // The page rebuilds the list on every render; only a change in which
  // appointments it holds resets the choice to the earliest one.
  const ids = appointments.map((appointment) => appointment.apiId).join(",")
  const firstId = appointments[0] ? String(appointments[0].apiId) : ""

  useEffect(() => {
    if (open) setChosen(firstId)
  }, [open, ids, firstId])

  const selected = appointments.find((appointment) => String(appointment.apiId) === chosen)

  return (
    <Modal open={open} onClose={onClose} size="lg" title={t("Check in a booked appointment")}
      description="Choose the patient at the desk. Each appointment gets one token."
      footer={<>
        <Button variant="secondary" onClick={onClose}>{t("Cancel")}</Button>
        <Button icon={Ticket} loading={busy} disabled={!selected} onClick={() => onIssue(selected)}>
          {selected ? t("Issue token for {patient}", { patient: selected.patient }) : t("Issue token")}
        </Button>
      </>}>
      {appointments.length === 0 ? (
        <EmptyState compact icon={Ticket} title={t("No booked appointment is waiting for a token")} />
      ) : (
        <fieldset>
          <legend className="sr-only">{t("Booked appointments without a token")}</legend>
          <ul className="divide-y divide-line rounded-xl border border-line">
            {appointments.map((appointment) => {
              const id = `issue-appointment-${appointment.apiId}`
              return (
                <li key={appointment.apiId}>
                  <label htmlFor={id} className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-ink-50">
                    <input id={id} type="radio" name="issue-appointment" className="mt-1"
                      checked={chosen === String(appointment.apiId)}
                      onChange={() => setChosen(String(appointment.apiId))} />
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium text-ink-900">{appointment.patient || t("Patient")}</span>
                      <span className="block text-[13px] text-ink-600 tabular-nums">
                        {[shortTime(appointment.time), appointment.doctor, appointment.contact].filter(Boolean).join(" · ")}
                      </span>
                      {appointment.reason && <span className="block text-xs text-ink-500">{appointment.reason}</span>}
                    </span>
                    <span className="text-xs text-ink-500 tabular-nums">A{String(appointment.apiId).padStart(3, "0")}</span>
                  </label>
                </li>
              )
            })}
          </ul>
        </fieldset>
      )}
    </Modal>
  )
}
