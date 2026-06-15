import React, { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../services/api'
import { useJobStream, StreamCandidate } from '../hooks/useJobStream'
import { useAuth } from '../hooks/useAuth'
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

function cleanAssessment(text: string): string {
  let cleaned = text.replace(/^\*?\*?Response:\*?\*?\s*/i, '')
  cleaned = cleaned.replace(/^\*?\*?Practical Notes:\*?\*?\s*/im, '\n**Practical Notes:**\n')
  return cleaned
}

function LcarsToggle({ label, active, onToggle }: { label: string; active: boolean; onToggle: () => void }) {
  return (
    <div className={`lcars-toggle${active ? ' active' : ''}`} onClick={onToggle}>
      <div className="lcars-toggle-track">
        <div className="lcars-toggle-knob" />
      </div>
      <span>{label}</span>
    </div>
  )
}

export function AdvisorPage() {
  const [searchParams] = useSearchParams()
  const auth = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [showDev, setShowDev] = useState(false)
  const [showEvent, setShowEvent] = useState(false)
  const showZt = true
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [turns, setTurns] = useState<TurnResults[]>([])
  const [activeTurn, setActiveTurn] = useState(0)
  const [sending, setSending] = useState(false)
  const [loadedSessionId, setLoadedSessionId] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const stream = useJobStream(activeJobId)

  const resetSession = () => {
    setLoadedSessionId(null)
    setMessages([])
    setTurns([])
    setActiveTurn(0)
    setActiveJobId(null)
    setSending(false)
    setInput('')
  }

  useEffect(() => {
    const handler = () => resetSession()
    window.addEventListener('rcars:new-session', handler)
    return () => window.removeEventListener('rcars:new-session', handler)
  }, [])

  // Load session from URL param, or reset for new session
  useEffect(() => {
    const sid = searchParams.get('session')
    if (!sid) {
      if (loadedSessionId) {
        resetSession()
      }
      return
    }
    if (sid !== loadedSessionId) {
      setLoadedSessionId(sid)
      api.getSession(sid).then(data => {
        const sessionTurns = (data as { turns: Array<{ query_text: string | null; overall_assessment: string | null; results_json: StreamCandidate[] | null; content_gaps?: string[] | null }> }).turns
        const newMessages: ChatMessage[] = []
        const newTurns: TurnResults[] = []
        for (const turn of sessionTurns) {
          if (turn.query_text) {
            newMessages.push({ role: 'user', content: turn.query_text })
          }
          let text = cleanAssessment(turn.overall_assessment || '')
          if (turn.content_gaps && turn.content_gaps.length > 0) {
            text += '\n\n**Content gaps:**'
            for (const gap of turn.content_gaps) text += `\n- ${gap}`
          }
          if (text) newMessages.push({ role: 'assistant', content: text })
          if (turn.results_json) {
            newTurns.push({
              candidates: turn.results_json,
              overall_assessment: turn.overall_assessment,
              content_gaps: (turn as Record<string, unknown>).content_gaps as string[] | null || null,
            })
          }
        }
        setMessages(newMessages)
        setTurns(newTurns)
        setActiveTurn(Math.max(0, newTurns.length - 1))
      }).catch(() => { /* session not found */ })
    }
  }, [searchParams])

  useEffect(() => {
    if (stream.isComplete && activeJobId) {
      api.getQueryResult(activeJobId).then(data => {
        if (data.result && typeof data.result === 'object') {
          const result = data.result as TurnResults
          setTurns(prev => [...prev, result])
          setActiveTurn(turns.length)

          let text = cleanAssessment(result.overall_assessment || '')
          if (result.content_gaps && result.content_gaps.length > 0) {
            text += '\n\n**Content gaps:**'
            for (const gap of result.content_gaps) text += `\n- ${gap}`
          }
          if (!text) text = 'No matching content found. Try adding more detail — describe the topic, audience, product area, or format you need. Short queries often lack enough context for RCARS to find a strong match.'
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

    // For follow-up queries, prepend context from the original query
    let searchQuery = query
    if (turns.length > 0) {
      const originalQuery = messages.find(m => m.role === 'user')?.content
      if (originalQuery) {
        searchQuery = `${originalQuery}\n\nAdditional context: ${query}`
      }
    }

    try {
      const stages = ['prod']
      if (showDev) stages.push('dev')
      if (showEvent) stages.push('event')
      const { job_id } = await api.submitQuery(searchQuery, stages, showZt)
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
                Results appear in the panel on the right. Ask follow-up questions to narrow down — for example, "focus on beginner-level content" or "show me something shorter than 30 minutes." Each turn produces a new set of recommendations you can compare.
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
        <div style={{ display: 'flex', gap: '12px', padding: '0 0 6px 0', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: '#555' }}>Include:</span>
          {auth.isCurator && <LcarsToggle label="dev" active={showDev} onToggle={() => setShowDev(!showDev)} />}
          <LcarsToggle label="event" active={showEvent} onToggle={() => setShowEvent(!showEvent)} />
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
            <div style={{ display: 'flex', gap: '6px', fontSize: '12px' }}>
              {turns.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveTurn(i)}
                  style={{
                    background: i === activeTurn ? '#1a3a5a' : 'transparent',
                    border: '1px solid #333',
                    color: i === activeTurn ? '#73bcf7' : '#666',
                    padding: '3px 10px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px',
                  }}
                >
                  {i === turns.length - 1 ? 'Current' : `Rec ${i + 1}`}
                </button>
              ))}
            </div>
          )}
        </div>

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

  // During streaming before triage, show flat list
  if (streamPhase === 'vector_search') {
    return (
      <>
        <div style={{ fontSize: '11px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px', margin: '8px 0 4px' }}>
          Candidates ({candidates.length})
        </div>
        {candidates.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={false} />)}
      </>
    )
  }

  // During streaming after triage but before rationale, show all scored candidates visibly
  if (!isComplete && green.length === 0 && yellow.length > 0) {
    return (
      <>
        <div style={{ fontSize: '11px', color: '#e8a838', textTransform: 'uppercase', letterSpacing: '0.5px', margin: '8px 0 4px' }}>
          Evaluating top {Math.min(yellow.length, 5)} matches...
        </div>
        {yellow.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={false} />)}
        {white.length > 0 && (
          <CollapsibleTier label={`Also reviewed (${white.length})`} candidates={white} isComplete={false} />
        )}
      </>
    )
  }

  return (
    <>
      {green.length > 0 && (
        <div style={{ fontSize: '12px', color: '#5cb85c', textTransform: 'uppercase', letterSpacing: '0.5px', margin: '8px 0 4px' }}>Best fit ({green.length})</div>
      )}
      {green.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={isComplete} />)}

      {yellow.length > 0 && (
        <CollapsibleTier label={`Other options (${yellow.length})`} candidates={yellow} isComplete={isComplete} />
      )}

      {white.length > 0 && (
        <CollapsibleTier label={`Also reviewed (${white.length})`} candidates={white} isComplete={isComplete} />
      )}
    </>
  )
}

function CollapsibleTier({ label, candidates, isComplete }: {
  label: string
  candidates: StreamCandidate[]
  isComplete: boolean
}) {
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
      {open && candidates.map(c => <RecCard key={c.ci_name} candidate={c} isComplete={isComplete} />)}
    </div>
  )
}
