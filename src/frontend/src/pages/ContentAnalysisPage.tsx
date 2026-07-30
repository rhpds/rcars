import { useState, useCallback, useEffect, useRef } from 'react'
import { Badge, Button, SearchInput, FormSelect, FormSelectOption, Spinner } from '@patternfly/react-core'
import { api } from '../services/api'

interface OverlapItem {
  content_id: string
  display_name: string
  content_type: string
  source: string
  ci_name: string | null
  category: string | null
  stage: string | null
  max_score: number
  neighbor_count: number
  score_band: string
  neighbors: Array<NeighborItem>
}

interface NeighborItem {
  content_id: string
  display_name: string
  content_type: string
  source: string
  ci_name: string | null
  category: string | null
  stage: string | null
  similarity_score: number
}

interface OverlapStats {
  near_duplicates: number
  high_overlap: number
  related_band: number
  total_pairs_stored: number
  last_computed: string | null
}

interface ItemSummary {
  display_name: string
  ci_name: string
  summary: string | null
  products: string[]
  topics: string[]
}

interface DrawerPair {
  item: OverlapItem
  neighbor: NeighborItem
  itemSummary: ItemSummary | null
  neighborSummary: ItemSummary | null
  loading: boolean
}

function extractSummary(detail: Record<string, unknown>): ItemSummary {
  const analysis = (detail.analysis || {}) as Record<string, unknown>
  const products = analysis.products_json as Array<{ name?: string }> | string[] | null
  const topics = analysis.topics_json as string[] | null
  return {
    display_name: (detail.display_name as string) || '',
    ci_name: (detail.ci_name as string) || '',
    summary: (analysis.summary as string) || null,
    products: products
      ? products.map(p => typeof p === 'string' ? p : (p.name || ''))
      : [],
    topics: topics || [],
  }
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
  const [drawer, setDrawer] = useState<DrawerPair | null>(null)
  const detailCache = useRef<Record<string, ItemSummary>>({})

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

  const openDrawer = async (item: OverlapItem, neighbor: NeighborItem) => {
    setDrawer({ item, neighbor, itemSummary: null, neighborSummary: null, loading: true })

    const fetchSummary = async (contentId: string): Promise<ItemSummary> => {
      if (detailCache.current[contentId]) return detailCache.current[contentId]
      const detail = await api.getCatalogItem(contentId) as Record<string, unknown>
      const summary = extractSummary(detail)
      detailCache.current[contentId] = summary
      return summary
    }

    try {
      const [itemSummary, neighborSummary] = await Promise.all([
        fetchSummary(item.content_id),
        fetchSummary(neighbor.content_id),
      ])
      setDrawer(prev => prev ? { ...prev, itemSummary, neighborSummary, loading: false } : null)
    } catch {
      setDrawer(prev => prev ? { ...prev, loading: false } : null)
    }
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
          {nearDupes.length > 0 && (
            <details open className="ca-band-section">
              <summary className="ca-band-header ca-band-red">
                Near-Duplicates ({nearDupes.length}) · ≥ {scorePct(thresholds.near_duplicate)}
              </summary>
              {nearDupes.map(item => (
                <OverlapItemRow
                  key={item.content_id}
                  item={item}
                  expanded={expandedItems.has(item.content_id)}
                  onToggle={toggleExpand}
                  onCompare={openDrawer}
                  scoreColor={scoreColor}
                  scoreBg={scoreBg}
                  scorePct={scorePct}
                />
              ))}
            </details>
          )}

          {highOverlap.length > 0 && (
            <details open className="ca-band-section">
              <summary className="ca-band-header ca-band-amber">
                High Overlap ({highOverlap.length}) · {scorePct(thresholds.display)}–{scorePct(thresholds.near_duplicate - 0.01)}
              </summary>
              {highOverlap.map(item => (
                <OverlapItemRow
                  key={item.content_id}
                  item={item}
                  expanded={expandedItems.has(item.content_id)}
                  onToggle={toggleExpand}
                  onCompare={openDrawer}
                  scoreColor={scoreColor}
                  scoreBg={scoreBg}
                  scorePct={scorePct}
                />
              ))}
            </details>
          )}

          {relatedBand.length > 0 && (
            <details className="ca-band-section">
              <summary className="ca-band-header ca-band-muted">
                Related ({relatedBand.length}) · 75%–84%
              </summary>
              {relatedBand.map(item => (
                <OverlapItemRow
                  key={item.content_id}
                  item={item}
                  expanded={expandedItems.has(item.content_id)}
                  onToggle={toggleExpand}
                  onCompare={openDrawer}
                  scoreColor={scoreColor}
                  scoreBg={scoreBg}
                  scorePct={scorePct}
                />
              ))}
            </details>
          )}

          {items.length === 0 && (
            <div className="browse-loading">No items found above {scorePct(minScore)} similarity.</div>
          )}
        </div>
      )}

      {drawer && (
        <ComparisonDrawer drawer={drawer} onClose={() => setDrawer(null)} scorePct={scorePct} scoreColor={scoreColor} scoreBg={scoreBg} />
      )}
    </div>
  )
}

