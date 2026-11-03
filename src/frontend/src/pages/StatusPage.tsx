import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { LlmProviderCard, type LlmProviderStatus } from '../components/admin/LlmProviderCard'

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
  infrastructure_workloads: number
  infrastructure_configs: number
}

// ── StatusPage ──

export function StatusPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<CatalogStatus | null>(null)
  const [infraStats, setInfraStats] = useState<InfraStats | null>(null)
  const [llmProvider, setLlmProvider] = useState<LlmProviderStatus | null>(null)
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
      role={count > 0 ? 'button' : undefined}
      tabIndex={count > 0 ? 0 : undefined}
      onClick={() => count > 0 && navigate(`/browse?content_filter=${filter}`)}
      onKeyDown={(e) => {
        if (count > 0 && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          navigate(`/browse?content_filter=${filter}`)
        }
      }}
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
        <>
        <div className="admin-section">
          <h3>Content</h3>
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

        </div>
        </div>

        <div className="admin-section">
          <h3>Infrastructure</h3>
          <div className="admin-stat-cards">
          <div className="admin-stat-card">
            <div className="admin-stat-card-title">AgnosticD v2</div>
            {infraStats ? (
              <>
                <div className="admin-stat-row"><span className="admin-stat-row-label">AgnosticD v2</span><span className="admin-stat-row-value">{infraStats.v2_items}</span></div>
                <div className="admin-stat-row"><span className="admin-stat-row-indent">With workloads</span><span className="admin-stat-row-value">{infraStats.with_workloads}</span></div>
                <div className="admin-stat-row-divider" />
                <div className="admin-stat-row"><span className="admin-stat-row-label">Infrastructure Workloads</span><span className="admin-stat-row-value">{infraStats.infrastructure_workloads}</span></div>
                <div className="admin-stat-row"><span className="admin-stat-row-label">Infrastructure Configs</span><span className="admin-stat-row-value">{infraStats.infrastructure_configs}</span></div>
              </>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Loading...</div>
            )}
          </div>

        </div>
        </div>

        <div className="admin-section">
          <h3>System</h3>
          <div className="admin-stat-cards">
          <div className="admin-stat-card">
            <div className="admin-stat-card-title">LLM Provider</div>
            {llmProvider ? (
              <LlmProviderCard status={llmProvider} />
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
        </div>
        </>
      ) : (
        <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
      )}

    </div>
  )
}
