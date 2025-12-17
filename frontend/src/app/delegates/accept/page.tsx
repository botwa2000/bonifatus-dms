// frontend/src/app/delegates/accept/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import { delegateService } from '@/services/delegate.service'
import { Button, Alert, SpinnerFullPage } from '@/components/ui'
import AppHeader from '@/components/AppHeader'

export default function AcceptInvitationPage() {
  const { user, isAuthenticated, isLoading: authLoading, hasAttemptedAuth, loadUser } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [isAccepting, setIsAccepting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [invitationDetails, setInvitationDetails] = useState<{
    owner_name: string
    owner_email: string
    role: string
  } | null>(null)
  const [accepted, setAccepted] = useState(false)

  // Load user on mount
  useEffect(() => {
    loadUser()
  }, [loadUser])

  // Check if token is present
  useEffect(() => {
    if (!token) {
      setError('Invalid invitation link. No token provided.')
    }
  }, [token])

  // Redirect to login if not authenticated, preserving token
  useEffect(() => {
    if (!hasAttemptedAuth) {
      return
    }

    if (!authLoading && !isAuthenticated && token) {
      // Redirect to login with return URL
      router.push(`/login?redirect=/delegates/accept?token=${token}`)
    }
  }, [isAuthenticated, authLoading, hasAttemptedAuth, token, router])

  const handleAcceptInvitation = async () => {
    if (!token) return

    try {
      setIsAccepting(true)
      setError(null)

      const response = await delegateService.acceptInvitation(token)

      setInvitationDetails({
        owner_name: response.owner_name,
        owner_email: response.owner_email,
        role: response.role
      })
      setAccepted(true)
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to accept invitation'
      setError(errorMessage)
    } finally {
      setIsAccepting(false)
    }
  }

  if (!hasAttemptedAuth || authLoading) {
    return <SpinnerFullPage />
  }

  if (!isAuthenticated) {
    return <SpinnerFullPage />
  }

  if (!token) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <AppHeader />
        <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Invalid Invitation
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              This invitation link is invalid or incomplete.
            </p>
            <Button variant="primary" onClick={() => router.push('/dashboard')}>
              Go to Dashboard
            </Button>
          </div>
        </main>
      </div>
    )
  }

  if (accepted && invitationDetails) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <AppHeader />
        <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center">
            <div className="mb-6">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 dark:bg-green-900">
                <svg
                  className="h-6 w-6 text-green-600 dark:text-green-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            </div>

            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Invitation Accepted!
            </h1>

            <p className="text-gray-600 dark:text-gray-400 mb-2">
              You now have <strong className="text-gray-900 dark:text-white">{invitationDetails.role}</strong> access to{' '}
              <strong className="text-gray-900 dark:text-white">{invitationDetails.owner_name}'s</strong> documents.
            </p>

            <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">
              ({invitationDetails.owner_email})
            </p>

            <div className="space-x-4">
              <Button variant="primary" onClick={() => router.push('/documents')}>
                View Documents
              </Button>
              <Button variant="ghost" onClick={() => router.push('/dashboard')}>
                Go to Dashboard
              </Button>
            </div>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <AppHeader />
      <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 text-center">
            Accept Delegate Invitation
          </h1>

          {error && (
            <Alert variant="destructive" className="mb-6" onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <div className="mb-8">
            <p className="text-gray-600 dark:text-gray-400 text-center">
              You've been invited to access another user's document library as a delegate.
            </p>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6 mb-8">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              As a delegate, you will be able to:
            </h2>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <li className="flex items-start">
                <svg className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                View and search the owner's documents
              </li>
              <li className="flex items-start">
                <svg className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Download documents for review
              </li>
              <li className="flex items-start">
                <svg className="h-5 w-5 text-red-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span>Cannot upload, edit, or delete documents</span>
              </li>
            </ul>
          </div>

          <div className="flex justify-center space-x-4">
            <Button
              variant="ghost"
              onClick={() => router.push('/dashboard')}
              disabled={isAccepting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleAcceptInvitation}
              disabled={isAccepting}
            >
              {isAccepting ? 'Accepting...' : 'Accept Invitation'}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}
