import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ReportingMetricsItem } from '../services/api'

type SortField = 'retirement_score' | 'provisions' | 'total_cost' | 'closed_amount' | 'touched_amount' | 'display_name'
type ScoreFilter = 'all' | 'high' | 'review' | 'keepers'

const fmt = (n: number) => {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toFixed(0)}`
}

const fmtRoi = (amount: number, cost: number) => {
  if (cost <= 0 || amount <= 0) return '—'
  return `${(amount / cost).toFixed(1)}x`
}

const scoreColor = (score: number) => {
  if (score >= 75) return 'var(--ret-red)'
  if (score >= 50) return 'var(--ret-orange)'
  return 'var(--ret-green)'
}

const scoreBg = (score: number) => {
  if (score >= 75) return 'rgba(233,69,96,0.2)'
  if (score >= 50) return 'rgba(233,138,58,0.2)'
  return 'rgba(78,204,163,0.2)'
}

const stageBadgeClass: Record<string, string> = {
  prod: 'ret-env-prod', event: 'ret-env-event', dev: 'ret-env-dev', test: 'ret-env-test',
}

const CSS = `
  :root {
    --ret-bg: #1a1a2e;
    --ret-surface: #16213e;
    --ret-border: #0f3460;
    --ret-text: #e0e0e0;
    --ret-muted: #8a8a9a;
    --ret-red: #e94560;
    --ret-green: #4ecca3;
    --ret-orange: #e98a3a;
    --ret-yellow: #f0c040;
    --ret-blue: #4a9eff;
  }

  .ret-page { padding: 20px 24px; color: var(--ret-text); height: 100%; display: flex; flex-direction: column; }
  .ret-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
  .ret-header h3 { margin: 0; font-size: 1.3rem; }
  .ret-sync { font-size: 0.8rem; color: var(--ret-muted); }

  .ret-stats { display: flex; gap: 20px; margin-bottom: 12px; font-size: 0.85rem; }
  .ret-stats strong { font-weight: 600; }

  .ret-controls { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; flex-wrap: wrap; }
  .ret-filter-btn {
    padding: 5px 12px; border-radius: 6px; cursor: pointer; font-size: 0.8rem;
    border: 1px solid var(--ret-border); background: transparent; color: var(--ret-text);
  }
  .ret-filter-btn.active { border-color: var(--ret-blue); background: rgba(74,158,255,0.1); }
  .ret-search {
    padding: 6px 12px; border-radius: 6px; margin-left: auto; width: 260px;
    border: 1px solid var(--ret-border); background: var(--ret-surface); color: var(--ret-text);
    font-size: 0.8rem;
  }
  .ret-search:focus { outline: none; border-color: var(--ret-blue); }

  .ret-table-wrap {
    flex: 1; overflow-y: auto; overflow-x: auto;
    border: 1px solid var(--ret-border); border-radius: 8px;
    min-height: 0;
  }

  .ret-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; white-space: nowrap; }

  .ret-table thead th {
    background: var(--ret-surface); color: var(--ret-muted);
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em;
    padding: 10px 12px; text-align: left;
    position: sticky; top: 0; z-index: 2;
    cursor: pointer; user-select: none;
    border-bottom: 2px solid var(--ret-border);
  }
  .ret-table thead th:hover { color: var(--ret-text); }
  .ret-table thead th.num { text-align: right; }

  .ret-table tbody tr { border-bottom: 1px solid rgba(15,52,96,0.5); cursor: pointer; }
  .ret-table tbody tr:hover { background: rgba(74,158,255,0.05); }
  .ret-table tbody tr.ret-expanded-row { background: var(--ret-surface); cursor: default; }
  .ret-table tbody tr.ret-expanded-row:hover { background: var(--ret-surface); }

  .ret-table td { padding: 8px 12px; }
  .ret-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .ret-table td.name { max-width: 420px; overflow: hidden; text-overflow: ellipsis; }
  .ret-table td.name a { color: var(--ret-blue); text-decoration: none; font-weight: 500; }
  .ret-table td.name a:hover { text-decoration: underline; }
  .ret-table td.muted { color: var(--ret-muted); }

  .ret-score-badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-weight: 700; font-size: 0.75rem; min-width: 32px; text-align: center;
  }

  .ret-detail { padding: 12px 16px; display: flex; gap: 24px; flex-wrap: wrap; font-size: 0.8rem; }
  .ret-detail-item { display: flex; flex-direction: column; gap: 2px; }
  .ret-detail-label { color: var(--ret-muted); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.03em; }
  .ret-detail-value { color: var(--ret-text); }

  .ret-env-tag {
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 0.65rem; font-weight: 600; margin-right: 3px;
    text-decoration: none; color: inherit;
  }
  .ret-env-tag:hover { filter: brightness(1.3); outline: 1px solid currentColor; }
  .ret-env-prod { background: rgba(78,204,163,0.25); color: var(--ret-green); }
  .ret-env-event { background: rgba(240,192,64,0.2); color: var(--ret-yellow); }
  .ret-env-dev { background: rgba(74,158,255,0.2); color: var(--ret-blue); }
  .ret-env-test { background: rgba(138,138,154,0.2); color: var(--ret-muted); }

  .ret-row-count { color: var(--ret-muted); font-size: 0.8rem; margin-bottom: 6px; }
