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

interface DriveStatus {
  connected: boolean
  email: string | null
  connected_at: string | null
  token_expires_at: string | null
}

export default function SettingsPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [preferences, setPreferences] = useState<UserPreferences | null>(null)
  const [systemSettings, setSystemSettings] = useState<SystemSettings | null>(null)
  const [driveStatus, setDriveStatus] = useState<DriveStatus | null>(null)
  const [saving, setSaving] = useState(false)
  const [driveLoading, setDriveLoading] = useState(false)
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
      const [prefsData, sysData, driveData] = await Promise.all([
        apiClient.get<UserPreferences>('/api/v1/users/preferences', true),
        apiClient.get<{ settings: SystemSettings }>('/api/v1/settings', false),
        apiClient.get<DriveStatus>('/api/v1/users/drive/status', true)
      ])

      setPreferences(prefsData)
      setSystemSettings(sysData.settings)
      setDriveStatus(driveData)
    } catch {
      // Error already logged by API client, just show user message
      setMessage({ type: 'error', text: 'Failed to load settings. Please try again.' })
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
    } catch {
      // Error already logged by API client
      setMessage({ type: 'error', text: 'Failed to save settings. Please try again.' })
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

  const handleConnectDrive = async () => {
    setDriveLoading(true)
    try {
      // Redirect to backend OAuth endpoint
      window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/drive/connect`
    } catch {
      setMessage({ type: 'error', text: 'Failed to initiate Drive connection' })
      setDriveLoading(false)
    }
  }

  const handleDisconnectDrive = async () => {
    if (!confirm('Are you sure you want to disconnect Google Drive? Your documents will remain in Drive.')) {
      return
    }

    setDriveLoading(true)
    setMessage(null)

    try {
      await apiClient.post('/api/v1/users/drive/disconnect', {}, true)
      setMessage({ type: 'success', text: 'Google Drive disconnected successfully' })

      // Reload Drive status
      const driveData = await apiClient.get<DriveStatus>('/api/v1/users/drive/status', true)
      setDriveStatus(driveData)
    } catch {
      setMessage({ type: 'error', text: 'Failed to disconnect Drive. Please try again.' })
    } finally {
      setDriveLoading(false)
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

  if (isLoading || !preferences || !systemSettings || !driveStatus) {
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

          <Card>
            <CardHeader title="Cloud Storage" />
            <CardContent>
              {driveStatus.connected ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0">
                        <svg className="h-10 w-10 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a6.033 6.033 0 110-12.064c1.498 0 2.866.549 3.921 1.453l2.814-2.814A9.969 9.969 0 0012.545 2C7.021 2 2.543 6.477 2.543 12s4.478 10 10.002 10c8.396 0 10.249-7.85 9.426-11.748l-9.426-.013z"/>
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-neutral-900">Google Drive Connected</p>
                        <p className="text-xs text-neutral-500">{driveStatus.email}</p>
                        {driveStatus.connected_at && (
                          <p className="text-xs text-neutral-400">
                            Connected {new Date(driveStatus.connected_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="secondary"
                      onClick={handleDisconnectDrive}
                      disabled={driveLoading}
                    >
                      {driveLoading ? 'Disconnecting...' : 'Disconnect'}
                    </Button>
                  </div>
                  <p className="text-xs text-neutral-500">
                    Your documents are automatically saved to Google Drive with full version history and sharing capabilities.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0">
                        <svg className="h-10 w-10 text-neutral-400" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a6.033 6.033 0 110-12.064c1.498 0 2.866.549 3.921 1.453l2.814-2.814A9.969 9.969 0 0012.545 2C7.021 2 2.543 6.477 2.543 12s4.478 10 10.002 10c8.396 0 10.249-7.85 9.426-11.748l-9.426-.013z"/>
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-neutral-900">Connect Google Drive</p>
                        <p className="text-xs text-neutral-500">Store your documents securely in the cloud</p>
                      </div>
                    </div>
                    <Button
                      variant="primary"
                      onClick={handleConnectDrive}
                      disabled={driveLoading}
                    >
                      {driveLoading ? 'Connecting...' : 'Connect'}
                    </Button>
                  </div>
                  <p className="text-xs text-neutral-500">
                    Connect your Google Drive to automatically sync and backup your documents with version control and easy sharing.
                  </p>
                </div>
              )}
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