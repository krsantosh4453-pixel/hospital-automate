import { useCallback, useEffect, useRef, useState } from "react"
import { ImageUp } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, EmptyState, SkeletonRows } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// Prompt 5 (MF-005): the images of one imaging study. Files come only through
// the study's audited endpoint (never a public /media/ URL); the server checks
// type, size and who may upload, and closes the study to images once signed.

const ACCEPT = ".png,.jpg,.jpeg,.dcm,.pdf"
const OPEN_FOR_IMAGES = ["Ordered", "Scheduled", "Performed"]
const size = (bytes) => (bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`)

export default function StudyImages({ study, canUpload }) {
  const { t } = useLanguage()
  const [images, setImages] = useState(null)
  const [error, setError] = useState("")
  const [uploading, setUploading] = useState(false)
  const input = useRef(null)

  const load = useCallback(() => {
    setError("")
    api.imaging.images(study.id).then(setImages).catch((err) => {
      setImages([])
      setError(err.message)
    })
  }, [study.id])

  useEffect(() => {
    load()
  }, [load])

  const upload = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (!file) return
    setUploading(true)
    setError("")
    try {
      await api.imaging.uploadImage(study.id, file)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const view = async (image) => {
    setError("")
    try {
      const url = URL.createObjectURL(await api.imaging.imageBlob(study.id, image.id))
      window.open(url, "_blank", "noopener")
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (err) {
      setError(err.message)
    }
  }

  const uploadAllowed = canUpload && OPEN_FOR_IMAGES.includes(study.status)
  return (
    <div className="space-y-3">
      {error && <Alert tone="danger">{error}</Alert>}
      {images === null ? (
        <SkeletonRows rows={2} />
      ) : images.length === 0 ? (
        <EmptyState compact icon={ImageUp} title={t("No images attached")} />
      ) : (
        <ul className="divide-y divide-ink-100 rounded-xl border border-line">
          {images.map((image) => (
            <li key={image.id} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
              <span className="min-w-0">
                <span className="block truncate font-medium text-ink-900">{image.title}</span>
                <span className="block text-xs text-ink-500">{size(image.file_size)} · {new Date(image.uploaded_at).toLocaleString("en-IN")}</span>
              </span>
              <Button size="sm" variant="secondary" onClick={() => view(image)}>{t("Open")}</Button>
            </li>
          ))}
        </ul>
      )}
      {uploadAllowed && (
        <div>
          <input ref={input} id={`study-image-${study.id}`} type="file" accept={ACCEPT} className="sr-only" onChange={upload} />
          <Button icon={ImageUp} variant="secondary" loading={uploading} onClick={() => input.current?.click()}>
            {t("Attach image")}
          </Button>
          <p className="mt-1 text-xs text-ink-500">{t("PNG, JPEG, DICOM or PDF, up to 50 MB.")}</p>
        </div>
      )}
      {!uploadAllowed && canUpload && <p className="text-xs text-ink-500">{t("A signed or cancelled study takes no more images.")}</p>}
    </div>
  )
}
