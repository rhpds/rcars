import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { api } from '../services/api'
import { useJobStream } from '../hooks/useJobStream'
import { ProgressStream } from '../components/advisor/ProgressStream'
import { RecCard } from '../components/advisor/RecCard'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  jobId?: string
}

interface TurnResults {
  candidates: Array<{
    ci_name: string; display_name: string; tier: string;
    relevance_score: number | null; vector_similarity_pct: number | null;
    stage: string; why_it_fits: string | null; how_to_use: string | null;
    suggested_format: string | null; duration_notes: string | null; caveats: string | null;
  }>
  overall_assessment: string | null
  content_gaps: string[] | null
}

export function AdvisorPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [turns, setTurns] = useState<TurnResults[]>([])
  const [activeTurn, setActiveTurn] = useState(0)
  const [sending, setSending] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const stream = useJobStream(activeJobId)

  useEffect(() => {
    if (stream.isComplete && activeJobId) {
      api.getQueryResult(activeJobId).then(data => {
        if (data.result && typeof data.result === 'object') {
          const result = data.result as TurnResults
          setTurns(prev => [...prev, result])
          setActiveTurn(turns.length)
          const assessment = result.overall_assessment || ''
          setMessages(prev => [...prev, { role: 'assistant', content: assessment, jobId: activeJobId }])
        }
        setActiveJobId(null)
        setSending(false)
      })
    }
  }, [stream.isComplete])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, stream.messages])

  const handleSend = async () => {
    const query = input.trim()
    if (!query || sending) return

    setSending(true)
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: query }])

    try {
      const { job_id } = await api.submitQuery(query)
      setActiveJobId(job_id)
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err}` }])
      setSending(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const currentResults = turns[activeTurn] || null

  return (
    <div className="advisor-layout">
      {/* Chat panel */}
      <div className="chat-pane">
        <div className="pane-label">Chat</div>
        <div className="chat-turns">
          {messages.length === 0 && !sending && (
            <div className="chat-welcome">
              <p>What content are you looking for?</p>
              <p className="hint">Describe your event, audience, or topic. Paste an event URL for automatic matching.</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={msg.role === 'user' ? 'chat-turn-user' : 'chat-turn-assistant'}>
              {msg.role === 'assistant' ? (
                <div className="assistant-content">{msg.content}</div>
              ) : (
                msg.content
              )}
            </div>
          ))}
          {sending && activeJobId && (
            <div className="chat-turn-assistant">
              <ProgressStream messages={stream.messages} />
              {!stream.isComplete && (
                <div className="thinking-dots" style={{ marginTop: '8px' }}>
                  <span>.</span><span>.</span><span>.</span>
                </div>
              )}
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
        <div className="chat-input-row">
          <textarea
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about content for your event..."
            rows={2}
            disabled={sending}
          />
          <button className={`btn-send${sending ? ' sending' : ''}`} onClick={handleSend} disabled={sending}>
            Send
          </button>
        </div>
      </div>

      {/* Recommendations panel */}
      <div className="rec-pane">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="pane-label">Recommendations</div>
          {turns.length > 1 && (
            <div style={{ display: 'flex', gap: '8px', fontSize: '13px' }}>
              {turns.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveTurn(i)}
                  style={{
                    background: i === activeTurn ? '#1a3a5a' : 'transparent',
                    border: '1px solid #333',
                    color: i === activeTurn ? '#73bcf7' : '#666',
                    padding: '4px 12px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '13px',
                  }}
                >
                  Turn {i + 1}
                </button>
              ))}
            </div>
          )}
        </div>

        {currentResults ? (
          <>
            {/* Green tier */}
            {currentResults.candidates
              .filter(c => c.tier === 'green')
              .map(c => <RecCard key={c.ci_name} candidate={c} isComplete={true} />)}

            {/* Yellow tier - collapsible */}
            {(() => {
              const yellow = currentResults.candidates.filter(c => c.tier === 'yellow')
              if (yellow.length === 0) return null
              return <CollapsibleTier label={`Yellow (${yellow.length})`} candidates={yellow} />
            })()}

            {/* White tier - collapsible */}
            {(() => {
              const white = currentResults.candidates.filter(c => c.tier === 'white')
              if (white.length === 0) return null
              return <CollapsibleTier label={`Other (${white.length})`} candidates={white} />
            })()}

            {currentResults.content_gaps && currentResults.content_gaps.length > 0 && (
              <div style={{ marginTop: '16px', fontSize: '14px', color: '#e8a838' }}>
                <strong>Content gaps:</strong>
                <ul style={{ margin: '4px 0 0 18px' }}>
                  {currentResults.content_gaps.map((gap, i) => <li key={i}>{gap}</li>)}
                </ul>
              </div>
            )}
          </>
        ) : sending ? (
          <div className="rec-pane-loading">Waiting for results...</div>
        ) : (
          <div style={{ color: '#444', fontSize: '15px', padding: '20px 0' }}>
            Submit a query to see recommendations.
          </div>
        )}
      </div>
    </div>
  )
}

function CollapsibleTier({ label, candidates }: { label: string; candidates: Array<{ ci_name: string; display_name: string; tier: string; relevance_score: number | null; vector_similarity_pct: number | null; stage: string; why_it_fits: string | null; how_to_use: string | null; suggested_format: string | null; duration_notes: string | null; caveats: string | null }> }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: 'transparent', border: 'none', color: '#666',
          cursor: 'pointer', fontSize: '14px', padding: '8px 0',
        }}
      >
        {open ? '▾' : '▸'} {label}
      </button>
      {open && candidates.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={true} />)}
    </div>
  )
}
