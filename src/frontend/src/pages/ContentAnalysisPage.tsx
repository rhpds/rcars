import { useState, useCallback, useEffect } from 'react'
import { Badge, Button, SearchInput, FormSelect, FormSelectOption, Spinner } from '@patternfly/react-core'
import { api } from '../services/api'

interface OverlapItem {
  content_id: string
  display_name: string
  content_type: string
  source: string
  category: string | null
  stage: string | null
  max_score: number
  neighbor_count: number
  score_band: string
  neighbors: Array<{
    content_id: string
    display_name: string
    content_type: string
    source: string
    category: string | null
    stage: string | null
    similarity_score: number
  }>
}

interface OverlapStats {
  near_duplicates: number
  high_overlap: number
  related_band: number
  total_pairs_stored: number
  last_computed: string | null
}

export function ContentOverlapPage() {
  const [items, setItems] = useState<OverlapItem[]>([])
  const [stats, setStats] = useState<OverlapStats | null>(null)
  const [thresholds, setThresholds] = useState({ display: 0.85, near_duplicate: 0.95 })
  const [loading, setLoading] = useState(true)
  const [computing, setComputing] = useState(false)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [minScore, setMinScore] = useState(0.85)
  const [stage, setStage] = useState<string>('prod')
  const [search, setSearch] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getOverlapReport(
        minScore,
        stage || undefined,
        search || undefined,
      )
      setItems(data.items)
      setStats(data.stats)
      setThresholds(data.thresholds)
    } finally {
      setLoading(false)
    }
  }, [minScore, stage, search])

  useEffect(() => { loadData() }, [loadData])

  const handleCompute = async () => {
    setComputing(true)
    try {
      await api.computeSimilarity(0.75, stage || undefined)
      await loadData()
    } finally {
      setComputing(false)
    }
  }

  const toggleExpand = (contentId: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      if (next.has(contentId)) next.delete(contentId)
      else next.add(contentId)
      return next
    })
  }

  const scoreColor = (score: number) =>
    score >= thresholds.near_duplicate ? 'var(--score-red)' : 'var(--score-amber)'
  const scoreBg = (score: number) =>
    score >= thresholds.near_duplicate ? 'var(--score-red-bg)' : 'var(--score-amber-bg)'
  const scorePct = (score: number) => `${Math.round(score * 100)}%`

  const bandItems = (band: string) => items.filter(i => i.score_band === band)
  const nearDupes = bandItems('near_duplicate')
  const highOverlap = bandItems('high_overlap')
  const relatedBand = bandItems('related')

  return (
    <div className="ca-page">
      <div className="ca-header">
        <h1>Content Overlap Detection</h1>
        <p className="ca-subtitle">
          {stats?.last_computed
            ? `Last computed ${new Date(stats.last_computed).toLocaleString()}`
            : 'Not yet computed'}
          {' · '}Items with similarity ≥ {scorePct(minScore)}
        </p>
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="ca-stats-grid">
          <div className="ca-stat-card ca-stat-red">
            <div className="ca-stat-value">{stats.near_duplicates}</div>
            <div className="ca-stat-label">Near-Duplicates</div>
            <div className="ca-stat-desc">≥ {scorePct(thresholds.near_duplicate)}</div>
          </div>
          <div className="ca-stat-card ca-stat-amber">
            <div className="ca-stat-value">{stats.high_overlap}</div>
            <div className="ca-stat-label">High Overlap</div>
            <div className="ca-stat-desc">{scorePct(thresholds.display)}–{scorePct(thresholds.near_duplicate - 0.01)}</div>
          </div>
          <div className="ca-stat-card ca-stat-blue">
            <div className="ca-stat-value">{stats.total_pairs_stored}</div>
            <div className="ca-stat-label">Total Pairs Stored</div>
            <div className="ca-stat-desc">≥ 75%</div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="ca-controls">
        <FormSelect value={stage} onChange={(_e, v) => setStage(v)} aria-label="Stage filter">
          <FormSelectOption value="prod" label="prod" />
          <FormSelectOption value="dev" label="dev" />
        </FormSelect>

        <FormSelect
          value={String(minScore)}
          onChange={(_e, v) => setMinScore(parseFloat(v))}
          aria-label="Min score"
        >
          <FormSelectOption value="0.95" label="≥ 95% (near-duplicates)" />
          <FormSelectOption value="0.85" label="≥ 85% (high overlap)" />
          <FormSelectOption value="0.75" label="≥ 75% (all stored)" />
        </FormSelect>

        <SearchInput
          placeholder="Search by name…"
          value={search}
          onChange={(_e, v) => setSearch(v)}
          onClear={() => setSearch('')}
        />

        <Button
          variant="secondary"
          size="sm"
          isLoading={computing}
          onClick={handleCompute}
        >
          {computing ? 'Computing…' : 'Refresh Similarity'}
        </Button>
      </div>

      {loading ? (
        <div className="browse-loading"><Spinner size="lg" /> Loading overlap data…</div>
      ) : (
        <div className="ca-band-sections">
          {/* Near-Duplicates */}
          {nearDupes.length > 0 && (
            <details open className="ca-band-section">
              <summary className="ca-band-header ca-band-red">
                Near-Duplicates ({nearDupes.length}) · ≥ {scorePct(thresholds.near_duplicate)}
              </summary>
              {nearDupes.map(item => renderItem(item, expandedItems, toggleExpand, scoreColor, scoreBg, scorePct))}
            </details>
          )}

          {/* High Overlap */}
          {highOverlap.length > 0 && (
            <details open className="ca-band-section">
              <summary className="ca-band-header ca-band-amber">
                High Overlap ({highOverlap.length}) · {scorePct(thresholds.display)}–{scorePct(thresholds.near_duplicate - 0.01)}
              </summary>
              {highOverlap.map(item => renderItem(item, expandedItems, toggleExpand, scoreColor, scoreBg, scorePct))}
            </details>
          )}

          {/* Related band — only when threshold < 0.85 */}
          {relatedBand.length > 0 && (
            <details className="ca-band-section">
              <summary className="ca-band-header ca-band-muted">
                Related ({relatedBand.length}) · 75%–84%
              </summary>
              {relatedBand.map(item => renderItem(item, expandedItems, toggleExpand, scoreColor, scoreBg, scorePct))}
            </details>
          )}

          {items.length === 0 && (
            <div className="browse-loading">No items found above {scorePct(minScore)} similarity.</div>
          )}
        </div>
      )}
    </div>
  )
}

