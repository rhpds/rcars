import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { Button } from '@patternfly/react-core'

// Temporary shim: maps old LcarsButton API to PF6 Button for compilation.
// Full migration to PF6 Button variants happens in Task 6.
function LcarsButton(props: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string }) {
  const { variant: _variant, ...rest } = props
  return <Button variant="secondary" size="sm" {...rest as Record<string, unknown>} />
}
import { LogWindow } from '../components/admin/LogWindow'

// ── Catalog Status Page ──

interface CatalogStatus {
  total: number
  prod: number
  dev: number
  event: number
  scannable: number
  unique_showrooms: number
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
  const [checking, setChecking] = useState(false)
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
          addLog(`Analysis complete: ${progress.complete} analyzed + ${propCount} propagated = ${progress.complete + propCount} total, ${progress.failed} failed`)
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

  useEffect(() => {
    api.getScanProgress().then(progress => {
      if ((progress.queued > 0 || progress.running > 0) && progress.total > 0) {
        lastCompleteRef.current = progress.complete
        lastFailedRef.current = progress.failed
        addLog(`Reconnected to active analysis: ${progress.complete} done, ${progress.running} running, ${progress.queued} queued`)
        startPolling()
      }
    }).catch(() => {})
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [])

  const handleScan = async () => {
    setLog([])
    lastCompleteRef.current = 0
    lastFailedRef.current = 0
    addLog('Analyzing unanalyzed and stale items...')
    const result = await api.startScan() as { job_id: string; enqueued: number; total_scannable?: number; unique_pairs?: number; will_propagate?: number }
    if (result.total_scannable !== undefined) {
      addLog(`${result.total_scannable} scannable → ${result.unique_pairs} unique Showrooms queued, ${result.will_propagate ?? 0} will propagate`)
    } else {
      addLog(`${result.enqueued} items queued`)
    }
    if (result.enqueued === 0) { addLog('Nothing to analyze — all items are current.'); return }
    addLog('Monitoring progress...')
    startPolling()
  }

  const handleCheckStale = async () => {
    setChecking(true)
    setLogOpen(true)
    addLog('Checking for stale content...')
    const result = await api.checkStale()
    addLog(`job_id=${result.job_id}`)
    let seen = 0
    await new Promise<void>((resolve) => {
      const interval = setInterval(async () => {
        try {
          const job = await api.getJob(result.job_id)
          const messages = (job.progress_json?.messages ?? []) as Array<{ message?: string }>
          for (let i = seen; i < messages.length; i++) {
            if (messages[i].message) addLog(messages[i].message!)
          }
          seen = messages.length
          if (job.status === 'complete' || job.status === 'failed') {
            clearInterval(interval)
            if (job.error) addLog(`Error: ${job.error}`)
            resolve()
          }
        } catch { /* ignore */ }
      }, 2000)
      setTimeout(() => { clearInterval(interval); resolve() }, 30 * 60 * 1000)
    })
    setChecking(false)
    onStatusChange()
  }

  return (
    <div className="admin-section">
      <h3>Content Analysis</h3>
      <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
        Analyze processes unanalyzed and stale items via Sonnet (~30-60s per item). Check Stale compares content hashes to detect changes since last analysis.
      </p>
      <div style={{ display: 'flex', gap: '8px' }}>
        <LcarsButton onClick={handleScan} disabled={scanning || checking}>
          {scanning ? 'Analyzing...' : 'Analyze'}
        </LcarsButton>
        <LcarsButton onClick={handleCheckStale} disabled={scanning || checking}>
          {checking ? 'Checking...' : 'Check Stale'}
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

function RescanAllSection({ onStatusChange }: { onStatusChange: () => void }) {
  const [log, setLog] = useState<string[]>([])
  const [logOpen, setLogOpen] = useState(false)
  const [running, setRunning] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastCompleteRef = useRef(0)
  const lastFailedRef = useRef(0)

  const addLog = useCallback((msg: string) => setLog(prev => [...prev, msg]), [])

  const handleRescanAll = async () => {
    setLog([])
    setLogOpen(true)
    setRunning(true)
    lastCompleteRef.current = 0
    lastFailedRef.current = 0
    addLog('Marking all items as stale and queueing full re-analysis...')
    const result = await api.rescanAll()
    addLog(`${result.marked_stale} items marked stale`)
    if (result.total_scannable !== undefined) {
      addLog(`${result.total_scannable} scannable → ${result.unique_pairs} unique Showrooms queued`)
    }
    addLog(`${result.enqueued} analysis jobs enqueued — this will take several hours`)
    if (result.enqueued === 0) { addLog('Nothing to analyze.'); setRunning(false); return }

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
          addLog(`Full re-analysis complete: ${progress.complete} analyzed + ${propCount} propagated, ${progress.failed} failed`)
          setRunning(false)
          onStatusChange()
        } else {
          const propInfo = progress.total_propagated ? `, ${progress.total_propagated} propagated` : ''
          addLog(`  [${progress.complete} done, ${progress.running} running, ${progress.queued} queued, ${progress.failed} failed${propInfo}]`)
          onStatusChange()
        }
      } catch { /* ignore */ }
    }, 10000)
  }

  useEffect(() => { return () => { if (intervalRef.current) clearInterval(intervalRef.current) } }, [])

  return (
    <div className="admin-section">
      <h3>Full Re-Analysis</h3>
      <p style={{ fontSize: '12px', color: '#c9190b', marginBottom: '10px' }}>
        Marks ALL items stale and re-analyzes every Showroom from scratch. Takes several hours and consumes significant API tokens. Use only when the analysis pipeline has changed (e.g. analyzer bug fix).
      </p>
      <LcarsButton onClick={handleRescanAll} disabled={running}>
        {running ? 'Re-Analyzing...' : 'Re-Analyze All'}
      </LcarsButton>
      <LogWindow
        lines={log}
        isOpen={logOpen}
        onToggle={() => setLogOpen(!logOpen)}
      />
    </div>
  )
}

