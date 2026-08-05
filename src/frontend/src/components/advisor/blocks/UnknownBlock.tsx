import { useState } from 'react'
import type { ChatBlock } from '../chatTypes'

interface UnknownBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

export function UnknownBlock({ block }: UnknownBlockProps) {
  const [open, setOpen] = useState(false)

  return (
    <div style={{
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-sm)',
      padding: '10px',
      color: 'var(--text-muted)',
      fontSize: '13px',
    }}>
      This response includes a "{block.type}" view this version of the UI can't render yet.
      <button
        onClick={() => setOpen(!open)}
        style={{
          marginLeft: '8px',
          cursor: 'pointer',
          background: 'transparent',
          border: '1px solid var(--border-subtle)',
          borderRadius: '3px',
          padding: '2px 6px',
          color: 'var(--text-link)',
          fontSize: '12px',
        }}
      >
        view data
      </button>
      {open && (
        <pre style={{
          fontSize: '11px',
          overflow: 'auto',
          marginTop: '8px',
          padding: '8px',
          background: 'var(--bg-page)',
          borderRadius: '3px',
        }}>
          {JSON.stringify(block.data, null, 2)}
        </pre>
      )}
    </div>
  )
}
