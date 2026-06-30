import { useState, useCallback, useMemo, useRef } from 'react'
import { api } from '../services/api'

// ── Interfaces ──

interface WorkloadMapping {
  workload_role: string
  product_name: string
  description: string | null
  category: string | null
  source_collection: string | null
  verified: boolean
  added_by: string | null
}

interface UnmappedWorkload {
  workload_role: string
  workload_collection: string | null
  ci_count: number
}

type StatusFilter = 'mapped' | 'unmapped' | 'all'
type VerificationFilter = 'all' | 'verified' | 'unverified'

// ── WorkloadsPage ──

export function WorkloadsPage() {
  const [mappings, setMappings] = useState<WorkloadMapping[]>([])
  const [unmapped, setUnmapped] = useState<UnmappedWorkload[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [mappingForm, setMappingForm] = useState<Record<string, { product: string; category: string }>>({})

  // Expanded card state
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())

  // Section collapse state
  const [unmappedSectionOpen, setUnmappedSectionOpen] = useState(false)

  // Filter state
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('mapped')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [verificationFilter, setVerificationFilter] = useState<VerificationFilter>('all')
  const [collectionFilter, setCollectionFilter] = useState('')

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [mapData, unmapData] = await Promise.all([
        api.getWorkloadMappings() as Promise<{ mappings: WorkloadMapping[]; aliases: unknown[] }>,
        api.getUnmappedWorkloads() as Promise<{ unmapped: UnmappedWorkload[] }>,
      ])
      setMappings(mapData.mappings.sort((a, b) => a.product_name.localeCompare(b.product_name)))
      setUnmapped(unmapData.unmapped.sort((a, b) => b.ci_count - a.ci_count))
      setLoaded(true)
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  // Load data on first render
  if (!loaded && !loading) {
    loadData()
  }

  const handleDelete = async (role: string) => {
    await api.deleteWorkloadMapping(role)
    loadData()
  }

  const handleMap = async (role: string) => {
    const form = mappingForm[role]
    if (!form?.product?.trim()) return
    await api.addWorkloadMapping({
      workload_role: role,
      product_name: form.product.trim(),
      category: form.category?.trim() || undefined,
    })
    setMappingForm(prev => { const next = { ...prev }; delete next[role]; return next })
    loadData()
  }

  const handleExpand = (role: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      if (next.has(role)) {
        next.delete(role)
      } else {
        next.add(role)
      }
      return next
    })
  }

  const handleSearchChange = (value: string) => {
    setSearch(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      // Search is applied via useMemo filtering — no debounced fetch needed
    }, 150)
  }

  // ── Derived filter options ──

  const uniqueCategories = useMemo(() => {
    const cats = new Set<string>()
    mappings.forEach(m => { if (m.category) cats.add(m.category) })
    return Array.from(cats).sort()
  }, [mappings])

  const uniqueCollections = useMemo(() => {
    const colls = new Set<string>()
    mappings.forEach(m => { if (m.source_collection) colls.add(m.source_collection) })
    unmapped.forEach(u => { if (u.workload_collection) colls.add(u.workload_collection) })
    return Array.from(colls).sort()
  }, [mappings, unmapped])

  // ── Filtered data ──

  const searchLower = search.toLowerCase()

  const filteredMappings = useMemo(() => {
    return mappings.filter(m => {
      if (searchLower && !(
        m.workload_role.toLowerCase().includes(searchLower) ||
        m.product_name.toLowerCase().includes(searchLower) ||
        (m.description && m.description.toLowerCase().includes(searchLower))
      )) return false
      if (categoryFilter && m.category !== categoryFilter) return false
      if (verificationFilter === 'verified' && !m.verified) return false
      if (verificationFilter === 'unverified' && m.verified) return false
      if (collectionFilter && m.source_collection !== collectionFilter) return false
      return true
    })
  }, [mappings, searchLower, categoryFilter, verificationFilter, collectionFilter])

  const filteredUnmapped = useMemo(() => {
    return unmapped.filter(u => {
      if (searchLower && !(
        u.workload_role.toLowerCase().includes(searchLower) ||
        (u.workload_collection && u.workload_collection.toLowerCase().includes(searchLower))
      )) return false
      if (collectionFilter && u.workload_collection !== collectionFilter) return false
      return true
    })
  }, [unmapped, searchLower, collectionFilter])

  const showMapped = statusFilter === 'mapped' || statusFilter === 'all'
  const showUnmapped = statusFilter === 'unmapped' || statusFilter === 'all'

  // ── Active filter chips ──

  const activeFilters: Array<{ label: string; onRemove: () => void }> = []
  if (categoryFilter) activeFilters.push({ label: `Category: ${categoryFilter}`, onRemove: () => setCategoryFilter('') })
  if (verificationFilter !== 'all') activeFilters.push({ label: verificationFilter === 'verified' ? 'Verified' : 'Unverified', onRemove: () => setVerificationFilter('all') })
  if (collectionFilter) activeFilters.push({ label: `Collection: ${collectionFilter}`, onRemove: () => setCollectionFilter('') })

  const clearAllFilters = () => {
    setCategoryFilter('')
    setVerificationFilter('all')
    setCollectionFilter('')
  }

  if (loading && !loaded) {
    return (
      <div className="browse-layout">
        <div className="browse-toolbar">
          <span className="browse-loading">Loading workload mappings...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="browse-layout">
      {/* ── Top Bar ── */}
      <div className="browse-toolbar">
        <input
          type="text"
          className="browse-search"
          placeholder="Search by role, product, or description..."
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
        />

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

        <span className="browse-item-count">
          {filteredMappings.length} mapped &middot; {filteredUnmapped.length} unmapped
        </span>
      </div>

      {/* ── Content: filter sidebar + card list ── */}
      <div className="browse-content">
        {/* Filter sidebar */}
        <div className="browse-filter-sidebar">
          {/* Status filter */}
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Status</div>
            <div className="wl-status-pills">
              {(['mapped', 'unmapped', 'all'] as StatusFilter[]).map(sf => (
                <button
                  key={sf}
                  className={`browse-curator-pill${statusFilter === sf ? ' active' : ''}`}
                  onClick={() => setStatusFilter(sf)}
                >
                  {sf.charAt(0).toUpperCase() + sf.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Category filter */}
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Category</div>
            <select
              className="browse-filter-select"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">All categories</option>
              {uniqueCategories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          {/* Verification filter */}
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Verification</div>
            <div className="wl-status-pills">
              {(['all', 'verified', 'unverified'] as VerificationFilter[]).map(vf => (
                <button
                  key={vf}
                  className={`browse-curator-pill${verificationFilter === vf ? ' active' : ''}`}
                  onClick={() => setVerificationFilter(vf)}
                >
                  {vf.charAt(0).toUpperCase() + vf.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Collection filter */}
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Collection</div>
            <select
              className="browse-filter-select"
              value={collectionFilter}
              onChange={(e) => setCollectionFilter(e.target.value)}
            >
              <option value="">All collections</option>
              {uniqueCollections.map(coll => (
                <option key={coll} value={coll}>{coll}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Card list */}
        <div className="browse-list">
          {/* ── Mapped Workloads Section ── */}
          {showMapped && (
            <div className="wl-section">
              <div className="wl-section-header wl-section-header--green">
                <span>Mapped Workloads</span>
                <span className="wl-section-count">{filteredMappings.length}</span>
              </div>
              {filteredMappings.length === 0 ? (
                <div className="wl-empty">No mapped workloads match the current filters.</div>
              ) : (
                filteredMappings.map(m => {
                  const isExpanded = expandedItems.has(m.workload_role)
                  return (
                    <div
                      key={m.workload_role}
                      className={`browse-item${isExpanded ? ' expanded' : ''}`}
                    >
                      {/* Collapsed header */}
                      <div className="browse-item-header">
                        <div className="browse-item-header-left">
                          <div
                            className="browse-item-title"
                            onClick={() => handleExpand(m.workload_role)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleExpand(m.workload_role) } }}
                          >
                            <span className="browse-expand-icon">{isExpanded ? '▼' : '▶'}</span>
                            <span className="wl-role-name">{m.workload_role}</span>
                            <span className="wl-product-name">{m.product_name}</span>
                            {m.verified && <span className="verified-badge">verified</span>}
                          </div>
                          <div className="browse-item-ci">
                            {m.category || 'Uncategorized'}
                          </div>
                        </div>
                      </div>

                      {/* Expanded body */}
                      {isExpanded && (
                        <div className="browse-item-body" onClick={(e) => e.stopPropagation()}>
                          {m.description && (
                            <p className="browse-description">{m.description}</p>
                          )}

                          <div className="wl-detail-grid">
                            <div className="wl-detail-item">
                              <span className="wl-detail-label">Category</span>
                              <span className="wl-detail-value">{m.category || '—'}</span>
                            </div>
                            <div className="wl-detail-item">
                              <span className="wl-detail-label">Collection</span>
                              <span className="wl-detail-value">{m.source_collection || '—'}</span>
                            </div>
                            <div className="wl-detail-item">
                              <span className="wl-detail-label">Verification</span>
                              <span className="wl-detail-value">
                                {m.verified ? (
                                  <span className="verified-badge">verified</span>
                                ) : (
                                  <span style={{ color: 'var(--text-muted)' }}>unverified</span>
                                )}
                              </span>
                            </div>
                            {m.added_by && (
                              <div className="wl-detail-item">
                                <span className="wl-detail-label">Added by</span>
                                <span className="wl-detail-value">{m.added_by}</span>
                              </div>
                            )}
                          </div>

                          <div className="wl-card-actions">
                            <button
                              className="mapping-delete-btn"
                              onClick={() => handleDelete(m.workload_role)}
                              title="Remove mapping"
                            >
                              Remove mapping
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          )}

          {/* ── Unmapped Workloads Section ── */}
          {showUnmapped && (
            <div className="wl-section">
              <div
                className="wl-section-header wl-section-header--amber wl-section-header--collapsible"
                onClick={() => setUnmappedSectionOpen(!unmappedSectionOpen)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setUnmappedSectionOpen(!unmappedSectionOpen) } }}
              >
                <span className="browse-toggle-caret" style={unmappedSectionOpen ? { transform: 'rotate(90deg)' } : undefined}>&#9654;</span>
                <span>Unmapped Workloads</span>
                <span className="wl-section-count">{filteredUnmapped.length}</span>
              </div>

              {unmappedSectionOpen && (
                <>
                  {filteredUnmapped.length === 0 ? (
                    <div className="wl-empty">No unmapped workloads match the current filters.</div>
                  ) : (
                    filteredUnmapped.map(u => {
                      const isExpanded = expandedItems.has(u.workload_role)
                      const hasForm = mappingForm[u.workload_role] !== undefined
                      return (
                        <div
                          key={u.workload_role}
                          className={`browse-item${isExpanded ? ' expanded' : ''}`}
                        >
                          {/* Collapsed header */}
                          <div className="browse-item-header">
                            <div className="browse-item-header-left">
                              <div
                                className="browse-item-title"
                                onClick={() => handleExpand(u.workload_role)}
                                role="button"
                                tabIndex={0}
                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleExpand(u.workload_role) } }}
                              >
                                <span className="browse-expand-icon">{isExpanded ? '▼' : '▶'}</span>
                                <span className="wl-role-name">{u.workload_role}</span>
                                {u.workload_collection && (
                                  <span className="wl-collection-muted">{u.workload_collection}</span>
                                )}
                                <span className="wl-ci-count-badge">Used by {u.ci_count} CI{u.ci_count !== 1 ? 's' : ''}</span>
                              </div>
                            </div>
                          </div>

                          {/* Expanded body */}
                          {isExpanded && (
                            <div className="browse-item-body" onClick={(e) => e.stopPropagation()}>
                              <div className="wl-detail-grid">
                                <div className="wl-detail-item">
                                  <span className="wl-detail-label">Collection</span>
                                  <span className="wl-detail-value">{u.workload_collection || '—'}</span>
                                </div>
                                <div className="wl-detail-item">
                                  <span className="wl-detail-label">Used by</span>
                                  <span className="wl-detail-value">{u.ci_count} catalog item{u.ci_count !== 1 ? 's' : ''}</span>
                                </div>
                              </div>

                              {/* Inline mapping form */}
                              {hasForm ? (
                                <div className="wl-mapping-form">
                                  <div className="wl-mapping-form-row">
                                    <input
                                      className="wl-mapping-input"
                                      placeholder="Product name"
                                      value={mappingForm[u.workload_role]?.product || ''}
                                      onChange={(e) => setMappingForm(prev => ({
                                        ...prev, [u.workload_role]: { ...prev[u.workload_role], product: e.target.value }
                                      }))}
                                      onKeyDown={(e) => { if (e.key === 'Enter') handleMap(u.workload_role) }}
                                    />
                                    <input
                                      className="wl-mapping-input wl-mapping-input--short"
                                      placeholder="Category"
                                      value={mappingForm[u.workload_role]?.category || ''}
                                      onChange={(e) => setMappingForm(prev => ({
                                        ...prev, [u.workload_role]: { ...prev[u.workload_role], category: e.target.value }
                                      }))}
                                      onKeyDown={(e) => { if (e.key === 'Enter') handleMap(u.workload_role) }}
                                    />
                                  </div>
                                  <div className="wl-mapping-form-actions">
                                    <button className="browse-btn-action" onClick={() => handleMap(u.workload_role)}>
                                      Save
                                    </button>
                                    <button
                                      className="wl-mapping-cancel"
                                      onClick={() => setMappingForm(prev => { const next = { ...prev }; delete next[u.workload_role]; return next })}
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <div className="wl-card-actions">
                                  <button
                                    className="browse-btn-action"
                                    onClick={() => setMappingForm(prev => ({ ...prev, [u.workload_role]: { product: '', category: '' } }))}
                                  >
                                    Map this workload
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
