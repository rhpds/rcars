import { useState, createContext, useContext } from 'react'

interface PrivateModeState {
  enabled: boolean
  toggle: () => void
}

export const PrivateModeContext = createContext<PrivateModeState>({
  enabled: false,
  toggle: () => {},
})

export function usePrivateMode() {
  return useContext(PrivateModeContext)
}

export function usePrivateModeProvider(): PrivateModeState {
  const [enabled, setEnabled] = useState(false)
  return { enabled, toggle: () => setEnabled(prev => !prev) }
}
