// frontend/src/app/settings/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import { apiClient } from '@/services/api-client'
import { Card, CardHeader, CardContent, Button, Select, Alert, Input, Badge, Modal, ModalHeader, ModalContent, ModalFooter } from '@/components/ui'
import AppHeader from '@/components/AppHeader'
import { logger } from '@/lib/logger'
import { delegateService, type Delegate, type GrantedAccess, type PendingInvitation } from '@/services/delegate.service'
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

  // Delegates state (for owners - Pro tier only)
  const [delegates, setDelegates] = useState<Delegate[]>([])
  const [delegatesLoading, setDelegatesLoading] = useState(false)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [isInviting, setIsInviting] = useState(false)

  // Shared with Me state (for all users)
  const [pendingInvitations, setPendingInvitations] = useState<PendingInvitation[]>([])
  const [grantedAccess, setGrantedAccess] = useState<GrantedAccess[]>([])
  const [sharedLoading, setSharedLoading] = useState(false)
  const [respondingToInvite, setRespondingToInvite] = useState<string | null>(null)

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
    logger.debug('[SETTINGS DEBUG] === Loading Settings Page ===')

    try {
      const [prefsData, sysData, driveData] = await Promise.all([
        apiClient.get<UserPreferences>('/api/v1/users/preferences', true),
        apiClient.get<{ settings: SystemSettings }>('/api/v1/settings', false),
        apiClient.get<DriveStatus>('/api/v1/users/drive/status', true)
      ])

      logger.debug('[SETTINGS DEBUG] === User Preferences Loaded from DB ===')
      logger.debug('[SETTINGS DEBUG] Language:', prefsData.language)
      logger.debug('[SETTINGS DEBUG] Preferred Doc Languages:', prefsData.preferred_doc_languages)
      logger.debug('[SETTINGS DEBUG] Timezone:', prefsData.timezone)
      logger.debug('[SETTINGS DEBUG] Theme:', prefsData.theme || '(not set, using default)')
      logger.debug('[SETTINGS DEBUG] Notifications Enabled:', prefsData.notifications_enabled)
      logger.debug('[SETTINGS DEBUG] Auto Categorization:', prefsData.auto_categorization)

      logger.debug('[SETTINGS DEBUG] === System Settings ===')
      logger.debug('[SETTINGS DEBUG] Available Languages:', sysData.settings.available_languages)
      logger.debug('[SETTINGS DEBUG] Available Themes:', sysData.settings.available_themes)
      logger.debug('[SETTINGS DEBUG] Default Theme:', sysData.settings.default_theme)
      logger.debug('[SETTINGS DEBUG] Default Language:', sysData.settings.default_language)

      setPreferences(prefsData)
      setSystemSettings(sysData.settings)
      setDriveStatus(driveData)

      // Load delegates (only if Pro tier)
      if (user && (user.tier_id === 2 || user.is_admin)) {
        await loadDelegates()
      }

      // Load shared with me (for all users)
      await loadSharedWithMe()
    } catch {
      // Error already logged by API client, just show user message
      logger.debug('[SETTINGS DEBUG] ❌ Failed to load settings')
      setMessage({ type: 'error', text: 'Failed to load settings. Please try again.' })
    }
  }

  const loadDelegates = async () => {
    try {
      setDelegatesLoading(true)
      const response = await delegateService.listMyDelegates()
      setDelegates(response.delegates)
    } catch (error) {
      logger.error('Failed to load delegates:', error)
    } finally {
      setDelegatesLoading(false)
    }
  }

  const loadSharedWithMe = async () => {
    try {
      setSharedLoading(true)
      const [pendingResponse, grantedResponse] = await Promise.all([
        delegateService.getPendingInvitations(),
        delegateService.listGrantedAccess()
      ])
      setPendingInvitations(pendingResponse.invitations)
      setGrantedAccess(grantedResponse.granted_access)
    } catch (error) {
      logger.error('Failed to load shared access:', error)
    } finally {
      setSharedLoading(false)
    }
  }

  const handleInviteDelegate = async (allowUnregistered = false) => {
    if (!inviteEmail.trim()) {
      setMessage({ type: 'error', text: 'Please enter an email address' })
      return
    }

    setIsInviting(true)
    setMessage(null)

    try {
      await delegateService.inviteDelegate({
        email: inviteEmail.trim(),
        role: 'viewer',
        allow_unregistered: allowUnregistered
      })

      setMessage({ type: 'success', text: `Invitation sent to ${inviteEmail}` })
      setInviteEmail('')
      setShowInviteModal(false)
      await loadDelegates()
    } catch (err: unknown) {
      logger.debug('[DELEGATE] Caught error:', err)
      logger.debug('[DELEGATE] Error type:', typeof err)
      logger.debug('[DELEGATE] Error keys:', err ? Object.keys(err as object) : 'null')

      const error = err as {
        status?: number
        error?: {
          detail?: { code?: string; message?: string } | string
        }
        response?: {
          status?: number
          data?: { detail?: { code?: string; message?: string } | string }
        }
        message?: string
      }

      // Check if this is a USER_NOT_REGISTERED error (409 Conflict)
      const status = error?.status || error?.response?.status
      logger.debug('[DELEGATE] Extracted status:', status)
      if (status === 409) {
        // Try multiple paths to get the detail object
        let detail = error?.response?.data?.detail || error?.error?.detail || error?.response?.data

        logger.debug('[DELEGATE DEBUG] 409 error detail:', detail)
        logger.debug('[DELEGATE DEBUG] Full error:', error)

        if (typeof detail === 'object' && detail?.code === 'USER_NOT_REGISTERED') {
          // Show confirmation dialog
          const confirmed = window.confirm(
            detail.message ||
            `The email ${inviteEmail.trim()} is not registered with BoniDoc. Would you like to send an invitation anyway? They will need to create an account first.`
          )

          if (confirmed) {
            // Retry with allow_unregistered flag
            await handleInviteDelegate(true)
            return
          } else {
            // User cancelled, clear the error message
            setMessage(null)
            return
          }
        }
      }

      // Handle other errors
      const errorMessage = typeof error?.error?.detail === 'string'
        ? error.error.detail
        : typeof error?.response?.data?.detail === 'string'
        ? error.response.data.detail
        : error instanceof Error
        ? error.message
        : 'Failed to send invitation. Please try again.'
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

  const handleRespondToInvitation = async (invitation: PendingInvitation, action: 'accept' | 'decline') => {
    setRespondingToInvite(invitation.id)
    setMessage(null)

    try {
      const response = await delegateService.respondToInvitation(invitation.id, action)
      setMessage({
        type: 'success',
        text: response.message
      })

      // Reload shared access data
      await loadSharedWithMe()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : `Failed to ${action} invitation. Please try again.`
      setMessage({
        type: 'error',
        text: errorMessage
      })
    } finally {
      setRespondingToInvite(null)
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
    if (!preferences || !systemSettings) return

    // Always include all available languages for document recognition
    const preferencesWithAllLanguages = {
      ...preferences,
      preferred_doc_languages: systemSettings.available_languages
    }

    logger.debug('[SETTINGS DEBUG] === Save Button Clicked ===')
    logger.debug('[SETTINGS DEBUG] Saving preferences to backend...')
    logger.debug('[SETTINGS DEBUG] Components being saved:')
    logger.debug('[SETTINGS DEBUG]   - Language:', preferencesWithAllLanguages.language)
    logger.debug('[SETTINGS DEBUG]   - Preferred Doc Languages (all):', preferencesWithAllLanguages.preferred_doc_languages)
    logger.debug('[SETTINGS DEBUG]   - Timezone:', preferencesWithAllLanguages.timezone)
    logger.debug('[SETTINGS DEBUG]   - Theme:', preferencesWithAllLanguages.theme)
    logger.debug('[SETTINGS DEBUG]   - Notifications Enabled:', preferencesWithAllLanguages.notifications_enabled)
    logger.debug('[SETTINGS DEBUG]   - Auto Categorization:', preferencesWithAllLanguages.auto_categorization)
    logger.debug('[SETTINGS DEBUG] Endpoint: PUT /api/v1/users/preferences')

    setSaving(true)
    setMessage(null)

    const oldLanguage = preferences.language

    try {
      await apiClient.put('/api/v1/users/preferences', preferencesWithAllLanguages, true)

      logger.debug('[SETTINGS DEBUG] ✅ Preferences saved successfully to database')
      logger.debug('[SETTINGS DEBUG] Theme was saved as:', preferences.theme)

      setMessage({ type: 'success', text: 'Settings saved successfully' })

      if (preferences.language !== oldLanguage) {
        logger.debug('[SETTINGS DEBUG] Language changed, reloading page...')
        setMessage({ type: 'success', text: 'Settings saved. Reloading to apply language changes...' })
        setTimeout(() => {
          window.location.href = '/dashboard'
        }, 1500)
      }
    } catch (error) {
      // Error already logged by API client
      logger.debug('[SETTINGS DEBUG] ❌ Failed to save preferences')
      logger.error('[SETTINGS DEBUG] Error:', error)
      setMessage({ type: 'error', text: 'Failed to save settings. Please try again.' })
    } finally {
      setSaving(false)
    }
  }

  const handleThemeChange = (newTheme: string) => {
    logger.debug('[SETTINGS DEBUG] === Theme Changed in UI ===')
    logger.debug('[SETTINGS DEBUG] New theme selected:', newTheme)
    logger.debug('[SETTINGS DEBUG] Note: Theme will be saved to DB when "Save Changes" is clicked')

    setPreferences({ ...preferences!, theme: newTheme })
    if (mounted && typeof window !== 'undefined') {
      localStorage.setItem('theme', newTheme)
      const root = document.documentElement
      root.classList.remove('light', 'dark')
      root.classList.add(newTheme)

      logger.debug('[SETTINGS DEBUG] Applied theme to DOM immediately for preview')
      logger.debug('[SETTINGS DEBUG] Saved theme to localStorage for persistence')
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
      logger.error('Drive OAuth initialization failed:', error)
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
      logger.debug('[CATEGORY RESET] Resetting categories to defaults...')
      const response = await apiClient.post<{ message: string, created: string[], skipped: string[] }>(
        '/api/v1/categories/restore-defaults',
        {},
        true
      )
      logger.debug('[CATEGORY RESET] ✅ Reset successful:', response)
      logger.debug(`[CATEGORY RESET] Created categories: ${response.created.join(', ')}`)
      logger.debug(`[CATEGORY RESET] Message: ${response.message}`)
      setMessage({ type: 'success', text: response.message })
    } catch (error) {
      logger.error('[CATEGORY RESET] ❌ Reset failed:', error)
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
                  Document Language Recognition
                </label>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <svg className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-blue-900 mb-2">
                        Your documents are automatically recognized in all supported languages
                      </p>
                      <p className="text-xs text-blue-700 mb-3">
                        The system will detect and process documents in any of the following languages:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {systemSettings.available_languages.map(langCode => (
                          <span
                            key={langCode}
                            className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-white text-blue-900 border border-blue-300"
                          >
                            {getLanguageName(langCode)}
                          </span>
                        ))}
                      </div>
                      <p className="text-xs text-blue-600 mt-3 italic">
                        More languages coming soon!
                      </p>
                    </div>
                  </div>
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

          {/* Shared with Me Section - All Users */}
          <Card>
            <CardHeader title="Shared with Me" />
            <CardContent>
              {sharedLoading ? (
                <div className="text-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
                  <p className="mt-4 text-sm text-neutral-600">Loading shared access...</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Pending Invitations */}
                  {pendingInvitations.length > 0 && (
                    <div>
                      <div className="flex items-center space-x-2 mb-4">
                        <h3 className="text-sm font-medium text-neutral-900">Pending Invitations</h3>
                        <Badge variant="warning">{pendingInvitations.length}</Badge>
                      </div>
                      <div className="space-y-3">
                        {pendingInvitations.map((invitation) => (
                          <div
                            key={invitation.id}
                            className="p-4 border border-yellow-200 bg-yellow-50 rounded-lg"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <p className="text-sm font-medium text-neutral-900">
                                  {invitation.owner_name}
                                </p>
                                <p className="text-xs text-neutral-500 mt-1">
                                  {invitation.owner_email} • Role: {invitation.role}
                                </p>
                                <p className="text-xs text-neutral-500 mt-1">
                                  Invited {invitation.invitation_sent_at ? new Date(invitation.invitation_sent_at).toLocaleDateString() : '—'}
                                  {invitation.invitation_expires_at && ` • Expires ${new Date(invitation.invitation_expires_at).toLocaleDateString()}`}
                                </p>
                              </div>
                              <div className="flex items-center space-x-2 ml-4">
                                <Button
                                  variant="primary"
                                  onClick={() => handleRespondToInvitation(invitation, 'accept')}
                                  disabled={respondingToInvite === invitation.id}
                                >
                                  {respondingToInvite === invitation.id ? 'Processing...' : 'Accept'}
                                </Button>
                                <Button
                                  variant="secondary"
                                  onClick={() => handleRespondToInvitation(invitation, 'decline')}
                                  disabled={respondingToInvite === invitation.id}
                                >
                                  Decline
                                </Button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Active Shared Access */}
                  {grantedAccess.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-neutral-900 mb-4">Active Shared Access</h3>
                      <div className="overflow-hidden border border-neutral-200 rounded-lg">
                        <table className="min-w-full divide-y divide-neutral-200">
                          <thead className="bg-neutral-50">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                                Owner
                              </th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                                Role
                              </th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                                Status
                              </th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                                Last Accessed
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-neutral-200">
                            {grantedAccess.map((access) => {
                              const badge = getStatusBadge(access.status)
                              return (
                                <tr key={access.id}>
                                  <td className="px-6 py-4 whitespace-nowrap">
                                    <div>
                                      <p className="text-sm font-medium text-neutral-900">{access.owner_name}</p>
                                      <p className="text-xs text-neutral-500">{access.owner_email}</p>
                                    </div>
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-900">
                                    {access.role}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap">
                                    <Badge variant={badge.variant}>{badge.label}</Badge>
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-500">
                                    {access.last_accessed_at
                                      ? new Date(access.last_accessed_at).toLocaleDateString()
                                      : 'Never'}
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Empty State */}
                  {pendingInvitations.length === 0 && grantedAccess.length === 0 && (
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
                          d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                        />
                      </svg>
                      <p className="mt-2 text-sm text-neutral-600">No shared access yet</p>
                      <p className="text-xs text-neutral-500">
                        When someone shares their documents with you, they will appear here
                      </p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Team Access Section - Pro Tier Only */}
          {user && (user.tier_id === 2 || user.is_admin) && (
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
                  onClick={() => handleInviteDelegate()}
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