// frontend/src/app/profile/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/auth-context'
import { useCurrency } from '@/contexts/currency-context'
import { apiClient } from '@/services/api-client'
import { Card, CardHeader, CardContent, Button, Input, Select, Modal, ModalHeader, ModalContent, ModalFooter, Alert, Badge, UsageMetric } from '@/components/ui'
import AppHeader from '@/components/AppHeader'
import CancellationModal from '@/components/CancellationModal'
import { logger } from '@/lib/logger'

interface UserProfile {
  id: string
  email: string
  full_name: string
  tier: string
  tier_id: number
  google_id: string
  profile_picture_url?: string
  created_at: string
  updated_at: string
  trial_start_date?: string
  trial_end_date?: string
  email_processing_address?: string
  email_processing_enabled?: boolean
}

interface UserStatistics {
  documents_count: number
  total_categories_count: number
  custom_categories_count: number
  storage_used_mb: number
  last_activity?: string
  monthly_usage?: {
    month_period: string
    pages_processed: number
    pages_limit: number | null
    pages_remaining: number
    volume_used_mb: number
    volume_limit_mb: number | null
    volume_remaining_mb: number
    period_start: string
    period_end: string
  }
}

interface Subscription {
  id: string
  tier_id: number
  tier_name: string
  billing_cycle: string
  status: string
  current_period_end: string
  cancel_at_period_end: boolean
  amount: number
  currency: string
  currency_symbol?: string
  created_at?: string
  stripe_price_id?: string
  pending_billing_cycle?: string
  pending_billing_cycle_date?: string
}

