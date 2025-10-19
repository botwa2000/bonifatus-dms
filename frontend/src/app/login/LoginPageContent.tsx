// frontend/src/app/login/LoginPageContent.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { authService } from '@/services/auth.service'

export default function LoginPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'login'>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        // Ensure searchParams is available
        if (!searchParams) {
          console.error('[LOGIN DEBUG] searchParams not available')
          setStatus('login')
          return
        }

        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const error = searchParams.get('error')

        console.log('[LOGIN DEBUG] OAuth callback started', { code: !!code, state: !!state, error })

        if (error) {
          setStatus('error')
          setError(`OAuth error: ${error}`)
          return
        }

        if (!code) {
          setStatus('login')
          return
        }

        // Exchange authorization code for JWT tokens and redirect immediately
        const result = await authService.exchangeGoogleToken(code, state)

        if (result.success) {
          const redirectUrl = searchParams.get('redirect') || '/dashboard'
          console.log('[LOGIN DEBUG] Redirecting to:', redirectUrl)
          window.location.href = redirectUrl
          return
        } else {
          console.error('[LOGIN DEBUG] Token exchange failed:', result.error)
          setStatus('error')
          setError('Authentication failed. Please try again.')
        }
      } catch (error) {
        console.error('[LOGIN DEBUG] OAuth callback error:', error)
        setStatus('error')
        setError(error instanceof Error ? error.message : 'Authentication failed')
      }
    }

    handleOAuthCallback()
  }, [searchParams, router])

  const handleGoogleLogin = async () => {
    try {
      setStatus('loading')
      await authService.initializeGoogleOAuth()
    } catch (error) {
      console.error('Login initialization failed:', error)
      setStatus('error')
      setError('Failed to initialize login. Please try again.')
    }
  }

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Processing Authentication
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Please wait while we complete your sign-in...
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <div className="h-12 w-12 text-green-600 mx-auto">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Sign In Successful
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Redirecting to dashboard...
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <div className="h-12 w-12 text-red-600 mx-auto">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Authentication Failed
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              {error}
            </p>
            <div className="mt-6">
              <button
                onClick={handleGoogleLogin}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // status === 'login' - show login page
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Sign in to Bonifatus DMS
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Professional document management system
          </p>
        </div>
        <div className="mt-8 space-y-6">
          <button
            onClick={handleGoogleLogin}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>
        </div>
      </div>
    </div>
  )
}