import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export function LcarsSidebar() {
  const auth = useAuth()
  const location = useLocation()
  const isAdminSection = location.pathname.startsWith('/admin')

  return (
    <nav className="rcars-nav">
      <NavLink to="/advisor" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
        Advisor
      </NavLink>
      {location.pathname === '/advisor' && (
        <a href="/advisor" className="nav-new-session" onClick={(e) => { e.preventDefault(); window.location.href = '/advisor' }}>
          + New Session
        </a>
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
