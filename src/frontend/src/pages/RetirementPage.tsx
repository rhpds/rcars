import { useState, useEffect, useCallback, Fragment } from 'react'
import { api, ReportingMetricsItem } from '../services/api'

type SortField = 'retirement_score' | 'provisions' | 'total_cost' | 'closed_amount' | 'touched_amount' | 'display_name'
type ScoreFilter = 'all' | 'high' | 'review' | 'keepers'
type AgeFilter = 'all' | 'old' | 'med' | 'new'
type RetirementTab = 'prod' | 'no-prod'
type TimeWindow = '1q' | '2q' | '3q' | '1y'

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

const scoreColor = (score: number) => score >= 55 ? '#e94560' : score >= 35 ? '#e98a3a' : '#4ecca3'
const scoreBg = (score: number) => score >= 55 ? 'rgba(233,69,96,0.2)' : score >= 35 ? 'rgba(233,138,58,0.2)' : 'rgba(78,204,163,0.2)'

const stageBadgeClass: Record<string, string> = {
  prod: 'ca-env-prod', event: 'ca-env-event', dev: 'ca-env-dev', test: 'ca-env-test',
}

const ageDays = (dateStr: string | null): number | null => {
  if (!dateStr) return null
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
}

const ageColor = (days: number | null) => {
  if (days === null) return '#666'
  if (days > 365) return '#e94560'
  if (days > 180) return '#e98a3a'
  return '#888'
}

