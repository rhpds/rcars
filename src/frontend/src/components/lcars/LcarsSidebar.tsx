import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export function LcarsSidebar() {
  const auth = useAuth()
  const location = useLocation()

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
        <NavLink to="/admin" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
          Admin
        </NavLink>
      )}
    </nav>
  )
}
