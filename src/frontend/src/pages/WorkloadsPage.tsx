import { useState, useCallback, useMemo, useEffect } from 'react'
import { api } from '../services/api'

interface InfrastructureItem {
  role_name: string
  fqcn: string | null
  collection: string | null
  type: string
  description: string | null
  products: string[]
  capabilities: string[]
  category: string | null
  requires: string[]
  scanned_at: string | null
  item_count: number
}

export function WorkloadsPage() {
  const [items, setItems] = useState<InfrastructureItem[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [linkedItems, setLinkedItems] = useState<Record<string, Array<{ content_id: string; display_name: string; ci_name: string; stage: string }>>>({})
  const [loadingItems, setLoadingItems] = useState<Set<string>>(new Set())

  // Filters
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [collectionFilter, setCollectionFilter] = useState('')
  const [mappingsFilter, setMappingsFilter] = useState<string>('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getInfrastructureCatalog()
      setItems(data.items)
      setLoaded(true)
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  useEffect(() => { loadData() }, [loadData])

  // Derived filter options
  const uniqueCategories = useMemo(() => {
    const cats = new Set<string>()
    items.forEach(i => { if (i.category) cats.add(i.category) })
    return Array.from(cats).sort()
  }, [items])

  const uniqueCollections = useMemo(() => {
    const colls = new Set<string>()
    items.forEach(i => { if (i.collection) colls.add(i.collection) })
    return Array.from(colls).sort()
  }, [items])

  // Client-side filtering
  const searchLower = search.toLowerCase()
  const filtered = useMemo(() => {
    return items.filter(i => {
      if (searchLower && !(
        i.role_name.toLowerCase().includes(searchLower) ||
        (i.description && i.description.toLowerCase().includes(searchLower)) ||
        i.products.some(p => p.toLowerCase().includes(searchLower)) ||
        i.capabilities.some(c => c.toLowerCase().includes(searchLower))
      )) return false
      if (typeFilter && i.type !== typeFilter) return false
      if (categoryFilter && i.category !== categoryFilter) return false
      if (collectionFilter && i.collection !== collectionFilter) return false
      if (mappingsFilter === 'with' && i.item_count === 0) return false
      if (mappingsFilter === 'without' && i.item_count > 0) return false
      return true
    })
  }, [items, searchLower, typeFilter, categoryFilter, collectionFilter, mappingsFilter])

  const handleExpand = (name: string, itemCount: number) => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
    if (itemCount > 0 && !linkedItems[name] && !loadingItems.has(name)) {
      setLoadingItems(prev => new Set(prev).add(name))
      api.getInfrastructureItems(name)
        .then(data => setLinkedItems(prev => ({ ...prev, [name]: data.items })))
        .catch(() => {})
        .finally(() => setLoadingItems(prev => { const n = new Set(prev); n.delete(name); return n }))
    }
  }

  // Active filter chips
  const activeFilters: Array<{ label: string; onRemove: () => void }> = []
  if (typeFilter) activeFilters.push({ label: `Type: ${typeFilter}`, onRemove: () => setTypeFilter('') })
  if (categoryFilter) activeFilters.push({ label: `Category: ${categoryFilter}`, onRemove: () => setCategoryFilter('') })
  if (collectionFilter) activeFilters.push({ label: `Collection: ${collectionFilter}`, onRemove: () => setCollectionFilter('') })
  if (mappingsFilter) activeFilters.push({ label: mappingsFilter === 'with' ? 'Has CIs' : 'No CIs', onRemove: () => setMappingsFilter('') })

  if (loading && !loaded) {
    return (
      <div className="browse-layout">
        <div className="browse-toolbar">
          <span className="browse-loading">Loading infrastructure catalog...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="browse-layout">
      <div className="browse-toolbar">
        <input
          type="text" className="browse-search"
          placeholder="Search by role, description, products, capabilities..."
          value={search} onChange={(e) => setSearch(e.target.value)}
        />
        {activeFilters.length > 0 && (
          <>
            <div className="browse-toolbar-divider" />
            {activeFilters.map(f => (
              <span key={f.label} className="browse-chip" onClick={f.onRemove}>
                {f.label} <span className="browse-chip-x">&times;</span>
              </span>
            ))}
            <button className="browse-chip browse-chip--clear"
              onClick={() => { setTypeFilter(''); setCategoryFilter(''); setCollectionFilter(''); setMappingsFilter('') }}>
              Clear all
            </button>
          </>
        )}
        <span className="browse-item-count">{filtered.length} items</span>
      </div>

      <div className="browse-content">
        <div className="browse-filter-sidebar">
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Type</div>
            <div className="wl-status-pills">
              {['', 'workload', 'config'].map(t => (
                <button key={t || 'all'}
                  className={`browse-curator-pill${typeFilter === t ? ' active' : ''}`}
                  onClick={() => setTypeFilter(t)}>
                  {t ? t.charAt(0).toUpperCase() + t.slice(1) : 'All'}
                </button>
              ))}
            </div>
          </div>
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Category</div>
            <select className="browse-filter-select" value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}>
              <option value="">All categories</option>
              {uniqueCategories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Collection</div>
            <select className="browse-filter-select" value={collectionFilter}
              onChange={(e) => setCollectionFilter(e.target.value)}>
              <option value="">All collections</option>
              {uniqueCollections.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Catalog Items</div>
            <div className="wl-status-pills">
              {[['', 'All'], ['with', 'Has CIs'], ['without', 'Orphans']].map(([v, l]) => (
                <button key={v}
                  className={`browse-curator-pill${mappingsFilter === v ? ' active' : ''}`}
                  onClick={() => setMappingsFilter(v)}>
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="browse-list">
          {filtered.length === 0 ? (
            <div className="wl-empty">No infrastructure items match the current filters.</div>
          ) : filtered.map(item => {
            const isExpanded = expandedItems.has(item.role_name)
            return (
              <div key={item.role_name} className={`browse-item${isExpanded ? ' expanded' : ''}`}>
                <div className="browse-item-header">
                  <div className="browse-item-header-left">
                    <div className="browse-item-title" onClick={() => handleExpand(item.role_name, item.item_count)}
                      role="button" tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleExpand(item.role_name, item.item_count) } }}>
                      <span className="browse-expand-icon">{isExpanded ? '▼' : '▶'}</span>
                      <span className="wl-role-name">{item.role_name}</span>
                      <span className={`stage-badge stage-badge--${item.type === 'config' ? 'prod' : 'dev'}`}>
                        {item.type}
                      </span>
                      {item.item_count > 0 && (
                        <span className="wl-ci-count-badge">
                          Used by {item.item_count} item{item.item_count !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="browse-item-body" onClick={(e) => e.stopPropagation()}>
                    {item.description && <p className="browse-description">{item.description}</p>}

                    {item.products.length > 0 && (
                      <div className="browse-pills">
                        {item.products.map(p => (
                          <span key={p} className="browse-pill browse-pill--product">{p}</span>
                        ))}
                      </div>
                    )}

                    {item.capabilities.length > 0 && (
                      <div className="browse-pills">
                        {item.capabilities.map(c => (
                          <span key={c} className="browse-pill browse-pill--topic">{c}</span>
                        ))}
                      </div>
                    )}

                    <div className="wl-detail-grid">
                      <div className="wl-detail-item">
                        <span className="wl-detail-label">Category</span>
                        <span className="wl-detail-value">{item.category || '—'}</span>
                      </div>
                      <div className="wl-detail-item">
                        <span className="wl-detail-label">Collection</span>
                        <span className="wl-detail-value">{item.collection || '—'}</span>
                      </div>
                      {item.fqcn && (
                        <div className="wl-detail-item">
                          <span className="wl-detail-label">FQCN</span>
                          <span className="wl-detail-value">{item.fqcn}</span>
                        </div>
                      )}
                      {item.requires.length > 0 && (
                        <div className="wl-detail-item">
                          <span className="wl-detail-label">Requires</span>
                          <span className="wl-detail-value">{item.requires.join(', ')}</span>
                        </div>
                      )}
                      {item.scanned_at && (
                        <div className="wl-detail-item">
                          <span className="wl-detail-label">Last scanned</span>
                          <span className="wl-detail-value">
                            {new Date(item.scanned_at).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>

                    {item.item_count > 0 && (
                      <div className="wl-linked-items">
                        <div className="wl-detail-label" style={{ marginBottom: '0.5rem' }}>
                          Catalog Items ({item.item_count})
                        </div>
                        {loadingItems.has(item.role_name) ? (
                          <span className="browse-loading">Loading items...</span>
                        ) : linkedItems[item.role_name] ? (
                          <div className="wl-linked-items-list">
                            {linkedItems[item.role_name].map(ci => (
                              <div key={ci.content_id} className="wl-linked-item">
                                <span className={`stage-badge stage-badge--${ci.stage || 'dev'}`}>{ci.stage}</span>
                                <span className="wl-linked-item-name">{ci.display_name || ci.ci_name}</span>
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
