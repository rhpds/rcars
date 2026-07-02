import { NavLink } from 'react-router-dom'
import { PageSidebar, PageSidebarBody } from '@patternfly/react-core'
import { useAuth } from '../hooks/useAuth'

export function RcarsSidebar() {
  const auth = useAuth()

  return (
    <PageSidebar className="rcars-sidebar">
      <PageSidebarBody>
        <nav>
          <div className="rcars-nav-section-label">Advisor</div>

          <NavLink
            to="/advisor"
            end
            className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
            onClick={() => window.dispatchEvent(new Event('rcars:new-session'))}
          >
            New Session
          </NavLink>

          <NavLink
            to="/advisor/history"
            className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
          >
            History
          </NavLink>

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
