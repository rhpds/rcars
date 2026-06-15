import { useState, useEffect } from 'react'
import { NavLink, useLocation, useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { api } from '../../services/api'

interface SessionSummary {
  session_id: string
  started_at: string
  turns: number
  first_query?: string
}

export function LcarsSidebar() {
  const auth = useAuth()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isAnalysisSection = location.pathname.startsWith('/analysis')
  const isAdminSection = location.pathname.startsWith('/admin')
  const isAdvisorPage = location.pathname === '/advisor'
  const activeSession = searchParams.get('session')
  const [sessions, setSessions] = useState<SessionSummary[]>([])

  useEffect(() => {
    if (isAdvisorPage) {
      api.listSessions().then(async (data) => {
        const items = (data.items as SessionSummary[]).slice(0, 8)
        // Fetch first query text for each session
        const enriched = await Promise.all(items.map(async (s) => {
          try {
            const detail = await api.getSession(s.session_id) as { turns: Array<{ query_text: string | null }> }
            return { ...s, first_query: detail.turns[0]?.query_text || undefined }
          } catch { return s }
        }))
        setSessions(enriched)
      })
    }
  }, [isAdvisorPage])

  const truncate = (s: string, max: number) => s.length > max ? s.slice(0, max) + '...' : s

  return (
    <nav className="rcars-nav">
      <NavLink to="/advisor" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
        Advisor
      </NavLink>
      {isAdvisorPage && (
        <>
          <a
            href="/advisor"
            className="nav-new-session"
            onClick={(e) => { e.preventDefault(); window.dispatchEvent(new Event('rcars:new-session')); navigate('/advisor', { replace: true }) }}
          >
            + New Session
          </a>
          {sessions.length > 0 && (
            <div style={{ padding: '8px 14px 4px', fontSize: '10px', color: '#555', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Recent</div>
          )}
          {sessions.map(s => (
            <NavLink
              key={s.session_id}
              to={`/advisor?session=${s.session_id}`}
              className="nav-session-item"
              style={{
                display: 'block', padding: '5px 14px', fontSize: '12px',
                color: activeSession === s.session_id ? '#73bcf7' : '#777',
                textDecoration: 'none', cursor: 'pointer',
                background: activeSession === s.session_id ? '#0d1520' : 'transparent',
                borderLeft: activeSession === s.session_id ? '2px solid #73bcf7' : '2px solid transparent',
              }}
              title={s.first_query || new Date(s.started_at).toLocaleString()}
            >
              {s.first_query ? truncate(s.first_query, 32) : new Date(s.started_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
            </NavLink>
          ))}
        </>
      )}
      <NavLink to="/browse" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
        Browse
      </NavLink>
      {auth.isAdmin && (
        <>
          <NavLink to="/analysis/overlap" className={() => `nav-item${isAnalysisSection ? ' active' : ''}`}>
            Content Analysis
          </NavLink>
          {isAnalysisSection && (
            <>
              <NavLink to="/analysis/overlap" className={({ isActive }) => `nav-item history-item${isActive ? ' active' : ''}`}>
                Overlap
              </NavLink>
            </>
          )}
          <NavLink to="/admin/catalog" className={() => `nav-item${isAdminSection ? ' active' : ''}`}>
            Admin
          </NavLink>
          {isAdminSection && (
            <>
              <NavLink to="/admin/catalog" className={({ isActive }) => `nav-item history-item${isActive ? ' active' : ''}`}>
                Catalog
              </NavLink>
              <NavLink to="/admin/tokens" className={({ isActive }) => `nav-item history-item${isActive ? ' active' : ''}`}>
                Token Usage
              </NavLink>
              <NavLink to="/admin/queries" className={({ isActive }) => `nav-item history-item${isActive ? ' active' : ''}`}>
                Query History
              </NavLink>
            </>
          )}
        </>
      )}
    </nav>
  )
}
