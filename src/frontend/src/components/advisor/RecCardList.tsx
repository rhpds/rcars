import { useState } from 'react'
import { RecCard } from './RecCard'
import { StreamCandidate } from '../../hooks/useJobStream'

interface RecCardListProps {
  candidates: StreamCandidate[]
  isComplete: boolean
  streamPhase?: string
  sessionId?: string
}

export function RecCardList({ candidates, isComplete, streamPhase, sessionId }: RecCardListProps) {
  const green = candidates.filter(c => c.tier === 'green')
  const yellow = candidates.filter(c => c.tier === 'yellow')
  const white = candidates.filter(c => c.tier === 'white' || c.tier === 'pending')

  // During streaming before triage, show flat list
  if (streamPhase === 'vector_search') {
    return (
      <>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: '8px 0 4px' }}>
          Candidates ({candidates.length})
        </div>
        {candidates.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={false} />)}
      </>
    )
  }

  // During streaming after triage but before rationale, show all scored candidates visibly
  if (!isComplete && green.length === 0 && yellow.length > 0) {
    return (
      <>
        <div style={{ fontSize: '11px', color: 'var(--score-amber)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: '8px 0 4px' }}>
          Evaluating top {Math.min(yellow.length, 5)} matches...
        </div>
        {yellow.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={false} />)}
        {white.length > 0 && (
          <CollapsibleTier label={`Also reviewed (${white.length})`} candidates={white} isComplete={false} />
        )}
      </>
    )
  }

  return (
    <>
      {green.length > 0 && (
        <div style={{ fontSize: '12px', color: 'var(--score-green)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: '8px 0 4px' }}>Best fit ({green.length})</div>
      )}
      {green.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={isComplete} sessionId={sessionId} turnIndex={0} />)}

      {yellow.length > 0 && (
        <CollapsibleTier label={`Other options (${yellow.length})`} candidates={yellow} isComplete={isComplete} sessionId={sessionId} />
      )}

      {white.length > 0 && (
        <CollapsibleTier label={`Also reviewed (${white.length})`} candidates={white} isComplete={isComplete} sessionId={sessionId} />
      )}
    </>
  )
}

function CollapsibleTier({ label, candidates, isComplete, sessionId }: {
  label: string
  candidates: StreamCandidate[]
  isComplete: boolean
  sessionId?: string
}) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: 'transparent', border: 'none', color: 'var(--text-muted)',
          cursor: 'pointer', fontSize: '14px', padding: '8px 0',
        }}
      >
        {open ? '▾' : '▸'} {label}
      </button>
      {open && candidates.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={isComplete} sessionId={sessionId} turnIndex={0} />)}
    </div>
  )
}
