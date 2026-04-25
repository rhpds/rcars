import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthContext, useAuthProvider } from './hooks/useAuth'
import { LcarsHeader, LcarsSidebar } from './components/lcars'
import { AdvisorPage } from './pages/AdvisorPage'
import { BrowsePage } from './pages/BrowsePage'
import { AdminPage } from './pages/AdminPage'
import './styles/lcars.css'

export default function App() {
  const auth = useAuthProvider()

  if (auth.isLoading) {
    return (
      <div style={{ background: '#0f1117', color: '#666', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        Loading...
      </div>
    )
  }

  return (
    <AuthContext.Provider value={auth}>
      <BrowserRouter>
        <LcarsHeader />
        <div className="rcars-body">
          <LcarsSidebar />
          <main className="rcars-main">
            <Routes>
              <Route path="/" element={<Navigate to="/advisor" replace />} />
              <Route path="/advisor" element={<AdvisorPage />} />
              <Route path="/browse" element={<BrowsePage />} />
              {auth.isAdmin && <Route path="/admin" element={<AdminPage />} />}
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}
