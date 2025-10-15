// frontend/src/app/settings/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/auth-context'
import { apiClient } from '@/services/api-client'
import { Card, CardHeader, CardContent, Button, Select, Alert } from '@/components/ui'

interface UserPreferences {
  language: string
  timezone: string
  theme?: string
  notifications_enabled: boolean
  auto_categorization: boolean
}

interface SystemSettings {
  available_languages: string[]
  available_themes: string[]
  default_theme: string
  default_language: string
}

export default function SettingsPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [preferences, setPreferences] = useState<UserPreferences | null>(null)
  const [systemSettings, setSystemSettings] = useState<SystemSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  useEffect(() => {
    if (isAuthenticated) {
      loadSettings()
    }
  }, [isAuthenticated])

  const loadSettings = async () => {
    try {
      const [prefsData, sysData] = await Promise.all([
        apiClient.get<UserPreferences>('/api/v1/users/preferences', true),
        apiClient.get<{ settings: SystemSettings }>('/api/v1/settings/public', false)
      ])
      
      setPreferences(prefsData)
      setSystemSettings(sysData.settings)
    } catch (error) {
      console.error('Failed to load settings:', error)
      setMessage({ type: 'error', text: 'Failed to load settings' })
    }
  }

  const handleSave = async () => {
    if (!preferences) return
    
    setSaving(true)
    setMessage(null)
    
    const oldLanguage = preferences.language
    
    try {
      await apiClient.put('/api/v1/users/preferences', preferences, true)
      setMessage({ type: 'success', text: 'Settings saved successfully' })
      
      if (preferences.language !== oldLanguage) {
        setMessage({ type: 'success', text: 'Settings saved. Reloading to apply language changes...' })
        setTimeout(() => {
          window.location.href = '/dashboard'
        }, 1500)
      }
    } catch (error) {
      console.error('Failed to save settings:', error)
      setMessage({ type: 'error', text: 'Failed to save settings' })
    } finally {
      setSaving(false)
    }
  }

  const handleThemeChange = (newTheme: string) => {
    setPreferences({ ...preferences!, theme: newTheme })
    if (mounted && typeof window !== 'undefined') {
      localStorage.setItem('theme', newTheme)
      const root = document.documentElement
      root.classList.remove('light', 'dark')
      root.classList.add(newTheme)
    }
  }

  const ToggleSwitch = ({ enabled, onChange, label, description }: {
    enabled: boolean
    onChange: () => void
    label: string
    description: string
  }) => (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-neutral-900">{label}</p>
        <p className="text-xs text-neutral-500">{description}</p>
      </div>
      <button
        type="button"
        onClick={onChange}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          enabled ? 'bg-admin-primary' : 'bg-neutral-300'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            enabled ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  )

  if (isLoading || !preferences || !systemSettings) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Loading settings...</p>
        </div>
      </div>
    )
  }

  const languageOptions = systemSettings.available_languages.map(lang => ({
    value: lang,
    label: lang === 'en' ? 'English' : lang === 'de' ? 'Deutsch' : lang === 'ru' ? 'Русский' : lang
  }))

  const themeOptions = systemSettings.available_themes.map(theme => ({
    value: theme,
    label: theme.charAt(0).toUpperCase() + theme.slice(1)
  }))

  const timezoneOptions = [
    { value: 'UTC', label: 'UTC' },
    { value: 'Europe/Berlin', label: 'Europe/Berlin' },
    { value: 'Europe/Moscow', label: 'Europe/Moscow' },
    { value: 'America/New_York', label: 'America/New York' },
    { value: 'America/Los_Angeles', label: 'America/Los Angeles' },
    { value: 'Asia/Tokyo', label: 'Asia/Tokyo' }
  ]

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="bg-white shadow-sm border-b border-neutral-200">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-4">
            <Link href="/dashboard" className="text-neutral-600 hover:text-neutral-900">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </Link>
            <h1 className="text-2xl font-bold text-neutral-900">Settings</h1>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        {message && (
          <div className="mb-6">
            <Alert type={message.type} message={message.text} />
          </div>
        )}

        <div className="space-y-6">
          <Card>
            <CardHeader title="Appearance" />
            <CardContent>
              <Select
                label="Theme"
                hint="Choose your preferred color theme"
                value={preferences.theme || systemSettings.default_theme}
                onChange={(e) => handleThemeChange(e.target.value)}
                options={themeOptions}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Language & Region" />
            <CardContent>
              <Select
                label="Interface Language"
                hint="Select your preferred language for the interface"
                value={preferences.language}
                onChange={(e) => setPreferences({ ...preferences, language: e.target.value })}
                options={languageOptions}
              />
              
              <Select
                label="Timezone"
                hint="Your timezone for displaying dates and times"
                value={preferences.timezone}
                onChange={(e) => setPreferences({ ...preferences, timezone: e.target.value })}
                options={timezoneOptions}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Notifications" />
            <CardContent>
              <ToggleSwitch
                enabled={preferences.notifications_enabled}
                onChange={() => setPreferences({ ...preferences, notifications_enabled: !preferences.notifications_enabled })}
                label="Email Notifications"
                description="Receive email updates about your documents"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Document Processing" />
            <CardContent>
              <ToggleSwitch
                enabled={preferences.auto_categorization}
                onChange={() => setPreferences({ ...preferences, auto_categorization: !preferences.auto_categorization })}
                label="AI Auto-Categorization"
                description="Automatically suggest categories for uploaded documents"
              />
            </CardContent>
          </Card>

          <div className="flex justify-end space-x-3">
            <Button variant="secondary" onClick={() => router.push('/dashboard')}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}