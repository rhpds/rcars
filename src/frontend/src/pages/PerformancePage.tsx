import { useState, useEffect, useCallback, useRef, Fragment } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, PerformanceItem } from '../services/api'
import { ScoreBreakdownPopover, scoreColor, scoreBg, fmt, num, fmtRoi } from '../components/performance/ScoreBreakdownPopover'
import { WorkflowDrawer } from '../components/performance/WorkflowDrawer'
import { useAuth } from '../hooks/useAuth'

type TimeWindow = '3m' | '6m' | '9m' | '12m'
type PerfFilter = 'all' | 'strong' | 'moderate' | 'low'
type StatusFilter = 'all' | 'none' | 'in_process' | 'started' | 'muted'
type SortField = 'performance_score' | 'provisions' | 'pipeline_touched' | 'touched_roi'
  | 'closed_amount' | 'closed_roi' | 'total_cost' | 'display_name'

const stageBadgeClass: Record<string, string> = {
  prod: 'ca-env-prod', event: 'ca-env-event', dev: 'ca-env-dev', test: 'ca-env-test',
}

const safeHref = (url: string | undefined) => url?.startsWith('http') ? url : `https://${url}`

function WorkflowInlineBadge({ status }: { status: string }) {
  const labels: Record<string, string> = { approved: 'recommended', notified: 'recommended', started: 'in progress' }
  const label = labels[status] || status
  return <span className="ret-inline-badge">{label}</span>
}

