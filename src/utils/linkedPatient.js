import { useSearchParams } from "react-router-dom"

/**
 * A patient handed over in the URL by another module, e.g. the ER action menu
 * (requirement J3): ?patient=<id>&q=<name>&edit=<id>&record=<id>.
 * @returns {{ patientId: string, query: string, editId: string, recordId: string }}
 */
export function useLinkedPatient() {
  const [params] = useSearchParams()
  return {
    patientId: params.get("patient") || "",
    query: params.get("q") || "",
    editId: params.get("edit") || "",
    recordId: params.get("record") || "",
  }
}
