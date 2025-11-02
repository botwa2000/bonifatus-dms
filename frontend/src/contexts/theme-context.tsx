// frontend/src/contexts/theme-context.tsx
'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { shouldLog } from '@/config/app.config'

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
      if (shouldLog('debug')) console.log('[THEME DEBUG] === Initializing Theme ===')
      setMounted(true)

      // Load from localStorage first (instant, no API call)
      const localTheme = localStorage.getItem('theme') as Theme
      if (shouldLog('debug')) console.log('[THEME DEBUG] localStorage theme:', localTheme)

      if (localTheme && (localTheme === 'light' || localTheme === 'dark')) {
        if (shouldLog('debug')) console.log('[THEME DEBUG] ✅ Using theme from localStorage:', localTheme)
        setThemeState(localTheme)
        applyTheme(localTheme)
      } else {
        // No valid theme in localStorage, use default
        if (shouldLog('debug')) console.log('[THEME DEBUG] ℹ️  No theme in localStorage, using default: light')
        setThemeState('light')
        applyTheme('light')
      }

      // Then try to sync with backend (only for logged-in users)
      // This will silently fail with 401 if user is not logged in - that's expected
      try {
        const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/settings/theme`
        if (shouldLog('debug')) console.log('[THEME DEBUG] Syncing theme from backend:', url)

        const response = await fetch(url, {
          credentials: 'include'
        })

        // Only update if we get a successful response (user is logged in)
        if (response.ok) {
          const data = await response.json()
          if (shouldLog('debug')) console.log('[THEME DEBUG] Backend response:', data)

          if (data.value === 'light' || data.value === 'dark') {
            // Update if backend theme is different from localStorage
            if (data.value !== localTheme) {
              if (shouldLog('debug')) console.log('[THEME DEBUG] ✅ Syncing theme from backend:', data.value)
              setThemeState(data.value as Theme)
              applyTheme(data.value as Theme)
              localStorage.setItem('theme', data.value)
            }
          }
        }
        // Silently ignore 401/403 errors (user not logged in - expected)
      } catch (error) {
        // Silently ignore fetch errors - theme already loaded from localStorage
        if (shouldLog('debug')) console.log('[THEME DEBUG] Could not sync with backend (user may not be logged in)')
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
    if (shouldLog('debug')) {
      console.log('[THEME DEBUG] === Setting Theme ===')
      console.log('[THEME DEBUG] New theme:', newTheme)
    }

    setThemeState(newTheme)

    if (typeof window !== 'undefined') {
      if (shouldLog('debug')) console.log('[THEME DEBUG] Saving to localStorage...')
      localStorage.setItem('theme', newTheme)
      if (shouldLog('debug')) console.log('[THEME DEBUG] ✅ Saved to localStorage')
    }

    if (shouldLog('debug')) console.log('[THEME DEBUG] Applying theme to DOM...')
    applyTheme(newTheme)
    if (shouldLog('debug')) console.log('[THEME DEBUG] ✅ Applied to DOM')

    // Save to backend for logged-in users
    try {
      const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/settings/theme`
      if (shouldLog('debug')) console.log('[THEME DEBUG] Saving to backend:', url)

      const body = { value: newTheme }
      if (shouldLog('debug')) console.log('[THEME DEBUG] Request body:', body)

      const response = await fetch(url, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })

      if (shouldLog('debug')) {
        console.log('[THEME DEBUG] Response status:', response.status)
        console.log('[THEME DEBUG] Response ok:', response.ok)
      }

      if (response.ok) {
        const data = await response.json()
        if (shouldLog('debug')) console.log('[THEME DEBUG] ✅✅✅ Saved theme to backend successfully:', data)
      } else {
        const errorText = await response.text()
        if (shouldLog('debug')) console.log('[THEME DEBUG] ❌ Backend save failed:', response.status, errorText)
      }
    } catch (error) {
      if (shouldLog('debug')) console.log('[THEME DEBUG] ❌ Could not save theme to backend:', error)
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