export function PerformancePage() {
  const { isCurator, canViewPerformance } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [channel, setChannel] = useState(searchParams.get('channel') === 'marketing' ? 'marketing' : 'sales')
  const [window_, setWindow] = useState<TimeWindow>((searchParams.get('window') as TimeWindow) || '12m')
  const [perfFilter, setPerfFilter] = useState<PerfFilter>((searchParams.get('performance') as PerfFilter) || 'all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>((searchParams.get('status') as StatusFilter) || 'all')
  const [selectedNamespaces, setSelectedNamespaces] = useState<Set<string>>(
    new Set(searchParams.get('namespace')?.split(',').filter(Boolean) || []))
  const [sortBy, setSortBy] = useState<SortField>((searchParams.get('sort') as SortField) || 'performance_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>(searchParams.get('order') === 'asc' ? 'asc' : 'desc')

  const emptyRanges = {
    provMin: '', provMax: '', touchedMin: '', touchedMax: '', closedMin: '', closedMax: '',
    costMin: '', costMax: '', usersMin: '', usersMax: '', expMin: '', expMax: '',
  }
  type RangeFilters = typeof emptyRanges
  const [rangeInputs, setRangeInputs] = useState<RangeFilters>({
    provMin: searchParams.get('provs_min') || '', provMax: searchParams.get('provs_max') || '',
    touchedMin: searchParams.get('touched_min') || '', touchedMax: searchParams.get('touched_max') || '',
    closedMin: searchParams.get('closed_min') || '', closedMax: searchParams.get('closed_max') || '',
    costMin: searchParams.get('cost_min') || '', costMax: searchParams.get('cost_max') || '',
    usersMin: searchParams.get('users_min') || '', usersMax: searchParams.get('users_max') || '',
    expMin: searchParams.get('exper_min') || '', expMax: searchParams.get('exper_max') || '',
  })
  const [appliedRanges, setAppliedRanges] = useState<RangeFilters>(rangeInputs)

  const [allItems, setAllItems] = useState<PerformanceItem[]>([])
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [addendumOpen, setAddendumOpen] = useState<Set<string>>(new Set())
  const [drawerItem, setDrawerItem] = useState<PerformanceItem | null>(null)
  const [scorePopover, setScorePopover] = useState<string | null>(null)
  const [scorePopoverRect, setScorePopoverRect] = useState<DOMRect | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const rangeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getPerformanceDashboard({
        sort_by: sortBy, sort_dir: sortDir,
        search: search || undefined,
        window: window_, channel,
        workflow_status: statusFilter !== 'all' && statusFilter !== 'muted' ? statusFilter : undefined,
      })
      setAllItems(data.items)
      setSyncedAt(data.synced_at)
    } finally { setLoading(false) }
  }, [sortBy, sortDir, search, window_, channel, statusFilter])

  useEffect(() => { loadData() }, [loadData])

  // Reset all filters when navigating to clean /analysis/performance (no params)
  useEffect(() => {
    if (searchParams.toString() === '') {
      setSearch('')
      setChannel('sales')
      setWindow('12m')
      setPerfFilter('all')
      setStatusFilter('all')
      setSelectedNamespaces(new Set())
      setSortBy('performance_score')
      setSortDir('desc')
      setRangeInputs(emptyRanges)
      setAppliedRanges(emptyRanges)
    }
  }, [searchParams])

  // URL sync effect (write only non-defaults)
  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    if (channel !== 'sales') params.channel = channel
    if (window_ !== '12m') params.window = window_
    if (perfFilter !== 'all') params.performance = perfFilter
    if (statusFilter !== 'all') params.status = statusFilter
    if (selectedNamespaces.size > 0) params.namespace = Array.from(selectedNamespaces).sort().join(',')
    if (sortBy !== 'performance_score') params.sort = sortBy
    if (sortDir !== 'desc') params.order = sortDir
    const rangeUrlMap: Record<keyof RangeFilters, string> = {
      provMin: 'provs_min', provMax: 'provs_max',
      touchedMin: 'touched_min', touchedMax: 'touched_max',
      closedMin: 'closed_min', closedMax: 'closed_max',
      costMin: 'cost_min', costMax: 'cost_max',
      usersMin: 'users_min', usersMax: 'users_max',
      expMin: 'exper_min', expMax: 'exper_max',
    }
    Object.entries(rangeUrlMap).forEach(([stateKey, urlKey]) => {
      if (appliedRanges[stateKey as keyof RangeFilters]) params[urlKey] = appliedRanges[stateKey as keyof RangeFilters]
    })
    setSearchParams(params, { replace: true })
  }, [search, channel, window_, perfFilter, statusFilter, selectedNamespaces, sortBy, sortDir, appliedRanges, setSearchParams])

  // Debounced range application
  useEffect(() => {
    if (rangeTimerRef.current) clearTimeout(rangeTimerRef.current)
    rangeTimerRef.current = setTimeout(() => {
      setAppliedRanges(rangeInputs)
    }, 300)
  }, [rangeInputs])

  const handleIgnore = async (baseName: string) => {
    try {
      const { ignored_until } = await api.ignoreItem(baseName)
      setAllItems(prev => prev.map(i => i.catalog_base_name === baseName ? { ...i, ignored_until } : i))
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Mute failed')
    }
  }

  const handleUnignore = async (baseName: string) => {
    try {
      await api.unignoreItem(baseName)
      setAllItems(prev => prev.map(i => i.catalog_base_name === baseName ? { ...i, ignored_until: null } : i))
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Unmute failed')
    }
  }

  const toggleExpand = (name: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const toggleAddendum = (name: string) => {
    setAddendumOpen(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(field)
      setSortDir(field === 'performance_score' ? 'desc' : 'desc')
    }
  }

  const [searchDisplay, setSearchDisplay] = useState(search)
  const handleSearchChange = (value: string) => {
    setSearchDisplay(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setSearch(value)
    }, 300)
  }

  const clearFilters = () => {
    setPerfFilter('all')
    setStatusFilter('all')
    setSelectedNamespaces(new Set())
    setRangeInputs(emptyRanges)
    setAppliedRanges(emptyRanges)
  }

  const isIgnored = (i: PerformanceItem) => !!i.ignored_until
  const activeItems = allItems.filter(i => !isIgnored(i))
  const recommendedCount = activeItems.filter(i => i.workflow_status === 'approved' || i.workflow_status === 'notified').length
  const inProgressCount = activeItems.filter(i => i.workflow_status === 'started').length

  const extractNs = (name: string) => name.split('.')[0]
  const statusBaseItems = statusFilter === 'muted' ? allItems.filter(isIgnored) : activeItems
  const availableNamespaces = (() => {
    const counts: Record<string, number> = {}
    for (const i of statusBaseItems) {
      const ns = extractNs(i.catalog_base_name)
      counts[ns] = (counts[ns] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]))
  })()
  const toggleNamespace = (ns: string) => {
    setSelectedNamespaces(prev => {
      const next = new Set(prev)
      if (next.has(ns)) next.delete(ns); else next.add(ns)
      return next
    })
  }
  const nsMatch = (i: PerformanceItem) =>
    selectedNamespaces.size === 0 || selectedNamespaces.has(extractNs(i.catalog_base_name))
  const nsActiveItems = activeItems.filter(nsMatch)

  const perfBandFiltered = (() => {
    const base = statusFilter === 'muted' ? allItems.filter(isIgnored) : activeItems
    if (perfFilter === 'all') return base.filter(nsMatch)
    if (perfFilter === 'strong') return base.filter(i => i.performance_score >= 55 && nsMatch(i))
    if (perfFilter === 'moderate') return base.filter(i => i.performance_score >= 35 && i.performance_score < 55 && nsMatch(i))
    return base.filter(i => i.performance_score < 35 && nsMatch(i))
  })()

  const hasActiveRanges = Object.values(appliedRanges).some(v => v !== '')
  const rangeFiltered = (() => {
    if (!hasActiveRanges) return perfBandFiltered
    const n = (s: string) => Number(s)
    return perfBandFiltered.filter(i => {
      const r = appliedRanges
      if (r.provMin && i.provisions < n(r.provMin)) return false
      if (r.provMax && i.provisions > n(r.provMax)) return false
      if (r.touchedMin && i.pipeline_touched < n(r.touchedMin)) return false
      if (r.touchedMax && i.pipeline_touched > n(r.touchedMax)) return false
      if (r.closedMin && i.closed_amount < n(r.closedMin)) return false
      if (r.closedMax && i.closed_amount > n(r.closedMax)) return false
      if (r.costMin && i.total_cost < n(r.costMin)) return false
      if (r.costMax && i.total_cost > n(r.costMax)) return false
      if (r.expMin && (i.completions || 0) < n(r.expMin)) return false
      if (r.expMax && (i.completions || 0) > n(r.expMax)) return false
      if (r.usersMin && (i.unique_users || 0) < n(r.usersMin)) return false
      if (r.usersMax && (i.unique_users || 0) > n(r.usersMax)) return false
      return true
    })
  })()
  const visibleItems = rangeFiltered

  const totalCost = nsActiveItems.reduce((s, i) => s + i.total_cost, 0)
  const totalClosed = nsActiveItems.reduce((s, i) => s + i.closed_amount, 0)
  const strongCount = nsActiveItems.filter(i => i.performance_score >= 55).length
  const moderateCount = nsActiveItems.filter(i => i.performance_score >= 35 && i.performance_score < 55).length
  const lowCount = nsActiveItems.filter(i => i.performance_score < 35).length

  const syncAge = syncedAt
    ? `${Math.round((Date.now() - new Date(syncedAt).getTime()) / 3600000)}h ago`
    : 'never'

  const exportCsv = () => {
    const headers = ['Name', 'Base Name', 'Score', 'Provisions', 'Touched', 'T-ROI', 'Closed', 'C-ROI', 'Cost', 'Status', 'Jira']
    const rows = visibleItems.map(i => {
      const troi = num(i.pipeline_touched) > 0 && num(i.total_cost) > 0 ? (num(i.pipeline_touched) / num(i.total_cost)).toFixed(1) : ''
      const croi = num(i.closed_amount) > 0 && num(i.total_cost) > 0 ? (num(i.closed_amount) / num(i.total_cost)).toFixed(1) : ''
      return [
        `"${(i.display_name || '').replace(/"/g, '""')}"`,
        i.catalog_base_name,
        i.performance_score,
        i.provisions,
        i.pipeline_touched,
        troi,
        i.closed_amount,
        croi,
        i.total_cost,
        i.workflow_status || '',
        i.jira_key || '',
      ].join(',')
    })
    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `rcars-performance-${channel}-${window_}-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!canViewPerformance) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <h3>Access Restricted</h3>
        <p>Performance metrics are not publicly available. Contact an administrator for access.</p>
      </div>
    )
  }

  return (
    <div className="browse-layout">
      <div className="browse-content">
      <div className="browse-filter-sidebar">
        <div className="browse-filter-group">
          <div className="browse-filter-group-label">Performance</div>
          <div className="ret-filter-group">
            <button onClick={() => setPerfFilter('all')}
              className={`ret-filter-group__btn${perfFilter === 'all' ? ' active' : ''}`}>
              All ({nsActiveItems.length})
            </button>
            <button onClick={() => setPerfFilter('strong')}
              className={`ret-filter-group__btn${perfFilter === 'strong' ? ' active' : ''}`}>
              <span className="ret-filter-group__dot ret-filter-group__dot--green" />Strong ({strongCount})
            </button>
            <button onClick={() => setPerfFilter('moderate')}
              className={`ret-filter-group__btn${perfFilter === 'moderate' ? ' active' : ''}`}>
              <span className="ret-filter-group__dot ret-filter-group__dot--amber" />Moderate ({moderateCount})
            </button>
            <button onClick={() => setPerfFilter('low')}
              className={`ret-filter-group__btn${perfFilter === 'low' ? ' active' : ''}`}>
              <span className="ret-filter-group__dot ret-filter-group__dot--red" />Low ({lowCount})
            </button>
          </div>
        </div>

        <div className="browse-filter-group">
          <div className="browse-filter-group-label">Metrics</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11px' }}>
            {([
              ['Provisions', 'provMin', 'provMax'],
              ['Completions', 'expMin', 'expMax'],
              ['Unique Users', 'usersMin', 'usersMax'],
              ['Touched ($)', 'touchedMin', 'touchedMax'],
              ['Closed ($)', 'closedMin', 'closedMax'],
              ['Cost ($)', 'costMin', 'costMax'],
            ] as [string, keyof RangeFilters, keyof RangeFilters][]).map(([label, minKey, maxKey]) => (
              <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>{label}</span>
                <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                  <input type="number" className="browse-drawer-input"
                    placeholder="Min" value={rangeInputs[minKey]}
                    onChange={e => setRangeInputs(p => ({ ...p, [minKey]: e.target.value }))}
                    style={{ width: '60px', fontSize: '11px' }} />
                  <span style={{ color: 'var(--text-muted)' }}>–</span>
                  <input type="number" className="browse-drawer-input"
                    placeholder="Max" value={rangeInputs[maxKey]}
                    onChange={e => setRangeInputs(p => ({ ...p, [maxKey]: e.target.value }))}
                    style={{ width: '60px', fontSize: '11px' }} />
                </div>
              </div>
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
              <label key={ns} style={{
                display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 8px',
                cursor: 'pointer', fontSize: '11px',
              }}>
                <input type="checkbox" checked={selectedNamespaces.has(ns)} onChange={() => toggleNamespace(ns)} />
                <span>{ns}</span>
                <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>
              </label>
            ))}
          </div>
        </div>

        {isCurator && (
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Retirement Status</div>
            <div className="ret-filter-group">
              {([['all', 'All'], ['none', 'No Action'], ['in_process', `Recommended (${recommendedCount})`], ['started', `In Progress (${inProgressCount})`], ['muted', 'Muted']] as [StatusFilter, string][]).map(([f, label]) => (
                <button key={f} onClick={() => setStatusFilter(f)}
                  className={`ret-filter-group__btn${statusFilter === f ? ' active' : ''}`}>
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: '16px' }}>
          <button onClick={clearFilters}
            style={{ background: 'none', border: 'none', color: 'var(--score-amber)', fontSize: '11px', cursor: 'pointer', padding: 0 }}>
            Clear filters
          </button>
        </div>
      </div>

      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'auto', padding: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Performance</h3>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Synced {syncAge}</span>
        </div>

        <div className="ca-tab-bar">
          <button className={channel === 'sales' ? 'active' : ''} onClick={() => setChannel('sales')}>Sales</button>
          <button disabled title="Marketing channel — Interactive Labs self-paced usage. Enabled when marketing data is synced.">
            Marketing
          </button>
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', gap: '4px' }}>
            {([['3m', '3 Mo'], ['6m', '6 Mo'], ['9m', '9 Mo'], ['12m', '1 Yr']] as [TimeWindow, string][]).map(([w, label]) => (
              <button key={w} onClick={() => setWindow(w)}
                className={`ca-filter-btn${window_ === w ? ' active' : ''}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '-8px' }}>
          Sales: RHDP provisioning tied to sales pipeline (source: rhdp). Marketing: self-paced web usage (source: Interactive Labs).
        </div>

        <div className="ca-stats-grid">
          <div className="ret-stat-card ret-stat-card--blue">
            <div className="ret-stat-label">Total Items</div>
            <div className="ret-stat-value ca-color-blue">{nsActiveItems.length}</div>
          </div>
          <div className="ret-stat-card ret-stat-card--green">
            <div className="ret-stat-label">Strong (≥55)</div>
            <div className="ret-stat-value ca-color-green">{strongCount}</div>
          </div>
          <div className="ret-stat-card ret-stat-card--amber">
            <div className="ret-stat-label">Moderate (35–54)</div>
            <div className="ret-stat-value ca-color-orange">{moderateCount}</div>
          </div>
          <div className="ret-stat-card ret-stat-card--red">
            <div className="ret-stat-label">Low (&lt;35)</div>
            <div className="ret-stat-value ca-color-red">{lowCount}</div>
          </div>
          <div className="ret-stat-card">
            <div className="ret-stat-label">Total Cost</div>
            <div className="ret-stat-value">{fmt(totalCost)}</div>
          </div>
          <div className="ret-stat-card">
            <div className="ret-stat-label">Total Closed</div>
            <div className="ret-stat-value">{fmt(totalClosed)}</div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <input
            type="text" placeholder="Search by name..."
            value={searchDisplay} onChange={e => handleSearchChange(e.target.value)}
            className="ca-search"
          />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
            {visibleItems.length} of {nsActiveItems.length} items
          </span>
          <button onClick={exportCsv}
            style={{ background: 'var(--bg-control)', border: '1px solid var(--border-section)',
              borderRadius: 'var(--radius-sm)', padding: '4px 10px', cursor: 'pointer', fontSize: '11px' }}>
            Export CSV
          </button>
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
                  <th className="clickable num" onClick={() => toggleSort('performance_score')}>
                    Score {sortBy === 'performance_score' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('provisions')}>
                    Provs {sortBy === 'provisions' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('pipeline_touched')}>
                    Touched {sortBy === 'pipeline_touched' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num muted" onClick={() => toggleSort('touched_roi')}>
                    T-ROI {sortBy === 'touched_roi' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('closed_amount')}>
                    Closed {sortBy === 'closed_amount' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num muted" onClick={() => toggleSort('closed_roi')}>
                    C-ROI {sortBy === 'closed_roi' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('total_cost')}>
                    Cost {sortBy === 'total_cost' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="num">Data</th>
                </tr>
              </thead>
              <tbody>
                {visibleItems.map(item => {
                  const isExpanded = expanded.has(item.catalog_base_name)
                  const muted = isIgnored(item)
                  return (
                    <Fragment key={item.catalog_base_name}>
                      <tr className="clickable" onClick={() => toggleExpand(item.catalog_base_name)}
                        style={muted ? { opacity: 0.45 } : undefined}>
                        <td className="name" title={item.display_name} style={{ maxWidth: '300px' }}>
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {item.display_name}
                            {item.workflow_status && <WorkflowInlineBadge status={item.workflow_status} />}
                            {muted && <span className="ret-inline-badge ret-inline-badge--muted">muted</span>}
                          </div>
                          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--ff-mono)', marginTop: '1px' }}>{item.catalog_base_name}</div>
                        </td>
                        <td className="num" style={{ position: 'relative' }}>
                          <span className="ca-score-badge" style={{ background: scoreBg(item.performance_score), color: scoreColor(item.performance_score), cursor: 'pointer' }}
                            onClick={(e) => { e.stopPropagation(); const target = e.currentTarget; setScorePopoverRect(target.getBoundingClientRect()); setScorePopover(scorePopover === item.catalog_base_name ? null : item.catalog_base_name) }}>
                            {item.performance_score}
                          </span>
                          {scorePopover === item.catalog_base_name && item.score_breakdown && (
                            <ScoreBreakdownPopover breakdown={item.score_breakdown} onClose={() => setScorePopover(null)} anchorRect={scorePopoverRect} />
                          )}
                        </td>
                        <td className="num">{item.provisions.toLocaleString()}</td>
                        <td className="num">{fmt(item.pipeline_touched)}</td>
                        <td className="num muted">{fmtRoi(item.pipeline_touched, item.total_cost)}</td>
                        <td className="num">{fmt(item.closed_amount)}</td>
                        <td className="num muted">{fmtRoi(item.closed_amount, item.total_cost)}</td>
                        <td className="num">{fmt(item.total_cost)}</td>
                        <td className="num">
                          {item.channels_present.includes('rhdp') && <span className="ca-env-tag ca-env-prod" title="Sales data (RHDP)">S</span>}
                          {item.channels_present.includes('interactive_labs') && <span className="ca-env-tag ca-env-dev" title="Marketing data (Interactive Labs)">M</span>}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="ca-expanded-row">
                          <td colSpan={9}>
                            <div className="ca-detail">
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Environments</span>
                                <span className="ca-detail-value">
                                  {item.stages.map(s => (
                                    <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(item.display_name)}`} target="_blank" rel="noreferrer"
                                      className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                                      onClick={e => e.stopPropagation()}>
                                      {s.stage}
                                    </a>
                                  ))}
                                  {!item.has_content && item.catalog_url && (
                                    <a href={safeHref(item.catalog_url)} target="_blank" rel="noreferrer"
                                      className="ca-env-tag ca-env-test"
                                      onClick={e => e.stopPropagation()}>
                                      catalog
                                    </a>
                                  )}
                                  {item.has_content && item.stages.length === 0 && <span className="ca-color-muted">none</span>}
                                </span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Unique Users</span>
                                <span className="ca-detail-value">{item.unique_users.toLocaleString()}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Completions</span>
                                <span className="ca-detail-value">{item.completions.toLocaleString()}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Cost / Provision</span>
                                <span className="ca-detail-value">${num(item.avg_cost_per_provision).toFixed(2)}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Success</span>
                                <span className="ca-detail-value">{(num(item.success_ratio) * 100).toFixed(1)}%</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Failure</span>
                                <span className="ca-detail-value">{(num(item.failure_ratio) * 100).toFixed(1)}%</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">First Activity</span>
                                <span className="ca-detail-value">{item.first_activity || 'N/A'}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Last Activity</span>
                                <span className="ca-detail-value">{item.last_activity || 'N/A'}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Category</span>
                                <span className="ca-detail-value">{item.category || '—'}</span>
                              </div>
                            </div>

                            {item.marketing && (
                              <div style={{ gridColumn: '1 / -1', border: '1px solid var(--border-subtle)',
                                borderRadius: 'var(--radius-sm)', padding: '8px 12px', marginTop: '6px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
                                  onClick={e => { e.stopPropagation(); toggleAddendum(item.catalog_base_name) }}>
                                  <span className="ca-env-tag ca-env-dev">M</span>
                                  <span style={{ fontWeight: 600, fontSize: '12px' }}>Marketing Data</span>
                                  <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Interactive Labs</span>
                                  {item.marketing.score != null && (
                                    <span className="ca-score-badge" style={{ marginLeft: 'auto',
                                      background: scoreBg(item.marketing.score), color: scoreColor(item.marketing.score) }}>
                                      {item.marketing.score}
                                    </span>
                                  )}
                                </div>
                                {addendumOpen.has(item.catalog_base_name) && (
                                  <div className="ca-detail" style={{ marginTop: '6px' }}>
                                    <div className="ca-detail-item">
                                      <span className="ca-detail-label">IL Provisions</span>
                                      <span className="ca-detail-value">{item.marketing.provisions.toLocaleString()}</span>
                                    </div>
                                    <div className="ca-detail-item">
                                      <span className="ca-detail-label">Unique Users</span>
                                      <span className="ca-detail-value">{item.marketing.unique_users.toLocaleString()}</span>
                                    </div>
                                    <div className="ca-detail-item">
                                      <span className="ca-detail-label">Completions</span>
                                      <span className="ca-detail-value">{item.marketing.completions.toLocaleString()}</span>
                                    </div>
                                    <div className="ca-detail-item">
                                      <span className="ca-detail-label">Page Views</span>
                                      <span className="ca-detail-value">{item.marketing.page_views.toLocaleString()}</span>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                            {isCurator && (
                              <div style={{ marginTop: '8px', display: 'flex', gap: '8px', alignItems: 'center',
                                borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
                                {muted ? (
                                  <button className="ret-action-btn" onClick={(e) => { e.stopPropagation(); handleUnignore(item.catalog_base_name) }}>
                                    Unmute
                                  </button>
                                ) : (
                                  <button className="ret-action-btn" onClick={(e) => { e.stopPropagation(); handleIgnore(item.catalog_base_name) }}
                                    title="Mute this item for 30 days — removes it from counts and filters">
                                    Mute 30d
                                  </button>
                                )}
                                <button className="ret-action-btn ret-action-btn--primary" onClick={(e) => { e.stopPropagation(); setDrawerItem(item) }}>
                                  Retirement Workflow
                                </button>
                              </div>
                            )}
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
