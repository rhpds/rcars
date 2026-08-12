import { useState, useEffect, useCallback, useRef, Fragment } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, NonProdItem } from '../services/api'
import { WorkflowDrawer, WorkflowItem } from '../components/performance/WorkflowDrawer'
import { useAuth } from '../hooks/useAuth'

type TimeWindow = '6m' | '12m'
type StatusFilter = 'all' | 'active' | 'muted'
type SortField = 'provisions' | 'unique_users' | 'success_ratio' | 'failure_ratio' | 'display_name'

const stageBadgeClass: Record<string, string> = {
  prod: 'ca-env-prod', event: 'ca-env-event', dev: 'ca-env-dev', test: 'ca-env-test',
}

export function NonProdItemsPage() {
  const { isCurator } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [searchDisplay, setSearchDisplay] = useState(search)
  const [window_, setWindow] = useState<TimeWindow>((searchParams.get('window') as TimeWindow) || '12m')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>((searchParams.get('status') as StatusFilter) || 'all')
  const [sortBy, setSortBy] = useState<SortField>((searchParams.get('sort') as SortField) || 'provisions')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>(searchParams.get('order') === 'asc' ? 'asc' : 'desc')

  const [selectedStages, setSelectedStages] = useState<Set<string>>(
    new Set(searchParams.get('stages')?.split(',').filter(Boolean) || []))
  const [selectedContentTypes, setSelectedContentTypes] = useState<Set<string>>(
    new Set(searchParams.get('content_types')?.split(',').filter(Boolean) || []))
  const [selectedNamespaces, setSelectedNamespaces] = useState<Set<string>>(
    new Set(searchParams.get('namespace')?.split(',').filter(Boolean) || []))
  const [provFilter, setProvFilter] = useState<string>(searchParams.get('provs') || 'all')

  const [allItems, setAllItems] = useState<NonProdItem[]>([])
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [drawerItem, setDrawerItem] = useState<WorkflowItem | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestRef = useRef(0)

  const loadData = useCallback(async () => {
    const reqId = ++requestRef.current
    setLoading(true)
    try {
      const data = await api.getNonprodItems({
        sort_by: sortBy, sort_dir: sortDir,
        search: search || undefined,
        window: window_,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      })
      if (reqId !== requestRef.current) return
      setAllItems(data.items)
      setSyncedAt(data.synced_at)
    } finally {
      if (reqId === requestRef.current) setLoading(false)
    }
  }, [sortBy, sortDir, search, window_, statusFilter])

  useEffect(() => { loadData() }, [loadData])

  // URL sync
  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    if (window_ !== '12m') params.window = window_
    if (statusFilter !== 'all') params.status = statusFilter
    if (sortBy !== 'provisions') params.sort = sortBy
    if (sortDir !== 'desc') params.order = sortDir
    if (selectedStages.size > 0) params.stages = Array.from(selectedStages).sort().join(',')
    if (selectedContentTypes.size > 0) params.content_types = Array.from(selectedContentTypes).sort().join(',')
    if (selectedNamespaces.size > 0) params.namespace = Array.from(selectedNamespaces).sort().join(',')
    if (provFilter !== 'all') params.provs = provFilter
    setSearchParams(params, { replace: true })
  }, [search, window_, statusFilter, sortBy, sortDir, selectedStages, selectedContentTypes, selectedNamespaces, provFilter, setSearchParams])

  const handleSearchChange = (value: string) => {
    setSearchDisplay(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => setSearch(value), 300)
  }

  const handleIgnore = async (baseName: string) => {
    try {
      const { ignored_until } = await api.ignoreNonprodItem(baseName)
      setAllItems(prev => prev.map(i => i.catalog_base_name === baseName ? { ...i, ignored_until } : i))
    } catch (e) { setActionError(e instanceof Error ? e.message : 'Mute failed') }
  }

  const handleUnignore = async (baseName: string) => {
    try {
      await api.unignoreNonprodItem(baseName)
      setAllItems(prev => prev.map(i => i.catalog_base_name === baseName ? { ...i, ignored_until: null } : i))
    } catch (e) { setActionError(e instanceof Error ? e.message : 'Unmute failed') }
  }

  const toggleExpand = (name: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const toggleSort = (field: SortField) => {
    if (sortBy === field) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortBy(field); setSortDir('desc') }
  }

  const clearFilters = () => {
    setStatusFilter('all')
    setSelectedStages(new Set())
    setSelectedContentTypes(new Set())
    setSelectedNamespaces(new Set())
    setProvFilter('all')
  }

  const isIgnored = (i: NonProdItem) => !!i.ignored_until
  const extractNs = (name: string) => name.split('.')[0]

  // Client-side filters
  const filteredItems = allItems.filter(i => {
    if (selectedStages.size > 0) {
      const itemStages = i.stages.map(s => s.stage)
      if (!itemStages.some(s => selectedStages.has(s))) return false
    }
    if (selectedContentTypes.size > 0 && (!i.content_type || !selectedContentTypes.has(i.content_type))) return false
    if (selectedNamespaces.size > 0 && !selectedNamespaces.has(extractNs(i.catalog_base_name))) return false
    if (provFilter === '0' && i.provisions !== 0) return false
    if (provFilter === '1-10' && (i.provisions < 1 || i.provisions > 10)) return false
    if (provFilter === '10+' && i.provisions <= 10) return false
    return true
  })

  // Derive facet values from data
  const availableStages = (() => {
    const counts: Record<string, number> = {}
    for (const i of allItems) {
      for (const s of i.stages) {
        counts[s.stage] = (counts[s.stage] || 0) + 1
      }
    }
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]))
  })()

  const availableContentTypes = (() => {
    const counts: Record<string, number> = {}
    for (const i of allItems) {
      if (i.content_type) counts[i.content_type] = (counts[i.content_type] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]))
  })()

  const availableNamespaces = (() => {
    const counts: Record<string, number> = {}
    for (const i of allItems) {
      const ns = extractNs(i.catalog_base_name)
      counts[ns] = (counts[ns] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]))
  })()

  const toggleSet = (setter: React.Dispatch<React.SetStateAction<Set<string>>>, value: string) => {
    setter(prev => {
      const next = new Set(prev)
      next.has(value) ? next.delete(value) : next.add(value)
      return next
    })
  }

  const syncAge = syncedAt
    ? `${Math.round((Date.now() - new Date(syncedAt).getTime()) / 3600000)}h ago`
    : 'never'

  if (!isCurator) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <h3>Access Restricted</h3>
        <p>Non-Prod Items is available to curators only.</p>
      </div>
    )
  }

  return (
    <div className="browse-layout">
      <div className="browse-content">
      <div className="browse-filter-sidebar">
        <div className="browse-filter-group">
          <div className="browse-filter-group-label">Stage</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {availableStages.map(([stage, count]) => (
              <label key={stage} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 0', cursor: 'pointer', fontSize: '11px' }}>
                <input type="checkbox" checked={selectedStages.has(stage)} onChange={() => toggleSet(setSelectedStages, stage)} />
                <span className={`ca-env-tag ${stageBadgeClass[stage] || 'ca-env-test'}`}>{stage}</span>
                <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>
              </label>
            ))}
          </div>
        </div>

        {availableContentTypes.length > 1 && (
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Content Type</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {availableContentTypes.map(([ct, count]) => (
                <label key={ct} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 0', cursor: 'pointer', fontSize: '11px' }}>
                  <input type="checkbox" checked={selectedContentTypes.has(ct)} onChange={() => toggleSet(setSelectedContentTypes, ct)} />
                  <span>{ct}</span>
                  <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="browse-filter-group">
          <div className="browse-filter-group-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            Namespace
            {selectedNamespaces.size > 0 && (
              <button onClick={() => setSelectedNamespaces(new Set())}
                style={{ background: 'none', border: 'none', color: 'var(--score-amber)', fontSize: '11px', cursor: 'pointer', padding: 0 }}>
                Clear ({selectedNamespaces.size})
              </button>
            )}
          </div>
          <div style={{
            maxHeight: '200px', overflowY: 'auto', paddingRight: '8px',
            border: '1px solid var(--border-section)', borderRadius: 'var(--radius-sm)', background: 'var(--bg-page)',
          }}>
            {availableNamespaces.map(([ns, count]) => (
              <label key={ns} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 8px', cursor: 'pointer', fontSize: '11px' }}>
                <input type="checkbox" checked={selectedNamespaces.has(ns)} onChange={() => toggleSet(setSelectedNamespaces, ns)} />
                <span>{ns}</span>
                <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>
              </label>
            ))}
          </div>
        </div>

        <div className="browse-filter-group">
          <div className="browse-filter-group-label">Provisions</div>
          <div className="ret-filter-group">
            {(['all', '0', '1-10', '10+'] as const).map(f => (
              <button key={f} onClick={() => setProvFilter(f)}
                className={`ret-filter-group__btn${provFilter === f ? ' active' : ''}`}>
                {f === 'all' ? 'All' : f}
              </button>
            ))}
          </div>
        </div>

        <div className="browse-filter-group">
          <div className="browse-filter-group-label">Status</div>
          <div className="ret-filter-group">
            {(['all', 'active', 'muted'] as StatusFilter[]).map(f => (
              <button key={f} onClick={() => setStatusFilter(f)}
                className={`ret-filter-group__btn${statusFilter === f ? ' active' : ''}`}>
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginTop: '16px' }}>
          <button onClick={clearFilters}
            style={{ background: 'none', border: 'none', color: 'var(--score-amber)', fontSize: '11px', cursor: 'pointer', padding: 0 }}>
            Clear filters
          </button>
        </div>
      </div>

      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'auto', padding: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Non-Prod Items</h3>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Synced {syncAge}</span>
        </div>

        <div className="ca-tab-bar">
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', gap: '4px' }}>
            {([['6m', '6 Mo'], ['12m', '1 Yr']] as [TimeWindow, string][]).map(([w, label]) => (
              <button key={w} onClick={() => setWindow(w)}
                className={`ca-filter-btn${window_ === w ? ' active' : ''}`}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="ca-stats-grid">
          <div className="ret-stat-card ret-stat-card--blue">
            <div className="ret-stat-label">Total Items</div>
            <div className="ret-stat-value ca-color-blue">{allItems.filter(i => !isIgnored(i)).length}</div>
          </div>
          <div className="ret-stat-card">
            <div className="ret-stat-label">With Provisions</div>
            <div className="ret-stat-value">{allItems.filter(i => !isIgnored(i) && i.provisions > 0).length}</div>
          </div>
          <div className="ret-stat-card">
            <div className="ret-stat-label">Zero Provisions</div>
            <div className="ret-stat-value">{allItems.filter(i => !isIgnored(i) && i.provisions === 0).length}</div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <input type="text" placeholder="Search by name..."
            value={searchDisplay} onChange={e => handleSearchChange(e.target.value)}
            className="ca-search" />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
            {filteredItems.length} of {allItems.length} items
          </span>
        </div>

        {actionError && (
          <div style={{ padding: '8px 12px', background: 'var(--score-red-bg)', color: 'var(--score-red)',
            borderRadius: 'var(--radius-sm)', fontSize: '11px' }}>
            {actionError}
          </div>
        )}

        {loading ? (
          <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="ca-table" style={{ tableLayout: 'auto', minWidth: '1000px' }}>
              <thead>
                <tr>
                  <th className="clickable" style={{ maxWidth: '300px' }} onClick={() => toggleSort('display_name')}>
                    Name {sortBy === 'display_name' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th>Type</th>
                  <th>Stages</th>
                  <th className="clickable num" onClick={() => toggleSort('provisions')}>
                    Provs {sortBy === 'provisions' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('unique_users')}>
                    Unique Users {sortBy === 'unique_users' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="num">Experiences</th>
                  <th className="clickable num" onClick={() => toggleSort('success_ratio')}>
                    Success {sortBy === 'success_ratio' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('failure_ratio')}>
                    Failure {sortBy === 'failure_ratio' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th>First Prov</th>
                  <th>Last Prov</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map(item => {
                  const isExpanded = expanded.has(item.catalog_base_name)
                  const muted = isIgnored(item)
                  return (
                    <Fragment key={item.catalog_base_name}>
                      <tr className="clickable" onClick={() => toggleExpand(item.catalog_base_name)}
                        style={muted ? { opacity: 0.45 } : undefined}>
                        <td className="name" title={item.display_name} style={{ maxWidth: '300px' }}>
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {item.display_name}
                            {muted && <span className="ret-inline-badge ret-inline-badge--muted">muted</span>}
                          </div>
                          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--ff-mono)', marginTop: '1px' }}>
                            {item.catalog_base_name}
                          </div>
                        </td>
                        <td><span className="ca-env-tag ca-env-test">{item.content_type || '—'}</span></td>
                        <td>
                          {item.stages.map(s => (
                            <span key={s.ci_name} className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}>
                              {s.stage}
                            </span>
                          ))}
                        </td>
                        <td className="num">{item.provisions.toLocaleString()}</td>
                        <td className="num">{item.unique_users.toLocaleString()}</td>
                        <td className="num">{item.completions.toLocaleString()}</td>
                        <td className="num">{(item.success_ratio * 100).toFixed(1)}%</td>
                        <td className="num">{(item.failure_ratio * 100).toFixed(1)}%</td>
                        <td style={{ fontSize: '11px' }}>{item.first_provision || '—'}</td>
                        <td style={{ fontSize: '11px' }}>{item.last_provision || '—'}</td>
                      </tr>
                      {isExpanded && (
                        <tr className="ca-expanded-row">
                          <td colSpan={10}>
                            {item.stages.length > 0 && (
                              <div style={{ marginBottom: '8px' }}>
                                <div style={{ fontSize: '11px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-muted)' }}>
                                  Per-Environment Breakdown
                                </div>
                                <table className="ca-table" style={{ fontSize: '11px', marginBottom: 0 }}>
                                  <thead>
                                    <tr>
                                      <th>Environment</th>
                                      <th className="num">Provisions</th>
                                      <th className="num">Unique Users</th>
                                      <th className="num">Experiences</th>
                                      <th>First Provision</th>
                                      <th>Last Provision</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {item.stages.map(s => (
                                      <tr key={s.ci_name}>
                                        <td>
                                          <a href={s.catalog_url} target="_blank" rel="noreferrer"
                                            className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                                            onClick={e => e.stopPropagation()}>
                                            {s.stage}
                                          </a>
                                          <span style={{ marginLeft: '6px', color: 'var(--text-muted)', fontFamily: 'var(--ff-mono)', fontSize: '10px' }}>
                                            {s.ci_name}
                                          </span>
                                        </td>
                                        <td className="num">—</td>
                                        <td className="num">—</td>
                                        <td className="num">—</td>
                                        <td>—</td>
                                        <td>—</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px', fontStyle: 'italic' }}>
                                  Per-environment metrics require per-stage MCP queries (not yet implemented). Totals shown in main row.
                                </div>
                              </div>
                            )}
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center',
                              borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
                              {muted ? (
                                <button className="ret-action-btn" onClick={(e) => { e.stopPropagation(); handleUnignore(item.catalog_base_name) }}>
                                  Unmute
                                </button>
                              ) : (
                                <button className="ret-action-btn" onClick={(e) => { e.stopPropagation(); handleIgnore(item.catalog_base_name) }}
                                  title="Mute for 30 days">
                                  Mute 30d
                                </button>
                              )}
                              <button className="ret-action-btn ret-action-btn--primary"
                                onClick={(e) => { e.stopPropagation(); setDrawerItem(item) }}>
                                Retirement Workflow
                              </button>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      </div>{/* end browse-content */}
      {drawerItem && <WorkflowDrawer item={drawerItem as any} onClose={() => setDrawerItem(null)} onChanged={loadData} />}
    </div>
  )
}