function OverlapItemRow({
  item, expanded, onToggle, onCompare, scoreColor, scoreBg, scorePct,
}: {
  item: OverlapItem
  expanded: boolean
  onToggle: (id: string) => void
  onCompare: (item: OverlapItem, neighbor: NeighborItem) => void
  scoreColor: (s: number) => string
  scoreBg: (s: number) => string
  scorePct: (s: number) => string
}) {
  return (
    <div className={`browse-item ${expanded ? 'expanded' : ''}`}>
      <div className="browse-item-header" onClick={() => onToggle(item.content_id)}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <span className="browse-item-title">{item.display_name}</span>
          {item.ci_name && <div className="browse-item-ci">{item.ci_name}</div>}
        </div>
        <Badge className="browse-badge">{item.content_type}</Badge>
        {item.category && <span className="browse-similar-cat">{item.category}</span>}
        {item.stage && item.stage !== 'prod' && (
          <Badge className={item.stage === 'dev' ? 'badge-dev' : 'badge-event'}>{item.stage}</Badge>
        )}
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
                className="ca-score-badge ca-score-clickable"
                style={{ color: scoreColor(n.similarity_score), backgroundColor: scoreBg(n.similarity_score), cursor: 'pointer' }}
                onClick={(e) => { e.stopPropagation(); onCompare(item, n) }}
                title="Compare summaries"
              >
                {scorePct(n.similarity_score)}
              </span>
              <a
                href={`/browse?search=${encodeURIComponent(n.ci_name || n.display_name)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="browse-similar-name"
              >
                {n.display_name}
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ComparisonDrawer({
  drawer, onClose, scorePct, scoreColor, scoreBg,
}: {
  drawer: DrawerPair
  onClose: () => void
  scorePct: (s: number) => string
  scoreColor: (s: number) => string
  scoreBg: (s: number) => string
}) {
  const score = drawer.neighbor.similarity_score
  return (
    <>
      <div className="browse-drawer-overlay" onClick={onClose} />
      <div className="browse-drawer ca-compare-drawer">
        <div className="browse-drawer-header">
          <div className="browse-drawer-title">
            <span
              className="ca-score-badge"
              style={{ color: scoreColor(score), backgroundColor: scoreBg(score), marginRight: '8px' }}
            >
              {scorePct(score)}
            </span>
            Similarity Comparison
          </div>
          <button className="browse-drawer-close" onClick={onClose} aria-label="Close drawer">&times;</button>
        </div>
        <div className="browse-drawer-body">
          {drawer.loading ? (
            <div className="browse-loading"><Spinner size="md" /> Loading summaries…</div>
          ) : (
            <>
              <SummarySection
                label="This item"
                name={drawer.item.display_name}
                ciName={drawer.item.ci_name}
                summary={drawer.itemSummary}
              />
              <SummarySection
                label="Compared to"
                name={drawer.neighbor.display_name}
                ciName={drawer.neighbor.ci_name}
                summary={drawer.neighborSummary}
              />
            </>
          )}
        </div>
      </div>
    </>
  )
}

function SummarySection({ label, name, ciName, summary }: {
  label: string
  name: string
  ciName: string | null
  summary: ItemSummary | null
}) {
  return (
    <div className="ca-compare-section">
      <div className="browse-drawer-label">{label}</div>
      <div className="ca-compare-name">{name}</div>
      {ciName && <div className="browse-item-ci">{ciName}</div>}
      {summary?.summary ? (
        <p className="ca-compare-summary">{summary.summary}</p>
      ) : (
        <p className="ca-compare-summary" style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>No summary available</p>
      )}
      {summary && summary.products.length > 0 && (
        <div className="ca-compare-tags">
          <span className="browse-drawer-label">Products</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
            {summary.products.map(p => (
              <Badge key={p} className="browse-badge">{p}</Badge>
            ))}
          </div>
        </div>
      )}
      {summary && summary.topics.length > 0 && (
        <div className="ca-compare-tags">
          <span className="browse-drawer-label">Topics</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
            {summary.topics.map(t => (
              <Badge key={t} className="browse-badge">{t}</Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
