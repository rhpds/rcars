import { useState, useEffect, useCallback, useRef, Fragment } from 'react'
import { api, ReportingMetricsItem } from '../services/api'
import type { RetirementWorkflow } from '../services/api'
import { useAuth } from '../hooks/useAuth'

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
type WorkflowFilter = 'all' | 'none' | 'in_process' | 'started'

const fmt = (v: number | string) => {
  const n = typeof v === 'string' ? parseFloat(v) || 0 : v
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toFixed(0)}`
}

const num = (v: unknown): number => typeof v === 'number' ? v : parseFloat(String(v)) || 0

const fmtRoi = (amount: number | string, cost: number | string) => {
  const a = num(amount), c = num(cost)
  if (c <= 0 || a <= 0) return '—'
  return `${(a / c).toFixed(1)}x`
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

function WorkflowInlineBadge({ status }: { status: string }) {
  if (status === 'retired') {
    return (
      <span className="ret-inline-badge ret-inline-badge--retired">
        <span className="ret-inline-badge__dot" />
        Retired
      </span>
    )
  }
  if (status === 'started') {
    return (
      <span className="ret-inline-badge ret-inline-badge--started">
        <span className="ret-inline-badge__dot" />
        Retirement Started
      </span>
    )
  }
  return (
    <span className="ret-inline-badge">
      <span className="ret-inline-badge__dot" />
      In Process
    </span>
  )
}

function ReplacementPicker({
  value,
  displayName,
  excludeBaseName,
  onSelect,
}: {
  value: string
  displayName: string
  excludeBaseName: string
  onSelect: (ci: string, name: string) => void
}) {
  const [query, setQuery] = useState(displayName || value)
  const [results, setResults] = useState<Array<{ ci_name: string; display_name: string }>>([])
  const [open, setOpen] = useState(false)
  const [manualMode, setManualMode] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const doSearch = (q: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      if (q.length < 2) { setResults([]); return }
      try {
        const data = await api.listCatalog({ search: q, limit: 10 }) as { items: Array<{ ci_name: string; display_name: string; base_ci_name?: string; is_published?: boolean }> }
        const stripStage = (name: string) => name.replace(/\.(prod|dev|event|test)$/, '')
        const byKey = new Map<string, { ci_name: string; display_name: string; isPublished: boolean }>()
        for (const i of data.items) {
          const key = stripStage(i.base_ci_name || i.ci_name)
          if (key === excludeBaseName) continue
          const existing = byKey.get(key)
          if (!existing || (i.is_published && !existing.isPublished)) {
            byKey.set(key, { ci_name: i.is_published ? stripStage(i.ci_name) : key, display_name: i.display_name, isPublished: !!i.is_published })
          }
        }
        setResults(Array.from(byKey.values()).map(v => ({ ci_name: v.ci_name, display_name: v.display_name })))
        setOpen(true)
      } catch { setResults([]) }
    }, 250)
  }

  if (manualMode) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <input type="text" className="browse-drawer-input" value={value}
            onChange={e => onSelect(e.target.value, displayName)}
            placeholder="CI base name" style={{ fontSize: '12px', flex: 1 }} />
          <input type="text" className="browse-drawer-input" value={displayName}
            onChange={e => onSelect(value, e.target.value)}
            placeholder="Display name" style={{ fontSize: '12px', flex: 1 }} />
        </div>
        <button onClick={() => setManualMode(false)}
          style={{ background: 'none', border: 'none', color: 'var(--text-link)', fontSize: '11px', cursor: 'pointer', padding: 0, textAlign: 'left' }}>
          Search RCARS catalog instead
        </button>
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <input
        type="text"
        className="browse-drawer-input"
        value={query}
        onChange={e => { setQuery(e.target.value); doSearch(e.target.value) }}
        onFocus={() => { if (results.length > 0) setOpen(true) }}
        placeholder="Search for replacement CI..."
        style={{ fontSize: '12px' }}
      />
      {open && results.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 20, marginTop: '2px',
          background: 'var(--bg-card)', border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-sm)', boxShadow: 'var(--shadow-elevated)',
          maxHeight: '180px', overflowY: 'auto',
        }}>
          {results.map(r => (
            <div key={r.ci_name}
              onClick={() => { onSelect(r.ci_name, r.display_name); setQuery(r.display_name); setOpen(false) }}
              style={{
                padding: '6px 10px', cursor: 'pointer', fontSize: '12px',
                borderBottom: '1px solid var(--border-subtle)',
                transition: 'background 150ms',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--nav-hover-bg)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
              <div style={{ color: 'var(--text-primary)' }}>{r.display_name}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '10px', fontFamily: 'var(--ff-mono)' }}>{r.ci_name}</div>
            </div>
          ))}
        </div>
      )}
      <button onClick={() => setManualMode(true)}
        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '11px', cursor: 'pointer', padding: '2px 0 0', textAlign: 'left' }}>
        Not in RCARS? Enter manually
      </button>
    </div>
  )
}

function StepperStep({
  title,
  complete,
  active,
  pending: _pending,
  auto,
  optional,
  completedAt,
  completedBy,
  children,
}: {
  title: string
  complete: boolean
  active: boolean
  pending: boolean
  auto?: boolean
  optional?: boolean
  completedAt?: string | null
  completedBy?: string | null
  children?: React.ReactNode
}) {
  const cls = complete ? 'ret-step--complete' : active ? 'ret-step--active' : auto ? 'ret-step--auto' : 'ret-step--pending'
  return (
    <div className={`ret-step ${cls}`}>
      <div className="ret-step__dot" />
      <div className="ret-step__title">
        {title}
        {optional && <span className="ret-step__badge ret-step__badge--optional">optional</span>}
        {auto && <span className="ret-step__badge ret-step__badge--auto">auto</span>}
      </div>
      {complete && completedAt && (
        <div className="ret-step__meta">
          {new Date(completedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
          {completedBy ? ` · ${completedBy}` : ''}
        </div>
      )}
      {children && <div className="ret-step__content">{children}</div>}
    </div>
  )
}

export function RetirementPage() {
  const { isAdmin } = useAuth()
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
  const [actionError, setActionError] = useState<string | null>(null)
  const [emailTemplate, setEmailTemplate] = useState<string | null>(null)

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
    setWorkflowFilter('all')
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
    setEmailTemplate(null)
    setActionError(null)
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

  const handleApprove = async () => {
    if (!drawerItem || !approvalReason.trim()) return
    setActionLoading(true)
    setActionError(null)
    try {
      const { workflow } = await api.approveRetirementItem(
        drawerItem.catalog_base_name, approvalReason,
        replacementCi || undefined, replacementName || undefined
      )
      setDrawerWorkflow(workflow)
      loadData()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Approval failed')
    }
    setActionLoading(false)
  }

  const handleNotify = async () => {
    if (!drawerItem) return
    setActionLoading(true)
    setActionError(null)
    try {
      const { workflow } = await api.notifyRetirementOwner(drawerItem.catalog_base_name)
      setDrawerWorkflow(workflow)
      loadData()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Notification failed')
    }
    setActionLoading(false)
  }

  const handleStart = async () => {
    if (!drawerItem) return
    setActionLoading(true)
    setActionError(null)
    try {
      const { workflow } = await api.startRetirement(drawerItem.catalog_base_name, targetDays, jiraProject)
      setDrawerWorkflow(workflow)
      loadData()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to start retirement')
    }
    setActionLoading(false)
  }

  const handleCancel = async () => {
    if (!drawerItem) return
    const hasJira = drawerWorkflow?.jira_key
    const msg = hasJira
      ? `This will cancel the retirement workflow and unlink ${drawerWorkflow.jira_key}. The Jira ticket will remain open. Continue?`
      : 'This will cancel the retirement workflow and remove all progress. Continue?'
    if (!confirm(msg)) return
    setActionLoading(true)
    setActionError(null)
    try {
      await api.cancelRetirementWorkflow(drawerItem.catalog_base_name)
      setDrawerWorkflow(null)
      setDrawerItem(null)
      loadData()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Cancel failed')
    }
    setActionLoading(false)
  }

  const handleSaveNotes = async () => {
    if (!drawerItem) return
    try {
      const { workflow } = await api.updateRetirementNotes(drawerItem.catalog_base_name, notesText)
      setDrawerWorkflow(workflow)
    } catch (e) { console.error(e) }
  }

  const generateEmailTemplate = () => {
    if (!drawerItem) return
    const owners = drawerItem.owners || []
    const ownerNames = owners.map(o => o.name || o.email).join(', ') || 'Content Owner'
    const reason = drawerWorkflow?.approval_reason || approvalReason || 'See RCARS retirement analysis'
    const replacement = drawerWorkflow?.replacement_name || replacementName
    const score = drawerItem.retirement_score
    const provs = num(drawerItem.provisions).toLocaleString()
    const cost = fmt(drawerItem.total_cost)
    const touched = fmt(drawerItem.touched_amount)

    const template = `Hi ${ownerNames},

