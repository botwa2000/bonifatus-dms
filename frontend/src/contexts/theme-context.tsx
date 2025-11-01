// frontend/src/contexts/theme-context.tsx
'use client'

import { createContext, useContext, useEffect, useState } from 'react'

type Theme = 'light' | 'dark'

interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextType>({
  theme: 'light',
  setTheme: () => {},
})

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>('light')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const initializeTheme = async () => {
      setMounted(true)

      // Try to fetch theme from backend (for logged-in users)
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/settings/theme`, {
          credentials: 'include'
        })
        if (response.ok) {
          const data = await response.json()
          if (data.value === 'light' || data.value === 'dark') {
            console.log('[THEME DEBUG] Loaded theme from backend:', data.value)
            setThemeState(data.value as Theme)
            applyTheme(data.value as Theme)
            localStorage.setItem('theme', data.value)
            return
          }
        }
      } catch (error) {
        // User not logged in or API error, fall back to localStorage
        console.log('[THEME DEBUG] Could not fetch theme from backend, using localStorage')
      }

      // Fallback to localStorage
      const localTheme = localStorage.getItem('theme') as Theme

      if (localTheme) {
        setThemeState(localTheme)
        applyTheme(localTheme)
      } else {
        const root = document.documentElement
        root.classList.add('light')
      }
    }

    initializeTheme()
  }, [])

  const applyTheme = (newTheme: Theme) => {
    if (typeof window === 'undefined') return
    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(newTheme)
  }

  const setTheme = async (newTheme: Theme) => {
    setThemeState(newTheme)
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme', newTheme)
    }
    applyTheme(newTheme)

    // Save to backend for logged-in users
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/settings/theme`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ value: newTheme })
      })
      if (response.ok) {
        console.log('[THEME DEBUG] Saved theme to backend:', newTheme)
      }
    } catch (error) {
      console.log('[THEME DEBUG] Could not save theme to backend:', error)
    }
  }

  if (!mounted) {
    return <>{children}</>
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  return context
}