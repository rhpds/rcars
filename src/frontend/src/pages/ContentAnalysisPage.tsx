import { useState, useCallback, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Badge, SearchInput, FormSelect, FormSelectOption, Spinner } from '@patternfly/react-core'
import { api } from '../services/api'

interface OverlapItem {
  content_id: string
  display_name: string
  content_type: string
  source: string
  ci_name: string | null
  category: string | null
  stage: string | null
  neighbor_count: number
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
  shared_products: number
  shared_topics: number
  verdict: string | null
  recommendation: string | null
  assessed_at: string | null
}

interface OverlapStats {
  redundant: number
  complementary: number
  differentiated: number
  unassessed: number
  total_pairs: number
  last_computed: string | null
}

interface ItemSummary {
  display_name: string
  ci_name: string
  summary: string | null
  products: string[]
  topics: string[]
}

interface OverlapAssessment {
  verdict: string
  shared_topics: string[]
  differentiators_a: string[]
  differentiators_b: string[]
  recommendation: string
  rationale: string
}

interface DrawerPair {
  item: OverlapItem
  neighbor: NeighborItem
  itemSummary: ItemSummary | null
  neighborSummary: ItemSummary | null
  loading: boolean
  assessment: OverlapAssessment | null
  assessmentLoading: boolean
  assessmentReason: string | null
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

const VERDICT_COLORS: Record<string, { color: string; bg: string }> = {
  redundant: { color: 'var(--score-red)', bg: 'var(--score-red-bg)' },
  complementary: { color: 'var(--score-amber)', bg: 'var(--score-amber-bg)' },
  differentiated: { color: 'var(--score-green, #2e7d32)', bg: 'var(--score-green-bg, #e8f5e9)' },
}

function VerdictBadge({ verdict, onClick, style, title }: {
  verdict: string | null; onClick?: (e: React.MouseEvent) => void; style?: React.CSSProperties; title?: string
}) {
  const colors = VERDICT_COLORS[verdict || ''] || { color: 'var(--text-muted)', bg: 'var(--bg-card)' }
  const sharedStyle = { color: colors.color, backgroundColor: colors.bg, ...style }
  const label = verdict || 'unassessed'
  if (onClick) {
    return (
      <button className="ca-score-badge" style={{ ...sharedStyle, border: 'none', cursor: 'pointer' }}
              onClick={onClick} title={title} aria-label={title || label}>
        {label}
      </button>
    )
  }
  return (
    <span className="ca-score-badge" style={sharedStyle} title={title}>
      {label}
    </span>
  )
}

export function ContentOverlapPage() {
  const [searchParams] = useSearchParams()
  const [items, setItems] = useState<OverlapItem[]>([])
  const [stats, setStats] = useState<OverlapStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [totalItems, setTotalItems] = useState(0)
  const [pageSize, setPageSize] = useState(100)
  const [page, setPage] = useState(1)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [verdict, setVerdict] = useState<string>(searchParams.get('verdict') || '')
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [searchDisplay, setSearchDisplay] = useState(searchParams.get('search') || '')
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [stage, setStage] = useState<string>('')
  const [drawer, setDrawer] = useState<DrawerPair | null>(null)
  const detailCache = useRef<Record<string, ItemSummary>>({})
  const requestRef = useRef(0)

  const loadData = useCallback(async () => {
    const reqId = ++requestRef.current
    setLoading(true)
    setError(null)
    try {
      const data = await api.getOverlapReport({
        verdict: verdict || undefined,
        search: search || undefined,
        stage: stage || undefined,
        page,
      })
      if (reqId !== requestRef.current) return
      setItems(data.items)
      setStats(data.stats)
      setTotalItems(data.total_items)
      setPageSize(data.page_size)
    } catch (e) {
      if (reqId !== requestRef.current) return
      setError(e instanceof Error ? e.message : 'Failed to load overlap data')
    } finally {
      if (reqId === requestRef.current) setLoading(false)
    }
  }, [verdict, search, stage, page])

  useEffect(() => { loadData() }, [loadData])

  const handleVerdictChange = (_e: React.FormEvent, v: string) => {
    setVerdict(v)
    setPage(1)
  }

  const handleSearchChange = (_e: React.FormEvent, v: string) => {
    setSearchDisplay(v)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => { setSearch(v); setPage(1) }, 300)
  }

