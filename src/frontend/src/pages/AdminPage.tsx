import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { LcarsButton } from '../components/lcars'
import { LogWindow } from '../components/admin/LogWindow'

// ── Catalog Status Page ──

interface CatalogStatus {
  total: number
  prod: number
  dev: number
  event: number
  scannable: number
  analyzed: number
  last_refresh: string
  catalog_stale: boolean
  catalog_date: string
  analysis_stale: boolean
  analysis_date: string
  unanalyzed: number
  stale_count: number
  failed_count: number
}

interface ActionState {
  log: string[]
  logOpen: boolean
  running: boolean
}

function AdminAction({ title, description, buttonLabel, onRun }: {
  title: string; description: string; buttonLabel: string; onRun: (addLog: (msg: string) => void) => Promise<void>
}) {
  const [state, setState] = useState<ActionState>({ log: [], logOpen: false, running: false })

  const addLog = (msg: string) => setState(prev => ({ ...prev, log: [...prev.log, msg] }))

  const handleRun = async () => {
    setState(prev => ({ ...prev, running: true, logOpen: true }))
    try {
      await onRun(addLog)
    } catch (err) {
      addLog(`Error: ${err}`)
    }
    setState(prev => ({ ...prev, running: false }))
  }

  return (
    <div className="admin-section">
      <h3>{title}</h3>
      <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>{description}</p>
      <LcarsButton onClick={handleRun} disabled={state.running}>
        {state.running ? `${buttonLabel}...` : buttonLabel}
      </LcarsButton>
      <LogWindow
        lines={state.log}
        isOpen={state.logOpen}
        onToggle={() => setState(prev => ({ ...prev, logOpen: !prev.logOpen }))}
      />
    </div>
  )
}

