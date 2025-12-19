// frontend/src/app/settings/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import { apiClient } from '@/services/api-client'
import { Card, CardHeader, CardContent, Button, Select, Alert, Input, Badge, Modal, ModalHeader, ModalContent, ModalFooter } from '@/components/ui'
import AppHeader from '@/components/AppHeader'
import { shouldLog } from '@/config/app.config'
import { delegateService, type Delegate } from '@/services/delegate.service'
import type { BadgeVariant } from '@/components/ui'

interface UserPreferences {
  language: string
  preferred_doc_languages: string[]
  timezone: string
  theme?: string
  notifications_enabled: boolean
  auto_categorization: boolean
  email_marketing_enabled: boolean
}

interface LanguageMetadata {
  code: string
  name: string
  native_name: string
}

interface SystemSettings {
  available_languages: string[]
  available_themes: string[]
  default_theme: string
  default_language: string
  language_metadata?: Record<string, LanguageMetadata>
}

interface DriveStatus {
  connected: boolean
  email: string | null
  connected_at: string | null
  token_expires_at: string | null
}

export default function SettingsPage() {
  const { user, isLoading, loadUser } = useAuth()
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [preferences, setPreferences] = useState<UserPreferences | null>(null)
  const [systemSettings, setSystemSettings] = useState<SystemSettings | null>(null)
  const [driveStatus, setDriveStatus] = useState<DriveStatus | null>(null)
  const [saving, setSaving] = useState(false)
  const [driveLoading, setDriveLoading] = useState(false)
  const [resettingCategories, setResettingCategories] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // Delegates state
  const [delegates, setDelegates] = useState<Delegate[]>([])
  const [delegatesLoading, setDelegatesLoading] = useState(false)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [isInviting, setIsInviting] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Load user data on mount for display purposes
  useEffect(() => {
    loadUser()
  }, [loadUser])

  // Load settings on mount
  // Security note: Middleware already protects this route (cookie check)
  // Backend API endpoints validate JWT on every call (actual security layer)
  // No need for redundant frontend auth check that causes race conditions
  useEffect(() => {
    loadSettings()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadSettings = async () => {
    if (shouldLog('debug')) console.log('[SETTINGS DEBUG] === Loading Settings Page ===')

    try {
      const [prefsData, sysData, driveData] = await Promise.all([
        apiClient.get<UserPreferences>('/api/v1/users/preferences', true),
        apiClient.get<{ settings: SystemSettings }>('/api/v1/settings', false),
        apiClient.get<DriveStatus>('/api/v1/users/drive/status', true)
      ])

      if (shouldLog('debug')) {
        console.log('[SETTINGS DEBUG] === User Preferences Loaded from DB ===')
        console.log('[SETTINGS DEBUG] Language:', prefsData.language)
        console.log('[SETTINGS DEBUG] Preferred Doc Languages:', prefsData.preferred_doc_languages)
        console.log('[SETTINGS DEBUG] Timezone:', prefsData.timezone)
        console.log('[SETTINGS DEBUG] Theme:', prefsData.theme || '(not set, using default)')
        console.log('[SETTINGS DEBUG] Notifications Enabled:', prefsData.notifications_enabled)
        console.log('[SETTINGS DEBUG] Auto Categorization:', prefsData.auto_categorization)

        console.log('[SETTINGS DEBUG] === System Settings ===')
        console.log('[SETTINGS DEBUG] Available Languages:', sysData.settings.available_languages)
        console.log('[SETTINGS DEBUG] Available Themes:', sysData.settings.available_themes)
        console.log('[SETTINGS DEBUG] Default Theme:', sysData.settings.default_theme)
        console.log('[SETTINGS DEBUG] Default Language:', sysData.settings.default_language)
      }

      setPreferences(prefsData)
      setSystemSettings(sysData.settings)
      setDriveStatus(driveData)

      // Load delegates
      await loadDelegates()
    } catch {
      // Error already logged by API client, just show user message
      if (shouldLog('debug')) console.log('[SETTINGS DEBUG] ❌ Failed to load settings')
      setMessage({ type: 'error', text: 'Failed to load settings. Please try again.' })
    }
  }

  const loadDelegates = async () => {
    try {
      setDelegatesLoading(true)
      const response = await delegateService.listMyDelegates()
      setDelegates(response.delegates)
    } catch (error) {
      console.error('Failed to load delegates:', error)
    } finally {
      setDelegatesLoading(false)
    }
  }

  const handleInviteDelegate = async () => {
    if (!inviteEmail.trim()) {
      setMessage({ type: 'error', text: 'Please enter an email address' })
      return
    }

    setIsInviting(true)
    setMessage(null)

    try {
      await delegateService.inviteDelegate({
        email: inviteEmail.trim(),
        role: 'viewer'
      })

      setMessage({ type: 'success', text: `Invitation sent to ${inviteEmail}` })
      setInviteEmail('')
      setShowInviteModal(false)
      await loadDelegates()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send invitation. Please try again.'
      setMessage({
        type: 'error',
        text: errorMessage
      })
    } finally {
      setIsInviting(false)
    }
  }

  const handleRevokeAccess = async (delegate: Delegate) => {
    if (!confirm(`Revoke access for ${delegate.delegate_email}? They will no longer be able to view your documents.`)) {
      return
    }

    try {
      await delegateService.revokeAccess(delegate.id)
      setMessage({ type: 'success', text: 'Delegate access revoked' })
      await loadDelegates()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to revoke access. Please try again.'
      setMessage({
        type: 'error',
        text: errorMessage
      })
    }
  }

  const getStatusBadge = (status: string): { variant: BadgeVariant, label: string } => {
    switch (status) {
      case 'active':
        return { variant: 'success', label: 'Active' }
      case 'pending':
        return { variant: 'warning', label: 'Pending' }
      case 'revoked':
        return { variant: 'error', label: 'Revoked' }
      default:
        return { variant: 'default', label: status }
    }
  }

  const handleSave = async () => {
    if (!preferences) return

    if (shouldLog('debug')) {
      console.log('[SETTINGS DEBUG] === Save Button Clicked ===')
      console.log('[SETTINGS DEBUG] Saving preferences to backend...')
      console.log('[SETTINGS DEBUG] Components being saved:')
      console.log('[SETTINGS DEBUG]   - Language:', preferences.language)
      console.log('[SETTINGS DEBUG]   - Preferred Doc Languages:', preferences.preferred_doc_languages)
      console.log('[SETTINGS DEBUG]   - Timezone:', preferences.timezone)
      console.log('[SETTINGS DEBUG]   - Theme:', preferences.theme)
      console.log('[SETTINGS DEBUG]   - Notifications Enabled:', preferences.notifications_enabled)
      console.log('[SETTINGS DEBUG]   - Auto Categorization:', preferences.auto_categorization)
      console.log('[SETTINGS DEBUG] Endpoint: PUT /api/v1/users/preferences')
    }

    setSaving(true)
    setMessage(null)

    const oldLanguage = preferences.language

    try {
      await apiClient.put('/api/v1/users/preferences', preferences, true)

      if (shouldLog('debug')) {
        console.log('[SETTINGS DEBUG] ✅ Preferences saved successfully to database')
        console.log('[SETTINGS DEBUG] Theme was saved as:', preferences.theme)
      }

      setMessage({ type: 'success', text: 'Settings saved successfully' })

      if (preferences.language !== oldLanguage) {
        if (shouldLog('debug')) console.log('[SETTINGS DEBUG] Language changed, reloading page...')
        setMessage({ type: 'success', text: 'Settings saved. Reloading to apply language changes...' })
        setTimeout(() => {
          window.location.href = '/dashboard'
        }, 1500)
      }
    } catch (error) {
      // Error already logged by API client
      if (shouldLog('debug')) {
        console.log('[SETTINGS DEBUG] ❌ Failed to save preferences')
        console.error('[SETTINGS DEBUG] Error:', error)
      }
      setMessage({ type: 'error', text: 'Failed to save settings. Please try again.' })
    } finally {
      setSaving(false)
    }
  }

  const handleThemeChange = (newTheme: string) => {
    if (shouldLog('debug')) {
      console.log('[SETTINGS DEBUG] === Theme Changed in UI ===')
      console.log('[SETTINGS DEBUG] New theme selected:', newTheme)
      console.log('[SETTINGS DEBUG] Note: Theme will be saved to DB when "Save Changes" is clicked')
    }

    setPreferences({ ...preferences!, theme: newTheme })
    if (mounted && typeof window !== 'undefined') {
      localStorage.setItem('theme', newTheme)
      const root = document.documentElement
      root.classList.remove('light', 'dark')
      root.classList.add(newTheme)

      if (shouldLog('debug')) {
        console.log('[SETTINGS DEBUG] Applied theme to DOM immediately for preview')
        console.log('[SETTINGS DEBUG] Saved theme to localStorage for persistence')
      }
    }
  }

  const handleConnectDrive = async () => {
    setDriveLoading(true)
    setMessage(null)

    try {
      // Get OAuth config from backend (includes user ID as state)
      const config = await apiClient.get<{
        google_client_id: string
        redirect_uri: string
        scope: string
        state: string
        login_hint: string
      }>('/api/v1/users/drive/oauth-config', true)

      // Build Google OAuth URL client-side (same pattern as login OAuth)
      const params = new URLSearchParams({
        client_id: config.google_client_id,
        redirect_uri: config.redirect_uri,
        response_type: 'code',
        scope: config.scope,
        access_type: 'offline',
        prompt: 'consent',
        state: config.state,
        login_hint: config.login_hint
      })

      const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`

      // Redirect directly to Google (no backend redirect)
      window.location.href = oauthUrl
    } catch (error) {
      console.error('Drive OAuth initialization failed:', error)
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

  const handleResetCategories = async () => {
    if (!confirm('Are you sure you want to reset to default categories? This will DELETE ALL your custom categories and restore only the system default categories. This action cannot be undone.')) {
      return
    }

    setResettingCategories(true)
    setMessage(null)

    try {
      console.log('[CATEGORY RESET] Resetting categories to defaults...')
      const response = await apiClient.post<{ message: string, created: string[], skipped: string[] }>(
        '/api/v1/categories/restore-defaults',
        {},
        true
      )
      console.log('[CATEGORY RESET] ✅ Reset successful:', response)
      console.log(`[CATEGORY RESET] Created categories: ${response.created.join(', ')}`)
      console.log(`[CATEGORY RESET] Message: ${response.message}`)
      setMessage({ type: 'success', text: response.message })
    } catch (error) {
      console.error('[CATEGORY RESET] ❌ Reset failed:', error)
      setMessage({ type: 'error', text: 'Failed to reset categories. Please try again.' })
    } finally {
      setResettingCategories(false)
    }
  }

  const toggleDocLanguage = (langCode: string) => {
    if (!preferences) return

    const currentLangs = preferences.preferred_doc_languages || [preferences.language]
    if (currentLangs.includes(langCode)) {
      // Don't allow removing the last language
      if (currentLangs.length === 1) {
        setMessage({ type: 'error', text: 'You must have at least one document language selected' })
        return
      }
      setPreferences({
        ...preferences,
        preferred_doc_languages: currentLangs.filter(l => l !== langCode)
      })
    } else {
      setPreferences({
        ...preferences,
        preferred_doc_languages: [...currentLangs, langCode]
      })
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

  // Get language display name from database metadata
  const getLanguageName = (code: string): string => {
    if (systemSettings.language_metadata && systemSettings.language_metadata[code]) {
      return systemSettings.language_metadata[code].native_name
    }
    return code.toUpperCase()
  }

  const languageOptions = systemSettings.available_languages.map(lang => ({
    value: lang,
    label: getLanguageName(lang)
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
      <AppHeader title="Settings" />

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

              <div className="mt-6">
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Document Languages
                </label>
                <p className="text-xs text-neutral-500 mb-3">
                  Select which languages you work with. Categories will be auto-translated to these languages.
                </p>
                <div className="space-y-2">
                  {systemSettings.available_languages.map(langCode => {
                    const currentLangs = preferences.preferred_doc_languages || [preferences.language]
                    const isSelected = currentLangs.includes(langCode)

                    return (
                      <label
                        key={langCode}
                        className="flex items-center space-x-3 p-3 border border-neutral-200 rounded-lg cursor-pointer hover:bg-neutral-50"
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleDocLanguage(langCode)}
                          className="h-4 w-4 text-admin-primary border-neutral-300 rounded focus:ring-admin-primary"
                        />
                        <span className="text-sm text-neutral-900">
                          {getLanguageName(langCode)}
                        </span>
                      </label>
                    )
                  })}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Email Communications" />
            <CardContent>
              <div className="space-y-4">
                <ToggleSwitch
                  enabled={true}
                  onChange={() => {}}
                  label="Essential Emails (Required)"
                  description="Security alerts, password resets, and critical service updates. Cannot be disabled for compliance."
                />

                <div className="pt-4 border-t border-neutral-200">
                  <ToggleSwitch
                    enabled={preferences.email_marketing_enabled}
                    onChange={() => setPreferences({ ...preferences, email_marketing_enabled: !preferences.email_marketing_enabled })}
                    label="Product Updates & Tips"
                    description="Welcome emails, feature announcements, and helpful tips (optional)"
                  />
                </div>
              </div>
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

              <div className="mt-6 pt-6 border-t border-neutral-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-neutral-900">Reset Categories</p>
                    <p className="text-xs text-neutral-500">Delete all custom categories and restore system defaults</p>
                  </div>
                  <Button
                    variant="secondary"
                    onClick={handleResetCategories}
                    disabled={resettingCategories}
                  >
                    {resettingCategories ? 'Resetting...' : 'Reset'}
                  </Button>
                </div>
              </div>
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

          {/* Team Access Section - Pro Tier Only */}
          {user && user.tier === 'Professional' && (
            <Card>
              <CardHeader title="Team Access" />
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-neutral-900">Delegate Access</p>
                      <p className="text-xs text-neutral-500">
                        Share read-only access to your documents with team members or assistants
                      </p>
                    </div>
                    <Button
                      variant="primary"
                      onClick={() => setShowInviteModal(true)}
                    >
                      Invite Delegate
                    </Button>
                  </div>

                  {delegatesLoading ? (
                    <div className="text-center py-8">
                      <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
                      <p className="mt-4 text-sm text-neutral-600">Loading delegates...</p>
                    </div>
                  ) : delegates.length > 0 ? (
                    <div className="mt-6">
                      <div className="overflow-hidden border border-neutral-200 rounded-lg">
                        <table className="min-w-full divide-y divide-neutral-200">
                          <thead className="bg-neutral-50">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                                Email
                              </th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                                Status
                              </th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                                Invited
                              </th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">
                                Actions
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-neutral-200">
                            {delegates.map((delegate) => {
                              const badge = getStatusBadge(delegate.status)
                              return (
                                <tr key={delegate.id}>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-900">
                                    {delegate.delegate_email}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap">
                                    <Badge variant={badge.variant}>{badge.label}</Badge>
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-500">
                                    {delegate.invitation_sent_at ? new Date(delegate.invitation_sent_at).toLocaleDateString() : '—'}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                                    {delegate.status === 'active' || delegate.status === 'pending' ? (
                                      <Button
                                        variant="danger"
                                        onClick={() => handleRevokeAccess(delegate)}
                                      >
                                        Revoke
                                      </Button>
                                    ) : (
                                      <span className="text-neutral-400">—</span>
                                    )}
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 border-2 border-dashed border-neutral-200 rounded-lg">
                      <svg
                        className="mx-auto h-12 w-12 text-neutral-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                        />
                      </svg>
                      <p className="mt-2 text-sm text-neutral-600">No delegates yet</p>
                      <p className="text-xs text-neutral-500">Invite team members to share access to your documents</p>
                    </div>
                  )}

                  <p className="text-xs text-neutral-500">
                    Delegates have read-only access to all your documents. They can view and download but cannot upload, edit, or delete.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Invite Delegate Modal */}
          {showInviteModal && (
            <Modal isOpen={showInviteModal} onClose={() => setShowInviteModal(false)}>
              <ModalHeader
                title="Invite Delegate"
                onClose={() => setShowInviteModal(false)}
              />
              <ModalContent>
                <p className="text-sm text-neutral-600 mb-4">
                  Send an invitation to grant read-only access to your documents. The recipient will receive an email with an acceptance link.
                </p>
                <Input
                  label="Email Address"
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@example.com"
                  disabled={isInviting}
                />
                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <p className="text-xs text-blue-800 font-medium">Delegate Permissions:</p>
                  <ul className="mt-2 text-xs text-blue-700 space-y-1">
                    <li>✓ View and search all your documents</li>
                    <li>✓ Download documents for review</li>
                    <li>✗ Cannot upload, edit, or delete documents</li>
                  </ul>
                </div>
              </ModalContent>
              <ModalFooter>
                <Button
                  variant="secondary"
                  onClick={() => setShowInviteModal(false)}
                  disabled={isInviting}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={handleInviteDelegate}
                  disabled={isInviting}
                >
                  {isInviting ? 'Sending...' : 'Send Invitation'}
                </Button>
              </ModalFooter>
            </Modal>
          )}

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