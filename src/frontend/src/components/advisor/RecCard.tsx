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
  booth_demo: 'Booth Demo',
  presentation: 'Presentation',
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

  const metaParts: string[] = [candidate.ci_name]
  if (candidate.suggested_format) {
    metaParts.push(FORMAT_LABELS[candidate.suggested_format] || candidate.suggested_format.replace(/_/g, ' '))
  }
  if (candidate.duration_min) {
    metaParts.push(candidate.duration_source === 'curated' ? 'Curated duration' : 'AI estimate')
  }

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
              <span style={{
                display: 'inline-block',
                background: candidate.stage === 'dev' ? '#2a4a6a' : '#5a4a1a',
                color: candidate.stage === 'dev' ? '#99ccff' : '#ffcc66',
                borderRadius: '10px', padding: '2px 8px', fontSize: '10px',
                fontWeight: 600, marginRight: '6px',
              }}>{candidate.stage.toUpperCase()}</span>
            )}
            {(candidate.catalog_namespace?.startsWith('zt-') || candidate.ci_name.startsWith('zt-')) && (
              <span style={{ display: 'inline-block', background: '#1a3a2a', color: '#66cc99', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginRight: '6px' }}>ZT</span>
            )}
            {metaParts.join(' · ')}
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
            <div className="rec-analysis">
              <div className="rec-analysis-row">
                <span className="rec-analysis-label">Why it fits</span>
                <span className="rec-analysis-value">{candidate.why_it_fits}</span>
              </div>
            </div>
          )}

          {tier === 'green' && candidate.learning_objectives && candidate.learning_objectives.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <div style={{ fontSize: '11px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>Learning Objectives</div>
              <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12px', color: '#aaa', lineHeight: '1.5' }}>
                {candidate.learning_objectives.slice(0, 5).map((obj, i) => (
                  <li key={i}>{obj}</li>
                ))}
              </ul>
            </div>
          )}

          {candidate.how_to_use && (
            <div className="rec-analysis-row" style={{ marginTop: '8px' }}>
              <span className="rec-analysis-label">How to use</span>
              <span className="rec-analysis-value">{candidate.how_to_use}</span>
            </div>
          )}

          {candidate.duration_notes && (
            <div style={{ fontSize: '12px', color: '#777', marginTop: '4px', paddingLeft: '93px' }}>
              {candidate.duration_notes}
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

          <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <a
              href={catalogUrl(candidate.ci_name, candidate.catalog_namespace)}
              target="_blank" rel="noopener noreferrer"
              style={{ color: '#73bcf7', fontSize: '13px' }}
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
