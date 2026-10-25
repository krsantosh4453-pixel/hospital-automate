import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { Eye, FileText, Trash2, Upload } from "lucide-react"
import { Alert, Badge, Button, Card, EmptyState, Field, Input, Modal, Select, SkeletonRows, TableWrap, useConfirm } from "../../components/ui"

function PatientDocuments() {
  const [confirm, confirmDialog] = useConfirm()

  const { patient } = useAuth()
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadForm, setUploadForm] = useState({ title: "", folder: "", file: null })

  useEffect(() => {
    if (!patient?.id) return

    const fetchDocuments = async () => {
      setLoading(true)
      try {
        const data = await api.patients.documents.list(patient.id)
        const allDocs = data?.results || data || []
        setDocuments(allDocs)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchDocuments()
  }, [patient?.id])

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      setUploadForm(prev => ({ ...prev, file, title: file.name.replace(/\.[^/.]+$/, "") }))
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!uploadForm.file) return

    setUploading(true)
    setError(null)

    try {
      await api.patients.documents.upload(patient.id, uploadForm.file, uploadForm.title, uploadForm.folder)
      setShowUpload(false)
      setUploadForm({ title: "", folder: "", file: null })
      const data = await api.patients.documents.list(patient.id)
      setDocuments(data?.results || data || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (docId) => {
    if (!(await confirm({ title: "Delete document?", message: "This removes the document from your record.", confirmLabel: "Delete", destructive: true }))) return

    try {
      await api.patients.documents.delete(docId)
      setDocuments(prev => prev.filter(d => d.id !== docId))
    } catch (err) {
      setError(err.message)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  const formatSize = (bytes) => {
    if (!bytes) return "—"
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const handleView = async (doc) => {
    // Opened through the authenticated download API (files are not public).
    const win = window.open("", "_blank")
    try {
      const blob = await api.patients.documents.download(doc.id)
      const url = URL.createObjectURL(blob)
      if (win) win.location.href = url
      else window.location.assign(url)
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (err) {
      if (win) win.close()
      setError(err.message)
    }
  }

  const closeUpload = () => {
    setShowUpload(false)
    setUploadForm({ title: "", folder: "", file: null })
  }

  return (
    <>{confirmDialog}<div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink-900 sm:text-2xl">Medical records</h1>
          <p className="mt-1 text-sm text-ink-500">Documents you or the hospital have added to your record.</p>
        </div>
        <Button icon={Upload} onClick={() => setShowUpload(true)}>Upload document</Button>
      </header>

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

      {loading ? (
        <Card><SkeletonRows rows={3} /></Card>
      ) : documents.length === 0 ? (
        <Card>
          <EmptyState
            icon={FileText}
            title="No documents yet"
            description="Upload reports or prescriptions from other clinics so your doctors can see them."
            action={<Button icon={Upload} onClick={() => setShowUpload(true)}>Upload document</Button>}
          />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <TableWrap>
            <table className="hms-table">
              <thead>
                <tr>
                  <th scope="col">Document</th>
                  <th scope="col">Category</th>
                  <th scope="col">Added</th>
                  <th scope="col" className="num">Size</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <span className="flex items-center gap-3">
                        <FileText size={18} className="shrink-0 text-ink-400" aria-hidden="true" />
                        <span className="font-medium text-ink-900">{doc.title}</span>
                      </span>
                    </td>
                    <td><Badge tone="neutral">{doc.folder || "Uncategorized"}</Badge></td>
                    <td className="whitespace-nowrap tabular-nums text-ink-600">{formatDate(doc.uploaded_at)}</td>
                    <td className="num text-ink-600">{formatSize(doc.file_size)}</td>
                    <td>
                      <div className="flex items-center justify-end gap-1">
                        <Button size="sm" variant="subtle" icon={Eye} onClick={() => handleView(doc)}>View</Button>
                        <Button size="icon-sm" variant="danger-ghost" icon={Trash2} onClick={() => handleDelete(doc.id)} aria-label={`Delete ${doc.title}`} title="Delete" />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </Card>
      )}

      <Modal
        open={showUpload}
        onClose={closeUpload}
        title="Upload document"
        footer={
          <>
            <Button variant="secondary" onClick={closeUpload} disabled={uploading}>Cancel</Button>
            <Button type="submit" form="doc-upload" loading={uploading}>Upload</Button>
          </>
        }
      >
        <form id="doc-upload" onSubmit={handleUpload} className="space-y-4">
          <Field label="File" required hint="PDF, image or office document.">
            <input type="file" onChange={handleFileChange} className="block w-full text-sm text-ink-700 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100" />
          </Field>
          <Field label="Title" required>
            <Input value={uploadForm.title} onChange={(e) => setUploadForm((prev) => ({ ...prev, title: e.target.value }))} />
          </Field>
          <Field label="Category">
            <Select value={uploadForm.folder} onChange={(e) => setUploadForm((prev) => ({ ...prev, folder: e.target.value }))}>
              <option value="">Select category</option>
              <option value="Prescriptions">Prescriptions</option>
              <option value="Lab Reports">Lab reports</option>
              <option value="Discharge Summaries">Discharge summaries</option>
              <option value="Imaging">Imaging (X-ray, MRI, CT)</option>
              <option value="Insurance">Insurance documents</option>
              <option value="Other">Other</option>
            </Select>
          </Field>
        </form>
      </Modal>
    </div></>
  )
}

export default PatientDocuments
