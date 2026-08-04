import type { ChatBlock } from '../chatTypes'

interface PerformanceTableBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

interface PerformanceRow {
  content_id?: string
  display_name: string
  provisions: number
  unique_users?: number
  last_activity?: string | null
  cost_per_provision: number | null
  sales_impact?: string
  score?: number
}

export function PerformanceTableBlock({ block }: PerformanceTableBlockProps) {
  const window = block.data.window as string | undefined
  const rows = (block.data.rows || []) as PerformanceRow[]

  const scoreColor = (score: number) => {
    if (score >= 55) return 'var(--score-green)'
    if (score >= 35) return 'var(--score-amber)'
    return 'var(--score-red)'
  }

  const scoreBg = (score: number) => {
    if (score >= 55) return 'var(--score-green-bg)'
    if (score >= 35) return 'var(--score-amber-bg)'
    return 'var(--score-red-bg)'
  }

  return (
    <div style={{
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-sm)',
      overflow: 'hidden',
    }}>
      {window && (
        <div style={{
          padding: '10px 12px',
          background: 'var(--bg-card)',
          borderBottom: '1px solid var(--border-subtle)',
          fontSize: '13px',
          color: 'var(--text-muted)',
        }}>
          Last {window}
        </div>
      )}

      <div style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%',
          fontSize: '13px',
          borderCollapse: 'collapse',
        }}>
          <thead style={{ background: 'var(--bg-subtle)', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            <tr>
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Item</th>
              <th style={{ padding: '8px 12px', textAlign: 'right' }}>Provisions</th>
              <th style={{ padding: '8px 12px', textAlign: 'right' }}>Unique Users</th>
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Last Provisioned</th>
              <th style={{ padding: '8px 12px', textAlign: 'right' }}>Cost/Provision</th>
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Sales Impact</th>
              <th style={{ padding: '8px 12px', textAlign: 'center' }}>Score</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} style={{ borderTop: i > 0 ? '1px solid var(--border-subtle)' : undefined }}>
                <td style={{ padding: '10px 12px' }}>{row.display_name}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--ff-mono)' }}>
                  {row.provisions.toLocaleString()}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--ff-mono)' }}>
                  {row.unique_users != null ? row.unique_users.toLocaleString() : '—'}
                </td>
                <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                  {row.last_activity || '—'}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--ff-mono)' }}>
                  {row.cost_per_provision != null ? `$${row.cost_per_provision.toFixed(2)}` : '—'}
                </td>
                <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                  {row.sales_impact || '—'}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                  {row.score != null ? (
                    <span style={{
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 600,
                      fontFamily: 'var(--ff-mono)',
                      background: scoreBg(row.score),
                      color: scoreColor(row.score),
                    }}>
                      {row.score}
                    </span>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{
        padding: '10px 12px',
        background: 'var(--bg-subtle)',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: '12px',
      }}>
        <a
          href={rows.length === 1
            ? `/analysis/performance?search=${encodeURIComponent(rows[0].display_name)}`
            : '/analysis/performance'}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--text-link)' }}
        >
          Open Performance Analysis
        </a>
      </div>
    </div>
  )
}
