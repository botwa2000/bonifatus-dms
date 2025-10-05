// frontend/src/app/settings/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/use-auth'
import { apiClient } from '@/services/api-client'

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
  const { isAuthenticated, user, isLoading } = useAuth()
  const router = useRouter()
  const [preferences, setPreferences] = useState<UserPreferences | null>(null)
  const [systemSettings, setSystemSettings] = useState<SystemSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

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
    
    try {
      await apiClient.put('/api/v1/users/preferences', preferences, true)
      setMessage({ type: 'success', text: 'Settings saved successfully' })
    } catch (error) {
      console.error('Failed to save settings:', error)
      setMessage({ type: 'error', text: 'Failed to save settings' })
    } finally {
      setSaving(false)
    }
  }

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
          <div className={`mb-6 rounded-lg border p-4 ${
            message.type === 'success' 
              ? 'bg-green-50 border-green-200 text-green-800' 
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            <p className="text-sm">{message.text}</p>
          </div>
        )}

        <div className="space-y-6">
          {/* Appearance Settings */}
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4">Appearance</h2>
            
            <div className="space-y-4">
              <div>
                <label htmlFor="theme" className="block text-sm font-medium text-neutral-700 mb-2">
                  Theme
                </label>
                <select
                  id="theme"
                  value={preferences.theme || systemSettings.default_theme}
                  onChange={(e) => setPreferences({ ...preferences, theme: e.target.value })}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
                >
                  {systemSettings.available_themes.map(theme => (
                    <option key={theme} value={theme}>
                      {theme.charAt(0).toUpperCase() + theme.slice(1)}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-neutral-500">Choose your preferred color theme</p>
              </div>
            </div>
          </div>

          {/* Language Settings */}
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4">Language & Region</h2>
            
            <div className="space-y-4">
              <div>
                <label htmlFor="language" className="block text-sm font-medium text-neutral-700 mb-2">
                  Interface Language
                </label>
                <select
                  id="language"
                  value={preferences.language}
                  onChange={(e) => setPreferences({ ...preferences, language: e.target.value })}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
                >
                  {systemSettings.available_languages.map(lang => (
                    <option key={lang} value={lang}>
                      {lang === 'en' ? 'English' : lang === 'de' ? 'Deutsch' : lang === 'ru' ? 'Русский' : lang}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-neutral-500">Select your preferred language for the interface</p>
              </div>

              <div>
                <label htmlFor="timezone" className="block text-sm font-medium text-neutral-700 mb-2">
                  Timezone
                </label>
                <select
                  id="timezone"
                  value={preferences.timezone}
                  onChange={(e) => setPreferences({ ...preferences, timezone: e.target.value })}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
                >
                  <option value="UTC">UTC</option>
                  <option value="Europe/Berlin">Europe/Berlin</option>
                  <option value="Europe/Moscow">Europe/Moscow</option>
                  <option value="America/New_York">America/New York</option>
                  <option value="America/Los_Angeles">America/Los Angeles</option>
                  <option value="Asia/Tokyo">Asia/Tokyo</option>
                </select>
                <p className="mt-1 text-xs text-neutral-500">Your timezone for displaying dates and times</p>
              </div>
            </div>
          </div>

          {/* Notifications Settings */}
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4">Notifications</h2>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-neutral-900">Email Notifications</p>
                  <p className="text-xs text-neutral-500">Receive email updates about your documents</p>
                </div>
                <button
                  type="button"
                  onClick={() => setPreferences({ ...preferences, notifications_enabled: !preferences.notifications_enabled })}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    preferences.notifications_enabled ? 'bg-admin-primary' : 'bg-neutral-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      preferences.notifications_enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* Document Processing Settings */}
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4">Document Processing</h2>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-neutral-900">AI Auto-Categorization</p>
                  <p className="text-xs text-neutral-500">Automatically suggest categories for uploaded documents</p>
                </div>
                <button
                  type="button"
                  onClick={() => setPreferences({ ...preferences, auto_categorization: !preferences.auto_categorization })}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    preferences.auto_categorization ? 'bg-admin-primary' : 'bg-neutral-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      preferences.auto_categorization ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end space-x-3">
            <Link
              href="/dashboard"
              className="px-4 py-2 text-sm font-medium text-neutral-700 bg-white border border-neutral-300 rounded-md hover:bg-neutral-50 transition-colors"
            >
              Cancel
            </Link>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-white bg-admin-primary rounded-md hover:bg-admin-primary/90 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}