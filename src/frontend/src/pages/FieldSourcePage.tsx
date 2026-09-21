import { useState, useEffect, useCallback, Fragment } from 'react'
import { api, FieldSourceData } from '../services/api'

type CatalogFilter = 'all' | 'ocp' | 'rhel'

const formatDate = (iso: string) => new Date(iso).toLocaleDateString()

const repoDisplayName = (url: string) => {
  try { return new URL(url).pathname.replace(/^\//, '').replace(/\.git$/, '') }
  catch { return url }
}

export function FieldSourcePage() {
  const [data, setData] = useState<FieldSourceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<CatalogFilter>('all')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await api.getFieldSource(filter)
      setData(resp)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => { fetchData() }, [fetchData])

  const toggleExpand = (key: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  if (loading) return <div className="ca-loading">Loading…</div>
  if (error) return <div className="ca-error">{error}</div>
  if (!data) return null

  return (
    <div className="ca-performance-page">
      <div className="ca-page-header">
        <h1>Field Source Content</h1>
        <div className="ca-filters">
          <select
            value={filter}
            onChange={e => setFilter(e.target.value as CatalogFilter)}
            className="ca-filter-select"
          >
            <option value="all">All</option>
            <option value="ocp">OCP</option>
            <option value="rhel">RHEL</option>
          </select>
        </div>
      </div>

      <div className="ca-stats-row">
        <span><strong>{data.total_repos}</strong> repos</span>
        <span className="ca-stats-sep">·</span>
        <span><strong>{data.total_provisions}</strong> total provisions</span>
      </div>

      <table className="ca-table">
        <thead>
          <tr>
            <th style={{ width: '2rem' }}></th>
            <th>Repository</th>
            <th>Ref</th>
            <th>Type</th>
            <th>Provisions</th>
            <th>First Used</th>
            <th>Last Used</th>
          </tr>
        </thead>
        <tbody>
          {data.repos.map(repo => {
            const key = `${repo.git_repo}|${repo.git_ref}|${repo.catalog_item}`
            const isExpanded = expanded.has(key)
            return (
              <Fragment key={key}>
                <tr className="ca-row-clickable" onClick={() => toggleExpand(key)}>
                  <td aria-expanded={isExpanded} aria-label="Toggle details">{isExpanded ? '▾' : '▸'}</td>
                  <td>
                    <a href={repo.git_repo} target="_blank" rel="noreferrer"
                       onClick={e => e.stopPropagation()}>
                      {repoDisplayName(repo.git_repo)}
                    </a>
                  </td>
                  <td><code>{repo.git_ref ?? '—'}</code></td>
                  <td>
                    <span className={`ca-badge ca-badge--${repo.catalog_item}`}>
                      {repo.catalog_item.toUpperCase()}
                    </span>
                  </td>
                  <td>{repo.provision_count}</td>
                  <td>{formatDate(repo.first_seen)}</td>
                  <td>{formatDate(repo.last_seen)}</td>
                </tr>
                {isExpanded && (
                  <tr className="ca-detail-row">
                    <td colSpan={7}>
                      <table className="ca-detail-table">
                        <thead>
                          <tr><th>Provisioned</th><th>Retired</th><th>Duration</th></tr>
                        </thead>
                        <tbody>
                          {repo.provisions.map((p, i) => {
                            const duration = p.retired_at
                              ? Math.round((new Date(p.retired_at).getTime() - new Date(p.provisioned_at).getTime()) / 86400000)
                              : null
                            return (
                              <tr key={i}>
                                <td>{formatDate(p.provisioned_at)}</td>
                                <td>{p.retired_at ? formatDate(p.retired_at) : 'Active'}</td>
                                <td>{duration !== null ? `${duration}d` : '—'}</td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>

      {data.repos.length === 0 && (
        <div className="ca-empty">No field source repos found for the selected filter.</div>
      )}
    </div>
  )
}

export default FieldSourcePage
