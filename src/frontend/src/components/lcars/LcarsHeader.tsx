import { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useTheme } from '../../hooks/useTheme'
import { api } from '../../services/api'

interface DbStatus {
  catalog_date: string
  catalog_stale: boolean
  analysis_date: string
  analysis_stale: boolean
}

const DOCS_BASE = 'https://rhpds.github.io/rcars'

function HeaderMenu() {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={menuRef} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: 'transparent',
          border: '1px solid var(--input-border)',
          color: 'var(--text-muted)',
          padding: '4px 10px',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
        }}
      >
        ☰
      </button>
      {open && (
        <div style={{
          position: 'absolute',
          right: 0,
          top: '100%',
          marginTop: '6px',
          background: 'var(--menu-bg)',
          border: '1px solid var(--input-border)',
          borderRadius: '6px',
          minWidth: '180px',
          zIndex: 100,
          boxShadow: '0 4px 12px var(--menu-shadow)',
        }}>
          <a
            href={`${DOCS_BASE}/overview/`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
            style={menuItemStyle}
          >
            Overview
          </a>
          <a
            href={`${DOCS_BASE}/user/guide-web/`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
            style={menuItemStyle}
          >
            Web UI Guide
          </a>
          <div style={{ borderTop: '1px solid var(--input-border)' }} />
          <button
            onClick={() => { setOpen(false) }}
            style={{ ...menuItemStyle, width: '100%', textAlign: 'left', background: 'transparent', border: 'none', cursor: 'not-allowed', opacity: 0.5 }}
          >
            Send Feedback
          </button>
        </div>
      )}
    </div>
  )
}

const menuItemStyle: React.CSSProperties = {
  display: 'block',
  padding: '10px 16px',
  color: 'var(--text-secondary)',
  textDecoration: 'none',
  fontSize: '14px',
  cursor: 'pointer',
}

export function LcarsHeader() {
  const auth = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [dbStatus, setDbStatus] = useState<DbStatus | null>(null)

  useEffect(() => {
    api.getCatalogStats()
      .then(data => setDbStatus(data as DbStatus))
      .catch(() => {})
  }, [])

  const catalogColor = dbStatus?.catalog_stale ? '#c9190b' : '#5cb85c'
  const catalogLabel = dbStatus?.catalog_stale ? 'STALE' : 'CURRENT'
  const analysisColor = dbStatus?.analysis_stale ? '#c9190b' : '#5cb85c'
  const analysisLabel = dbStatus?.analysis_stale ? 'STALE' : 'CURRENT'

  return (
    <header className="rcars-header">
      <div id="currency-badges">
        <Link to="/advisor" style={{ display: 'inline-block', lineHeight: 0 }}>
        <svg width="380" height="110" viewBox="0 0 380 110" xmlns="http://www.w3.org/2000/svg" className="rcars-logo">
          {/* Arc */}
          <path d="M 12 10 A 54 54 0 0 1 66 64 L 84 64 L 84 104 L 56 104 Q 12 104 12 40 Z" fill="#FF9900"/>
          <path d="M 24 28 A 28 28 0 0 1 50 54" stroke="#CC6600" strokeWidth="4" fill="none" opacity="0.6"/>
          {/* Header bars */}
          <rect x="90" y="10" width="140" height="30" rx="5" fill="#FF9900"/>
          <rect x="236" y="10" width="34" height="30" rx="5" fill="#FFCC99"/>
          <rect x="276" y="10" width="60" height="30" rx="5" fill="#9966CC"/>
          {/* Middle bar */}
          <rect x="90" y="46" width="246" height="18" rx="4" fill="var(--lcars-logo-middle)"/>
          {/* Catalog status bar */}
          <rect x="90" y="70" width="246" height="16" rx="4" fill="var(--lcars-logo-middle)"/>
          {/* Analysis status bar */}
          <rect x="90" y="90" width="246" height="16" rx="4" fill="var(--lcars-logo-middle)"/>
          {/* RCARS */}
          <text x="100" y="32" fontFamily="Arial Black, Impact, sans-serif" fontSize="20" fontWeight="900" fill="#000" letterSpacing="5">RCARS</text>
          {/* RHDP CONTENT ADVISOR */}
          <text x="100" y="60" fontFamily="Arial, sans-serif" fontSize="13" fill="#FF9900" letterSpacing="2">RHDP CONTENT ADVISOR</text>
          {/* Catalog row */}
          <text x="100" y="82" fontFamily="Arial, sans-serif" fontSize="10" fill="#666">
            CATALOG {dbStatus?.catalog_date || '...'}
          </text>
          {dbStatus && (
            <text x="230" y="82" fontFamily="Arial Black, sans-serif" fontSize="10" fontWeight="900" fill={catalogColor}>
              ● {catalogLabel}
            </text>
          )}
          {/* Analysis row */}
          <text x="100" y="102" fontFamily="Arial, sans-serif" fontSize="10" fill="#666">
            ANALYSIS {dbStatus?.analysis_date || '...'}
          </text>
          {dbStatus && (
            <text x="230" y="102" fontFamily="Arial Black, sans-serif" fontSize="10" fontWeight="900" fill={analysisColor}>
              ● {analysisLabel}
            </text>
          )}
        </svg>
        </Link>
      </div>

      <div className="header-right">
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? '\u2600' : '\u263D'}
        </button>
        <HeaderMenu />
        {auth.email && <span className="user-email">{auth.email}</span>}
      </div>
    </header>
  )
}
