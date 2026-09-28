import { useState } from 'react'
import { api } from '../../services/api'
import type { StreamCandidate } from '../../hooks/useJobStream'

interface RecCardProps {
  candidate: StreamCandidate
  sessionId?: string
  turnIndex?: number
  chosenCiName?: string
  isComplete: boolean
}

function buildUrl(template: string, candidate: StreamCandidate): string {
  if (template === 'catalog' && candidate.ci_name) {
    const ns = candidate.catalog_namespace || 'babylon-catalog-prod'
    return `https://demo.redhat.com/catalog?item=${ns}/${candidate.ci_name}`
  }
  if (template === 'browse') {
    return '/browse?search=' + encodeURIComponent(candidate.display_name)
  }
  return '#'
}

const FALLBACK_FORMAT_LABELS: Record<string, string> = {
  hands_on_lab: 'Hands-on Lab',
  demo: 'Demo',
}

const FORMAT_COLORS: Record<string, { bg: string; color: string }> = {
  hands_on_lab: { bg: 'var(--badge-blue-bg)', color: 'var(--badge-blue-text)' },
  demo: { bg: 'var(--badge-amber-bg)', color: 'var(--badge-amber-text)' },
  architecture: { bg: 'var(--badge-purple-bg, var(--badge-blue-bg))', color: 'var(--badge-purple-text, var(--badge-blue-text))' },
}

