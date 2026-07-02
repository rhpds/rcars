import { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Masthead, MastheadMain, MastheadContent } from '@patternfly/react-core'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import { api } from '../services/api'

interface DbStatus {
  catalog_date: string
  catalog_stale: boolean
  analysis_date: string
  analysis_stale: boolean
}

function formatAge(dateStr: string): string {
  const t = new Date(dateStr).getTime()
  if (Number.isNaN(t)) return '—'
  const ms = Date.now() - t
  const hours = Math.floor(ms / 3_600_000)
  if (hours < 1) return '<1h ago'
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

const DOCS_BASE = 'https://rhpds.github.io/rcars'

function HelpMenu() {
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
        className="rcars-help-toggle"
        onClick={() => setOpen(!open)}
        title="Help & Links"
      >
        ?
      </button>
      {open && (
        <div className="rcars-help-menu">
          <a href={`${DOCS_BASE}/overview/`} target="_blank" rel="noopener noreferrer" className="rcars-help-menu-item" onClick={() => setOpen(false)}>
            Overview
          </a>
          <a href={`${DOCS_BASE}/user/guide-web/`} target="_blank" rel="noopener noreferrer" className="rcars-help-menu-item" onClick={() => setOpen(false)}>
            Web UI Guide
          </a>
          <div style={{ borderTop: '1px solid var(--border-default)', margin: '4px 0' }} />
          <a href="https://demo.redhat.com" target="_blank" rel="noopener noreferrer" className="rcars-help-menu-item" onClick={() => setOpen(false)}>
            RHDP Catalog
          </a>
        </div>
      )}
    </div>
  )
}

function getInitials(email: string): string {
  if (!email) return '?'
  const name = email.split('@')[0]
  const parts = name.split(/[.\-_]/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

export function RcarsMasthead() {
  const auth = useAuth()
  const { theme, toggle } = useTheme()
  const [dbStatus, setDbStatus] = useState<DbStatus | null>(null)

  useEffect(() => {
    api.getCatalogStats()
      .then(data => setDbStatus(data as DbStatus))
      .catch(() => {})
  }, [])

  return (
    <Masthead className="rcars-masthead">
      <MastheadMain>
        <div className="rcars-masthead-left">
          <Link to="/advisor" className="rcars-masthead-logo" aria-label="RCARS Home">
            <svg viewBox="0 0 196 54" xmlns="http://www.w3.org/2000/svg">
              <path d="M 6 3 A 28 28 0 0 1 34 31 L 46 31 L 46 51 L 30 51 Q 6 51 6 22 Z" className="rcars-svg-arc"/>
              <path d="M 14 14 A 14 14 0 0 1 28 28" className="rcars-svg-arc-stroke" strokeWidth="2" fill="none" opacity="0.6"/>
              <rect x="50" y="3" width="80" height="14" rx="3" className="rcars-svg-bar1"/>
              <rect x="134" y="3" width="18" height="14" rx="3" className="rcars-svg-bar2"/>
              <rect x="156" y="3" width="34" height="14" rx="3" className="rcars-svg-bar3"/>
              <rect x="50" y="21" width="140" height="10" rx="2" className="rcars-svg-mid"/>
              <rect x="50" y="35" width="34" height="14" rx="3" className="rcars-svg-bar-b1"/>
              <rect x="88" y="35" width="80" height="14" rx="3" className="rcars-svg-bar-b2"/>
              <rect x="172" y="35" width="18" height="14" rx="3" className="rcars-svg-bar-b3"/>
              <text x="56" y="15" fontFamily="'Red Hat Display', Arial Black, sans-serif" fontSize="11" fontWeight="900" className="rcars-svg-title" letterSpacing="3">RCARS</text>
              <text x="56" y="29" fontFamily="'Red Hat Display', Arial, sans-serif" fontSize="7" className="rcars-svg-subtitle" letterSpacing="1.5">RHDP CONTENT ADVISOR</text>
            </svg>
          </Link>

          <div className="rcars-masthead-status">
            {dbStatus && (
              <>
                <span className="rcars-masthead-status-item">
                  <span className={`rcars-status-dot ${dbStatus.catalog_stale ? 'rcars-status-dot--stale' : 'rcars-status-dot--ok'}`}>
                    CATALOG
                  </span>
                  <span>{formatAge(dbStatus.catalog_date)}</span>
                </span>
                <span className="rcars-masthead-status-item">
                  <span className={`rcars-status-dot ${dbStatus.analysis_stale ? 'rcars-status-dot--stale' : 'rcars-status-dot--ok'}`}>
                    ANALYSIS
                  </span>
                  <span>{formatAge(dbStatus.analysis_date)}</span>
                </span>
              </>
            )}
          </div>
        </div>
      </MastheadMain>

      <MastheadContent>
        <div className="rcars-masthead-right">
          <HelpMenu />
          <button
            className="rcars-theme-toggle"
            onClick={toggle}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? '☽' : '☀'}
          </button>
          {auth.email && (
            <div className="rcars-user-avatar" title={auth.email}>
              {getInitials(auth.email)}
            </div>
          )}
        </div>
      </MastheadContent>
    </Masthead>
  )
}
