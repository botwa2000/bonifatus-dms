// src/app/login/page.tsx
/**
 * Login page with Google OAuth integration
 * Handles authentication and redirects to dashboard after login
 */

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/use-auth'
import { GoogleLoginButton } from '@/components/GoogleLoginButton'

export default function LoginPage() {
  const { handleGoogleCallback, isLoading, isAuthenticated, user } = useAuth()
  const router = useRouter()

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const code = urlParams.get('code')
    const error = urlParams.get('error')

    // Handle OAuth callback if parameters are present
    if (code || error) {
      handleGoogleCallback().then(() => {
        // Redirect will be handled by the authentication state change
      }).catch(callbackError => {
        console.error('OAuth callback failed:', callbackError)
      })
    }
  }, [handleGoogleCallback])

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (isAuthenticated && user) {
      router.push('/dashboard')
    }
  }, [isAuthenticated, user, router])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Processing authentication...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50">
      <div className="w-full max-w-md space-y-8 p-8">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 rounded-lg bg-admin-primary flex items-center justify-center">
            <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h1 className="mt-6 text-3xl font-bold text-neutral-900">
            Welcome to Bonifatus DMS
          </h1>
          <p className="mt-2 text-sm text-neutral-600">
            Professional Document Management System
          </p>
        </div>
        
        <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-lg font-semibold text-neutral-900">
                Sign in to your account
              </h2>
              <p className="mt-1 text-sm text-neutral-500">
                Get started with secure document management
              </p>
            </div>

            <GoogleLoginButton 
              size="lg" 
              className="w-full"
            >
              Sign in with Google
            </GoogleLoginButton>

            <div className="rounded-lg bg-green-50 p-4 border border-green-200">
              <div className="flex items-start">
                <svg className="h-5 w-5 text-green-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-green-800">
                    New Users Welcome!
                  </h3>
                  <p className="text-sm text-green-700 mt-1">
                    First-time login includes 30 days of premium features absolutely free.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="text-center space-y-2">
          <p className="text-xs text-neutral-400">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
          <div className="flex justify-center space-x-4 text-xs">
            <a href="/legal/terms" className="text-admin-primary hover:underline">Terms</a>
            <a href="/legal/privacy" className="text-admin-primary hover:underline">Privacy</a>
            <a href="/about" className="text-admin-primary hover:underline">About</a>
            <a href="/contact" className="text-admin-primary hover:underline">Contact</a>
          </div>
        </div>
      </div>
    </div>
  )
}