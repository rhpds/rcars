import { useState, useEffect, useCallback, Fragment, useRef } from 'react'
import { api, FieldSourceData, FieldSourceRepo as FSRepo } from '../services/api'

type Tab = 'ocp' | 'rhel'
type SortField = 'repository' | 'ref' | 'provisions' | 'cnv' | 'aws' | 'sno' | 'multinode' | 'first_seen' | 'last_seen'

const formatDate = (iso: string) => new Date(iso).toLocaleDateString()

const repoDisplayName = (url: string) => {
  if (!url) return 'No automation repo provided'
  try { return new URL(url).pathname.replace(/^\//, '').replace(/\.git$/, '') }
  catch { return url }
}

export function FieldSourcePage() {
  const [data, setData] = useState<FieldSourceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('ocp')
  const [search, setSearch] = useState('')
  const [searchDisplay, setSearchDisplay] = useState('')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [sortBy, setSortBy] = useState<SortField>('provisions')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await api.getFieldSource(tab))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [tab])

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

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(field)
      setSortDir('desc')
    }
  }

  const sortVal = (r: FSRepo, f: SortField): string | number => {
    switch (f) {
      case 'repository': return repoDisplayName(r.git_repo).toLowerCase()
      case 'ref': return (r.git_ref ?? '').toLowerCase()
      case 'provisions': return r.provision_count
      case 'cnv': return r.cnv_count
      case 'aws': return r.aws_count
      case 'sno': return r.sno_count
      case 'multinode': return r.multinode_count
      case 'first_seen': return r.first_seen
      case 'last_seen': return r.last_seen
    }
  }

  const sorted = [...filtered].sort((a, b) => {
    const av = sortVal(a, sortBy), bv = sortVal(b, sortBy)
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortDir === 'desc' ? -cmp : cmp
  })

  const arrow = (field: SortField) => sortBy === field ? (sortDir === 'desc' ? ' ↓' : ' ↑') : ''

  const totalProvisions = filtered.reduce((s, r) => s + r.provision_count, 0)
  const totalCnv = filtered.reduce((s, r) => s + r.cnv_count, 0)
  const totalAws = filtered.reduce((s, r) => s + r.aws_count, 0)

  if (loading) return <div className="ca-loading">Loading…</div>
  if (error) return <div className="ca-error">{error}</div>
  if (!data) return null

  const ocpColumns = (
    <tr>
      <th style={{ width: '2rem' }}></th>
      <th className="clickable" onClick={() => toggleSort('repository')}>Repository{arrow('repository')}</th>
      <th className="clickable" style={{ width: '9rem' }} onClick={() => toggleSort('ref')}>Ref{arrow('ref')}</th>
      <th className="clickable num" style={{ width: '4.5rem' }} onClick={() => toggleSort('provisions')}>Total{arrow('provisions')}</th>
      <th className="clickable num" style={{ width: '4rem' }} onClick={() => toggleSort('cnv')}>CNV{arrow('cnv')}</th>
      <th className="clickable num" style={{ width: '4rem' }} onClick={() => toggleSort('aws')}>AWS{arrow('aws')}</th>
      <th className="clickable num" style={{ width: '4rem' }} onClick={() => toggleSort('sno')}>SNO{arrow('sno')}</th>
      <th className="clickable num" style={{ width: '5rem' }} onClick={() => toggleSort('multinode')}>Multi{arrow('multinode')}</th>
      <th className="clickable" style={{ width: '7rem' }} onClick={() => toggleSort('first_seen')}>First Used{arrow('first_seen')}</th>
      <th className="clickable" style={{ width: '7rem' }} onClick={() => toggleSort('last_seen')}>Last Used{arrow('last_seen')}</th>
    </tr>
  )

  const rhelColumns = (
    <tr>
      <th style={{ width: '2rem' }}></th>
      <th className="clickable" onClick={() => toggleSort('repository')}>Repository{arrow('repository')}</th>
      <th className="clickable" style={{ width: '9rem' }} onClick={() => toggleSort('ref')}>Ref{arrow('ref')}</th>
      <th className="clickable num" style={{ width: '4.5rem' }} onClick={() => toggleSort('provisions')}>Total{arrow('provisions')}</th>
      <th className="clickable num" style={{ width: '5rem' }} onClick={() => toggleSort('sno')}>Single{arrow('sno')}</th>
      <th className="clickable num" style={{ width: '5rem' }} onClick={() => toggleSort('multinode')}>Multi{arrow('multinode')}</th>
      <th className="clickable" style={{ width: '7rem' }} onClick={() => toggleSort('first_seen')}>First Used{arrow('first_seen')}</th>
      <th className="clickable" style={{ width: '7rem' }} onClick={() => toggleSort('last_seen')}>Last Used{arrow('last_seen')}</th>
    </tr>
  )

  const colCount = tab === 'ocp' ? 10 : 8

  const renderRow = (repo: FSRepo) => {
    const key = `${repo.git_repo}|${repo.git_ref}|${repo.catalog_item}`
    const isExpanded = expanded.has(key)
    return (
      <Fragment key={key}>
        <tr className="ca-row-clickable" onClick={() => toggleExpand(key)}>
          <td aria-expanded={isExpanded} aria-label="Toggle details">{isExpanded ? '▾' : '▸'}</td>
          <td>
            {repo.git_repo && /^https?:\/\//i.test(repo.git_repo) ? (
              <a href={repo.git_repo} target="_blank" rel="noreferrer"
                 onClick={e => e.stopPropagation()}>
                {repoDisplayName(repo.git_repo)}
              </a>
            ) : (
              <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                {repoDisplayName(repo.git_repo)}
              </span>
            )}
          </td>
          <td><code>{repo.git_ref ?? '—'}</code></td>
          <td style={{ textAlign: 'right' }}>{repo.provision_count}</td>
          {tab === 'ocp' && <>
            <td style={{ textAlign: 'right' }}>{repo.cnv_count}</td>
            <td style={{ textAlign: 'right' }}>{repo.aws_count}</td>
          </>}
          <td style={{ textAlign: 'right' }}>{repo.sno_count}</td>
          <td style={{ textAlign: 'right' }}>{repo.multinode_count}</td>
          <td>{formatDate(repo.first_seen)}</td>
          <td>{formatDate(repo.last_seen)}</td>
        </tr>
        {isExpanded && (
          <tr className="ca-detail-row">
            <td colSpan={colCount}>
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                <table className="ca-detail-table">
                  <thead>
                    <tr>
                      <th>Provisioned</th><th>Retired</th><th>Duration</th>
                      {tab === 'ocp' && <><th>Provider</th><th>Size</th></>}
                      {tab === 'rhel' && <><th>Nodes</th><th>Size</th></>}
                    </tr>
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
                          {tab === 'ocp' && <>
                            <td>{p.cloud_provider?.toUpperCase() ?? '—'}</td>
                            <td>{p.cluster_size ?? '—'}</td>
                          </>}
                          {tab === 'rhel' && <>
                            <td>{p.cluster_size ?? '—'}</td>
                            <td>{p.node_size ?? '—'}</td>
                          </>}
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
  }

  return (
    <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h3 style={{ margin: 0 }}>Field Source Content</h3>
      </div>

      <div className="ca-stats-grid">
        <div className="ret-stat-card ret-stat-card--blue">
          <div className="ret-stat-label">Repos</div>
          <div className="ret-stat-value ca-color-blue">{filtered.length}</div>
        </div>
        <div className="ret-stat-card">
          <div className="ret-stat-label">Total Provisions</div>
          <div className="ret-stat-value">{totalProvisions}</div>
        </div>
        <div className="ret-stat-card">
          <div className="ret-stat-label">CNV Provisions</div>
          <div className="ret-stat-value">{totalCnv}</div>
        </div>
        <div className="ret-stat-card">
          <div className="ret-stat-label">AWS Provisions</div>
          <div className="ret-stat-value">{totalAws}</div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', maxWidth: '70rem', marginBottom: '8px' }}>
        <input
          type="text" placeholder="Search by name..."
          value={searchDisplay} onChange={e => handleSearchChange(e.target.value)}
          className="ca-search"
          style={{ flex: 1 }}
        />
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          {filtered.length} of {data.total_repos} repos
        </span>
      </div>

      <div style={{ display: 'flex', gap: '0', borderBottom: '2px solid var(--border-subtle)', marginBottom: '8px' }}>
        {(['ocp', 'rhel'] as Tab[]).map(t => (
          <button key={t} onClick={() => { setTab(t); setExpanded(new Set()) }}
            style={{
              padding: '6px 16px', cursor: 'pointer', fontWeight: 600, fontSize: '13px',
              background: 'none', border: 'none',
              borderBottom: tab === t ? '2px solid var(--text-link)' : '2px solid transparent',
              color: tab === t ? 'var(--text-link)' : 'var(--text-secondary)',
              marginBottom: '-2px',
            }}>
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      <table className="ca-table" style={{ maxWidth: '70rem' }}>
        <thead>{tab === 'ocp' ? ocpColumns : rhelColumns}</thead>
        <tbody>{sorted.map(renderRow)}</tbody>
      </table>

      {filtered.length === 0 && (
        <div className="ca-empty">No field source repos found.</div>
      )}
    </div>
  )
}

export default FieldSourcePage
