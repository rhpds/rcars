import type { ChatBlock } from '../chatTypes'

interface OverlapTableBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

interface OverlapNeighbor {
  content_id: string
  display_name: string
  ci_name?: string
  shared_products?: number
  shared_topics?: number
  verdict?: string
  recommendation?: string
  stage?: string
}


const verdictStyle = (v?: string) => {
  if (v === 'redundant') return { bg: 'var(--score-red-bg)', color: 'var(--score-red)' }
  if (v === 'complementary') return { bg: 'var(--score-amber-bg)', color: 'var(--score-amber)' }
  if (v === 'differentiated') return { bg: 'var(--score-green-bg, #e8f5e9)', color: 'var(--score-green, #2e7d32)' }
  return { bg: 'var(--bg-card)', color: 'var(--text-muted)' }
}

export function OverlapTableBlock({ block }: OverlapTableBlockProps) {
  const anchor = block.data.anchor as { display_name: string } | undefined
  const neighbors = (block.data.neighbors || []) as OverlapNeighbor[]

  if (!anchor) return null

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
        Overlaps with: {anchor.display_name}
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
              <th style={{ padding: '8px 12px', textAlign: 'center' }}>Verdict</th>
              <th style={{ padding: '8px 12px', textAlign: 'right' }}>Products</th>
              <th style={{ padding: '8px 12px', textAlign: 'right' }}>Topics</th>
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Stage</th>
            </tr>
          </thead>
          <tbody>
            {neighbors.map((n, i) => {
              const vs = verdictStyle(n.verdict)
              return (
                <tr key={i} style={{ borderTop: i > 0 ? '1px solid var(--border-subtle)' : undefined }}>
                  <td style={{ padding: '10px 12px' }}>
                    {n.display_name ? (
                      <a href={'/browse?search=' + encodeURIComponent(n.display_name) +
                               (n.stage && n.stage !== 'prod' ? '&stage=prod,' + encodeURIComponent(n.stage) : '')}
                         target="_blank" rel="noopener noreferrer"
                         style={{ color: 'var(--text-link)', textDecoration: 'none' }}>
                        {n.display_name}
                      </a>
                    ) : n.display_name}
                  </td>
                  <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                    {n.verdict && (
                      <span style={{
                        padding: '2px 6px',
                        borderRadius: '3px',
                        fontSize: '11px',
                        background: vs.bg,
                        color: vs.color,
                      }}>
                        {n.verdict}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--ff-mono)' }}>
                    {n.shared_products ?? '—'}
                  </td>
                  <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--ff-mono)' }}>
                    {n.shared_topics ?? '—'}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{n.stage || '—'}</td>
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
        <a href="/analysis/overlap" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--text-link)' }}>
          Open in Content Analysis → Overlap
        </a>
      </div>
    </div>
  )
}
