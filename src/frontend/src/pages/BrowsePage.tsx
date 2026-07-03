import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams, useLocation } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { Pagination } from '../components/Pagination'
import { WorkloadMultiSelect } from '../components/WorkloadMultiSelect'

function safeHref(url: string | null): string {
  if (!url) return '#'
  try { return ['http:', 'https:'].includes(new URL(url).protocol) ? url : '#' }
  catch { return '#' }
}

/* ── Types ── */

interface CatalogItem {
  ci_name: string
  display_name: string
  category: string
  stage: string
  catalog_namespace: string
  showroom_url: string | null
  scan_status: string
  is_published?: boolean
  is_stale?: boolean
  enrichment_review_needed?: boolean
  is_agd_v2?: boolean
  agd_config?: string | null
  cloud_provider?: string | null
  retired_at?: string | null
}

interface Module {
  title: string
  topics?: string[]
  learning_objectives?: string[]
}

interface LearningObjectives {
  stated?: string[]
  inferred?: string[]
}

interface ItemDetail {
  ci_name: string
  display_name: string
  category: string
  stage: string
  catalog_namespace: string
  showroom_url: string | null
  scan_status: string
  content_path: string | null
  showroom_url_override: string | null
  scan_error_class: string | null
  scan_error: string | null
  scan_failed_at: string | null
  analysis: {
    summary: string | null
    content_type: string | null
    difficulty: string | null
    estimated_duration_min: number | null
    curated_duration_min: number | null
    topics_json: string[] | null
    products_json: string[] | null
    audience_json: string[] | null
    modules_json: Module[] | null
    learning_objectives_json: LearningObjectives | null
    notes: string | null
    is_stale: boolean
    enrichment_review_needed: boolean
  } | null
  tags: Array<{ id: number; tag_type: string; tag_value: string; added_by: string | null }>
  is_agd_v2?: boolean
  agd_config?: string | null
  cloud_provider?: string | null
  ocp_version?: string | null
  os_image?: string | null
  worker_instance_count?: string | null
  control_plane_instance_count?: string | null
  workloads?: Array<{ workload_fqcn: string; workload_role: string; workload_collection: string | null }>
  acl_groups?: string[]
}

interface Facets {
  workloads: Array<{ product_name: string; category: string; ci_count: number }>
  configs: Array<{ agd_config: string; ci_count: number }>
  cloud_providers: Array<{ cloud_provider: string; ci_count: number }>
}

type ContentFilter = 'unanalyzed' | 'scan_failures' | 'stale' | 'needs_review' | 'retired'

const PAGE_SIZE = 50
const OBJECTIVES_PREVIEW_COUNT = 5

/* ── Helpers ── */

function isZtItem(item: CatalogItem): boolean {
  return item.catalog_namespace?.startsWith('zt-') || item.ci_name.startsWith('zt-')
}

function catalogUrl(ciName: string, namespace: string): string {
  return `https://catalog.demo.redhat.com/catalog?item=${namespace}/${ciName}`
}

const CONTENT_FILTER_LABELS: Record<ContentFilter, string> = {
  unanalyzed: 'Unanalyzed',
  scan_failures: 'Failures',
  stale: 'Stale',
  needs_review: 'Needs Review',
  retired: 'Retired',
}

/* ── Sub-components ── */

function StageToggle({ label, active, onToggle }: { label: string; active: boolean; onToggle: () => void }) {
  return (
    <div
      className={`browse-toggle${active ? ' active' : ''}`}
      onClick={onToggle}
      role="switch"
      aria-checked={active}
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle() } }}
    >
      <div className="browse-toggle-track">
        <div className="browse-toggle-knob" />
      </div>
      <span>{label}</span>
    </div>
  )
}

function Badge({ className, children }: { className: string; children: React.ReactNode }) {
  return <span className={`browse-badge ${className}`}>{children}</span>
}

function Pill({ variant, children }: { variant: string; children: React.ReactNode }) {
  return <span className={`browse-pill browse-pill--${variant}`}>{children}</span>
}

function SectionLabel({ color, children }: { color: string; children: React.ReactNode }) {
  return <div className={`browse-section-label browse-section-label--${color}`}>{children}</div>
}

