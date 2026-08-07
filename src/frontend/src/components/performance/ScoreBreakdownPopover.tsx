import type { ScoreBreakdown } from '../../services/api'

// Shared formatting helpers
export const fmt = (v: number | string) => {
  const n = typeof v === 'string' ? parseFloat(v) || 0 : v
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toFixed(0)}`
}

export const num = (v: unknown): number => typeof v === 'number' ? v : parseFloat(String(v)) || 0

export const fmtRoi = (amount: number | string, cost: number | string) => {
  const a = num(amount), c = num(cost)
  if (c <= 0 || a <= 0) return '—'
  return `${(a / c).toFixed(1)}x`
}

// Performance score colors (inverted: high = green)
export const scoreColor = (score: number) => score >= 55 ? 'var(--score-green)' : score >= 35 ? 'var(--score-amber)' : 'var(--score-red)'
export const scoreBg = (score: number) => score >= 55 ? 'var(--score-green-bg)' : score >= 35 ? 'var(--score-amber-bg)' : 'var(--score-red-bg)'

export function ScoreBreakdownPopover({ breakdown, onClose, anchorRect }: { breakdown: ScoreBreakdown; onClose: () => void; anchorRect: DOMRect | null }) {
  const factorLabels: Record<string, string> = { usage: 'Usage', pipeline: 'Pipeline', sales: 'Closed Sales', roi: 'Cost Efficiency' }
  const levelColor = (level: string) => {
    if (level === 'strong') return 'var(--score-green)'
    if (level === 'moderate') return 'var(--score-amber)'
    if (level === 'low') return 'var(--score-red)'
    return 'var(--score-red)'  // 'none'
  }

  const popoverStyle: React.CSSProperties = anchorRect ? {
    position: 'fixed',
    top: anchorRect.bottom + 4,
    left: anchorRect.left + anchorRect.width / 2,
    transform: 'translateX(-50%)',
  } : {}

  return (
    <>
      <div className="ret-score-backdrop" onClick={e => { e.stopPropagation(); onClose() }} />
      <div className="ret-score-popover" style={popoverStyle} onClick={e => e.stopPropagation()}>
      <div className="ret-score-popover__summary">{breakdown.summary}</div>
      <div className="ret-score-popover__factors">
        {breakdown.factors.map(f => (
          <div key={f.factor} className="ret-score-popover__factor">
            <div className="ret-score-popover__factor-header">
              <span className="ret-score-popover__factor-name">{factorLabels[f.factor] || f.factor}</span>
              <span className="ret-score-popover__factor-pts" style={{ color: levelColor(f.level) }}>
                +{f.points}/{f.max}
              </span>
            </div>
            <div className="ret-score-popover__factor-bar">
              <div className="ret-score-popover__factor-fill" style={{
                width: `${(f.points / f.max) * 100}%`,
                background: levelColor(f.level),
              }} />
            </div>
            <div className="ret-score-popover__factor-reason">{f.reason}</div>
          </div>
        ))}
      </div>
    </div>
    </>
  )
}