`

export function RetirementPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<ReportingMetricsItem[]>([])
  const [summary, setSummary] = useState<{ total: number; high: number; review: number; keepers: number } | null>(null)
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortField>('retirement_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
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
    if (sortBy !== field) return ''
    return sortDir === 'desc' ? ' ▼' : ' ▲'
  }

  const syncAge = syncedAt
    ? `${Math.round((Date.now() - new Date(syncedAt).getTime()) / 3600000)}h ago`
    : 'never'

  return (
    <>
      <style>{CSS}</style>
      <div className="ret-page">
        <div className="ret-header">
          <h3>Retirement Analysis</h3>
          <span className="ret-sync">Last synced: {syncAge}</span>
        </div>

        {summary && (
          <div className="ret-stats">
            <span>Total: <strong>{summary.total}</strong></span>
            <span style={{ color: 'var(--ret-red)' }}>High (&ge;75): <strong>{summary.high}</strong></span>
            <span style={{ color: 'var(--ret-orange)' }}>Review (50-74): <strong>{summary.review}</strong></span>
            <span style={{ color: 'var(--ret-green)' }}>Keepers (&lt;50): <strong>{summary.keepers}</strong></span>
          </div>
        )}

        <div className="ret-controls">
          {(['all', 'high', 'review', 'keepers'] as ScoreFilter[]).map(f => (
            <button key={f} onClick={() => setScoreFilter(f)}
              className={`ret-filter-btn${scoreFilter === f ? ' active' : ''}`}>
              {f === 'all' ? 'All' : f === 'high' ? 'High ≥75' : f === 'review' ? 'Review 50-74' : 'Keepers <50'}
            </button>
          ))}
          <input
            type="text" placeholder="Search by name..."
            value={search} onChange={e => setSearch(e.target.value)}
            className="ret-search"
          />
        </div>

        {loading ? (
          <p style={{ color: 'var(--ret-muted)' }}>Loading...</p>
        ) : (
          <>
            <div className="ret-row-count">Showing {items.length} items</div>
            <div className="ret-table-wrap">
              <table className="ret-table">
                <thead>
                  <tr>
                    <th onClick={() => toggleSort('display_name')}>Name{sortIndicator('display_name')}</th>
                    <th className="num" onClick={() => toggleSort('retirement_score')}>Score{sortIndicator('retirement_score')}</th>
                    <th className="num" onClick={() => toggleSort('provisions')}>Provisions{sortIndicator('provisions')}</th>
                    <th className="num" onClick={() => toggleSort('touched_amount')}>Touched{sortIndicator('touched_amount')}</th>
                    <th className="num">T-ROI</th>
                    <th className="num" onClick={() => toggleSort('closed_amount')}>Closed{sortIndicator('closed_amount')}</th>
                    <th className="num">C-ROI</th>
                    <th className="num" onClick={() => toggleSort('total_cost')}>Cost{sortIndicator('total_cost')}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map(item => {
                    const isExpanded = expanded.has(item.catalog_base_name)
                    return (
                      <>
                        <tr key={item.catalog_base_name} onClick={() => toggleExpand(item.catalog_base_name)}>
                          <td className="name">
                            <a href="#" onClick={e => { e.preventDefault(); e.stopPropagation(); navigate(`/browse?search=${encodeURIComponent(item.display_name)}`) }}
                              title={item.display_name}>
                              {item.display_name}
                            </a>
                          </td>
                          <td className="num">
                            <span className="ret-score-badge" style={{ background: scoreBg(item.retirement_score), color: scoreColor(item.retirement_score) }}>
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
                          <tr key={`${item.catalog_base_name}-detail`} className="ret-expanded-row">
                            <td colSpan={8}>
                              <div className="ret-detail">
                                <div className="ret-detail-item">
                                  <span className="ret-detail-label">Environments</span>
                                  <span className="ret-detail-value">
                                    {item.stages.map(s => (
                                      <a key={s.ci_name} href={s.catalog_url} target="_blank" rel="noreferrer"
                                        className={`ret-env-tag ${stageBadgeClass[s.stage] || 'ret-env-test'}`}>
                                        {s.stage}
                                      </a>
                                    ))}
                                    {item.stages.length === 0 && <span style={{ color: 'var(--ret-muted)' }}>none in RCARS</span>}
                                  </span>
                                </div>
                                <div className="ret-detail-item">
                                  <span className="ret-detail-label">Unique Users</span>
                                  <span className="ret-detail-value">{item.unique_users.toLocaleString()}</span>
                                </div>
                                <div className="ret-detail-item">
                                  <span className="ret-detail-label">Experiences</span>
                                  <span className="ret-detail-value">{item.experiences.toLocaleString()}</span>
                                </div>
                                <div className="ret-detail-item">
                                  <span className="ret-detail-label">Cost / Provision</span>
                                  <span className="ret-detail-value">${item.avg_cost_per_provision.toFixed(2)}</span>
                                </div>
                                <div className="ret-detail-item">
                                  <span className="ret-detail-label">Success</span>
                                  <span className="ret-detail-value">{(item.success_ratio * 100).toFixed(1)}%</span>
                                </div>
                                <div className="ret-detail-item">
                                  <span className="ret-detail-label">Failure</span>
                                  <span className="ret-detail-value">{(item.failure_ratio * 100).toFixed(1)}%</span>
                                </div>
                                <div className="ret-detail-item">
                                  <span className="ret-detail-label">First Provision</span>
                                  <span className="ret-detail-value">{item.first_provision || 'N/A'}</span>
                                </div>
                                <div className="ret-detail-item">
                                  <span className="ret-detail-label">Last Provision</span>
                                  <span className="ret-detail-value">{item.last_provision || 'N/A'}</span>
                                </div>
                                <div className="ret-detail-item">
                                  <span className="ret-detail-label">Category</span>
                                  <span className="ret-detail-value">{item.category || '—'}</span>
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
    </>
  )
}
