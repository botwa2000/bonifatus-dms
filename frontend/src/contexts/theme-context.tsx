// frontend/src/contexts/theme-context.tsx
'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { logger } from '@/lib/logger'

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
      logger.debug('[THEME DEBUG] === Initializing Theme ===')

      // Load from localStorage first as immediate fallback
      const localTheme = localStorage.getItem('theme') as Theme
      let resolvedTheme: Theme = 'light'

      if (localTheme && (localTheme === 'light' || localTheme === 'dark')) {
        resolvedTheme = localTheme
      }

      // Apply localStorage theme to DOM immediately to prevent flash
      applyTheme(resolvedTheme)

      // Try to sync with backend (only succeeds for logged-in users)
      // Backend is the source of truth for logged-in users
      try {
        const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/settings/theme`

        const response = await fetch(url, {
          credentials: 'include'
        })

        if (response.ok) {
          const data = await response.json()

          if (data.value === 'light' || data.value === 'dark') {
            resolvedTheme = data.value as Theme
            localStorage.setItem('theme', resolvedTheme)
            applyTheme(resolvedTheme)
          }
        }
        // 401/403 = not logged in → keep light default
      } catch {
        // Fetch error → keep localStorage/default theme
      }

      setThemeState(resolvedTheme)
      setMounted(true)
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
    logger.debug('[THEME DEBUG] === Setting Theme ===')
    logger.debug('[THEME DEBUG] New theme:', newTheme)

    setThemeState(newTheme)

    if (typeof window !== 'undefined') {
      logger.debug('[THEME DEBUG] Saving to localStorage...')
      localStorage.setItem('theme', newTheme)
      logger.debug('[THEME DEBUG] ✅ Saved to localStorage')
    }

    logger.debug('[THEME DEBUG] Applying theme to DOM...')
    applyTheme(newTheme)
    logger.debug('[THEME DEBUG] ✅ Applied to DOM')

    // Save to backend for logged-in users
    try {
      const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/settings/theme`
      logger.debug('[THEME DEBUG] Saving to backend:', url)

      const body = { value: newTheme }
      logger.debug('[THEME DEBUG] Request body:', body)

      const response = await fetch(url, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })

      logger.debug('[THEME DEBUG] Response status:', response.status)
      logger.debug('[THEME DEBUG] Response ok:', response.ok)

      if (response.ok) {
        const data = await response.json()
        logger.debug('[THEME DEBUG] ✅✅✅ Saved theme to backend successfully:', data)
      } else {
        const errorText = await response.text()
        logger.debug('[THEME DEBUG] ❌ Backend save failed:', response.status, errorText)
      }
    } catch (error) {
      logger.debug('[THEME DEBUG] ❌ Could not save theme to backend:', error)
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