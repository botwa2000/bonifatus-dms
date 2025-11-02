// frontend/src/app/settings/drive/callback/page.tsx
'use client'

import { useEffect, useState, useRef, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { apiClient } from '@/services/api-client'

function DriveCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [message, setMessage] = useState<string>('Connecting to Google Drive...')
  const processingRef = useRef(false)

  useEffect(() => {
    const handleCallback = async () => {
      console.log('[DRIVE CALLBACK DEBUG] === Drive OAuth Callback Started ===')
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const error = searchParams.get('error')

      console.log('[DRIVE CALLBACK DEBUG] OAuth params:', {
        hasCode: !!code,
        hasState: !!state,
        error
      })

      if (error) {
        console.error('[DRIVE CALLBACK DEBUG] OAuth error from Google:', error)
        setStatus('error')
        setMessage(`Authentication failed: ${error}`)
        setTimeout(() => router.push('/settings'), 3000)
        return
      }

      if (!code || !state) {
        console.error('[DRIVE CALLBACK DEBUG] Missing OAuth parameters')
        setStatus('error')
        setMessage('Missing authentication parameters')
        setTimeout(() => router.push('/settings'), 3000)
        return
      }

      // Create unique key for this Drive OAuth attempt
      const attemptKey = `drive_oauth_processing_${state}`

      // Check if already processed (prevents duplicate processing)
      if (processingRef.current || sessionStorage.getItem(attemptKey)) {
        console.log('[DRIVE CALLBACK DEBUG] Already processing or processed, skipping')
        return
      }

      // Mark as processing immediately
      processingRef.current = true
      sessionStorage.setItem(attemptKey, 'true')

      console.log('[DRIVE CALLBACK DEBUG] Calling backend /api/v1/users/drive/callback')
      try {
        // Complete OAuth flow by calling backend
        const result = await apiClient.post<{ success: boolean; message: string }>(
          '/api/v1/users/drive/callback',
          undefined,
          true,
          { params: { code, state } }
        )

        console.log('[DRIVE CALLBACK DEBUG] Backend response:', result)

        if (result.success) {
          console.log('[DRIVE CALLBACK DEBUG] ✅ Drive connected successfully')
          setStatus('success')
          setMessage('Google Drive connected successfully!')
          // Use router.push for client-side navigation
          setTimeout(() => {
            router.push('/settings')
          }, 2000)
          // Don't remove attemptKey - component will unmount during redirect
        } else {
          console.error('[DRIVE CALLBACK DEBUG] ❌ Backend returned failure:', result.message)
          setStatus('error')
          setMessage(result.message || 'Failed to connect Drive')
          sessionStorage.removeItem(attemptKey)
          setTimeout(() => router.push('/settings'), 3000)
        }
      } catch (error) {
        console.error('[DRIVE CALLBACK DEBUG] ❌ API call failed:', error)
        console.error('[DRIVE CALLBACK DEBUG] Error details:', {
          message: error instanceof Error ? error.message : 'Unknown',
          type: error?.constructor?.name,
          error
        })
        setStatus('error')
        const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred'
        setMessage(errorMessage)
        sessionStorage.removeItem(attemptKey)
        setTimeout(() => router.push('/settings'), 3000)
      }
    }

    handleCallback()
  }, [searchParams, router, processingRef])

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
