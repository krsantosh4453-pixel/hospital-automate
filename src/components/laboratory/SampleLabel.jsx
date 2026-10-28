import { code39Bars, canEncode } from "../../utils/code39.js"
import { formatPrintDate } from "../../utils/printDate.js"

const MODULE_PX = 2
const BAR_HEIGHT = 56
const QUIET_ZONE = 10 // narrow modules of white space each side, required by scanners

/** Code 39 barcode of a sample number, as a crisp SVG. */
export function Barcode({ value }) {
  if (!value || !canEncode(value)) return <p className="font-mono text-sm">{value}</p>
  const { bars, width } = code39Bars(value)
  const total = width + QUIET_ZONE * 2
  return (
    <svg
      role="img"
      aria-label={`Barcode ${value}`}
      width={total * MODULE_PX}
      height={BAR_HEIGHT}
      viewBox={`0 0 ${total} ${BAR_HEIGHT}`}
      preserveAspectRatio="none"
      shapeRendering="crispEdges"
      style={{ maxWidth: "100%", height: "auto" }}
    >
      <rect width={total} height={BAR_HEIGHT} fill="#fff" />
      {bars.map((bar) => (
        <rect key={bar.x} x={bar.x + QUIET_ZONE} width={bar.width} height={BAR_HEIGHT} fill="#000" />
      ))}
    </svg>
  )
}

/** Tube label: barcode, sample number, patient, test and collection date (F6). */
export default function SampleLabel({ test }) {
  const sample = test.sample_collection || {}
  return (
    <div className="inline-block max-w-full border border-black p-2 text-black">
      <Barcode value={sample.sample_id} />
      <p className="font-mono text-sm font-semibold tracking-wider">{sample.sample_id}</p>
      <p className="text-xs">{test.patient_name} · {test.name}</p>
      <p className="text-xs">{sample.sample_type} · {sample.container_type} · {formatPrintDate(sample.collected_at)}</p>
    </div>
  )
}
