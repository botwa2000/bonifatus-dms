// frontend/src/app/profile/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/auth-context'
import { apiClient } from '@/services/api-client'
import { Card, CardHeader, CardContent, Button, Input, Select, Modal, ModalHeader, ModalContent, ModalFooter, Alert, Badge } from '@/components/ui'
import AppHeader from '@/components/AppHeader'
import CancellationModal from '@/components/CancellationModal'

interface UserProfile {
  id: string
  email: string
  full_name: string
  tier: string
  google_id: string
  profile_picture_url?: string
  created_at: string
  updated_at: string
  trial_start_date?: string
  trial_end_date?: string
}

interface UserStatistics {
  documents_count: number
  categories_count: number
  storage_used_mb: number
  last_activity?: string
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
}

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading, loadUser, logout } = useAuth()
  const router = useRouter()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [fullName, setFullName] = useState('')
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
      console.error('Failed to load profile:', error)
      setMessage({ type: 'error', text: 'Failed to load profile data' })
    }
  }

  const handleUpdateProfile = async () => {
    if (!profile) return
    
    setSaving(true)
    setMessage(null)
    
    try {
      await apiClient.put('/api/v1/users/profile', { full_name: fullName }, true)
      setMessage({ type: 'success', text: 'Profile updated successfully' })
      setEditMode(false)
      await loadProfileData()
    } catch (error) {
      console.error('Failed to update profile:', error)
      setMessage({ type: 'error', text: 'Failed to update profile' })
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
      console.error('Failed to delete account:', error)
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
      console.error('Failed to load subscription:', error)
    } finally {
      setLoadingSubscription(false)
    }
  }

  const handleUpgrade = async (tierId: number) => {
    setProcessingSubscription(true)
    setMessage(null)

    try {
      // Currency comes from tier data - backend will use it
      const response = await apiClient.post<{ checkout_url: string }>(
        '/api/v1/billing/subscriptions/create-checkout',
        { tier_id: tierId, billing_cycle: billingCycle },
        true
      )

      window.location.href = response.checkout_url
    } catch (error) {
      console.error('Failed to create checkout:', error)
      setMessage({ type: 'error', text: 'Failed to start upgrade process' })
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
      console.error('Failed to open payment portal:', error)
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
                  <div className="flex space-x-3 pt-4">
                    <Button onClick={handleUpdateProfile} disabled={saving}>
                      {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                    <Button 
                      variant="secondary" 
                      onClick={() => {
                        setEditMode(false)
                        setFullName(profile.full_name)
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
                      <p className="text-xs text-neutral-500 mt-1">Email cannot be changed (linked to Google account)</p>
                    </>
                  } />
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
                <StatCard label="Categories" value={statistics.categories_count} />
                <StatCard label="Storage Used" value={`${statistics.storage_used_mb} MB`} />
              </div>
            </CardContent>
          </Card>

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
                          const isComingSoon = isPro
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
                                // Schedule billing cycle change at period end
                                const response = await apiClient.post<{
                                  success: boolean
                                  message: string
                                  change_effective_date: string
                                }>(
                                  '/api/v1/billing/subscriptions/schedule-billing-cycle-change',
                                  { billing_cycle: newCycle },
                                  true
                                )

                                if (response.success) {
                                  setMessage({
                                    type: 'success',
                                    text: response.message
                                  })
                                  await loadSubscriptionData()
                                }
                              } catch (error) {
                                console.error('Failed to schedule billing cycle change:', error)
                                setMessage({
                                  type: 'error',
                                  text: 'Failed to schedule billing cycle change. Please try again.'
                                })
                              } finally {
                                setProcessingSubscription(false)
                              }
                            }}
                            disabled={processingSubscription}
                          >
                            {processingSubscription ? 'Processing...' : 'Schedule Change'}
                          </Button>
                        </div>
                      </div>
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
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-sm font-medium text-neutral-700">Upgrade to unlock more features:</p>

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

                    {availableTiers
                      .filter(tier => tier.name.toLowerCase() !== 'free')
                      .map(tier => {
                        const isPro = tier.name.toLowerCase() === 'pro'
                        const isComingSoon = isPro

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
                                      {tier.currency_symbol}{(tier.price_yearly_cents / 100).toFixed(2)}
                                      <span className="text-sm font-normal text-neutral-600">/year</span>
                                    </p>
                                    <p className="text-xs text-neutral-500 mt-1">
                                      {tier.currency_symbol}{(tier.price_yearly_cents / 100 / 12).toFixed(2)}/month
                                    </p>
                                  </>
                                ) : (
                                  <p className="text-2xl font-bold text-neutral-900">
                                    {tier.currency_symbol}{(tier.price_monthly_cents / 100).toFixed(2)}
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
                  Once you delete your account, there is no going back. Your documents will remain in Google Drive, but all metadata and categorization will be permanently deleted after 30 days.
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
            message="Warning: This action cannot be undone. Your account will be deactivated immediately, and all data will be permanently deleted after 30 days."
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
    </div>
  )
}