export function RecCard({ candidate, sessionId, turnIndex, chosenCiName, isComplete }: RecCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [selected, setSelected] = useState(chosenCiName === candidate.content_id || chosenCiName === candidate.ci_name)
  const [showFullCaveat, setShowFullCaveat] = useState(false)
  const [showSalesInfo, setShowSalesInfo] = useState(false)

  const score = Math.min(100, Math.max(0, candidate.relevance_score ?? candidate.vector_similarity_pct ?? 0))
  const tier = candidate.tier as 'green' | 'yellow' | 'white'
  const tierClass = tier === 'green' ? 'tier-green' : tier === 'yellow' ? 'tier-yellow' : ''
  const display = candidate.display

  const handleSelect = async () => {
    if (!sessionId || turnIndex == null) return
    await api.selectRecommendation(sessionId, turnIndex, candidate.ci_name || candidate.content_id)
    setSelected(true)
  }

  const caveatText = candidate.caveats || ''
  const caveatTruncated = caveatText.length > 200 && !showFullCaveat

  // Format badge — from display config or fallback
  const formatBadge = display?.format_badge
  const formatKey = formatBadge?.key || candidate.suggested_format || ''
  const formatLabel = formatBadge?.label || FALLBACK_FORMAT_LABELS[formatKey] || (formatKey ? formatKey.replace(/_/g, ' ') : null)
  const formatStyle = FORMAT_COLORS[formatKey] || { bg: 'var(--badge-blue-bg)', color: 'var(--badge-blue-text)' }

  // Header right — from display config or fallback to duration_min
  const headerRight = display?.header_right
  const durationDisplay = headerRight?.value || (candidate.duration_min ? `~${candidate.duration_min} min` : null)
  const durationTooltip = headerRight?.tooltip || (candidate.duration_min
    ? (candidate.duration_source === 'curated' ? 'Curated duration' : 'AI duration estimate')
    : null)

  // Stage display
  const stage = candidate.stage || candidate.status || 'prod'

  return (
    <div className={`rec-card ${tierClass}`}>
      <div
        className="rec-card-header"
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(!expanded) } }}
        style={{ cursor: 'pointer' }}
      >
        <span className="rec-score" style={{ fontFamily: 'var(--ff-display)' }}>{score}%</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="rec-title" style={{ fontFamily: 'var(--ff-display)' }}>{candidate.display_name}</div>
          <div className="rec-meta">
            {stage !== 'prod' && (
              <span className="rec-badge" style={{ background: stage === 'dev' ? 'var(--badge-blue-bg)' : 'var(--badge-amber-bg)', color: stage === 'dev' ? 'var(--badge-blue-text)' : 'var(--badge-amber-text)' }}>
                {stage.toUpperCase()}
              </span>
            )}
            {(candidate.catalog_namespace?.startsWith('zt-') || candidate.ci_name?.startsWith('zt-')) && (
              <span className="rec-badge" style={{ background: 'var(--score-green-bg)', color: 'var(--score-green)' }}>ZT</span>
            )}
            {formatLabel && (
              <span className="rec-badge" style={{ background: formatStyle.bg, color: formatStyle.color }}>{formatLabel}</span>
            )}
            {candidate.ci_name && (
              <span style={{ fontFamily: 'var(--ff-mono)' }}>{candidate.ci_name}</span>
            )}
            {durationTooltip && !durationDisplay && (
              <><span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>·</span><span>{durationTooltip}</span></>
            )}
          </div>
        </div>
        {durationDisplay && (
          <span
            style={{ fontSize: '14px', color: 'var(--text-secondary)', fontWeight: 500, flexShrink: 0, fontFamily: 'var(--ff-mono)' }}
            title={durationTooltip || undefined}
          >
            {durationDisplay}
          </span>
        )}
        <span className="rec-expand-hint">{expanded ? '▾' : '▸'}</span>
      </div>

      {expanded && (
        <div className="rec-expanded" style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
          {/* Detail rows — from display config or fallback */}
          {display?.detail_rows ? (
            display.detail_rows.map((row, i) => {
              const value = candidate[row.field] as string | string[] | null | undefined
              if (!value || (Array.isArray(value) && value.length === 0)) return null
              return (
                <div key={i} className="rec-row">
                  <span className="rec-row-label">{row.label}</span>
                  {row.type === 'list' && Array.isArray(value) ? (
                    <div className="rec-row-value">
                      <ul className="rec-objectives-list">
                        {(value as string[]).slice(0, row.max || 5).map((item, j) => (
                          <li key={j}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <span className="rec-row-value">{value as string}</span>
                  )}
                </div>
              )
            })
          ) : (
            <>
              {candidate.why_it_fits && (
                <div className="rec-row">
                  <span className="rec-row-label">Why it fits</span>
                  <span className="rec-row-value">{candidate.why_it_fits}</span>
                </div>
              )}
              {tier === 'green' && candidate.learning_objectives && candidate.learning_objectives.length > 0 && (
                <div className="rec-row">
                  <span className="rec-row-label">Objectives</span>
                  <div className="rec-row-value">
                    <ul className="rec-objectives-list">
                      {candidate.learning_objectives.slice(0, 5).map((obj, i) => (
                        <li key={i}>{obj}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
              {candidate.how_to_use && (
                <div className="rec-row">
                  <span className="rec-row-label">How to use</span>
                  <div className="rec-row-value">
                    <div>{candidate.how_to_use}</div>
                    {candidate.duration_notes && (
                      <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>{candidate.duration_notes}</div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          {caveatText && (
            <div className="rec-caveat">
              <span>⚠ {caveatTruncated ? caveatText.slice(0, 200) + '...' : caveatText}</span>
              {caveatText.length > 200 && (
                <button
                  className="rec-caveat-toggle"
                  onClick={(e) => { e.stopPropagation(); setShowFullCaveat(!showFullCaveat) }}
                >
                  {showFullCaveat ? 'less' : 'more'}
                </button>
              )}
            </div>
          )}

          {/* Footer metrics — from display config or fallback */}
          {candidate.provisions_quarter !== null && candidate.provisions_quarter !== undefined && (
            <>
              <div style={{
                display: 'flex', gap: '0.6rem', padding: '0.5rem 0', marginTop: '0.5rem',
                borderTop: '1px solid var(--border-subtle)', fontSize: '0.8rem', color: 'var(--text-muted)',
                alignItems: 'center', flexWrap: 'wrap',
              }}>
                <span>{candidate.provisions_quarter.toLocaleString()} deployments (last 90d)</span>
                {candidate.sales_impact && candidate.sales_impact !== 'low' && (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                    <span style={{
                      padding: '0.1rem 0.4rem', borderRadius: '3px', fontSize: '0.75rem',
                      background: candidate.sales_impact === 'high' ? 'var(--score-green-bg)' : 'var(--score-amber-bg)',
                      color: candidate.sales_impact === 'high' ? 'var(--score-green)' : 'var(--score-amber)',
                    }}>
                      {candidate.sales_impact === 'high' ? '$ High Sales Impact' : '$ Moderate Sales Impact'}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setShowSalesInfo(!showSalesInfo) }}
                      style={{ cursor: 'pointer', fontSize: '0.7rem', opacity: 0.6, userSelect: 'none', background: 'transparent', border: 'none', padding: 0, color: 'inherit' }}
                      aria-label={showSalesInfo ? 'Hide sales impact details' : 'Show sales impact details'}
                    >ⓘ</button>
                  </span>
                )}
                {isComplete && (tier === 'green' || tier === 'yellow') && (
                  selected ? (
                    <span style={{
                      padding: '0.1rem 0.4rem', borderRadius: '3px', fontSize: '0.75rem',
                      background: 'var(--score-green-bg)', color: 'var(--score-green)',
                    }}>
                      ★ Best fit
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="btn-best-fit-badge"
                      title="Helps us improve recommendations by tracking which results are most useful"
                      onClick={(e) => { e.stopPropagation(); handleSelect() }}
                      style={{
                        padding: '0.1rem 0.4rem', borderRadius: '3px', fontSize: '0.75rem',
                        background: 'transparent', color: 'var(--score-green)',
                        border: '1px solid var(--score-green)', cursor: 'pointer',
                      }}
                    >
                      ★ Best fit?
                    </button>
                  )
                )}
              </div>
              {showSalesInfo && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '0 0 0.5rem' }}>
                  Based on closed sales opportunities linked to deployments of this asset over the trailing year.
                </div>
              )}
            </>
          )}

          {/* Links — from display config or fallback */}
          <div className="rec-footer">
            {display?.links ? (
              display.links.map((link, i) => (
                <a
                  key={i}
                  href={buildUrl(link.url_template, candidate)}
                  target="_blank" rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  {link.label}
                </a>
              ))
            ) : (
              <>
                {candidate.ci_name && (
                  <a
                    href={buildUrl('catalog', candidate)}
                    target="_blank" rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    View in RHDP Catalog
                  </a>
                )}
                <a
                  href={buildUrl('browse', candidate)}
                  target="_blank" rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  View in RCARS
                </a>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
