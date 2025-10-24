// frontend/src/app/settings/drive/callback/page.tsx
'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { apiClient } from '@/services/api-client'

function DriveCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [message, setMessage] = useState<string>('Connecting to Google Drive...')

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const error = searchParams.get('error')

        if (error) {
          setStatus('error')
          setMessage(`Authentication failed: ${error}`)
          setTimeout(() => router.push('/settings'), 3000)
          return
        }

        if (!code || !state) {
          setStatus('error')
          setMessage('Missing authentication parameters')
          setTimeout(() => router.push('/settings'), 3000)
          return
        }

        // Complete OAuth flow by calling backend
        const result = await apiClient.post<{ success: boolean; message: string }>(
          '/api/v1/users/drive/callback',
          undefined,
          true,
          { params: { code, state } }
        )

        if (result.success) {
          setStatus('success')
          setMessage('Google Drive connected successfully!')
          setTimeout(() => router.push('/settings'), 2000)
        } else {
          setStatus('error')
          setMessage(result.message || 'Failed to connect Drive')
          setTimeout(() => router.push('/settings'), 3000)
        }
      } catch (error) {
        setStatus('error')
        const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred'
        setMessage(errorMessage)
        setTimeout(() => router.push('/settings'), 3000)
      }
    }

    handleCallback()
  }, [searchParams, router])

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50">
      <div className="max-w-md w-full p-8 bg-white rounded-lg shadow-lg text-center">
        {status === 'processing' && (
          <>
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-neutral-900 mb-2">
              Connecting Google Drive
            </h2>
            <p className="text-sm text-neutral-600">{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="h-12 w-12 mx-auto mb-4 text-green-600">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-neutral-900 mb-2">Success!</h2>
            <p className="text-sm text-neutral-600">{message}</p>
            <p className="text-xs text-neutral-500 mt-2">Redirecting to settings...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="h-12 w-12 mx-auto mb-4 text-red-600">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-neutral-900 mb-2">Connection Failed</h2>
            <p className="text-sm text-neutral-600">{message}</p>
            <p className="text-xs text-neutral-500 mt-2">Redirecting to settings...</p>
          </>
        )}
      </div>
    </div>
  )
}

export default function DriveCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto mb-4"></div>
          <p className="text-sm text-neutral-600">Loading...</p>
        </div>
      </div>
    }>
      <DriveCallbackContent />
    </Suspense>
  )
}
