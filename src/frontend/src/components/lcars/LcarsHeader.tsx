import { NavLink } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export function LcarsHeader() {
  const auth = useAuth()

  return (
    <header className="rcars-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <svg className="rcars-logo" viewBox="0 0 200 50" xmlns="http://www.w3.org/2000/svg">
          <path d="M5 45 Q5 5 45 5 L120 5" stroke="#FF9900" strokeWidth="8" fill="none" strokeLinecap="round" />
          <rect x="125" y="1" width="30" height="8" rx="4" fill="#9966CC" />
          <rect x="160" y="1" width="15" height="8" rx="4" fill="#FF9900" />
          <text x="45" y="35" fontFamily="Arial, sans-serif" fontSize="22" fontWeight="700" fill="#FF9900">RCARS</text>
          <text x="122" y="35" fontFamily="Arial, sans-serif" fontSize="10" fill="#666">v2</text>
        </svg>
        <nav style={{ display: 'flex', gap: '4px' }}>
          <NavLink to="/advisor" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            Advisor
          </NavLink>
          <NavLink to="/browse" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            Browse
          </NavLink>
          {auth.isAdmin && (
            <NavLink to="/admin" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              Admin
            </NavLink>
          )}
        </nav>
      </div>
      <div className="header-right">
        {auth.email && <span className="user-email">{auth.email}</span>}
      </div>
    </header>
  )
}
