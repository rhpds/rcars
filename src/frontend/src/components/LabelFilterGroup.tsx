import { labelDisplay, withSelected } from '../utils/labelFilters'
import { CollapsibleFilterGroup } from './CollapsibleFilterGroup'

interface LabelFilterGroupProps {
  title: string
  /** Values with an optional count; the count is hidden when absent. */
  options: [string, number?][]
  selected: Set<string>
  onToggle: (value: string) => void
  onClear: () => void
  /** Display text for a value. Defaults to labelDisplay (underscores → spaces, None sentinel → "None"). */
  formatValue?: (value: string) => string
}

export function LabelFilterGroup({ title, options, selected, onToggle, onClear, formatValue = labelDisplay }: LabelFilterGroupProps) {
  return (
    <CollapsibleFilterGroup title={title} activeCount={selected.size} onClear={onClear}>
      <div style={{
        maxHeight: '200px', overflowY: 'auto', paddingRight: '8px',
        border: '1px solid var(--border-section)', borderRadius: 'var(--radius-sm)', background: 'var(--bg-page)',
      }}>
        {withSelected(options, selected).map(([value, count]) => (
          <label key={value} style={{
            display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 8px',
            cursor: 'pointer', fontSize: '11px',
          }}>
            <input type="checkbox" checked={selected.has(value)} onChange={() => onToggle(value)} />
            <span>{formatValue(value)}</span>
            {count !== undefined && <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>}
          </label>
        ))}
      </div>
    </CollapsibleFilterGroup>
  )
}
