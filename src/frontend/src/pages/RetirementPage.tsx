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
  if (score >= 75) return '#c9190b'
  if (score >= 50) return '#e8a838'
  return '#3e8635'
}

const stageBadgeColor: Record<string, string> = {
  prod: '#3e8635', event: '#0066cc', dev: '#e8a838', test: '#6a6e73',
}

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

  const sortArrow = (field: SortField) => sortBy === field ? (sortDir === 'desc' ? ' ▼' : ' ▲') : ''

  const syncAge = syncedAt
    ? `${Math.round((Date.now() - new Date(syncedAt).getTime()) / 3600000)}h ago`
    : 'never'

  return (
    <div style={{ padding: '1.5rem', color: '#c8ccd0', maxWidth: '100%', overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0 }}>Retirement Analysis</h3>
        <span style={{ fontSize: '0.85rem', color: '#6a6e73' }}>Last synced: {syncAge}</span>
      </div>

      {summary && (
        <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', fontSize: '0.9rem' }}>
          <span>Total: <strong>{summary.total}</strong></span>
          <span style={{ color: '#c9190b' }}>High (&ge;75): <strong>{summary.high}</strong></span>
          <span style={{ color: '#e8a838' }}>Review (50-74): <strong>{summary.review}</strong></span>
          <span style={{ color: '#3e8635' }}>Keepers (&lt;50): <strong>{summary.keepers}</strong></span>
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {(['all', 'high', 'review', 'keepers'] as ScoreFilter[]).map(f => (
          <button key={f} onClick={() => setScoreFilter(f)}
            style={{
              padding: '0.3rem 0.8rem', borderRadius: '4px', cursor: 'pointer',
              border: scoreFilter === f ? '1px solid #e8a838' : '1px solid #2a2d35',
              background: scoreFilter === f ? '#1e2030' : '#0d1117', color: '#c8ccd0',
            }}>
            {f === 'all' ? 'All' : f === 'high' ? 'High ≥75' : f === 'review' ? 'Review 50-74' : 'Keepers <50'}
          </button>
        ))}
        <input
          type="text" placeholder="Search display name..."
          value={search} onChange={e => setSearch(e.target.value)}
          style={{
            padding: '0.3rem 0.6rem', borderRadius: '4px', marginLeft: 'auto',
            border: '1px solid #2a2d35', background: '#0d1117', color: '#c8ccd0', width: '220px',
          }}
        />
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2a2d35', textAlign: 'left' }}>
              <th style={{ padding: '0.5rem', cursor: 'pointer' }} onClick={() => toggleSort('display_name')}>
                Name{sortArrow('display_name')}
              </th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('retirement_score')}>
                Score{sortArrow('retirement_score')}
              </th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('provisions')}>
                Provisions{sortArrow('provisions')}
              </th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('touched_amount')}>
                Touched{sortArrow('touched_amount')}
              </th>
              <th style={{ padding: '0.5rem', textAlign: 'right' }}>T-ROI</th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('closed_amount')}>
                Closed{sortArrow('closed_amount')}
              </th>
              <th style={{ padding: '0.5rem', textAlign: 'right' }}>C-ROI</th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('total_cost')}>
                Cost{sortArrow('total_cost')}
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => {
              const isExpanded = expanded.has(item.catalog_base_name)
              return (
                <tbody key={item.catalog_base_name}>
                  <tr
                    onClick={() => toggleExpand(item.catalog_base_name)}
                    style={{ borderBottom: '1px solid #1a1d25', cursor: 'pointer' }}>
                    <td style={{ padding: '0.5rem', maxWidth: '350px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span onClick={e => { e.stopPropagation(); navigate(`/browse?search=${encodeURIComponent(item.display_name)}`) }}
                        style={{ color: '#58a6ff', cursor: 'pointer' }} title={item.display_name}>
                        {item.display_name}
                      </span>
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>
                      <span style={{ color: scoreColor(item.retirement_score), fontWeight: 'bold' }}>
                        {item.retirement_score}
                      </span>
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>{item.provisions.toLocaleString()}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>{fmt(item.touched_amount)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right', color: '#6a6e73' }}>{fmtRoi(item.touched_amount, item.total_cost)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>{fmt(item.closed_amount)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right', color: '#6a6e73' }}>{fmtRoi(item.closed_amount, item.total_cost)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>{fmt(item.total_cost)}</td>
                  </tr>
                  {isExpanded && (
                    <tr style={{ background: '#0d1117' }}>
                      <td colSpan={8} style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', fontSize: '0.85rem' }}>
                          <div>
                            <strong>Environments:</strong>{' '}
                            {item.stages.map(s => (
                              <a key={s.ci_name} href={s.catalog_url} target="_blank" rel="noreferrer"
                                style={{
                                  display: 'inline-block', padding: '0.15rem 0.5rem', borderRadius: '3px', marginRight: '0.3rem',
                                  background: stageBadgeColor[s.stage] || '#6a6e73', color: '#fff', fontSize: '0.75rem',
                                  textDecoration: 'none',
                                }}>
                                {s.stage}
                              </a>
                            ))}
                            {item.stages.length === 0 && <span style={{ color: '#6a6e73' }}>none in RCARS</span>}
                          </div>
                          <div><strong>Unique Users:</strong> {item.unique_users.toLocaleString()}</div>
                          <div><strong>Experiences:</strong> {item.experiences.toLocaleString()}</div>
                          <div><strong>Cost/Provision:</strong> ${item.avg_cost_per_provision.toFixed(2)}</div>
                          <div><strong>Success:</strong> {(item.success_ratio * 100).toFixed(1)}%</div>
                          <div><strong>Failure:</strong> {(item.failure_ratio * 100).toFixed(1)}%</div>
                          <div><strong>First Provision:</strong> {item.first_provision || 'N/A'}</div>
                          <div><strong>Last Provision:</strong> {item.last_provision || 'N/A'}</div>
                          <div><strong>Category:</strong> {item.category || '—'}</div>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