export function RetirementPage() {
  const [tab, setTab] = useState<RetirementTab>('prod')
  const [items, setItems] = useState<ReportingMetricsItem[]>([])
  const [allItems, setAllItems] = useState<ReportingMetricsItem[]>([])
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortField>('retirement_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>('all')
  const [ageFilter, setAgeFilter] = useState<AgeFilter>('all')
  const [search, setSearch] = useState('')
  const [window, setWindow] = useState<TimeWindow>('1y')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const minScore = scoreFilter === 'high' ? 55 : scoreFilter === 'review' ? 35 : scoreFilter === 'keepers' ? 0 : undefined
      const maxForKeepers = scoreFilter === 'keepers'
      const data = await api.getRetirementDashboard({
        sort_by: tab === 'prod' ? sortBy : 'provisions',
        sort_dir: tab === 'prod' ? sortDir : 'desc',
        min_score: tab === 'prod' ? minScore : undefined,
        has_prod: tab === 'prod' ? true : false,
        search: search || undefined,
        window: tab === 'prod' ? window : undefined,
      })
      let filtered = data.items
      if (tab === 'prod' && maxForKeepers) {
        filtered = filtered.filter(i => i.retirement_score < 35)
      } else if (tab === 'prod' && scoreFilter === 'review') {
        filtered = filtered.filter(i => i.retirement_score < 55)
      }
      setItems(filtered)
      setAllItems(data.items)
      setSyncedAt(data.synced_at)
    } finally {
      setLoading(false)
    }
  }, [tab, sortBy, sortDir, scoreFilter, search, window])

  useEffect(() => { loadData() }, [loadData])

  useEffect(() => {
    setExpanded(new Set())
    setScoreFilter('all')
    setAgeFilter('all')
    setSearch('')
    setSortBy(tab === 'prod' ? 'retirement_score' : 'provisions')
    setSortDir(tab === 'prod' ? 'asc' : 'desc')
  }, [tab])

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
  const prodHigh = allItems.filter(i => i.retirement_score >= 55).length
  const prodReview = allItems.filter(i => i.retirement_score >= 35 && i.retirement_score < 55).length
  const prodKeepers = allItems.filter(i => i.retirement_score < 35).length

  const noProdOld = allItems.filter(i => {
    const d = ageDays(i.first_provision)
    return d !== null && d > 365
  }).length
  const noProdMed = allItems.filter(i => {
    const d = ageDays(i.first_provision)
    return d !== null && d > 180 && d <= 365
  }).length
  const noProdNew = allItems.length - noProdOld - noProdMed

  return (
    <div className="ca-page">
      <div className="ca-header">
        <h3>Retirement Analysis</h3>
        <span className="ca-subtitle" style={{ marginBottom: 0 }}>Last synced: {syncAge}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
        <p className="ca-subtitle" style={{ margin: 0 }}>Retirement scoring based on provisions, sales, cost, and catalog presence.</p>
        {tab === 'prod' && (
          <div className="ca-controls" style={{ margin: 0, padding: 0 }}>
            {([['1q', '1 Quarter'], ['2q', '2 Quarters'], ['3q', '3 Quarters'], ['1y', '1 Year']] as [TimeWindow, string][]).map(([w, label]) => (
              <button key={w} onClick={() => setWindow(w)}
                className={`ca-filter-btn${window === w ? ' active' : ''}`}
                style={{ fontSize: '11px', padding: '3px 8px' }}>
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ca-tab-bar" style={{ marginBottom: '12px' }}>
        <button className={`ca-tab-btn${tab === 'prod' ? ' active' : ''}`} onClick={() => setTab('prod')}>Prod Retirements</button>
        <button className={`ca-tab-btn${tab === 'no-prod' ? ' active' : ''}`} onClick={() => setTab('no-prod')}>Without Prod</button>
      </div>

      {tab === 'prod' ? (
        <>
          {allItems.length > 0 && (
            <div className="ca-stats-grid">
              <div className="ca-stat-card">
                <div className="ca-stat-label">Total Assets</div>
                <div className="ca-stat-value ca-color-blue">{allItems.length}</div>
              </div>
              <div className="ca-stat-card">
                <div className="ca-stat-label">High Retirement</div>
                <div className="ca-stat-value ca-color-red">{prodHigh}</div>
              </div>
              <div className="ca-stat-card">
                <div className="ca-stat-label">Review</div>
                <div className="ca-stat-value ca-color-orange">{prodReview}</div>
              </div>
              <div className="ca-stat-card">
                <div className="ca-stat-label">Keepers</div>
                <div className="ca-stat-value ca-color-green">{prodKeepers}</div>
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
                {f === 'all' ? 'All' : f === 'high' ? 'High ≥55' : f === 'review' ? 'Review 35-54' : 'Keepers <35'}
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
              <div className="ca-row-count">{items.length} of {allItems.length} assets</div>
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
                        <Fragment key={item.catalog_base_name}>
                          <tr className="clickable" onClick={() => toggleExpand(item.catalog_base_name)}>
                            <td className="name" title={item.display_name}>{item.display_name}</td>
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
                            <tr className="ca-expanded-row">
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
                                      {!item.has_content && item.catalog_url && (
                                        <a href={item.catalog_url} target="_blank" rel="noreferrer"
                                          className="ca-env-tag" style={{ background: 'rgba(150,150,150,0.2)', color: '#999', border: '1px solid #555' }}
                                          onClick={e => e.stopPropagation()}>
                                          catalog
                                        </a>
                                      )}
                                      {item.has_content && item.stages.length === 0 && <span className="ca-color-muted">none</span>}
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
                        </Fragment>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      ) : (
        <>
          <div className="ca-stats-grid">
            <div className="ca-stat-card">
              <div className="ca-stat-label">Without Prod</div>
              <div className="ca-stat-value ca-color-blue">{allItems.length}</div>
            </div>
            <div className="ca-stat-card">
              <div className="ca-stat-label">&gt; 1 Year</div>
              <div className="ca-stat-value ca-color-red">{noProdOld}</div>
            </div>
            <div className="ca-stat-card">
              <div className="ca-stat-label">6-12 Months</div>
              <div className="ca-stat-value ca-color-orange">{noProdMed}</div>
            </div>
            <div className="ca-stat-card">
              <div className="ca-stat-label">&lt; 6 Months</div>
              <div className="ca-stat-value ca-color-green">{noProdNew}</div>
            </div>
          </div>

          <div className="ca-controls">
            {([['all', 'All'], ['old', '> 1 Year'], ['med', '6-12 Mo'], ['new', '< 6 Mo']] as [AgeFilter, string][]).map(([f, label]) => (
              <button key={f} onClick={() => setAgeFilter(f)}
                className={`ca-filter-btn${ageFilter === f ? ' active' : ''}`}>
                {label}
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
          ) : (() => {
            const filtered = ageFilter === 'all' ? items : items.filter(i => {
              const d = ageDays(i.first_provision)
              if (ageFilter === 'old') return d !== null && d > 365
              if (ageFilter === 'med') return d !== null && d > 180 && d <= 365
              return d === null || d <= 180
            })
            return (
            <>
              <div className="ca-row-count">{filtered.length} of {items.length} items without production deployment</div>
              <div className="ca-table-wrap">
                <table className="ca-table">
                  <thead>
                    <tr>
                      <th style={{ width: '40%' }}>Name</th>
                      <th style={{ width: '12%' }}>Stages</th>
                      <th style={{ width: '12%' }}>First Provision</th>
                      <th style={{ width: '12%' }}>Last Provision</th>
                      <th className="num" style={{ width: '10%' }}>Provisions</th>
                      <th className="num" style={{ width: '10%' }}>Age (days)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map(item => {
                      const age = ageDays(item.first_provision)
                      const isExpanded = expanded.has(item.catalog_base_name)
                      return (
                        <Fragment key={item.catalog_base_name}>
                          <tr className="clickable" onClick={() => toggleExpand(item.catalog_base_name)}>
                            <td className="name" title={item.display_name}>{item.display_name}</td>
                            <td>
                              {item.stages.map(s => (
                                <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(s.ci_name)}`} target="_blank" rel="noreferrer"
                                  className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                                  style={{ marginRight: 4 }} onClick={e => e.stopPropagation()}>
                                  {s.stage}
                                </a>
                              ))}
                              {item.stages.length === 0 && <span className="ca-color-muted">—</span>}
                            </td>
                            <td>{item.first_provision || '—'}</td>
                            <td>{item.last_provision || '—'}</td>
                            <td className="num">{item.provisions.toLocaleString()}</td>
                            <td className="num" style={{ color: ageColor(age), fontWeight: age && age > 365 ? 600 : 400 }}>
                              {age !== null ? age : '—'}
                            </td>
                          </tr>
                          {isExpanded && (
                            <tr className="ca-expanded-row">
                              <td colSpan={6}>
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
                                    <span className="ca-detail-label">Catalog Name</span>
                                    <span className="ca-detail-value">{item.catalog_base_name}</span>
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
                                    <span className="ca-detail-label">Total Cost</span>
                                    <span className="ca-detail-value">{fmt(item.total_cost)}</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Category</span>
                                    <span className="ca-detail-value">{item.category || '—'}</span>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
            )
          })()}
        </>
      )}
    </div>
  )
}
