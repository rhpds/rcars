import { useState, useRef, useEffect } from 'react'

interface WorkloadMultiSelectProps {
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
}

export function WorkloadMultiSelect({ options, selected, onChange, placeholder = 'Select workloads...' }: WorkloadMultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setIsOpen(false)
    }
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
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

  const sorted = [...options].sort((a, b) => a.localeCompare(b))
  const hasSelection = selected.length > 0
  const label = hasSelection ? `${selected.length} selected` : placeholder

  return (
    <div className="wl-multiselect" ref={ref}>
      <div
        className={`wl-multiselect-trigger${hasSelection ? ' active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        {label} ▾
      </div>
      {isOpen && (
        <div className="wl-multiselect-panel">
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
