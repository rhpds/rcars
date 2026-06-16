import { useState, useEffect, useCallback } from 'react'
import { api, ReportingMetricsItem } from '../services/api'

type SortField = 'retirement_score' | 'provisions' | 'total_cost' | 'closed_amount' | 'touched_amount' | 'display_name'
type ScoreFilter = 'all' | 'high' | 'review' | 'keepers'

const fmt = (n: number) => {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toFixed(0)}`
}

const fmtRoi = (amount: number, cost: number) => {
  if (cost <= 0 || amount <= 0) return '—'
  return `${(amount / cost).toFixed(1)}x`
}

const scoreColor = (score: number) => score >= 75 ? '#e94560' : score >= 50 ? '#e98a3a' : '#4ecca3'
const scoreBg = (score: number) => score >= 75 ? 'rgba(233,69,96,0.2)' : score >= 50 ? 'rgba(233,138,58,0.2)' : 'rgba(78,204,163,0.2)'

const stageBadgeClass: Record<string, string> = {
  prod: 'ca-env-prod', event: 'ca-env-event', dev: 'ca-env-dev', test: 'ca-env-test',
}

export function RetirementPage() {
  const [items, setItems] = useState<ReportingMetricsItem[]>([])
  const [allItems, setAllItems] = useState<ReportingMetricsItem[]>([])
  const [summary, setSummary] = useState<{ total: number; high: number; review: number; keepers: number } | null>(null)
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortField>('retirement_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>('all')
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const minScore = scoreFilter === 'high' ? 75 : scoreFilter === 'review' ? 50 : scoreFilter === 'keepers' ? 0 : undefined
      const maxForKeepers = scoreFilter === 'keepers'
      const data = await api.getRetirementDashboard({
        sort_by: sortBy, sort_dir: sortDir,
        min_score: minScore,
        search: search || undefined,
      })
      let filtered = data.items
      if (maxForKeepers) {
        filtered = filtered.filter(i => i.retirement_score < 50)
      } else if (scoreFilter === 'review') {
        filtered = filtered.filter(i => i.retirement_score < 75)
      }
      setItems(filtered)
      setAllItems(data.items)
      setSummary(data.summary)
      setSyncedAt(data.synced_at)
    } finally {
      setLoading(false)
    }
  }, [sortBy, sortDir, scoreFilter, search])

  useEffect(() => { loadData() }, [loadData])

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(field)
      setSortDir('desc')
    }
  }

  const toggleExpand = (name: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const sortIndicator = (field: SortField) => {
    if (sortBy !== field) return null
    return <span className="sort-indicator">{sortDir === 'desc' ? ' ▼' : ' ▲'}</span>
  }

  const syncAge = syncedAt
    ? `${Math.round((Date.now() - new Date(syncedAt).getTime()) / 3600000)}h ago`
    : 'never'

  const totalCost = allItems.reduce((s, i) => s + i.total_cost, 0)
  const totalClosed = allItems.reduce((s, i) => s + i.closed_amount, 0)
  const totalTouched = allItems.reduce((s, i) => s + i.touched_amount, 0)

  return (
    <div className="ca-page">
      <div className="ca-header">
        <h3>Retirement Analysis</h3>
        <span className="ca-subtitle" style={{ marginBottom: 0 }}>Last synced: {syncAge}</span>
      </div>
      <p className="ca-subtitle">Retirement scoring based on provisions, sales, cost, and catalog presence over the trailing year.</p>

      {summary && (
        <div className="ca-stats-grid">
          <div className="ca-stat-card">
            <div className="ca-stat-label">Total Assets</div>
            <div className="ca-stat-value ca-color-blue">{summary.total}</div>
          </div>
          <div className="ca-stat-card">
            <div className="ca-stat-label">High Retirement</div>
            <div className="ca-stat-value ca-color-red">{summary.high}</div>
          </div>
          <div className="ca-stat-card">
            <div className="ca-stat-label">Review</div>
            <div className="ca-stat-value ca-color-orange">{summary.review}</div>
          </div>
          <div className="ca-stat-card">
            <div className="ca-stat-label">Keepers</div>
            <div className="ca-stat-value ca-color-green">{summary.keepers}</div>
          </div>
          <div className="ca-stat-card">
            <div className="ca-stat-label">Total Cost</div>
            <div className="ca-stat-value">{fmt(totalCost)}</div>
          </div>
          <div className="ca-stat-card">
            <div className="ca-stat-label">Total Closed</div>
            <div className="ca-stat-value ca-color-green">{fmt(totalClosed)}</div>
          </div>
          <div className="ca-stat-card">
            <div className="ca-stat-label">Total Touched</div>
            <div className="ca-stat-value">{fmt(totalTouched)}</div>
          </div>
        </div>
      )}

      <div className="ca-controls">
        {(['all', 'high', 'review', 'keepers'] as ScoreFilter[]).map(f => (
          <button key={f} onClick={() => setScoreFilter(f)}
            className={`ca-filter-btn${scoreFilter === f ? ' active' : ''}`}>
            {f === 'all' ? 'All' : f === 'high' ? 'High ≥75' : f === 'review' ? 'Review 50-74' : 'Keepers <50'}
          </button>
        ))}
        <input
          type="text" placeholder="Search by name..."
          value={search} onChange={e => setSearch(e.target.value)}
          className="ca-search"
        />
      </div>

      {loading ? (
        <p className="ca-color-muted">Loading...</p>
      ) : (
        <>
          <div className="ca-row-count">{items.length} of {summary?.total ?? 0} assets</div>
          <div className="ca-table-wrap">
            <table className="ca-table">
              <thead>
                <tr>
                  <th onClick={() => toggleSort('display_name')} style={{ width: '40%' }}>Name{sortIndicator('display_name')}</th>
                  <th className="num" onClick={() => toggleSort('retirement_score')} style={{ width: '7%' }}>Score{sortIndicator('retirement_score')}</th>
                  <th className="num" onClick={() => toggleSort('provisions')} style={{ width: '9%' }}>Provisions{sortIndicator('provisions')}</th>
                  <th className="num" onClick={() => toggleSort('touched_amount')} style={{ width: '9%' }}>Touched{sortIndicator('touched_amount')}</th>
                  <th className="num" style={{ width: '7%' }}>T-ROI</th>
                  <th className="num" onClick={() => toggleSort('closed_amount')} style={{ width: '9%' }}>Closed{sortIndicator('closed_amount')}</th>
                  <th className="num" style={{ width: '7%' }}>C-ROI</th>
                  <th className="num" onClick={() => toggleSort('total_cost')} style={{ width: '9%' }}>Cost{sortIndicator('total_cost')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => {
                  const isExpanded = expanded.has(item.catalog_base_name)
                  return (
                    <>{/* Fragment avoids nested tbody */}
                      <tr key={item.catalog_base_name} className="clickable" onClick={() => toggleExpand(item.catalog_base_name)}>
                        <td className="name" title={item.display_name}>
                          {item.display_name}
                        </td>
                        <td className="num">
                          <span className="ca-score-badge" style={{ background: scoreBg(item.retirement_score), color: scoreColor(item.retirement_score) }}>
                            {item.retirement_score}
                          </span>
                        </td>
                        <td className="num">{item.provisions.toLocaleString()}</td>
                        <td className="num">{fmt(item.touched_amount)}</td>
                        <td className="num muted">{fmtRoi(item.touched_amount, item.total_cost)}</td>
                        <td className="num">{fmt(item.closed_amount)}</td>
                        <td className="num muted">{fmtRoi(item.closed_amount, item.total_cost)}</td>
                        <td className="num">{fmt(item.total_cost)}</td>
                      </tr>
                      {isExpanded && (
                        <tr key={`${item.catalog_base_name}-detail`} className="ca-expanded-row">
                          <td colSpan={8}>
                            <div className="ca-detail">
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Environments</span>
                                <span className="ca-detail-value">
                                  {item.stages.map(s => (
                                    <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(s.ci_name)}`} target="_blank" rel="noreferrer"
                                      className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                                      onClick={e => e.stopPropagation()}>
                                      {s.stage}
                                    </a>
                                  ))}
                                  {item.stages.length === 0 && <span className="ca-color-muted">none in RCARS</span>}
                                </span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Unique Users</span>
                                <span className="ca-detail-value">{item.unique_users.toLocaleString()}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Experiences</span>
                                <span className="ca-detail-value">{item.experiences.toLocaleString()}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Cost / Provision</span>
                                <span className="ca-detail-value">${item.avg_cost_per_provision.toFixed(2)}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Success</span>
                                <span className="ca-detail-value">{(item.success_ratio * 100).toFixed(1)}%</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Failure</span>
                                <span className="ca-detail-value">{(item.failure_ratio * 100).toFixed(1)}%</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">First Provision</span>
                                <span className="ca-detail-value">{item.first_provision || 'N/A'}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Last Provision</span>
                                <span className="ca-detail-value">{item.last_provision || 'N/A'}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Category</span>
                                <span className="ca-detail-value">{item.category || '—'}</span>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