  useEffect(() => () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current) }, [])

  const handleStageChange = (_e: React.FormEvent, v: string) => {
    setStage(v)
    setPage(1)
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
    setDrawer({ item, neighbor, itemSummary: null, neighborSummary: null, loading: true,
                assessment: null, assessmentLoading: true, assessmentReason: null })

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

    const reqA = item.content_id
    const reqB = neighbor.content_id
    try {
      const resp = await api.getOverlapAssessment(reqA, reqB)
      setDrawer(prev => {
        if (!prev || prev.item.content_id !== reqA || prev.neighbor.content_id !== reqB) return prev
        return { ...prev, assessment: resp.assessment as OverlapAssessment | null, assessmentLoading: false, assessmentReason: resp.reason || null }
      })
    } catch {
      setDrawer(prev => {
        if (!prev || prev.item.content_id !== reqA || prev.neighbor.content_id !== reqB) return prev
        return { ...prev, assessmentLoading: false }
      })
    }
  }

  return (
    <div className="ca-page">
      <div className="ca-header">
        <h1>Content Overlap Detection — <span style={{ fontWeight: 400, fontStyle: 'italic', opacity: 0.7 }}>Preview</span></h1>
        <p className="ca-subtitle">
          {stats?.last_computed
            ? `Last computed ${new Date(stats.last_computed).toLocaleString()}`
            : 'Not yet computed'}
        </p>
      </div>

      {stats && (
        <div className="ca-stats-grid">
          <button className="ca-stat-card ca-stat-red" onClick={() => { setVerdict('redundant'); setPage(1) }} aria-label="Filter by redundant">
            <div className="ca-stat-value">{stats.redundant}</div>
            <div className="ca-stat-label">Redundant</div>
          </button>
          <button className="ca-stat-card ca-stat-amber" onClick={() => { setVerdict('complementary'); setPage(1) }} aria-label="Filter by complementary">
            <div className="ca-stat-value">{stats.complementary}</div>
            <div className="ca-stat-label">Complementary</div>
          </button>
          <button className="ca-stat-card" onClick={() => { setVerdict('differentiated'); setPage(1) }} aria-label="Filter by differentiated">
            <div className="ca-stat-value">{stats.differentiated}</div>
            <div className="ca-stat-label">Differentiated</div>
          </button>
          <button className="ca-stat-card ca-stat-blue" onClick={() => { setVerdict('unassessed'); setPage(1) }} aria-label="Filter by unassessed">
            <div className="ca-stat-value">{stats.unassessed}</div>
            <div className="ca-stat-label">Unassessed</div>
          </button>
        </div>
      )}

      <div className="ca-controls">
        <FormSelect value={verdict} onChange={handleVerdictChange} aria-label="Verdict filter">
          <FormSelectOption value="" label="All verdicts" />
          <FormSelectOption value="redundant" label="Redundant" />
          <FormSelectOption value="complementary" label="Complementary" />
          <FormSelectOption value="differentiated" label="Differentiated" />
          <FormSelectOption value="unassessed" label="Unassessed" />
        </FormSelect>

        <FormSelect value={stage} onChange={handleStageChange} aria-label="Stage filter">
          <FormSelectOption value="" label="All stages" />
          <FormSelectOption value="prod" label="Prod" />
          <FormSelectOption value="event" label="Event" />
          <FormSelectOption value="dev" label="Dev" />
        </FormSelect>

        <SearchInput
          placeholder="Search by name…"
          value={searchDisplay}
          onChange={handleSearchChange}
          onClear={() => { setSearchDisplay(''); setSearch(''); setPage(1) }}
        />
      </div>

      {loading ? (
        <div className="browse-loading"><Spinner size="lg" /> Loading overlap data…</div>
      ) : error ? (
        <div className="browse-loading" style={{ color: 'var(--score-red)' }}>Error: {error}</div>
      ) : items.length === 0 ? (
        <div className="browse-loading">No overlap candidates found{verdict ? ` with verdict "${verdict}"` : ''}.</div>
      ) : (
        <div className="ca-band-sections">
          {items.map(item => (
            <OverlapItemRow
              key={item.content_id}
              item={item}
              expanded={expandedItems.has(item.content_id)}
              onToggle={toggleExpand}
              onCompare={openDrawer}
            />
          ))}
        </div>
      )}

      {totalItems > pageSize && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 0', justifyContent: 'center' }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                  style={{ padding: '4px 12px', cursor: page === 1 ? 'default' : 'pointer' }}>
            ← Prev
          </button>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Page {page} · {totalItems} items
          </span>
          <button onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= totalItems}
                  style={{ padding: '4px 12px', cursor: page * pageSize >= totalItems ? 'default' : 'pointer' }}>
            Next →
          </button>
        </div>
      )}

      {drawer && (
        <ComparisonDrawer drawer={drawer} onClose={() => setDrawer(null)} />
      )}
    </div>
  )
}

