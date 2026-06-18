import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { LcarsButton } from '../components/lcars'
import { Pagination } from '../components/Pagination'
import { WorkloadMultiSelect } from '../components/WorkloadMultiSelect'

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

type ContentFilter = 'unanalyzed' | 'scan_failures' | 'stale' | 'needs_review'

const PAGE_SIZE = 50

function isZtItem(item: CatalogItem): boolean {
  return item.catalog_namespace?.startsWith('zt-') || item.ci_name.startsWith('zt-')
}

function LcarsToggle({ label, active, onToggle }: { label: string; active: boolean; onToggle: () => void }) {
  return (
    <div className={`lcars-toggle${active ? ' active' : ''}`} onClick={onToggle}>
      <div className="lcars-toggle-track">
        <div className="lcars-toggle-knob" />
      </div>
      <span>{label}</span>
    </div>
  )
}

function catalogUrl(ciName: string, namespace: string): string {
  return `https://catalog.demo.redhat.com/catalog?item=${namespace}/${ciName}`
}

export function BrowsePage() {
  const auth = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

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
  const [showRetired, setShowRetired] = useState(searchParams.get('include_retired') === 'true')
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1)

  const [items, setItems] = useState<CatalogItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [facets, setFacets] = useState<Facets | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [curatorFiltersOpen, setCuratorFiltersOpen] = useState(false)

  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [itemDetails, setItemDetails] = useState<Record<string, ItemDetail>>({})
  const [newTags, setNewTags] = useState<Record<string, string>>({})
  const [noteTexts, setNoteTexts] = useState<Record<string, string>>({})
  const [contentPaths, setContentPaths] = useState<Record<string, string>>({})
  const [overrideUrls, setOverrideUrls] = useState<Record<string, string>>({})
  const [curatedDurations, setCuratedDurations] = useState<Record<string, string>>({})
  const [scanningPath, setScanningPath] = useState<Record<string, boolean>>({})
  const [flaggedItems, setFlaggedItems] = useState<Set<string>>(new Set())
  const [analyzing, setAnalyzing] = useState<string | null>(null)
  const [similarItems, setSimilarItems] = useState<Record<string, Array<{
    ci_name: string; display_name: string; category: string; stage: string
    summary: string | null; similarity_score: number
  }>>>({})
  const [similarLoading, setSimilarLoading] = useState<Set<string>>(new Set())

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const searchRef = useRef(search)
  searchRef.current = search

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
      if (contentFilter) params.content_filter = contentFilter
      if (showRetired) (params as Record<string, unknown>).include_retired = true

      const data = await api.listCatalog(params as Parameters<typeof api.listCatalog>[0])
      setItems(data.items as CatalogItem[])
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to load catalog:', err)
    }
    setLoading(false)
  }, [buildStageString, cloudProvider, agdConfig, selectedWorkloads, contentFilter, showRetired])

  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    const stage = buildStageString()
    if (stage !== 'prod') params.stage = stage
    if (cloudProvider) params.cloud_provider = cloudProvider
    if (agdConfig) params.agd_config = agdConfig
    if (selectedWorkloads.length > 0) params.workloads = selectedWorkloads.join(',')
    if (contentFilter) params.content_filter = contentFilter
    if (showRetired) params.include_retired = 'true'
    if (page > 1) params.page = String(page)
    setSearchParams(params, { replace: true })
  }, [search, buildStageString, cloudProvider, agdConfig, selectedWorkloads, contentFilter, showRetired, page, setSearchParams])

  useEffect(() => {
    setPage(1)
    fetchItems(1)
  }, [fetchItems])

  useEffect(() => {
    fetchItems(page)
  }, [page])

  const handleSearchChange = (value: string) => {
    setSearch(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setPage(1)
      fetchItems(1, value)
    }, 300)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const activeFilters: Array<{ label: string; onRemove: () => void }> = []
  if (cloudProvider) activeFilters.push({ label: cloudProvider, onRemove: () => setCloudProvider('') })
  if (agdConfig) activeFilters.push({ label: agdConfig, onRemove: () => setAgdConfig('') })
  selectedWorkloads.forEach(wl => {
    activeFilters.push({ label: wl, onRemove: () => setSelectedWorkloads(prev => prev.filter(w => w !== wl)) })
  })
  const hasActiveFilters = activeFilters.length > 0

  const clearAllFilters = () => {
    setCloudProvider('')
    setAgdConfig('')
    setSelectedWorkloads([])
  }

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
        setSimilarLoading(prev => { const next = new Set(prev); next.delete(ciName); return next })
      }).catch(() => {
        setSimilarItems(prev => ({ ...prev, [ciName]: [] }))
        setSimilarLoading(prev => { const next = new Set(prev); next.delete(ciName); return next })
      })
    }
  }

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
    setScanningPath(prev => ({ ...prev, [ciName]: true }))
    await api.setContentPath(ciName, path)
    setTimeout(async () => {
      const detail = await api.getCatalogItem(ciName) as ItemDetail
      setItemDetails(prev => ({ ...prev, [ciName]: detail }))
      setScanningPath(prev => ({ ...prev, [ciName]: false }))
      fetchItems(page)
    }, 5000)
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

  return (
    <div className="curate-layout">
      {/* Primary bar */}
      <div className="filter-bar">
        <input
          className="filter-input"
          placeholder="Search by name or CI..."
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
        />
        <LcarsToggle label="dev" active={showDev} onToggle={() => setShowDev(!showDev)} />
        <LcarsToggle label="event" active={showEvent} onToggle={() => setShowEvent(!showEvent)} />
        <span style={{ color: '#666', fontSize: '14px', alignSelf: 'center' }}>
          {total} items
        </span>
      </div>

      {/* Filter panel */}
      <div className="filter-panel">
        <div className="filter-panel-header" onClick={() => setFiltersOpen(!filtersOpen)}>
          {filtersOpen ? (
            <>
              <span className="filter-panel-label">▾ Filters</span>
              {hasActiveFilters && (
                <button className="filter-panel-clear" onClick={(e) => { e.stopPropagation(); clearAllFilters() }}>
                  Clear all
                </button>
              )}
            </>
          ) : (
            <>
              <span className="filter-panel-label">▸ Filters</span>
              <div className="filter-panel-collapsed">
                {hasActiveFilters ? (
                  <div className="filter-chips">
                    {activeFilters.map(f => (
                      <span key={f.label} className="filter-chip" onClick={(e) => { e.stopPropagation(); f.onRemove() }}>
                        {f.label} ✕
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="filter-panel-muted">no filters active</span>
                )}
                {hasActiveFilters && (
                  <button className="filter-panel-clear" onClick={(e) => { e.stopPropagation(); clearAllFilters() }}>
                    Clear all
                  </button>
                )}
              </div>
            </>
          )}
        </div>
        {filtersOpen && (
          <div className="filter-panel-body">
            <div className="filter-panel-dropdowns">
              <div className="filter-panel-dropdown">
                <div className="filter-panel-dropdown-label">Cloud Provider</div>
                <select
                  className="filter-select"
                  value={cloudProvider}
                  onChange={(e) => setCloudProvider(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="">All providers</option>
                  {facets?.cloud_providers.map(cp => (
                    <option key={cp.cloud_provider} value={cp.cloud_provider}>{cp.cloud_provider}</option>
                  ))}
                </select>
              </div>
              <div className="filter-panel-dropdown">
                <div className="filter-panel-dropdown-label">Workloads</div>
                <WorkloadMultiSelect
                  options={facets?.workloads || []}
                  selected={selectedWorkloads}
                  onChange={setSelectedWorkloads}
                />
              </div>
              <div className="filter-panel-dropdown">
                <div className="filter-panel-dropdown-label">AgnosticD Config</div>
                <select
                  className="filter-select"
                  value={agdConfig}
                  onChange={(e) => setAgdConfig(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="">All configs</option>
                  {facets?.configs.map(c => (
                    <option key={c.agd_config} value={c.agd_config}>{c.agd_config}</option>
                  ))}
                </select>
              </div>
            </div>
            {hasActiveFilters && (
              <div className="filter-chips">
                {activeFilters.map(f => (
                  <span key={f.label} className="filter-chip" onClick={() => f.onRemove()}>
                    {f.label} ✕
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Curator filter panel */}
      {auth.isCurator && (
        <div className="curator-panel">
          <div className="filter-panel-header" onClick={() => setCuratorFiltersOpen(!curatorFiltersOpen)}>
            <span className="filter-panel-label">
              {curatorFiltersOpen ? '▾' : '▸'} Curator Filters
            </span>
            {contentFilter && (
              <button className="filter-panel-clear" onClick={(e) => { e.stopPropagation(); setContentFilter('') }}>
                Clear
              </button>
            )}
          </div>
          {curatorFiltersOpen && (
            <div className="curator-filter-pills">
              {(['unanalyzed', 'scan_failures', 'stale', 'needs_review'] as ContentFilter[]).map(cf => (
                <span
                  key={cf}
                  className={`curator-filter-pill${contentFilter === cf ? ' active' : ''}`}
                  onClick={() => setContentFilter(contentFilter === cf ? '' : cf)}
                >
                  {cf === 'scan_failures' ? 'Failures' : cf === 'needs_review' ? 'Needs Review' :
                   cf.charAt(0).toUpperCase() + cf.slice(1)}
                </span>
              ))}
              <span style={{ marginLeft: '12px', borderLeft: '1px solid #555', paddingLeft: '12px' }}>
                <LcarsToggle label="Show Retired" active={showRetired} onToggle={() => setShowRetired(!showRetired)} />
              </span>
            </div>
          )}
        </div>
      )}

      {/* Results */}
      {loading ? (
        <div style={{ color: '#666', padding: '20px' }}>Loading...</div>
      ) : (
        <>
          {items.map(item => {
            const isExpanded = expandedItems.has(item.ci_name)
            const detail = itemDetails[item.ci_name]
            const isZt = isZtItem(item)

            return (
              <div key={item.ci_name} className="curate-item" style={item.retired_at ? { opacity: 0.6 } : undefined}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div className="curate-item-title" style={{ cursor: 'pointer' }} onClick={() => handleExpand(item.ci_name)}>
                      {isExpanded ? '▾' : '▸'}{' '}
                      {item.display_name || item.ci_name}
                      {item.stage !== 'prod' && (
                        <span style={{ display: 'inline-block', background: item.stage === 'dev' ? '#2a4a6a' : '#5a4a1a', color: item.stage === 'dev' ? '#99ccff' : '#ffcc66', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>{item.stage.toUpperCase()}</span>
                      )}
                      {isZt && <span style={{ display: 'inline-block', background: '#1a3a2a', color: '#66cc99', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>ZT</span>}
                      {item.is_agd_v2 && <span style={{ display: 'inline-block', background: '#1a2a3a', color: '#73bcf7', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>v2</span>}
                      {item.scan_status === 'failed' && <span style={{ display: 'inline-block', background: '#5a2020', color: '#ff9999', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>FAILED</span>}
                      {item.enrichment_review_needed && <span className="review-badge">needs review</span>}
                      {item.retired_at && <span style={{ display: 'inline-block', background: '#3a2a1a', color: '#cc9966', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>RETIRED {new Date(item.retired_at).toLocaleDateString()}</span>}
                    </div>
                    <div className="curate-item-ci">{item.ci_name} · {item.category}</div>
                  </div>
                  {auth.isCurator && (
                    analyzing === item.ci_name ? (
                      <span style={{ color: '#e8a838', fontSize: '13px', padding: '5px 12px', animation: 'pulse-bg 1.5s ease-in-out infinite' }}>Analyzing...</span>
                    ) : (
                      <LcarsButton variant="curator-secondary" onClick={() => handleAnalyze(item.ci_name)}>Re-analyze</LcarsButton>
                    )
                  )}
                </div>

                {isExpanded && detail && (
                  <div style={{ marginTop: '12px' }}>
                    {detail.scan_status === 'failed' && (
                      <div style={{ background: '#2a1515', border: '1px solid #5a2020', borderRadius: '6px', padding: '10px 14px', marginBottom: '12px' }}>
                        <div style={{ fontSize: '12px', color: '#ff9999', fontWeight: 600, marginBottom: '4px' }}>Scan Error{detail.scan_error_class ? `: ${detail.scan_error_class}` : ''}</div>
                        <div style={{ fontSize: '12px', color: '#cc8888', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>{detail.scan_error || 'No error details available'}</div>
                        {detail.scan_failed_at && <div style={{ fontSize: '11px', color: '#666', marginTop: '6px' }}>Failed: {new Date(detail.scan_failed_at).toLocaleString()}</div>}
                      </div>
                    )}
                    {detail.is_agd_v2 && (
                      <div style={{ background: '#111a2a', border: '1px solid #1a3050', borderRadius: '6px', padding: '10px 14px', marginBottom: '12px' }}>
                        <div style={{ fontSize: '11px', color: '#73bcf7', fontWeight: 600, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Infrastructure</div>
                        <div style={{ fontSize: '12px', color: '#ccc', display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '8px' }}>
                          <span>Config: <strong>{detail.agd_config || '—'}</strong></span>
                          {detail.cloud_provider && detail.cloud_provider !== 'none' && <span>Cloud: <strong>{detail.cloud_provider}</strong></span>}
                          {detail.ocp_version && <span>OCP: <strong>{detail.ocp_version}</strong></span>}
                          {detail.os_image && <span>OS: <strong>{detail.os_image}</strong></span>}
                          {detail.worker_instance_count && <span>Workers: <strong>{detail.worker_instance_count}</strong></span>}
                          {detail.control_plane_instance_count && <span>Control plane: <strong>{detail.control_plane_instance_count}</strong></span>}
                        </div>
                        {detail.workloads && detail.workloads.length > 0 && (
                          <div style={{ marginBottom: '6px' }}>
                            <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px' }}>Workloads ({detail.workloads.length})</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                              {detail.workloads.map((w, i) => (
                                <span key={i} style={{ display: 'inline-block', background: '#1a2a1a', color: '#88bb88', border: '1px solid #2a4a2a', borderRadius: '10px', padding: '2px 8px', fontSize: '11px' }}>{w.workload_role}</span>
                              ))}
                            </div>
                          </div>
                        )}
                        {detail.acl_groups && detail.acl_groups.length > 0 && <div style={{ fontSize: '11px', color: '#888' }}>ACL: {detail.acl_groups.join(', ')}</div>}
                      </div>
                    )}
                    {detail.analysis && (
                      <>
                        {detail.analysis.content_type && (
                          <div style={{ fontSize: '12px', color: '#73bcf7', marginBottom: '6px', display: 'flex', gap: '8px' }}>
                            <span>{detail.analysis.content_type}</span>
                            {detail.analysis.difficulty && <span style={{ color: '#888' }}>{detail.analysis.difficulty}</span>}
                            {(detail.analysis.curated_duration_min || detail.analysis.estimated_duration_min) && (
                              <span style={{ color: '#888' }}>
                                ~{detail.analysis.curated_duration_min || detail.analysis.estimated_duration_min} min
                                {detail.analysis.curated_duration_min ? ' (estimated)' : ' (AI estimate)'}
                              </span>
                            )}
                          </div>
                        )}
                        {detail.analysis.summary && <p style={{ fontSize: '12px', color: '#aaa', marginBottom: '10px', lineHeight: '1.5' }}>{detail.analysis.summary}</p>}
                        {detail.analysis.products_json && detail.analysis.products_json.length > 0 && (
                          <div style={{ marginBottom: '6px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {detail.analysis.products_json.map((prod, i) => (
                              <span key={i} style={{ display: 'inline-block', background: '#2a1a3a', color: '#9966CC', border: '1px solid #4a2a6a', borderRadius: '10px', padding: '2px 8px', fontSize: '11px' }}>{prod}</span>
                            ))}
                          </div>
                        )}
                        {detail.analysis.topics_json && detail.analysis.topics_json.length > 0 && (
                          <div style={{ marginBottom: '8px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {detail.analysis.topics_json.map((topic, i) => (
                              <span key={i} style={{ display: 'inline-block', background: '#1a2a3a', color: '#73bcf7', border: '1px solid #2a4a6a', borderRadius: '10px', padding: '2px 8px', fontSize: '11px' }}>{topic}</span>
                            ))}
                          </div>
                        )}
                        {detail.analysis.learning_objectives_json && (() => {
                          const lo = detail.analysis.learning_objectives_json
                          const allObjectives = [...(lo.stated || []), ...(lo.inferred || [])]
                          if (allObjectives.length === 0) return null
                          return (
                            <div style={{ marginBottom: '10px' }}>
                              <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Learning Objectives</div>
                              <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12px', color: '#aaa', lineHeight: '1.6' }}>
                                {allObjectives.map((obj, i) => <li key={i}>{obj}</li>)}
                              </ul>
                            </div>
                          )
                        })()}
                        {detail.analysis.modules_json && detail.analysis.modules_json.length > 0 && (
                          <div style={{ marginBottom: '10px' }}>
                            <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Modules ({detail.analysis.modules_json.length})</div>
                            {detail.analysis.modules_json.map((mod, i) => (
                              <div key={i} style={{ marginBottom: '6px', paddingLeft: '8px', borderLeft: '2px solid #2a2a3a' }}>
                                <div style={{ fontSize: '12px', color: '#ccc', fontWeight: 500 }}>{mod.title}</div>
                                {mod.topics && mod.topics.length > 0 && (
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px', marginTop: '3px' }}>
                                    {mod.topics.map((t, ti) => (
                                      <span key={ti} style={{ display: 'inline-block', background: '#0d1520', color: '#5a9fd4', border: '1px solid #1e3350', borderRadius: '8px', padding: '1px 6px', fontSize: '10px' }}>{t}</span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}

                    {/* Similar Content */}
                    {similarItems[item.ci_name] && similarItems[item.ci_name].length > 0 && (
                      <div style={{ marginBottom: '10px', background: '#111520', border: '1px solid #1e2030', borderRadius: '6px', padding: '10px 14px' }}>
                        <div style={{ fontSize: '11px', color: '#e8a838', fontWeight: 600, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Similar Content ({similarItems[item.ci_name].length})
                        </div>
                        {similarItems[item.ci_name].map(sim => (
                          <div key={sim.ci_name} style={{ display: 'flex', gap: '8px', alignItems: 'baseline', marginBottom: '4px', fontSize: '12px' }}>
                            <span style={{ color: sim.similarity_score >= 0.85 ? '#c9190b' : '#e8a838', fontWeight: 600, width: '36px', textAlign: 'right', flexShrink: 0 }}>
                              {Math.round(sim.similarity_score * 100)}%
                            </span>
                            <span
                              style={{ color: '#73bcf7', cursor: 'pointer' }}
                              onClick={() => { handleSearchChange(sim.ci_name); window.scrollTo({ top: 0 }) }}
                            >
                              {sim.display_name || sim.ci_name}
                            </span>
                            <span style={{ color: '#555' }}>{sim.category}</span>
                            {sim.stage !== 'prod' && (
                              <span style={{ background: sim.stage === 'dev' ? '#2a4a6a' : '#5a4a1a', color: sim.stage === 'dev' ? '#99ccff' : '#ffcc66', borderRadius: '10px', padding: '1px 6px', fontSize: '10px' }}>{sim.stage}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="tag-list" style={{ marginBottom: '8px' }}>
                      {detail.tags.map(tag => (
                        <span key={tag.id} className="tag-pill-removable" onClick={auth.isCurator ? () => handleRemoveTag(item.ci_name, tag.id) : undefined} title={auth.isCurator ? 'Click to remove' : `Added by ${tag.added_by || 'unknown'}`} style={{ cursor: auth.isCurator ? 'pointer' : 'default' }}>
                          {tag.tag_value} {auth.isCurator && '×'}
                        </span>
                      ))}
                      {auth.isCurator && (
                        <input type="text" value={newTags[item.ci_name] || ''} onChange={(e) => setNewTags(prev => ({ ...prev, [item.ci_name]: e.target.value }))} onKeyDown={(e) => { if (e.key === 'Enter') handleAddTag(item.ci_name) }} placeholder="+ add tag" style={{ background: 'transparent', border: '1px dashed #3a5a3a', color: '#5cb85c', padding: '3px 10px', borderRadius: '10px', fontSize: '12px', width: '110px', outline: 'none' }} />
                      )}
                    </div>

                    {auth.isCurator && (
                      <>
                        <input type="text" value={noteTexts[item.ci_name] || ''} onChange={(e) => setNoteTexts(prev => ({ ...prev, [item.ci_name]: e.target.value }))} onBlur={() => handleSaveNote(item.ci_name)} onKeyDown={(e) => { if (e.key === 'Enter') handleSaveNote(item.ci_name) }} placeholder="Add a note..." style={{ background: 'var(--bg-card)', border: '1px solid #333', color: '#aaa', padding: '6px 10px', borderRadius: '4px', fontSize: '13px', width: '100%', fontStyle: 'italic', marginBottom: '8px', outline: 'none' }} />
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                          <input
                            type="number"
                            value={curatedDurations[item.ci_name] ?? ''}
                            onChange={(e) => setCuratedDurations(prev => ({ ...prev, [item.ci_name]: e.target.value }))}
                            onBlur={() => handleSetDuration(item.ci_name)}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleSetDuration(item.ci_name) }}
                            placeholder={detail.analysis?.estimated_duration_min ? `${detail.analysis.estimated_duration_min} (AI)` : 'Duration (min)'}
                            style={{ background: 'var(--bg-card)', border: '1px solid #333', color: '#aaa', padding: '6px 10px', borderRadius: '4px', fontSize: '13px', width: '160px', outline: 'none' }}
                          />
                          <span style={{ fontSize: '12px', color: '#666' }}>Duration (min)</span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                          <input type="text" value={overrideUrls[item.ci_name] ?? ''} onChange={(e) => setOverrideUrls(prev => ({ ...prev, [item.ci_name]: e.target.value }))} onKeyDown={(e) => { if (e.key === 'Enter') handleOverrideUrl(item.ci_name) }} placeholder="Override Showroom URL (full git repo URL)" style={{ background: 'var(--bg-card)', border: '1px solid #333', color: '#aaa', padding: '6px 10px', borderRadius: '4px', fontSize: '13px', flex: 1, outline: 'none' }} />
                          <LcarsButton variant="curator-secondary" onClick={() => handleOverrideUrl(item.ci_name)}>Set URL</LcarsButton>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                          <input type="text" value={contentPaths[item.ci_name] ?? ''} onChange={(e) => setContentPaths(prev => ({ ...prev, [item.ci_name]: e.target.value }))} onKeyDown={(e) => { if (e.key === 'Enter') handleSetContentPath(item.ci_name) }} placeholder="Content path (e.g. docs/labs/)" style={{ background: 'var(--bg-card)', border: '1px solid #333', color: '#aaa', padding: '6px 10px', borderRadius: '4px', fontSize: '13px', flex: 1, outline: 'none' }} />
                          <LcarsButton variant="curator-secondary" onClick={() => handleSetContentPath(item.ci_name)} disabled={scanningPath[item.ci_name]}>{scanningPath[item.ci_name] ? 'Scanning...' : 'Set & Scan'}</LcarsButton>
                        </div>
                        {scanningPath[item.ci_name] && <div style={{ fontSize: '12px', color: '#e8a838', marginBottom: '8px', animation: 'pulse-bg 1.5s ease-in-out infinite' }}>Content path updated — scanning with new path...</div>}
                        <LcarsButton variant="curator-secondary" onClick={() => handleFlag(item.ci_name)} disabled={flaggedItems.has(item.ci_name)}>{flaggedItems.has(item.ci_name) ? '✓ Flagged for review' : 'Flag for review'}</LcarsButton>
                      </>
                    )}

                    <div style={{ marginTop: '10px', fontSize: '13px', display: 'flex', gap: '16px' }}>
                      <a href={catalogUrl(item.ci_name, item.catalog_namespace || 'babylon-catalog-prod')} target="_blank" rel="noopener noreferrer" style={{ color: '#73bcf7' }}>RHDP Catalog</a>
                      {item.showroom_url && <a href={item.showroom_url} target="_blank" rel="noopener noreferrer" style={{ color: '#73bcf7' }}>Showroom Repo</a>}
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
  )
}
