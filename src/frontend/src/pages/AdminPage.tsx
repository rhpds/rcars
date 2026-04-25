import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { LcarsButton } from '../components/lcars'
import { LogWindow } from '../components/admin/LogWindow'

interface WorkerHealth {
  queue_depths: Record<string, number>
  active_jobs: number
  running_jobs: Array<{ id: string; job_type: string; created_at: string }>
  failed_jobs_recent: number
}

interface TokenStats {
  stats: Array<{ operation: string; model: string; calls: number; total_tokens: number }>
  recent_queries: Array<{ query_text: string; query_time: string; total_tokens: number }>
  days: number
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
}

export function AdminPage() {
  const [workerHealth, setWorkerHealth] = useState<WorkerHealth | null>(null)
  const [tokenStats, setTokenStats] = useState<TokenStats | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [actionLog, setActionLog] = useState<string[]>([])
  const [logOpen, setLogOpen] = useState(false)
  const [days, setDays] = useState(30)

  const loadData = async () => {
    const [wh, ts, jb] = await Promise.all([
      api.getWorkerHealth() as Promise<WorkerHealth>,
      api.getTokenUsage(days) as Promise<TokenStats>,
      api.listJobs(20) as Promise<{ items: Job[]; total: number }>,
    ])
    setWorkerHealth(wh)
    setTokenStats(ts)
    setJobs(jb.items)
  }

  useEffect(() => { loadData() }, [days])

  // Auto-refresh worker health every 10s
  useEffect(() => {
    const interval = setInterval(async () => {
      const wh = await api.getWorkerHealth() as WorkerHealth
      setWorkerHealth(wh)
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleAction = async (action: string, fn: () => Promise<{ job_id: string }>) => {
    setActionLog(prev => [...prev, `Starting ${action}...`])
    setLogOpen(true)
    try {
      const result = await fn()
      setActionLog(prev => [...prev, `${action} enqueued: job_id=${result.job_id}`])
      loadData()
    } catch (err) {
      setActionLog(prev => [...prev, `Error: ${err}`])
    }
  }

  return (
    <div className="admin-layout">
      {/* Worker health */}
      <div className="admin-section">
        <h3>Worker Health</h3>
        {workerHealth && (
          <table className="status-table">
            <tbody>
              <tr>
                <th>Queue</th>
                <th>Depth</th>
              </tr>
              {Object.entries(workerHealth.queue_depths).map(([queue, depth]) => (
                <tr key={queue}>
                  <td>{queue}</td>
                  <td style={{ color: depth > 0 ? '#e8a838' : '#5cb85c' }}>{depth}</td>
                </tr>
              ))}
              <tr>
                <td>Active jobs</td>
                <td>{workerHealth.active_jobs}</td>
              </tr>
              <tr>
                <td>Recent failures</td>
                <td style={{ color: workerHealth.failed_jobs_recent > 0 ? '#c9190b' : '#5cb85c' }}>
                  {workerHealth.failed_jobs_recent}
                </td>
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {/* Actions */}
      <div className="admin-section">
        <h3>Actions</h3>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <LcarsButton onClick={() => handleAction('Catalog refresh', api.refreshCatalog)}>
            Refresh Catalog
          </LcarsButton>
          <LcarsButton onClick={() => handleAction('Scan', api.startScan)}>
            Scan Unanalyzed
          </LcarsButton>
          <LcarsButton onClick={() => handleAction('Stale check', api.checkStale)}>
            Check Stale
          </LcarsButton>
          <LcarsButton onClick={() => handleAction('Rescan stale', api.rescanStale)}>
            Rescan Stale
          </LcarsButton>
        </div>
        <LogWindow lines={actionLog} isOpen={logOpen} onToggle={() => setLogOpen(!logOpen)} />
      </div>

      {/* Token usage */}
      <div className="admin-section">
        <h3>Token Usage</h3>
        <div style={{ marginBottom: '10px' }}>
          <select
            className="filter-select"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
        {tokenStats && tokenStats.stats.length > 0 && (
          <table className="status-table">
            <thead>
              <tr>
                <th>Operation</th>
                <th>Model</th>
                <th>Calls</th>
                <th>Tokens</th>
              </tr>
            </thead>
            <tbody>
              {tokenStats.stats.map((s, i) => (
                <tr key={i}>
                  <td>{s.operation}</td>
                  <td style={{ color: '#666' }}>{s.model}</td>
                  <td>{s.calls}</td>
                  <td>{s.total_tokens?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Recent jobs */}
      <div className="admin-section">
        <h3>Recent Jobs</h3>
        {jobs.length > 0 ? (
          <table className="status-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Status</th>
                <th>Queue</th>
                <th>Created</th>
                <th>By</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.id}>
                  <td>{job.job_type}</td>
                  <td style={{
                    color: job.status === 'complete' ? '#5cb85c'
                      : job.status === 'failed' ? '#c9190b'
                      : job.status === 'running' ? '#e8a838'
                      : '#666'
                  }}>
                    {job.status}
                  </td>
                  <td style={{ color: '#666' }}>{job.queue}</td>
                  <td style={{ color: '#666', fontSize: '13px' }}>
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                  <td style={{ color: '#666', fontSize: '13px' }}>{job.created_by || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color: '#666' }}>No recent jobs.</div>
        )}
      </div>
    </div>
  )
}
