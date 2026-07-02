import { useState, useEffect, useCallback, Fragment } from 'react'
import { api, ReportingMetricsItem } from '../services/api'
import type { RetirementWorkflow } from '../services/api'

function safeHref(url: string | null): string {
  if (!url) return '#'
  try { return ['http:', 'https:'].includes(new URL(url).protocol) ? url : '#' }
  catch { return '#' }
}

type SortField = 'retirement_score' | 'provisions' | 'total_cost' | 'closed_amount' | 'touched_amount' | 'display_name'
type ScoreFilter = 'all' | 'high' | 'review' | 'keepers'
type AgeFilter = 'all' | 'old' | 'med' | 'new'
type RetirementTab = 'prod' | 'no-prod'
type TimeWindow = '1q' | '2q' | '3q' | '1y'
type WorkflowFilter = 'all' | 'none' | 'in_process' | 'started' | 'retired'

const fmt = (n: number) => {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toFixed(0)}`
}

const fmtRoi = (amount: number, cost: number) => {
  if (cost <= 0 || amount <= 0) return '—'
  return `${(amount / cost).toFixed(1)}x`
}

const scoreColor = (score: number) => score >= 55 ? 'var(--score-red)' : score >= 35 ? 'var(--score-amber)' : 'var(--score-green)'
const scoreBg = (score: number) => score >= 55 ? 'var(--score-red-bg)' : score >= 35 ? 'var(--score-amber-bg)' : 'var(--score-green-bg)'

const stageBadgeClass: Record<string, string> = {
  prod: 'ca-env-prod', event: 'ca-env-event', dev: 'ca-env-dev', test: 'ca-env-test',
}

const ageDays = (dateStr: string | null): number | null => {
  if (!dateStr) return null
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
}

const ageColor = (days: number | null) => {
  if (days === null) return 'var(--text-muted)'
  if (days > 365) return 'var(--score-red)'
  if (days > 180) return 'var(--score-amber)'
  return 'var(--text-muted)'
}

export function RetirementPage() {
  const [tab, setTab] = useState<RetirementTab>('prod')
  const [items, setItems] = useState<ReportingMetricsItem[]>([])
  const [allItems, setAllItems] = useState<ReportingMetricsItem[]>([])
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortField>('retirement_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>('all')
  const [ageFilter, setAgeFilter] = useState<AgeFilter>('all')
  const [search, setSearch] = useState('')
  const [window, setWindow] = useState<TimeWindow>('1y')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [workflowFilter, setWorkflowFilter] = useState<WorkflowFilter>('all')
  const [drawerItem, setDrawerItem] = useState<ReportingMetricsItem | null>(null)
  const [drawerWorkflow, setDrawerWorkflow] = useState<RetirementWorkflow | null>(null)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [approvalReason, setApprovalReason] = useState('')
  const [replacementCi, setReplacementCi] = useState('')
  const [replacementName, setReplacementName] = useState('')
  const [notesText, setNotesText] = useState('')
  const [targetDays, setTargetDays] = useState(30)
  const [jiraProject, setJiraProject] = useState('RHDPCD')
  const [actionLoading, setActionLoading] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const minScore = scoreFilter === 'high' ? 55 : scoreFilter === 'review' ? 35 : scoreFilter === 'keepers' ? 0 : undefined
      const maxForKeepers = scoreFilter === 'keepers'
      const data = await api.getRetirementDashboard({
        sort_by: tab === 'prod' ? sortBy : 'provisions',
        sort_dir: tab === 'prod' ? sortDir : 'desc',
        min_score: tab === 'prod' ? minScore : undefined,
        has_prod: tab === 'prod' ? true : false,
        search: search || undefined,
        window: tab === 'prod' ? window : undefined,
        workflow_status: workflowFilter !== 'all' ? workflowFilter : undefined,
      })
      let filtered = data.items
      if (tab === 'prod' && maxForKeepers) {
        filtered = filtered.filter(i => i.retirement_score < 35)
      } else if (tab === 'prod' && scoreFilter === 'review') {
        filtered = filtered.filter(i => i.retirement_score < 55)
      }
      setItems(filtered)
      setAllItems(data.items)
      setSyncedAt(data.synced_at)
    } finally {
      setLoading(false)
    }
  }, [tab, sortBy, sortDir, scoreFilter, search, window, workflowFilter])

  useEffect(() => { loadData() }, [loadData])

  useEffect(() => {
    setExpanded(new Set())
    setScoreFilter('all')
    setAgeFilter('all')
    setSearch('')
    setSortBy(tab === 'prod' ? 'retirement_score' : 'provisions')
    setSortDir(tab === 'prod' ? 'asc' : 'desc')
  }, [tab])

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(field)
      setSortDir('desc')
    }
  }

  const toggleExpand = (name: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const openDrawer = async (item: ReportingMetricsItem) => {
    setDrawerItem(item)
    setDrawerLoading(true)
    try {
      const { workflow } = await api.getRetirementWorkflow(item.catalog_base_name)
      setDrawerWorkflow(workflow)
      setApprovalReason(workflow?.approval_reason || '')
      setReplacementCi(workflow?.replacement_ci || '')
      setReplacementName(workflow?.replacement_name || '')
      setNotesText(workflow?.curator_notes || '')
      setTargetDays(30)
      setJiraProject(workflow?.jira_project || 'RHDPCD')
    } catch { setDrawerWorkflow(null) }
    setDrawerLoading(false)
  }

  const handleReview = async () => {
    if (!drawerItem) return
    setActionLoading(true)
    try {
      const { workflow } = await api.reviewRetirementItem(drawerItem.catalog_base_name)
      setDrawerWorkflow(workflow)
      loadData()
    } catch (e) { console.error(e) }
    setActionLoading(false)
  }

  const handleApprove = async () => {
    if (!drawerItem || !approvalReason.trim()) return
    setActionLoading(true)
    try {
      const { workflow } = await api.approveRetirementItem(
        drawerItem.catalog_base_name, approvalReason,
        replacementCi || undefined, replacementName || undefined
      )
      setDrawerWorkflow(workflow)
      loadData()
    } catch (e) { console.error(e) }
    setActionLoading(false)
  }

  const handleNotify = async () => {
    if (!drawerItem) return
    setActionLoading(true)
    try {
      const { workflow } = await api.notifyRetirementOwner(drawerItem.catalog_base_name)
      setDrawerWorkflow(workflow)
      loadData()
    } catch (e) { console.error(e) }
    setActionLoading(false)
  }

  const handleStart = async () => {
    if (!drawerItem) return
    setActionLoading(true)
    try {
      const { workflow } = await api.startRetirement(drawerItem.catalog_base_name, targetDays, jiraProject)
      setDrawerWorkflow(workflow)
      loadData()
    } catch (e) { console.error(e) }
    setActionLoading(false)
  }

  const handleCancel = async () => {
    if (!drawerItem) return
    setActionLoading(true)
    try {
      await api.cancelRetirementWorkflow(drawerItem.catalog_base_name)
      setDrawerWorkflow(null)
      setDrawerItem(null)
      loadData()
    } catch (e) { console.error(e) }
    setActionLoading(false)
  }

  const handleSaveNotes = async () => {
    if (!drawerItem) return
    try {
      const { workflow } = await api.updateRetirementNotes(drawerItem.catalog_base_name, notesText)
      setDrawerWorkflow(workflow)
    } catch (e) { console.error(e) }
  }

  const sortIndicator = (field: SortField) => {
    if (sortBy !== field) return null
    return <span className="sort-indicator">{sortDir === 'desc' ? ' ▼' : ' ▲'}</span>
  }

  const syncAge = syncedAt
    ? `${Math.round((Date.now() - new Date(syncedAt).getTime()) / 3600000)}h ago`
    : 'never'

  const totalCost = allItems.reduce((s, i) => s + i.total_cost, 0)
  const totalClosed = allItems.reduce((s, i) => s + i.closed_amount, 0)
  const totalTouched = allItems.reduce((s, i) => s + i.touched_amount, 0)
  const prodHigh = allItems.filter(i => i.retirement_score >= 55).length
  const prodReview = allItems.filter(i => i.retirement_score >= 35 && i.retirement_score < 55).length
  const prodKeepers = allItems.filter(i => i.retirement_score < 35).length

  const noProdOld = allItems.filter(i => {
    const d = ageDays(i.first_provision)
    return d !== null && d > 365
  }).length
  const noProdMed = allItems.filter(i => {
    const d = ageDays(i.first_provision)
    return d !== null && d > 180 && d <= 365
  }).length
  const noProdNew = allItems.length - noProdOld - noProdMed

  return (
    <div className="ca-page">
      <div className="ca-header">
        <h3>Retirement Analysis</h3>
        <span className="ca-subtitle" style={{ marginBottom: 0 }}>Last synced: {syncAge}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
        <p className="ca-subtitle" style={{ margin: 0 }}>Retirement scoring based on provisions, sales, cost, and catalog presence.</p>
        {tab === 'prod' && (
          <div className="ca-controls" style={{ margin: 0, padding: 0 }}>
            {([['1q', 'Last 3 Months'], ['2q', 'Last 6 Months'], ['3q', 'Last 9 Months'], ['1y', '1 Year']] as [TimeWindow, string][]).map(([w, label]) => (
              <button key={w} onClick={() => setWindow(w)}
                className={`ca-filter-btn${window === w ? ' active' : ''}`}
                style={{ fontSize: '11px', padding: '3px 8px' }}>
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ca-tab-bar" style={{ marginBottom: '12px' }}>
        <button className={`ca-tab-btn${tab === 'prod' ? ' active' : ''}`} onClick={() => setTab('prod')}>Prod Retirements</button>
        <button className={`ca-tab-btn${tab === 'no-prod' ? ' active' : ''}`} onClick={() => setTab('no-prod')}>Without Prod</button>
      </div>

      {tab === 'prod' ? (
        <>
          {allItems.length > 0 && (
            <div className="ca-stats-grid">
              <div className="ca-stat-card">
                <div className="ca-stat-label">Total Assets</div>
                <div className="ca-stat-value ca-color-blue">{allItems.length}</div>
              </div>
              <div className="ca-stat-card">
                <div className="ca-stat-label">High Retirement</div>
                <div className="ca-stat-value ca-color-red">{prodHigh}</div>
              </div>
              <div className="ca-stat-card">
                <div className="ca-stat-label">Review</div>
                <div className="ca-stat-value ca-color-orange">{prodReview}</div>
              </div>
              <div className="ca-stat-card">
                <div className="ca-stat-label">Keepers</div>
                <div className="ca-stat-value ca-color-green">{prodKeepers}</div>
              </div>
              <div className="ca-stat-card">
                <div className="ca-stat-label">Total Cost</div>
                <div className="ca-stat-value">{fmt(totalCost)}</div>
              </div>
              <div className="ca-stat-card">
                <div className="ca-stat-label">Total Closed</div>
                <div className="ca-stat-value ca-color-green">{fmt(totalClosed)}</div>
              </div>
              <div className="ca-stat-card">
                <div className="ca-stat-label">Total Touched</div>
                <div className="ca-stat-value">{fmt(totalTouched)}</div>
              </div>
            </div>
          )}

          <div className="ca-controls">
            {(['all', 'high', 'review', 'keepers'] as ScoreFilter[]).map(f => (
              <button key={f} onClick={() => setScoreFilter(f)}
                className={`ca-filter-btn${scoreFilter === f ? ' active' : ''}`}>
                {f === 'all' ? 'All' : f === 'high' ? 'High ≥55' : f === 'review' ? 'Review 35-54' : 'Keepers <35'}
              </button>
            ))}
            <input
              type="text" placeholder="Search by name..."
              value={search} onChange={e => setSearch(e.target.value)}
              className="ca-search"
            />
          </div>
          <div className="ca-controls" style={{ margin: 0, padding: 0 }}>
            {([['all', 'All'], ['none', 'No Action'], ['in_process', 'In Process'], ['started', 'Started'], ['retired', 'Retired']] as [WorkflowFilter, string][]).map(([f, label]) => (
              <button key={f} onClick={() => setWorkflowFilter(f)}
                className={`ca-filter-btn${workflowFilter === f ? ' active' : ''}`}
                style={{ fontSize: '11px', padding: '3px 8px' }}>
                {label}
              </button>
            ))}
          </div>

          {loading ? (
            <p className="ca-color-muted">Loading...</p>
          ) : (
            <>
              <div className="ca-row-count">{items.length} of {allItems.length} assets</div>
              <div className="ca-table-wrap">
                <table className="ca-table">
                  <thead>
                    <tr>
                      <th onClick={() => toggleSort('display_name')} style={{ width: '40%' }}>Name{sortIndicator('display_name')}</th>
                      <th className="num" onClick={() => toggleSort('retirement_score')} style={{ width: '7%' }}>Score{sortIndicator('retirement_score')}</th>
                      <th className="num" onClick={() => toggleSort('provisions')} style={{ width: '9%' }}>Provisions{sortIndicator('provisions')}</th>
                      <th className="num" onClick={() => toggleSort('touched_amount')} style={{ width: '9%' }}>Touched{sortIndicator('touched_amount')}</th>
                      <th className="num" style={{ width: '7%' }}>T-ROI</th>
                      <th className="num" onClick={() => toggleSort('closed_amount')} style={{ width: '9%' }}>Closed{sortIndicator('closed_amount')}</th>
                      <th className="num" style={{ width: '7%' }}>C-ROI</th>
                      <th className="num" onClick={() => toggleSort('total_cost')} style={{ width: '9%' }}>Cost{sortIndicator('total_cost')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map(item => {
                      const isExpanded = expanded.has(item.catalog_base_name)
                      return (
                        <Fragment key={item.catalog_base_name}>
                          <tr className="clickable" onClick={() => toggleExpand(item.catalog_base_name)}>
                            <td className="name" title={item.display_name}>
                              <span style={{ cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); openDrawer(item) }}>
                                {item.display_name}
                              </span>
                              {item.workflow_status && item.workflow_status !== 'retired' && (
                                <span style={{
                                  fontSize: '9px', padding: '1px 6px', marginLeft: '8px',
                                  background: 'var(--pf-t--global--color--status--info--default, #0066cc)',
                                  color: '#fff', borderRadius: '3px', whiteSpace: 'nowrap', verticalAlign: 'middle',
                                }}>Retirement In Process</span>
                              )}
                            </td>
                            <td className="num">
                              <span className="ca-score-badge" style={{ background: scoreBg(item.retirement_score), color: scoreColor(item.retirement_score) }}>
                                {item.retirement_score}
                              </span>
                            </td>
                            <td className="num">{item.provisions.toLocaleString()}</td>
                            <td className="num">{fmt(item.touched_amount)}</td>
                            <td className="num muted">{fmtRoi(item.touched_amount, item.total_cost)}</td>
                            <td className="num">{fmt(item.closed_amount)}</td>
                            <td className="num muted">{fmtRoi(item.closed_amount, item.total_cost)}</td>
                            <td className="num">{fmt(item.total_cost)}</td>
                          </tr>
                          {isExpanded && (
                            <tr className="ca-expanded-row">
                              <td colSpan={8}>
                                <div className="ca-detail">
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Environments</span>
                                    <span className="ca-detail-value">
                                      {item.stages.map(s => (
                                        <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(s.ci_name)}`} target="_blank" rel="noreferrer"
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
                                    <span className="ca-detail-label">Experiences</span>
                                    <span className="ca-detail-value">{item.experiences.toLocaleString()}</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Cost / Provision</span>
                                    <span className="ca-detail-value">${item.avg_cost_per_provision.toFixed(2)}</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Success</span>
                                    <span className="ca-detail-value">{(item.success_ratio * 100).toFixed(1)}%</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Failure</span>
                                    <span className="ca-detail-value">{(item.failure_ratio * 100).toFixed(1)}%</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">First Provision</span>
                                    <span className="ca-detail-value">{item.first_provision || 'N/A'}</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Last Provision</span>
                                    <span className="ca-detail-value">{item.last_provision || 'N/A'}</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Category</span>
                                    <span className="ca-detail-value">{item.category || '—'}</span>
                                  </div>
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
            </>
          )}
        </>
      ) : (
        <>
          <div className="ca-stats-grid">
            <div className="ca-stat-card">
              <div className="ca-stat-label">Without Prod</div>
              <div className="ca-stat-value ca-color-blue">{allItems.length}</div>
            </div>
            <div className="ca-stat-card">
              <div className="ca-stat-label">&gt; 1 Year</div>
              <div className="ca-stat-value ca-color-red">{noProdOld}</div>
            </div>
            <div className="ca-stat-card">
              <div className="ca-stat-label">6-12 Months</div>
              <div className="ca-stat-value ca-color-orange">{noProdMed}</div>
            </div>
            <div className="ca-stat-card">
              <div className="ca-stat-label">&lt; 6 Months</div>
              <div className="ca-stat-value ca-color-green">{noProdNew}</div>
            </div>
          </div>

          <div className="ca-controls">
            {([['all', 'All'], ['old', '> 1 Year'], ['med', '6-12 Mo'], ['new', '< 6 Mo']] as [AgeFilter, string][]).map(([f, label]) => (
              <button key={f} onClick={() => setAgeFilter(f)}
                className={`ca-filter-btn${ageFilter === f ? ' active' : ''}`}>
                {label}
              </button>
            ))}
            <input
              type="text" placeholder="Search by name..."
              value={search} onChange={e => setSearch(e.target.value)}
              className="ca-search"
            />
          </div>

          {loading ? (
            <p className="ca-color-muted">Loading...</p>
          ) : (() => {
            const filtered = ageFilter === 'all' ? items : items.filter(i => {
              const d = ageDays(i.first_provision)
              if (ageFilter === 'old') return d !== null && d > 365
              if (ageFilter === 'med') return d !== null && d > 180 && d <= 365
              return d === null || d <= 180
            })
            return (
            <>
              <div className="ca-row-count">{filtered.length} of {items.length} items without production deployment</div>
              <div className="ca-table-wrap">
                <table className="ca-table">
                  <thead>
                    <tr>
                      <th style={{ width: '40%' }}>Name</th>
                      <th style={{ width: '12%' }}>Stages</th>
                      <th style={{ width: '12%' }}>First Provision</th>
                      <th style={{ width: '12%' }}>Last Provision</th>
                      <th className="num" style={{ width: '10%' }}>Provisions</th>
                      <th className="num" style={{ width: '10%' }}>Age (days)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map(item => {
                      const age = ageDays(item.first_provision)
                      const isExpanded = expanded.has(item.catalog_base_name)
                      return (
                        <Fragment key={item.catalog_base_name}>
                          <tr className="clickable" onClick={() => toggleExpand(item.catalog_base_name)}>
                            <td className="name" title={item.display_name}>{item.display_name}</td>
                            <td>
                              {item.stages.map(s => (
                                <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(s.ci_name)}`} target="_blank" rel="noreferrer"
                                  className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                                  style={{ marginRight: 4 }} onClick={e => e.stopPropagation()}>
                                  {s.stage}
                                </a>
                              ))}
                              {item.stages.length === 0 && <span className="ca-color-muted">—</span>}
                            </td>
                            <td>{item.first_provision || '—'}</td>
                            <td>{item.last_provision || '—'}</td>
                            <td className="num">{item.provisions.toLocaleString()}</td>
                            <td className="num" style={{ color: ageColor(age), fontWeight: age && age > 365 ? 600 : 400 }}>
                              {age !== null ? age : '—'}
                            </td>
                          </tr>
                          {isExpanded && (
                            <tr className="ca-expanded-row">
                              <td colSpan={6}>
                                <div className="ca-detail">
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Environments</span>
                                    <span className="ca-detail-value">
                                      {item.stages.map(s => (
                                        <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(s.ci_name)}`} target="_blank" rel="noreferrer"
                                          className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                                          onClick={e => e.stopPropagation()}>
                                          {s.stage}
                                        </a>
                                      ))}
                                      {item.stages.length === 0 && <span className="ca-color-muted">none in RCARS</span>}
                                    </span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Catalog Name</span>
                                    <span className="ca-detail-value">{item.catalog_base_name}</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Unique Users</span>
                                    <span className="ca-detail-value">{item.unique_users.toLocaleString()}</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Experiences</span>
                                    <span className="ca-detail-value">{item.experiences.toLocaleString()}</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Total Cost</span>
                                    <span className="ca-detail-value">{fmt(item.total_cost)}</span>
                                  </div>
                                  <div className="ca-detail-item">
                                    <span className="ca-detail-label">Category</span>
                                    <span className="ca-detail-value">{item.category || '—'}</span>
                                  </div>
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
            </>
            )
          })()}
        </>
      )}

      {drawerItem && (
        <>
          <div className="browse-drawer-overlay" onClick={() => setDrawerItem(null)} />
          <div className="browse-drawer" style={{ width: '480px' }}>
            <div className="browse-drawer-header">
              <div className="browse-drawer-title">{drawerItem.display_name}</div>
              <button className="browse-drawer-close" onClick={() => setDrawerItem(null)} aria-label="Close drawer">&times;</button>
            </div>
            <div className="browse-drawer-body">
              {drawerLoading ? (
                <p className="ca-color-muted">Loading workflow...</p>
              ) : (
                <>
                  {/* Top: item info */}
                  <div className="browse-drawer-field">
                    <label className="browse-drawer-label">Base Name</label>
                    <div>{drawerItem.catalog_base_name}</div>
                  </div>
                  <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <label className="browse-drawer-label">Score</label>
                      <span className="ca-score-badge" style={{ background: scoreBg(drawerItem.retirement_score), color: scoreColor(drawerItem.retirement_score) }}>
                        {drawerItem.retirement_score}
                      </span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <label className="browse-drawer-label">Category</label>
                      <div>{drawerItem.category || '—'}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
                    <div style={{ flex: '1 1 45%' }}>
                      <label className="browse-drawer-label">Provisions</label>
                      <div>{drawerItem.provisions.toLocaleString()}</div>
                    </div>
                    <div style={{ flex: '1 1 45%' }}>
                      <label className="browse-drawer-label">Cost</label>
                      <div>{fmt(drawerItem.total_cost)}</div>
                    </div>
                    <div style={{ flex: '1 1 45%' }}>
                      <label className="browse-drawer-label">Touched</label>
                      <div>{fmt(drawerItem.touched_amount)}</div>
                    </div>
                    <div style={{ flex: '1 1 45%' }}>
                      <label className="browse-drawer-label">Closed</label>
                      <div>{fmt(drawerItem.closed_amount)}</div>
                    </div>
                  </div>
                  <div className="browse-drawer-field">
                    <label className="browse-drawer-label">Stages</label>
                    <div>
                      {drawerItem.stages.map(s => (
                        <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(s.ci_name)}`} target="_blank" rel="noreferrer"
                          className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                          style={{ marginRight: 4 }}>
                          {s.stage}
                        </a>
                      ))}
                      {drawerItem.stages.length === 0 && <span className="ca-color-muted">none</span>}
                    </div>
                  </div>

                  {/* Workflow checklist */}
                  <div style={{ borderTop: '1px solid var(--border-color, #333)', paddingTop: '12px', marginTop: '8px' }}>
                    <label className="browse-drawer-label" style={{ marginBottom: '8px', display: 'block' }}>Retirement Workflow</label>

                    {/* Step 1: Reviewed */}
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '10px' }}>
                      <input type="checkbox" checked={!!drawerWorkflow?.step_reviewed_at} readOnly style={{ marginTop: '3px' }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500 }}>Reviewed</div>
                        {drawerWorkflow?.step_reviewed_at ? (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {new Date(drawerWorkflow.step_reviewed_at).toLocaleDateString()} by {drawerWorkflow.step_reviewed_by || '—'}
                          </div>
                        ) : (
                          <button className="browse-btn-action" onClick={handleReview} disabled={actionLoading}
                            style={{ marginTop: '4px', fontSize: '11px', padding: '2px 8px' }}>
                            {actionLoading ? 'Working...' : 'Mark Reviewed'}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Step 2: Approved */}
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '10px' }}>
                      <input type="checkbox" checked={!!drawerWorkflow?.step_approved_at} readOnly style={{ marginTop: '3px' }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500 }}>Approved</div>
                        {drawerWorkflow?.step_approved_at ? (
                          <>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                              {new Date(drawerWorkflow.step_approved_at).toLocaleDateString()} by {drawerWorkflow.step_approved_by || '—'}
                            </div>
                            {drawerWorkflow.approval_reason && (
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                                Reason: {drawerWorkflow.approval_reason}
                              </div>
                            )}
                            {drawerWorkflow.replacement_ci && (
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                                Replacement: {drawerWorkflow.replacement_name || drawerWorkflow.replacement_ci}
                              </div>
                            )}
                          </>
                        ) : (
                          <div style={{ marginTop: '4px' }}>
                            <textarea
                              className="browse-drawer-textarea"
                              value={approvalReason}
                              onChange={e => setApprovalReason(e.target.value)}
                              placeholder="Reason for retirement (required)..."
                              rows={2}
                              style={{ fontSize: '11px', marginBottom: '4px' }}
                            />
                            <input
                              type="text"
                              className="browse-drawer-input"
                              value={replacementCi}
                              onChange={e => setReplacementCi(e.target.value)}
                              placeholder="Replacement CI (optional)"
                              style={{ fontSize: '11px', marginBottom: '4px' }}
                            />
                            <input
                              type="text"
                              className="browse-drawer-input"
                              value={replacementName}
                              onChange={e => setReplacementName(e.target.value)}
                              placeholder="Replacement display name (optional)"
                              style={{ fontSize: '11px', marginBottom: '4px' }}
                            />
                            <button className="browse-btn-action browse-btn-action--primary" onClick={handleApprove}
                              disabled={actionLoading || !approvalReason.trim()}
                              style={{ fontSize: '11px', padding: '2px 8px' }}>
                              {actionLoading ? 'Working...' : 'Approve Retirement'}
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Step 3: Owner Notified */}
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '10px' }}>
                      <input type="checkbox" checked={!!drawerWorkflow?.step_notified_at} readOnly style={{ marginTop: '3px' }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500 }}>Owner Notified</div>
                        {drawerWorkflow?.step_notified_at ? (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {new Date(drawerWorkflow.step_notified_at).toLocaleDateString()} by {drawerWorkflow.step_notified_by || '—'}
                          </div>
                        ) : (
                          <button className="browse-btn-action" onClick={handleNotify} disabled={actionLoading}
                            style={{ marginTop: '4px', fontSize: '11px', padding: '2px 8px' }}>
                            {actionLoading ? 'Working...' : 'Mark Notified'}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Step 4: Start Retirement */}
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '10px' }}>
                      <input type="checkbox" checked={!!drawerWorkflow?.step_started_at} readOnly style={{ marginTop: '3px' }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500 }}>Retirement Started</div>
                        {drawerWorkflow?.step_started_at ? (
                          <>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                              {new Date(drawerWorkflow.step_started_at).toLocaleDateString()} by {drawerWorkflow.step_started_by || '—'}
                            </div>
                            {drawerWorkflow.retirement_target_date && (
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                                Target: {new Date(drawerWorkflow.retirement_target_date).toLocaleDateString()}
                              </div>
                            )}
                            {drawerWorkflow.jira_key && (
                              <div style={{ fontSize: '11px' }}>
                                <a href={`https://redhat.atlassian.net/browse/${drawerWorkflow.jira_key}`} target="_blank" rel="noreferrer"
                                  style={{ color: 'var(--pf-t--global--color--status--info--default, #0066cc)' }}>
                                  {drawerWorkflow.jira_key}
                                </a>
                              </div>
                            )}
                          </>
                        ) : (
                          <div style={{ marginTop: '4px' }}>
                            {!drawerWorkflow?.step_approved_at && (
                              <div style={{ fontSize: '11px', color: 'var(--score-amber)', marginBottom: '4px' }}>
                                Approval required before starting retirement
                              </div>
                            )}
                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '4px' }}>
                              <label style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>Target days:</label>
                              <input type="number" className="browse-drawer-input"
                                value={targetDays} onChange={e => setTargetDays(Number(e.target.value) || 30)}
                                style={{ width: '60px', fontSize: '11px' }} />
                            </div>
                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '4px' }}>
                              <label style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>Jira project:</label>
                              <input type="text" className="browse-drawer-input"
                                value={jiraProject} onChange={e => setJiraProject(e.target.value)}
                                style={{ width: '80px', fontSize: '11px' }} />
                            </div>
                            <button className="browse-btn-action browse-btn-action--primary" onClick={handleStart}
                              disabled={actionLoading || !drawerWorkflow?.step_approved_at}
                              style={{ fontSize: '11px', padding: '2px 8px' }}>
                              {actionLoading ? 'Working...' : 'Start Retirement'}
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Step 5: Retired (auto-status) */}
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '10px' }}>
                      <input type="checkbox" checked={!!drawerWorkflow?.step_retired_at} readOnly style={{ marginTop: '3px' }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500 }}>Retired</div>
                        {drawerWorkflow?.step_retired_at ? (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {new Date(drawerWorkflow.step_retired_at).toLocaleDateString()}
                          </div>
                        ) : (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            Auto-completes when retirement is finalized
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Approval snapshot comparison */}
                  {drawerWorkflow?.approval_snapshot && (
                    <div style={{ borderTop: '1px solid var(--border-color, #333)', paddingTop: '12px', marginTop: '8px' }}>
                      <label className="browse-drawer-label" style={{ marginBottom: '6px', display: 'block' }}>Metrics: At Approval vs Current</label>
                      <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: 'left', padding: '2px 4px', borderBottom: '1px solid var(--border-color, #333)' }}>Metric</th>
                            <th style={{ textAlign: 'right', padding: '2px 4px', borderBottom: '1px solid var(--border-color, #333)' }}>At Approval</th>
                            <th style={{ textAlign: 'right', padding: '2px 4px', borderBottom: '1px solid var(--border-color, #333)' }}>Current</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(drawerWorkflow.approval_snapshot).map(([key, val]) => {
                            const currentMap: Record<string, number | string> = {
                              provisions: drawerItem.provisions,
                              total_cost: drawerItem.total_cost,
                              touched_amount: drawerItem.touched_amount,
                              closed_amount: drawerItem.closed_amount,
                              retirement_score: drawerItem.retirement_score,
                            }
                            const current = currentMap[key]
                            return (
                              <tr key={key}>
                                <td style={{ padding: '2px 4px' }}>{key.replace(/_/g, ' ')}</td>
                                <td style={{ textAlign: 'right', padding: '2px 4px' }}>{typeof val === 'number' ? val.toLocaleString() : val}</td>
                                <td style={{ textAlign: 'right', padding: '2px 4px' }}>{current !== undefined ? (typeof current === 'number' ? current.toLocaleString() : current) : '—'}</td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Curator notes */}
                  <div style={{ borderTop: '1px solid var(--border-color, #333)', paddingTop: '12px', marginTop: '8px' }}>
                    <div className="browse-drawer-field">
                      <label className="browse-drawer-label">Curator Notes</label>
                      <textarea
                        className="browse-drawer-textarea"
                        value={notesText}
                        onChange={e => setNotesText(e.target.value)}
                        onBlur={handleSaveNotes}
                        placeholder="Add notes about this retirement..."
                        rows={3}
                      />
                    </div>
                  </div>

                  {/* Jira link */}
                  {drawerWorkflow?.jira_key && (
                    <div className="browse-drawer-field">
                      <label className="browse-drawer-label">Jira Ticket</label>
                      <a href={`https://redhat.atlassian.net/browse/${drawerWorkflow.jira_key}`} target="_blank" rel="noreferrer"
                        style={{ color: 'var(--pf-t--global--color--status--info--default, #0066cc)' }}>
                        {drawerWorkflow.jira_key}
                      </a>
                    </div>
                  )}

                  {/* Cancel workflow */}
                  <div style={{ borderTop: '1px solid var(--border-color, #333)', paddingTop: '12px', marginTop: '12px' }}>
                    <button className="browse-btn-action browse-btn-action--danger" onClick={handleCancel}
                      disabled={actionLoading}
                      style={{ fontSize: '11px', padding: '3px 10px' }}>
                      {actionLoading ? 'Canceling...' : 'Cancel Workflow'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
