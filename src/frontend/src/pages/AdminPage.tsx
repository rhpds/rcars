import { useState, useEffect } from 'react'
import { api } from '../services/api'

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

interface QuerySession {
  session_id: string
  started_at: string
  turn_count: number
  turns: Array<{
    query_text: string | null
    overall_assessment: string | null
    results_json: unknown[] | null
    chosen_ci_name: string | null
    opted_out: boolean
    created_at: string
  }>
}

export function AdminQueriesPage() {
  const [sessions, setSessions] = useState<QuerySession[]>([])
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getQueryHistory(50).then(data => {
      setSessions((data as { items: QuerySession[] }).items)
      setLoading(false)
    })
  }, [])

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
              const firstQuery = session.turns[0]?.query_text
              const isExpanded = expandedSessions.has(session.session_id)
              return (
                <div key={session.session_id} style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)' }}>
                  <div
                    style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', gap: '12px', alignItems: 'baseline' }}
                    onClick={() => setExpandedSessions(prev => {
                      const next = new Set(prev)
                      if (next.has(session.session_id)) next.delete(session.session_id)
                      else next.add(session.session_id)
                      return next
                    })}
                  >
                    <span style={{ color: 'var(--text-muted)', fontSize: '12px', flexShrink: 0, whiteSpace: 'nowrap' }}>
                      {isExpanded ? '▾' : '▸'} {shortTime(session.started_at)}
                    </span>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {firstQuery || '(empty query)'}
                    </span>
                    {session.turns.some(t => t.chosen_ci_name) && (
                      <span style={{ color: 'var(--score-green)', fontSize: '11px', flexShrink: 0 }}>has selection</span>
                    )}
                  </div>
                  {isExpanded && session.turns.map((turn, ti) => (
                    <div key={ti} style={{ padding: '10px 14px 14px', borderTop: '1px solid var(--border-default)' }}>
                      {turn.opted_out ? (
                        <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '13px' }}>Query redacted (user opted out)</div>
                      ) : (
                        <>
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
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
