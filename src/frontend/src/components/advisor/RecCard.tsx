import { useState } from 'react'
import { LcarsCard } from '../lcars'
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
  hands_on_lab: { bg: '#1a2a3a', color: '#73bcf7' },
  demo: { bg: '#2a2a1a', color: '#e8a838' },
}

export function RecCard({ candidate, sessionId, turnIndex, chosenCiName, isComplete }: RecCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [selected, setSelected] = useState(chosenCiName === candidate.ci_name)
  const [showFullCaveat, setShowFullCaveat] = useState(false)

  const score = candidate.relevance_score ?? candidate.vector_similarity_pct ?? 0
  const tier = candidate.tier as 'green' | 'yellow' | 'white'

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
  const formatStyle = FORMAT_COLORS[formatKey] || { bg: '#1a2a3a', color: '#73bcf7' }

  return (
    <LcarsCard tier={tier}>
      <div
        className="rec-card-header"
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(!expanded) } }}
        style={{ cursor: 'pointer' }}
      >
        <span className="rec-score">{score}%</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="rec-title">{candidate.display_name}</div>
          <div className="rec-meta">
            {candidate.stage !== 'prod' && (
              <span className="rec-badge" style={{ background: candidate.stage === 'dev' ? '#2a4a6a' : '#5a4a1a', color: candidate.stage === 'dev' ? '#99ccff' : '#ffcc66' }}>
                {candidate.stage.toUpperCase()}
              </span>
            )}
            {(candidate.catalog_namespace?.startsWith('zt-') || candidate.ci_name.startsWith('zt-')) && (
              <span className="rec-badge" style={{ background: '#1a3a2a', color: '#66cc99' }}>ZT</span>
            )}
            {formatLabel && (
              <span className="rec-badge" style={{ background: formatStyle.bg, color: formatStyle.color }}>{formatLabel}</span>
            )}
            <span>{candidate.ci_name}</span>
            {durationSourceLabel && (
              <><span style={{ color: '#444', margin: '0 4px' }}>·</span><span>{durationSourceLabel}</span></>
            )}
          </div>
        </div>
        {candidate.duration_min && (
          <span style={{ fontSize: '14px', color: '#999', fontWeight: 500, flexShrink: 0 }}>
            ~{candidate.duration_min} min
          </span>
        )}
        <span className="rec-expand-hint">{expanded ? '▾' : '▸'}</span>
      </div>

      {expanded && (
        <div className="rec-expanded">
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
                  <div style={{ color: '#777', marginTop: '2px' }}>{candidate.duration_notes}</div>
                )}
              </div>
            </div>
          )}

          {!candidate.how_to_use && candidate.duration_notes && (
            <div className="rec-row">
              <span className="rec-row-label">Timing</span>
              <span className="rec-row-value" style={{ color: '#777' }}>{candidate.duration_notes}</span>
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
            <div style={{
              display: 'flex', gap: '1rem', padding: '0.5rem 0', marginTop: '0.5rem',
              borderTop: '1px solid #2a2d35', fontSize: '0.8rem', color: '#8b949e',
            }}>
              <span>{candidate.provisions_quarter.toLocaleString()} deployments (last 90d)</span>
              {candidate.sales_impact && candidate.sales_impact !== 'low' && (
                <span title="Based on closed sales opportunities linked to provisions of this asset over the trailing year."
                  style={{
                    padding: '0.1rem 0.4rem', borderRadius: '3px', fontSize: '0.75rem',
                    background: candidate.sales_impact === 'high' ? '#1a4731' : '#3d2e00',
                    color: candidate.sales_impact === 'high' ? '#3e8635' : '#e8a838',
                    cursor: 'help',
                  }}>
                  {candidate.sales_impact === 'high' ? 'High Sales Impact' : 'Moderate Sales Impact'}
                </span>
              )}
            </div>
          )}

          <div className="rec-footer">
            <a
              href={catalogUrl(candidate.ci_name, candidate.catalog_namespace)}
              target="_blank" rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              View in RHDP Catalog
            </a>
            {isComplete && (tier === 'green' || tier === 'yellow') && (
              selected ? (
                <span style={{ color: '#5cb85c', fontSize: '13px', fontWeight: 500 }}>✓ Best fit</span>
              ) : (
                <button
                  className="btn-best-fit"
                  title="Helps us improve recommendations by tracking which results are most useful"
                  onClick={(e) => { e.stopPropagation(); handleSelect() }}
                >
                  ★ Best fit
                </button>
              )
            )}
          </div>
        </div>
      )}
    </LcarsCard>
  )
}
