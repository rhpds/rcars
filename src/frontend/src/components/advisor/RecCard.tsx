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

function formatSuggestedFormat(raw: string): string {
  const map: Record<string, string> = {
    hands_on_lab: 'Hands-on Lab',
    booth_demo: 'Booth Demo',
    presentation: 'Presentation',
  }
  return map[raw] || raw.replace(/_/g, ' ')
}

export function RecCard({ candidate, sessionId, turnIndex, chosenCiName, isComplete }: RecCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [selected, setSelected] = useState(chosenCiName === candidate.ci_name)
  const [showFullCaveat, setShowFullCaveat] = useState(false)
  const [showObjectives, setShowObjectives] = useState(false)

  const score = candidate.relevance_score ?? candidate.vector_similarity_pct ?? 0
  const tier = candidate.tier as 'green' | 'yellow' | 'white'

  const handleSelect = async () => {
    if (!sessionId || turnIndex == null) return
    await api.selectRecommendation(sessionId, turnIndex, candidate.ci_name)
    setSelected(true)
  }

  const caveatText = candidate.caveats || ''
  const caveatTruncated = caveatText.length > 200 && !showFullCaveat

  const hasMetadata = candidate.suggested_format || candidate.duration_min
  const durationLabel = candidate.duration_min
    ? `~${candidate.duration_min} min (${candidate.duration_source === 'curated' ? 'curated' : 'AI estimate'})`
    : null

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
        <div>
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
            {candidate.ci_name}
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

          {(candidate.how_to_use || candidate.duration_notes) && (
            <div className="rec-analysis-row">
              <span className="rec-analysis-label">How to use</span>
              <span className="rec-analysis-value">
                {candidate.how_to_use}
                {candidate.how_to_use && candidate.duration_notes && ' '}
                {candidate.duration_notes && (
                  <span style={{ color: '#888' }}>{candidate.duration_notes}</span>
                )}
              </span>
            </div>
          )}

          {hasMetadata && (
            <div className="rec-metadata-line">
              {candidate.suggested_format && formatSuggestedFormat(candidate.suggested_format)}
              {candidate.suggested_format && durationLabel && ' · '}
              {durationLabel}
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

          {tier === 'green' && candidate.learning_objectives && candidate.learning_objectives.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <div
                className="rec-objectives-toggle"
                onClick={(e) => { e.stopPropagation(); setShowObjectives(!showObjectives) }}
              >
                {showObjectives ? '▾' : '▸'} Learning objectives ({candidate.learning_objectives.length})
              </div>
              {showObjectives && (
                <ul style={{ margin: '4px 0 0', paddingLeft: '16px', fontSize: '12px', color: '#aaa', lineHeight: '1.5' }}>
                  {candidate.learning_objectives.slice(0, 5).map((obj, i) => (
                    <li key={i}>{obj}</li>
                  ))}
                </ul>
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