interface ScheduleInfo {
  pipeline_enabled: boolean
  pipeline_schedule: string
  last_pipeline: {
    job_id: string; status: string; created_at: string; completed_at: string | null
    result: { refresh?: { total_items?: number; retired_items?: number }; stale_check?: { stale?: number; stale_cis?: number; checked?: number; skipped?: number }; analysis_enqueued?: number; warnings?: string[] } | null
    error: string | null
  } | null
}

function ScheduledMaintenance({ onStatusChange }: { onStatusChange: () => void }) {
  const [schedule, setSchedule] = useState<ScheduleInfo | null>(null)
  const [log, setLog] = useState<string[]>([])
  const [logOpen, setLogOpen] = useState(false)
  const [running, setRunning] = useState(false)
  const addLog = useCallback((msg: string) => setLog(prev => [...prev, msg]), [])

  const loadSchedule = useCallback(() => {
    api.getScheduleStatus().then(data => setSchedule(data as ScheduleInfo))
  }, [])

  useEffect(() => { loadSchedule() }, [loadSchedule])

  const handleRun = async () => {
    setLog([])
    setLogOpen(true)
    setRunning(true)
    addLog('Starting maintenance pipeline...')
    const result = await api.runMaintenance()
    addLog(`job_id=${result.job_id}`)
    let seen = 0
    await new Promise<void>((resolve) => {
      const interval = setInterval(async () => {
        try {
          const job = await api.getJob(result.job_id)
          const messages = (job.progress_json?.messages ?? []) as Array<{ message?: string }>
          for (let i = seen; i < messages.length; i++) {
            if (messages[i].message) addLog(messages[i].message!)
          }
          seen = messages.length
          if (job.status === 'complete' || job.status === 'failed') {
            clearInterval(interval)
            if (job.error) addLog(`Error: ${job.error}`)
            resolve()
          }
        } catch { /* ignore */ }
      }, 3000)
      setTimeout(() => { clearInterval(interval); resolve() }, 3 * 60 * 60 * 1000)
    })
    setRunning(false)
    loadSchedule()
    onStatusChange()
  }

  const shortTime = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' })
  const elapsed = (created: string, completed: string | null) => {
    if (!completed) return 'running'
    const ms = new Date(completed).getTime() - new Date(created).getTime()
    const s = Math.round(ms / 1000)
    if (s < 60) return `${s}s`
    const m = Math.floor(s / 60)
    return `${m}m ${s % 60}s`
  }

  return (
    <div className="admin-section">
      <h3>Scheduled Maintenance</h3>
      <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
        Automated nightly pipeline: catalog refresh → stale check → re-analyze → workload scan. Runs inside the scan worker via arq cron.
      </p>
      {schedule && (
        <>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '10px', fontSize: '13px' }}>
            <span style={{ color: schedule.pipeline_enabled ? '#5cb85c' : '#c9190b', fontWeight: 600 }}>
              {schedule.pipeline_enabled ? 'Enabled' : 'Disabled'}
            </span>
            <span style={{ color: '#888' }}>Schedule: {schedule.pipeline_schedule}</span>
          </div>
          {schedule.last_pipeline && (
            <div style={{ fontSize: '12px', color: '#888', marginBottom: '10px', lineHeight: '1.6' }}>
              <div>
                Last run: <span style={{ color: '#ccc' }}>{shortTime(schedule.last_pipeline.created_at)}</span>
                {' '}— <span style={{
                  color: schedule.last_pipeline.status === 'complete' ? '#5cb85c'
                    : schedule.last_pipeline.status === 'failed' ? '#c9190b'
                    : schedule.last_pipeline.status === 'running' ? '#e8a838' : '#888'
                }}>{schedule.last_pipeline.status}</span>
                {schedule.last_pipeline.completed_at && (
                  <span> ({elapsed(schedule.last_pipeline.created_at, schedule.last_pipeline.completed_at)})</span>
                )}
              </div>
              {schedule.last_pipeline.result && (
                <div style={{ color: '#666' }}>
                  {schedule.last_pipeline.result.refresh && (
                    <span>{schedule.last_pipeline.result.refresh.total_items} items synced</span>
                  )}
                  {schedule.last_pipeline.result.stale_check && (
                    <span> · {schedule.last_pipeline.result.stale_check.stale} stale</span>
                  )}
                  {schedule.last_pipeline.result.analysis_enqueued !== undefined && schedule.last_pipeline.result.analysis_enqueued > 0 && (
                    <span> · {schedule.last_pipeline.result.analysis_enqueued} queued for re-analysis</span>
                  )}
                  {schedule.last_pipeline.result.warnings && schedule.last_pipeline.result.warnings.length > 0 && (
                    <span style={{ color: '#e8a838' }}> · {schedule.last_pipeline.result.warnings.length} warning(s)</span>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
      <LcarsButton onClick={handleRun} disabled={running}>
        {running ? 'Running...' : 'Run Maintenance Now'}
      </LcarsButton>
      <LogWindow
        lines={log}
        isOpen={logOpen}
        onToggle={() => setLogOpen(!logOpen)}
      />
    </div>
  )
}

interface InfraStats {
  v2_items: number
  with_workloads: number
  mapped_workloads: number
  verified_workloads: number
  unmapped_workloads: number
}

interface WorkloadMapping {
  workload_role: string
  product_name: string
  description: string | null
  category: string | null
  verified: boolean
}

interface UnmappedWorkload {
  workload_role: string
  workload_collection: string | null
  ci_count: number
}

function WorkloadScanSection({ onStatusChange }: { onStatusChange: () => void }) {
  const [log, setLog] = useState<string[]>([])
  const [logOpen, setLogOpen] = useState(false)
  const [running, setRunning] = useState(false)
  const addLog = useCallback((msg: string) => setLog(prev => [...prev, msg]), [])

  const handleScan = async () => {
    setLog([])
    setLogOpen(true)
    setRunning(true)
    addLog('Starting workload repository scan...')
    try {
      const result = await api.scanWorkloads()
      addLog(`job_id=${result.job_id}`)
      let seen = 0
      await new Promise<void>((resolve) => {
        const interval = setInterval(async () => {
          try {
            const job = await api.getJob(result.job_id)
            const messages = (job.progress_json?.messages ?? []) as Array<{ message?: string }>
            for (let i = seen; i < messages.length; i++) {
              if (messages[i].message) addLog(messages[i].message!)
            }
            seen = messages.length
            if (job.status === 'complete' || job.status === 'failed') {
              clearInterval(interval)
              if (job.error) addLog(`Error: ${job.error}`)
              resolve()
            }
          } catch { /* ignore */ }
        }, 3000)
        setTimeout(() => { clearInterval(interval); resolve() }, 30 * 60 * 1000)
      })
    } catch (err) {
      addLog(`Error: ${err}`)
    }
    setRunning(false)
    onStatusChange()
  }

  return (
    <div className="admin-section">
      <h3>Workload Repos</h3>
      <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
        Scan AgnosticD v2 workload repos for role changes. Reads Ansible code and uses Haiku to determine what each role installs. Updates the workload mapping table with verified product names.
      </p>
      <LcarsButton onClick={handleScan} disabled={running}>
        {running ? 'Scanning...' : 'Scan Workload Repos'}
      </LcarsButton>
      <LogWindow
        lines={log}
        isOpen={logOpen}
        onToggle={() => setLogOpen(!logOpen)}
      />
    </div>
  )
}

function WorkloadMappingSection({ onStatusChange }: { onStatusChange: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [mappings, setMappings] = useState<WorkloadMapping[]>([])
  const [unmapped, setUnmapped] = useState<UnmappedWorkload[]>([])
  const [loading, setLoading] = useState(false)
  const [mappingForm, setMappingForm] = useState<Record<string, { product: string; category: string }>>({})

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [mapData, unmapData] = await Promise.all([
        api.getWorkloadMappings() as Promise<{ mappings: WorkloadMapping[]; aliases: unknown[] }>,
        api.getUnmappedWorkloads() as Promise<{ unmapped: UnmappedWorkload[] }>,
      ])
      setMappings(mapData.mappings.sort((a, b) => a.product_name.localeCompare(b.product_name)))
      setUnmapped(unmapData.unmapped.sort((a, b) => b.ci_count - a.ci_count))
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  const handleExpand = () => {
    const next = !expanded
    setExpanded(next)
    if (next && mappings.length === 0) loadData()
  }

  const handleDelete = async (role: string) => {
    await api.deleteWorkloadMapping(role)
    loadData()
    onStatusChange()
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
    onStatusChange()
  }

  return (
    <div className="admin-section">
      <h3
        style={{ cursor: 'pointer' }}
        onClick={handleExpand}
      >
        {expanded ? '▾' : '▸'} Workload Mappings
        {mappings.length > 0 && (
          <span style={{ fontSize: '12px', color: '#666', fontWeight: 'normal', textTransform: 'none', letterSpacing: 0, marginLeft: '8px' }}>
            {mappings.length} mapped · {unmapped.length} unmapped
          </span>
        )}
      </h3>
      {expanded && (
        loading ? (
          <div style={{ color: '#666' }}>Loading...</div>
        ) : (
          <>
            {unmapped.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '13px', color: '#e8a838', marginBottom: '8px', fontWeight: 600 }}>
                  Unmapped Workloads ({unmapped.length})
                </div>
                <table className="status-table status-table--compact">
                  <thead><tr><th>Role</th><th>Collection</th><th style={{ textAlign: 'right' }}>CIs</th><th></th></tr></thead>
                  <tbody>
                    {unmapped.map(u => (
                      <tr key={u.workload_role}>
                        <td style={{ fontFamily: 'monospace', fontSize: '11px' }}>{u.workload_role}</td>
                        <td style={{ color: '#666', fontSize: '11px' }}>{u.workload_collection || '—'}</td>
                        <td style={{ textAlign: 'right' }}>{u.ci_count}</td>
                        <td style={{ textAlign: 'right' }}>
                          {mappingForm[u.workload_role] !== undefined ? (
                            <div className="mapping-inline-form">
                              <input
                                placeholder="Product name"
                                value={mappingForm[u.workload_role]?.product || ''}
                                onChange={(e) => setMappingForm(prev => ({
                                  ...prev, [u.workload_role]: { ...prev[u.workload_role], product: e.target.value }
                                }))}
                                onKeyDown={(e) => { if (e.key === 'Enter') handleMap(u.workload_role) }}
                              />
                              <input
                                placeholder="Category"
                                value={mappingForm[u.workload_role]?.category || ''}
                                onChange={(e) => setMappingForm(prev => ({
                                  ...prev, [u.workload_role]: { ...prev[u.workload_role], category: e.target.value }
                                }))}
                                onKeyDown={(e) => { if (e.key === 'Enter') handleMap(u.workload_role) }}
                                style={{ width: '100px' }}
                              />
                              <button onClick={() => handleMap(u.workload_role)}>Save</button>
                              <button
                                onClick={() => setMappingForm(prev => { const next = { ...prev }; delete next[u.workload_role]; return next })}
                                style={{ background: 'none', color: '#666' }}
                              >✕</button>
                            </div>
                          ) : (
                            <button
                              className="mapping-delete-btn"
                              style={{ color: '#73bcf7' }}
                              onClick={() => setMappingForm(prev => ({ ...prev, [u.workload_role]: { product: '', category: '' } }))}
                            >
                              Map
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div>
              <div style={{ fontSize: '13px', color: '#5cb85c', marginBottom: '8px', fontWeight: 600 }}>
                Mapped Workloads ({mappings.length})
              </div>
              <table className="status-table status-table--compact">
                <thead><tr><th>Role</th><th>Product Name</th><th>Category</th><th></th><th></th></tr></thead>
                <tbody>
                  {mappings.map(m => (
                    <tr key={m.workload_role}>
                      <td style={{ fontFamily: 'monospace', fontSize: '11px' }}>{m.workload_role}</td>
                      <td>{m.product_name}</td>
                      <td style={{ color: '#666' }}>{m.category || '—'}</td>
                      <td>{m.verified && <span className="verified-badge">verified</span>}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button className="mapping-delete-btn" onClick={() => handleDelete(m.workload_role)} title="Remove mapping">✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )
      )}
    </div>
  )
}

type AdminTab = 'status' | 'sync' | 'workloads'

export function AdminCatalogPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<AdminTab>('status')
  const [status, setStatus] = useState<CatalogStatus | null>(null)
  const [infraStats, setInfraStats] = useState<InfraStats | null>(null)
  const [llmProvider, setLlmProvider] = useState<{ litemaas_enabled: boolean; litemaas_url: string | null; litemaas_models: string[]; vertex_enabled: boolean; vertex_region: string | null; vertex_models: string[]; analysis_model: string; triage_model: string; rationale_model: string; scanning_model: string } | null>(null)
  const [reportingStatus, setReportingStatus] = useState<{ configured: boolean; total: number; with_provisions: number; with_cost: number; with_sales: number; last_synced: string | null } | null>(null)

  const loadStatus = () => {
    api.getCatalogStats().then(data => setStatus(data as CatalogStatus)).catch(() => {})
    api.getInfraStats().then(data => setInfraStats(data as InfraStats)).catch(() => {})
    api.getLlmProviderStatus().then(setLlmProvider).catch(() => {})
    api.getReportingStatus().then(setReportingStatus).catch(() => {})
  }

  useEffect(() => { loadStatus() }, [])

  const statusColor = (stale: boolean) => stale ? '#c9190b' : '#5cb85c'

  const clickableCount = (count: number, filter: string, warnColor = '#e8a838') => (
    <span
      onClick={() => count > 0 && navigate(`/browse?content_filter=${filter}`)}
      className={count > 0 ? 'admin-stat-row-link' : undefined}
      style={{ color: count > 0 ? warnColor : '#5cb85c' }}
    >{count}</span>
  )

  return (
    <div className="admin-layout admin-layout--flex">
      <div className="admin-tabs">
        <button className={`admin-tab${tab === 'status' ? ' active' : ''}`} onClick={() => setTab('status')}>Status</button>
        <button className={`admin-tab${tab === 'sync' ? ' active' : ''}`} onClick={() => setTab('sync')}>Sync & Analysis</button>
        <button className={`admin-tab${tab === 'workloads' ? ' active' : ''}`} onClick={() => setTab('workloads')}>Workloads</button>
      </div>

      {tab === 'status' && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <button
              onClick={loadStatus}
              style={{ background: 'transparent', border: '1px solid #333', color: '#666', cursor: 'pointer', fontSize: '12px', padding: '2px 8px', borderRadius: '4px' }}
            >↻ Refresh</button>
          </div>

          {status ? (
            <div className="admin-stat-cards">
              <div className="admin-stat-card">
                <div className="admin-stat-card-title">Catalog</div>
                <div className="admin-stat-row"><span className="admin-stat-row-label">Total items</span><span className="admin-stat-row-value">{status.total}</span></div>
                <div className="admin-stat-row"><span className="admin-stat-row-indent">Production</span><span className="admin-stat-row-value">{status.prod}</span></div>
                <div className="admin-stat-row"><span className="admin-stat-row-indent">Dev</span><span className="admin-stat-row-value">{status.dev}</span></div>
                <div className="admin-stat-row"><span className="admin-stat-row-indent">Event</span><span className="admin-stat-row-value">{status.event}</span></div>
                <div className="admin-stat-row-divider" />
                <div className="admin-stat-row"><span className="admin-stat-row-label">With Showroom</span><span className="admin-stat-row-value">{status.scannable}</span></div>
                <div className="admin-stat-row"><span className="admin-stat-row-indent">Unique</span><span className="admin-stat-row-value">{status.unique_showrooms}</span></div>
                <div className="admin-stat-row-divider" />
                <div className="admin-stat-row"><span className="admin-stat-row-label">Last sync</span><span style={{ color: statusColor(status.catalog_stale), fontSize: '12px' }}>{status.catalog_date}</span></div>
              </div>

              <div className="admin-stat-card">
                <div className="admin-stat-card-title">Analysis</div>
                <div className="admin-stat-row"><span className="admin-stat-row-label">Analyzed</span><span className="admin-stat-row-value">{status.analyzed}</span></div>
                <div className="admin-stat-row"><span className="admin-stat-row-label">Unanalyzed</span>{clickableCount(status.unanalyzed, 'unanalyzed')}</div>
                <div className="admin-stat-row"><span className="admin-stat-row-label">Stale</span>{clickableCount(status.stale_count, 'stale')}</div>
                <div className="admin-stat-row"><span className="admin-stat-row-label">Failures</span>{clickableCount(status.failed_count, 'scan_failures', '#c9190b')}</div>
                <div className="admin-stat-row-divider" />
                <div className="admin-stat-row"><span className="admin-stat-row-label">Last run</span><span style={{ color: statusColor(status.analysis_stale), fontSize: '12px' }}>{status.analysis_date}</span></div>
              </div>

              <div className="admin-stat-card">
                <div className="admin-stat-card-title">Infrastructure</div>
                {infraStats ? (
                  <>
                    <div className="admin-stat-row"><span className="admin-stat-row-label">AgnosticD v2</span><span className="admin-stat-row-value">{infraStats.v2_items}</span></div>
                    <div className="admin-stat-row"><span className="admin-stat-row-indent">With workloads</span><span className="admin-stat-row-value">{infraStats.with_workloads}</span></div>
                    <div className="admin-stat-row-divider" />
                    <div className="admin-stat-row"><span className="admin-stat-row-label">Mapped roles</span><span className="admin-stat-row-value">{infraStats.mapped_workloads}</span></div>
                    <div className="admin-stat-row"><span className="admin-stat-row-indent">Verified</span><span className="admin-stat-row-value">{infraStats.verified_workloads}</span></div>
                    <div className="admin-stat-row"><span className="admin-stat-row-label">Unmapped</span><span style={{ color: infraStats.unmapped_workloads > 0 ? '#e8a838' : '#5cb85c' }}>{infraStats.unmapped_workloads}</span></div>
                  </>
                ) : (
                  <div style={{ color: '#666', fontSize: '12px' }}>Loading...</div>
                )}
              </div>

              <div className="admin-stat-card">
                <div className="admin-stat-card-title">LLM Provider</div>
                {llmProvider ? (
                  <>
                    <div className="admin-stat-row"><span className="admin-stat-row-label">LiteMaaS</span><span style={{ color: llmProvider.litemaas_enabled ? '#3e8635' : '#666' }}>{llmProvider.litemaas_enabled ? 'Active' : 'Off'}</span></div>
                    {llmProvider.litemaas_enabled && (
                      <div className="admin-stat-row"><span className="admin-stat-row-indent">Models</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.litemaas_models.join(', ')}</span></div>
                    )}
                    <div className="admin-stat-row"><span className="admin-stat-row-label">Vertex AI</span><span style={{ color: llmProvider.vertex_enabled ? '#3e8635' : '#666' }}>{llmProvider.vertex_enabled ? (llmProvider.litemaas_enabled ? 'Fallback' : 'Active') : 'Off'}</span></div>
                    {llmProvider.vertex_enabled && llmProvider.vertex_models.length > 0 && (
                      <div className="admin-stat-row"><span className="admin-stat-row-indent">Models</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.vertex_models.join(', ')}</span></div>
                    )}
                    <div className="admin-stat-row-divider" />
                    <div className="admin-stat-row"><span className="admin-stat-row-label">Analysis</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.analysis_model}</span></div>
                    <div className="admin-stat-row"><span className="admin-stat-row-label">Triage</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.triage_model}</span></div>
                    <div className="admin-stat-row"><span className="admin-stat-row-label">Rationale</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.rationale_model}</span></div>
                  </>
                ) : (
                  <div style={{ color: '#666', fontSize: '12px' }}>Loading...</div>
                )}
              </div>

              <div className="admin-stat-card">
                <div className="admin-stat-card-title">Reporting Sync</div>
                {reportingStatus ? (
                  reportingStatus.total > 0 ? (
                    <>
                      <div className="admin-stat-row"><span className="admin-stat-row-label">Status</span><span style={{ color: '#5cb85c' }}>Synced</span></div>
                      <div className="admin-stat-row"><span className="admin-stat-row-label">Assets tracked</span><span className="admin-stat-row-value">{reportingStatus.total}</span></div>
                      <div className="admin-stat-row"><span className="admin-stat-row-label">With provisions</span><span className="admin-stat-row-value">{reportingStatus.with_provisions}</span></div>
                      <div className="admin-stat-row"><span className="admin-stat-row-label">With cost data</span><span className="admin-stat-row-value">{reportingStatus.with_cost}</span></div>
                      <div className="admin-stat-row"><span className="admin-stat-row-label">With sales data</span><span className="admin-stat-row-value">{reportingStatus.with_sales}</span></div>
                      <div className="admin-stat-row-divider" />
                      <div className="admin-stat-row"><span className="admin-stat-row-label">Last synced</span><span style={{ fontSize: '12px', color: '#888' }}>{reportingStatus.last_synced ? new Date(reportingStatus.last_synced).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'never'}</span></div>
                    </>
                  ) : (
                    <div style={{ color: '#666', fontSize: '12px' }}>{reportingStatus.configured ? 'Not synced yet' : 'Not configured'}</div>
                  )
                ) : (
                  <div style={{ color: '#666', fontSize: '12px' }}>Loading...</div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ color: '#666' }}>Loading...</div>
          )}

          <ScheduledMaintenance onStatusChange={loadStatus} />
        </>
      )}

      {tab === 'sync' && (
        <>
          <AdminAction
            title="Catalog Sync"
            description="Pull latest catalog metadata from all Babylon namespaces (prod, dev, event) and retire items no longer in Babylon."
            buttonLabel="Refresh Catalog"
            onRun={async (addLog) => {
              addLog('Starting catalog refresh...')
              const result = await api.refreshCatalog()
              addLog(`job_id=${result.job_id}`)
              let seen = 0
              await new Promise<void>((resolve) => {
                const interval = setInterval(async () => {
                  try {
                    const job = await api.getJob(result.job_id)
                    const messages = (job.progress_json?.messages ?? []) as Array<{ message?: string }>
                    for (let i = seen; i < messages.length; i++) {
                      if (messages[i].message) addLog(messages[i].message!)
                    }
                    seen = messages.length
                    if (job.status === 'complete' || job.status === 'failed') {
                      clearInterval(interval)
                      if (job.error) addLog(`Error: ${job.error}`)
                      resolve()
                    }
                  } catch { /* ignore */ }
                }, 2000)
                setTimeout(() => { clearInterval(interval); resolve() }, 5 * 60 * 1000)
              })
              loadStatus()
            }}
          />

          <ScanMonitor onStatusChange={loadStatus} />

          <RescanAllSection onStatusChange={loadStatus} />

          <RecentJobsSection />
        </>
      )}

      {tab === 'workloads' && (
        <>
          <WorkloadScanSection onStatusChange={loadStatus} />

          <WorkloadMappingSection onStatusChange={loadStatus} />
        </>
      )}

    </div>
  )
}

// ── Recent Jobs (embedded in Sync & Analysis tab) ──

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

function RecentJobsSection() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [expanded, setExpanded] = useState(false)

  const loadJobs = useCallback(async () => {
    const jb = await api.listJobs(50) as { items: Job[]; total: number }
    const statusOrder: Record<string, number> = { running: 0, queued: 1, failed: 2, complete: 3 }
    setJobs(jb.items.sort((a, b) => (statusOrder[a.status] ?? 9) - (statusOrder[b.status] ?? 9)))
  }, [])

  useEffect(() => {
    if (expanded) {
      loadJobs()
      const interval = setInterval(loadJobs, 10000)
      return () => clearInterval(interval)
    }
  }, [expanded, loadJobs])

  const jobStatusColor = (s: string) => s === 'complete' ? '#5cb85c' : s === 'failed' ? '#c9190b' : s === 'running' ? '#e8a838' : '#666'

  const shortTime = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

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
    <div className="admin-section">
      <h3 style={{ cursor: 'pointer' }} onClick={() => setExpanded(!expanded)}>
        {expanded ? '▾' : '▸'} Recent Jobs
      </h3>
      {expanded && (
        <>
          <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>Auto-refreshes every 10 seconds.</p>
          {jobs.length > 0 ? (
            <table className="status-table status-table--compact">
              <thead><tr><th>Type</th><th>CI Name</th><th>Status</th><th>Created</th><th>Completed</th><th>Duration</th></tr></thead>
              <tbody>
                {jobs.map(job => {
                  const ciName = job.progress_json?.ci_name || job.result_json?.ci_name
                  return (
                    <tr key={job.id} title={job.error || undefined}>
                      <td>{job.job_type}</td>
                      <td style={{ fontSize: '12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ciName || '-'}</td>
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
        </>
      )}
    </div>
  )
}

// ── Token Usage Page ──

interface TokenStats {
  stats: Array<{ operation: string; model: string; provider: string; calls: number; input_tokens: number; output_tokens: number; total_tokens: number }>
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
            <thead><tr><th>Operation</th><th>Model</th><th>Provider</th><th>Calls</th><th>Input</th><th>Output</th><th>Total</th></tr></thead>
            <tbody>
              {stats.stats.map((s, i) => (
                <tr key={i}>
                  <td>{s.operation}</td>
                  <td style={{ color: '#666' }}>{s.model}</td>
                  <td style={{ color: s.provider === 'litemaas' ? '#3e8635' : '#666' }}>{s.provider}</td>
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
          <table className="status-table status-table--compact">
            <thead><tr><th>Time</th><th>Query</th><th style={{ textAlign: 'right' }}>Triage</th><th style={{ textAlign: 'right' }}>Rationale</th></tr></thead>
            <tbody>
              {stats.recent_queries.map((q, i) => {
                const shortTime = new Date(q.query_time).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                const displayQuery = q.query_text.includes('\nAdditional context: ')
                  ? q.query_text.split('\nAdditional context: ').pop()!
                  : q.query_text
                const triage = q.triage_input + q.triage_output
                const rationale = q.rationale_input + q.rationale_output
                return (
                  <tr key={i}>
                    <td style={{ color: '#666', fontSize: '12px', whiteSpace: 'nowrap' }}>{shortTime}</td>
                    <td style={{ fontSize: '13px', maxWidth: '500px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {displayQuery}
                    </td>
                    <td style={{ textAlign: 'right', color: '#666', whiteSpace: 'nowrap' }}>{triage.toLocaleString()}</td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{rationale.toLocaleString()}</td>
                  </tr>
                )
              })}
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
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set())
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
              const isExpanded = expandedSessions.has(session.session_id)
              return (
                <div key={session.session_id} style={{ background: '#0d1117', borderRadius: '6px', border: '1px solid #1e2030' }}>
                  <div
                    style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', gap: '12px', alignItems: 'baseline' }}
                    onClick={() => setExpandedSessions(prev => {
                      const next = new Set(prev)
                      if (next.has(session.session_id)) next.delete(session.session_id)
                      else next.add(session.session_id)
                      return next
                    })}
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
                          {turn.query_text && (
                            <div style={{ color: '#e8a838', fontSize: '13px', marginBottom: '8px', fontWeight: 500 }}>
                              {turn.query_text}
                            </div>
                          )}
                          {turn.overall_assessment && (
                            <div style={{ color: '#aaa', fontSize: '13px', marginBottom: '10px', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                              {turn.overall_assessment.slice(0, 500)}{turn.overall_assessment.length > 500 ? '...' : ''}
                            </div>
                          )}
                          {turn.results_json && Array.isArray(turn.results_json) && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              {(turn.results_json as Array<{ ci_name?: string; display_name?: string; tier?: string; relevance_score?: number; vector_similarity_pct?: number; stage?: string }>).map((r, ri) => (
                                <div key={ri} style={{ fontSize: '12px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                                  <span style={{ color: tierColor(r.tier || 'white'), fontWeight: 600, width: '36px' }}>
                                    {r.relevance_score ?? r.vector_similarity_pct ?? '?'}%
                                  </span>
                                  <span style={{ color: '#bbb' }}>{r.display_name || r.ci_name}</span>
                                  {r.stage && r.stage !== 'prod' && (
                                    <span style={{ color: '#666', fontSize: '10px', border: '1px solid #333', borderRadius: '3px', padding: '0 4px' }}>
                                      {r.stage}
                                    </span>
                                  )}
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
