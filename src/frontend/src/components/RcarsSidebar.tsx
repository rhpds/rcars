import { useState, useEffect } from 'react'
import { NavLink, useLocation, useSearchParams } from 'react-router-dom'
import { PageSidebar, PageSidebarBody } from '@patternfly/react-core'
import { useAuth } from '../hooks/useAuth'
import { api } from '../services/api'

interface SessionSummary {
  session_id: string
  started_at: string
  turns: number
  first_query?: string
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '...' : s
}

export function RcarsSidebar() {
  const auth = useAuth()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const isAdvisorPage = location.pathname === '/advisor'
  const activeSession = searchParams.get('session')
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [historyOpen, setHistoryOpen] = useState(true)

  useEffect(() => {
    if (isAdvisorPage) {
      api.listSessions().then(async (data) => {
        const items = (data.items as SessionSummary[]).slice(0, 8)
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

  return (
    <PageSidebar className="rcars-sidebar">
      <PageSidebarBody>
        <nav>
          {/* ── Top section (everyone) ── */}
          <NavLink
            to="/advisor"
            className={({ isActive }) => `rcars-nav-item${isActive ? ' active' : ''}`}
          >
            Advisor
          </NavLink>

          {/* History sub-items when on Advisor page */}
          {isAdvisorPage && sessions.length > 0 && (
            <>
              <div
                className="rcars-nav-session-label"
                style={{ cursor: 'pointer' }}
                onClick={() => setHistoryOpen(!historyOpen)}
              >
                {historyOpen ? '▾' : '▸'} History
              </div>
              {historyOpen && sessions.map(s => (
                <NavLink
                  key={s.session_id}
                  to={`/advisor?session=${s.session_id}`}
                  className={`rcars-nav-session-item${activeSession === s.session_id ? ' active' : ''}`}
                  title={s.first_query || new Date(s.started_at).toLocaleString()}
                >
                  {s.first_query
                    ? truncate(s.first_query, 32)
                    : new Date(s.started_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                </NavLink>
              ))}
            </>
          )}

          <div className="rcars-nav-section-label">Browse</div>

          <NavLink
            to="/browse"
            className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
          >
            Catalog
          </NavLink>

          {auth.isCurator && (
            <NavLink
              to="/browse/workloads"
              className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
            >
              Workloads
            </NavLink>
          )}

          {/* ── Analysis section (admin only) ── */}
          {auth.isAdmin && (
            <>
              <div className="rcars-nav-section-label">Analysis</div>

              <NavLink
                to="/analysis/overlap"
                className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
              >
                Overlap
              </NavLink>

              <NavLink
                to="/analysis/retirement"
                className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
              >
                Retirement
              </NavLink>

              {/* ── System section (admin only) ── */}
              <div className="rcars-nav-section-label">System</div>

              <NavLink
                to="/system/status"
                className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
              >
                Status
              </NavLink>

              <NavLink
                to="/system/sync"
                className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
              >
                Sync & Analysis
              </NavLink>

              <NavLink
                to="/system/jobs"
                className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
              >
                Recent Jobs
              </NavLink>

              <NavLink
                to="/system/tokens"
                className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
              >
                Token Usage
              </NavLink>

              <NavLink
                to="/system/queries"
                className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
              >
                Query History
              </NavLink>
            </>
          )}
        </nav>
      </PageSidebarBody>
    </PageSidebar>
  )
}
