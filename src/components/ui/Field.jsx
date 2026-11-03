import { Children, cloneElement, isValidElement, useId } from "react"
import { useT } from "./useT.js"

/**
 * Label + control + hint/error, wired for screen readers.
 * Pass a single input/select/textarea as the child; its id and aria props are set here.
 */
export function Field({ label, hint, error, required = false, className = "", children }) {
  const tr = useT()
  const autoId = useId()
  const id = (isValidElement(children) && children.props.id) || autoId
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined

  const control = isValidElement(children)
    ? cloneElement(children, {
        id,
        "aria-describedby": describedBy,
        "aria-invalid": error ? "true" : children.props["aria-invalid"],
        placeholder: tr(children.props.placeholder),
        required: required || children.props.required,
      })
    : children

  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="hms-label">
          {tr(label)}
          {required && (
            <span className="ml-0.5 text-red-600" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      {control}
      {hint && !error && (
        <p id={hintId} className="mt-1.5 text-xs text-ink-500">
          {tr(hint)}
        </p>
      )}
      {error && (
        <p id={errorId} className="mt-1.5 text-xs font-medium text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}

export function Input({ className = "", ...props }) {
  return <input className={`hms-input w-full ${className}`} {...props} />
}

export function Select({ className = "", children, ...props }) {
  const tr = useT()
  // Only options with an explicit value are translated: an option without one
  // submits its text, which must stay the English value the server expects.
  const options = Children.map(children, (child) =>
    isValidElement(child) && child.type === "option" && child.props.value !== undefined && typeof child.props.children === "string"
      ? cloneElement(child, {}, tr(child.props.children))
      : child,
  )
  return (
    <select className={`hms-input w-full pr-8 ${className}`} {...props}>
      {options}
    </select>
  )
}

export function Textarea({ className = "", rows = 3, ...props }) {
  return <textarea rows={rows} className={`hms-input w-full min-h-[5rem] ${className}`} {...props} />
}

/** Titled group of fields inside a long form. */
export function FormSection({ title, description, children, className = "" }) {
  const tr = useT()
  return (
    <fieldset className={`border-t border-line pt-5 first:border-t-0 first:pt-0 ${className}`}>
      <legend className="sr-only">{tr(title)}</legend>
      <div className="mb-4">
        <p className="text-sm font-semibold text-ink-900" aria-hidden="true">{tr(title)}</p>
        {description && <p className="mt-0.5 text-[13px] text-ink-500">{tr(description)}</p>}
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  )
}
