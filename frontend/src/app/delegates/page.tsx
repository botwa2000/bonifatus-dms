// frontend/src/app/delegates/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import {
  delegateService,
  type Delegate,
  type DelegateInviteRequest
} from '@/services/delegate.service'
import { Button, Modal, ModalHeader, ModalContent, ModalFooter, Alert, Badge, SpinnerFullPage } from '@/components/ui'
import AppHeader from '@/components/AppHeader'
import type { BadgeVariant } from '@/components/ui'

export default function DelegatesPage() {
  const { user, isAuthenticated, isLoading: authLoading, hasAttemptedAuth, loadUser } = useAuth()
  const router = useRouter()

  const [delegates, setDelegates] = useState<Delegate[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<'viewer' | 'editor' | 'owner'>('viewer')
  const [isInviting, setIsInviting] = useState(false)

  const [revokingDelegate, setRevokingDelegate] = useState<Delegate | null>(null)
  const [isRevoking, setIsRevoking] = useState(false)

  // Load user on mount
  useEffect(() => {
    loadUser()
  }, [loadUser])

  // Auth check
  useEffect(() => {
    if (!hasAttemptedAuth) {
      return
    }

    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, authLoading, hasAttemptedAuth, router])

  // Load delegates when authenticated
  useEffect(() => {
    if (isAuthenticated && user) {
      loadDelegates()
    }
  }, [isAuthenticated, user])

  const loadDelegates = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await delegateService.listMyDelegates()
      setDelegates(response.delegates)
    } catch (err) {
      setError('Failed to load delegates. Please try again.')
      console.error('Load delegates error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleInviteDelegate = async (allowUnregistered = false) => {
    if (!inviteEmail.trim()) {
      setError('Please enter an email address')
      return
    }

    try {
      setIsInviting(true)
      setError(null)

      const request: DelegateInviteRequest = {
        email: inviteEmail.trim(),
        role: inviteRole,
        allow_unregistered: allowUnregistered
      }

      await delegateService.inviteDelegate(request)

      setSuccess('Invitation sent successfully!')
      setShowInviteModal(false)
      setInviteEmail('')
      setInviteRole('viewer')

      // Reload delegates
      await loadDelegates()

      // Clear success message after 5 seconds
      setTimeout(() => setSuccess(null), 5000)
    } catch (err: unknown) {
      const error = err as {
        response?: {
          status?: number
          data?: { detail?: { code?: string; message?: string } | string }
        }
        message?: string
      }

      // Check if this is a USER_NOT_REGISTERED error (409 Conflict)
      if (error?.response?.status === 409) {
        const detail = error.response.data?.detail
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
          }
        }
      }

      // Handle other errors
      const errorMessage = typeof error?.response?.data?.detail === 'string'
        ? error.response.data.detail
        : error?.message || 'Failed to send invitation'
      setError(errorMessage)
    } finally {
      setIsInviting(false)
    }
  }

  const handleRevokeAccess = async () => {
    if (!revokingDelegate) return

    try {
      setIsRevoking(true)
      setError(null)

      await delegateService.revokeAccess(revokingDelegate.id)

      setSuccess('Access revoked successfully')
      setRevokingDelegate(null)

      // Reload delegates
      await loadDelegates()

      // Clear success message after 5 seconds
      setTimeout(() => setSuccess(null), 5000)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to revoke access'
      setError(errorMessage)
      setRevokingDelegate(null)
    } finally {
      setIsRevoking(false)
    }
  }

  const getStatusBadgeVariant = (status: string): BadgeVariant => {
    switch (status) {
      case 'active':
        return 'success'
      case 'pending':
        return 'warning'
      case 'revoked':
        return 'error'
      default:
        return 'default'
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  if (!isAuthenticated || authLoading) {
    return <SpinnerFullPage />
  }

  // Check if user is Pro tier (tier_id = 2)
  const isProUser = user?.tier_id === 2 || user?.is_admin

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <AppHeader />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Delegate Access
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Share your document library with trusted delegates
              </p>
            </div>

            {isProUser && (
              <Button
                variant="primary"
                onClick={() => setShowInviteModal(true)}
              >
                Invite Delegate
              </Button>
            )}
          </div>

          {!isProUser && (
            <Alert type="info" message="Upgrade to Professional tier to invite delegates and share your document library." />
          )}
        </div>

        {error && (
          <Alert type="error" message={error} />
        )}

        {success && (
          <Alert type="success" message={success} />
        )}

        {/* Delegates List */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              My Delegates ({delegates.length})
            </h2>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : delegates.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 dark:text-gray-400">
                No delegates yet. Invite someone to share your documents.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Role
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Invited
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Last Access
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {delegates.map((delegate) => (
                    <tr key={delegate.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {delegate.delegate_email}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
                          {delegate.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge variant={getStatusBadgeVariant(delegate.status)}>
                          {delegate.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {formatDate(delegate.invitation_sent_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {formatDate(delegate.last_accessed_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {delegate.status !== 'revoked' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setRevokingDelegate(delegate)}
                          >
                            Revoke
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Invite Modal */}
      {showInviteModal && (
        <Modal isOpen={showInviteModal} onClose={() => !isInviting && setShowInviteModal(false)}>
          <ModalHeader title="Invite Delegate" onClose={() => !isInviting && setShowInviteModal(false)} />
          <ModalContent>
            <div className="space-y-4">
              <div>
                <label htmlFor="inviteEmail" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  id="inviteEmail"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="delegate@example.com"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                  disabled={isInviting}
                />
              </div>

              <div>
                <label htmlFor="inviteRole" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Access Role
                </label>
                <select
                  id="inviteRole"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as 'viewer' | 'editor' | 'owner')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                  disabled={isInviting}
                >
                  <option value="viewer">Viewer (Read-only)</option>
                  <option value="editor" disabled>Editor (Not yet available)</option>
                  <option value="owner" disabled>Owner (Not yet available)</option>
                </select>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Viewers can search, view, and download documents but cannot upload, edit, or delete.
                </p>
              </div>
            </div>
          </ModalContent>
          <ModalFooter>
            <Button
              variant="ghost"
              onClick={() => setShowInviteModal(false)}
              disabled={isInviting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleInviteDelegate}
              disabled={isInviting || !inviteEmail.trim()}
            >
              {isInviting ? 'Sending...' : 'Send Invitation'}
            </Button>
          </ModalFooter>
        </Modal>
      )}

      {/* Revoke Confirmation Modal */}
      {revokingDelegate && (
        <Modal isOpen={!!revokingDelegate} onClose={() => !isRevoking && setRevokingDelegate(null)}>
          <ModalHeader title="Revoke Delegate Access" onClose={() => !isRevoking && setRevokingDelegate(null)} />
          <ModalContent>
            <p className="text-gray-700 dark:text-gray-300">
              Are you sure you want to revoke access for{' '}
              <strong>{revokingDelegate.delegate_email}</strong>?
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              They will immediately lose access to your documents. You can invite them again later if needed.
            </p>
          </ModalContent>
          <ModalFooter>
            <Button
              variant="ghost"
              onClick={() => setRevokingDelegate(null)}
              disabled={isRevoking}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleRevokeAccess}
              disabled={isRevoking}
            >
              {isRevoking ? 'Revoking...' : 'Revoke Access'}
            </Button>
          </ModalFooter>
        </Modal>
      )}
    </div>
  )
}
