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
  why_it_fits: string | null
  how_to_use: string | null
  suggested_format: string | null
  duration_notes: string | null
  caveats: string | null
}

interface RecCardProps {
  candidate: Candidate
  sessionId?: string
  turnIndex?: number
  chosenCiName?: string
  isComplete: boolean
}

export function RecCard({ candidate, sessionId, turnIndex, chosenCiName, isComplete }: RecCardProps) {
  const [expanded, setExpanded] = useState(candidate.tier === 'green')
  const [selected, setSelected] = useState(chosenCiName === candidate.ci_name)

  const score = candidate.relevance_score ?? candidate.vector_similarity_pct ?? 0
  const tier = candidate.tier as 'green' | 'yellow' | 'white'

  const handleSelect = async () => {
    if (!sessionId || turnIndex == null) return
    await api.selectRecommendation(sessionId, turnIndex, candidate.ci_name)
    setSelected(true)
  }

  return (
    <LcarsCard tier={tier} onClick={() => setExpanded(!expanded)}>
      <div className="rec-card-header">
        <span className="rec-score">{score}%</span>
        <div>
          <div className="rec-title">{candidate.display_name}</div>
          <div className="rec-meta">
            {candidate.stage} · {candidate.ci_name}
          </div>
        </div>
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
          {candidate.how_to_use && (
            <div className="rec-analysis-row">
              <span className="rec-analysis-label">How to use</span>
              <span className="rec-analysis-value">{candidate.how_to_use}</span>
            </div>
          )}
          {candidate.suggested_format && (
            <div className="rec-pill-row">
              <span className="rec-pill pill-format">{candidate.suggested_format}</span>
              {candidate.duration_notes && <span className="rec-pill">{candidate.duration_notes}</span>}
            </div>
          )}
          {candidate.caveats && (
            <div className="rec-caveat">Caveat: {candidate.caveats}</div>
          )}
          {isComplete && (tier === 'green' || tier === 'yellow') && (
            <div style={{ marginTop: '10px' }}>
              {selected ? (
                <span style={{ color: '#5cb85c', fontSize: '14px' }}>✓ Selected</span>
              ) : (
                <button
                  className="btn-curator"
                  onClick={(e) => { e.stopPropagation(); handleSelect() }}
                >
                  This fits best
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </LcarsCard>
  )
}
