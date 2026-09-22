import { useState, useEffect, useCallback, useRef, Fragment } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, RetirementItem } from '../services/api'
import { WorkflowDrawer, WorkflowItem } from '../components/performance/WorkflowDrawer'
import { useAuth } from '../hooks/useAuth'

type TimeWindow = '6m' | '12m'
type StatusFilter = 'all' | 'recommended' | 'in_progress' | 'retired'
type SortField = 'display_name' | 'provisions' | 'unique_users' | 'experiences' | 'success_ratio'

const stageBadgeClass: Record<string, string> = {
  prod: 'ca-env-prod', event: 'ca-env-event', dev: 'ca-env-dev', test: 'ca-env-test',
}

const statusLabels: Record<string, string> = {
  recommended: 'Recommended',
  in_progress: 'In Progress',
  retired: 'Retired',
}

const statusBadgeClass: Record<string, string> = {
  recommended: 'ret-inline-badge',
  in_progress: 'ret-inline-badge',
  retired: 'ret-inline-badge ret-inline-badge--muted',
}

function fmtDate(d: string | null) {
  if (!d) return '—'
  const date = d.includes('T') ? new Date(d) : new Date(d + 'T00:00:00')
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function fmtEmail(email: string | null) {
  if (!email) return '—'
  return email.replace(/@.*/, '')
}

export function RetirementPage() {
  const { isCurator, isAdmin } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [searchDisplay, setSearchDisplay] = useState(search)
  const [window_, setWindow] = useState<TimeWindow>((searchParams.get('window') as TimeWindow) || '12m')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>((searchParams.get('status') as StatusFilter) || 'all')
  const [selectedNamespaces, setSelectedNamespaces] = useState<Set<string>>(
    new Set(searchParams.get('namespace')?.split(',').filter(Boolean) || []))
  const [sortBy, setSortBy] = useState<SortField>((searchParams.get('sort') as SortField) || 'display_name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>(searchParams.get('order') === 'desc' ? 'desc' : 'asc')

  const [allItems, setAllItems] = useState<RetirementItem[]>([])
  const [earliestRetiredAt, setEarliestRetiredAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [drawerItem, setDrawerItem] = useState<WorkflowItem | null>(null)

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestRef = useRef(0)

  const loadData = useCallback(async () => {
    const reqId = ++requestRef.current
    setLoading(true)
    try {
      const data = await api.getRetirementDashboard({
        search: search || undefined,
        window: window_,
      })
      if (reqId !== requestRef.current) return
      setAllItems(data.items)
      setEarliestRetiredAt(data.earliest_retired_at)
    } finally {
      if (reqId === requestRef.current) setLoading(false)
    }
  }, [search, window_])

  useEffect(() => { loadData() }, [loadData])

  // URL sync
  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    if (window_ !== '12m') params.window = window_
    if (statusFilter !== 'all') params.status = statusFilter
    if (sortBy !== 'display_name') params.sort = sortBy
    if (sortDir !== 'asc') params.order = sortDir
    if (selectedNamespaces.size > 0) params.namespace = Array.from(selectedNamespaces).sort().join(',')
    setSearchParams(params, { replace: true })
  }, [search, window_, statusFilter, sortBy, sortDir, selectedNamespaces, setSearchParams])

  const handleSearchChange = (value: string) => {
    setSearchDisplay(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => setSearch(value), 300)
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
    else { setSortBy(field); setSortDir(field === 'display_name' ? 'asc' : 'desc') }
  }

  const extractNs = (name: string) => name.split('.')[0]

  // Client-side filters
  const filteredItems = allItems.filter(i => {
    if (statusFilter !== 'all' && i.effective_status !== statusFilter) return false
    if (selectedNamespaces.size > 0 && !selectedNamespaces.has(extractNs(i.catalog_base_name))) return false
    return true
  })

  // Client-side sort
  const sortedItems = [...filteredItems].sort((a, b) => {
    const mul = sortDir === 'asc' ? 1 : -1
    if (sortBy === 'display_name') return mul * (a.display_name || '').localeCompare(b.display_name || '')
    const av = (a[sortBy as keyof RetirementItem] as number) ?? 0
    const bv = (b[sortBy as keyof RetirementItem] as number) ?? 0
    return mul * (av - bv)
  })

  // Counts
  const recommendedCount = allItems.filter(i => i.effective_status === 'recommended').length
  const inProgressCount = allItems.filter(i => i.effective_status === 'in_progress').length
  const retiredCount = allItems.filter(i => i.effective_status === 'retired').length

  // Namespace facets
  const availableNamespaces = (() => {
    const counts: Record<string, number> = {}
    for (const i of allItems) {
      const ns = extractNs(i.catalog_base_name)
      counts[ns] = (counts[ns] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]))
  })()

  const toggleNamespace = (ns: string) => {
    setSelectedNamespaces(prev => {
      const next = new Set(prev)
      next.has(ns) ? next.delete(ns) : next.add(ns)
      return next
    })
  }

  const clearFilters = () => {
    setStatusFilter('all')
    setSelectedNamespaces(new Set())
  }

  if (!isCurator && !isAdmin) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <h3>Access Restricted</h3>
        <p>Retirement report is available to curators and admins only.</p>
      </div>
    )
  }

  return (
    <div className="browse-layout">
      <div className="browse-content">
      <div className="browse-filter-sidebar">
        <div className="browse-filter-group">
          <div className="browse-filter-group-label">Status</div>
          <div className="ret-filter-group">
            {([['all', `All (${allItems.length})`], ['recommended', `Recommended (${recommendedCount})`], ['in_progress', `In Progress (${inProgressCount})`], ['retired', `Retired (${retiredCount})`]] as [StatusFilter, string][]).map(([f, label]) => (
              <button key={f} onClick={() => setStatusFilter(f)}
                className={`ret-filter-group__btn${statusFilter === f ? ' active' : ''}`}>
                {label}
              </button>
            ))}
          </div>
        </div>

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
                <input type="checkbox" checked={selectedNamespaces.has(ns)} onChange={() => toggleNamespace(ns)} />
                <span>{ns}</span>
                <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>
              </label>
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
          <h3 style={{ margin: 0 }}>Retirement Report</h3>
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
            <div className="ret-stat-label">Total</div>
            <div className="ret-stat-value ca-color-blue">{allItems.length}</div>
          </div>
          <div className="ret-stat-card ret-stat-card--amber">
            <div className="ret-stat-label">Recommended</div>
            <div className="ret-stat-value ca-color-orange">{recommendedCount}</div>
          </div>
          <div className="ret-stat-card ret-stat-card--red">
            <div className="ret-stat-label">In Progress</div>
            <div className="ret-stat-value ca-color-red">{inProgressCount}</div>
          </div>
          <div className="ret-stat-card">
            <div className="ret-stat-label">Retired</div>
            <div className="ret-stat-value">{retiredCount}</div>
            {earliestRetiredAt && (
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                (since {fmtDate(earliestRetiredAt)})
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <input type="text" placeholder="Search by name..."
            value={searchDisplay} onChange={e => handleSearchChange(e.target.value)}
            className="ca-search" />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
            {sortedItems.length} of {allItems.length} items
          </span>
        </div>

        {loading ? (
          <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="ca-table" style={{ tableLayout: 'auto', minWidth: '900px' }}>
              <thead>
                <tr>
                  <th className="clickable" style={{ maxWidth: '280px' }} onClick={() => toggleSort('display_name')}>
                    Name {sortBy === 'display_name' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th>Status</th>
                  <th>Type</th>
                  <th className="clickable num" onClick={() => toggleSort('provisions')}>
                    Provisions {sortBy === 'provisions' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('unique_users')}>
                    Unique Users {sortBy === 'unique_users' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('experiences')}>
                    Experiences {sortBy === 'experiences' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('success_ratio')}>
                    Success {sortBy === 'success_ratio' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th>First</th>
                  <th>Last</th>
                </tr>
              </thead>
              <tbody>
                {sortedItems.map(item => {
                  const isExpanded = expanded.has(item.catalog_base_name)
                  return (
                    <Fragment key={item.catalog_base_name}>
                      <tr className="clickable" onClick={() => toggleExpand(item.catalog_base_name)}
                        style={item.effective_status === 'retired' ? { opacity: 0.65 } : undefined}>
                        <td className="name" title={item.display_name} style={{ maxWidth: '280px' }}>
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {item.display_name}
                          </div>
                          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--ff-mono)', marginTop: '1px' }}>
                            {item.catalog_base_name}
                          </div>
                        </td>
                        <td>
                          <span className={statusBadgeClass[item.effective_status] || 'ret-inline-badge'}>
                            {statusLabels[item.effective_status] || item.effective_status}
                          </span>
                        </td>
                        <td><span className="ca-env-tag ca-env-test">{item.content_type || '—'}</span></td>
                        <td className="num">{item.provisions.toLocaleString()}</td>
                        <td className="num">{item.unique_users.toLocaleString()}</td>
                        <td className="num">{item.experiences.toLocaleString()}</td>
                        <td className="num">{(item.success_ratio * 100).toFixed(1)}%</td>
                        <td>{fmtDate(item.first_activity)}</td>
                        <td>{fmtDate(item.last_activity)}</td>
                      </tr>
                      {isExpanded && (
                        <tr className="ca-expanded-row">
                          <td colSpan={9}>
                            <div className="ca-detail">
                              {item.jira_key && (
                                <div className="ca-detail-item">
                                  <span className="ca-detail-label">Jira</span>
                                  <span className="ca-detail-value">
                                    <a href={`https://redhat.atlassian.net/browse/${item.jira_key}`}
                                      target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}>
                                      {item.jira_key}
                                    </a>
                                  </span>
                                </div>
                              )}
                              {item.retirement_target_date && (
                                <div className="ca-detail-item">
                                  <span className="ca-detail-label">Target Date</span>
                                  <span className="ca-detail-value">{fmtDate(item.retirement_target_date)}</span>
                                </div>
                              )}
                              {item.performance_score != null && (
                                <div className="ca-detail-item">
                                  <span className="ca-detail-label">Score</span>
                                  <span className="ca-detail-value">{item.performance_score}</span>
                                </div>
                              )}
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Environments</span>
                                <span className="ca-detail-value">
                                  {item.stages.length > 0
                                    ? item.stages.map(s => (
                                        <span key={s.ci_name} className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}>
                                          {s.stage}
                                        </span>
                                      ))
                                    : <span className="ca-color-muted">none</span>}
                                </span>
                              </div>
                              {item.step_approved_by && (
                                <div className="ca-detail-item">
                                  <span className="ca-detail-label">Approved By</span>
                                  <span className="ca-detail-value">
                                    {fmtEmail(item.step_approved_by)} on {fmtDate(item.step_approved_at)}
                                  </span>
                                </div>
                              )}
                              {item.approval_reason && (
                                <div className="ca-detail-item">
                                  <span className="ca-detail-label">Reason</span>
                                  <span className="ca-detail-value">{item.approval_reason}</span>
                                </div>
                              )}
                              {item.step_notified_by && (
                                <div className="ca-detail-item">
                                  <span className="ca-detail-label">Notified By</span>
                                  <span className="ca-detail-value">
                                    {fmtEmail(item.step_notified_by)} on {fmtDate(item.step_notified_at)}
                                  </span>
                                </div>
                              )}
                              {item.step_started_by && (
                                <div className="ca-detail-item">
                                  <span className="ca-detail-label">Started By</span>
                                  <span className="ca-detail-value">
                                    {fmtEmail(item.step_started_by)} on {fmtDate(item.step_started_at)}
                                  </span>
                                </div>
                              )}
                              {item.retired_at && (
                                <div className="ca-detail-item">
                                  <span className="ca-detail-label">Retired</span>
                                  <span className="ca-detail-value">{fmtDate(item.retired_at)}</span>
                                </div>
                              )}
                              {item.replacement_ci && (
                                <div className="ca-detail-item">
                                  <span className="ca-detail-label">Replacement</span>
                                  <span className="ca-detail-value">{item.replacement_name || item.replacement_ci}</span>
                                </div>
                              )}
                              {item.curator_notes && (
                                <div className="ca-detail-item" style={{ gridColumn: '1 / -1' }}>
                                  <span className="ca-detail-label">Notes</span>
                                  <span className="ca-detail-value">{item.curator_notes}</span>
                                </div>
                              )}
                            </div>
                            <div style={{ marginTop: '8px', display: 'flex', gap: '8px', alignItems: 'center',
                              borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
                              <button className="ret-action-btn ret-action-btn--primary"
                                onClick={(e) => { e.stopPropagation(); setDrawerItem(item as WorkflowItem) }}>
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
      {drawerItem && <WorkflowDrawer item={drawerItem} onClose={() => setDrawerItem(null)} onChanged={loadData} />}
    </div>
  )
}
