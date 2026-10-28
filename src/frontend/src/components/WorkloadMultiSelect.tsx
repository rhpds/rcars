import { useState, useRef, useEffect } from 'react'

interface WorkloadMultiSelectProps {
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  formatOption?: (v: string) => string
}

export function WorkloadMultiSelect({ options, selected, onChange, placeholder = 'Select workloads...', formatOption }: WorkloadMultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [filterText, setFilterText] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  const closePanel = () => { setIsOpen(false); setFilterText('') }

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) closePanel()
    }
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closePanel()
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [])

  const toggle = (name: string) => {
    if (selected.includes(name)) {
      onChange(selected.filter(s => s !== name))
    } else {
      onChange([...selected, name])
    }
  }

  // Keep NONE_LABEL (__none__) last if present
  const NONE_LABEL = '__none__'
  const hasNone = options.includes(NONE_LABEL)
  const regularOptions = options.filter(o => o !== NONE_LABEL)
  const sorted = [...regularOptions].sort((a, b) => a.localeCompare(b))
  if (hasNone) sorted.push(NONE_LABEL)

  // Filter using formatted display text if formatOption is provided
  const filtered = sorted.filter(o => {
    const displayText = formatOption ? formatOption(o) : o
    return displayText.toLowerCase().includes(filterText.toLowerCase())
  })
  const hasSelection = selected.length > 0
  const label = hasSelection ? `${selected.length} selected` : placeholder

  return (
    <div className="wl-multiselect" ref={ref}>
      <div
        className={`wl-multiselect-trigger${hasSelection ? ' active' : ''}`}
        onClick={() => isOpen ? closePanel() : setIsOpen(true)}
      >
        {label} ▾
      </div>
      {isOpen && (
        <div className="wl-multiselect-panel">
          <input
            className="wl-multiselect-search"
            type="text"
            placeholder="Search..."
            value={filterText}
            onChange={e => setFilterText(e.target.value)}
            onClick={e => e.stopPropagation()}
            autoFocus
          />
          {filtered.map(opt => (
            <label key={opt} className="wl-multiselect-option">
              <input
                type="checkbox"
                checked={selected.includes(opt)}
                onChange={() => toggle(opt)}
              />
              <span>{formatOption ? formatOption(opt) : opt}</span>
            </label>
          ))}
          {filtered.length === 0 && (
            <div style={{ padding: '8px 12px', color: 'var(--text-muted)', fontSize: '12px' }}>
              No workload mappings available
            </div>
          )}
        </div>
      )}
    </div>
  )
}
