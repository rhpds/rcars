import { ButtonHTMLAttributes } from 'react'

interface LcarsButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'send' | 'action' | 'curator' | 'curator-secondary'
}

const variantClasses: Record<string, string> = {
  primary: 'btn-action',
  send: 'btn-send',
  action: 'btn-action',
  curator: 'btn-curator',
  'curator-secondary': 'btn-curator secondary',
}

export function LcarsButton({ variant = 'primary', className = '', ...props }: LcarsButtonProps) {
  return (
    <button className={`${variantClasses[variant] || 'btn-action'} ${className}`} {...props} />
  )
}