interface TierPlan {
  id: number
  name: string
  display_name: string
  price_monthly_cents: number
  price_yearly_cents: number
  currency: string
  currency_symbol: string
  description: string
  email_to_process_enabled?: boolean
}

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading, loadUser, logout } = useAuth()
  const { selectedCurrency, availableCurrencies, setSelectedCurrency } = useCurrency()
  const router = useRouter()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [fullName, setFullName] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteReason, setDeleteReason] = useState('')
  const [deleteFeedback, setDeleteFeedback] = useState('')
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [availableTiers, setAvailableTiers] = useState<TierPlan[]>([])
  const [loadingSubscription, setLoadingSubscription] = useState(true)
  const [processingSubscription, setProcessingSubscription] = useState(false)
  const [showCancelModal, setShowCancelModal] = useState(false)
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly')
  const [hasAttemptedAuth, setHasAttemptedAuth] = useState(false)
  const [showBillingChangeModal, setShowBillingChangeModal] = useState(false)
  const [billingChangePreview, setBillingChangePreview] = useState<{
    current_subscription: {
      tier_name: string
      billing_cycle: string
      amount: number
      currency: string
      currency_symbol: string
      period_end: string
    }
    new_subscription: {
      tier_name: string
      billing_cycle: string
      amount: number
      currency: string
      currency_symbol: string
      effective_date: string
    }
    change_details: {
      change_effective_date: string
      proration_info: string
      next_billing_date: string
    }
  } | null>(null)

  // Load user data on mount
  useEffect(() => {
    const attemptAuth = async () => {
      await loadUser()
      setHasAttemptedAuth(true)
    }
    attemptAuth()
  }, [loadUser])

  useEffect(() => {
    if (isAuthenticated) {
      loadProfileData()
      loadSubscriptionData()

      // Check if returning from Stripe payment portal
      const params = new URLSearchParams(window.location.search)
      if (params.get('payment_updated') === 'true') {
        setMessage({ type: 'success', text: 'Payment method updated successfully' })
        // Clean up URL
        window.history.replaceState({}, '', '/profile')
      }
    } else if (hasAttemptedAuth && !isLoading && !isAuthenticated) {
      // Only redirect after we've attempted auth AND loading completes AND user is not authenticated
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, hasAttemptedAuth, router])

  const loadProfileData = async () => {
    try {
      const [profileData, statsData] = await Promise.all([
        apiClient.get<UserProfile>('/api/v1/users/profile', true),
        apiClient.get<UserStatistics>('/api/v1/users/statistics', true)
      ])
      
      setProfile(profileData)
      setStatistics(statsData)
      setFullName(profileData.full_name)
    } catch (error) {
      logger.error('Failed to load profile:', error)
      setMessage({ type: 'error', text: 'Failed to load profile data' })
    }
  }

  const handleUpdateProfile = async () => {
    if (!profile) return

    // Validate email change
    if (newEmail && newEmail !== profile.email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(newEmail)) {
        setMessage({ type: 'error', text: 'Please enter a valid email address' })
        return
      }
    }

    // Validate password fields if attempting to change password
    if (newPassword || confirmPassword || currentPassword) {
      if (!currentPassword) {
        setMessage({ type: 'error', text: 'Current password is required to change password' })
        return
      }
      if (!newPassword) {
        setMessage({ type: 'error', text: 'New password is required' })
        return
      }
      if (newPassword !== confirmPassword) {
        setMessage({ type: 'error', text: 'New passwords do not match' })
        return
      }
      if (newPassword.length < 8) {
        setMessage({ type: 'error', text: 'Password must be at least 8 characters long' })
        return
      }
    }

    setSaving(true)
    setMessage(null)

    try {
      const updateData: Record<string, string> = { full_name: fullName }

      // Add email change if provided
      if (newEmail && newEmail !== profile.email) {
        updateData.new_email = newEmail
      }

      // Add password change if provided
      if (currentPassword && newPassword) {
        updateData.current_password = currentPassword
        updateData.new_password = newPassword
      }

      await apiClient.put('/api/v1/users/profile', updateData, true)

      const hasEmailChange = newEmail && newEmail !== profile.email
      const hasPasswordChange = currentPassword && newPassword

      let successMessage = 'Profile updated successfully'
      if (hasEmailChange && hasPasswordChange) {
        successMessage = 'Profile, email, and password updated successfully'
      } else if (hasEmailChange) {
        successMessage = 'Profile and email updated successfully'
      } else if (hasPasswordChange) {
        successMessage = 'Profile and password updated successfully'
      }

      setMessage({ type: 'success', text: successMessage })
      setEditMode(false)
      setNewEmail('')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      await loadProfileData()
    } catch (error: unknown) {
      logger.error('Failed to update profile:', error)
      const errorMessage = error && typeof error === 'object' && 'response' in error
        ? ((error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to update profile')
        : 'Failed to update profile'
      setMessage({ type: 'error', text: errorMessage })
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteAccount = async () => {
    setDeleting(true)
    setMessage(null)

    try {
      await apiClient.post('/api/v1/users/deactivate', {
        reason: deleteReason,
        feedback: deleteFeedback
      }, true)

      setMessage({ type: 'success', text: 'Account deactivated. Signing out...' })

      // Account is deleted, so clear local auth and redirect without calling backend logout
      setTimeout(() => {
        // Clear local storage and auth state
        if (typeof window !== 'undefined') {
          localStorage.removeItem('theme')
          localStorage.clear()
          document.documentElement.classList.remove('dark')
          document.documentElement.classList.add('light')
        }

        // Redirect to homepage
        window.location.href = '/'
      }, 2000)
    } catch (error) {
      logger.error('Failed to delete account:', error)
      setMessage({ type: 'error', text: 'Failed to deactivate account' })
      setDeleting(false)
    }
  }

  const loadSubscriptionData = async () => {
    try {
      setLoadingSubscription(true)
      const [subData, tiersResponse] = await Promise.all([
        apiClient.get<Subscription>('/api/v1/billing/subscription', true).catch(() => null),
        apiClient.get<{ tiers: TierPlan[] }>('/api/v1/settings/tiers/public', true)
      ])

      setSubscription(subData)
      setAvailableTiers(tiersResponse?.tiers || [])
      if (subData) {
        setBillingCycle(subData.billing_cycle as 'monthly' | 'yearly')
      }
    } catch (error) {
      logger.error('Failed to load subscription:', error)
    } finally {
      setLoadingSubscription(false)
    }
  }

  const handleUpgrade = async (tierId: number) => {
    setProcessingSubscription(true)
    setMessage(null)

    try {
      // If user has an active subscription, use update endpoint
      if (subscription) {
        const response = await apiClient.put(
          '/api/v1/billing/subscriptions/update',
          {
            tier_id: tierId,
            billing_cycle: billingCycle
          },
          true
        )

        setMessage({ type: 'success', text: 'Subscription upgraded successfully! Changes will take effect immediately with prorated billing.' })

        // Reload profile to show updated tier
        await loadProfileData()
        await loadSubscriptionData()
      } else {
        // No active subscription - create new checkout session
        // Validate currency is selected
        if (!selectedCurrency) {
          setMessage({ type: 'error', text: 'Please select a currency first' })
          setProcessingSubscription(false)
          return
        }

        const response = await apiClient.post<{ checkout_url: string }>(
          '/api/v1/billing/subscriptions/create-checkout',
          {
            tier_id: tierId,
            billing_cycle: billingCycle,
            currency: selectedCurrency.code
          },
          true
        )

        window.location.href = response.checkout_url
      }
    } catch (error) {
      logger.error('Failed to upgrade subscription:', error)
      setMessage({ type: 'error', text: 'Failed to upgrade subscription. Please try again.' })
    } finally {
      setProcessingSubscription(false)
    }
  }

  const handleCancellationSuccess = async () => {
    setMessage({ type: 'success', text: 'Subscription canceled successfully' })
    await loadSubscriptionData()
    await loadProfileData()
  }


  const handleUpdatePaymentMethod = async () => {
    setProcessingSubscription(true)
    setMessage(null)

    try {
      const response = await apiClient.post<{ url: string }>(
        '/api/v1/billing/subscriptions/portal',
        {},
        true
      )

      // Redirect to Stripe Customer Portal
      window.location.href = response.url
    } catch (error) {
      logger.error('Failed to open payment portal:', error)
      setMessage({ type: 'error', text: 'Failed to open payment management portal' })
      setProcessingSubscription(false)
    }
  }

  const getTierBadgeVariant = (tier: string): 'default' | 'success' | 'warning' | 'error' => {
    switch (tier?.toLowerCase()) {
      case 'premium': return 'warning'
      case 'enterprise': return 'success'
      default: return 'default'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const isTrialActive = profile?.trial_end_date && new Date(profile.trial_end_date) > new Date()

  const StatCard = ({ label, value }: { label: string; value: string | number }) => (
    <div className="bg-neutral-50 rounded-lg p-4">
      <p className="text-sm text-neutral-600">{label}</p>
      <p className="text-2xl font-bold text-neutral-900">{value}</p>
    </div>
  )

  const InfoRow = ({ label, value }: { label: string; value: string | React.ReactNode }) => (
    <div>
      <label className="block text-sm font-medium text-neutral-700 mb-1">{label}</label>
      <p className="text-neutral-900">{value}</p>
    </div>
  )

  if (isLoading || !profile || !statistics) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Loading profile...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  const deleteReasonOptions = [
    { value: '', label: 'Select a reason' },
    { value: 'no_longer_needed', label: 'No longer need the service' },
    { value: 'switching_service', label: 'Switching to another service' },
    { value: 'too_expensive', label: 'Too expensive' },
    { value: 'missing_features', label: 'Missing features' },
    { value: 'privacy_concerns', label: 'Privacy concerns' },
    { value: 'other', label: 'Other' }
  ]

  return (
    <div className="min-h-screen bg-neutral-50">
      <AppHeader title="Account Profile" subtitle="Manage your profile and settings" />

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        {message && (
          <div className="mb-6">
            <Alert type={message.type} message={message.text} />
          </div>
        )}

        <div className="space-y-6">
          <Card>
            <CardHeader 
              title="Profile Information"
              action={!editMode ? (
                <Button variant="ghost" size="sm" onClick={() => setEditMode(true)}>
                  Edit
                </Button>
              ) : undefined}
            />
            <CardContent>
              <div className="flex items-center space-x-4 mb-4">
                <div className="h-16 w-16 rounded-full bg-admin-primary flex items-center justify-center text-white text-2xl font-medium">
                  {profile.full_name?.charAt(0) || 'U'}
                </div>
                <Badge variant={getTierBadgeVariant(profile.tier)}>
                  {isTrialActive ? 'Premium Trial' : profile.tier?.toUpperCase() || 'FREE'}
                </Badge>
              </div>

              {editMode ? (
                <>
                  <Input
                    label="Full Name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />

                  <Input
                    label="Email Address"
                    type="email"
                    value={newEmail || profile.email}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder={profile.email}
                    disabled={!!profile.google_id}
                  />
                  {profile.google_id && (
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                      Email cannot be changed for Google accounts
                    </p>
                  )}

                  {!profile.google_id && (
                    <div className="mt-6 pt-6 border-t border-neutral-200 dark:border-neutral-700">
                      <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-4">Change Password (optional)</h4>
                      <div className="space-y-3">
                        <div className="relative">
                          <Input
                            label="Current Password"
                            type={showCurrentPassword ? "text" : "password"}
                            value={currentPassword}
                            onChange={(e) => setCurrentPassword(e.target.value)}
                            placeholder="Enter current password"
                          />
                          <button
                            type="button"
                            onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                            className="absolute right-3 top-9 text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
                          >
                            {showCurrentPassword ? (
                              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                              </svg>
                            ) : (
                              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            )}
                          </button>
                        </div>

                        <div className="relative">
                          <Input
                            label="New Password"
                            type={showNewPassword ? "text" : "password"}
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            placeholder="Enter new password (min 8 characters)"
                          />
                          <button
                            type="button"
                            onClick={() => setShowNewPassword(!showNewPassword)}
                            className="absolute right-3 top-9 text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
                          >
                            {showNewPassword ? (
                              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                              </svg>
                            ) : (
                              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            )}
                          </button>
                        </div>

                        <div className="relative">
                          <Input
                            label="Confirm New Password"
                            type={showConfirmPassword ? "text" : "password"}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="Confirm new password"
                          />
                          <button
                            type="button"
                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                            className="absolute right-3 top-9 text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
                          >
                            {showConfirmPassword ? (
                              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                              </svg>
                            ) : (
                              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="flex space-x-3 pt-4">
                    <Button onClick={handleUpdateProfile} disabled={saving}>
                      {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setEditMode(false)
                        setFullName(profile.full_name)
                        setCurrentPassword('')
                        setNewPassword('')
                        setConfirmPassword('')
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <InfoRow label="Full Name" value={profile.full_name} />
                  <InfoRow label="Email Address" value={
                    <>
                      {profile.email}
                      {profile.google_id && (
                        <p className="text-xs text-neutral-500 mt-1">Email cannot be changed (linked to Google account)</p>
                      )}
                      {!profile.google_id && (
                        <p className="text-xs text-neutral-500 mt-1">Email can be changed in edit mode</p>
                      )}
                    </>
                  } />
                  {(() => {
                    // Check if user's tier supports email processing
                    // Use subscription tier if available, otherwise fall back to profile tier_id
                    const tierIdToCheck = subscription?.tier_id ?? profile.tier_id
                    const userTier = availableTiers.find(t => t.id === tierIdToCheck)
                    const tierSupportsEmailProcessing = userTier?.email_to_process_enabled

                    if (tierSupportsEmailProcessing && profile.email_processing_enabled && profile.email_processing_address) {
                      // Pro/Premium user with email processing enabled - show processing email
                      return (
                        <InfoRow label="Document Processing Email" value={
                          <>
                            <span className="font-mono text-sm bg-blue-50 dark:bg-blue-900 px-2 py-1 rounded">
                              {profile.email_processing_address}
                            </span>
                            <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-2">
                              Send documents from <span className="font-semibold">{profile.email}</span> to this address to automatically process them.
                            </p>
                            <p className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">
                              Only emails from your registered account email are accepted.
                            </p>
                          </>
                        } />
                      )
                    }
                    return null
                  })()}
                  <InfoRow label="Member Since" value={formatDate(profile.created_at)} />
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Account Statistics" />
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard label="Documents" value={statistics.documents_count} />
                <StatCard
                  label="Categories"
                  value={`${statistics.total_categories_count}${statistics.custom_categories_count > 0 ? ` (${statistics.custom_categories_count} custom)` : ''}`}
                />
                <StatCard label="Storage Used" value={`${statistics.storage_used_mb} MB`} />
              </div>
            </CardContent>
          </Card>

          {statistics.monthly_usage && (
            <Card>
              <CardHeader title="Monthly Usage" />
              <CardContent>
                <div className="space-y-4">
                  <div className="text-sm text-neutral-600">
                    Period: {new Date(statistics.monthly_usage.period_start).toLocaleDateString()} - {new Date(statistics.monthly_usage.period_end).toLocaleDateString()}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <UsageMetric
                      label="Pages Processed"
                      value={statistics.monthly_usage.pages_processed}
                      limit={statistics.monthly_usage.pages_limit}
                      unit="pages"
                      remaining={statistics.monthly_usage.pages_remaining}
                    />
                    <UsageMetric
                      label="Upload Volume"
                      value={statistics.monthly_usage.volume_used_mb}
                      limit={statistics.monthly_usage.volume_limit_mb}
                      unit="MB"
                      remaining={statistics.monthly_usage.volume_remaining_mb}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {user?.is_admin && (
            <Card className="border-admin-primary">
              <CardHeader title="Administrator Access" />
              <CardContent>
                <div className="space-y-3">
                  <p className="text-sm text-neutral-600">
                    You have administrator privileges. Access the admin dashboard to manage users, tiers, and monitor system health.
                  </p>
                  <div className="flex items-center space-x-2">
                    <svg className="h-5 w-5 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <Link href="/admin" className="text-sm text-admin-primary hover:underline font-medium">
                      Go to Admin Dashboard →
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader title="Subscription & Billing" />
            <CardContent>
              {loadingSubscription ? (
                <div className="flex items-center justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-admin-primary border-t-transparent"></div>
                  <span className="ml-3 text-sm text-neutral-600">Loading subscription...</span>
                </div>
              ) : subscription && subscription.status === 'active' ? (
                <div className="space-y-4">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-green-900">{subscription.tier_name}</h3>
                        <p className="text-sm text-green-700 mt-1">
                          {subscription.billing_cycle === 'yearly' ? 'Annual' : 'Monthly'} billing •
                          {subscription.currency_symbol || subscription.currency}{(subscription.amount / 100).toFixed(2)}/{subscription.billing_cycle === 'yearly' ? 'year' : 'month'}
                        </p>
                        {subscription.pending_billing_cycle && subscription.pending_billing_cycle_date && (
                          <p className="text-xs text-blue-700 mt-2 font-medium">
                            → Switching to {subscription.pending_billing_cycle === 'yearly' ? 'annual' : 'monthly'} billing on {formatDate(subscription.pending_billing_cycle_date)}
                          </p>
                        )}
                      </div>
                      <Badge variant="success">Active</Badge>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-neutral-600">Next billing date:</span>
                      <span className="font-medium text-neutral-900">{formatDate(subscription.current_period_end)}</span>
                    </div>
                    {subscription.cancel_at_period_end && (
                      <Alert type="warning" message="Your subscription will be cancelled at the end of the current billing period." />
                    )}
                  </div>

                  {/* Tier Change Options */}
                  {!subscription.cancel_at_period_end && availableTiers.length > 0 && (
                    <div className="pt-4 border-t border-neutral-200 space-y-3">
                      <h4 className="font-medium text-neutral-900">Change Plan</h4>

                      {availableTiers
                        .filter(tier => tier.name.toLowerCase() !== 'free' && tier.id !== subscription.tier_id)
                        .map(tier => {
                          const isPro = tier.name.toLowerCase() === 'pro'
                          const isComingSoon = false // Pro tier is now available
                          const isUpgrade = tier.id > subscription.tier_id

                          return (
                            <div key={tier.id} className="border border-neutral-200 rounded-lg p-3">
                              <div className="flex items-center justify-between">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2">
                                    <h5 className="font-medium text-neutral-900">{tier.display_name}</h5>
                                    {isComingSoon && <Badge variant="warning" className="text-xs">Coming Soon</Badge>}
                                    {isUpgrade && !isComingSoon && <Badge variant="success" className="text-xs">Upgrade</Badge>}
                                  </div>
                                  <p className="text-xs text-neutral-600 mt-1">
                                    {subscription.billing_cycle === 'yearly'
                                      ? `${tier.currency_symbol}${(tier.price_yearly_cents / 100).toFixed(2)}/year`
                                      : `${tier.currency_symbol}${(tier.price_monthly_cents / 100).toFixed(2)}/month`
                                    }
                                  </p>
                                </div>
                                <Button
                                  variant={isUpgrade ? "primary" : "secondary"}
                                  size="sm"
                                  onClick={() => !isComingSoon && handleUpgrade(tier.id)}
                                  disabled={isComingSoon || processingSubscription}
                                >
                                  {isComingSoon ? 'Coming Soon' : isUpgrade ? 'Upgrade' : 'Switch'}
                                </Button>
                              </div>
                            </div>
                          )
                        })}

                      {/* Billing Cycle Change */}
                      {!subscription.pending_billing_cycle && (
                        <div className="border border-neutral-200 rounded-lg p-3 bg-blue-50">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <h5 className="font-medium text-blue-900">
                                Switch to {subscription.billing_cycle === 'yearly' ? 'Monthly' : 'Annual'} Billing
                              </h5>
                              <p className="text-xs text-blue-700 mt-1">
                                {subscription.billing_cycle === 'yearly'
                                  ? 'Change will take effect at the end of your current billing period'
                                  : 'Switch to annual billing and save. Change takes effect at period end.'
                                }
                              </p>
                            </div>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={async () => {
                              const newCycle = subscription.billing_cycle === 'yearly' ? 'monthly' : 'yearly'
                              setProcessingSubscription(true)
                              setMessage(null)

                              try {
                                // Get preview of billing cycle change
                                const previewResponse = await apiClient.post<{
                                  success: boolean
                                  current_subscription: {
                                    tier_name: string
                                    billing_cycle: string
                                    amount: number
                                    currency: string
                                    currency_symbol: string
                                    period_end: string
                                  }
                                  new_subscription: {
                                    tier_name: string
                                    billing_cycle: string
                                    amount: number
                                    currency: string
                                    currency_symbol: string
                                    effective_date: string
                                  }
                                  change_details: {
                                    change_effective_date: string
                                    proration_info: string
                                    next_billing_date: string
                                  }
                                }>(
                                  '/api/v1/billing/subscriptions/preview-billing-cycle-change',
                                  { billing_cycle: newCycle },
                                  true
                                )

                                if (previewResponse.success) {
                                  setBillingChangePreview(previewResponse)
                                  setShowBillingChangeModal(true)
                                }
                              } catch (error) {
                                logger.error('Failed to preview billing cycle change:', error)
                                setMessage({
                                  type: 'error',
                                  text: 'Failed to load billing cycle change preview. Please try again.'
                                })
                              } finally {
                                setProcessingSubscription(false)
                              }
                            }}
                            disabled={processingSubscription}
                          >
                            {processingSubscription ? 'Loading...' : 'Schedule Change'}
                          </Button>
                        </div>
                      </div>
                      )}
                    </div>
                  )}

                  <div className="space-y-2 pt-4 border-t border-neutral-200">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleUpdatePaymentMethod}
                      disabled={processingSubscription}
                      className="w-full"
                    >
                      Update Payment Method
                    </Button>

                    {!subscription.cancel_at_period_end && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowCancelModal(true)}
                        className="w-full text-red-600 hover:bg-red-50"
                      >
                        Cancel Subscription
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-neutral-900">Free Plan</h3>
                        <p className="text-sm text-neutral-600 mt-1">
                          {isTrialActive && profile.trial_end_date
                            ? `Premium trial ends ${formatDate(profile.trial_end_date)}`
                            : 'Basic features included'}
                        </p>
                      </div>
                      <Badge variant="default">Free</Badge>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="mb-4">
                      <p className="text-sm font-medium text-neutral-700 mb-3">Upgrade to unlock more features:</p>

                      <div className="flex items-center justify-between gap-3">
                        {/* Currency Selector */}
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-neutral-600">Currency:</span>
                          <select
                            value={selectedCurrency?.code || ''}
                            onChange={(e) => {
                              const currency = availableCurrencies.find(c => c.code === e.target.value)
                              if (currency) setSelectedCurrency(currency)
                            }}
                            className="px-3 py-1.5 text-sm border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-admin-primary"
                          >
                            {availableCurrencies.map(currency => (
                              <option key={currency.code} value={currency.code}>
                                {currency.code} ({currency.symbol})
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* Billing Cycle Toggle */}
                        <div className="flex items-center gap-2">
                          <Button
                            variant={billingCycle === 'monthly' ? 'primary' : 'secondary'}
                            size="sm"
                            onClick={() => setBillingCycle('monthly')}
                          >
                            Monthly
                          </Button>
                          <Button
                            variant={billingCycle === 'yearly' ? 'primary' : 'secondary'}
                            size="sm"
                            onClick={() => setBillingCycle('yearly')}
                          >
                            Yearly
                            {availableTiers.length > 0 && (() => {
                              const sampleTier = availableTiers.find(t => t.name.toLowerCase() !== 'free')
                              if (sampleTier && sampleTier.price_yearly_cents > 0 && sampleTier.price_monthly_cents > 0) {
                                const yearlyCostPerMonth = sampleTier.price_yearly_cents / 12
                                const monthlyCost = sampleTier.price_monthly_cents
                                const savingsPercent = Math.round(((monthlyCost - yearlyCostPerMonth) / monthlyCost) * 100)
                                return savingsPercent > 0 ? ` (Save ${savingsPercent}%)` : ''
                              }
                              return ''
                            })()}
                          </Button>
                        </div>
                      </div>
                    </div>

                    {availableTiers
                      .filter(tier => tier.name.toLowerCase() !== 'free')
                      .map(tier => {
                        const isPro = tier.name.toLowerCase() === 'pro'
                        const isComingSoon = false // Pro tier is now available

                        // Convert prices from base currency (EUR cents) to selected currency
                        const priceMonthlyInEur = tier.price_monthly_cents / 100
                        const priceYearlyInEur = tier.price_yearly_cents / 100

                        const priceMonthly = selectedCurrency
                          ? priceMonthlyInEur * selectedCurrency.exchange_rate
                          : priceMonthlyInEur

                        const priceYearly = selectedCurrency
                          ? priceYearlyInEur * selectedCurrency.exchange_rate
                          : priceYearlyInEur

                        const currencySymbol = selectedCurrency?.symbol || tier.currency_symbol
                        const decimalPlaces = selectedCurrency?.decimal_places || 2

                        return (
                          <div key={tier.id} className="border border-neutral-200 rounded-lg p-4 hover:border-admin-primary transition-colors">
                            <div className="flex items-start justify-between mb-3">
                              <div>
                                <h4 className="font-semibold text-neutral-900">{tier.display_name}</h4>
                                <p className="text-sm text-neutral-600 mt-1">{tier.description}</p>
                              </div>
                              {isComingSoon && <Badge variant="warning">Coming Soon</Badge>}
                            </div>

                            <div className="flex items-center justify-between">
                              <div>
                                {billingCycle === 'yearly' ? (
                                  <>
                                    <p className="text-2xl font-bold text-neutral-900">
                                      {currencySymbol}{priceYearly.toFixed(decimalPlaces)}
                                      <span className="text-sm font-normal text-neutral-600">/year</span>
                                    </p>
                                    <p className="text-xs text-neutral-500 mt-1">
                                      {currencySymbol}{(priceYearly / 12).toFixed(decimalPlaces)}/month
                                    </p>
                                  </>
                                ) : (
                                  <p className="text-2xl font-bold text-neutral-900">
                                    {currencySymbol}{priceMonthly.toFixed(decimalPlaces)}
                                    <span className="text-sm font-normal text-neutral-600">/month</span>
                                  </p>
                                )}
                              </div>

                              <Button
                                variant={isComingSoon ? "secondary" : "primary"}
                                size="sm"
                                onClick={() => !isComingSoon && handleUpgrade(tier.id)}
                                disabled={isComingSoon || processingSubscription}
                              >
                                {isComingSoon ? 'Coming Soon' : 'Upgrade'}
                              </Button>
                            </div>
                          </div>
                        )
                      })}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-red-200">
            <CardHeader title="Danger Zone" />
            <CardContent>
              <div>
                <h3 className="font-medium text-neutral-900 mb-2">Delete Account</h3>
                <p className="text-sm text-neutral-600 mb-4">
                  Once you delete your account, there is no going back. Your documents will remain in Google Drive, but all metadata and categorization will be permanently deleted immediately.
                </p>
                <Button variant="danger" onClick={() => setShowDeleteModal(true)}>
                  Delete Account
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>

      <Modal isOpen={showDeleteModal} onClose={() => setShowDeleteModal(false)}>
        <ModalHeader title="Delete Account" onClose={() => setShowDeleteModal(false)} />
        <ModalContent>
          <Alert
            type="error"
            message="Warning: This action cannot be undone. Your account and all associated data will be permanently deleted immediately."
          />

          <Alert
            type="info"
            message="Your documents are safe: All files in your Google Drive will remain intact. Only the Bonifatus DMS metadata and categorization will be deleted."
          />

          <Select
            label="Reason for leaving (optional)"
            value={deleteReason}
            onChange={(e) => setDeleteReason(e.target.value)}
            options={deleteReasonOptions}
          />

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Additional feedback (optional)
            </label>
            <textarea
              value={deleteFeedback}
              onChange={(e) => setDeleteFeedback(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
              placeholder="Help us improve by sharing your thoughts..."
            />
          </div>
        </ModalContent>
        <ModalFooter>
          <Button variant="danger" onClick={handleDeleteAccount} disabled={deleting} className="flex-1">
            {deleting ? 'Deleting...' : 'Yes, Delete My Account'}
          </Button>
          <Button variant="secondary" onClick={() => setShowDeleteModal(false)} disabled={deleting} className="flex-1">
            Cancel
          </Button>
        </ModalFooter>
      </Modal>

      {subscription && (
        <CancellationModal
          isOpen={showCancelModal}
          onClose={() => setShowCancelModal(false)}
          subscription={subscription}
          onSuccess={handleCancellationSuccess}
        />
      )}

      {/* Billing Cycle Change Confirmation Modal */}
      <Modal isOpen={showBillingChangeModal} onClose={() => setShowBillingChangeModal(false)}>
        <ModalHeader title="Confirm Billing Cycle Change" onClose={() => setShowBillingChangeModal(false)} />
        <ModalContent>
          {billingChangePreview && (
            <div className="space-y-4">
              <Alert
                type="info"
                message={billingChangePreview.change_details.proration_info}
              />

              {/* Current Subscription */}
              <div className="border border-neutral-200 rounded-lg p-4 bg-neutral-50">
                <h4 className="font-medium text-neutral-900 mb-2">Current Subscription</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Plan:</span>
                    <span className="font-medium text-neutral-900">{billingChangePreview.current_subscription.tier_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Billing Cycle:</span>
                    <span className="font-medium text-neutral-900 capitalize">{billingChangePreview.current_subscription.billing_cycle}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Price:</span>
                    <span className="font-medium text-neutral-900">
                      {billingChangePreview.current_subscription.currency_symbol}
                      {(billingChangePreview.current_subscription.amount / 100).toFixed(2)}/
                      {billingChangePreview.current_subscription.billing_cycle === 'yearly' ? 'year' : 'month'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Arrow */}
              <div className="flex justify-center">
                <svg className="h-6 w-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </div>

              {/* New Subscription */}
              <div className="border border-admin-primary rounded-lg p-4 bg-blue-50">
                <h4 className="font-medium text-admin-primary mb-2">New Subscription</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Plan:</span>
                    <span className="font-medium text-neutral-900">{billingChangePreview.new_subscription.tier_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Billing Cycle:</span>
                    <span className="font-medium text-neutral-900 capitalize">{billingChangePreview.new_subscription.billing_cycle}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Price:</span>
                    <span className="font-medium text-neutral-900">
                      {billingChangePreview.new_subscription.currency_symbol}
                      {(billingChangePreview.new_subscription.amount / 100).toFixed(2)}/
                      {billingChangePreview.new_subscription.billing_cycle === 'yearly' ? 'year' : 'month'}
                    </span>
                  </div>
                  <div className="flex justify-between pt-2 border-t border-admin-primary/20">
                    <span className="text-neutral-600">Effective Date:</span>
                    <span className="font-medium text-admin-primary">{billingChangePreview.change_details.change_effective_date}</span>
                  </div>
                </div>
              </div>

              <Alert
                type="warning"
                message="This change will take effect at the end of your current billing period. You will continue to have access to your current plan until then."
              />
            </div>
          )}
        </ModalContent>
        <ModalFooter>
          <Button
            variant="primary"
            onClick={async () => {
              setProcessingSubscription(true)
              setMessage(null)

              try {
                // Execute billing cycle change
                const response = await apiClient.post<{
                  success: boolean
                  message: string
                  change_effective_date: string
                }>(
                  '/api/v1/billing/subscriptions/schedule-billing-cycle-change',
                  { billing_cycle: billingChangePreview?.new_subscription.billing_cycle },
                  true
                )

                if (response.success) {
                  setMessage({
                    type: 'success',
                    text: response.message
                  })
                  setShowBillingChangeModal(false)
                  setBillingChangePreview(null)
                  await loadSubscriptionData()
                }
              } catch (error) {
                logger.error('Failed to schedule billing cycle change:', error)
                setMessage({
                  type: 'error',
                  text: 'Failed to schedule billing cycle change. Please try again.'
                })
              } finally {
                setProcessingSubscription(false)
              }
            }}
            disabled={processingSubscription}
            className="flex-1"
          >
            {processingSubscription ? 'Processing...' : 'Confirm Change'}
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setShowBillingChangeModal(false)
              setBillingChangePreview(null)
            }}
            disabled={processingSubscription}
            className="flex-1"
          >
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}