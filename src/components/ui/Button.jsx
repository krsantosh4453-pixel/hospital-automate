import { forwardRef } from "react"
import { LoaderCircle } from "lucide-react"

const VARIANTS = {
  primary:
    "bg-brand-600 text-white shadow-sm hover:bg-brand-700 active:bg-brand-800 disabled:bg-brand-300",
  secondary:
    "bg-white text-ink-800 border border-line-strong shadow-sm hover:bg-ink-50 hover:border-ink-400 active:bg-ink-100 disabled:text-ink-400",
  ghost:
    "text-ink-700 hover:bg-ink-100 active:bg-ink-200 disabled:text-ink-400",
  subtle:
    "bg-brand-50 text-brand-700 hover:bg-brand-100 active:bg-brand-200 disabled:text-brand-300",
  danger:
    "bg-red-600 text-white shadow-sm hover:bg-red-700 active:bg-red-800 disabled:bg-red-200",
  "danger-ghost":
    "text-red-700 hover:bg-red-50 active:bg-red-100 disabled:text-red-200",
}

const SIZES = {
  sm: "h-8 px-3 text-[13px] gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-[15px] gap-2",
  icon: "h-9 w-9 justify-center",
  "icon-sm": "h-8 w-8 justify-center",
}

/**
 * The one button used across HMS.
 * `icon` / `iconRight` take a lucide component (not an element).
 */
const Button = forwardRef(function Button(
  {
    variant = "primary",
    size = "md",
    icon: Icon,
    iconRight: IconRight,
    loading = false,
    disabled,
    className = "",
    children,
    type = "button",
    ...rest
  },
  ref,
) {
  const iconSize = size === "sm" || size === "icon-sm" ? 15 : 17
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex shrink-0 items-center rounded-lg font-medium whitespace-nowrap transition-colors duration-150 disabled:cursor-not-allowed ${VARIANTS[variant] || VARIANTS.primary} ${SIZES[size] || SIZES.md} ${className}`}
      {...rest}
    >
      {loading ? (
        <LoaderCircle size={iconSize} className="animate-spin" aria-hidden="true" />
      ) : (
        Icon && <Icon size={iconSize} aria-hidden="true" strokeWidth={2} />
      )}
      {children}
      {IconRight && !loading && <IconRight size={iconSize} aria-hidden="true" strokeWidth={2} />}
    </button>
  )
})

export default Button
