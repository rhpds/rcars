import { useState, useEffect, useRef } from 'react'
import { api } from '../services/api'
import { RecCard } from '../components/advisor/RecCard'
import { StreamCandidate } from '../hooks/useJobStream'

interface SessionSummary {
  session_id: string
  started_at: string
  turns: number
  first_query?: string
}

interface SessionTurn {
  query_text: string | null
  overall_assessment: string | null
  results_json: StreamCandidate[] | null
  chosen_ci_name: string | null
  envelope_json?: { intent: string; scope_echo: string; answer: string } | null
}

interface SessionDetail {
  session_id: string
  turns: SessionTurn[]
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '...' : s
}

function shortTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function HistoryPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<SessionDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const latestRequestRef = useRef<string | null>(null)

  useEffect(() => {
    api.listSessions().then(async (data) => {
      const items = (data.items as SessionSummary[]).slice(0, 50)
      const enriched = await Promise.all(items.map(async (s) => {
        try {
          const d = await api.getSession(s.session_id) as { turns: Array<{ query_text: string | null }> }
          return { ...s, first_query: d.turns[0]?.query_text || undefined }
        } catch { return s }
      }))
      setSessions(enriched)
    }).finally(() => setLoading(false))
  }, [])

  const handleSelect = async (sessionId: string) => {
    latestRequestRef.current = sessionId
    setSelectedId(sessionId)
    setDetailLoading(true)
    try {
      const d = await api.getSession(sessionId) as SessionDetail
      if (latestRequestRef.current === sessionId) setDetail(d)
    } catch {
      if (latestRequestRef.current === sessionId) setDetail(null)
    }
    if (latestRequestRef.current === sessionId) setDetailLoading(false)
  }

  return (
    <div className="history-layout">
      <div className="history-sidebar">
        <div className="history-sidebar-header">
          <span className="history-sidebar-title">Sessions</span>
          <span className="history-sidebar-count">{sessions.length}</span>
        </div>
        <div className="history-sidebar-list">
          {loading ? (
            <div className="history-empty">Loading sessions...</div>
          ) : sessions.length === 0 ? (
            <div className="history-empty">No sessions yet.</div>
          ) : (
            sessions.map(s => (
              <div
                key={s.session_id}
                role="button"
                tabIndex={0}
                className={`history-session-item${selectedId === s.session_id ? ' active' : ''}`}
                onClick={() => handleSelect(s.session_id)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSelect(s.session_id) } }}
              >
                <div className="history-session-query">
                  {s.first_query ? truncate(s.first_query, 60) : '(empty query)'}
                </div>
                <div className="history-session-meta">
                  {shortTime(s.started_at)} &middot; {s.turns} turn{s.turns !== 1 ? 's' : ''}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="history-detail">
        {!selectedId ? (
          <div className="history-empty-detail">
            Select a session to view recommendations.
          </div>
        ) : detailLoading ? (
          <div className="history-empty-detail">Loading...</div>
        ) : !detail || detail.turns.length === 0 ? (
          <div className="history-empty-detail">Session not found.</div>
        ) : (
          <>
            {detail.turns.map((turn, turnIdx) => {
              const candidates = turn.results_json || []
              return (
                <div key={turnIdx} style={{
                  marginBottom: 24,
                  paddingBottom: turnIdx < detail.turns.length - 1 ? 24 : 0,
                  borderBottom: turnIdx < detail.turns.length - 1 ? '1px solid var(--border-subtle)' : undefined,
                }}>
                  {turn.query_text && (
                    <div className="history-query-banner">
                      {turn.query_text}
                    </div>
                  )}
                  {turn.envelope_json ? (
                    <>
                      <div style={{ padding: '12px 0', fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                        {turn.envelope_json.intent.replace('_', ' ')}
                      </div>
                      <div className="history-assessment">
                        {turn.envelope_json.answer}
                      </div>
                    </>
                  ) : (
                    <>
                      {turn.overall_assessment && (
                        <div className="history-assessment">
                          {turn.overall_assessment}
                        </div>
                      )}
                      {candidates.length > 0 && (
                        <div className="history-rec-list">
                          {candidates.filter(c => c.tier === 'green').length > 0 && (
                            <div className="history-tier-label" style={{ color: 'var(--score-green)' }}>
                              Best fit ({candidates.filter(c => c.tier === 'green').length})
                            </div>
                          )}
                          {candidates.filter(c => c.tier === 'green').map(c => (
                            <RecCard key={c.ci_name} candidate={c} isComplete={true} sessionId={detail.session_id} turnIndex={turnIdx} chosenCiName={turn.chosen_ci_name || undefined} />
                          ))}
                          {candidates.filter(c => c.tier === 'yellow').length > 0 && (
                            <div className="history-tier-label" style={{ color: 'var(--score-amber)' }}>
                              Other options ({candidates.filter(c => c.tier === 'yellow').length})
                            </div>
                          )}
                          {candidates.filter(c => c.tier === 'yellow').map(c => (
                            <RecCard key={c.ci_name} candidate={c} isComplete={true} sessionId={detail.session_id} turnIndex={turnIdx} />
                          ))}
                          {candidates.filter(c => c.tier !== 'green' && c.tier !== 'yellow').length > 0 && (
                            <div className="history-tier-label" style={{ color: 'var(--text-muted)' }}>
                              Also reviewed ({candidates.filter(c => c.tier !== 'green' && c.tier !== 'yellow').length})
                            </div>
                          )}
                          {candidates.filter(c => c.tier !== 'green' && c.tier !== 'yellow').map(c => (
                            <RecCard key={c.ci_name} candidate={c} isComplete={true} sessionId={detail.session_id} turnIndex={turnIdx} />
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )
            })}
            <div style={{ marginTop: 12 }}>
              <a href={`/advisor?session=${detail.session_id}`} style={{ color: 'var(--text-link)', fontSize: '13px' }}>
                Open in Advisor →
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