export function AdminCatalogPage() {
  const [status, setStatus] = useState<CatalogStatus | null>(null)

  const loadStatus = () => {
    api.getCatalogStats().then(data => setStatus(data as CatalogStatus))
  }

  useEffect(() => { loadStatus() }, [])

  const statusColor = (stale: boolean) => stale ? '#c9190b' : '#5cb85c'

  return (
    <div className="admin-layout">
      <div className="admin-section">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <h3 style={{ margin: 0 }}>Catalog Status</h3>
          <button
            onClick={loadStatus}
            style={{ background: 'transparent', border: '1px solid #333', color: '#666', cursor: 'pointer', fontSize: '12px', padding: '2px 8px', borderRadius: '4px' }}
          >
            ↻ Refresh
          </button>
        </div>
        {status ? (
          <table className="status-table">
            <thead><tr><th>Metric</th><th>Count</th></tr></thead>
            <tbody>
              <tr><td>Total catalog items</td><td>{status.total}</td></tr>
              <tr><td style={{ paddingLeft: '24px', color: '#888' }}>Production</td><td>{status.prod}</td></tr>
              <tr><td style={{ paddingLeft: '24px', color: '#888' }}>Dev</td><td>{status.dev}</td></tr>
              <tr><td style={{ paddingLeft: '24px', color: '#888' }}>Event</td><td>{status.event}</td></tr>
              <tr style={{ borderTop: '1px solid #2a2a3a' }}>
                <td>Scannable (with Showroom)</td><td>{status.scannable}</td>
              </tr>
              <tr><td>Analyzed</td><td>{status.analyzed}</td></tr>
              <tr><td>Unanalyzed</td><td>{status.unanalyzed}</td></tr>
              <tr>
                <td>Stale (needs rescan)</td>
                <td style={{ color: status.stale_count > 0 ? '#e8a838' : '#5cb85c' }}>{status.stale_count}</td>
              </tr>
              <tr>
                <td>Scan failures</td>
                <td style={{ color: status.failed_count > 0 ? '#c9190b' : '#5cb85c' }}>{status.failed_count}</td>
              </tr>
              <tr style={{ borderTop: '1px solid #2a2a3a' }}>
                <td style={{ color: '#666' }}>Last catalog sync</td>
                <td style={{ color: statusColor(status.catalog_stale) }}>{status.catalog_date}</td>
              </tr>
              <tr>
                <td style={{ color: '#666' }}>Last analysis run</td>
                <td style={{ color: statusColor(status.analysis_stale) }}>{status.analysis_date}</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <div style={{ color: '#666' }}>Loading...</div>
        )}
      </div>

      <AdminAction
        title="Catalog Sync"
        description="Pull latest catalog metadata from all Babylon namespaces (prod, dev, event) and reconcile removed items."
        buttonLabel="Refresh Catalog"
        onRun={async (addLog) => {
          addLog('Starting catalog refresh...')
          const result = await api.refreshCatalog()
          addLog(`job_id=${result.job_id}`)
          await new Promise<void>((resolve) => {
            const stop = api.streamJob(result.job_id, (msg) => {
              addLog(msg.user_message)
              if (msg.phase === 'complete' || msg.phase === 'failed') {
                stop()
                resolve()
              }
            })
            // Fallback: resolve after 5 minutes even if SSE stalls
            setTimeout(() => { stop(); resolve() }, 5 * 60 * 1000)
          })
          loadStatus()
        }}
      />

      <AdminAction
        title="Showroom Analysis"
        description="Clone and analyze Showroom repos via Sonnet for unscanned items. Runs in background. Duration depends on item count (~30-60s per item)."
        buttonLabel="Scan Unanalyzed"
        onRun={async (addLog) => {
          addLog('Starting scan...')
          const result = await api.startScan() as { job_id: string; enqueued: number; total_scannable?: number; unique_pairs?: number; will_propagate?: number }
          if (result.total_scannable !== undefined && result.unique_pairs !== undefined) {
            addLog(`${result.total_scannable} scannable → ${result.unique_pairs} unique Showrooms queued, ${result.will_propagate ?? 0} will propagate from siblings`)
          } else {
            addLog(`${result.enqueued} items queued for analysis`)
          }
          addLog('Monitoring progress...')

          let lastComplete = 0
          let lastFailed = 0
          let lastStatusLine = ''
          const poll = async (): Promise<boolean> => {
            const progress = await api.getScanProgress()
            // Log newly completed items
            if (progress.complete > lastComplete) {
              const newItems = progress.recent_complete.slice(-(progress.complete - lastComplete))
              for (const ci of newItems) {
                addLog(`  ✓ ${ci}`)
              }
            }
            if (progress.failed > lastFailed) {
              const newFails = progress.recent_failures.slice(-(progress.failed - lastFailed))
              for (const err of newFails) {
                addLog(`  ✗ ${err}`)
              }
            }
            lastComplete = progress.complete
            lastFailed = progress.failed

            const done = progress.queued === 0 && progress.running === 0 && progress.total > 0
            if (!done) {
              const propInfo = progress.total_propagated ? `, ${progress.total_propagated} propagated` : ''
              const statusLine = `  [${progress.complete} scanned, ${progress.running} running, ${progress.queued} queued, ${progress.failed} failed${propInfo}]`
              if (statusLine !== lastStatusLine) {
                addLog(statusLine)
                lastStatusLine = statusLine
              }
            }
            loadStatus()
            return done
          }

          // Poll every 10 seconds until all jobs are done
          const interval = setInterval(async () => {
            try {
              const done = await poll()
              if (done) {
                clearInterval(interval)
                const finalProgress = await api.getScanProgress()
                const propCount = finalProgress.total_propagated || 0
                addLog(`Scan complete: ${lastComplete} scanned + ${propCount} propagated = ${lastComplete + propCount} total, ${lastFailed} failed`)
                loadStatus()
              }
            } catch {
              // ignore polling errors
            }
          }, 10000)
        }}
      />

      <AdminAction
        title="Content Updates"
        description="Check if any analyzed Showrooms have changed since last scan by comparing content hashes. Marks changed items as stale for re-analysis."
        buttonLabel="Check Stale"
        onRun={async (addLog) => {
          addLog('Starting stale check...')
          const result = await api.checkStale()
          addLog(`job_id=${result.job_id}`)
          await new Promise<void>((resolve) => {
            const stop = api.streamJob(result.job_id, (msg) => {
              addLog(msg.user_message)
              if (msg.phase === 'complete' || msg.phase === 'failed') {
                stop()
                resolve()
              }
            })
            setTimeout(() => { stop(); resolve() }, 30 * 60 * 1000)
          })
          loadStatus()
        }}
      />

      <AdminAction
        title="Rescan Stale Items"
        description="Re-analyze all items currently marked as stale. Enqueues individual analysis jobs for each stale item."
        buttonLabel="Rescan Stale"
        onRun={async (addLog) => {
          addLog('Starting rescan of stale items...')
          const result = await api.rescanStale() as { job_id: string; enqueued: number }
          addLog(`${result.enqueued} stale items queued (job_id=${result.job_id})`)
          if (result.enqueued > 0) {
            addLog('Analysis jobs running — monitor progress in the Scan Unanalyzed log above.')
          }
          loadStatus()
        }}
      />
    </div>
  )
}

// ── Workers Page ──

interface WorkerHealth {
  queue_depths: Record<string, number>
  active_jobs: number
  running_jobs: Array<{ id: string; job_type: string; ci_name: string | null; created_at: string }>
  failed_jobs_recent: number
}

interface Job {
  id: string
  job_type: string
  status: string
  queue: string
  created_by: string | null
  error: string | null
  created_at: string
  completed_at: string | null
  progress_json: { ci_name?: string } | null
  result_json: { ci_name?: string; status?: string; propagated?: number } | null
}

