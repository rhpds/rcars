import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../services/api'
import { Button } from '@patternfly/react-core'
import { LogWindow } from '../components/admin/LogWindow'

// ── Shared types ──

interface ActionState {
  log: string[]
  logOpen: boolean
  running: boolean
}

// ── AdminAction (reusable action button + log window) ──

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
      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>{description}</p>
      <Button variant="secondary" size="sm" onClick={handleRun} isDisabled={state.running}>
        {state.running ? `${buttonLabel}...` : buttonLabel}
      </Button>
      <LogWindow
        lines={state.log}
        isOpen={state.logOpen}
        onToggle={() => setState(prev => ({ ...prev, logOpen: !prev.logOpen }))}
      />
    </div>
  )
}

// ── ScanMonitor ──

function ScanMonitor() {
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
        } else {
          const propInfo = progress.total_propagated ? `, ${progress.total_propagated} propagated` : ''
          addLog(`  [${progress.complete} done, ${progress.running} running, ${progress.queued} queued, ${progress.failed} failed${propInfo}]`)
        }
      } catch { /* ignore */ }
    }, 10000)
  }, [addLog])

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
  }

  return (
    <div className="admin-section">
      <h3>Content Analysis</h3>
      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px', lineHeight: '1.7' }}>
        <p style={{ margin: '0 0 6px' }}><strong>Analyze</strong> — incremental; skips items whose content hasn't changed.</p>
        <ul style={{ margin: '0 0 8px 16px', padding: 0 }}>
          <li>Processes items that have never been analyzed</li>
          <li>Re-processes <em>stale</em> items — ones whose Showroom content changed since last analysis</li>
          <li>Each item takes ~30–60s; the AI model reads the pages and extracts products, audience, topics, and difficulty</li>
        </ul>
        <p style={{ margin: '0 0 6px' }}><strong>Check Stale</strong> — lightweight pre-pass, no AI calls.</p>
        <ul style={{ margin: '0 0 0 16px', padding: 0 }}>
          <li>Compares each item's current Showroom content hash against what was recorded at last analysis</li>
          <li>Flags changed items as stale so they're included in the next Analyze run</li>
        </ul>
      </div>
      <div style={{ display: 'flex', gap: '8px' }}>
        <Button variant="secondary" size="sm" onClick={handleScan} isDisabled={scanning || checking}>
          {scanning ? 'Analyzing...' : 'Analyze'}
        </Button>
        <Button variant="secondary" size="sm" onClick={handleCheckStale} isDisabled={scanning || checking}>
          {checking ? 'Checking...' : 'Check Stale'}
        </Button>
      </div>
      <LogWindow
        lines={log}
        isOpen={logOpen}
        onToggle={() => setLogOpen(!logOpen)}
      />
    </div>
  )
}

// ── RescanAllSection ──

function RescanAllSection() {
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
        } else {
          const propInfo = progress.total_propagated ? `, ${progress.total_propagated} propagated` : ''
          addLog(`  [${progress.complete} done, ${progress.running} running, ${progress.queued} queued, ${progress.failed} failed${propInfo}]`)
        }
      } catch { /* ignore */ }
    }, 10000)
  }

  useEffect(() => { return () => { if (intervalRef.current) clearInterval(intervalRef.current) } }, [])

  return (
    <div className="admin-section">
      <h3>Full Re-Analysis</h3>
      <div style={{ fontSize: '12px', color: 'var(--score-red)', marginBottom: '10px', lineHeight: '1.7' }}>
        <p style={{ margin: '0 0 6px' }}>Marks every item stale and re-analyzes all of them from scratch — <strong>not incremental</strong>.</p>
        <ul style={{ margin: '0 0 0 16px', padding: 0 }}>
          <li>Includes items whose content hasn't changed</li>
          <li>Takes several hours and consumes a large number of AI tokens</li>
          <li>Use only when the analysis pipeline itself has changed — e.g. after an analyzer bug fix or a prompt update that should affect all results</li>
        </ul>
      </div>
      <Button variant="secondary" size="sm" onClick={handleRescanAll} isDisabled={running}>
        {running ? 'Re-Analyzing...' : 'Re-Analyze All'}
      </Button>
      <LogWindow
        lines={log}
        isOpen={logOpen}
        onToggle={() => setLogOpen(!logOpen)}
      />
    </div>
  )
}

