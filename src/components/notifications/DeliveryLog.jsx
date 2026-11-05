import { useEffect, useState } from "react"
import { Send } from "lucide-react"
import api from "../../services/api.js"
import { Card, CardHeader, EmptyState, StatusBadge, TableWrap } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// K7: what happened to each message the hospital tried to send. A "skipped"
// row is honest about why (no consent, provider not set up), never shown as sent.
const list = (data) => (Array.isArray(data) ? data : data?.results || [])

export default function DeliveryLog({ hospitalId }) {
  const { t } = useLanguage()
  const [rows, setRows] = useState([])
  const [state, setState] = useState("loading")

  useEffect(() => {
    let cancelled = false
    api.notifications.deliveries.list(hospitalId)
      .then((data) => !cancelled && (setRows(list(data)), setState("loaded")))
      .catch((err) => !cancelled && setState(err.status === 403 ? "forbidden" : "failed"))
    return () => {
      cancelled = true
    }
  }, [hospitalId])

  return (
    <Card className="mt-6">
      <CardHeader icon={Send} title="Message delivery" description="Each attempt to send a notification, with its result." />
      {state === "forbidden" ? <EmptyState compact title="Not available for your role" />
        : state === "failed" ? <EmptyState compact title="Could not load deliveries" />
          : rows.length === 0 ? <EmptyState compact title="No messages sent yet" /> : (
            <TableWrap maxHeight="22rem">
              <table className="hms-table">
                <thead>
                  <tr>
                    <th scope="col">{t("When")}</th>
                    <th scope="col">{t("Patient")}</th>
                    <th scope="col">{t("Channel")}</th>
                    <th scope="col">{t("Status")}</th>
                    <th scope="col">{t("Reason")}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 30).map((row) => (
                    <tr key={row.id}>
                      <td className="whitespace-nowrap text-ink-600">{new Date(row.attempted_at).toLocaleString("en-IN")}</td>
                      <td>{row.patient_name}</td>
                      <td>{t(row.channel)}</td>
                      <td><StatusBadge status={row.status} /></td>
                      <td className="text-xs text-ink-500">{row.error || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}
    </Card>
  )
}
