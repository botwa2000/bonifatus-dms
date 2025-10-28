// frontend/src/app/login/LoginPageContent.tsx
'use client'

import { useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { GoogleLoginButton } from '@/components/GoogleLoginButton'

export default function LoginPageContent() {
  const searchParams = useSearchParams()
  const [error] = useState<string | null>(searchParams.get('error'))

  // Map backend error codes to user-friendly messages
  const getErrorMessage = (errorCode: string | null): string | null => {
    if (!errorCode) return null

    const errorMessages: Record<string, string> = {
      'auth_failed': 'Google authentication failed. Please try again.',
      'server_error': 'Authentication service error. Please try again later.',
      'access_denied': 'You denied access. Please authorize the application to continue.'
    }

    return errorMessages[errorCode] || 'Authentication failed. Please try again.'
  }

  const errorMessage = getErrorMessage(error)

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

          {errorMessage && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{errorMessage}</p>
            </div>
          )}
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
