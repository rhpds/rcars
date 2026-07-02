import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'

// ── Interfaces ──

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

// ── RecentJobsPage ──

export function RecentJobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])

  const loadJobs = useCallback(async () => {
    const jb = await api.listJobs(50) as { items: Job[]; total: number }
    const statusOrder: Record<string, number> = { running: 0, queued: 1, failed: 2, complete: 3 }
    setJobs(jb.items.sort((a, b) => (statusOrder[a.status] ?? 9) - (statusOrder[b.status] ?? 9)))
  }, [])

  useEffect(() => {
    loadJobs()
    const interval = setInterval(loadJobs, 10000)
    return () => clearInterval(interval)
  }, [loadJobs])

  const jobStatusColor = (s: string) =>
    s === 'complete' ? 'var(--score-green)'
      : s === 'failed' ? 'var(--score-red)'
      : s === 'running' ? 'var(--score-amber)' : 'var(--text-muted)'

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
    <div className="admin-layout admin-layout--wide">
      <div className="admin-section">
        <h3>Recent Jobs</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>Auto-refreshes every 10 seconds.</p>
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
                    <td style={{ color: 'var(--text-muted)', fontSize: '12px', whiteSpace: 'nowrap' }}>{shortTime(job.created_at)}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '12px', whiteSpace: 'nowrap' }}>{job.completed_at ? shortTime(job.completed_at) : '-'}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '12px', whiteSpace: 'nowrap' }}>{elapsed(job.created_at, job.completed_at)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ color: 'var(--text-muted)' }}>No recent jobs.</div>
        )}
      </div>
    </div>
  )
}