function CollapsibleSection({
  label,
  color,
  count,
  children,
}: {
  label: string
  color: string
  count?: number
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="browse-card-section">
      <div
        className="browse-section-toggle"
        onClick={() => setOpen(!open)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(!open) } }}
      >
        <SectionLabel color={color}>
          <span className="browse-toggle-caret" style={open ? { transform: 'rotate(90deg)' } : undefined}>&#9654;</span>
          {label}
          {count != null && <span className="browse-section-count">{count}</span>}
        </SectionLabel>
      </div>
      {open && <div className="browse-section-body">{children}</div>}
    </div>
  )
}

/* ── Curator Drawer ── */

function CuratorDrawer({
  ciName,
  detail,
  newTag,
  onNewTagChange,
  onAddTag,
  onRemoveTag,
  noteText,
  onNoteChange,
  onNoteSave,
  curatedDuration,
  onDurationChange,
  onDurationSave,
  overrideUrl,
  onOverrideUrlChange,
  onOverrideUrlSave,
  contentPath,
  onContentPathChange,
  onContentPathSave,
  flagged,
  onFlag,
  analyzing,
  onAnalyze,
  onClose,
}: {
  ciName: string
  detail: ItemDetail
  newTag: string
  onNewTagChange: (val: string) => void
  onAddTag: () => void
  onRemoveTag: (tagId: number) => void
  noteText: string
  onNoteChange: (val: string) => void
  onNoteSave: () => void
  curatedDuration: string
  onDurationChange: (val: string) => void
  onDurationSave: () => void
  overrideUrl: string
  onOverrideUrlChange: (val: string) => void
  onOverrideUrlSave: () => void
  contentPath: string
  onContentPathChange: (val: string) => void
  onContentPathSave: () => void
  flagged: boolean
  onFlag: () => void
  analyzing: boolean
  onAnalyze: () => void
  onClose: () => void
}) {
  return (
    <>
      <div className="browse-drawer-overlay" onClick={onClose} />
      <div className="browse-drawer">
        <div className="browse-drawer-header">
          <div className="browse-drawer-title">Edit: {detail.display_name || ciName}</div>
          <button className="browse-drawer-close" onClick={onClose} aria-label="Close drawer">&times;</button>
        </div>
        <div className="browse-drawer-body">
          {/* Tags */}
          <div className="browse-drawer-field">
            <label className="browse-drawer-label">Tags</label>
            <div className="browse-drawer-tags">
              {detail.tags.map(tag => (
                <span
                  key={tag.id}
                  className="browse-pill browse-pill--curator browse-pill--removable"
                  onClick={() => onRemoveTag(tag.id)}
                  title="Click to remove"
                >
                  {tag.tag_value} &times;
                </span>
              ))}
            </div>
            <div className="browse-drawer-tag-input-row">
              <input
                type="text"
                className="browse-drawer-input"
                value={newTag}
                onChange={(e) => onNewTagChange(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') onAddTag() }}
                placeholder="Add tag..."
              />
              <button className="browse-btn-action" onClick={onAddTag}>Add</button>
            </div>
          </div>

          {/* Notes */}
          <div className="browse-drawer-field">
            <label className="browse-drawer-label">Notes</label>
            <textarea
              className="browse-drawer-textarea"
              value={noteText}
              onChange={(e) => onNoteChange(e.target.value)}
              onBlur={onNoteSave}
              placeholder="Add a note..."
              rows={3}
            />
          </div>

          {/* Curated Duration */}
          <div className="browse-drawer-field">
            <label className="browse-drawer-label">Curated Duration (min)</label>
            <input
              type="number"
              className="browse-drawer-input"
              value={curatedDuration}
              onChange={(e) => onDurationChange(e.target.value)}
              onBlur={onDurationSave}
              onKeyDown={(e) => { if (e.key === 'Enter') onDurationSave() }}
              placeholder={detail.analysis?.estimated_duration_min ? `${detail.analysis.estimated_duration_min} (AI)` : 'Duration (min)'}
            />
          </div>

          {/* URL Override */}
          <div className="browse-drawer-field">
            <label className="browse-drawer-label">URL Override</label>
            <div className="browse-drawer-input-row">
              <input
                type="text"
                className="browse-drawer-input"
                value={overrideUrl}
                onChange={(e) => onOverrideUrlChange(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') onOverrideUrlSave() }}
                placeholder="Override Showroom URL..."
              />
              <button className="browse-btn-action" onClick={onOverrideUrlSave}>Set URL</button>
            </div>
          </div>

          {/* Content Path */}
          <div className="browse-drawer-field">
            <label className="browse-drawer-label">Content Path</label>
            <div className="browse-drawer-input-row">
              <input
                type="text"
                className="browse-drawer-input"
                value={contentPath}
                onChange={(e) => onContentPathChange(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') onContentPathSave() }}
                placeholder="Content path (e.g. docs/labs/)"
              />
              <button className="browse-btn-action" onClick={onContentPathSave}>
                Set Path
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="browse-drawer-actions">
            <button
              className="browse-btn-action"
              onClick={onFlag}
              disabled={flagged}
            >
              {flagged ? 'Flagged for review' : 'Flag for review'}
            </button>
            <button
              className="browse-btn-action browse-btn-action--primary"
              onClick={onAnalyze}
              disabled={analyzing}
            >
              {analyzing ? 'Analyzing...' : 'Re-analyze'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

/* ── Main component ── */

export function BrowsePage() {
  const auth = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()

  // Filter state
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [showDev, setShowDev] = useState(searchParams.get('stage')?.includes('dev') || false)
  const [showEvent, setShowEvent] = useState(searchParams.get('stage')?.includes('event') || false)
  const [cloudProvider, setCloudProvider] = useState(searchParams.get('cloud_provider') || '')
  const [agdConfig, setAgdConfig] = useState(searchParams.get('agd_config') || '')
  const [selectedWorkloads, setSelectedWorkloads] = useState<string[]>(
    searchParams.get('workloads')?.split(',').filter(Boolean) || []
  )
  const [contentFilter, setContentFilter] = useState<ContentFilter | ''>(
    (searchParams.get('content_filter') as ContentFilter) || ''
  )
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1)

  useEffect(() => {
    if ((location.state as { reset?: number } | null)?.reset && !searchParams.toString()) {
      setSearch('')
      setShowDev(false)
      setShowEvent(false)
      setCloudProvider('')
      setAgdConfig('')
      setSelectedWorkloads([])
      setContentFilter('')
      setPage(1)
    }
  }, [location.state, searchParams])

  // Data state
  const [items, setItems] = useState<CatalogItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [facets, setFacets] = useState<Facets | null>(null)

  // Expanded card state
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [itemDetails, setItemDetails] = useState<Record<string, ItemDetail>>({})
  const [objectivesExpanded, setObjectivesExpanded] = useState<Set<string>>(new Set())
  const [similarItems, setSimilarItems] = useState<Record<string, Array<{
    ci_name: string; display_name: string; category: string; stage: string
    summary: string | null; similarity_score: number
  }>>>({})
  const [similarLoading, setSimilarLoading] = useState<Set<string>>(new Set())

  // Curator editing state
  const [drawerItem, setDrawerItem] = useState<string | null>(null)
  const [newTags, setNewTags] = useState<Record<string, string>>({})
  const [noteTexts, setNoteTexts] = useState<Record<string, string>>({})
  const [contentPaths, setContentPaths] = useState<Record<string, string>>({})
  const [overrideUrls, setOverrideUrls] = useState<Record<string, string>>({})
  const [curatedDurations, setCuratedDurations] = useState<Record<string, string>>({})
  const [flaggedItems, setFlaggedItems] = useState<Set<string>>(new Set())
  const [analyzing, setAnalyzing] = useState<string | null>(null)

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const searchRef = useRef(search)
  searchRef.current = search

  // Load facets
  useEffect(() => {
    api.getCatalogFacets().then(data => setFacets(data as Facets)).catch(() => {})
  }, [])

  const buildStageString = useCallback(() => {
    const stages = ['prod']
    if (showDev) stages.push('dev')
    if (showEvent) stages.push('event')
    return stages.join(',')
  }, [showDev, showEvent])

  const fetchItems = useCallback(async (targetPage: number, searchOverride?: string) => {
    setLoading(true)
    try {
      const searchVal = searchOverride !== undefined ? searchOverride : searchRef.current
      const params: Record<string, string | number> = {
        stage: buildStageString(),
        limit: PAGE_SIZE,
        offset: (targetPage - 1) * PAGE_SIZE,
      }
      if (searchVal) params.search = searchVal
      if (cloudProvider) params.cloud_provider = cloudProvider
      if (agdConfig) params.agd_config = agdConfig
      if (selectedWorkloads.length > 0) params.workloads = selectedWorkloads.join(',')
      if (contentFilter && contentFilter !== 'retired') params.content_filter = contentFilter
      if (contentFilter === 'retired') (params as Record<string, unknown>).include_retired = 'only'

      const data = await api.listCatalog(params as Parameters<typeof api.listCatalog>[0])
      setItems(data.items as CatalogItem[])
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to load catalog:', err)
    }
    setLoading(false)
  }, [buildStageString, cloudProvider, agdConfig, selectedWorkloads, contentFilter])

  // Sync URL params
  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    const stage = buildStageString()
    if (stage !== 'prod') params.stage = stage
    if (cloudProvider) params.cloud_provider = cloudProvider
    if (agdConfig) params.agd_config = agdConfig
    if (selectedWorkloads.length > 0) params.workloads = selectedWorkloads.join(',')
    if (contentFilter) params.content_filter = contentFilter
    if (page > 1) params.page = String(page)
    setSearchParams(params, { replace: true })
  }, [search, buildStageString, cloudProvider, agdConfig, selectedWorkloads, contentFilter, page, setSearchParams])

  // Fetch on filter change
  useEffect(() => {
    setPage(1)
    fetchItems(1)
  }, [fetchItems])

  // Fetch on page change
  useEffect(() => {
    fetchItems(page)
  }, [page]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearchChange = (value: string) => {
    setSearch(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setPage(1)
      fetchItems(1, value)
    }, 300)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  // Active filter chips
  const activeFilters: Array<{ label: string; onRemove: () => void }> = []
  if (cloudProvider) activeFilters.push({ label: cloudProvider, onRemove: () => setCloudProvider('') })
  if (agdConfig) activeFilters.push({ label: agdConfig, onRemove: () => setAgdConfig('') })
  selectedWorkloads.forEach(wl => {
    activeFilters.push({ label: wl, onRemove: () => setSelectedWorkloads(prev => prev.filter(w => w !== wl)) })
  })
  if (contentFilter) {
    activeFilters.push({ label: CONTENT_FILTER_LABELS[contentFilter], onRemove: () => setContentFilter('') })
  }

  const clearAllFilters = () => {
    setCloudProvider('')
    setAgdConfig('')
    setSelectedWorkloads([])
    setContentFilter('')
  }

  /* ── Expand / collapse ── */

  const handleExpand = async (ciName: string) => {
    const next = new Set(expandedItems)
    if (next.has(ciName)) {
      next.delete(ciName)
      setExpandedItems(next)
      return
    }
    next.add(ciName)
    setExpandedItems(next)
    if (!itemDetails[ciName]) {
      const detail = await api.getCatalogItem(ciName) as ItemDetail
      setItemDetails(prev => ({ ...prev, [ciName]: detail }))
      setNoteTexts(prev => ({ ...prev, [ciName]: detail.analysis?.notes || '' }))
      setContentPaths(prev => ({ ...prev, [ciName]: detail.content_path || '' }))
      setOverrideUrls(prev => ({ ...prev, [ciName]: detail.showroom_url_override || '' }))
      setCuratedDurations(prev => ({
        ...prev,
        [ciName]: detail.analysis?.curated_duration_min != null ? String(detail.analysis.curated_duration_min) : '',
      }))
      if (detail.analysis?.enrichment_review_needed) {
        setFlaggedItems(prev => new Set(prev).add(ciName))
      }
    }
    if (similarItems[ciName] === undefined && !similarLoading.has(ciName)) {
      setSimilarLoading(prev => new Set(prev).add(ciName))
      api.getSimilarItems(ciName).then(data => {
        setSimilarItems(prev => ({ ...prev, [ciName]: data.similar }))
        setSimilarLoading(prev => { const s = new Set(prev); s.delete(ciName); return s })
      }).catch(() => {
        setSimilarItems(prev => ({ ...prev, [ciName]: [] }))
        setSimilarLoading(prev => { const s = new Set(prev); s.delete(ciName); return s })
      })
    }
  }

  /* ── Curator actions ── */

  const handleAnalyze = async (ciName: string) => {
    setAnalyzing(ciName)
    const { job_id } = await api.analyzeSingle(ciName)
    const poll = async () => {
      const result = await api.getJobStatus(job_id)
      if (result.status === 'complete' || result.status === 'failed') {
        setAnalyzing(null)
        fetchItems(page)
        if (expandedItems.has(ciName)) {
          const detail = await api.getCatalogItem(ciName) as ItemDetail
          setItemDetails(prev => ({ ...prev, [ciName]: detail }))
        }
      } else {
        setTimeout(poll, 3000)
      }
    }
    setTimeout(poll, 3000)
  }

  const handleAddTag = async (ciName: string) => {
    const tag = (newTags[ciName] || '').trim()
    if (!tag) return
    await api.addTag(ciName, 'label', tag)
    setNewTags(prev => ({ ...prev, [ciName]: '' }))
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetails(prev => ({ ...prev, [ciName]: detail }))
  }

  const handleRemoveTag = async (ciName: string, tagId: number) => {
    await api.removeTag(ciName, tagId)
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetails(prev => ({ ...prev, [ciName]: detail }))
  }

  const handleSaveNote = async (ciName: string) => {
    await api.setNote(ciName, noteTexts[ciName] || '')
  }

  const handleSetContentPath = async (ciName: string) => {
    const path = contentPaths[ciName]?.trim() || null
    await api.setContentPath(ciName, path)
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetails(prev => ({ ...prev, [ciName]: detail }))
  }

  const handleOverrideUrl = async (ciName: string) => {
    const url = overrideUrls[ciName]?.trim()
    if (!url) return
    await api.overrideUrl(ciName, url)
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetails(prev => ({ ...prev, [ciName]: detail }))
  }

  const handleSetDuration = async (ciName: string) => {
    const val = curatedDurations[ciName]?.trim()
    const durationMin = val ? parseInt(val, 10) : null
    if (val && isNaN(durationMin!)) return
    await api.setCuratedDuration(ciName, durationMin)
  }

  const handleFlag = async (ciName: string) => {
    await api.flagItem(ciName)
    setFlaggedItems(prev => new Set(prev).add(ciName))
    fetchItems(page)
  }

  /* ── Render ── */

  const drawerDetail = drawerItem ? itemDetails[drawerItem] : null

  return (
    <div className="browse-layout">
      {/* ── Top Bar: search + stage toggles + count ── */}
      <div className="browse-toolbar">
        <input
          type="text"
          className="browse-search"
          placeholder="Search by name or CI..."
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
        />
        <div className="browse-toolbar-divider" />
        <StageToggle label="dev" active={showDev} onToggle={() => setShowDev(!showDev)} />
        <StageToggle label="event" active={showEvent} onToggle={() => setShowEvent(!showEvent)} />

        {/* Active filter chips */}
        {activeFilters.length > 0 && (
          <>
            <div className="browse-toolbar-divider" />
            {activeFilters.map(f => (
              <span key={f.label} className="browse-chip" onClick={f.onRemove}>
                {f.label} <span className="browse-chip-x">&times;</span>
              </span>
            ))}
            <button className="browse-chip browse-chip--clear" onClick={clearAllFilters}>
              Clear all
            </button>
          </>
        )}

        <span className="browse-item-count">{total} items</span>
      </div>

      {/* ── Content area: filter sidebar + item list ── */}
      <div className="browse-content">
        {/* Filter sidebar */}
        <div className="browse-filter-sidebar">
          {/* Infrastructure filters — AgnosticD v2 only */}
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Infrastructure</div>
            <div className="browse-filter-group-note">AgnosticD v2 items only</div>
            <select
              className="browse-filter-select"
              value={cloudProvider}
              onChange={(e) => setCloudProvider(e.target.value)}
            >
              <option value="">All cloud providers</option>
              {facets?.cloud_providers.map(cp => (
                <option key={cp.cloud_provider} value={cp.cloud_provider}>{cp.cloud_provider}</option>
              ))}
            </select>
            <WorkloadMultiSelect
              options={facets?.workloads || []}
              selected={selectedWorkloads}
              onChange={setSelectedWorkloads}
            />
            <select
              className="browse-filter-select"
              value={agdConfig}
              onChange={(e) => setAgdConfig(e.target.value)}
            >
              <option value="">All configs</option>
              {facets?.configs.map(c => (
                <option key={c.agd_config} value={c.agd_config}>{c.agd_config}</option>
              ))}
            </select>
          </div>

          {/* Curator filters — curator/admin only */}
          {auth.isCurator && (
            <div className="browse-filter-group">
              <div className="browse-filter-group-label">Curator Tools</div>
              <div className="browse-curator-pills">
                {(['unanalyzed', 'scan_failures', 'stale', 'needs_review', 'retired'] as ContentFilter[]).map(cf => (
                  <button
                    key={cf}
                    className={`browse-curator-pill${contentFilter === cf ? ' active' : ''}`}
                    onClick={() => setContentFilter(contentFilter === cf ? '' : cf)}
                  >
                    {CONTENT_FILTER_LABELS[cf]}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Item list */}
        <div className="browse-list">
        {loading ? (
          <div className="browse-loading">Loading...</div>
        ) : (
          <>
            {items.map(item => {
              const isExpanded = expandedItems.has(item.ci_name)
              const detail = itemDetails[item.ci_name]
              const isZt = isZtItem(item)

              return (
                <div
                  key={item.ci_name}
                  className={`browse-item${isExpanded ? ' expanded' : ''}`}
                  style={item.retired_at ? { opacity: 0.6 } : undefined}
                >
                  {/* ── Row header ── */}
                  <div className="browse-item-header">
                    <div className="browse-item-header-left">
                      <div
                        className="browse-item-title"
                        onClick={() => handleExpand(item.ci_name)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleExpand(item.ci_name) } }}
                      >
                        <span className="browse-expand-icon">{isExpanded ? '▼' : '▶'}</span>
                        {item.display_name || item.ci_name}
                        {item.stage !== 'prod' && (
                          <Badge className={item.stage === 'dev' ? 'badge-dev' : 'badge-event'}>
                            {item.stage.toUpperCase()}
                          </Badge>
                        )}
                        {isZt && <Badge className="badge-zt">ZT</Badge>}
                        {item.is_agd_v2 && <Badge className="badge-v2">v2</Badge>}
                        {item.scan_status === 'failed' && <Badge className="badge-failed">FAILED</Badge>}
                        {item.enrichment_review_needed && <Badge className="badge-review">needs review</Badge>}
                        {item.retired_at && (
                          <Badge className="badge-retired">RETIRED {new Date(item.retired_at).toLocaleDateString()}</Badge>
                        )}
                      </div>
                      <div className="browse-item-ci">{item.ci_name} &middot; {item.category}</div>
                    </div>
                    {auth.isCurator && isExpanded && detail && (
                      <button className="browse-btn-action" onClick={() => setDrawerItem(item.ci_name)}>
                        Edit
                      </button>
                    )}
                  </div>

                  {/* ── Expanded card body ── */}
                  {isExpanded && detail && (
                    <div className="browse-item-body" onClick={(e) => e.stopPropagation()}>
                      {/* Scan Error */}
                      {detail.scan_status === 'failed' && (
                        <div className="browse-scan-error">
                          <div className="browse-scan-error-title">
                            Scan Error{detail.scan_error_class ? `: ${detail.scan_error_class}` : ''}
                          </div>
                          <div className="browse-scan-error-text">
                            {detail.scan_error || 'No error details available'}
                          </div>
                          {detail.scan_failed_at && (
                            <div className="browse-scan-error-time">
                              Failed: {new Date(detail.scan_failed_at).toLocaleString()}
                            </div>
                          )}
                        </div>
                      )}

                      {/* 1. Description */}
                      <div>
                        {detail.analysis?.content_type && (
                          <div className="browse-type-line">
                            <span className="browse-type-val">{detail.analysis.content_type}</span>
                            {detail.analysis.difficulty && (
                              <><span className="browse-type-sep">&middot;</span><span>{detail.analysis.difficulty}</span></>
                            )}
                            {(detail.analysis.curated_duration_min || detail.analysis.estimated_duration_min) && (
                              <><span className="browse-type-sep">&middot;</span><span>
                                ~{detail.analysis.curated_duration_min || detail.analysis.estimated_duration_min} min
                                {detail.analysis.curated_duration_min ? ' (curated)' : ' (AI estimate)'}
                              </span></>
                            )}
                          </div>
                        )}
                        {detail.analysis?.summary && (
                          <p className="browse-description">{detail.analysis.summary}</p>
                        )}
                      </div>

                      {/* 2. Learning Objectives */}
                      {detail.analysis?.learning_objectives_json && (() => {
                        const lo = detail.analysis.learning_objectives_json
                        const allObjectives = [...(lo.stated || []), ...(lo.inferred || [])]
                        if (allObjectives.length === 0) return null
                        const showAll = objectivesExpanded.has(item.ci_name)
                        const visible = showAll ? allObjectives : allObjectives.slice(0, OBJECTIVES_PREVIEW_COUNT)
                        const remaining = allObjectives.length - OBJECTIVES_PREVIEW_COUNT
                        return (
                          <div>
                            <SectionLabel color="blue">Learning Objectives</SectionLabel>
                            <ul className="browse-objectives">
                              {visible.map((obj, i) => <li key={i}>{obj}</li>)}
                            </ul>
                            {remaining > 0 && !showAll && (
                              <button
                                className="browse-objectives-more"
                                onClick={() => setObjectivesExpanded(prev => new Set(prev).add(item.ci_name))}
                              >
                                Show {remaining} more...
                              </button>
                            )}
                            {showAll && allObjectives.length > OBJECTIVES_PREVIEW_COUNT && (
                              <button
                                className="browse-objectives-more"
                                onClick={() => setObjectivesExpanded(prev => { const s = new Set(prev); s.delete(item.ci_name); return s })}
                              >
                                Show less
                              </button>
                            )}
                          </div>
                        )
                      })()}

                      {/* 3. Content Analysis */}
                      {detail.analysis && (detail.analysis.products_json?.length || detail.analysis.topics_json?.length) ? (
                        <div className="browse-card-section">
                          <SectionLabel color="purple">Content Analysis</SectionLabel>
                          {detail.analysis.products_json && detail.analysis.products_json.length > 0 && (
                            <div className="browse-pill-group">
                              <div className="browse-pill-sublabel">Products</div>
                              <div className="browse-pill-row">
                                {detail.analysis.products_json.map((prod, i) => (
                                  <Pill key={i} variant="product">{prod}</Pill>
                                ))}
                              </div>
                            </div>
                          )}
                          {detail.analysis.topics_json && detail.analysis.topics_json.length > 0 && (
                            <div className="browse-pill-group">
                              <div className="browse-pill-sublabel">Topics</div>
                              <div className="browse-pill-row">
                                {detail.analysis.topics_json.map((topic, i) => (
                                  <Pill key={i} variant="topic">{topic}</Pill>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : null}

                      {/* 4. Modules (collapsible) */}
                      {detail.analysis?.modules_json && detail.analysis.modules_json.length > 0 && (
                        <CollapsibleSection
                          label="Modules"
                          color="amber"
                          count={detail.analysis.modules_json.length}
                        >
                          {detail.analysis.modules_json.map((mod, i) => (
                            <div key={i} className="browse-module-item">
                              <div className="browse-module-title">{mod.title}</div>
                              {mod.topics && mod.topics.length > 0 && (
                                <div className="browse-pill-row">
                                  {mod.topics.map((t, ti) => (
                                    <Pill key={ti} variant="module">{t}</Pill>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </CollapsibleSection>
                      )}

                      {/* 5. Infrastructure (collapsible) */}
                      {detail.is_agd_v2 && (
                        <CollapsibleSection label="Infrastructure" color="green">
                          <div className="browse-infra-grid">
                            <span className="browse-infra-kv">Config: <strong>{detail.agd_config || '—'}</strong></span>
                            {detail.cloud_provider && detail.cloud_provider !== 'none' && (
                              <span className="browse-infra-kv">Cloud: <strong>{detail.cloud_provider}</strong></span>
                            )}
                            {detail.ocp_version && (
                              <span className="browse-infra-kv">OCP: <strong>{detail.ocp_version}</strong></span>
                            )}
                            {detail.os_image && (
                              <span className="browse-infra-kv">OS: <strong>{detail.os_image}</strong></span>
                            )}
                            {detail.worker_instance_count && (
                              <span className="browse-infra-kv">Workers: <strong>{detail.worker_instance_count}</strong></span>
                            )}
                            {detail.control_plane_instance_count && (
                              <span className="browse-infra-kv">Control plane: <strong>{detail.control_plane_instance_count}</strong></span>
                            )}
                          </div>
                          {detail.workloads && detail.workloads.length > 0 && (
                            <div className="browse-pill-group">
                              <div className="browse-pill-sublabel">Mapped Workloads ({detail.workloads.length})</div>
                              <div className="browse-pill-row">
                                {detail.workloads.map((w, i) => (
                                  <Pill key={i} variant="workload">{w.workload_role}</Pill>
                                ))}
                              </div>
                            </div>
                          )}
                          {detail.acl_groups && detail.acl_groups.length > 0 && (
                            <div className="browse-infra-access">Access: {detail.acl_groups.join(', ')}</div>
                          )}
                        </CollapsibleSection>
                      )}

                      {/* 6. Similar Content (collapsible) */}
                      {similarItems[item.ci_name] && similarItems[item.ci_name].length > 0 && (
                        <CollapsibleSection
                          label="Similar Content"
                          color="amber"
                          count={similarItems[item.ci_name].length}
                        >
                          {similarItems[item.ci_name].map(sim => (
                            <div key={sim.ci_name} className="browse-similar-row">
                              <span className={`browse-similar-score ${sim.similarity_score >= 0.85 ? 'high' : 'medium'}`}>
                                {Math.round(sim.similarity_score * 100)}%
                              </span>
                              <span
                                className="browse-similar-name"
                                onClick={() => { handleSearchChange(sim.ci_name); window.scrollTo({ top: 0 }) }}
                              >
                                {sim.display_name || sim.ci_name}
                              </span>
                              <span className="browse-similar-cat">{sim.category}</span>
                              {sim.stage !== 'prod' && (
                                <Badge className={sim.stage === 'dev' ? 'badge-dev' : 'badge-event'}>
                                  {sim.stage}
                                </Badge>
                              )}
                            </div>
                          ))}
                        </CollapsibleSection>
                      )}
                      {similarLoading.has(item.ci_name) && (
                        <div className="browse-loading-inline">Loading similar content...</div>
                      )}

                      {/* 7. Curator Tags */}
                      {detail.tags.length > 0 && (
                        <div>
                          <div className="browse-pill-sublabel">Curator Tags</div>
                          <div className="browse-pill-row">
                            {detail.tags.map(tag => (
                              <Pill key={tag.id} variant="curator">{tag.tag_value}</Pill>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* 8. Links */}
                      <div className="browse-links">
                        <a
                          href={catalogUrl(item.ci_name, item.catalog_namespace || 'babylon-catalog-prod')}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          RHDP Catalog
                        </a>
                        {item.showroom_url && (
                          <a href={safeHref(item.showroom_url)} target="_blank" rel="noopener noreferrer">
                            Showroom Repo
                          </a>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}

            <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        )}
      </div>
      </div>{/* end browse-content */}

      {/* ── Curator Drawer ── */}
      {drawerItem && drawerDetail && (
        <CuratorDrawer
          ciName={drawerItem}
          detail={drawerDetail}
          newTag={newTags[drawerItem] || ''}
          onNewTagChange={(val) => setNewTags(prev => ({ ...prev, [drawerItem]: val }))}
          onAddTag={() => handleAddTag(drawerItem)}
          onRemoveTag={(tagId) => handleRemoveTag(drawerItem, tagId)}
          noteText={noteTexts[drawerItem] || ''}
          onNoteChange={(val) => setNoteTexts(prev => ({ ...prev, [drawerItem]: val }))}
          onNoteSave={() => handleSaveNote(drawerItem)}
          curatedDuration={curatedDurations[drawerItem] ?? ''}
          onDurationChange={(val) => setCuratedDurations(prev => ({ ...prev, [drawerItem]: val }))}
          onDurationSave={() => handleSetDuration(drawerItem)}
          overrideUrl={overrideUrls[drawerItem] ?? ''}
          onOverrideUrlChange={(val) => setOverrideUrls(prev => ({ ...prev, [drawerItem]: val }))}
          onOverrideUrlSave={() => handleOverrideUrl(drawerItem)}
          contentPath={contentPaths[drawerItem] ?? ''}
          onContentPathChange={(val) => setContentPaths(prev => ({ ...prev, [drawerItem]: val }))}
          onContentPathSave={() => handleSetContentPath(drawerItem)}
          flagged={flaggedItems.has(drawerItem)}
          onFlag={() => handleFlag(drawerItem)}
          analyzing={analyzing === drawerItem}
          onAnalyze={() => handleAnalyze(drawerItem)}
          onClose={() => setDrawerItem(null)}
        />
      )}
    </div>
  )
}
