import { useRef, useEffect, useState } from 'react'

interface LogWindowProps {
  lines: string[]
  isOpen: boolean
  onToggle: () => void
}

export function LogWindow({ lines, isOpen, onToggle }: LogWindowProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isAtBottom, setIsAtBottom] = useState(true)

  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    const threshold = 30
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold
    setIsAtBottom(atBottom)
  }

  useEffect(() => {
    if (isAtBottom && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [lines, isAtBottom])

  return (
    <div style={{ marginTop: '10px' }}>
      <button
        onClick={onToggle}
        style={{
          background: 'transparent', border: 'none', color: '#666',
          cursor: 'pointer', fontSize: '14px', padding: '4px 0',
        }}
      >
        {isOpen ? '▾' : '▸'} Log ({lines.length} lines)
      </button>
      {isOpen && (
        <div
          ref={containerRef}
          onScroll={handleScroll}
          style={{
            background: '#0a0d12',
            border: '1px solid #1e2030',
            borderRadius: '6px',
            padding: '12px',
            maxHeight: '300px',
            overflowY: 'auto',
            fontSize: '13px',
            fontFamily: 'monospace',
            color: '#999',
            marginTop: '6px',
          }}
        >
          {lines.map((line, i) => (
            <div key={i} style={{ whiteSpace: 'pre-wrap', marginBottom: '2px' }}>{line}</div>
          ))}
        </div>
      )}
    </div>
  )
}
