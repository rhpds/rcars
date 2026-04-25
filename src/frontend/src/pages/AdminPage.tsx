import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { LcarsButton } from '../components/lcars'
import { LogWindow } from '../components/admin/LogWindow'

type AdminTab = 'catalog' | 'workers' | 'tokens'

interface CatalogStatus {
  last_refresh: string
  catalog_stale: boolean
  catalog_date: string
  analysis_stale: boolean
  analysis_date: string
  unanalyzed: number
  stale_count: number
  failed_count: number
}

interface WorkerHealth {
  queue_depths: Record<string, number>
  active_jobs: number
  running_jobs: Array<{ id: string; job_type: string; created_at: string }>
  failed_jobs_recent: number
}

interface TokenStats {
  stats: Array<{ operation: string; model: string; calls: number; input_tokens: number; output_tokens: number; total_tokens: number }>
  recent_queries: Array<{ query_text: string; query_time: string; total_tokens: number; triage_input: number; triage_output: number; rationale_input: number; rationale_output: number }>
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
  const [activeTab, setActiveTab] = useState<AdminTab>('catalog')

  const tabStyle = (tab: AdminTab) => ({
    background: activeTab === tab ? '#1a3a5a' : 'transparent',
    border: `1px solid ${activeTab === tab ? '#73bcf7' : '#333'}`,
    color: activeTab === tab ? '#73bcf7' : '#666',
    padding: '8px 20px',
    borderRadius: '6px',
    cursor: 'pointer' as const,
    fontSize: '15px',
  })

  return (
    <div className="admin-layout">
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        <button style={tabStyle('catalog')} onClick={() => setActiveTab('catalog')}>Catalog Status</button>
        <button style={tabStyle('workers')} onClick={() => setActiveTab('workers')}>Workers</button>
        <button style={tabStyle('tokens')} onClick={() => setActiveTab('tokens')}>Token Usage</button>
      </div>

      {activeTab === 'catalog' && <CatalogTab />}
      {activeTab === 'workers' && <WorkersTab />}
      {activeTab === 'tokens' && <TokensTab />}
    </div>
  )
}

function CatalogTab() {
  const [status, setStatus] = useState<CatalogStatus | null>(null)
  const [actionLog, setActionLog] = useState<string[]>([])
  const [logOpen, setLogOpen] = useState(false)

  useEffect(() => {
    api.getCatalogStats().then(data => setStatus(data as CatalogStatus))
  }, [])

  const handleAction = async (label: string, fn: () => Promise<{ job_id: string }>) => {
    setActionLog(prev => [...prev, `Starting ${label}...`])
    setLogOpen(true)
    try {
      const result = await fn()
      setActionLog(prev => [...prev, `${label} enqueued: job_id=${result.job_id}`])
      api.getCatalogStats().then(data => setStatus(data as CatalogStatus))
    } catch (err) {
      setActionLog(prev => [...prev, `Error: ${err}`])
    }
  }

  const statusColor = (stale: boolean) => stale ? '#c9190b' : '#5cb85c'
  const statusLabel = (stale: boolean) => stale ? 'STALE' : 'CURRENT'

  return (
    <>
      <div className="admin-section">
        <h3>Catalog & Analysis Status</h3>
        {status ? (
          <table className="status-table">
            <tbody>
              <tr>
                <td>Catalog</td>
                <td>{status.catalog_date}</td>
                <td style={{ color: statusColor(status.catalog_stale), fontWeight: 600 }}>
                  {statusLabel(status.catalog_stale)}
                </td>
              </tr>
              <tr>
                <td>Analysis</td>
                <td>{status.analysis_date}</td>
                <td style={{ color: statusColor(status.analysis_stale), fontWeight: 600 }}>
                  {statusLabel(status.analysis_stale)}
                </td>
              </tr>
              <tr>
                <td>Unanalyzed items</td>
                <td colSpan={2}>{status.unanalyzed}</td>
              </tr>
              <tr>
                <td>Stale items</td>
                <td colSpan={2} style={{ color: status.stale_count > 0 ? '#e8a838' : '#5cb85c' }}>
                  {status.stale_count}
                </td>
              </tr>
              <tr>
                <td>Scan failures</td>
                <td colSpan={2} style={{ color: status.failed_count > 0 ? '#c9190b' : '#5cb85c' }}>
                  {status.failed_count}
                </td>
              </tr>
            </tbody>
          </table>
        ) : (
          <div style={{ color: '#666' }}>Loading...</div>
        )}
      </div>

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
    </>
  )
}

function WorkersTab() {
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
      const wh = await api.getWorkerHealth() as WorkerHealth
      setHealth(wh)
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const jobStatusColor = (status: string) => {
    if (status === 'complete') return '#5cb85c'
    if (status === 'failed') return '#c9190b'
    if (status === 'running') return '#e8a838'
    return '#666'
  }

  return (
    <>
      <div className="admin-section">
        <h3>Queue Depths</h3>
        {health ? (
          <table className="status-table">
            <thead>
              <tr><th>Queue</th><th>Depth</th><th>Status</th></tr>
            </thead>
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
          <div style={{ marginTop: '12px', fontSize: '14px', color: '#aaa' }}>
            Active jobs: {health.active_jobs} · Recent failures: {' '}
            <span style={{ color: health.failed_jobs_recent > 0 ? '#c9190b' : '#5cb85c' }}>
              {health.failed_jobs_recent}
            </span>
          </div>
        )}
      </div>

      <div className="admin-section">
        <h3>Recent Jobs</h3>
        {jobs.length > 0 ? (
          <table className="status-table">
            <thead>
              <tr><th>Type</th><th>Status</th><th>Queue</th><th>Created</th><th>By</th></tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.id}>
                  <td>{job.job_type}</td>
                  <td style={{ color: jobStatusColor(job.status) }}>{job.status}</td>
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
    </>
  )
}

function TokensTab() {
  const [stats, setStats] = useState<TokenStats | null>(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    api.getTokenUsage(days).then(data => setStats(data as TokenStats))
  }, [days])

  return (
    <>
      <div className="admin-section">
        <h3>Token Usage</h3>
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
            <thead>
              <tr><th>Operation</th><th>Model</th><th>Calls</th><th>Input</th><th>Output</th><th>Total</th></tr>
            </thead>
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
            <thead>
              <tr><th>Query</th><th>Time</th><th>Triage</th><th>Rationale</th><th>Total</th></tr>
            </thead>
            <tbody>
              {stats.recent_queries.map((q, i) => (
                <tr key={i}>
                  <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {q.query_text}
                  </td>
                  <td style={{ color: '#666', fontSize: '13px' }}>
                    {new Date(q.query_time).toLocaleString()}
                  </td>
                  <td style={{ color: '#666' }}>
                    {(q.triage_input + q.triage_output).toLocaleString()}
                  </td>
                  <td style={{ color: '#666' }}>
                    {(q.rationale_input + q.rationale_output).toLocaleString()}
                  </td>
                  <td>{q.total_tokens?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