function renderItem(
  item: OverlapItem,
  expandedItems: Set<string>,
  toggleExpand: (id: string) => void,
  scoreColor: (s: number) => string,
  scoreBg: (s: number) => string,
  scorePct: (s: number) => string,
) {
  const expanded = expandedItems.has(item.content_id)
  return (
    <div key={item.content_id} className={`browse-item ${expanded ? 'expanded' : ''}`}>
      <div className="browse-item-header" onClick={() => toggleExpand(item.content_id)}>
        <span className="browse-item-title">{item.display_name}</span>
        <Badge className="browse-badge">{item.content_type}</Badge>
        {item.category && <span className="browse-similar-cat">{item.category}</span>}
        {item.stage && item.stage !== 'prod' && (
          <Badge className={item.stage === 'dev' ? 'badge-dev' : 'badge-event'}>{item.stage}</Badge>
        )}
        <span style={{ flex: 1 }} />
        <Badge className="browse-badge">{item.neighbor_count} similar</Badge>
        <span
          className="ca-score-badge"
          style={{ color: scoreColor(item.max_score), backgroundColor: scoreBg(item.max_score) }}
        >
          {scorePct(item.max_score)}
        </span>
        <span className="browse-expand-icon">{expanded ? '▾' : '▸'}</span>
      </div>
      {expanded && (
        <div className="ca-item-neighbors">
          {item.neighbors.map(n => (
            <div key={n.content_id} className="browse-similar-row">
              <span
                className="ca-score-badge"
                style={{ color: scoreColor(n.similarity_score), backgroundColor: scoreBg(n.similarity_score) }}
              >
                {scorePct(n.similarity_score)}
              </span>
              <a href={`/browse?search=${encodeURIComponent(n.display_name)}`} className="browse-similar-name">
                {n.display_name}
              </a>
              <Badge className="browse-badge">{n.content_type}</Badge>
              {n.category && <span className="browse-similar-cat">{n.category}</span>}
              {n.stage && n.stage !== 'prod' && (
                <Badge className={n.stage === 'dev' ? 'badge-dev' : 'badge-event'}>{n.stage}</Badge>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
