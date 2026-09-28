interface ProgressMessage {
  phase: string
  message: string
  done: boolean
  category?: string
}

interface ProgressStreamProps {
  messages: ProgressMessage[]
}

export function ProgressStream({ messages }: ProgressStreamProps) {
  if (messages.length === 0) return null

  const hasCategories = messages.some(m => m.category)

  if (!hasCategories) {
    return (
      <div style={{ fontSize: '14px', lineHeight: '1.8' }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ color: msg.done ? 'var(--score-green)' : 'var(--score-amber)' }}>
            {msg.done ? '✓' : '●'} {msg.message}
          </div>
        ))}
      </div>
    )
  }

  const byCategory = new Map<string, ProgressMessage[]>()
  for (const msg of messages) {
    const key = msg.category || '_default'
    const list = byCategory.get(key) || []
    list.push(msg)
    byCategory.set(key, list)
  }

  const allDone = messages.every(m => m.done)

  return (
    <div style={{ fontSize: '14px', lineHeight: '1.8' }}>
      <div style={{ color: allDone ? 'var(--score-green)' : 'var(--score-amber)' }}>
        {allDone ? '✓' : '●'} Searching {byCategory.size} content types...
      </div>
      {Array.from(byCategory.entries()).map(([cat, msgs]) => {
        const latest = msgs[msgs.length - 1]
        return (
          <div key={cat} style={{ paddingLeft: '20px', color: latest?.done ? 'var(--score-green)' : 'var(--score-amber)' }}>
            {latest?.done ? '✓' : '●'} {cat}: {latest?.message}
          </div>
        )
      })}
    </div>
  )
}
