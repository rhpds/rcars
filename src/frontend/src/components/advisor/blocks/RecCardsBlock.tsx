import { useState } from 'react'
import { RecCardList } from '../RecCardList'
import type { ChatBlock } from '../chatTypes'
import type { StreamCandidate } from '../../../hooks/useJobStream'

interface RecCardsBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

const CATEGORY_LABELS: Record<string, string> = {
  hands_on: 'Hands-on Labs & Demos',
  architecture: 'Architectures',
  _default: 'Results',
}

export function RecCardsBlock({ block, sessionId, turnIndex }: RecCardsBlockProps) {
  const candidates = (block.data.candidates || []) as StreamCandidate[]
  const contentGaps = (block.data.content_gaps || []) as string[]

  const categories = new Map<string, StreamCandidate[]>()
  for (const c of candidates) {
    const key = c.content_type === 'architecture' ? 'architecture'
      : (c.content_type === 'lab' || c.content_type === 'demo' || c.content_type === 'sandbox') ? 'hands_on'
      : '_default'
    const list = categories.get(key) || []
    list.push(c)
    categories.set(key, list)
  }

  const categoryKeys = Array.from(categories.keys())
  const [activeTab, setActiveTab] = useState(categoryKeys[0] || '_default')
  const showTabs = categoryKeys.length > 1

  return (
    <div>
      {showTabs && (
        <div style={{ display: 'flex', gap: '0', borderBottom: '2px solid var(--border-subtle)', marginBottom: '12px' }}>
          {categoryKeys.map(key => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              style={{
                background: 'transparent', border: 'none', cursor: 'pointer',
                padding: '8px 16px', fontSize: '13px', fontWeight: 600,
                color: activeTab === key ? 'var(--text-primary)' : 'var(--text-muted)',
                borderBottom: activeTab === key ? '2px solid var(--score-green)' : '2px solid transparent',
                marginBottom: '-2px',
              }}
            >
              {CATEGORY_LABELS[key] || key} ({(categories.get(key) || []).length})
            </button>
          ))}
        </div>
      )}

      <RecCardList
        candidates={categories.get(activeTab) || []}
        isComplete
        sessionId={sessionId}
        turnIndex={turnIndex}
      />

      {contentGaps.length > 0 && (
        <div style={{
          marginTop: '16px', padding: '12px', background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)',
          fontSize: '13px', color: 'var(--text-muted)',
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
