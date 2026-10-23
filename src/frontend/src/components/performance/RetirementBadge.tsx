// Retirement workflow status, as returned by the API (`workflow_status`):
// approved/notified = recommended, started = in progress.
export type RetirementFilter = 'all' | 'hide' | 'only'

export function isRecommended(status: string | null | undefined) {
  return status === 'approved' || status === 'notified'
}

export function isInProgress(status: string | null | undefined) {
  return status === 'started'
}

export function isRetiring(status: string | null | undefined) {
  return isRecommended(status) || isInProgress(status)
}

export function matchesRetirementFilter(status: string | null | undefined, filter: RetirementFilter) {
  if (filter === 'hide') return !isRetiring(status)
  if (filter === 'only') return isRetiring(status)
  return true
}

export function fmtTargetDate(d: string | null | undefined) {
  if (!d) return null
  const date = d.length === 10 ? new Date(d + 'T00:00:00') : new Date(d)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function RetirementInlineBadge({ status, targetDate }: {
  status: string | null | undefined
  targetDate?: string | null
}) {
  if (!isRetiring(status)) return null
  const started = isInProgress(status)
  const date = started ? fmtTargetDate(targetDate) : null
  return (
    <span className={`ret-inline-badge${started ? ' ret-inline-badge--started' : ''}`}>
      {started ? 'in progress' : 'recommended'}{date && ` · ${date}`}
    </span>
  )
}

export function RetirementFilterGroup({ value, onChange, counts }: {
  value: RetirementFilter
  onChange: (v: RetirementFilter) => void
  counts?: { retiring: number }
}) {
  const options: [RetirementFilter, string][] = [
    ['all', 'All'], ['hide', 'Hide'], ['only', counts ? `Only (${counts.retiring})` : 'Only'],
  ]
  return (
    <div className="ret-filter-group">
      {options.map(([f, label]) => (
        <button key={f} type="button" onClick={() => onChange(f)}
          className={`ret-filter-group__btn${value === f ? ' active' : ''}`}>
          {label}
        </button>
      ))}
    </div>
  )
}
