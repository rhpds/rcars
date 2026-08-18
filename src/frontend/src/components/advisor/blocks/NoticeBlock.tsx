import type { ChatBlock } from '../chatTypes'

interface NoticeBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

export function NoticeBlock({ block }: NoticeBlockProps) {
  const kind = block.data.kind as string | undefined

  const kindLabels: Record<string, { label: string; icon: string }> = {
    out_of_scope: { label: 'Out of scope', icon: '⚠' },
    role_redirect: { label: 'Restricted', icon: '🔒' },
    clarify: { label: 'Needs clarification', icon: '❓' },
    scope_expanded: { label: 'Expanded search', icon: '🔎' },
  }

  const kindInfo = (kind ? kindLabels[kind] : undefined) ?? { label: 'Notice', icon: 'ℹ' }
  const message = block.data.message as string | undefined

  return (
    <div style={{
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-sm)',
      padding: '12px 16px',
      background: 'var(--bg-subtle)',
      fontSize: '13px',
      color: 'var(--text-muted)',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
    }}>
      <span style={{ fontSize: '16px' }}>{kindInfo.icon}</span>
      <span style={{ fontWeight: 600 }}>{kindInfo.label}</span>
      {message && <span>{message}</span>}
    </div>
  )
}
