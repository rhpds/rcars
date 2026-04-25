import { useState, useEffect } from 'react'
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
  enrichment_review_needed?: boolean
}

interface ItemDetail {
  ci_name: string
  display_name: string
  category: string
  stage: string
  catalog_namespace: string
  showroom_url: string | null
  analysis: {
    summary: string | null
    content_type: string | null
    difficulty: string | null
    estimated_duration_min: number | null
    topics_json: string[] | null
    products_json: string[] | null
    audience_json: string[] | null
    notes: string | null
    is_stale: boolean
    enrichment_review_needed: boolean
  } | null
  tags: Array<{ id: number; tag_type: string; tag_value: string; added_by: string | null }>
}

type ContentFilter = 'all' | 'has_showroom' | 'analyzed' | 'needs_review' | 'untagged' | 'scan_failures'

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
  const [allItems, setAllItems] = useState<CatalogItem[]>([])
  const [search, setSearch] = useState('')
  const [showDev, setShowDev] = useState(false)
  const [showEvent, setShowEvent] = useState(false)
  const [contentFilter, setContentFilter] = useState<ContentFilter>('all')
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expandedItem, setExpandedItem] = useState<string | null>(null)
  const [itemDetail, setItemDetail] = useState<ItemDetail | null>(null)
  const [newTag, setNewTag] = useState('')
  const [noteText, setNoteText] = useState('')
  const [flagged, setFlagged] = useState(false)
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
    if (search) {
      const q = search.toLowerCase()
      if (!(item.display_name || '').toLowerCase().includes(q) &&
          !item.ci_name.toLowerCase().includes(q)) return false
    }
    switch (contentFilter) {
      case 'has_showroom': if (!item.showroom_url) return false; break
      case 'analyzed': if (item.scan_status !== 'success') return false; break
      case 'needs_review': if (!item.enrichment_review_needed) return false; break
      case 'scan_failures': if (item.scan_status !== 'failed') return false; break
    }
    return true
  })

  const total = filteredItems.length
  const pageItems = filteredItems.slice(offset, offset + limit)

  const handleExpand = async (ciName: string) => {
    if (expandedItem === ciName) {
      setExpandedItem(null)
      setItemDetail(null)
      return
    }
    setExpandedItem(ciName)
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetail(detail)
    setNoteText(detail.analysis?.notes || '')
    setFlagged(detail.analysis?.enrichment_review_needed || false)
  }

  const handleAnalyze = async (ciName: string) => {
    setAnalyzing(ciName)
    await api.analyzeSingle(ciName)
    setAnalyzing(null)
    loadItems()
  }

  const handleAddTag = async (ciName: string) => {
    if (!newTag.trim()) return
    await api.addTag(ciName, 'label', newTag.trim())
    setNewTag('')
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetail(detail)
  }

  const handleRemoveTag = async (ciName: string, tagId: number) => {
    await api.removeTag(ciName, tagId)
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetail(detail)
  }

  const handleSaveNote = async (ciName: string) => {
    await api.setNote(ciName, noteText)
  }

  const handleFlag = async (ciName: string) => {
    await api.flagItem(ciName)
    setFlagged(true)
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
          <option value="needs_review">Needs review</option>
          <option value="untagged">Untagged</option>
          <option value="scan_failures">Scan failures</option>
        </select>
        <LcarsToggle label="dev" active={showDev} onToggle={() => { setShowDev(!showDev); setOffset(0) }} />
        <LcarsToggle label="event" active={showEvent} onToggle={() => { setShowEvent(!showEvent); setOffset(0) }} />
        <span style={{ color: '#666', fontSize: '14px', alignSelf: 'center' }}>
          {total} items
        </span>
      </div>

      {loading ? (
        <div style={{ color: '#666', padding: '20px' }}>Loading...</div>
      ) : (
        <>
          {pageItems.map(item => (
            <div key={item.ci_name} className="curate-item">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div
                    className="curate-item-title"
                    style={{ cursor: 'pointer' }}
                    onClick={() => handleExpand(item.ci_name)}
                  >
                    {expandedItem === item.ci_name ? '▾' : '▸'}{' '}
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
                  <LcarsButton
                    variant="curator-secondary"
                    onClick={() => handleAnalyze(item.ci_name)}
                    disabled={analyzing === item.ci_name}
                  >
                    {analyzing === item.ci_name ? 'Analyzing...' : 'Re-analyze'}
                  </LcarsButton>
                )}
              </div>

              {expandedItem === item.ci_name && itemDetail && (
                <div style={{ marginTop: '12px' }}>
                  {/* Analysis metadata + summary */}
                  {itemDetail.analysis && (
                    <>
                      {itemDetail.analysis.content_type && (
                        <div style={{ fontSize: '12px', color: '#73bcf7', marginBottom: '6px', display: 'flex', gap: '8px' }}>
                          <span>{itemDetail.analysis.content_type}</span>
                          {itemDetail.analysis.difficulty && <span style={{ color: '#888' }}>{itemDetail.analysis.difficulty}</span>}
                          {itemDetail.analysis.estimated_duration_min && <span style={{ color: '#888' }}>~{itemDetail.analysis.estimated_duration_min} min</span>}
                        </div>
                      )}
                      {itemDetail.analysis.summary && (
                        <p style={{ fontSize: '12px', color: '#aaa', marginBottom: '10px', lineHeight: '1.5' }}>
                          {itemDetail.analysis.summary}
                        </p>
                      )}

                      {/* Analysis topics — blue pills */}
                      {itemDetail.analysis.topics_json && itemDetail.analysis.topics_json.length > 0 && (
                        <div style={{ marginBottom: '8px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          {itemDetail.analysis.topics_json.map((topic, i) => (
                            <span key={i} style={{
                              display: 'inline-block', background: '#1a2a3a',
                              color: '#73bcf7', border: '1px solid #2a4a6a',
                              borderRadius: '10px', padding: '2px 8px', fontSize: '11px',
                            }}>{topic}</span>
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {/* Curator tags — green pills, just the value */}
                  <div className="tag-list" style={{ marginBottom: '8px' }}>
                    {itemDetail.tags.map(tag => (
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
                    {/* Inline add tag — just type the value, like original RCARS */}
                    {auth.isCurator && (
                      <input
                        type="text"
                        value={newTag}
                        onChange={(e) => setNewTag(e.target.value)}
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
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
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
                      <LcarsButton
                        variant="curator-secondary"
                        onClick={() => handleFlag(item.ci_name)}
                        disabled={flagged}
                      >
                        {flagged ? '✓ Flagged for review' : 'Flag for review'}
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
          ))}

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
