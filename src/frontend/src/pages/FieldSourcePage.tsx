import { useState, useEffect, useCallback, Fragment, useRef } from 'react'
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
  const [search, setSearch] = useState('')
  const [searchDisplay, setSearchDisplay] = useState('')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  const handleSearchChange = (value: string) => {
    setSearchDisplay(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => setSearch(value), 300)
  }

  const filtered = data?.repos.filter(r => {
    if (!search) return true
    const q = search.toLowerCase()
    return repoDisplayName(r.git_repo).toLowerCase().includes(q)
      || (r.git_ref?.toLowerCase().includes(q) ?? false)
  }) ?? []

  const ocpCount = data?.repos.filter(r => r.catalog_item === 'ocp').length ?? 0
  const rhelCount = data?.repos.filter(r => r.catalog_item === 'rhel').length ?? 0
  const totalProvisions = filtered.reduce((s, r) => s + r.provision_count, 0)

  if (loading) return <div className="ca-loading">Loading…</div>
  if (error) return <div className="ca-error">{error}</div>
  if (!data) return null

  return (
    <div className="browse-layout">
      <div className="browse-content">
        <div className="browse-filter-sidebar">
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Type</div>
            <div className="ret-filter-group">
              <button onClick={() => setFilter('all')}
                className={`ret-filter-group__btn${filter === 'all' ? ' active' : ''}`}>
                All ({data.total_repos})
              </button>
              <button onClick={() => setFilter('ocp')}
                className={`ret-filter-group__btn${filter === 'ocp' ? ' active' : ''}`}>
                <span className="ret-filter-group__dot" style={{ background: 'var(--score-red)' }} />
                OCP ({ocpCount})
              </button>
              <button onClick={() => setFilter('rhel')}
                className={`ret-filter-group__btn${filter === 'rhel' ? ' active' : ''}`}>
                <span className="ret-filter-group__dot" style={{ background: 'var(--text-link)' }} />
                RHEL ({rhelCount})
              </button>
            </div>
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'auto', padding: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h3 style={{ margin: 0 }}>Field Source Content</h3>
          </div>

          <div className="ca-stats-grid">
            <div className="ret-stat-card ret-stat-card--blue">
              <div className="ret-stat-label">Repos</div>
              <div className="ret-stat-value ca-color-blue">{filtered.length}</div>
            </div>
            <div className="ret-stat-card">
              <div className="ret-stat-label">OCP Repos</div>
              <div className="ret-stat-value">{ocpCount}</div>
            </div>
            <div className="ret-stat-card">
              <div className="ret-stat-label">RHEL Repos</div>
              <div className="ret-stat-value">{rhelCount}</div>
            </div>
            <div className="ret-stat-card">
              <div className="ret-stat-label">Total Provisions</div>
              <div className="ret-stat-value">{totalProvisions}</div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
            <input
              type="text" placeholder="Search by name..."
              value={searchDisplay} onChange={e => handleSearchChange(e.target.value)}
              className="ca-search"
            />
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
              {filtered.length} of {data.total_repos} repos
            </span>
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
              {filtered.map(repo => {
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
                          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
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
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>

          {filtered.length === 0 && (
            <div className="ca-empty">No field source repos found for the selected filter.</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FieldSourcePage