export function AdminWorkersPage() {
  const [health, setHealth] = useState<WorkerHealth | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])

  const loadData = async () => {
    const [wh, jb] = await Promise.all([
      api.getWorkerHealth() as Promise<WorkerHealth>,
      api.listJobs(30) as Promise<{ items: Job[]; total: number }>,
    ])
    setHealth(wh)
    setJobs(jb.items)
  }

  useEffect(() => { loadData() }, [])

  useEffect(() => {
    const interval = setInterval(async () => {
      const [wh, jb] = await Promise.all([
        api.getWorkerHealth() as Promise<WorkerHealth>,
        api.listJobs(30) as Promise<{ items: Job[]; total: number }>,
      ])
      setHealth(wh)
      setJobs(jb.items)
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const jobStatusColor = (status: string) => {
    if (status === 'complete') return '#5cb85c'
    if (status === 'failed') return '#c9190b'
    if (status === 'running') return '#e8a838'
    return '#666'
  }

  const shortTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  const elapsed = (created: string, completed: string | null) => {
    if (!completed) return '-'
    const ms = new Date(completed).getTime() - new Date(created).getTime()
    if (ms < 1000) return '<1s'
    const s = Math.round(ms / 1000)
    if (s < 60) return `${s}s`
    const m = Math.floor(s / 60)
    return `${m}m ${s % 60}s`
  }

  return (
    <div className="admin-layout admin-layout--wide">
      <div className="admin-section">
        <h3>Queue Depths</h3>
        <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
          Number of jobs waiting in each Redis queue. Auto-refreshes every 10 seconds.
        </p>
        {health ? (
          <table className="status-table status-table--compact">
            <thead><tr><th>Queue</th><th>Depth</th><th>Status</th></tr></thead>
            <tbody>
              {Object.entries(health.queue_depths).map(([queue, depth]) => (
                <tr key={queue}>
                  <td>{queue}</td>
                  <td>{depth}</td>
                  <td style={{ color: depth > 0 ? '#e8a838' : '#5cb85c' }}>
                    {depth > 0 ? 'Jobs waiting' : 'Clear'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color: '#666' }}>Loading...</div>
        )}
        {health && (
          <div style={{ marginTop: '10px', fontSize: '14px', color: '#aaa' }}>
            Active jobs: {health.active_jobs} · Recent failures:{' '}
            <span style={{ color: health.failed_jobs_recent > 0 ? '#c9190b' : '#5cb85c' }}>
              {health.failed_jobs_recent}
            </span>
          </div>
        )}
      </div>

      <div className="admin-section">
        <h3>Recent Jobs</h3>
        {jobs.length > 0 ? (
          <table className="status-table status-table--compact">
            <thead><tr><th>Type</th><th>CI Name</th><th>Status</th><th>Created</th><th>Completed</th><th>Duration</th></tr></thead>
            <tbody>
              {jobs.map(job => {
                const ciName = job.progress_json?.ci_name || job.result_json?.ci_name
                return (
                  <tr key={job.id} title={job.error || undefined}>
                    <td>{job.job_type}</td>
                    <td style={{ fontSize: '12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {ciName || '-'}
                    </td>
                    <td style={{ color: jobStatusColor(job.status) }}>{job.status}</td>
                    <td style={{ color: '#666', fontSize: '12px', whiteSpace: 'nowrap' }}>{shortTime(job.created_at)}</td>
                    <td style={{ color: '#666', fontSize: '12px', whiteSpace: 'nowrap' }}>{job.completed_at ? shortTime(job.completed_at) : '-'}</td>
                    <td style={{ color: '#888', fontSize: '12px', whiteSpace: 'nowrap' }}>{elapsed(job.created_at, job.completed_at)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ color: '#666' }}>No recent jobs.</div>
        )}
      </div>
    </div>
  )
}

// ── Token Usage Page ──

interface TokenStats {
  stats: Array<{ operation: string; model: string; calls: number; input_tokens: number; output_tokens: number; total_tokens: number }>
  recent_queries: Array<{ query_text: string; query_time: string; total_tokens: number; triage_input: number; triage_output: number; rationale_input: number; rationale_output: number }>
  days: number
}

export function AdminTokensPage() {
  const [stats, setStats] = useState<TokenStats | null>(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    api.getTokenUsage(days).then(data => setStats(data as TokenStats))
  }, [days])

  return (
    <div className="admin-layout">
      <div className="admin-section">
        <h3>Token Usage</h3>
        <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
          Claude API token consumption by model and operation.
        </p>
        <div style={{ marginBottom: '12px' }}>
          <select
            className="filter-select"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </div>

        {stats && stats.stats.length > 0 ? (
          <table className="status-table">
            <thead><tr><th>Operation</th><th>Model</th><th>Calls</th><th>Input</th><th>Output</th><th>Total</th></tr></thead>
            <tbody>
              {stats.stats.map((s, i) => (
                <tr key={i}>
                  <td>{s.operation}</td>
                  <td style={{ color: '#666' }}>{s.model}</td>
                  <td>{s.calls}</td>
                  <td style={{ color: '#666' }}>{s.input_tokens?.toLocaleString()}</td>
                  <td style={{ color: '#666' }}>{s.output_tokens?.toLocaleString()}</td>
                  <td>{s.total_tokens?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color: '#666' }}>No token usage data for this period.</div>
        )}
      </div>

      {stats && stats.recent_queries.length > 0 && (
        <div className="admin-section">
          <h3>Recent Queries</h3>
          <table className="status-table">
            <thead><tr><th>Query</th><th>Time</th><th>Triage</th><th>Rationale</th><th>Total</th></tr></thead>
            <tbody>
              {stats.recent_queries.map((q, i) => (
                <tr key={i}>
                  <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {q.query_text}
                  </td>
                  <td style={{ color: '#666', fontSize: '13px' }}>{new Date(q.query_time).toLocaleString()}</td>
                  <td style={{ color: '#666' }}>{(q.triage_input + q.triage_output).toLocaleString()}</td>
                  <td style={{ color: '#666' }}>{(q.rationale_input + q.rationale_output).toLocaleString()}</td>
                  <td>{q.total_tokens?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── Query History Page ──

interface QuerySession {
  session_id: string
  started_at: string
  turn_count: number
  turns: Array<{
    query_text: string | null
    overall_assessment: string | null
    results_json: unknown[] | null
    chosen_ci_name: string | null
    opted_out: boolean
    created_at: string
  }>
}

export function AdminQueriesPage() {
  const [sessions, setSessions] = useState<QuerySession[]>([])
  const [expandedSession, setExpandedSession] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getQueryHistory(50).then(data => {
      setSessions((data as { items: QuerySession[] }).items)
      setLoading(false)
    })
  }, [])

  const shortTime = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  const tierColor = (tier: string) => {
    if (tier === 'green') return '#5cb85c'
    if (tier === 'yellow') return '#e8a838'
    return '#666'
  }

  return (
    <div className="admin-layout admin-layout--wide">
      <div className="admin-section">
        <h3>Query History</h3>
        <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
          Advisor queries and recommendations. Click to expand details.
        </p>

        {loading ? (
          <div style={{ color: '#666' }}>Loading...</div>
        ) : sessions.length === 0 ? (
          <div style={{ color: '#666' }}>No queries recorded yet.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {sessions.map(session => {
              const firstQuery = session.turns[0]?.query_text
              const isExpanded = expandedSession === session.session_id
              return (
                <div key={session.session_id} style={{ background: '#0d1117', borderRadius: '6px', border: '1px solid #1e2030' }}>
                  <div
                    style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', gap: '12px', alignItems: 'baseline' }}
                    onClick={() => setExpandedSession(isExpanded ? null : session.session_id)}
                  >
                    <span style={{ color: '#666', fontSize: '12px', flexShrink: 0, whiteSpace: 'nowrap' }}>
                      {isExpanded ? '▾' : '▸'} {shortTime(session.started_at)}
                    </span>
                    <span style={{ color: '#ccc', fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {firstQuery || '(empty query)'}
                    </span>
                    {session.turns.some(t => t.chosen_ci_name) && (
                      <span style={{ color: '#5cb85c', fontSize: '11px', flexShrink: 0 }}>has selection</span>
                    )}
                  </div>
                  {isExpanded && session.turns.map((turn, ti) => (
                    <div key={ti} style={{ padding: '10px 14px 14px', borderTop: '1px solid #1e2030' }}>
                      {turn.opted_out ? (
                        <div style={{ color: '#555', fontStyle: 'italic', fontSize: '13px' }}>Query redacted (user opted out)</div>
                      ) : (
                        <>
                          {turn.overall_assessment && (
                            <div style={{ color: '#aaa', fontSize: '13px', marginBottom: '10px', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                              {turn.overall_assessment.slice(0, 500)}{turn.overall_assessment.length > 500 ? '...' : ''}
                            </div>
                          )}
                          {turn.results_json && Array.isArray(turn.results_json) && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              {(turn.results_json as Array<{ ci_name?: string; display_name?: string; tier?: string; relevance_score?: number }>).map((r, ri) => (
                                <div key={ri} style={{ fontSize: '12px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                                  <span style={{ color: tierColor(r.tier || 'white'), fontWeight: 600, width: '36px' }}>
                                    {r.relevance_score ?? '?'}%
                                  </span>
                                  <span style={{ color: '#bbb' }}>{r.display_name || r.ci_name}</span>
                                  {turn.chosen_ci_name === r.ci_name && (
                                    <span style={{ color: '#5cb85c', fontSize: '10px' }}>SELECTED</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
