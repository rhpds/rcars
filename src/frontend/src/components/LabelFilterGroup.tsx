import { labelDisplay } from '../utils/labelFilters'

interface LabelFilterGroupProps {
  title: string
  options: [string, number][]
  selected: Set<string>
  onToggle: (value: string) => void
  onClear: () => void
}

export function LabelFilterGroup({ title, options, selected, onToggle, onClear }: LabelFilterGroupProps) {
  return (
    <div className="browse-filter-group">
      <div className="browse-filter-group-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {title}
        {selected.size > 0 && (
          <button onClick={onClear}
            style={{ background: 'none', border: 'none', color: 'var(--score-amber)', fontSize: '11px', cursor: 'pointer', padding: 0 }}>
            Clear ({selected.size})
          </button>
        )}
      </div>
      <div style={{
        maxHeight: '200px', overflowY: 'auto', paddingRight: '8px',
        border: '1px solid var(--border-section)', borderRadius: 'var(--radius-sm)', background: 'var(--bg-page)',
      }}>
        {options.map(([value, count]) => (
          <label key={value} style={{
            display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 8px',
            cursor: 'pointer', fontSize: '11px',
          }}>
            <input type="checkbox" checked={selected.has(value)} onChange={() => onToggle(value)} />
            <span>{labelDisplay(value)}</span>
            <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>
          </label>
        ))}
      </div>
    </div>
  )
}
