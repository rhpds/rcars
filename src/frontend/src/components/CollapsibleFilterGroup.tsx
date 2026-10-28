import { useState, type ReactNode } from 'react'

interface CollapsibleFilterGroupProps {
  title: string
  note?: string
  /** Number of active filters inside this group; shown in the header so a closed group never hides a filter. */
  activeCount?: number
  /** When given, the header shows "Clear (n)" instead of a plain "(n)". */
  onClear?: () => void
  defaultOpen?: boolean
  children: ReactNode
}

/** Sidebar filter group whose body folds away behind its title. Starts open if a filter in it is already active. */
export function CollapsibleFilterGroup({
  title, note, activeCount = 0, onClear, defaultOpen = false, children,
}: CollapsibleFilterGroupProps) {
  const [open, setOpen] = useState(defaultOpen || activeCount > 0)

  return (
    <div className="browse-filter-group">
      <div className="browse-filter-group-label browse-filter-group-header">
        <button type="button" className="browse-filter-group-toggle" aria-expanded={open} onClick={() => setOpen(o => !o)}>
          <span className="browse-filter-group-chevron" aria-hidden="true">{open ? '▾' : '▸'}</span>
          {title}
          {!onClear && activeCount > 0 && <span className="browse-filter-group-count">({activeCount})</span>}
        </button>
        {onClear && activeCount > 0 && (
          <button type="button" className="browse-filter-group-clear" onClick={onClear}>
            Clear ({activeCount})
          </button>
        )}
      </div>
      {open && note && <div className="browse-filter-group-note">{note}</div>}
      {open && children}
    </div>
  )
}
