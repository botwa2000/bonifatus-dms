// frontend/src/app/login/LoginPageContent.tsx
/**
 * Login Page - Conversion-Optimized Login Flow
 * Supports both Google OAuth and Email/Password authentication
 */
'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { GoogleLoginButton } from '@/components/GoogleLoginButton'
import { Button } from '@/components/ui/Button'
import { logger } from '@/lib/logger'

export default function LoginPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>(searchParams.get('error') || '')
  const [showEmailForm, setShowEmailForm] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  // Form state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false
  })

  // Map backend error codes to user-friendly messages
  const getErrorMessage = (errorCode: string): string => {
    const errorMessages: Record<string, string> = {
      'auth_failed': 'Google authentication failed. Please try again.',
      'server_error': 'Authentication service error. Please try again later.',
      'access_denied': 'You denied access. Please authorize the application to continue.'
    }

    return errorMessages[errorCode] || errorCode
  }

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/email/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          remember_me: formData.rememberMe
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        // Successful login - redirect to dashboard
        router.push('/dashboard')
      } else if (data.requires_verification) {
        // Email not verified - redirect to verification page
        // Store email securely in sessionStorage (not in URL)
        sessionStorage.setItem('verification_email', formData.email)
        router.push('/verify-email')
      } else {
        setError(data.message || 'Login failed. Please try again.')
      }
    } catch (error) {
      logger.error('Login error:', error)
      setError('An error occurred. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white dark:from-neutral-900 dark:to-neutral-900">
      {/* Header */}
      <nav className="bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center">
              <div className="relative h-10 w-40">
                <Image
                  src="/logo_text.png"
                  alt="Bonifatus DMS"
                  fill
                  className="object-contain object-left"
                  priority
                />
              </div>
            </Link>

            <div className="text-sm text-neutral-600 dark:text-neutral-400">
              Don&apos;t have an account?{' '}
              <Link href="/signup" className="text-admin-primary hover:text-admin-primary-dark font-medium">
                Sign up
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-md mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Headline */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-neutral-900 dark:text-white mb-2">
            Welcome back
          </h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            Sign in to continue to Bonifatus DMS
          </p>
        </div>

        {/* Auth Options */}
        <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-8">
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-3 bg-semantic-error-bg dark:bg-red-900/20 border border-semantic-error-border dark:border-red-800 rounded-lg text-sm text-admin-danger dark:text-red-400 dark:text-red-400">
              {getErrorMessage(error)}
            </div>
          )}

          {!showEmailForm ? (
            <div className="space-y-4">
              {/* Google Sign In (Primary) */}
              <GoogleLoginButton
                className="w-full"
                size="lg"
              >
                <div className="flex items-center justify-center gap-3">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Sign in with Google
                </div>
              </GoogleLoginButton>

              {/* OR Divider */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-neutral-300 dark:border-neutral-600"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 dark:text-neutral-400">
                    or
                  </span>
                </div>
              </div>

              {/* Email Sign In (Secondary) */}
              <Button
                onClick={() => setShowEmailForm(true)}
                variant="secondary"
                size="lg"
                className="w-full"
              >
                <div className="flex items-center justify-center gap-3">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  Sign in with Email
                </div>
              </Button>
            </div>
          ) : (
            /* Email Login Form */
            <form onSubmit={handleEmailLogin} className="space-y-4">
              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-2">
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-4 py-3 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:ring-2 focus:ring-admin-primary focus:border-transparent dark:bg-neutral-700 dark:text-white"
                  placeholder="you@example.com"
                />
              </div>

              {/* Password */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    required
                    autoComplete="current-password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-4 py-3 pr-12 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:ring-2 focus:ring-admin-primary focus:border-transparent dark:bg-neutral-700 dark:text-white"
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
                  >
                    {showPassword ? (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Remember Me & Forgot Password */}
              <div className="flex items-center justify-between">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.rememberMe}
                    onChange={(e) => setFormData({ ...formData, rememberMe: e.target.checked })}
                    className="h-4 w-4 text-admin-primary border-neutral-300 rounded focus:ring-admin-primary"
                  />
                  <span className="ml-2 text-sm text-neutral-600 dark:text-neutral-400">
                    Remember me
                  </span>
                </label>

                <Link href="/forgot-password" className="text-sm text-admin-primary hover:underline">
                  Forgot password?
                </Link>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                size="lg"
                className="w-full"
                disabled={loading}
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>

              {/* Back to options */}
              <button
                type="button"
                onClick={() => setShowEmailForm(false)}
                className="w-full text-sm text-neutral-600 dark:text-neutral-400 hover:text-admin-primary"
              >
                ← Back to sign in options
              </button>
            </form>
          )}

          {/* Trust Signals */}
          <div className="mt-6 pt-6 border-t border-neutral-200 dark:border-neutral-700">
            <div className="flex flex-wrap justify-center gap-4 text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-400">
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4 text-admin-success dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                GDPR Compliant
              </div>
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4 text-admin-success dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                </svg>
                256-bit Encryption
              </div>
            </div>
          </div>
        </div>

        {/* Additional Links */}
        <div className="mt-8 text-center">
          <Link href="/" className="text-sm text-neutral-600 dark:text-neutral-400 hover:text-admin-primary">
            ← Back to Homepage
          </Link>
        </div>
      </div>
    </div>
  )
}
