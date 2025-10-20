// frontend/src/app/login/LoginPageContent.tsx
'use client'

import { useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { authService } from '@/services/auth.service'

export default function LoginPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  useEffect(() => {
    const handleOAuthCallback = async () => {
      // Prevent duplicate calls from React StrictMode double-render
      if (isProcessing) return
      setIsProcessing(true)

      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const errorParam = searchParams.get('error')

        // No OAuth code - redirect to homepage
        if (!code) {
          router.push('/')
          return
        }

        // OAuth error from Google
        if (errorParam) {
          setError(`Authentication error: ${errorParam}`)
          return
        }

        // Exchange authorization code for JWT tokens
        // Backend returns user data, avoiding a second API call
        const result = await authService.exchangeGoogleToken(code, state)

        if (result.success && result.user) {
          // Use Next.js router for instant client-side navigation
          // User data is already cached in localStorage
          const redirectUrl = searchParams.get('redirect') || '/dashboard'
          router.push(redirectUrl)
        } else {
          setError('Authentication failed. Please try again.')
        }
      } catch (err) {
        console.error('[OAuth] Callback error:', err)
        setError(err instanceof Error ? err.message : 'Authentication failed')
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

  // Show blank screen during redirect - no loading UI needed
  // The faster we process, the less the user sees this page
  return null
}
