// frontend/src/app/login/LoginPageContent.tsx
'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { authService } from '@/services/auth.service'

export default function LoginPageContent() {
  const searchParams = useSearchParams()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const errorParam = searchParams.get('error')

        // No OAuth code - redirect to homepage
        if (!code) {
          window.location.href = '/'
          return
        }

        // OAuth error from Google
        if (errorParam) {
          setError(`Authentication error: ${errorParam}`)
          return
        }

        // Exchange authorization code for JWT tokens and redirect immediately
        const result = await authService.exchangeGoogleToken(code, state)

        if (result.success) {
          // Immediate redirect to dashboard - no interim success page
          const redirectUrl = searchParams.get('redirect') || '/dashboard'
          window.location.href = redirectUrl
        } else {
          setError('Authentication failed. Please try again.')
        }
      } catch (err) {
        console.error('[OAuth] Callback error:', err)
        setError(err instanceof Error ? err.message : 'Authentication failed')
      }
    }

    handleOAuthCallback()
  }, [searchParams])

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

  // Show minimal spinner while processing - no interim success page
  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-admin-primary mx-auto"></div>
          <h2 className="mt-6 text-3xl font-extrabold text-neutral-900">
            Signing you in...
          </h2>
        </div>
      </div>
    </div>
  )
}
