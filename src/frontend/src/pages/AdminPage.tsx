import { useState, useEffect } from 'react'
import { api } from '../services/api'
import type { RoleAssignment } from '../services/api'

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
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
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
                  <td style={{ color: 'var(--text-muted)' }}>{s.model}</td>
                  <td style={{ color: s.provider === 'litemaas' ? 'var(--score-green)' : 'var(--text-muted)' }}>{s.provider}</td>
                  <td>{s.calls}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{s.input_tokens?.toLocaleString()}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{s.output_tokens?.toLocaleString()}</td>
                  <td>{s.total_tokens?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color: 'var(--text-muted)' }}>No token usage data for this period.</div>
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
                    <td style={{ color: 'var(--text-muted)', fontSize: '12px', whiteSpace: 'nowrap' }}>{shortTime}</td>
                    <td style={{ fontSize: '13px', maxWidth: '500px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {displayQuery}
                    </td>
                    <td style={{ textAlign: 'right', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{triage.toLocaleString()}</td>
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

interface QuerySessionSummary {
  session_id: string
  started_at: string
  query_text: string | null
  chosen_ci_name: string | null
}

interface SessionTurn {
  query_text: string | null
  overall_assessment: string | null
  results_json: unknown[] | null
  chosen_ci_name: string | null
  created_at: string
}

export function AdminQueriesPage() {
  const [sessions, setSessions] = useState<QuerySessionSummary[]>([])
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set())
  const [sessionDetails, setSessionDetails] = useState<Record<string, SessionTurn[]>>({})
  const [loadingDetails, setLoadingDetails] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getQueryHistory(50).then(data => {
      setSessions((data as { items: QuerySessionSummary[] }).items)
    }).catch(() => {
      setSessions([])
    }).finally(() => {
      setLoading(false)
    })
  }, [])

  const toggleSession = (sessionId: string) => {
    const wasExpanded = expandedSessions.has(sessionId)
    setExpandedSessions(prev => {
      const next = new Set(prev)
      if (wasExpanded) next.delete(sessionId)
      else next.add(sessionId)
      return next
    })
    if (wasExpanded) return
    if (sessionDetails[sessionId] || loadingDetails.has(sessionId)) return
    setLoadingDetails(ld => new Set(ld).add(sessionId))
    api.getQuerySessionDetail(sessionId)
      .then(data => {
        const detail = data as { session_id: string; turns: SessionTurn[] }
        setSessionDetails(prev => ({ ...prev, [sessionId]: detail.turns }))
      })
      .catch(() => {
        setSessionDetails(prev => ({ ...prev, [sessionId]: [] }))
      })
      .finally(() => {
        setLoadingDetails(ld => { const next = new Set(ld); next.delete(sessionId); return next })
      })
  }

  const shortTime = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  const tierColor = (tier: string) => {
    if (tier === 'green') return 'var(--score-green)'
    if (tier === 'yellow') return 'var(--score-amber)'
    return 'var(--text-muted)'
  }

  return (
    <div className="admin-layout admin-layout--wide">
      <div className="admin-section">
        <h3>Query History</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
          Advisor queries and recommendations. Click to expand details.
        </p>

        {loading ? (
          <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
        ) : sessions.length === 0 ? (
          <div style={{ color: 'var(--text-muted)' }}>No queries recorded yet.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {sessions.map(session => {
              const isExpanded = expandedSessions.has(session.session_id)
              const turns = sessionDetails[session.session_id]
              const isLoadingDetail = loadingDetails.has(session.session_id)
              return (
                <div key={session.session_id} style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)' }}>
                  <div
                    style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', gap: '12px', alignItems: 'baseline' }}
                    onClick={() => toggleSession(session.session_id)}
                  >
                    <span style={{ color: 'var(--text-muted)', fontSize: '12px', flexShrink: 0, whiteSpace: 'nowrap' }}>
                      {isExpanded ? '▾' : '▸'} {shortTime(session.started_at)}
                    </span>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {session.query_text || '(empty query)'}
                    </span>
                    {session.chosen_ci_name && (
                      <span style={{ color: 'var(--score-green)', fontSize: '11px', flexShrink: 0 }}>has selection</span>
                    )}
                  </div>
                  {isExpanded && (
                    isLoadingDetail ? (
                      <div style={{ padding: '10px 14px', borderTop: '1px solid var(--border-default)', color: 'var(--text-muted)', fontSize: '13px' }}>Loading details...</div>
                    ) : turns?.map((turn, ti) => (
                      <div key={ti} style={{ padding: '10px 14px 14px', borderTop: '1px solid var(--border-default)' }}>
                            {turn.query_text && (
                              <div style={{ color: 'var(--score-amber)', fontSize: '13px', marginBottom: '8px', fontWeight: 500 }}>
                                {turn.query_text}
                              </div>
                            )}
                            {turn.overall_assessment && (
                              <div style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '10px', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
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
                                    <span style={{ color: 'var(--text-secondary)' }}>{r.display_name || r.ci_name}</span>
                                    {r.stage && r.stage !== 'prod' && (
                                      <span style={{ color: 'var(--text-muted)', fontSize: '10px', border: '1px solid var(--border-default)', borderRadius: '3px', padding: '0 4px' }}>
                                        {r.stage}
                                      </span>
                                    )}
                                    {turn.chosen_ci_name === r.ci_name && (
                                      <span style={{ color: 'var(--score-green)', fontSize: '10px' }}>SELECTED</span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                      </div>
                    ))
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Role Assignments Page ──

export function AdminRolesPage() {
  const [assignments, setAssignments] = useState<RoleAssignment[]>([])
  const [loading, setLoading] = useState(true)
  const [type, setType] = useState<'user' | 'group'>('group')
  const [value, setValue] = useState('')
  const [role, setRole] = useState<'curator' | 'admin'>('curator')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState('')

  const load = () => {
    setLoading(true)
    api.getRoleAssignments()
      .then(data => setAssignments(data.assignments))
      .catch(() => setAssignments([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleAdd = async () => {
    if (!value.trim()) return
    setAdding(true)
    setAddError('')
    try {
      await api.addRoleAssignment(type, value.trim(), role)
      setValue('')
      load()
    } catch (e: unknown) {
      const status = (e as { status?: number })?.status
      setAddError(status === 409 ? `A ${type} entry for '${value.trim()}' already exists.` : 'Failed to add assignment.')
    } finally {
      setAdding(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.deleteRoleAssignment(id)
      load()
    } catch {
      // ignore — reload will reflect actual state
    }
  }

  const configEntries = assignments.filter(a => a.source === 'config')
  const dbEntries = assignments.filter(a => a.source === 'db')

  const shortTime = (iso: string) =>
    new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })

  const roleLabel = (r: string) => r.charAt(0).toUpperCase() + r.slice(1)
  const typeLabel = (t: string) => t === 'user' ? 'User' : 'Group'

  return (
    <div className="admin-layout admin-layout--wide">
      {configEntries.length > 0 && (
        <div className="admin-section">
          <h3>From Configuration</h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
            Set via environment variables at deploy time. Manage in Ansible vars to change.
          </p>
          <table className="status-table">
            <thead>
              <tr><th>Type</th><th>Value</th><th>Role</th><th></th></tr>
            </thead>
            <tbody>
              {configEntries.map((a, i) => (
                <tr key={i}>
                  <td style={{ color: 'var(--text-muted)' }}>{typeLabel(a.type)}</td>
                  <td>{a.value}</td>
                  <td>{roleLabel(a.role)}</td>
                  <td>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', border: '1px solid var(--border-default)', borderRadius: '3px', padding: '1px 5px' }}>
                      config
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="admin-section">
        <h3>Managed Access</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
          Add users or OpenShift group names. Group membership is resolved live at login.
        </p>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap' }}>
          <select
            className="filter-select"
            value={type}
            onChange={e => setType(e.target.value as 'user' | 'group')}
            style={{ width: 'auto' }}
          >
            <option value="group">Group</option>
            <option value="user">User</option>
          </select>
          <input
            type="text"
            className="filter-select"
            placeholder={type === 'group' ? 'OpenShift group name' : 'Username'}
            value={value}
            onChange={e => { setValue(e.target.value); setAddError('') }}
            onKeyDown={e => { if (e.key === 'Enter') handleAdd() }}
            style={{ minWidth: '220px' }}
          />
          <select
            className="filter-select"
            value={role}
            onChange={e => setRole(e.target.value as 'curator' | 'admin')}
            style={{ width: 'auto' }}
          >
            <option value="curator">Curator</option>
            <option value="admin">Admin</option>
          </select>
          <button
            className="action-btn action-btn--primary"
            onClick={handleAdd}
            disabled={adding || !value.trim()}
          >
            {adding ? 'Adding…' : 'Add'}
          </button>
          {addError && (
            <span style={{ fontSize: '12px', color: 'var(--score-red, #c9190b)' }}>{addError}</span>
          )}
        </div>

        {loading ? (
          <div style={{ color: 'var(--text-muted)' }}>Loading…</div>
        ) : dbEntries.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No managed assignments yet.</div>
        ) : (
          <table className="status-table">
            <thead>
              <tr><th>Type</th><th>Value</th><th>Role</th><th>Added by</th><th>Added</th><th></th></tr>
            </thead>
            <tbody>
              {dbEntries.map(a => (
                <tr key={a.id}>
                  <td style={{ color: 'var(--text-muted)' }}>{typeLabel(a.type)}</td>
                  <td>{a.value}</td>
                  <td>{roleLabel(a.role)}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>{a.added_by}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '12px', whiteSpace: 'nowrap' }}>
                    {a.added_at ? shortTime(a.added_at) : '—'}
                  </td>
                  <td>
                    <button
                      className="action-btn"
                      onClick={() => handleDelete(a.id!)}
                      style={{ padding: '2px 8px', fontSize: '12px' }}
                      title="Remove"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
