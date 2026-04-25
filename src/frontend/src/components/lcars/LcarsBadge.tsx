import { ReactNode } from 'react'

interface LcarsBadgeProps {
  children: ReactNode
  variant?: 'green' | 'amber' | 'red' | 'review' | 'tag' | 'pill'
  className?: string
}

const variantClasses: Record<string, string> = {
  green: 'tag-pill',
  amber: 'review-badge',
  red: 'review-badge',
  review: 'review-badge',
  tag: 'tag-pill',
  pill: 'rec-pill',
}

export function LcarsBadge({ children, variant = 'tag', className = '' }: LcarsBadgeProps) {
  return (
    <span className={`${variantClasses[variant] || 'tag-pill'} ${className}`}>
      {children}
    </span>
  )
}
