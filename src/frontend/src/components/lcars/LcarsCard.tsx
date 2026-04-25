import { ReactNode } from 'react'

interface LcarsCardProps {
  children: ReactNode
  tier?: 'green' | 'yellow' | 'white'
  className?: string
  onClick?: () => void
}

export function LcarsCard({ children, tier = 'white', className = '', onClick }: LcarsCardProps) {
  const tierClass = tier === 'green' ? 'tier-green' : tier === 'yellow' ? 'tier-yellow' : ''
  return (
    <div className={`rec-card ${tierClass} ${className}`} onClick={onClick}>
      {children}
    </div>
  )
}
