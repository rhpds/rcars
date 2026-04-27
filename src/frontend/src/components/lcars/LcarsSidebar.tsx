import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { api } from '../../services/api'

interface SessionSummary {
  session_id: string
  started_at: string
  turns: number
}

export function LcarsSidebar() {
  const auth = useAuth()
  const location = useLocation()
  const isAdminSection = location.pathname.startsWith('/admin')
  const isAdvisorPage = location.pathname === '/advisor'
  const [sessions, setSessions] = useState<SessionSummary[]>([])

  useEffect(() => {
    if (isAdvisorPage) {
      api.listSessions().then(data => setSessions((data.items as SessionSummary[]).slice(0, 8)))
    }
  }, [isAdvisorPage])

  return (
    <nav className="rcars-nav">
      <NavLink to="/advisor" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
        Advisor
      </NavLink>
      {isAdvisorPage && (
        <>
          <a href="/advisor" className="nav-new-session" onClick={(e) => { e.preventDefault(); window.location.href = '/advisor' }}>
            + New Session
          </a>
          {sessions.length > 0 && (
            <div style={{ padding: '8px 14px 4px', fontSize: '10px', color: '#555', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Recent</div>
          )}
          {sessions.map(s => (
            <div
              key={s.session_id}
              style={{ padding: '3px 14px', fontSize: '12px', color: '#666', cursor: 'default' }}
              title={new Date(s.started_at).toLocaleString()}
            >
              {new Date(s.started_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} · {s.turns} turn{s.turns !== 1 ? 's' : ''}
            </div>
          ))}
        </>
      )}
      <NavLink to="/browse" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
        Browse
      </NavLink>
      {auth.isAdmin && (
        <>
          <NavLink to="/admin/catalog" className={() => `nav-item${isAdminSection ? ' active' : ''}`}>
            Admin
          </NavLink>
          {isAdminSection && (
            <>
              <NavLink
                to="/admin/catalog"
                className={({ isActive }) => `nav-item history-item${isActive ? ' active' : ''}`}
              >
                Catalog Status
              </NavLink>
              <NavLink
                to="/admin/workers"
                className={({ isActive }) => `nav-item history-item${isActive ? ' active' : ''}`}
              >
                Workers
              </NavLink>
              <NavLink
                to="/admin/tokens"
                className={({ isActive }) => `nav-item history-item${isActive ? ' active' : ''}`}
              >
                Token Usage
              </NavLink>
              <NavLink
                to="/admin/queries"
                className={({ isActive }) => `nav-item history-item${isActive ? ' active' : ''}`}
              >
                Query History
              </NavLink>
            </>
          )}
        </>
      )}
    </nav>
  )
}
