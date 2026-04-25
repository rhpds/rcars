import { useState, useEffect, createContext, useContext } from 'react'
import { api } from '../services/api'

interface AuthState {
  email: string
  roles: string[]
  isLoading: boolean
  isCurator: boolean
  isAdmin: boolean
}

const defaultState: AuthState = {
  email: '', roles: [], isLoading: true, isCurator: false, isAdmin: false,
}

export const AuthContext = createContext<AuthState>(defaultState)

export function useAuth() {
  return useContext(AuthContext)
}

export function useAuthProvider(): AuthState {
  const [state, setState] = useState<AuthState>(defaultState)

  useEffect(() => {
    api.getMe()
      .then(data => setState({
        email: data.email,
        roles: data.roles,
        isLoading: false,
        isCurator: data.roles.includes('curator'),
        isAdmin: data.roles.includes('admin'),
      }))
      .catch(() => setState(prev => ({ ...prev, isLoading: false })))
  }, [])

  return state
}
