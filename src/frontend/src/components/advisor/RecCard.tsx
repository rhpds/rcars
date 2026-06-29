import { useState } from 'react'
import { api } from '../../services/api'

interface Candidate {
  ci_name: string
  display_name: string
  tier: string
  relevance_score: number | null
  vector_similarity_pct: number | null
  stage: string
  catalog_namespace: string
  learning_objectives: string[]
  why_it_fits: string | null
  how_to_use: string | null
  suggested_format: string | null
  duration_notes: string | null
  caveats: string | null
  duration_min: number | null
  duration_source: string | null
  provisions_quarter?: number | null
  sales_impact?: string | null
}

interface RecCardProps {
  candidate: Candidate
  sessionId?: string
  turnIndex?: number
  chosenCiName?: string
  isComplete: boolean
}

function catalogUrl(ciName: string, namespace: string): string {
  const ns = namespace || 'babylon-catalog-prod'
  return `https://demo.redhat.com/catalog?item=${ns}/${ciName}`
}

const FORMAT_LABELS: Record<string, string> = {
  hands_on_lab: 'Hands-on Lab',
  demo: 'Demo',
}

const FORMAT_COLORS: Record<string, { bg: string; color: string }> = {
  hands_on_lab: { bg: 'var(--badge-blue-bg)', color: 'var(--badge-blue-text)' },
  demo: { bg: 'var(--badge-amber-bg)', color: 'var(--badge-amber-text)' },
}

export function RecCard({ candidate, sessionId, turnIndex, chosenCiName, isComplete }: RecCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [selected, setSelected] = useState(chosenCiName === candidate.ci_name)
  const [showFullCaveat, setShowFullCaveat] = useState(false)
  const [showSalesInfo, setShowSalesInfo] = useState(false)

  const score = Math.min(100, Math.max(0, candidate.relevance_score ?? candidate.vector_similarity_pct ?? 0))
  const tier = candidate.tier as 'green' | 'yellow' | 'white'
  const tierClass = tier === 'green' ? 'tier-green' : tier === 'yellow' ? 'tier-yellow' : ''

  const handleSelect = async () => {
    if (!sessionId || turnIndex == null) return
    await api.selectRecommendation(sessionId, turnIndex, candidate.ci_name)
    setSelected(true)
  }

  const caveatText = candidate.caveats || ''
  const caveatTruncated = caveatText.length > 200 && !showFullCaveat

  const durationSourceLabel = candidate.duration_min
    ? (candidate.duration_source === 'curated' ? 'Curated duration' : 'AI duration estimate')
    : null

  const formatKey = candidate.suggested_format || ''
  const formatLabel = FORMAT_LABELS[formatKey] || (formatKey ? formatKey.replace(/_/g, ' ') : null)
  const formatStyle = FORMAT_COLORS[formatKey] || { bg: 'var(--badge-blue-bg)', color: 'var(--badge-blue-text)' }

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
            {candidate.stage !== 'prod' && (
              <span className="rec-badge" style={{ background: candidate.stage === 'dev' ? 'var(--badge-blue-bg)' : 'var(--badge-amber-bg)', color: candidate.stage === 'dev' ? 'var(--badge-blue-text)' : 'var(--badge-amber-text)' }}>
                {candidate.stage.toUpperCase()}
              </span>
            )}
            {(candidate.catalog_namespace?.startsWith('zt-') || candidate.ci_name.startsWith('zt-')) && (
              <span className="rec-badge" style={{ background: 'var(--score-green-bg)', color: 'var(--score-green)' }}>ZT</span>
            )}
            {formatLabel && (
              <span className="rec-badge" style={{ background: formatStyle.bg, color: formatStyle.color }}>{formatLabel}</span>
            )}
            <span style={{ fontFamily: 'var(--ff-mono)' }}>{candidate.ci_name}</span>
            {durationSourceLabel && (
              <><span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>·</span><span>{durationSourceLabel}</span></>
            )}
          </div>
        </div>
        {candidate.duration_min && (
          <span style={{ fontSize: '14px', color: 'var(--text-secondary)', fontWeight: 500, flexShrink: 0, fontFamily: 'var(--ff-mono)' }}>
            ~{candidate.duration_min} min
          </span>
        )}
        <span className="rec-expand-hint">{expanded ? '▾' : '▸'}</span>
      </div>

      {expanded && (
        <div className="rec-expanded" style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
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

          {!candidate.how_to_use && candidate.duration_notes && (
            <div className="rec-row">
              <span className="rec-row-label">Timing</span>
              <span className="rec-row-value" style={{ color: 'var(--text-muted)' }}>{candidate.duration_notes}</span>
            </div>
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
                    <span
                      onClick={(e) => { e.stopPropagation(); setShowSalesInfo(!showSalesInfo) }}
                      style={{ cursor: 'pointer', fontSize: '0.7rem', opacity: 0.6, userSelect: 'none' }}
                    >ⓘ</span>
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
                    <span
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
                    </span>
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

          <div className="rec-footer">
            <a
              href={catalogUrl(candidate.ci_name, candidate.catalog_namespace)}
              target="_blank" rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              View in RHDP Catalog
            </a>
            <a
              href={'/browse?search=' + encodeURIComponent(candidate.display_name)}
              target="_blank" rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              View in RCARS
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