This is a notification that "${drawerItem.display_name}" has been flagged for retirement from the Red Hat Demo Platform.

Reason:
${reason.split('\n').filter(l => l.trim()).map(l => `- ${l.trim()}`).join('\n')}

Key metrics (last 12 months):
- Retirement Score: ${score}
- Provisions: ${provs}
- Total Cost: ${cost}
- Pipeline Touched: ${touched}
${replacement ? `\nReplacement: ${replacement}` : ''}
${drawerWorkflow?.jira_key ? `\nJira: https://redhat.atlassian.net/browse/${drawerWorkflow.jira_key}` : ''}
If you have questions or concerns about this retirement, please reach out to Nate Stephany (nstephan@redhat.com).

Thank you,
RHDP Content Team`

    setEmailTemplate(template)
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

  const wf = drawerWorkflow
  const isApproved = !!wf?.step_approved_at
  const isNotified = !!wf?.step_notified_at
  const isStarted = !!wf?.step_started_at
  const isRetired = !!wf?.step_retired_at

  const approveIsNext = !isApproved
  const notifyIsNext = isApproved && !isNotified && !isStarted
  const startIsNext = isApproved && !isStarted

  return (
    <div className="ca-page">
      <div className="ca-header">
        <h3>Retirement Analysis</h3>
        <span className="ca-subtitle" style={{ marginBottom: 0 }}>Synced {syncAge}</span>
      </div>

      {/* Tab bar + time window */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '12px' }}>
        <div className="ca-tab-bar" style={{ marginBottom: 0, flex: 'none' }}>
          <button className={`ca-tab-btn${tab === 'prod' ? ' active' : ''}`} onClick={() => setTab('prod')}>Prod Retirements</button>
          <button className={`ca-tab-btn${tab === 'no-prod' ? ' active' : ''}`} onClick={() => setTab('no-prod')}>Without Prod</button>
        </div>
        {tab === 'prod' && (
          <div className="ret-filter-group">
            {([['1q', '3 Mo'], ['2q', '6 Mo'], ['3q', '9 Mo'], ['1y', '1 Yr']] as [TimeWindow, string][]).map(([w, label]) => (
              <button key={w} onClick={() => setWindow(w)}
                className={`ret-filter-group__btn${window === w ? ' active' : ''}`}>
                {label}
              </button>
            ))}
          </div>
        )}
        <span className="ca-subtitle" style={{ margin: 0, marginLeft: 'auto' }}>
          Scoring based on provisions, sales, cost, and catalog presence
        </span>
      </div>

      {tab === 'prod' ? (
        <>
          {/* Stats grid */}
          {allItems.length > 0 && (
            <div className="ca-stats-grid">
              <div className="ret-stat-card ret-stat-card--blue">
                <div className="ret-stat-label">Total Assets</div>
                <div className="ret-stat-value ca-color-blue">{allItems.length}</div>
              </div>
              <div className="ret-stat-card ret-stat-card--red">
                <div className="ret-stat-label">High Retirement</div>
                <div className="ret-stat-value ca-color-red">{prodHigh}</div>
                <div className="ret-stat-sub">score ≥ 55</div>
              </div>
              <div className="ret-stat-card ret-stat-card--amber">
                <div className="ret-stat-label">Review</div>
                <div className="ret-stat-value ca-color-orange">{prodReview}</div>
                <div className="ret-stat-sub">score 35–54</div>
              </div>
              <div className="ret-stat-card ret-stat-card--green">
                <div className="ret-stat-label">Keepers</div>
                <div className="ret-stat-value ca-color-green">{prodKeepers}</div>
                <div className="ret-stat-sub">score &lt; 35</div>
              </div>
              <div className="ret-stat-card ret-stat-card--neutral">
                <div className="ret-stat-label">Total Cost</div>
                <div className="ret-stat-value">{fmt(totalCost)}</div>
              </div>
              <div className="ret-stat-card ret-stat-card--green">
                <div className="ret-stat-label">Total Closed</div>
                <div className="ret-stat-value ca-color-green">{fmt(totalClosed)}</div>
              </div>
              <div className="ret-stat-card ret-stat-card--neutral">
                <div className="ret-stat-label">Total Touched</div>
                <div className="ret-stat-value">{fmt(totalTouched)}</div>
              </div>
            </div>
          )}

          {/* Controls row: score filter + workflow filter + search */}
          <div className="ret-controls-row">
            <span className="ret-filter-label">Score</span>
            <div className="ret-filter-group">
              <button onClick={() => setScoreFilter('all')}
                className={`ret-filter-group__btn${scoreFilter === 'all' ? ' active' : ''}`}>All</button>
              <button onClick={() => setScoreFilter('high')}
                className={`ret-filter-group__btn${scoreFilter === 'high' ? ' active' : ''}`}>
                <span className="ret-filter-group__dot ret-filter-group__dot--red" />High ≥55
              </button>
              <button onClick={() => setScoreFilter('review')}
                className={`ret-filter-group__btn${scoreFilter === 'review' ? ' active' : ''}`}>
                <span className="ret-filter-group__dot ret-filter-group__dot--amber" />Review
              </button>
              <button onClick={() => setScoreFilter('keepers')}
                className={`ret-filter-group__btn${scoreFilter === 'keepers' ? ' active' : ''}`}>
                <span className="ret-filter-group__dot ret-filter-group__dot--green" />Keepers
              </button>
            </div>

            <div className="ret-controls-row__divider" />

            <span className="ret-filter-label">Status</span>
            <div className="ret-filter-group">
              {([['all', 'All'], ['none', 'No Action'], ['in_process', 'In Process'], ['started', 'Started']] as [WorkflowFilter, string][]).map(([f, label]) => (
                <button key={f} onClick={() => setWorkflowFilter(f)}
                  className={`ret-filter-group__btn${workflowFilter === f ? ' active' : ''}`}>
                  {label}
                </button>
              ))}
            </div>

            <input
              type="text" placeholder="Search by name..."
              value={search} onChange={e => setSearch(e.target.value)}
              className="ca-search"
            />
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
                              <div>{item.display_name}{item.workflow_status && <WorkflowInlineBadge status={item.workflow_status} />}</div>
                              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--ff-mono)', marginTop: '1px' }}>{item.catalog_base_name}</div>
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
                                    <span className="ca-detail-label">Experiences</span>
                                    <span className="ca-detail-value">{item.experiences.toLocaleString()}</span>
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
                                  <div className="ca-detail-item" style={{ marginLeft: 'auto' }}>
                                    <button className="ret-action-btn ret-action-btn--primary" onClick={(e) => { e.stopPropagation(); openDrawer(item) }}>
                                      Retirement Workflow
                                    </button>
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
            <div className="ret-stat-card ret-stat-card--blue">
              <div className="ret-stat-label">Without Prod</div>
              <div className="ret-stat-value ca-color-blue">{allItems.length}</div>
            </div>
            <div className="ret-stat-card ret-stat-card--red">
              <div className="ret-stat-label">&gt; 1 Year</div>
              <div className="ret-stat-value ca-color-red">{noProdOld}</div>
            </div>
            <div className="ret-stat-card ret-stat-card--amber">
              <div className="ret-stat-label">6–12 Months</div>
              <div className="ret-stat-value ca-color-orange">{noProdMed}</div>
            </div>
            <div className="ret-stat-card ret-stat-card--green">
              <div className="ret-stat-label">&lt; 6 Months</div>
              <div className="ret-stat-value ca-color-green">{noProdNew}</div>
            </div>
          </div>

          <div className="ret-controls-row">
            <div className="ret-filter-group">
              {([['all', 'All'], ['old', '> 1 Year'], ['med', '6–12 Mo'], ['new', '< 6 Mo']] as [AgeFilter, string][]).map(([f, label]) => (
                <button key={f} onClick={() => setAgeFilter(f)}
                  className={`ret-filter-group__btn${ageFilter === f ? ' active' : ''}`}>
                  {label}
                </button>
              ))}
            </div>
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
                            <td className="name" title={item.display_name}>
                              <div>{item.display_name}</div>
                              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--ff-mono)', marginTop: '1px' }}>{item.catalog_base_name}</div>
                            </td>
                            <td>
                              {item.stages.map(s => (
                                <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(item.display_name)}`} target="_blank" rel="noreferrer"
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
                                        <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(item.display_name)}`} target="_blank" rel="noreferrer"
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
                                  <div className="ca-detail-item" style={{ marginLeft: 'auto' }}>
                                    <button className="ret-action-btn ret-action-btn--primary" onClick={(e) => { e.stopPropagation(); openDrawer(item) }}>
                                      Retirement Workflow
                                    </button>
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

      {/* ══════════════ Retirement Workflow Drawer ══════════════ */}
      {drawerItem && (
        <>
          <div className="browse-drawer-overlay" onClick={() => setDrawerItem(null)} />
          <div className="browse-drawer ret-drawer">
            <div className="browse-drawer-header">
              <div className="browse-drawer-title">{drawerItem.display_name}</div>
              <button className="browse-drawer-close" onClick={() => setDrawerItem(null)} aria-label="Close drawer">&times;</button>
            </div>
            <div className="browse-drawer-body" style={{ padding: 0, gap: 0 }}>
              {drawerLoading ? (
                <p className="ca-color-muted" style={{ padding: 'var(--sp-md)' }}>Loading workflow...</p>
              ) : (
                <>
                  {/* ── Usage Data Grid (fixed top, not scrollable) ── */}
                  <div style={{ flexShrink: 0, padding: 'var(--sp-md)', paddingBottom: 0 }}>
                  <div className="ret-data-grid">
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Score</div>
                      <div className="ret-data-value" style={{ color: scoreColor(drawerItem.retirement_score) }}>
                        {drawerItem.retirement_score}
                      </div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Provisions</div>
                      <div className="ret-data-value">{drawerItem.provisions.toLocaleString()}</div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Unique Users</div>
                      <div className="ret-data-value">{drawerItem.unique_users.toLocaleString()}</div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Experiences</div>
                      <div className="ret-data-value">{drawerItem.experiences.toLocaleString()}</div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Touched</div>
                      <div className="ret-data-value">{fmt(drawerItem.touched_amount)}</div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Closed</div>
                      <div className="ret-data-value ret-data-value--green">{fmt(drawerItem.closed_amount)}</div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Total Cost</div>
                      <div className="ret-data-value">{fmt(drawerItem.total_cost)}</div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Cost / Provision</div>
                      <div className="ret-data-value ret-data-value--small">${num(drawerItem.avg_cost_per_provision).toFixed(2)}</div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Success Rate</div>
                      <div className="ret-data-value ret-data-value--green ret-data-value--small">{(num(drawerItem.success_ratio) * 100).toFixed(1)}%</div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Failure Rate</div>
                      <div className="ret-data-value ret-data-value--small" style={{ color: num(drawerItem.failure_ratio) > 0.1 ? 'var(--score-red)' : 'var(--text-primary)' }}>
                        {(num(drawerItem.failure_ratio) * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">First Provision</div>
                      <div className="ret-data-value ret-data-value--small">{drawerItem.first_provision || 'N/A'}</div>
                    </div>
                    <div className="ret-data-cell">
                      <div className="ret-data-label">Last Provision</div>
                      <div className="ret-data-value ret-data-value--small">{drawerItem.last_provision || 'N/A'}</div>
                    </div>
                    <div className="ret-data-cell ret-data-cell--wide">
                      <div className="ret-data-label">Environments</div>
                      <div style={{ marginTop: '4px' }}>
                        {drawerItem.stages.map(s => (
                          <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(drawerItem.display_name)}`} target="_blank" rel="noreferrer"
                            className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                            style={{ marginRight: 4 }}>
                            {s.stage}
                          </a>
                        ))}
                        {drawerItem.stages.length === 0 && <span className="ca-color-muted">none</span>}
                      </div>
                    </div>
                  </div>
                  </div>

                  {/* ── Scrollable workflow section ── */}
                  <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--sp-md)', paddingTop: 0 }}>

                  {/* ── Workflow Stepper ── */}
                  <div className="ret-drawer-section">
                    <div className="ret-drawer-section__title">Retirement Workflow</div>

                    <div className="ret-stepper">
                      {/* Step 1: Recommend for Retirement */}
                      <StepperStep
                        title="Recommend for Retirement"
                        complete={isApproved}
                        active={approveIsNext}
                        pending={false}
                        completedAt={wf?.step_approved_at}
                        completedBy={wf?.step_approved_by}
                      >
                        {isApproved ? (
                          <div style={{ fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {wf?.approval_reason && (
                              <div>
                                <span style={{ color: 'var(--text-muted)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Reason: </span>
                                <span style={{ color: 'var(--text-secondary)' }}>{wf.approval_reason}</span>
                              </div>
                            )}
                            {wf?.replacement_ci && (
                              <div>
                                <span style={{ color: 'var(--text-muted)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Replacement: </span>
                                <a href={`/browse?search=${encodeURIComponent(wf.replacement_ci)}`} target="_blank" rel="noreferrer"
                                  style={{ color: 'var(--text-link)', fontSize: '12px' }}>
                                  {wf.replacement_name || wf.replacement_ci}
                                </a>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <textarea
                              className="browse-drawer-textarea"
                              value={approvalReason}
                              onChange={e => setApprovalReason(e.target.value)}
                              placeholder="Reason for retirement (required)..."
                              rows={2}
                              style={{ fontSize: '12px' }}
                            />
                            <div>
                              <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Replacement CI (optional)</label>
                              <ReplacementPicker
                                value={replacementCi}
                                displayName={replacementName}
                                excludeBaseName={drawerItem.catalog_base_name}
                                onSelect={(ci, name) => { setReplacementCi(ci); setReplacementName(name) }}
                              />
                            </div>
                            <button className="ret-action-btn ret-action-btn--primary" onClick={handleApprove}
                              disabled={actionLoading || !approvalReason.trim()}>
                              {actionLoading ? 'Submitting...' : 'Recommend Retirement'}
                            </button>
                          </div>
                        )}
                      </StepperStep>

                      {/* Step 2: Owner Notified (optional) */}
                      <StepperStep
                        title="Owner Notified"
                        complete={isNotified}
                        active={notifyIsNext}
                        pending={!isApproved}
                        optional
                        completedAt={wf?.step_notified_at}
                        completedBy={wf?.step_notified_by}
                      >
                        {isApproved && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {/* Show detected owners */}
                            {drawerItem.owners && drawerItem.owners.length > 0 && (
                              <div style={{ fontSize: '12px' }}>
                                <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>Detected owners:</div>
                                {drawerItem.owners.map((o, i) => (
                                  <div key={i} style={{ color: 'var(--text-secondary)', marginBottom: '2px' }}>
                                    {o.name || o.email}
                                    {o.name && o.email && <span style={{ color: 'var(--text-muted)' }}> ({o.email})</span>}
                                  </div>
                                ))}
                              </div>
                            )}
                            {drawerItem.owners && drawerItem.owners.length === 0 && (
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                No owner info in AgnosticV metadata
                              </div>
                            )}

                            {/* Email template generator + notify (admin only) */}
                            {!isNotified && !isStarted && (
                              isAdmin ? (
                                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                  <button className="ret-action-btn ret-action-btn--primary" onClick={generateEmailTemplate}
                                    style={{ fontSize: '11px' }}>
                                    Generate Email Template
                                  </button>
                                  <button className="ret-action-btn ret-action-btn--primary" onClick={handleNotify}
                                    disabled={actionLoading} style={{ fontSize: '11px' }}>
                                    {actionLoading ? 'Saving...' : 'Mark as Notified'}
                                  </button>
                                </div>
                              ) : (
                                <div style={{ fontSize: '11px', color: 'var(--score-amber)' }}>
                                  Admin access required to notify owner
                                </div>
                              )
                            )}

                            {/* Show generated email template */}
                            {emailTemplate && (
                              <div style={{ position: 'relative', background: 'var(--bg-section)', border: '1px solid var(--border-section)', borderRadius: 'var(--radius-sm)', padding: '6px' }}>
                                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '4px', marginBottom: '4px' }}>
                                  <button
                                    className="ret-action-btn ret-action-btn--start"
                                    onClick={() => { navigator.clipboard.writeText(emailTemplate); }}
                                    style={{ padding: '3px 8px', fontSize: '11px', lineHeight: 1 }}
                                    title="Copy to clipboard">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ verticalAlign: 'middle' }}>
                                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                    </svg>
                                  </button>
                                  <button
                                    className="ret-action-btn ret-action-btn--danger"
                                    onClick={() => setEmailTemplate(null)}
                                    style={{ padding: '3px 8px', fontSize: '11px', lineHeight: 1 }}
                                    title="Dismiss">
                                    &times;
                                  </button>
                                </div>
                                <textarea
                                  className="browse-drawer-textarea"
                                  value={emailTemplate}
                                  readOnly
                                  rows={6}
                                  style={{ fontSize: '11px', fontFamily: 'var(--ff-mono)', lineHeight: '1.5', maxHeight: '150px', resize: 'vertical' }}
                                />
                              </div>
                            )}
                          </div>
                        )}
                      </StepperStep>

                      {/* Step 3: Start Retirement */}
                      <StepperStep
                        title="Start Retirement"
                        complete={isStarted}
                        active={startIsNext}
                        pending={!isApproved}
                        completedAt={wf?.step_started_at}
                        completedBy={wf?.step_started_by}
                      >
                        {isStarted ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {wf?.jira_key && (
                              <a href={`https://redhat.atlassian.net/browse/${wf.jira_key}`}
                                target="_blank" rel="noreferrer" className="ret-jira-link">
                                {wf.jira_key}
                              </a>
                            )}
                            <button className="ret-action-btn ret-action-btn--danger" onClick={handleCancel}
                              disabled={actionLoading}
                              style={{ fontSize: '11px', marginTop: '4px' }}>
                              {actionLoading ? 'Stopping...' : 'Stop Retirement'}
                            </button>
                          </div>
                        ) : isApproved ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                              Creates a Jira ticket in the selected project with retirement details, metrics snapshot, and adoc template. The retirement clock starts from this point.
                            </div>
                            {isAdmin ? (
                              <>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Target days:</label>
                                  <input type="number" className="browse-drawer-input"
                                    value={targetDays} onChange={e => setTargetDays(Number(e.target.value) || 30)}
                                    style={{ width: '60px', fontSize: '12px' }} />
                                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Jira:</label>
                                  <input type="text" className="browse-drawer-input"
                                    value={jiraProject} onChange={e => setJiraProject(e.target.value)}
                                    style={{ width: '80px', fontSize: '12px' }} />
                                </div>
                                <button className="ret-action-btn ret-action-btn--start" onClick={handleStart}
                                  disabled={actionLoading}>
                                  {actionLoading ? 'Creating Jira...' : 'Start Retirement'}
                                </button>
                              </>
                            ) : (
                              <div style={{ fontSize: '11px', color: 'var(--score-amber)' }}>
                                Admin access required to start retirement
                              </div>
                            )}
                          </div>
                        ) : (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            Requires recommendation first
                          </div>
                        )}
                      </StepperStep>

                      {/* Step 4: Retired (auto) */}
                      <StepperStep
                        title="Retired"
                        complete={isRetired}
                        active={false}
                        pending={!isStarted}
                        auto
                        completedAt={wf?.step_retired_at}
                      >
                        {!isRetired && (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            Auto-completes when item disappears from Babylon
                          </div>
                        )}
                      </StepperStep>
                    </div>
                  </div>

                  {/* ── Action Error ── */}
                  {actionError && (
                    <div style={{
                      background: 'var(--error-bg)', border: '1px solid var(--error-border)',
                      borderRadius: 'var(--radius-sm)', padding: '8px 12px', fontSize: '12px',
                      color: 'var(--error-title)', marginTop: '8px',
                    }}>
                      {actionError}
                    </div>
                  )}

                  {/* ── Approval Snapshot Comparison ── */}
                  {wf?.approval_snapshot && (
                    <div className="ret-drawer-section">
                      <div className="ret-drawer-section__title">Metrics at Approval vs Current</div>
                      <table className="ret-snapshot-table">
                        <thead>
                          <tr>
                            <th>Metric</th>
                            <th>At Approval</th>
                            <th>Current</th>
                            <th>Δ</th>
                          </tr>
                        </thead>
                        <tbody>
                          {([
                            ['retirement_score', 'Score', drawerItem.retirement_score],
                            ['provisions', 'Provisions', drawerItem.provisions],
                            ['unique_users', 'Users', drawerItem.unique_users],
                            ['experiences', 'Experiences', drawerItem.experiences],
                            ['total_cost', 'Cost', drawerItem.total_cost],
                            ['touched_amount', 'Touched', drawerItem.touched_amount],
                            ['closed_amount', 'Closed', drawerItem.closed_amount],
                          ] as [string, string, number][]).map(([key, label, current]) => {
                            const snapped = wf.approval_snapshot![key]
                            if (snapped === undefined) return null
                            const snapVal = num(snapped)
                            const delta = current - snapVal
                            const isMoney = ['total_cost', 'touched_amount', 'closed_amount'].includes(key)
                            const fmtVal = (v: number) => isMoney ? fmt(v) : v.toLocaleString()
                            return (
                              <tr key={key}>
                                <td>{label}</td>
                                <td>{fmtVal(snapVal)}</td>
                                <td>{fmtVal(current)}</td>
                                <td>
                                  {delta !== 0 && (
                                    <span className={`ret-snapshot-delta ${
                                      key === 'retirement_score'
                                        ? (delta > 0 ? 'ret-snapshot-delta--up' : 'ret-snapshot-delta--down')
                                        : (delta > 0 ? 'ret-snapshot-delta--down' : 'ret-snapshot-delta--up')
                                    }`}>
                                      {delta > 0 ? '+' : ''}{isMoney ? fmt(delta) : delta.toLocaleString()}
                                    </span>
                                  )}
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* ── Curator Notes ── */}
                  <div className="ret-drawer-section">
                    <div className="ret-drawer-section__title">Curator Notes</div>
                    <textarea
                      className="browse-drawer-textarea"
                      value={notesText}
                      onChange={e => setNotesText(e.target.value)}
                      onBlur={handleSaveNotes}
                      placeholder="Add notes about this retirement..."
                      rows={3}
                      style={{ fontSize: '12px' }}
                    />
                  </div>

                  {/* ── Cancel Workflow (before start only — after start, use Stop in the step) ── */}
                  {wf && !isStarted && (
                    <div style={{ paddingTop: '8px' }}>
                      <button className="ret-action-btn ret-action-btn--danger" onClick={handleCancel}
                        disabled={actionLoading}>
                        {actionLoading ? 'Canceling...' : 'Cancel Workflow'}
                      </button>
                    </div>
                  )}
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
