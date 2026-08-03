import type { ChatBlock } from '../chatTypes'

interface OverlapTableBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

interface OverlapNeighbor {
  display_name: string
  similarity_pct: number
  relationship_type?: string
  stage?: string
  shared_products?: string[]
  why?: string
}

export function OverlapTableBlock({ block }: OverlapTableBlockProps) {
  const anchor = block.data.anchor as { display_name: string } | undefined
  const neighbors = (block.data.neighbors || []) as OverlapNeighbor[]

  if (!anchor) return null

  const relationshipBadgeStyle = (type?: string) => {
    if (type === 'overlap') return { bg: 'var(--badge-amber-bg)', color: 'var(--badge-amber-text)' }
    if (type === 'related') return { bg: 'var(--badge-blue-bg)', color: 'var(--badge-blue-text)' }
    return { bg: 'var(--bg-card)', color: 'var(--text-muted)' }
  }

  return (
    <div style={{
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-sm)',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '12px',
        background: 'var(--bg-card)',
        borderBottom: '1px solid var(--border-subtle)',
        fontWeight: 600,
        fontSize: '14px',
      }}>
        Similar to: {anchor.display_name}
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%',
          fontSize: '13px',
          borderCollapse: 'collapse',
        }}>
          <thead style={{ background: 'var(--bg-subtle)', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            <tr>
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Item</th>
              <th style={{ padding: '8px 12px', textAlign: 'right' }}>Similarity</th>
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Type</th>
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Stage</th>
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Shared Products</th>
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Why</th>
            </tr>
          </thead>
          <tbody>
            {neighbors.map((n, i) => {
              const badgeStyle = relationshipBadgeStyle(n.relationship_type)
              return (
                <tr key={i} style={{ borderTop: i > 0 ? '1px solid var(--border-subtle)' : undefined }}>
                  <td style={{ padding: '10px 12px' }}>{n.display_name}</td>
                  <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--ff-mono)' }}>
                    {n.similarity_pct}%
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {n.relationship_type && (
                      <span style={{
                        padding: '2px 6px',
                        borderRadius: '3px',
                        fontSize: '11px',
                        background: badgeStyle.bg,
                        color: badgeStyle.color,
                      }}>
                        {n.relationship_type}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{n.stage || '—'}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                    {n.shared_products && n.shared_products.length > 0 ? n.shared_products.join(', ') : '—'}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '12px' }}>
                    {n.why || '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div style={{
        padding: '10px 12px',
        background: 'var(--bg-subtle)',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: '12px',
      }}>
        <a href="/analysis/overlap" style={{ color: 'var(--text-link)' }}>
          Open in Content Analysis → Overlap
        </a>
      </div>
    </div>
  )
}
