import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { LcarsButton } from '../components/lcars'

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
  const navigate = useNavigate()
  const [pairs, setPairs] = useState<OverlapPair[]>([])
  const [stats, setStats] = useState<OverlapStats | null>(null)
  const [thresholds, setThresholds] = useState<{ related: number; high_overlap: number }>({ related: 0.75, high_overlap: 0.85 })
  const [loading, setLoading] = useState(true)
  const [computing, setComputing] = useState(false)
  const [expandedPairs, setExpandedPairs] = useState<Set<string>>(new Set())
  const [filterLevel, setFilterLevel] = useState<'all' | 'high'>('all')
  const [stage, setStage] = useState<'prod' | 'event' | 'dev'>('prod')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getOverlapReport(thresholds.related)
      setPairs(data.pairs)
      setStats(data.stats)
      setThresholds(data.thresholds)
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

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

  const filteredPairs = filterLevel === 'high'
    ? pairs.filter(p => p.similarity_score >= thresholds.high_overlap)
    : pairs

  const shortTime = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  const scoreColor = (score: number) => score >= thresholds.high_overlap ? '#c9190b' : '#e8a838'

  const scorePct = (score: number) => `${Math.round(score * 100)}%`

  return (
    <div className="admin-layout admin-layout--flex">
      <div className="admin-section">
        <h3>Content Overlap Detection</h3>
        <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
          Pairwise cosine similarity between CI summary embeddings. High overlap ({'≥'}{Math.round(thresholds.high_overlap * 100)}%) suggests near-duplicate content. Related ({Math.round(thresholds.related * 100)}%–{Math.round(thresholds.high_overlap * 100)}%) indicates similar topics.
        </p>

        {stats && (
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '12px', fontSize: '13px', flexWrap: 'wrap' }}>
            <span style={{ color: '#c9190b' }}>{stats.high_overlap} high overlap</span>
            <span style={{ color: '#e8a838' }}>{stats.related} related</span>
            <span style={{ color: '#666' }}>{stats.total_pairs} total pairs</span>
            {stats.last_computed && (
              <span style={{ color: '#555', fontSize: '12px' }}>Last computed: {shortTime(stats.last_computed)}</span>
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap' }}>
          <select
            className="filter-select"
            value={stage}
            onChange={(e) => setStage(e.target.value as 'prod' | 'event' | 'dev')}
            style={{ width: 'auto' }}
          >
            <option value="prod">Production</option>
            <option value="event">Event</option>
            <option value="dev">Dev</option>
          </select>
          <LcarsButton onClick={handleCompute} disabled={computing}>
            {computing ? 'Computing...' : 'Compute Similarity'}
          </LcarsButton>
          <select
            className="filter-select"
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value as 'all' | 'high')}
            style={{ width: 'auto' }}
          >
            <option value="all">All pairs ({pairs.length})</option>
            <option value="high">High overlap only ({pairs.filter(p => p.similarity_score >= thresholds.high_overlap).length})</option>
          </select>
        </div>
      </div>

      <div className="admin-section">
        {loading ? (
          <div style={{ color: '#666' }}>Loading...</div>
        ) : filteredPairs.length === 0 ? (
          <div style={{ color: '#666' }}>
            {stats?.total_pairs === 0
              ? 'No similarity data computed yet. Click "Compute Similarity" to analyze content overlap.'
              : 'No pairs match the current filter.'}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {filteredPairs.map(pair => {
              const key = pairKey(pair)
              const isExpanded = expandedPairs.has(key)
              return (
                <div key={key} style={{ background: '#0d1117', borderRadius: '6px', border: `1px solid ${pair.similarity_score >= thresholds.high_overlap ? '#3a1515' : '#1e2030'}` }}>
                  <div
                    style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', gap: '12px', alignItems: 'center' }}
                    onClick={() => setExpandedPairs(prev => {
                      const next = new Set(prev)
                      if (next.has(key)) next.delete(key); else next.add(key)
                      return next
                    })}
                  >
                    <span style={{ color: scoreColor(pair.similarity_score), fontWeight: 700, fontSize: '14px', flexShrink: 0, width: '42px', textAlign: 'right' }}>
                      {scorePct(pair.similarity_score)}
                    </span>
                    <span style={{ color: '#ccc', fontSize: '13px', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {pair.display_name_a || pair.ci_name_a}
                    </span>
                    <span style={{ color: '#555', fontSize: '12px', flexShrink: 0 }}>{'↔'}</span>
                    <span style={{ color: '#ccc', fontSize: '13px', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {pair.display_name_b || pair.ci_name_b}
                    </span>
                    <span style={{ color: '#444', fontSize: '11px', flexShrink: 0 }}>
                      {isExpanded ? '▾' : '▸'}
                    </span>
                  </div>
                  {isExpanded && (
                    <div style={{ padding: '0 14px 14px', borderTop: '1px solid #1e2030', display: 'flex', gap: '16px' }}>
                      {[
                        { name: pair.ci_name_a, display: pair.display_name_a, category: pair.category_a, stage: pair.stage_a, summary: pair.summary_a },
                        { name: pair.ci_name_b, display: pair.display_name_b, category: pair.category_b, stage: pair.stage_b, summary: pair.summary_b },
                      ].map((item, i) => (
                        <div key={i} style={{ flex: 1, paddingTop: '12px' }}>
                          <div style={{ fontSize: '13px', color: '#73bcf7', marginBottom: '4px', cursor: 'pointer' }}
                               onClick={() => navigate(`/browse?search=${encodeURIComponent(item.name)}`)}>
                            {item.display || item.name}
                          </div>
                          <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px' }}>
                            {item.name} · {item.category}
                            {item.stage !== 'prod' && (
                              <span style={{ marginLeft: '6px', background: item.stage === 'dev' ? '#2a4a6a' : '#5a4a1a', color: item.stage === 'dev' ? '#99ccff' : '#ffcc66', borderRadius: '10px', padding: '1px 6px', fontSize: '10px' }}>{item.stage}</span>
                            )}
                          </div>
                          {item.summary && (
                            <div style={{ fontSize: '12px', color: '#888', lineHeight: '1.5' }}>
                              {item.summary.slice(0, 300)}{item.summary.length > 300 ? '...' : ''}
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
        )}
      </div>
    </div>
  )
}
