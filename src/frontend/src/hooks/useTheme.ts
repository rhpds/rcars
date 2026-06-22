import { useState, useEffect, createContext, useContext } from 'react'

type Theme = 'dark' | 'light'

interface ThemeState {
  theme: Theme
  toggleTheme: () => void
}

export const ThemeContext = createContext<ThemeState>({
  theme: 'dark',
  toggleTheme: () => {},
})

export function useTheme() {
  return useContext(ThemeContext)
}

export function useThemeProvider(): ThemeState {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem('rcars-theme')
    return stored === 'light' ? 'light' : 'dark'
  })

  useEffect(() => {
    localStorage.setItem('rcars-theme', theme)
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(prev => (prev === 'dark' ? 'light' : 'dark'))

  return { theme, toggleTheme }
}
