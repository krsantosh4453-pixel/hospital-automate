export function Card({ as: Tag = "section", className = "", children, ...rest }) {
  return (
    <Tag className={`rounded-2xl border border-line bg-surface ${className}`} {...rest}>
      {children}
    </Tag>
  )
}

/** Card heading row: title + optional description on the left, actions on the right. */
export function CardHeader({ title, description, icon: Icon, actions, className = "", level = 2 }) {
  const Heading = `h${level}`
  return (
    <div className={`flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4 ${className}`}>
      <div className="flex min-w-0 items-start gap-3">
        {Icon && (
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <Icon size={17} aria-hidden="true" />
          </span>
        )}
        <div className="min-w-0">
          <Heading className="text-[15px] font-semibold leading-6 text-ink-900">{title}</Heading>
          {description && <p className="mt-0.5 text-[13px] leading-5 text-ink-500">{description}</p>}
        </div>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function CardBody({ className = "", children }) {
  return <div className={`px-5 py-4 ${className}`}>{children}</div>
}

export default Card
