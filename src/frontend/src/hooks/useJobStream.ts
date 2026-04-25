import { useState, useEffect } from 'react'

interface ProgressMessage {
  phase: string
  message: string
  done: boolean
}

interface StreamState {
  phase: string
  progress: { current?: number; total?: number } | null
  userMessage: string
  results: unknown | null
  isComplete: boolean
  error: string | null
  messages: ProgressMessage[]
}

const initialState: StreamState = {
  phase: '', progress: null, userMessage: '', results: null,
  isComplete: false, error: null, messages: [],
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
      const data = JSON.parse(event.data)
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
