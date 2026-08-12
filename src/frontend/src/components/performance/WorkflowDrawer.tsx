import { useState, useEffect, useRef } from 'react'
import { api } from '../../services/api'
import type { RetirementWorkflow } from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { fmt, num, scoreColor } from './ScoreBreakdownPopover'

export interface WorkflowItem {
  catalog_base_name: string
  display_name: string
  provisions: number
  unique_users: number
  experiences: number
  success_ratio: number
  failure_ratio: number
  performance_score?: number
  pipeline_touched?: number
  closed_amount?: number
  total_cost?: number
  avg_cost_per_provision?: number
  first_activity?: string | null
  last_activity?: string | null
  owners?: Array<{ name: string; email: string }>
  stages?: Array<{ stage: string; ci_name: string; catalog_url: string }>
}

const stageBadgeClass: Record<string, string> = {
  prod: 'ca-env-prod', event: 'ca-env-event', dev: 'ca-env-dev', test: 'ca-env-test',
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

export function WorkflowDrawer({ item, onClose, onChanged }: { item: WorkflowItem; onClose: () => void; onChanged: () => void }) {
  const { isAdmin } = useAuth()
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
  const [notesSaved, setNotesSaved] = useState(false)
  const [linkJiraKey, setLinkJiraKey] = useState('')

  useEffect(() => {
    const loadWorkflow = async () => {
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
        setLinkJiraKey('')
        setNotesSaved(false)
      } catch { setDrawerWorkflow(null) }
      setDrawerLoading(false)
    }
    loadWorkflow()
  }, [item.catalog_base_name])

  const handleApprove = async () => {
    if (!approvalReason.trim()) return
    setActionLoading(true)
    setActionError(null)
    try {
      const { workflow } = await api.approveRetirementItem(
        item.catalog_base_name, approvalReason,
        replacementCi || undefined, replacementName || undefined
      )
      setDrawerWorkflow(workflow)
      onChanged()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Approval failed')
    }
    setActionLoading(false)
  }

  const handleNotify = async () => {
    setActionLoading(true)
    setActionError(null)
    try {
      const { workflow } = await api.notifyRetirementOwner(item.catalog_base_name)
      setDrawerWorkflow(workflow)
      onChanged()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Notification failed')
    }
    setActionLoading(false)
  }

  const handleStart = async () => {
    setActionLoading(true)
    setActionError(null)
    try {
      const { workflow } = await api.startRetirement(item.catalog_base_name, targetDays, jiraProject)
      setDrawerWorkflow(workflow)
      onChanged()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to start retirement')
    }
    setActionLoading(false)
  }

  const handleCancel = async () => {
    const hasJira = drawerWorkflow?.jira_key
    const msg = hasJira
      ? `This will cancel the retirement workflow and unlink ${drawerWorkflow.jira_key}. The Jira ticket will remain open. Continue?`
      : 'This will cancel the retirement workflow and remove all progress. Continue?'
    if (!confirm(msg)) return
    setActionLoading(true)
    setActionError(null)
    try {
      await api.cancelRetirementWorkflow(item.catalog_base_name)
      setDrawerWorkflow(null)
      onClose()
      onChanged()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Cancel failed')
    }
    setActionLoading(false)
  }

  const handleSaveNotes = async () => {
    try {
      const { workflow } = await api.updateRetirementNotes(item.catalog_base_name, notesText)
      setDrawerWorkflow(workflow)
      setNotesSaved(true)
      setTimeout(() => setNotesSaved(false), 2000)
    } catch (e) { console.error(e) }
  }

  const handleLinkJira = async () => {
    if (!linkJiraKey.trim()) return
    setActionLoading(true)
    setActionError(null)
    try {
      const { workflow } = await api.linkRetirementJira(item.catalog_base_name, linkJiraKey.trim())
      setDrawerWorkflow(workflow)
      setLinkJiraKey('')
      onChanged()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to link Jira ticket')
    }
    setActionLoading(false)
  }

  const generateEmailTemplate = () => {
    const owners = item.owners || []
    const ownerNames = owners.map(o => o.name || o.email).join(', ') || 'Content Owner'
    const reason = drawerWorkflow?.approval_reason || approvalReason || 'See RCARS retirement analysis'
    const replacement = drawerWorkflow?.replacement_name || replacementName
    const provs = num(item.provisions).toLocaleString()

    const metrics = [`- Provisions: ${provs}`]
    if (item.performance_score != null) metrics.push(`- Performance Score: ${item.performance_score}`)
    if (item.total_cost != null) metrics.push(`- Total Cost: ${fmt(item.total_cost)}`)
    if (item.pipeline_touched != null) metrics.push(`- Pipeline Touched: ${fmt(item.pipeline_touched)}`)

    const template = `Hi ${ownerNames},

This is a notification that "${item.display_name}" has been flagged for retirement from the Red Hat Demo Platform.

Reason:
${reason.split('\n').filter(l => l.trim()).map(l => `- ${l.trim()}`).join('\n')}

Key metrics (last 12 months):
${metrics.join('\n')}
${replacement ? `\nReplacement: ${replacement}` : ''}
${drawerWorkflow?.jira_key ? `\nJira: https://redhat.atlassian.net/browse/${drawerWorkflow.jira_key}` : ''}
If you have questions or concerns about this retirement, please reach out to Nate Stephany (nstephan@redhat.com).

Thank you,
RHDP Content Team`

    setEmailTemplate(template)
  }

  const wf = drawerWorkflow
  const isApproved = !!wf?.step_approved_at
  const isNotified = !!wf?.step_notified_at
  const isStarted = !!wf?.step_started_at
  const isRetired = !!wf?.step_retired_at

  const approveIsNext = !isApproved
  const notifyIsNext = isApproved && !isNotified && !isStarted
  const startIsNext = isApproved && !isStarted

  return (
    <>
      <div className="browse-drawer-overlay" onClick={onClose} />
      <div className="browse-drawer ret-drawer">
        <div className="browse-drawer-header">
          <div className="browse-drawer-title">{item.display_name}</div>
          <button className="browse-drawer-close" onClick={onClose} aria-label="Close drawer">&times;</button>
        </div>
        <div className="browse-drawer-body" style={{ padding: 0, gap: 0 }}>
          {drawerLoading ? (
            <p className="ca-color-muted" style={{ padding: 'var(--sp-md)' }}>Loading workflow...</p>
          ) : (
            <>
              {/* ── Usage Data Grid (fixed top, not scrollable) ── */}
              <div style={{ flexShrink: 0, padding: 'var(--sp-md)', paddingBottom: 0 }}>
              <div className="ret-data-grid">
                {item.performance_score != null && (
                <div className="ret-data-cell">
                  <div className="ret-data-label">Score</div>
                  <div className="ret-data-value" style={{ color: scoreColor(item.performance_score) }}>
                    {item.performance_score}
                  </div>
                </div>
                )}
                <div className="ret-data-cell">
                  <div className="ret-data-label">Provisions</div>
                  <div className="ret-data-value">{item.provisions.toLocaleString()}</div>
                </div>
                <div className="ret-data-cell">
                  <div className="ret-data-label">Unique Users</div>
                  <div className="ret-data-value">{item.unique_users.toLocaleString()}</div>
                </div>
                <div className="ret-data-cell">
                  <div className="ret-data-label">Experiences</div>
                  <div className="ret-data-value">{item.experiences.toLocaleString()}</div>
                </div>
                {item.pipeline_touched != null && (
                <div className="ret-data-cell">
                  <div className="ret-data-label">Touched</div>
                  <div className="ret-data-value">{fmt(item.pipeline_touched)}</div>
                </div>
                )}
                {item.closed_amount != null && (
                <div className="ret-data-cell">
                  <div className="ret-data-label">Closed</div>
                  <div className="ret-data-value ret-data-value--green">{fmt(item.closed_amount)}</div>
                </div>
                )}
                {item.total_cost != null && (
                <div className="ret-data-cell">
                  <div className="ret-data-label">Total Cost</div>
                  <div className="ret-data-value">{fmt(item.total_cost)}</div>
                </div>
                )}
                {item.avg_cost_per_provision != null && (
                <div className="ret-data-cell">
                  <div className="ret-data-label">Cost / Provision</div>
                  <div className="ret-data-value ret-data-value--small">${num(item.avg_cost_per_provision).toFixed(2)}</div>
                </div>
                )}
                <div className="ret-data-cell">
                  <div className="ret-data-label">Success Rate</div>
                  <div className="ret-data-value ret-data-value--green ret-data-value--small">{(num(item.success_ratio) * 100).toFixed(1)}%</div>
                </div>
                <div className="ret-data-cell">
                  <div className="ret-data-label">Failure Rate</div>
                  <div className="ret-data-value ret-data-value--small" style={{ color: num(item.failure_ratio) > 0.1 ? 'var(--score-red)' : 'var(--text-primary)' }}>
                    {(num(item.failure_ratio) * 100).toFixed(1)}%
                  </div>
                </div>
                {'first_activity' in item && (
                <div className="ret-data-cell">
                  <div className="ret-data-label">First Activity</div>
                  <div className="ret-data-value ret-data-value--small">{item.first_activity || 'N/A'}</div>
                </div>
                )}
                {'last_activity' in item && (
                <div className="ret-data-cell">
                  <div className="ret-data-label">Last Activity</div>
                  <div className="ret-data-value ret-data-value--small">{item.last_activity || 'N/A'}</div>
                </div>
                )}
                {item.stages && (
                <div className="ret-data-cell ret-data-cell--wide">
                  <div className="ret-data-label">Environments</div>
                  <div style={{ marginTop: '4px' }}>
                    {item.stages.map(s => (
                      <a key={s.ci_name} href={`/browse?search=${encodeURIComponent(item.display_name)}`} target="_blank" rel="noreferrer"
                        className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                        style={{ marginRight: 4 }}>
                        {s.stage}
                      </a>
                    ))}
                    {item.stages.length === 0 && <span className="ca-color-muted">none</span>}
                  </div>
                </div>
                )}
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
                            excludeBaseName={item.catalog_base_name}
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
                        {item.owners && item.owners.length > 0 && (
                          <div style={{ fontSize: '12px' }}>
                            <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>Detected owners:</div>
                            {item.owners.map((o, i) => (
                              <div key={i} style={{ color: 'var(--text-secondary)', marginBottom: '2px' }}>
                                {o.name || o.email}
                                {o.name && o.email && <span style={{ color: 'var(--text-muted)' }}> ({o.email})</span>}
                              </div>
                            ))}
                          </div>
                        )}
                        {item.owners && item.owners.length === 0 && (
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

                  {/* Step 3: Retirement In Progress */}
                  <StepperStep
                    title="Retirement In Progress"
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
                        {isAdmin ? (
                          <button className="ret-action-btn ret-action-btn--danger" onClick={handleCancel}
                            disabled={actionLoading}
                            style={{ fontSize: '11px', marginTop: '4px' }}>
                            {actionLoading ? 'Stopping...' : 'Stop Retirement'}
                          </button>
                        ) : (
                          <div style={{ fontSize: '11px', color: 'var(--score-amber)' }}>
                            Admin access required to stop retirement
                          </div>
                        )}
                      </div>
                    ) : isApproved ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {isAdmin ? (
                          <>
                            {/* Link existing Jira */}
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                              Already have a Jira ticket for this retirement?
                            </div>
                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                              <input type="text" className="browse-drawer-input"
                                value={linkJiraKey} onChange={e => setLinkJiraKey(e.target.value.toUpperCase())}
                                placeholder="RHDPCD-123"
                                style={{ width: '120px', fontSize: '12px' }} />
                              <button className="ret-action-btn ret-action-btn--start" onClick={handleLinkJira}
                                disabled={actionLoading || !linkJiraKey.trim()}
                                style={{ padding: '3px 10px', fontSize: '11px' }}>
                                {actionLoading ? 'Linking...' : 'Link Jira'}
                              </button>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '4px 0' }}>
                              <div style={{ flex: 1, height: '1px', background: 'var(--border-section)' }} />
                              <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>or create new</span>
                              <div style={{ flex: 1, height: '1px', background: 'var(--border-section)' }} />
                            </div>

                            {/* Create new Jira */}
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                              Creates a Jira ticket with retirement details, metrics snapshot, and adoc template.
                            </div>
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
                        ['score', 'Score', item.performance_score],
                        ['provisions', 'Provisions', item.provisions],
                        ['unique_users', 'Users', item.unique_users],
                        ['experiences', 'Experiences', item.experiences],
                        ['total_cost', 'Cost', item.total_cost],
                        ['pipeline_touched', 'Touched', item.pipeline_touched],
                        ['closed_amount', 'Closed', item.closed_amount],
                      ] as [string, string, number | undefined][]).map(([key, label, current]) => {
                        const snap = (wf.approval_snapshot?.sales ?? wf.approval_snapshot) as Record<string, number>
                        const snapped = snap[key as string]
                        if (snapped === undefined) return null
                        const snapVal = num(snapped)
                        const isMoney = ['total_cost', 'pipeline_touched', 'closed_amount'].includes(key as string)
                        const fmtVal = (v: number) => isMoney ? fmt(v) : v.toLocaleString()

                        if (current == null) {
                          return (
                            <tr key={key}>
                              <td>{label}</td>
                              <td>{fmtVal(snapVal)}</td>
                              <td>N/A</td>
                              <td />
                            </tr>
                          )
                        }

                        const delta = current - snapVal
                        let deltaClass = ''
                        if (delta !== 0) {
                          if (key === 'score') {
                            deltaClass = delta > 0 ? 'ret-snapshot-delta--up' : 'ret-snapshot-delta--down'
                          } else if (key === 'total_cost') {
                            deltaClass = delta > 0 ? 'ret-snapshot-delta--down' : 'ret-snapshot-delta--up'
                          } else {
                            deltaClass = delta > 0 ? 'ret-snapshot-delta--up' : 'ret-snapshot-delta--down'
                          }
                        }

                        return (
                          <tr key={key}>
                            <td>{label}</td>
                            <td>{fmtVal(snapVal)}</td>
                            <td>{fmtVal(current)}</td>
                            <td>
                              {delta !== 0 && (
                                <span className={`ret-snapshot-delta ${deltaClass}`}>
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
                  onChange={e => { setNotesText(e.target.value); setNotesSaved(false) }}
                  placeholder="Add notes about this item..."
                  rows={3}
                  style={{ fontSize: '12px' }}
                />
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                  <button className="ret-action-btn ret-action-btn--start"
                    onClick={handleSaveNotes}
                    style={{ padding: '3px 10px', fontSize: '11px' }}>
                    Save Notes
                  </button>
                  {notesSaved && (
                    <span style={{ fontSize: '11px', color: 'var(--pf-t--global--color--status--success--default)' }}>Saved</span>
                  )}
                </div>
              </div>

              {/* ── Cancel Workflow (admin only, when approved but not yet started) ── */}
              {wf && isApproved && !isStarted && isAdmin && (
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
  )
}