function OverlapItemRow({
  item, expanded, onToggle, onCompare,
}: {
  item: OverlapItem
  expanded: boolean
  onToggle: (id: string) => void
  onCompare: (item: OverlapItem, neighbor: NeighborItem) => void
}) {
  return (
    <div className={`browse-item ${expanded ? 'expanded' : ''}`}>
      <div className="browse-item-header" onClick={() => onToggle(item.content_id)}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <span className="browse-item-title">{item.display_name}</span>
          {item.ci_name && <div className="browse-item-ci">{item.ci_name}</div>}
        </div>
        <Badge className="browse-badge">{item.neighbor_count} overlap{item.neighbor_count !== 1 ? 's' : ''}</Badge>
        <span className="browse-expand-icon">{expanded ? '▾' : '▸'}</span>
      </div>
      {expanded && (
        <div className="ca-item-neighbors">
          {item.neighbors.map(n => (
            <div key={n.content_id} className="browse-similar-row">
              <VerdictBadge
                verdict={n.verdict}
                onClick={(e) => { e.stopPropagation(); onCompare(item, n) }}
                style={{ cursor: 'pointer' }}
                title="Compare details"
              />
              <a
                href={`/browse?search=${encodeURIComponent(n.ci_name || n.display_name)}`}
                target="_blank" rel="noopener noreferrer"
                className="browse-similar-name"
              >
                {n.display_name}
              </a>
              <span className="browse-similar-cat" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                {n.shared_products} products · {n.shared_topics} topics
              </span>
              {n.recommendation && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  {n.recommendation.replace('_', ' ')}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ComparisonDrawer({
  drawer, onClose,
}: {
  drawer: DrawerPair
  onClose: () => void
}) {
  return (
    <>
      <div className="browse-drawer-overlay" onClick={onClose} />
      <div className="browse-drawer ca-compare-drawer">
        <div className="browse-drawer-header">
          <div className="browse-drawer-title">
            <VerdictBadge verdict={drawer.neighbor.verdict} style={{ marginRight: '8px' }} />
            Overlap Comparison
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
              <AssessmentSection
                assessment={drawer.assessment}
                loading={drawer.assessmentLoading}
                reason={drawer.assessmentReason}
                itemName={drawer.item.display_name}
                neighborName={drawer.neighbor.display_name}
              />
            </>
          )}
        </div>
      </div>
    </>
  )
}

function AssessmentSection({ assessment, loading, reason, itemName, neighborName }: {
  assessment: OverlapAssessment | null
  loading: boolean
  reason: string | null
  itemName: string
  neighborName: string
}) {
  if (loading) {
    return (
      <div className="ca-assessment-section">
        <div className="browse-drawer-label">LLM Assessment</div>
        <div className="browse-loading"><Spinner size="sm" /> Analyzing overlap…</div>
      </div>
    )
  }
  if (!assessment) {
    return (
      <div className="ca-assessment-section">
        <div className="browse-drawer-label">LLM Assessment</div>
        <p className="ca-compare-summary" style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>
          {reason === 'missing_analysis' ? 'One or both items have not been analyzed yet.' : 'Assessment unavailable.'}
        </p>
      </div>
    )
  }

  const verdictColor: Record<string, string> = {
    redundant: 'var(--score-red)',
    complementary: 'var(--score-amber)',
    differentiated: 'var(--score-green, #2e7d32)',
  }
  const verdictBg: Record<string, string> = {
    redundant: 'var(--score-red-bg)',
    complementary: 'var(--score-amber-bg)',
    differentiated: 'var(--score-green-bg, #e8f5e9)',
  }

  return (
    <div className="ca-assessment-section">
      <div className="ca-assessment-header">
        <span className="browse-drawer-label">LLM Assessment</span>
        <span
          className="ca-score-badge"
          style={{ color: verdictColor[assessment.verdict] || 'inherit',
                   backgroundColor: verdictBg[assessment.verdict] || 'transparent' }}
        >
          {assessment.verdict}
        </span>
      </div>

      {assessment.shared_topics.length > 0 && (
        <div className="ca-assessment-group">
          <div className="ca-assessment-sublabel">Shared Topics</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {assessment.shared_topics.map(t => (
              <Badge key={t} className="browse-badge">{t}</Badge>
            ))}
          </div>
        </div>
      )}

      <div className="ca-assessment-diff-grid">
        {assessment.differentiators_a.length > 0 && (
          <div className="ca-assessment-group">
            <div className="ca-assessment-sublabel">Unique to {itemName}</div>
            <ul className="ca-assessment-list">
              {assessment.differentiators_a.map(d => <li key={d}>{d}</li>)}
            </ul>
          </div>
        )}
        {assessment.differentiators_b.length > 0 && (
          <div className="ca-assessment-group">
            <div className="ca-assessment-sublabel">Unique to {neighborName}</div>
            <ul className="ca-assessment-list">
              {assessment.differentiators_b.map(d => <li key={d}>{d}</li>)}
            </ul>
          </div>
        )}
      </div>

      <div className="ca-assessment-group">
        <div className="ca-assessment-sublabel">
          Recommendation: <strong>{assessment.recommendation.replace('_', ' ')}</strong>
        </div>
        <p className="ca-compare-summary">{assessment.rationale}</p>
      </div>
    </div>
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
      {ciName ? (
        <a href={`/browse?search=${encodeURIComponent(ciName)}`} target="_blank" rel="noopener noreferrer"
           className="ca-compare-name" style={{ textDecoration: 'none', color: 'var(--link-color, #0066cc)' }}>
          {name}
        </a>
      ) : (
        <div className="ca-compare-name">{name}</div>
      )}
      {ciName && <div className="browse-item-ci">{ciName}</div>}
      {summary?.summary ? (
        <p className="ca-compare-summary">{summary.summary}</p>
      ) : (
        <p className="ca-compare-summary" style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>No summary available</p>
      )}
    </div>
  )
}
