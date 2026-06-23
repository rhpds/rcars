import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthContext, useAuthProvider } from './hooks/useAuth'
import { PrivateModeContext, usePrivateModeProvider } from './hooks/usePrivateMode'
import { LcarsHeader, LcarsSidebar } from './components/lcars'
import { AdvisorPage } from './pages/AdvisorPage'
import { BrowsePage } from './pages/BrowsePage'
import { AdminCatalogPage, AdminTokensPage, AdminQueriesPage } from './pages/AdminPage'
import { ContentOverlapPage } from './pages/ContentAnalysisPage'
import { RetirementPage } from './pages/RetirementPage'
import './styles/lcars.css'

export default function App() {
  const auth = useAuthProvider()
  const privateMode = usePrivateModeProvider()

  if (auth.isLoading) {
    return (
      <div style={{ background: '#0f1117', color: '#666', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        Loading...
      </div>
    )
  }

  return (
    <AuthContext.Provider value={auth}>
      <PrivateModeContext.Provider value={privateMode}>
        <BrowserRouter>
          <LcarsHeader />
          <div className="rcars-body">
            <LcarsSidebar />
            <main className="rcars-main">
              <Routes>
                <Route path="/" element={<Navigate to="/advisor" replace />} />
                <Route path="/advisor" element={<AdvisorPage />} />
                <Route path="/browse" element={<BrowsePage />} />
                {auth.isAdmin && (
                  <>
                    <Route path="/analysis" element={<Navigate to="/analysis/overlap" replace />} />
                    <Route path="/analysis/overlap" element={<ContentOverlapPage />} />
                    <Route path="/analysis/retirement" element={<RetirementPage />} />
                    <Route path="/admin" element={<Navigate to="/admin/catalog" replace />} />
                    <Route path="/admin/catalog" element={<AdminCatalogPage />} />
                    <Route path="/admin/workers" element={<Navigate to="/admin/catalog" replace />} />
                    <Route path="/admin/tokens" element={<AdminTokensPage />} />
                    <Route path="/admin/queries" element={<AdminQueriesPage />} />
                  </>
                )}
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </PrivateModeContext.Provider>
    </AuthContext.Provider>
  )
}
