import { useCallback, useEffect, useState } from "react"
import { ReceiptText } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Badge, Button, Card, CardHeader, Field, Input, TableWrap, useConfirm } from "../ui"
import { useToast } from "../Toast.jsx"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// B-2 / B-3: consultations and laboratory tests the server skipped because
// they had no price, and charges left on a cancelled bill. "Bill priced work"
// bills only the first kind; a charge from a cancelled bill is billed only
// when picked, since the cancellation may have been deliberate. The server
// charges each service once only. Hidden when there is nothing to bill.

export default function UnbilledWork({ hospitalId, canCharge, onCharged }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()
  const [since, setSince] = useState("")
  const [rows, setRows] = useState([])
  const [error, setError] = useState("")
  const [charging, setCharging] = useState(false)

  const load = useCallback(async () => {
    if (!hospitalId) return
    try {
      const data = await api.billing.priceList.unbilled(hospitalId, since || undefined)
      setRows(data?.results || [])
      setError("")
    } catch (err) {
      setError(err.message || "Could not load unbilled work.")
    }
  }, [hospitalId, since])

  useEffect(() => {
    load()
  }, [load])

  const priced = rows.filter((r) => r.priced && r.source !== "cancelled")
  const [billingRow, setBillingRow] = useState(null)

  const billOne = async (row) => {
    const ok = await confirm({
      title: t("Bill this again?"),
      message: t("It was on bill {invoice}, cancelled because: {reason}", {
        invoice: row.cancelled_invoice, reason: row.cancel_reason || t("no reason recorded"),
      }),
      confirmLabel: "Bill it",
    })
    if (!ok) return
    setBillingRow(`${row.kind}-${row.id}`)
    try {
      const result = await api.billing.priceList.chargeUnbilled(hospitalId, since || undefined, [{ kind: row.kind, id: row.id }])
      toast.success(t("{count} services billed.", { count: result?.charged?.length || 0 }))
      await load()
      onCharged?.()
    } catch (err) {
      toast.error(err.message || "Could not bill the work.")
    } finally {
      setBillingRow(null)
    }
  }

  const charge = async () => {
    const ok = await confirm({
      title: t("Bill {count} services?", { count: priced.length }),
      message: t("Each goes on the patient's open bill at today's price. Services without a price stay on this list."),
      confirmLabel: "Bill them",
    })
    if (!ok) return
    setCharging(true)
    try {
      const result = await api.billing.priceList.chargeUnbilled(hospitalId, since || undefined)
      toast.success(t("{count} services billed.", { count: result?.charged?.length || 0 }))
      await load()
      onCharged?.()
    } catch (err) {
      toast.error(err.message || "Could not bill the work.")
    } finally {
      setCharging(false)
    }
  }

  if (!hospitalId || (rows.length === 0 && !error)) return null

  return (
    <Card className="mb-6" role="region" aria-label={t("Unbilled work")}>
      <CardHeader
        icon={ReceiptText}
        title={`${t("Unbilled work")} (${rows.length})`}
        description="Consultations and laboratory tests that could not be billed because they had no price, and charges from cancelled bills."
      />
      {error && <Alert tone="danger" className="m-4">{error}</Alert>}
      <div className="space-y-3 px-5 pb-5">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Since (at most 90 days back)">
            <Input type="date" value={since} onChange={(e) => setSince(e.target.value)} />
          </Field>
          {canCharge && (
            <Button onClick={charge} loading={charging} disabled={priced.length === 0}>
              {t("Bill priced work")} ({priced.length})
            </Button>
          )}
        </div>
        <TableWrap>
          <table className="hms-table">
            <thead>
              <tr>
                <th scope="col">{t("Date")}</th>
                <th scope="col">{t("Work")}</th>
                <th scope="col">{t("Service")}</th>
                <th scope="col">{t("Price")}</th>
                {canCharge && <th scope="col"><span className="sr-only">{t("Actions")}</span></th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.kind}-${row.id}`}>
                  <td className="tabular-nums">{row.date}</td>
                  <td>{row.kind === "consultation" ? t("Consultation") : row.kind === "imaging" ? t("Imaging study") : t("Laboratory test")} #{row.id}</td>
                  <td>
                    {row.service}
                    {row.source === "cancelled" && (
                      <span className="block text-xs text-ink-500">
                        {t("On cancelled bill {invoice}: {reason}", { invoice: row.cancelled_invoice, reason: row.cancel_reason || t("no reason recorded") })}
                      </span>
                    )}
                  </td>
                  <td>
                    {row.priced ? <Badge tone="success">{t("Priced")}</Badge> : <Badge tone="warning">{t("Add a price first")}</Badge>}
                  </td>
                  {canCharge && (
                    <td className="text-right">
                      {row.source === "cancelled" && row.priced && (
                        <Button size="sm" variant="secondary" loading={billingRow === `${row.kind}-${row.id}`} onClick={() => billOne(row)}>
                          {t("Bill")}
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </div>
      {confirmDialog}
    </Card>
  )
}
