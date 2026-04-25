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
}

export function BrowsePage() {
  const auth = useAuth()
  const [allItems, setAllItems] = useState<CatalogItem[]>([])
  const [search, setSearch] = useState('')
  const [showDev, setShowDev] = useState(false)
  const [showEvent, setShowEvent] = useState(false)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expandedItem, setExpandedItem] = useState<string | null>(null)
  const [itemDetail, setItemDetail] = useState<Record<string, unknown> | null>(null)
  const limit = 50

  const loadItems = async () => {
    setLoading(true)
    const data = await api.listCatalog({ limit: 500 })
    setAllItems(data.items as CatalogItem[])
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
    const detail = await api.getCatalogItem(ciName) as Record<string, unknown>
    setItemDetail(detail)
  }

  const handleAnalyze = async (ciName: string) => {
    await api.analyzeSingle(ciName)
    loadItems()
  }

  const toggleStyle = (active: boolean) => ({
    background: active ? '#1a3a5a' : 'transparent',
    border: `1px solid ${active ? '#73bcf7' : '#333'}`,
    color: active ? '#73bcf7' : '#666',
    padding: '6px 16px',
    borderRadius: '6px',
    cursor: 'pointer' as const,
    fontSize: '14px',
  })

  return (
    <div className="curate-layout">
      <div className="filter-bar">
        <input
          className="filter-input"
          placeholder="Search by name or CI..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
        />
        <button
          style={toggleStyle(showDev)}
          onClick={() => { setShowDev(!showDev); setOffset(0) }}
        >
          Show dev
        </button>
        <button
          style={toggleStyle(showEvent)}
          onClick={() => { setShowEvent(!showEvent); setOffset(0) }}
        >
          Show event
        </button>
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
                    {item.display_name || item.ci_name}
                    {item.stage !== 'prod' && (
                      <span style={{ fontSize: '12px', color: '#e8a838', marginLeft: '8px' }}>{item.stage}</span>
                    )}
                    {item.scan_status === 'failed' && <LcarsBadge variant="red"> FAILED</LcarsBadge>}
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
                <div style={{ marginTop: '12px', fontSize: '14px', color: '#aaa' }}>
                  {(itemDetail as { analysis?: { summary?: string } }).analysis?.summary && (
                    <p style={{ marginBottom: '8px' }}>{(itemDetail as { analysis: { summary: string } }).analysis.summary}</p>
                  )}
                  {(itemDetail as { tags?: Array<{ id: number; tag_type: string; tag_value: string }> }).tags &&
                    ((itemDetail as { tags: Array<{ id: number; tag_type: string; tag_value: string }> }).tags).length > 0 && (
                    <div className="tag-list">
                      {((itemDetail as { tags: Array<{ id: number; tag_type: string; tag_value: string }> }).tags).map(tag => (
                        <LcarsBadge key={tag.id} variant="tag">{tag.tag_type}: {tag.tag_value}</LcarsBadge>
                      ))}
                    </div>
                  )}
                  {item.showroom_url && (
                    <div style={{ marginTop: '8px', fontSize: '13px', color: '#666' }}>
                      Showroom: {item.showroom_url}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {total > limit && (
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginTop: '20px' }}>
              <button
                className="btn-action"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                Previous
              </button>
              <span style={{ color: '#666', alignSelf: 'center', fontSize: '14px' }}>
                {offset + 1}-{Math.min(offset + limit, total)} of {total}
              </span>
              <button
                className="btn-action"
                disabled={offset + limit >= total}
                onClick={() => setOffset(offset + limit)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
