// frontend/src/app/profile/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/auth-context'
import { apiClient } from '@/services/api-client'
import { Card, CardHeader, CardContent, Button, Input, Select, Modal, ModalHeader, ModalContent, ModalFooter, Alert, Badge } from '@/components/ui'
import AppHeader from '@/components/AppHeader'

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

  // Load user data on mount
  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  useEffect(() => {
    if (isAuthenticated) {
      loadProfileData()
    }
  }, [isAuthenticated])

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
      
      setTimeout(() => {
        logout().then(() => {
          router.push('/')
        })
      }, 2000)
    } catch (error) {
      console.error('Failed to delete account:', error)
      setMessage({ type: 'error', text: 'Failed to deactivate account' })
      setDeleting(false)
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
            <CardHeader title="Subscription" />
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-neutral-600">Current Plan:</span>
                  <span className="font-medium text-neutral-900">
                    {isTrialActive ? 'Premium Trial' : profile.tier || 'Free'}
                  </span>
                </div>
                {isTrialActive && profile.trial_end_date && (
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Trial Ends:</span>
                    <span className="font-medium text-neutral-900">{formatDate(profile.trial_end_date)}</span>
                  </div>
                )}
                <div className="pt-3">
                  <Link href="/pricing" className="text-sm text-admin-primary hover:underline">
                    View pricing plans →
                  </Link>
                </div>
              </div>
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
    </div>
  )
}