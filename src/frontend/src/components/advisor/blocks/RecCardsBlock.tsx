import { RecCardList } from '../RecCardList'
import type { ChatBlock } from '../chatTypes'
import type { StreamCandidate } from '../../../hooks/useJobStream'

interface RecCardsBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

export function RecCardsBlock({ block, sessionId }: RecCardsBlockProps) {
  const candidates = (block.data.candidates || []) as StreamCandidate[]
  const contentGaps = (block.data.content_gaps || []) as string[]

  // Separate lab/demo from other content types
  const primaryCandidates = candidates.filter(c =>
    !c.content_type || c.content_type === 'lab' || c.content_type === 'demo'
  )
  const secondaryCandidates = candidates.filter(c =>
    c.content_type && c.content_type !== 'lab' && c.content_type !== 'demo'
  )

  return (
    <div>
      <RecCardList candidates={primaryCandidates} isComplete sessionId={sessionId} />

      {secondaryCandidates.length > 0 && (
        <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
            Also similar, though not labs:
          </div>
          <RecCardList candidates={secondaryCandidates} isComplete sessionId={sessionId} />
        </div>
      )}

      {contentGaps.length > 0 && (
        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          fontSize: '13px',
          color: 'var(--text-muted)',
        }}>
          <div style={{ fontWeight: 600, marginBottom: '6px' }}>Content gaps identified:</div>
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {contentGaps.map((gap, i) => <li key={i}>{gap}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
