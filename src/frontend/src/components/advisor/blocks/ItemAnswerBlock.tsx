import type { ChatBlock } from '../chatTypes'

interface ItemAnswerBlockProps {
  block: ChatBlock
}

export function ItemAnswerBlock({ block }: ItemAnswerBlockProps) {
  const answer = block.data.answer as string | undefined
  const item = block.data.item as { display_name?: string; content_id?: string; content_type?: string } | undefined
  const sources = (block.data.sources || []) as string[]

  if (!answer) return null

  return (
    <div style={{
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-sm)',
      padding: '16px',
      background: 'var(--bg-card)',
    }}>
      {item?.display_name && (
        <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>
          {item.display_name}
        </h3>
      )}

      <div style={{
        fontSize: '13px',
        lineHeight: '1.6',
        color: 'var(--text-primary)',
        whiteSpace: 'pre-wrap',
      }}>
        {answer}
      </div>

      <div style={{
        marginTop: '12px',
        paddingTop: '8px',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: '11px',
        color: 'var(--text-muted)',
      }}>
        Based on stored analysis{sources.length > 0 && ` (${sources.map(s => s.replace(/_/g, ' ')).join(', ')})`}
        {' — '}answers may not reflect the full content.
      </div>
    </div>
  )
}
