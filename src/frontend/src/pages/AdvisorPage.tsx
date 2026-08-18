import React, { useState, useRef, useEffect, useCallback, KeyboardEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../services/api'
import { useJobStream, StreamCandidate } from '../hooks/useJobStream'
import { useAuth } from '../hooks/useAuth'
import { ProgressStream } from '../components/advisor/ProgressStream'
import { RecCardList } from '../components/advisor/RecCardList'
import { ChatEnvelope, ChatChip } from '../components/advisor/chatTypes'
import { resolveBlockRenderer } from '../components/advisor/blocks/registry'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  jobId?: string
  envelope?: ChatEnvelope
}

function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: React.ReactElement[] = []
  let listItems: string[] = []

  const flushList = () => {
    if (listItems.length === 0) return
    elements.push(
      <ul key={`ul-${elements.length}`} style={{ margin: '6px 0', paddingLeft: '20px', listStyle: 'disc' }}>
        {listItems.map((li, i) => <li key={i} dangerouslySetInnerHTML={{ __html: inlineMd(li) }} />)}
      </ul>
    )
    listItems = []
  }

  const escapeHtml = (s: string) =>
    s.replace(/&/g, '&amp;')
     .replace(/</g, '&lt;')
     .replace(/>/g, '&gt;')
     .replace(/"/g, '&quot;')
     .replace(/'/g, '&#39;')

  const inlineMd = (s: string) =>
    escapeHtml(s)
     .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
     .replace(/`([^`]+)`/g, '<code style="background:var(--bg-input);padding:1px 4px;border-radius:3px;font-size:12px">$1</code>')

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


function RcarsToggle({ label, active, onToggle }: { label: string; active: boolean; onToggle: () => void }) {
  return (
    <div
      className={`rcars-toggle-switch${active ? ' active' : ''}`}
      onClick={onToggle}
      role="switch"
      aria-checked={active}
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle() } }}
    >
      <div className="rcars-toggle-switch-track">
        <div className="rcars-toggle-switch-knob" />
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
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [turns, setTurns] = useState<ChatEnvelope[]>([])
  const [activeTurn, setActiveTurn] = useState(0)
  const [sending, setSending] = useState(false)
  const [loadedSessionId, setLoadedSessionId] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const layoutRef = useRef<HTMLDivElement>(null)
  const [chatWidthPct, setChatWidthPct] = useState(40)
  const isDragging = useRef(false)
  const cleanupDragRef = useRef<(() => void) | null>(null)

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    const onMove = (ev: MouseEvent) => {
      if (!isDragging.current || !layoutRef.current) return
      const rect = layoutRef.current.getBoundingClientRect()
      const pct = ((ev.clientX - rect.left) / rect.width) * 100
      setChatWidthPct(Math.max(25, Math.min(75, pct)))
    }
    const onUp = () => {
      isDragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      window.removeEventListener('blur', onUp)
      cleanupDragRef.current = null
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    window.addEventListener('blur', onUp)
    cleanupDragRef.current = onUp
  }, [])

  useEffect(() => () => cleanupDragRef.current?.(), [])

  const stream = useJobStream(activeJobId)

  const resetSession = () => {
    setLoadedSessionId(null)
    setSessionId(null)
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
      setSessionId(sid)
      api.getSession(sid).then(data => {
        const sessionTurns = (data as { turns: Array<{ query_text: string | null; overall_assessment: string | null; results_json: StreamCandidate[] | null; content_gaps?: string[] | null; envelope_json?: ChatEnvelope | null }> }).turns
        const newMessages: ChatMessage[] = []
        const newTurns: ChatEnvelope[] = []
        for (const turn of sessionTurns) {
          if (turn.query_text) {
            newMessages.push({ role: 'user', content: turn.query_text })
          }
          // New chat turns: envelope_json exists
          if (turn.envelope_json) {
            const env = turn.envelope_json
            newMessages.push({ role: 'assistant', content: env.answer, envelope: env })
            newTurns.push(env)
          } else {
            // Legacy single-turn recommend sessions: results_json only
            let text = turn.overall_assessment || ''
            if (turn.content_gaps && turn.content_gaps.length > 0) {
              text += '\n\n**Content gaps:**'
              for (const gap of turn.content_gaps) text += `\n- ${gap}`
            }
            if (text) newMessages.push({ role: 'assistant', content: text })
            if (turn.results_json) {
              // Legacy turn — no envelope, keep in TurnResults format for compatibility
              // Don't push to newTurns since it's now ChatEnvelope[] only
            }
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
        const env = data.result as ChatEnvelope
        if (env && env.intent) {
          setTurns(prev => [...prev, env])
          setActiveTurn(turns.length)
          setMessages(prev => [...prev, { role: 'assistant', content: env.answer, envelope: env, jobId: activeJobId }])
        } else {
          const errMsg = data.error || 'Something went wrong. Please try again.'
          setMessages(prev => [...prev, { role: 'assistant', content: errMsg }])
        }
        setActiveJobId(null)
        setSending(false)
      }).catch(() => {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Something went wrong. Please try again.' }])
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
      const stages = ['prod']
      if (showDev) stages.push('dev')
      if (showEvent) stages.push('event')
      const { job_id, session_id } = await api.submitChat(query, sessionId, stages, showZt)
      setSessionId(session_id)
      setActiveJobId(job_id)
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err}` }])
      setSending(false)
    }
  }

  const handleChip = async (chip: ChatChip) => {
    if (sending) return

    setSending(true)
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: chip.label }])

    try {
      const stages = ['prod']
      if (showDev) stages.push('dev')
      if (showEvent) stages.push('event')
      const { job_id, session_id } = await api.submitChat(
        chip.label,
        sessionId,
        stages,
        showZt,
        { intent: chip.intent, args: chip.args, scope: chip.scope }
      )
      setSessionId(session_id)
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
    <div className="advisor-layout" ref={layoutRef}>
      {/* Chat panel */}
      <div className="chat-pane" style={{ flex: `0 0 ${chatWidthPct}%` }}>
        <div className="pane-label">Chat</div>
        <div className="chat-turns">
          {messages.length === 0 && !sending && (
            <div className="chat-welcome">
              <p style={{ fontSize: '17px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Welcome to the RHDP Content Advisor &amp; Recommendation System (RCARS)!
              </p>
              <p style={{ fontSize: '13px', color: 'var(--rcars-amber-vivid)', marginBottom: '14px', fontStyle: 'italic' }}>
                This is a beta release and we are regularly adding features.
              </p>
              <p className="hint" style={{ marginBottom: '14px' }}>
                RCARS knows about all RHDP content with Showroom guides. Ask it to:
              </p>
              <p className="hint" style={{ marginBottom: '8px' }}>
                <strong style={{ color: 'var(--text-primary)' }}>Find content</strong> — "I need a 2-hour hands-on lab for platform engineers covering OpenShift virtualization"
              </p>
              <p className="hint" style={{ marginBottom: '8px' }}>
                <strong style={{ color: 'var(--text-primary)' }}>Check overlap</strong> — "What overlaps with Red Hat Trusted Application Pipeline?"
              </p>
              <p className="hint" style={{ marginBottom: '8px' }}>
                <strong style={{ color: 'var(--text-primary)' }}>Check performance</strong> — "How impactful is the OpenShift Virtualization Migration Factory demo?"
              </p>
              <p className="hint" style={{ marginBottom: '8px' }}>
                <strong style={{ color: 'var(--text-primary)' }}>Item facts</strong> — "What is the Parasol Insurance AI Workshop about?"
              </p>
              <p className="hint" style={{ marginBottom: '14px' }}>
                <strong style={{ color: 'var(--text-primary)' }}>Automation &amp; workloads</strong> — "What deploys OpenShift AI?" or "What workloads configure an OpenShift cluster?"
              </p>
              <p className="hint" style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '13px' }}>
                Be specific about audience, topic, format, and time. Follow-up questions refine results.
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '12px' }}>
                Questions or feedback? Join <a href="https://redhat.enterprise.slack.com/archives/C0BNJ74JA3V" target="_blank" rel="noopener noreferrer">#forum-dem-rcars</a> on Slack.
              </p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={msg.role === 'user' ? 'chat-turn-user' : 'chat-turn-assistant'}>
              {msg.role === 'assistant' ? (
                <>
                  {msg.envelope && (
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', marginBottom: 6 }}>
                      {msg.envelope.scope_echo}
                    </div>
                  )}
                  <div className="assistant-content">{renderMarkdown(msg.content)}</div>
                  {msg.envelope && msg.envelope.suggested_followups.length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                      {msg.envelope.suggested_followups.map((chip, ci) => (
                        <button
                          key={ci}
                          onClick={() => handleChip(chip)}
                          disabled={sending}
                          style={{
                            border: '1px solid var(--border-default)',
                            background: 'transparent',
                            color: 'var(--text-link)',
                            borderRadius: 12,
                            padding: '3px 10px',
                            fontSize: 12,
                            cursor: 'pointer',
                          }}
                        >
                          {chip.label}
                        </button>
                      ))}
                    </div>
                  )}
                </>
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
        {showSettings && auth.isCurator && (
          <div style={{
            display: 'flex', gap: '12px', padding: '8px 12px', alignItems: 'center',
            background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)', marginBottom: '8px',
          }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Include:</span>
            <RcarsToggle label="dev" active={showDev} onToggle={() => setShowDev(!showDev)} />
            <RcarsToggle label="event" active={showEvent} onToggle={() => setShowEvent(!showEvent)} />
          </div>
        )}
        <div className="chat-input-row">
          <button
            className="btn-settings-toggle"
            onClick={() => setShowSettings(!showSettings)}
            title="Query settings"
            aria-label="Toggle query settings"
            style={{
              background: showSettings ? 'var(--bg-card)' : 'transparent',
              border: '1px solid var(--border-default)',
              color: showSettings ? 'var(--text-link)' : 'var(--text-muted)',
              padding: '8px 10px',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              fontSize: '16px',
              lineHeight: 1,
              flexShrink: 0,
              transition: 'color var(--transition-fast), background var(--transition-fast)',
            }}
          >
            ⚙
          </button>
          <div style={{ flex: 1, position: 'relative' }}>
            <textarea
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, 2000))}
              onKeyDown={handleKeyDown}
              placeholder="Describe what you're looking for..."
              rows={2}
              maxLength={2000}
              disabled={sending}
            />
            <span style={{
              position: 'absolute', bottom: '4px', right: '8px',
              fontSize: '11px', fontFamily: 'var(--ff-mono)',
              color: input.length > 1800 ? 'var(--score-amber)' : 'var(--text-muted)',
              opacity: input.length > 0 ? 0.7 : 0,
              transition: 'opacity var(--transition-fast)',
            }}>{input.length}/2000</span>
          </div>
          <button className={`btn-send${sending ? ' sending' : ''}`} onClick={handleSend} disabled={sending}>
            Send
          </button>
        </div>
        {turns.length > 5 && (
          <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '4px 2px' }}>
            Long session — references only reach the last 5 turns. Fresh often works better (use New Session).
          </div>
        )}
      </div>

      {/* Resize handle */}
      <div
        className="pane-divider"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize chat and recommendations panes"
        aria-valuemin={25}
        aria-valuemax={75}
        aria-valuenow={chatWidthPct}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault()
            setChatWidthPct(prev => Math.max(25, Math.min(75, prev + (e.key === 'ArrowRight' ? 5 : -5))))
          }
        }}
        onMouseDown={handleResizeStart}
      />

      {/* Results panel */}
      <div className="rec-pane" style={{ flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="pane-label">Results</div>
          {turns.length > 1 && (
            <div style={{ display: 'flex', gap: '6px', fontSize: '12px' }}>
              {turns.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveTurn(i)}
                  style={{
                    background: i === activeTurn ? 'var(--badge-blue-bg)' : 'transparent',
                    border: '1px solid var(--border-default)',
                    color: i === activeTurn ? 'var(--text-link)' : 'var(--text-muted)',
                    padding: '3px 10px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px',
                  }}
                >
                  {i === turns.length - 1 ? 'Current' : `Turn ${i + 1}`}
                </button>
              ))}
            </div>
          )}
        </div>

        {streamingCandidates ? (
          <RecCardList candidates={streamingCandidates} isComplete={false} streamPhase={stream.phase} />
        ) : currentResults ? (
          <>
            {currentResults.blocks.map((b, i) => {
              const Renderer = resolveBlockRenderer(b.type)
              return <Renderer key={i} block={b} sessionId={sessionId ?? undefined} turnIndex={activeTurn} />
            })}
          </>
        ) : sending ? (
          <div className="rec-pane-loading">Waiting for results...</div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: '15px', padding: '20px 0' }}>
            Submit a query to see results.
          </div>
        )}
      </div>
    </div>
  )
}

