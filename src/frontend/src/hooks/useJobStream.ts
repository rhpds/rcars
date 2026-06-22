import { useState, useEffect } from 'react'

interface ProgressMessage {
  phase: string
  message: string
  done: boolean
}

export interface StreamCandidate {
  ci_name: string
  display_name: string
  tier: string
  relevance_score: number | null
  vector_similarity_pct: number | null
  stage: string
  catalog_namespace: string
  learning_objectives: string[]
  why_it_fits: string | null
  how_to_use: string | null
  suggested_format: string | null
  duration_notes: string | null
  caveats: string | null
  duration_min: number | null
  duration_source: string | null
}

interface StreamState {
  phase: string
  progress: { current?: number; total?: number } | null
  userMessage: string
  results: unknown | null
  isComplete: boolean
  error: string | null
  messages: ProgressMessage[]
  candidates: StreamCandidate[]
}

const initialState: StreamState = {
  phase: '', progress: null, userMessage: '', results: null,
  isComplete: false, error: null, messages: [], candidates: [],
}

export function useJobStream(jobId: string | null): StreamState {
  const [state, setState] = useState<StreamState>(initialState)

  useEffect(() => {
    if (!jobId) {
      setState(initialState)
      return
    }

    const eventSource = new EventSource(`/api/v1/advisor/query/${jobId}/stream`)

    eventSource.onmessage = (event) => {
      let data: Record<string, unknown>
      try {
        data = JSON.parse(event.data)
      } catch (err) {
        console.error('Failed to parse SSE message:', err)
        return
      }
      setState(prev => {
        const newMessage: ProgressMessage = {
          phase: data.phase,
          message: data.user_message,
          done: data.status === 'complete' || data.phase === 'complete',
        }
        return {
          phase: data.phase,
          progress: data.current != null ? { current: data.current, total: data.total } : null,
          userMessage: data.user_message,
          results: data.results || prev.results,
          isComplete: data.phase === 'complete' || data.phase === 'failed',
          error: data.phase === 'failed' ? (data.error || 'Unknown error') : null,
          messages: [...prev.messages, newMessage],
          candidates: data.candidate_data || prev.candidates,
        }
      })

      if (data.phase === 'complete' || data.phase === 'failed') {
        eventSource.close()
      }
    }

    eventSource.onerror = () => {
      setState(prev => ({ ...prev, isComplete: true, error: prev.error || 'Connection lost' }))
      eventSource.close()
    }

    return () => eventSource.close()
  }, [jobId])

  return state
}
