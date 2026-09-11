import { useState, useRef, useEffect } from 'react'

interface WorkloadMultiSelectProps {
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
}

export function WorkloadMultiSelect({ options, selected, onChange, placeholder = 'Select workloads...' }: WorkloadMultiSelectProps) {
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

  const sorted = [...options].sort((a, b) => a.localeCompare(b)).filter(o => o.toLowerCase().includes(filterText.toLowerCase()))
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
          {sorted.map(opt => (
            <label key={opt} className="wl-multiselect-option">
              <input
                type="checkbox"
                checked={selected.includes(opt)}
                onChange={() => toggle(opt)}
              />
              <span>{opt}</span>
            </label>
          ))}
          {sorted.length === 0 && (
            <div style={{ padding: '8px 12px', color: 'var(--text-muted)', fontSize: '12px' }}>
              No workload mappings available
            </div>
          )}
        </div>
      )}
    </div>
  )
}
