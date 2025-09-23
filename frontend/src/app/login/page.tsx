// src/app/login/page.tsx
/**
 * Login page with Google OAuth callback handling
 * Will implement complete OAuth flow in Phase 3.2
 */

'use client'

import { useEffect } from 'react'
import { useAuth } from '@/hooks/use-auth'

export default function LoginPage() {
  const { handleGoogleCallback, isLoading } = useAuth()

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const code = urlParams.get('code')
    const error = urlParams.get('error')

    // Handle OAuth callback if parameters are present
    if (code || error) {
      handleGoogleCallback().catch(callbackError => {
        console.error('OAuth callback failed:', callbackError)
      })
    }
  }, [handleGoogleCallback])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent"></div>
          <p className="mt-2 text-sm text-neutral-600">Processing authentication...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50">
      <div className="w-full max-w-md space-y-8 p-8">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 rounded-lg bg-admin-primary flex items-center justify-center">
            <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="mt-4 text-2xl font-bold text-neutral-900">
            Admin Login
          </h1>
          <p className="mt-2 text-sm text-neutral-600">
            Google OAuth integration coming in Step 2
          </p>
        </div>
        
        <div className="rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="space-y-4">
            <div className="relative">
              <div className="h-10 w-full rounded-md bg-neutral-100 flex items-center justify-center">
                <svg className="h-5 w-5 text-neutral-400" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              </div>
              <div className="absolute inset-0 rounded-md bg-white bg-opacity-90 flex items-center justify-center">
                <span className="text-xs font-medium text-neutral-500">Coming Soon</span>
              </div>
            </div>
            
            <div className="text-center">
              <p className="text-xs text-neutral-500">
                Google OAuth login will be implemented in the next step
              </p>
              <p className="mt-1 text-xs text-neutral-400">
                Authentication hook and service ready for integration
              </p>
            </div>
          </div>
        </div>

        <div className="text-center">
          <p className="text-xs text-neutral-400">
            Bonifatus DMS - Professional Document Management
          </p>
        </div>
      </div>
    </div>
  )
}