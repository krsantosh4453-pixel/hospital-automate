import { useMemo } from "react"
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react"

const btn =
  "inline-flex h-8 min-w-8 items-center justify-center rounded-md px-2 text-[13px] font-medium text-ink-700 hover:bg-ink-100 disabled:pointer-events-none disabled:text-ink-300"

function Pagination({ currentPage, totalPages, totalRecords, onPageChange, showPageNumbers = true }) {
  const pageNumbers = useMemo(() => {
    const pages = []
    const maxVisible = 5
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2))
    let end = Math.min(totalPages, start + maxVisible - 1)

    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1)
    }

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }
    return pages
  }, [currentPage, totalPages])

  if (totalPages <= 1) return null

  return (
    <nav
      aria-label="Pagination"
      className="flex flex-col items-center justify-between gap-3 border-t border-line px-4 py-3 sm:flex-row"
    >
      <p className="text-[13px] text-ink-500">
        Page <span className="font-medium text-ink-800 tabular-nums">{currentPage}</span> of{" "}
        <span className="tabular-nums">{totalPages}</span>
        {totalRecords !== undefined && <span className="ml-1 tabular-nums">· {totalRecords} records</span>}
      </p>

      <div className="flex items-center gap-0.5">
        <button type="button" onClick={() => onPageChange(1)} disabled={currentPage === 1} className={btn} aria-label="First page">
          <ChevronsLeft size={16} aria-hidden="true" />
        </button>
        <button type="button" onClick={() => onPageChange(currentPage - 1)} disabled={currentPage === 1} className={btn} aria-label="Previous page">
          <ChevronLeft size={16} aria-hidden="true" />
        </button>

        {showPageNumbers && (
          <>
            {pageNumbers[0] > 1 && (
              <>
                <button type="button" onClick={() => onPageChange(1)} className={btn}>1</button>
                {pageNumbers[0] > 2 && <span className="px-1 text-ink-400">…</span>}
              </>
            )}

            {pageNumbers.map((page) => (
              <button
                key={page}
                type="button"
                onClick={() => onPageChange(page)}
                aria-current={page === currentPage ? "page" : undefined}
                className={page === currentPage ? `${btn} bg-brand-600 text-white hover:bg-brand-700` : btn}
              >
                {page}
              </button>
            ))}

            {pageNumbers[pageNumbers.length - 1] < totalPages && (
              <>
                {pageNumbers[pageNumbers.length - 1] < totalPages - 1 && <span className="px-1 text-ink-400">…</span>}
                <button type="button" onClick={() => onPageChange(totalPages)} className={btn}>{totalPages}</button>
              </>
            )}
          </>
        )}

        <button type="button" onClick={() => onPageChange(currentPage + 1)} disabled={currentPage === totalPages} className={btn} aria-label="Next page">
          <ChevronRight size={16} aria-hidden="true" />
        </button>
        <button type="button" onClick={() => onPageChange(totalPages)} disabled={currentPage === totalPages} className={btn} aria-label="Last page">
          <ChevronsRight size={16} aria-hidden="true" />
        </button>
      </div>
    </nav>
  )
}

export default Pagination
