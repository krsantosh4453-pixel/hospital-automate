import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { FileTextIcon, TriangleAlertIcon, UploadIcon, XIcon } from "lucide-react"
import { useConfirm } from "../../components/ui"

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
    if (!(await confirm("Are you sure you want to delete this document?"))) return

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

  const getFileIcon = (fileName) => {
    const ext = fileName?.split('.').pop()?.toLowerCase()
    if (['pdf'].includes(ext)) return ""
    if (['jpg', 'jpeg', 'png', 'gif'].includes(ext)) return ""
    if (['doc', 'docx'].includes(ext)) return ""
    if (['xls', 'xlsx'].includes(ext)) return ""
    return ""
  }

  return (
    <>{confirmDialog}<div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Documents</h1>
          <p className="text-gray-500 mt-1">Manage your medical documents</p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="px-5 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 flex items-center gap-2"
        >
          <span><UploadIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></span> Upload Document
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm flex items-center justify-between">
          <span><TriangleAlertIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> {error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700"><XIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></button>
        </div>
      )}

      {showUpload && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-800">Upload Document</h2>
              <button onClick={() => setShowUpload(false)} className="text-gray-400 hover:text-gray-700 text-xl font-semibold"><XIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></button>
            </div>
            <form onSubmit={handleUpload} className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">File</label>
                <input type="file" onChange={handleFileChange} required className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                <input
                  type="text"
                  value={uploadForm.title}
                  onChange={(e) => setUploadForm(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="Document title"
                  className="hms-input w-full"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={uploadForm.folder}
                  onChange={(e) => setUploadForm(prev => ({ ...prev, folder: e.target.value }))}
                  className="hms-input w-full"
                >
                  <option value="">Select category</option>
                  <option value="Prescriptions">Prescriptions</option>
                  <option value="Lab Reports">Lab Reports</option>
                  <option value="Discharge Summaries">Discharge Summaries</option>
                  <option value="Imaging">Imaging (X-ray, MRI, CT)</option>
                  <option value="Insurance">Insurance Documents</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowUpload(false)} className="flex-1 px-5 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200">Cancel</button>
                <button type="submit" disabled={uploading} className="flex-1 px-5 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">{uploading ? "Uploading..." : "Upload"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : documents.length > 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Document</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Category</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Uploaded</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Size</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{getFileIcon(doc.file)}</span>
                        <div>
                          <p className="font-medium text-gray-800">{doc.title}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">{doc.folder || "Uncategorized"}</span>
                    </td>
                    <td className="px-5 py-4 text-gray-700">{formatDate(doc.uploaded_at)}</td>
                    <td className="px-5 py-4 text-gray-700">{formatSize(doc.file_size)}</td>
                    <td className="px-5 py-4">
                      <div className="flex gap-2">
                        {doc.file && (
                          <a href={doc.file} target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
                            View
                          </a>
                        )}
                        <button onClick={() => handleDelete(doc.id)} className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700">Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
          <div className="text-4xl mb-3"><FileTextIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <h3 className="font-bold text-gray-800">No documents uploaded</h3>
          <p className="text-sm text-gray-500 mt-1">Upload your medical documents for easy access.</p>
          <button onClick={() => setShowUpload(true)} className="mt-4 px-5 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700">Upload First Document</button>
        </div>
      )}
    </div></>
  )
}

export default PatientDocuments