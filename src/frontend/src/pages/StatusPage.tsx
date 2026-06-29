import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { Button } from '@patternfly/react-core'
import { LogWindow } from '../components/admin/LogWindow'

// ── Interfaces ──

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

interface InfraStats {
  v2_items: number
  with_workloads: number
  mapped_workloads: number
  verified_workloads: number
  unmapped_workloads: number
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

// ── ScheduledMaintenance (status-page-only component) ──

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

  const jobStatusColor = (status: string) =>
    status === 'complete' ? 'var(--score-green)'
      : status === 'failed' ? 'var(--score-red)'
      : status === 'running' ? 'var(--score-amber)' : 'var(--text-muted)'

  return (
    <div className="admin-section">
      <h3>Scheduled Maintenance</h3>
      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
        Automated nightly pipeline: catalog refresh &rarr; stale check &rarr; re-analyze &rarr; workload scan. Runs inside the scan worker via arq cron.
      </p>
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
              <div>
                Last run: <span style={{ color: 'var(--text-secondary)' }}>{shortTime(schedule.last_pipeline.created_at)}</span>
                {' '}&mdash; <span style={{ color: jobStatusColor(schedule.last_pipeline.status) }}>{schedule.last_pipeline.status}</span>
                {schedule.last_pipeline.completed_at && (
                  <span> ({elapsed(schedule.last_pipeline.created_at, schedule.last_pipeline.completed_at)})</span>
                )}
              </div>
              {schedule.last_pipeline.result && (
                <div style={{ color: 'var(--text-muted)' }}>
                  {schedule.last_pipeline.result.refresh && (
                    <span>{schedule.last_pipeline.result.refresh.total_items} items synced</span>
                  )}
                  {schedule.last_pipeline.result.stale_check && (
                    <span> &middot; {schedule.last_pipeline.result.stale_check.stale} stale</span>
                  )}
                  {schedule.last_pipeline.result.analysis_enqueued !== undefined && schedule.last_pipeline.result.analysis_enqueued > 0 && (
                    <span> &middot; {schedule.last_pipeline.result.analysis_enqueued} queued for re-analysis</span>
                  )}
                  {schedule.last_pipeline.result.warnings && schedule.last_pipeline.result.warnings.length > 0 && (
                    <span style={{ color: 'var(--score-amber)' }}> &middot; {schedule.last_pipeline.result.warnings.length} warning(s)</span>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
      <Button variant="secondary" size="sm" onClick={handleRun} isDisabled={running}>
        {running ? 'Running...' : 'Run Maintenance Now'}
      </Button>
      <LogWindow
        lines={log}
        isOpen={logOpen}
        onToggle={() => setLogOpen(!logOpen)}
      />
    </div>
  )
}

// ── StatusPage ──

export function StatusPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<CatalogStatus | null>(null)
  const [infraStats, setInfraStats] = useState<InfraStats | null>(null)
  const [llmProvider, setLlmProvider] = useState<{ litemaas_enabled: boolean; litemaas_url: string | null; litemaas_models: string[]; vertex_enabled: boolean; vertex_region: string | null; vertex_models: string[]; analysis_model: string; triage_model: string; rationale_model: string; scanning_model: string } | null>(null)
  const [reportingStatus, setReportingStatus] = useState<{ configured: boolean; total: number; with_provisions: number; with_cost: number; with_sales: number; last_synced: string | null } | null>(null)

  const loadStatus = useCallback(() => {
    api.getCatalogStats().then(data => setStatus(data as CatalogStatus)).catch(() => {})
    api.getInfraStats().then(data => setInfraStats(data as InfraStats)).catch(() => {})
    api.getLlmProviderStatus().then(setLlmProvider).catch(() => {})
    api.getReportingStatus().then(setReportingStatus).catch(() => {})
  }, [])

  useEffect(() => { loadStatus() }, [loadStatus])

  const statusColor = (stale: boolean) => stale ? 'var(--score-red)' : 'var(--score-green)'

  const clickableCount = (count: number, filter: string, warnColor = 'var(--score-amber)') => (
    <span
      onClick={() => count > 0 && navigate(`/browse?content_filter=${filter}`)}
      className={count > 0 ? 'admin-stat-row-link' : undefined}
      style={{ color: count > 0 ? warnColor : 'var(--score-green)' }}
    >{count}</span>
  )

  return (
    <div className="admin-layout admin-layout--flex">
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        <button
          onClick={loadStatus}
          style={{ background: 'transparent', border: '1px solid var(--border-default)', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '12px', padding: '2px 8px', borderRadius: 'var(--radius-sm)' }}
        >&#8635; Refresh</button>
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
            <div className="admin-stat-row"><span className="admin-stat-row-label">Failures</span>{clickableCount(status.failed_count, 'scan_failures', 'var(--score-red)')}</div>
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
                <div className="admin-stat-row"><span className="admin-stat-row-label">Unmapped</span><span style={{ color: infraStats.unmapped_workloads > 0 ? 'var(--score-amber)' : 'var(--score-green)' }}>{infraStats.unmapped_workloads}</span></div>
              </>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Loading...</div>
            )}
          </div>

          <div className="admin-stat-card">
            <div className="admin-stat-card-title">LLM Provider</div>
            {llmProvider ? (
              <>
                <div className="admin-stat-row"><span className="admin-stat-row-label">LiteMaaS</span><span style={{ color: llmProvider.litemaas_enabled ? 'var(--score-green)' : 'var(--text-muted)' }}>{llmProvider.litemaas_enabled ? 'Active' : 'Off'}</span></div>
                {llmProvider.litemaas_enabled && (
                  <div className="admin-stat-row"><span className="admin-stat-row-indent">Models</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.litemaas_models.join(', ')}</span></div>
                )}
                <div className="admin-stat-row"><span className="admin-stat-row-label">Vertex AI</span><span style={{ color: llmProvider.vertex_enabled ? 'var(--score-green)' : 'var(--text-muted)' }}>{llmProvider.vertex_enabled ? (llmProvider.litemaas_enabled ? 'Fallback' : 'Active') : 'Off'}</span></div>
                {llmProvider.vertex_enabled && llmProvider.vertex_models.length > 0 && (
                  <div className="admin-stat-row"><span className="admin-stat-row-indent">Models</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.vertex_models.join(', ')}</span></div>
                )}
                <div className="admin-stat-row-divider" />
                <div className="admin-stat-row"><span className="admin-stat-row-label">Analysis</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.analysis_model}</span></div>
                <div className="admin-stat-row"><span className="admin-stat-row-label">Triage</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.triage_model}</span></div>
                <div className="admin-stat-row"><span className="admin-stat-row-label">Rationale</span><span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{llmProvider.rationale_model}</span></div>
              </>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Loading...</div>
            )}
          </div>

          <div className="admin-stat-card">
            <div className="admin-stat-card-title">Reporting Sync</div>
            {reportingStatus ? (
              reportingStatus.total > 0 ? (
                <>
                  <div className="admin-stat-row"><span className="admin-stat-row-label">Status</span><span style={{ color: 'var(--score-green)' }}>Synced</span></div>
                  <div className="admin-stat-row"><span className="admin-stat-row-label">Assets tracked</span><span className="admin-stat-row-value">{reportingStatus.total}</span></div>
                  <div className="admin-stat-row"><span className="admin-stat-row-label">With provisions</span><span className="admin-stat-row-value">{reportingStatus.with_provisions}</span></div>
                  <div className="admin-stat-row"><span className="admin-stat-row-label">With cost data</span><span className="admin-stat-row-value">{reportingStatus.with_cost}</span></div>
                  <div className="admin-stat-row"><span className="admin-stat-row-label">With sales data</span><span className="admin-stat-row-value">{reportingStatus.with_sales}</span></div>
                  <div className="admin-stat-row-divider" />
                  <div className="admin-stat-row"><span className="admin-stat-row-label">Last synced</span><span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{reportingStatus.last_synced ? new Date(reportingStatus.last_synced).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'never'}</span></div>
                </>
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>{reportingStatus.configured ? 'Not synced yet' : 'Not configured'}</div>
              )
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Loading...</div>
            )}
          </div>
        </div>
      ) : (
        <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
      )}

      <ScheduledMaintenance onStatusChange={loadStatus} />
    </div>
  )
}
