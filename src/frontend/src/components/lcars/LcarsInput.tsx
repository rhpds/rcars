import { TextareaHTMLAttributes, InputHTMLAttributes } from 'react'

interface LcarsTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  variant?: 'chat' | 'filter'
}

export function LcarsInput({ variant = 'chat', className = '', ...props }: LcarsTextareaProps) {
  const cls = variant === 'filter' ? 'filter-input' : 'chat-input'
  return <textarea className={`${cls} ${className}`} {...props} />
}

interface LcarsSelectProps extends InputHTMLAttributes<HTMLSelectElement> {
  options: Array<{ value: string; label: string }>
}

export function LcarsSelect({ options, className = '', ...props }: LcarsSelectProps) {
  return (
    <select className={`filter-select ${className}`} {...(props as React.SelectHTMLAttributes<HTMLSelectElement>)}>
      {options.map(opt => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  )
}
