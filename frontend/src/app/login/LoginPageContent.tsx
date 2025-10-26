// frontend/src/app/login/LoginPageContent.tsx
'use client'

import { useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { authService } from '@/services/auth.service'
import { GoogleLoginButton } from '@/components/GoogleLoginButton'

// Module-level flag to prevent duplicate OAuth processing across remounts
let isProcessingOAuth = false

export default function LoginPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  // Check if user is already authenticated
  // If so, redirect immediately to dashboard
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const cachedUser = sessionStorage.getItem('user')
      if (cachedUser && !searchParams.get('code')) {
        console.log('[Login] User already authenticated, redirecting to dashboard')
        router.replace('/dashboard')
      }
    }
  }, [router, searchParams])

  // Handle OAuth callback
  useEffect(() => {
    const handleOAuthCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const errorParam = searchParams.get('error')

      // No OAuth code? User needs to sign in normally
      if (!code && !errorParam) {
        return
      }

      // Block duplicate executions with module-level flag
      if (isProcessingOAuth) {
        console.log('[OAuth] Already processing, skipping duplicate execution')
        return
      }

      isProcessingOAuth = true
      setIsProcessing(true)

      console.log('[OAuth] Processing callback...')

      try {
        // Handle OAuth error from Google
        if (errorParam) {
          console.error('[OAuth] Error from Google:', errorParam)
          setError(`Authentication error: ${errorParam}`)
          setIsProcessing(false)
          isProcessingOAuth = false
          return
        }

        // Exchange authorization code for tokens
        const result = await authService.exchangeGoogleToken(code!, state)

        if (result.success && result.user) {
          // Success - user is cached in sessionStorage by authService
          const redirectUrl = searchParams.get('redirect') || '/dashboard'
          console.log('[OAuth] Success! Navigating to:', redirectUrl)

          // Stop spinner and navigate - auth context will load user from sessionStorage
          setIsProcessing(false)
          router.replace(redirectUrl)
        } else {
          console.error('[OAuth] Failed:', result.error)
          setError(result.error || 'Authentication failed. Please try again.')
          setIsProcessing(false)
          isProcessingOAuth = false
        }
      } catch (err) {
        console.error('[OAuth] Exception:', err)
        setError(err instanceof Error ? err.message : 'Authentication failed')
        setIsProcessing(false)
        isProcessingOAuth = false
      }
    }

    handleOAuthCallback()
  }, [searchParams, router])

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

  // Show processing spinner during OAuth callback
  if (isProcessing) {
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

  // Show normal login page
  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-neutral-900">
            Sign in to Bonifatus DMS
          </h2>
          <p className="mt-2 text-sm text-neutral-600">
            Document Management System
          </p>
        </div>
        <div className="mt-8">
          <GoogleLoginButton size="lg" className="w-full" />
        </div>
        <div className="text-center mt-4">
          <Link
            href="/"
            className="text-sm text-admin-primary hover:underline"
          >
            Back to Homepage
          </Link>
        </div>
      </div>
    </div>
  )
}
