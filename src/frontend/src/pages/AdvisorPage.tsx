import React, { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { api } from '../services/api'
import { useJobStream, StreamCandidate } from '../hooks/useJobStream'
import { ProgressStream } from '../components/advisor/ProgressStream'
import { RecCard } from '../components/advisor/RecCard'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  jobId?: string
}

interface TurnResults {
  candidates: StreamCandidate[]
  overall_assessment: string | null
  content_gaps: string[] | null
}

function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: React.ReactElement[] = []
  let listItems: string[] = []

  const flushList = () => {
    if (listItems.length === 0) return
    elements.push(
      <ul key={`ul-${elements.length}`} style={{ margin: '6px 0', paddingLeft: '20px' }}>
        {listItems.map((li, i) => <li key={i} dangerouslySetInnerHTML={{ __html: inlineMd(li) }} />)}
      </ul>
    )
    listItems = []
  }

  const inlineMd = (s: string) =>
    s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
     .replace(/`([^`]+)`/g, '<code style="background:#1a2030;padding:1px 4px;border-radius:3px;font-size:12px">$1</code>')

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const bullet = line.match(/^[-–•]\s+(.*)/)
    if (bullet) {
      listItems.push(bullet[1])
      continue
    }
    flushList()
    if (line.trim() === '') {
      elements.push(<div key={`br-${i}`} style={{ height: '8px' }} />)
    } else {
      elements.push(<p key={`p-${i}`} style={{ margin: '4px 0' }} dangerouslySetInnerHTML={{ __html: inlineMd(line) }} />)
    }
  }
  flushList()
  return <>{elements}</>
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

          // Build chat message: overall assessment + content gaps
          let text = result.overall_assessment || ''
          if (result.content_gaps && result.content_gaps.length > 0) {
            text += '\n\n**Content gaps:**'
            for (const gap of result.content_gaps) {
              text += `\n- ${gap}`
            }
          }
          setMessages(prev => [...prev, { role: 'assistant', content: text, jobId: activeJobId }])
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
  // During streaming, show progressive candidates from SSE
  const streamingCandidates = sending && stream.candidates.length > 0 ? stream.candidates : null

  return (
    <div className="advisor-layout">
      {/* Chat panel */}
      <div className="chat-pane">
        <div className="pane-label">Chat</div>
        <div className="chat-turns">
          {messages.length === 0 && !sending && (
            <div className="chat-welcome">
              <p className="hint" style={{ marginBottom: '14px' }}>
                RCARS searches across the entire RHDP catalog to find what fits your needs. It uses AI to match your request against analyzed content, scoring relevance and generating detailed recommendations. This goes far deeper than keyword matching against a description.
              </p>
              <p className="hint" style={{ marginBottom: '12px' }}>
                <strong style={{ color: '#d2d2d2' }}>How to get the best results:</strong><br/>
                Be specific about your audience, activity, the topic or product area, the format you need (hands-on lab, presentation, demonstration, etc.), and how much time you have. The more detail you provide, the better the match.
              </p>
              <p className="hint" style={{ marginBottom: '12px' }}>
                <strong style={{ color: '#d2d2d2' }}>Refine as you go:</strong><br/>
                Results appear in the panel on the right. Ask follow-up questions to narrow down — for example, "focus on beginner-level content" or "show me something shorter than 30 minutes." Each turn produces a new set of recommendations you can compare. If you prefer an earlier result, click on that message to restore those recommendations.
              </p>
              <p className="hint" style={{ marginBottom: '14px' }}>
                <strong style={{ color: '#d2d2d2' }}>Event matching:</strong><br/>
                Paste an event URL (conference site, call for papers, etc.) and RCARS will analyze the event themes and suggest content that fits the tracks and audience.
              </p>
              <p className="hint" style={{ color: '#555', fontStyle: 'italic', fontSize: '13px' }}>
                Try: "I need a 2-hour hands-on lab for platform engineers covering OpenShift virtualization and migration from VMware"
              </p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={msg.role === 'user' ? 'chat-turn-user' : 'chat-turn-assistant'}>
              {msg.role === 'assistant' ? (
                <div className="assistant-content">{renderMarkdown(msg.content)}</div>
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
            placeholder="Describe what you're looking for..."
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

        {/* Show progressive candidates during streaming */}
        {streamingCandidates ? (
          <RecCardList candidates={streamingCandidates} isComplete={false} streamPhase={stream.phase} />
        ) : currentResults ? (
          <RecCardList candidates={currentResults.candidates} isComplete={true} />
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

function RecCardList({ candidates, isComplete, streamPhase }: {
  candidates: StreamCandidate[]
  isComplete: boolean
  streamPhase?: string
}) {
  const green = candidates.filter(c => c.tier === 'green')
  const yellow = candidates.filter(c => c.tier === 'yellow')
  const white = candidates.filter(c => c.tier === 'white' || c.tier === 'pending')

  // During vector_search phase, all candidates are unsorted — show flat list
  if (streamPhase === 'vector_search' || (!isComplete && green.length === 0 && yellow.length === 0)) {
    return (
      <>
        {candidates.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={false} />)}
      </>
    )
  }

  return (
    <>
      {green.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={isComplete} />)}

      {yellow.length > 0 && (
        <CollapsibleTier label={`Yellow (${yellow.length})`} candidates={yellow} defaultOpen={green.length === 0} isComplete={isComplete} />
      )}

      {white.length > 0 && (
        <CollapsibleTier label={`Other (${white.length})`} candidates={white} isComplete={isComplete} />
      )}
    </>
  )
}

function CollapsibleTier({ label, candidates, defaultOpen, isComplete }: {
  label: string
  candidates: StreamCandidate[]
  defaultOpen?: boolean
  isComplete: boolean
}) {
  const [open, setOpen] = useState(defaultOpen || false)
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
      {open && candidates.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={isComplete} />)}
    </div>
  )
}
