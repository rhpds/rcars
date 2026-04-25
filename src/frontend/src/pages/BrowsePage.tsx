import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { LcarsButton, LcarsBadge } from '../components/lcars'

interface CatalogItem {
  ci_name: string
  display_name: string
  category: string
  stage: string
  showroom_url: string | null
  scan_status: string
  enrichment_review_needed?: boolean
}

interface ItemDetail {
  ci_name: string
  display_name: string
  category: string
  stage: string
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
  const [newTagType, setNewTagType] = useState('')
  const [newTagValue, setNewTagValue] = useState('')
  const [noteText, setNoteText] = useState('')
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
  }

  const handleAnalyze = async (ciName: string) => {
    await api.analyzeSingle(ciName)
    loadItems()
  }

  const handleAddTag = async (ciName: string) => {
    if (!newTagType.trim() || !newTagValue.trim()) return
    await api.addTag(ciName, newTagType.trim(), newTagValue.trim())
    setNewTagType('')
    setNewTagValue('')
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
                      <span style={{ fontSize: '12px', color: '#e8a838', marginLeft: '8px' }}>{item.stage}</span>
                    )}
                    {item.scan_status === 'failed' && <LcarsBadge variant="red"> FAILED</LcarsBadge>}
                    {item.enrichment_review_needed && <LcarsBadge variant="amber"> REVIEW</LcarsBadge>}
                  </div>
                  <div className="curate-item-ci">{item.ci_name} · {item.category}</div>
                </div>
                {auth.isCurator && (
                  <LcarsButton variant="curator-secondary" onClick={() => handleAnalyze(item.ci_name)}>
                    Re-analyze
                  </LcarsButton>
                )}
              </div>

              {expandedItem === item.ci_name && itemDetail && (
                <div style={{ marginTop: '12px' }}>
                  {/* Analysis summary and metadata */}
                  {itemDetail.analysis && (
                    <>
                      {itemDetail.analysis.content_type && (
                        <div style={{ fontSize: '13px', color: '#888', marginBottom: '6px' }}>
                          {itemDetail.analysis.content_type}
                          {itemDetail.analysis.difficulty && ` · ${itemDetail.analysis.difficulty}`}
                          {itemDetail.analysis.estimated_duration_min && ` · ~${itemDetail.analysis.estimated_duration_min} min`}
                        </div>
                      )}
                      {itemDetail.analysis.summary && (
                        <p style={{ fontSize: '14px', color: '#aaa', marginBottom: '10px', lineHeight: '1.6' }}>
                          {itemDetail.analysis.summary}
                        </p>
                      )}

                      {/* Analysis topics as pills */}
                      {itemDetail.analysis.topics_json && itemDetail.analysis.topics_json.length > 0 && (
                        <div className="rec-pill-row" style={{ marginBottom: '8px' }}>
                          {itemDetail.analysis.topics_json.map((topic, i) => (
                            <span key={i} className="rec-pill">{topic}</span>
                          ))}
                        </div>
                      )}

                      {/* Products */}
                      {itemDetail.analysis.products_json && itemDetail.analysis.products_json.length > 0 && (
                        <div className="rec-pill-row" style={{ marginBottom: '8px' }}>
                          {itemDetail.analysis.products_json.map((prod, i) => (
                            <span key={i} className="rec-pill pill-format">{prod}</span>
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {/* Curator enrichment tags */}
                  {itemDetail.tags.length > 0 && (
                    <div className="tag-list" style={{ marginBottom: '8px' }}>
                      {itemDetail.tags.map(tag => (
                        <span
                          key={tag.id}
                          className="tag-pill-removable"
                          onClick={auth.isCurator ? () => handleRemoveTag(item.ci_name, tag.id) : undefined}
                          title={auth.isCurator ? 'Click to remove' : `Added by ${tag.added_by || 'unknown'}`}
                        >
                          {tag.tag_type}: {tag.tag_value}
                          {auth.isCurator && ' ×'}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Curator controls */}
                  {auth.isCurator && (
                    <div style={{ marginTop: '10px' }}>
                      {/* Add tag */}
                      <div style={{ display: 'flex', gap: '6px', marginBottom: '8px', alignItems: 'center' }}>
                        <input
                          className="filter-input"
                          placeholder="Tag type"
                          value={newTagType}
                          onChange={(e) => setNewTagType(e.target.value)}
                          style={{ width: '120px', padding: '6px 10px', fontSize: '13px' }}
                        />
                        <input
                          className="filter-input"
                          placeholder="Tag value"
                          value={newTagValue}
                          onChange={(e) => setNewTagValue(e.target.value)}
                          style={{ width: '160px', padding: '6px 10px', fontSize: '13px' }}
                          onKeyDown={(e) => { if (e.key === 'Enter') handleAddTag(item.ci_name) }}
                        />
                        <LcarsButton variant="curator" onClick={() => handleAddTag(item.ci_name)}>
                          + Add tag
                        </LcarsButton>
                      </div>

                      {/* Note */}
                      <div style={{ display: 'flex', gap: '6px', marginBottom: '8px', alignItems: 'center' }}>
                        <input
                          className="filter-input"
                          placeholder="Add a note..."
                          value={noteText}
                          onChange={(e) => setNoteText(e.target.value)}
                          style={{ flex: 1, padding: '6px 10px', fontSize: '13px' }}
                          onKeyDown={(e) => { if (e.key === 'Enter') handleSaveNote(item.ci_name) }}
                        />
                      </div>

                      {/* Flag */}
                      <LcarsButton variant="curator-secondary" onClick={() => handleFlag(item.ci_name)}>
                        Flag for review
                      </LcarsButton>
                    </div>
                  )}

                  {/* Showroom link */}
                  {item.showroom_url && (
                    <div style={{ marginTop: '8px', fontSize: '13px', color: '#555' }}>
                      Showroom: <a href={item.showroom_url} target="_blank" rel="noopener noreferrer" style={{ color: '#73bcf7' }}>{item.showroom_url}</a>
                    </div>
                  )}
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
