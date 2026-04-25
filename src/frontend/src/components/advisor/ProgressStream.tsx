interface ProgressMessage {
  phase: string
  message: string
  done: boolean
}

interface ProgressStreamProps {
  messages: ProgressMessage[]
}

export function ProgressStream({ messages }: ProgressStreamProps) {
  if (messages.length === 0) return null

  return (
    <div style={{ fontSize: '14px', lineHeight: '1.8' }}>
      {messages.map((msg, i) => (
        <div key={i} style={{ color: msg.done ? '#5cb85c' : '#e8a838' }}>
          {msg.done ? '✓' : '●'} {msg.message}
        </div>
      ))}
    </div>
  )
}
