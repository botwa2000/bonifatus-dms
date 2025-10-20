// frontend/src/app/login/LoginPageContent.tsx
'use client'

import { useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { authService } from '@/services/auth.service'

// Global singleton to prevent duplicate OAuth processing across component re-renders
let globalOAuthProcessing = false

export default function LoginPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(true) // Start as true to show loading

  useEffect(() => {
    const handleOAuthCallback = async () => {
      // Global singleton pattern - prevents duplicate processing in React StrictMode
      if (globalOAuthProcessing) {
        console.log('[OAuth] Already processing, skipping duplicate')
        return
      }
      globalOAuthProcessing = true

      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const errorParam = searchParams.get('error')

        // No OAuth code - redirect to homepage
        if (!code) {
          console.log('[OAuth] No code present, redirecting to homepage')
          router.push('/')
          return
        }

        // OAuth error from Google
        if (errorParam) {
          console.error('[OAuth] Error from Google:', errorParam)
          setError(`Authentication error: ${errorParam}`)
          setIsProcessing(false)
          return
        }

        console.log('[OAuth] Processing authorization code...')

        // Exchange authorization code for JWT tokens
        // Backend returns user data, avoiding a second API call
        const result = await authService.exchangeGoogleToken(code, state)

        console.log('[OAuth] Exchange result:', { success: result.success, hasUser: !!result.user, error: result.error })

        if (result.success && result.user) {
          // Use Next.js router for instant client-side navigation
          // User data is already cached in localStorage
          const redirectUrl = searchParams.get('redirect') || '/dashboard'
          console.log('[OAuth] Success! Redirecting to:', redirectUrl)
          router.push(redirectUrl)
        } else {
          console.error('[OAuth] Exchange failed:', result.error)
          setError(result.error || 'Authentication failed. Please try again.')
          setIsProcessing(false)
        }
      } catch (err) {
        console.error('[OAuth] Callback error:', err)
        setError(err instanceof Error ? err.message : 'Authentication failed')
        setIsProcessing(false)
      }
    }

    handleOAuthCallback()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Run only once on mount - searchParams doesn't change

  // Show error page
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-50">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <div className="h-12 w-12 text-admin-danger mx-auto">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="mt-6 text-3xl font-extrabold text-neutral-900">
              Authentication Failed
            </h2>
            <p className="mt-2 text-sm text-neutral-600">
              {error}
            </p>
            <div className="mt-6">
              <Link
                href="/"
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-admin-primary hover:bg-admin-secondary"
              >
                Return to Homepage
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Show loading indicator during OAuth processing
  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-admin-primary mx-auto"></div>
          <h2 className="mt-6 text-2xl font-bold text-neutral-900">
            Completing sign in...
          </h2>
          <p className="mt-2 text-sm text-neutral-600">
            Please wait while we verify your account
          </p>
        </div>
      </div>
    </div>
  )
}