// ── WorkloadScanSection ──

function WorkloadScanSection() {
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
  }

  return (
    <div className="admin-section">
      <h3>Workload Repos</h3>
      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px', lineHeight: '1.7' }}>
        <p style={{ margin: '0 0 6px' }}>Scans AgnosticD v2 Ansible role repositories — incremental; skips repos whose HEAD commit hasn't changed.</p>
        <ul style={{ margin: '0 0 0 16px', padding: 0 }}>
          <li>An AI model reads each role's tasks to determine what products, operators, or services it installs</li>
          <li>Results are stored in the infrastructure catalog and used to classify what workloads a catalog item runs</li>
          <li>Also cleans up catalog entries for roles that have been deleted from the repository</li>
        </ul>
      </div>
      <Button variant="secondary" size="sm" onClick={handleScan} isDisabled={running}>
        {running ? 'Scanning...' : 'Scan Workload Repos'}
      </Button>
      <LogWindow
        lines={log}
        isOpen={logOpen}
        onToggle={() => setLogOpen(!logOpen)}
      />
    </div>
  )
}

// ── Scheduled Maintenance ──

interface ScheduleInfo {
  pipeline_enabled: boolean
  pipeline_schedule: string
  last_pipeline: {
    job_id: string; status: string; created_at: string; completed_at: string | null
    result: { refresh?: { total_items?: number }; stale_check?: { stale?: number }; analysis_enqueued?: number; warnings?: string[] } | null
    error: string | null
  } | null
}

function ScheduledMaintenance() {
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
  const jobStatusColor = (s: string) => s === 'complete' ? 'var(--score-green)' : s === 'failed' ? 'var(--score-red)' : s === 'running' ? 'var(--score-amber)' : 'var(--text-muted)'

  return (
    <div className="admin-section">
      <h3>Scheduled Maintenance</h3>
      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px', lineHeight: '1.7' }}>
        <p style={{ margin: '0 0 6px' }}>Runs automatically every night in four steps:</p>
        <ol style={{ margin: '0 0 6px 16px', padding: 0 }}>
          <li><strong>Catalog Sync</strong> — pulls latest metadata from all Babylon namespaces; retires items that no longer exist</li>
          <li><strong>Check Stale</strong> — compares Showroom content hashes to find items changed since last analysis</li>
          <li><strong>Re-Analyze</strong> — processes any stale or unanalyzed items</li>
          <li><strong>Workload Scan</strong> — checks AgnosticD repositories for new or changed roles; updates the infrastructure catalog</li>
        </ol>
        <p style={{ margin: 0 }}>Use the button below to trigger the full pipeline manually without waiting for the scheduled run.</p>
      </div>
      {schedule && (
        <>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '10px', fontSize: '13px' }}>
            <span style={{ color: schedule.pipeline_enabled ? 'var(--score-green)' : 'var(--score-red)', fontWeight: 600 }}>
              {schedule.pipeline_enabled ? 'Enabled' : 'Disabled'}
            </span>
            <span style={{ color: 'var(--text-muted)' }}>Schedule: {schedule.pipeline_schedule}</span>
          </div>
          {schedule.last_pipeline && (
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px', lineHeight: '1.6' }}>
              Last run: <span style={{ color: 'var(--text-secondary)' }}>{shortTime(schedule.last_pipeline.created_at)}</span>
              {' '}&mdash; <span style={{ color: jobStatusColor(schedule.last_pipeline.status) }}>{schedule.last_pipeline.status}</span>
              {schedule.last_pipeline.completed_at && <span> ({elapsed(schedule.last_pipeline.created_at, schedule.last_pipeline.completed_at)})</span>}
            </div>
          )}
        </>
      )}
      <Button variant="secondary" size="sm" onClick={handleRun} isDisabled={running}>
        {running ? 'Running...' : 'Run Maintenance Now'}
      </Button>
      <LogWindow lines={log} isOpen={logOpen} onToggle={() => setLogOpen(!logOpen)} />
    </div>
  )
}

// ── SyncPage ──

export function SyncPage() {
  return (
    <div className="admin-layout admin-layout--flex">
      <ScheduledMaintenance />

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
        }}
      />

      <ScanMonitor />

      <RescanAllSection />

      <WorkloadScanSection />

    </div>
  )
}
