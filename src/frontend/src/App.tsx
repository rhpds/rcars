import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Page } from '@patternfly/react-core'
import { AuthContext, useAuthProvider } from './hooks/useAuth'
import { PrivateModeContext, usePrivateModeProvider } from './hooks/usePrivateMode'
import { ThemeContext, useThemeProvider } from './hooks/useTheme'
import { RcarsMasthead } from './components/RcarsMasthead'
import { RcarsSidebar } from './components/RcarsSidebar'
import { AdvisorPage } from './pages/AdvisorPage'
import { BrowsePage } from './pages/BrowsePage'
import { WorkloadsPage } from './pages/WorkloadsPage'
import { AdminTokensPage, AdminQueriesPage } from './pages/AdminPage'
import { ContentOverlapPage } from './pages/ContentAnalysisPage'
import { RetirementPage } from './pages/RetirementPage'
import { StatusPage } from './pages/StatusPage'
import { SyncPage } from './pages/SyncPage'
import { RecentJobsPage } from './pages/RecentJobsPage'
import { HistoryPage } from './pages/HistoryPage'
import './styles/rcars-app.css'

export default function App() {
  const auth = useAuthProvider()
  const privateMode = usePrivateModeProvider()
  const themeState = useThemeProvider()

  if (auth.isLoading) {
    return (
      <div style={{ background: 'var(--bg-page, #0f1117)', color: 'var(--text-muted, #666)', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        Loading...
      </div>
    )
  }

  return (
    <AuthContext.Provider value={auth}>
      <PrivateModeContext.Provider value={privateMode}>
        <ThemeContext.Provider value={themeState}>
          <BrowserRouter>
            <Page
              masthead={<RcarsMasthead />}
              sidebar={<RcarsSidebar />}
            >
              <div className="rcars-main">
                <Routes>
                  <Route path="/" element={<Navigate to="/advisor" replace />} />
                  <Route path="/advisor" element={<AdvisorPage />} />
                <Route path="/advisor/history" element={<HistoryPage />} />
                  <Route path="/browse" element={<BrowsePage />} />
                  {auth.isCurator && (
                    <Route path="/browse/workloads" element={<WorkloadsPage />} />
                  )}
                  {auth.isAdmin && (
                    <>
                      <Route path="/analysis" element={<Navigate to="/analysis/overlap" replace />} />
                      <Route path="/analysis/overlap" element={<ContentOverlapPage />} />
                      <Route path="/analysis/retirement" element={<RetirementPage />} />
                      <Route path="/system/status" element={<StatusPage />} />
                      <Route path="/system/sync" element={<SyncPage />} />
                      <Route path="/system/jobs" element={<RecentJobsPage />} />
                      <Route path="/system/tokens" element={<AdminTokensPage />} />
                      <Route path="/system/queries" element={<AdminQueriesPage />} />
                      {/* Legacy routes redirect */}
                      <Route path="/admin" element={<Navigate to="/system/status" replace />} />
                      <Route path="/admin/catalog" element={<Navigate to="/system/status" replace />} />
                      <Route path="/admin/tokens" element={<Navigate to="/system/tokens" replace />} />
                      <Route path="/admin/queries" element={<Navigate to="/system/queries" replace />} />
                    </>
                  )}
                </Routes>
              </div>
            </Page>
          </BrowserRouter>
        </ThemeContext.Provider>
      </PrivateModeContext.Provider>
    </AuthContext.Provider>
  )
}
