import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { LcarsButton } from '../components/lcars'

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
  scan_error_class: string | null
  scan_error: string | null
  scan_failed_at: string | null
  analysis: {
    summary: string | null
    content_type: string | null
    difficulty: string | null
    estimated_duration_min: number | null
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
}

type ContentFilter = 'all' | 'has_showroom' | 'analyzed' | 'unanalyzed' | 'needs_review' | 'untagged' | 'scan_failures' | 'stale'

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
  const [searchParams] = useSearchParams()
  const [allItems, setAllItems] = useState<CatalogItem[]>([])
  const [search, setSearch] = useState('')
  const [showDev, setShowDev] = useState(false)
  const [showEvent, setShowEvent] = useState(false)
  const [showZt, setShowZt] = useState(true)
  const initialFilter = (searchParams.get('filter') as ContentFilter) || 'all'
  const [contentFilter, setContentFilter] = useState<ContentFilter>(initialFilter)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [itemDetails, setItemDetails] = useState<Record<string, ItemDetail>>({})
  const [newTags, setNewTags] = useState<Record<string, string>>({})
  const [noteTexts, setNoteTexts] = useState<Record<string, string>>({})
  const [contentPaths, setContentPaths] = useState<Record<string, string>>({})
  const [scanningPath, setScanningPath] = useState<Record<string, boolean>>({})
  const [flaggedItems, setFlaggedItems] = useState<Set<string>>(new Set())
  const [analyzing, setAnalyzing] = useState<string | null>(null)
  const limit = 50

  const loadItems = async () => {
    setLoading(true)
    try {
      const data = await api.listCatalog({ limit: 1000 })
      setAllItems(data.items as CatalogItem[])
    } catch (err) {
      console.error('Failed to load catalog:', err)
    }
    setLoading(false)
  }

  useEffect(() => { loadItems() }, [])

  const filteredItems = allItems.filter(item => {
    if (item.stage === 'dev' && !showDev) return false
    if (item.stage === 'event' && !showEvent) return false
    if (!showZt && isZtItem(item)) return false
    if (search) {
      const q = search.toLowerCase()
      if (!(item.display_name || '').toLowerCase().includes(q) &&
          !item.ci_name.toLowerCase().includes(q)) return false
    }
    switch (contentFilter) {
      case 'has_showroom': if (!item.showroom_url) return false; break
      case 'analyzed': if (item.scan_status !== 'success') return false; break
      case 'unanalyzed': if (!item.showroom_url || item.is_published || item.scan_status === 'success' || item.scan_status === 'failed') return false; break
      case 'needs_review': if (!item.enrichment_review_needed) return false; break
      case 'scan_failures': if (item.scan_status !== 'failed') return false; break
      case 'stale': if (!item.is_stale) return false; break
    }
    return true
  })

  const total = filteredItems.length
  const ztCount = allItems.filter(isZtItem).length
  const pageItems = filteredItems.slice(offset, offset + limit)

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
      if (detail.analysis?.enrichment_review_needed) {
        setFlaggedItems(prev => new Set(prev).add(ciName))
      }
    }
  }

  const handleAnalyze = async (ciName: string) => {
    setAnalyzing(ciName)
    const { job_id } = await api.analyzeSingle(ciName)
    const poll = async () => {
      const result = await api.getJobStatus(job_id)
      if (result.status === 'complete' || result.status === 'failed') {
        setAnalyzing(null)
        loadItems()
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
      loadItems()
    }, 5000)
  }

  const handleFlag = async (ciName: string) => {
    await api.flagItem(ciName)
    setFlaggedItems(prev => new Set(prev).add(ciName))
    loadItems()
  }

  return (
    <div className="curate-layout">
      <div className="filter-bar">
        <input
          className="filter-input"
          placeholder="Search by name or CI..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
        />
        <select
          className="filter-select"
          value={contentFilter}
          onChange={(e) => { setContentFilter(e.target.value as ContentFilter); setOffset(0) }}
        >
          <option value="all">All items</option>
          <option value="has_showroom">Has Showroom</option>
          <option value="analyzed">Analyzed</option>
          <option value="unanalyzed">Unanalyzed</option>
          <option value="needs_review">Needs review</option>
          <option value="untagged">Untagged</option>
          <option value="scan_failures">Analysis failures</option>
          <option value="stale">Stale (needs re-analysis)</option>
        </select>
        <LcarsToggle label="dev" active={showDev} onToggle={() => { setShowDev(!showDev); setOffset(0) }} />
        <LcarsToggle label="event" active={showEvent} onToggle={() => { setShowEvent(!showEvent); setOffset(0) }} />
        <LcarsToggle label={`ZT (${ztCount})`} active={showZt} onToggle={() => { setShowZt(!showZt); setOffset(0) }} />
        <span style={{ color: '#666', fontSize: '14px', alignSelf: 'center' }}>
          {total} items
        </span>
      </div>

      {loading ? (
        <div style={{ color: '#666', padding: '20px' }}>Loading...</div>
      ) : (
        <>
          {pageItems.map(item => {
            const isExpanded = expandedItems.has(item.ci_name)
            const detail = itemDetails[item.ci_name]
            const isZt = isZtItem(item)

            return (
              <div key={item.ci_name} className="curate-item">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div
                      className="curate-item-title"
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleExpand(item.ci_name)}
                    >
                      {isExpanded ? '▾' : '▸'}{' '}
                      {item.display_name || item.ci_name}
                      {item.stage !== 'prod' && (
                        <span style={{
                          display: 'inline-block',
                          background: item.stage === 'dev' ? '#2a4a6a' : '#5a4a1a',
                          color: item.stage === 'dev' ? '#99ccff' : '#ffcc66',
                          borderRadius: '10px', padding: '2px 8px', fontSize: '10px',
                          fontWeight: 600, marginLeft: '6px',
                        }}>{item.stage.toUpperCase()}</span>
                      )}
                      {isZt && (
                        <span style={{ display: 'inline-block', background: '#1a3a2a', color: '#66cc99', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>ZT</span>
                      )}
                      {item.scan_status === 'failed' && (
                        <span style={{ display: 'inline-block', background: '#5a2020', color: '#ff9999', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>FAILED</span>
                      )}
                      {item.enrichment_review_needed && (
                        <span className="review-badge">needs review</span>
                      )}
                    </div>
                    <div className="curate-item-ci">{item.ci_name} · {item.category}</div>
                  </div>
                  {auth.isCurator && (
                    analyzing === item.ci_name ? (
                      <span style={{
                        color: '#e8a838', fontSize: '13px', padding: '5px 12px',
                        animation: 'pulse-bg 1.5s ease-in-out infinite',
                      }}>
                        Analyzing...
                      </span>
                    ) : (
                      <LcarsButton
                        variant="curator-secondary"
                        onClick={() => handleAnalyze(item.ci_name)}
                      >
                        Re-analyze
                      </LcarsButton>
                    )
                  )}
                </div>

                {isExpanded && detail && (
                  <div style={{ marginTop: '12px' }}>
                    {detail.scan_status === 'failed' && (
                      <div style={{ background: '#2a1515', border: '1px solid #5a2020', borderRadius: '6px', padding: '10px 14px', marginBottom: '12px' }}>
                        <div style={{ fontSize: '12px', color: '#ff9999', fontWeight: 600, marginBottom: '4px' }}>
                          Scan Error{detail.scan_error_class ? `: ${detail.scan_error_class}` : ''}
                        </div>
                        <div style={{ fontSize: '12px', color: '#cc8888', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                          {detail.scan_error || 'No error details available'}
                        </div>
                        {detail.scan_failed_at && (
                          <div style={{ fontSize: '11px', color: '#666', marginTop: '6px' }}>
                            Failed: {new Date(detail.scan_failed_at).toLocaleString()}
                          </div>
                        )}
                      </div>
                    )}
                    {detail.analysis && (
                      <>
                        {detail.analysis.content_type && (
                          <div style={{ fontSize: '12px', color: '#73bcf7', marginBottom: '6px', display: 'flex', gap: '8px' }}>
                            <span>{detail.analysis.content_type}</span>
                            {detail.analysis.difficulty && <span style={{ color: '#888' }}>{detail.analysis.difficulty}</span>}
                            {detail.analysis.estimated_duration_min && <span style={{ color: '#888' }}>~{detail.analysis.estimated_duration_min} min</span>}
                          </div>
                        )}
                        {detail.analysis.summary && (
                          <p style={{ fontSize: '12px', color: '#aaa', marginBottom: '10px', lineHeight: '1.5' }}>
                            {detail.analysis.summary}
                          </p>
                        )}

                        {/* Products */}
                        {detail.analysis.products_json && detail.analysis.products_json.length > 0 && (
                          <div style={{ marginBottom: '6px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {detail.analysis.products_json.map((prod, i) => (
                              <span key={i} style={{
                                display: 'inline-block', background: '#2a1a3a',
                                color: '#9966CC', border: '1px solid #4a2a6a',
                                borderRadius: '10px', padding: '2px 8px', fontSize: '11px',
                              }}>{prod}</span>
                            ))}
                          </div>
                        )}

                        {/* Topics */}
                        {detail.analysis.topics_json && detail.analysis.topics_json.length > 0 && (
                          <div style={{ marginBottom: '8px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {detail.analysis.topics_json.map((topic, i) => (
                              <span key={i} style={{
                                display: 'inline-block', background: '#1a2a3a',
                                color: '#73bcf7', border: '1px solid #2a4a6a',
                                borderRadius: '10px', padding: '2px 8px', fontSize: '11px',
                              }}>{topic}</span>
                            ))}
                          </div>
                        )}

                        {/* Learning Objectives */}
                        {detail.analysis.learning_objectives_json && (
                          (() => {
                            const lo = detail.analysis.learning_objectives_json
                            const allObjectives = [...(lo.stated || []), ...(lo.inferred || [])]
                            if (allObjectives.length === 0) return null
                            return (
                              <div style={{ marginBottom: '10px' }}>
                                <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Learning Objectives</div>
                                <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12px', color: '#aaa', lineHeight: '1.6' }}>
                                  {allObjectives.map((obj, i) => (
                                    <li key={i}>{obj}</li>
                                  ))}
                                </ul>
                              </div>
                            )
                          })()
                        )}

                        {/* Modules */}
                        {detail.analysis.modules_json && detail.analysis.modules_json.length > 0 && (
                          <div style={{ marginBottom: '10px' }}>
                            <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Modules ({detail.analysis.modules_json.length})</div>
                            {detail.analysis.modules_json.map((mod, i) => (
                              <div key={i} style={{ marginBottom: '6px', paddingLeft: '8px', borderLeft: '2px solid #2a2a3a' }}>
                                <div style={{ fontSize: '12px', color: '#ccc', fontWeight: 500 }}>{mod.title}</div>
                                {mod.topics && mod.topics.length > 0 && (
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px', marginTop: '3px' }}>
                                    {mod.topics.map((t, ti) => (
                                      <span key={ti} style={{
                                        display: 'inline-block', background: '#0d1520',
                                        color: '#5a9fd4', border: '1px solid #1e3350',
                                        borderRadius: '8px', padding: '1px 6px', fontSize: '10px',
                                      }}>{t}</span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}

                    {/* Curator tags */}
                    <div className="tag-list" style={{ marginBottom: '8px' }}>
                      {detail.tags.map(tag => (
                        <span
                          key={tag.id}
                          className="tag-pill-removable"
                          onClick={auth.isCurator ? () => handleRemoveTag(item.ci_name, tag.id) : undefined}
                          title={auth.isCurator ? 'Click to remove' : `Added by ${tag.added_by || 'unknown'}`}
                          style={{ cursor: auth.isCurator ? 'pointer' : 'default' }}
                        >
                          {tag.tag_value} {auth.isCurator && '×'}
                        </span>
                      ))}
                      {auth.isCurator && (
                        <input
                          type="text"
                          value={newTags[item.ci_name] || ''}
                          onChange={(e) => setNewTags(prev => ({ ...prev, [item.ci_name]: e.target.value }))}
                          onKeyDown={(e) => { if (e.key === 'Enter') handleAddTag(item.ci_name) }}
                          placeholder="+ add tag"
                          style={{
                            background: 'transparent', border: '1px dashed #3a5a3a',
                            color: '#5cb85c', padding: '3px 10px', borderRadius: '10px',
                            fontSize: '12px', width: '110px', outline: 'none',
                          }}
                        />
                      )}
                    </div>

                    {/* Curator controls */}
                    {auth.isCurator && (
                      <>
                        <input
                          type="text"
                          value={noteTexts[item.ci_name] || ''}
                          onChange={(e) => setNoteTexts(prev => ({ ...prev, [item.ci_name]: e.target.value }))}
                          onBlur={() => handleSaveNote(item.ci_name)}
                          onKeyDown={(e) => { if (e.key === 'Enter') handleSaveNote(item.ci_name) }}
                          placeholder="Add a note..."
                          style={{
                            background: 'var(--bg-card)', border: '1px solid #333',
                            color: '#aaa', padding: '6px 10px', borderRadius: '4px',
                            fontSize: '13px', width: '100%', fontStyle: 'italic',
                            marginBottom: '8px', outline: 'none',
                          }}
                        />
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                          <input
                            type="text"
                            value={contentPaths[item.ci_name] ?? ''}
                            onChange={(e) => setContentPaths(prev => ({ ...prev, [item.ci_name]: e.target.value }))}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleSetContentPath(item.ci_name) }}
                            placeholder="Content path (e.g. docs/labs/)"
                            style={{
                              background: 'var(--bg-card)', border: '1px solid #333',
                              color: '#aaa', padding: '6px 10px', borderRadius: '4px',
                              fontSize: '13px', flex: 1, outline: 'none',
                            }}
                          />
                          <LcarsButton
                            variant="curator-secondary"
                            onClick={() => handleSetContentPath(item.ci_name)}
                            disabled={scanningPath[item.ci_name]}
                          >
                            {scanningPath[item.ci_name] ? 'Scanning...' : 'Set & Scan'}
                          </LcarsButton>
                        </div>
                        {scanningPath[item.ci_name] && (
                          <div style={{ fontSize: '12px', color: '#e8a838', marginBottom: '8px', animation: 'pulse-bg 1.5s ease-in-out infinite' }}>
                            Content path updated — scanning with new path...
                          </div>
                        )}
                        <LcarsButton
                          variant="curator-secondary"
                          onClick={() => handleFlag(item.ci_name)}
                          disabled={flaggedItems.has(item.ci_name)}
                        >
                          {flaggedItems.has(item.ci_name) ? '✓ Flagged for review' : 'Flag for review'}
                        </LcarsButton>
                      </>
                    )}

                    {/* Links */}
                    <div style={{ marginTop: '10px', fontSize: '13px', display: 'flex', gap: '16px' }}>
                      <a
                        href={catalogUrl(item.ci_name, item.catalog_namespace || 'babylon-catalog-prod')}
                        target="_blank" rel="noopener noreferrer"
                        style={{ color: '#73bcf7' }}
                      >
                        RHDP Catalog
                      </a>
                      {item.showroom_url && (
                        <a href={item.showroom_url} target="_blank" rel="noopener noreferrer" style={{ color: '#73bcf7' }}>
                          Showroom Repo
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          {total > limit && (
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginTop: '20px' }}>
              <button className="btn-action" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
                Previous
              </button>
              <span style={{ color: '#666', alignSelf: 'center', fontSize: '14px' }}>
                {offset + 1}-{Math.min(offset + limit, total)} of {total}
              </span>
              <button className="btn-action" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
