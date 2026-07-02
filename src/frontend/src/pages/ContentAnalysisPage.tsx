import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'

// ── Content Overlap Page ──

interface OverlapPair {
  ci_name_a: string; ci_name_b: string; similarity_score: number; computed_at: string
  display_name_a: string; category_a: string; stage_a: string; summary_a: string | null
  display_name_b: string; category_b: string; stage_b: string; summary_b: string | null
}

interface OverlapStats {
  total_pairs: number; high_overlap: number; related: number; last_computed: string | null
}

export function ContentOverlapPage() {
  const [pairs, setPairs] = useState<OverlapPair[]>([])
  const [stats, setStats] = useState<OverlapStats | null>(null)
  const [thresholds, setThresholds] = useState<{ related: number; high_overlap: number }>({ related: 0.75, high_overlap: 0.85 })
  const [loading, setLoading] = useState(true)
  const [computing, setComputing] = useState(false)
  const [expandedPairs, setExpandedPairs] = useState<Set<string>>(new Set())
  const [filterLevel, setFilterLevel] = useState<'all' | 'high'>('all')
  const [stage, setStage] = useState<'prod' | 'event' | 'dev'>('prod')
  const [search, setSearch] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getOverlapReport(thresholds.related, stage)
      setPairs(data.pairs)
      setStats(data.stats)
      setThresholds(data.thresholds)
    } catch { /* ignore */ }
    setLoading(false)
  }, [thresholds.related, stage])

  useEffect(() => { loadData() }, [loadData])

  const handleCompute = async () => {
    setComputing(true)
    try {
      await api.computeSimilarity(thresholds.related, stage)
      loadData()
    } catch (err) {
      console.error('Compute similarity failed:', err)
    }
    setComputing(false)
  }

  const pairKey = (p: OverlapPair) => `${p.ci_name_a}::${p.ci_name_b}`

  const filteredPairs = pairs.filter(p => {
    if (filterLevel === 'high' && p.similarity_score < thresholds.high_overlap) return false
    if (search) {
      const q = search.toLowerCase()
      return (p.display_name_a || p.ci_name_a).toLowerCase().includes(q)
        || (p.display_name_b || p.ci_name_b).toLowerCase().includes(q)
        || p.ci_name_a.toLowerCase().includes(q)
        || p.ci_name_b.toLowerCase().includes(q)
    }
    return true
  })

  const shortTime = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  const scoreColor = (score: number) => score >= thresholds.high_overlap ? 'var(--score-red)' : 'var(--score-amber)'
  const scoreBg = (score: number) => score >= thresholds.high_overlap ? 'var(--score-red-bg)' : 'var(--score-amber-bg)'
  const scorePct = (score: number) => `${Math.round(score * 100)}%`

  return (
    <div className="ca-page">
      <div className="ca-header">
        <h3>Content Overlap Detection</h3>
        {stats?.last_computed && <span className="ca-subtitle" style={{ marginBottom: 0 }}>Last computed: {shortTime(stats.last_computed)}</span>}
      </div>
      <p className="ca-subtitle">
        Pairwise cosine similarity between CI summary embeddings. High overlap ({'≥'}{Math.round(thresholds.high_overlap * 100)}%) suggests near-duplicate content.
      </p>

      {stats && (
        <div className="ca-stats-grid">
          <div className="ca-stat-card">
            <div className="ca-stat-label">Total Pairs</div>
            <div className="ca-stat-value ca-color-blue">{stats.total_pairs}</div>
          </div>
          <div className="ca-stat-card">
            <div className="ca-stat-label">High Overlap</div>
            <div className="ca-stat-value ca-color-red">{stats.high_overlap}</div>
          </div>
          <div className="ca-stat-card">
            <div className="ca-stat-label">Related</div>
            <div className="ca-stat-value ca-color-orange">{stats.related}</div>
          </div>
        </div>
      )}

      <div className="ca-controls">
        <select className="ca-select" value={stage}
          onChange={(e) => setStage(e.target.value as 'prod' | 'event' | 'dev')}>
          <option value="prod">Production</option>
          <option value="event">Event</option>
          <option value="dev">Dev</option>
        </select>
        <button className="ca-compute-btn" onClick={handleCompute} disabled={computing}>
          {computing ? 'Computing...' : 'Compute Similarity'}
        </button>
        <select className="ca-select" value={filterLevel}
          onChange={(e) => setFilterLevel(e.target.value as 'all' | 'high')}>
          <option value="all">All pairs ({pairs.length})</option>
          <option value="high">High overlap only ({pairs.filter(p => p.similarity_score >= thresholds.high_overlap).length})</option>
        </select>
        <input
          type="text" placeholder="Search by name..."
          value={search} onChange={e => setSearch(e.target.value)}
          className="ca-search"
        />
      </div>

      {loading ? (
        <p className="ca-color-muted">Loading...</p>
      ) : filteredPairs.length === 0 ? (
        <p className="ca-color-muted">
          {stats?.total_pairs === 0
            ? 'No similarity data computed yet. Click "Compute Similarity" to analyze content overlap.'
            : 'No pairs match the current filter.'}
        </p>
      ) : (
        <>
          <div className="ca-row-count">{filteredPairs.length} of {pairs.length} pairs</div>
          <div className="ca-table-wrap">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '4px' }}>
              {filteredPairs.map(pair => {
                const key = pairKey(pair)
                const isExpanded = expandedPairs.has(key)
                const isHigh = pair.similarity_score >= thresholds.high_overlap
                return (
                  <div key={key} className={`ca-pair-card${isHigh ? ' ca-pair-card--high' : ''}`}>
                    <div
                      className="ca-pair-header"
                      onClick={() => setExpandedPairs(prev => {
                        const next = new Set(prev)
                        if (next.has(key)) next.delete(key); else next.add(key)
                        return next
                      })}
                    >
                      <span className="ca-score-badge" style={{ background: scoreBg(pair.similarity_score), color: scoreColor(pair.similarity_score), flexShrink: 0 }}>
                        {scorePct(pair.similarity_score)}
                      </span>
                      <span style={{ color: 'var(--text-primary)', fontSize: '0.8rem', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {pair.display_name_a || pair.ci_name_a}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', flexShrink: 0 }}>{'↔'}</span>
                      <span style={{ color: 'var(--text-primary)', fontSize: '0.8rem', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {pair.display_name_b || pair.ci_name_b}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', flexShrink: 0 }}>
                        {isExpanded ? '▾' : '▸'}
                      </span>
                    </div>
                    {isExpanded && (
                      <div className="ca-pair-detail">
                        {[
                          { name: pair.ci_name_a, display: pair.display_name_a, category: pair.category_a, stage: pair.stage_a, summary: pair.summary_a },
                          { name: pair.ci_name_b, display: pair.display_name_b, category: pair.category_b, stage: pair.stage_b, summary: pair.summary_b },
                        ].map((item, i) => (
                          <div key={i} className="ca-pair-detail-item">
                            <a href={`/browse?search=${encodeURIComponent(item.name)}`} target="_blank" rel="noreferrer"
                               onClick={e => e.stopPropagation()}>
                              {item.display || item.name}
                            </a>
                            <div className="ca-pair-detail-meta">
                              {item.name} · {item.category}
                              {item.stage !== 'prod' && (
                                <span className={`ca-env-tag ${item.stage === 'dev' ? 'ca-env-dev' : 'ca-env-event'}`} style={{ marginLeft: '6px' }}>{item.stage}</span>
                              )}
                            </div>
                            {item.summary && (
                              <div className="ca-pair-detail-summary">
                                {item.summary}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
