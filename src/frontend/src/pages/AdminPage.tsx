import { useState, useEffect, useRef, useCallback } from 'react'
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

function ScanMonitor({ onStatusChange }: { onStatusChange: () => void }) {
  const [log, setLog] = useState<string[]>([])
  const [logOpen, setLogOpen] = useState(false)
  const [scanning, setScanning] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastCompleteRef = useRef(0)
  const lastFailedRef = useRef(0)

  const addLog = useCallback((msg: string) => setLog(prev => [...prev, msg]), [])

  const startPolling = useCallback(() => {
    if (intervalRef.current) return
    setScanning(true)
    setLogOpen(true)

    intervalRef.current = setInterval(async () => {
      try {
        const progress = await api.getScanProgress()
        if (progress.complete > lastCompleteRef.current) {
          const newItems = progress.recent_complete.slice(-(progress.complete - lastCompleteRef.current))
          for (const ci of newItems) addLog(`  ✓ ${ci}`)
        }
        if (progress.failed > lastFailedRef.current) {
          const newFails = progress.recent_failures.slice(-(progress.failed - lastFailedRef.current))
          for (const err of newFails) addLog(`  ✗ ${err}`)
        }
        lastCompleteRef.current = progress.complete
        lastFailedRef.current = progress.failed

        const done = progress.queued === 0 && progress.running === 0 && progress.total > 0
        if (done) {
          if (intervalRef.current) clearInterval(intervalRef.current)
          intervalRef.current = null
          const propCount = progress.total_propagated || 0
          addLog(`Scan complete: ${progress.complete} scanned + ${propCount} propagated = ${progress.complete + propCount} total, ${progress.failed} failed`)
          setScanning(false)
          onStatusChange()
        } else {
          const propInfo = progress.total_propagated ? `, ${progress.total_propagated} propagated` : ''
          addLog(`  [${progress.complete} done, ${progress.running} running, ${progress.queued} queued, ${progress.failed} failed${propInfo}]`)
          onStatusChange()
        }
      } catch { /* ignore */ }
    }, 10000)
  }, [addLog, onStatusChange])

  // On mount, check if a scan is already running
  useEffect(() => {
    api.getScanProgress().then(progress => {
      if ((progress.queued > 0 || progress.running > 0) && progress.total > 0) {
        lastCompleteRef.current = progress.complete
        lastFailedRef.current = progress.failed
        addLog(`Reconnected to active scan: ${progress.complete} done, ${progress.running} running, ${progress.queued} queued`)
        startPolling()
      }
    }).catch(() => {})
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [])

  const handleScanUnanalyzed = async () => {
    setLog([])
    lastCompleteRef.current = 0
    lastFailedRef.current = 0
    addLog('Starting scan of unanalyzed items...')
    const result = await api.startScan() as { job_id: string; enqueued: number; total_scannable?: number; unique_pairs?: number; will_propagate?: number }
    if (result.total_scannable !== undefined) {
      addLog(`${result.total_scannable} scannable → ${result.unique_pairs} unique Showrooms queued, ${result.will_propagate ?? 0} will propagate`)
    } else {
      addLog(`${result.enqueued} items queued`)
    }
    if (result.enqueued === 0) { addLog('Nothing to scan.'); return }
    addLog('Monitoring progress...')
    startPolling()
  }

  const handleRescanAll = async () => {
    setLog([])
    lastCompleteRef.current = 0
    lastFailedRef.current = 0
    addLog('Marking all items as stale and queueing full rescan...')
    const result = await api.rescanAll()
    addLog(`${result.marked_stale} items marked stale`)
    if (result.total_scannable !== undefined) {
      addLog(`${result.total_scannable} scannable → ${result.unique_pairs} unique Showrooms queued`)
    }
    addLog(`${result.enqueued} analysis jobs enqueued`)
    if (result.enqueued === 0) { addLog('Nothing to scan.'); return }
    addLog('Monitoring progress...')
    startPolling()
  }

  return (
    <div className="admin-section">
      <h3>Showroom Analysis</h3>
      <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
        Clone and analyze Showroom repos via Sonnet. Duration depends on item count (~30-60s per item).
      </p>
      <div style={{ display: 'flex', gap: '8px' }}>
        <LcarsButton onClick={handleScanUnanalyzed} disabled={scanning}>
          {scanning ? 'Scanning...' : 'Scan Unanalyzed'}
        </LcarsButton>
        <LcarsButton onClick={handleRescanAll} disabled={scanning}>
          Rescan All
        </LcarsButton>
      </div>
      <LogWindow
        lines={log}
        isOpen={logOpen}
        onToggle={() => setLogOpen(!logOpen)}
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

      <ScanMonitor onStatusChange={loadStatus} />

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
    <div className="admin-layout admin-layout--wide">
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {stats.recent_queries.map((q, i) => {
              const isFollowUp = q.query_text.includes('\nAdditional context: ')
              const displayQuery = isFollowUp
                ? '↳ ' + q.query_text.split('\nAdditional context: ').pop()
                : q.query_text
              const triageTotal = q.triage_input + q.triage_output
              const rationaleTotal = q.rationale_input + q.rationale_output
              const shortTime = new Date(q.query_time).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
              return (
                <div key={i} style={{
                  display: 'flex', gap: '10px', alignItems: 'baseline', fontSize: '13px',
                  padding: isFollowUp ? '2px 0 2px 16px' : '4px 0',
                  borderTop: !isFollowUp && i > 0 ? '1px solid #1a1a2a' : undefined,
                }}>
                  <span style={{ color: '#666', fontSize: '11px', flexShrink: 0, width: '110px' }}>{shortTime}</span>
                  <span style={{ color: isFollowUp ? '#888' : '#ccc', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {displayQuery}
                  </span>
                  <span style={{ color: '#666', fontSize: '11px', flexShrink: 0 }} title="Triage tokens">T:{triageTotal.toLocaleString()}</span>
                  <span style={{ color: '#666', fontSize: '11px', flexShrink: 0 }} title="Rationale tokens">R:{rationaleTotal.toLocaleString()}</span>
                  <span style={{ color: '#aaa', fontSize: '11px', flexShrink: 0, width: '50px', textAlign: 'right' }}>{q.total_tokens?.toLocaleString()}</span>
                </div>
              )
            })}
          </div>
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
