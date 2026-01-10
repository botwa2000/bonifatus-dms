// src/app/reset-password/page.tsx
/**
 * Reset Password Page
 * User creates new password using token from email
 */

'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { Button } from '@/components/ui/Button'
import { logger } from '@/lib/logger'

function ResetPasswordContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token') || ''

  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [passwordStrength, setPasswordStrength] = useState({
    valid: false,
    errors: [] as string[]
  })

  // Check if token is present
  useEffect(() => {
    if (!token) {
      setError('Invalid or missing reset token. Please request a new password reset link.')
    }
  }, [token])

  // Check password strength in real-time
  useEffect(() => {
    if (formData.password.length > 0) {
      checkPasswordStrength(formData.password)
    } else {
      setPasswordStrength({ valid: false, errors: [] })
    }
  }, [formData.password])

  const checkPasswordStrength = async (password: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/email/check-password-strength`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      })

      if (response.ok) {
        const data = await response.json()
        setPasswordStrength(data)
      }
    } catch (error) {
      logger.error('Password strength check failed:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Validate password strength
    if (!passwordStrength.valid) {
      setError('Please choose a stronger password')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/email/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: token,
          new_password: formData.password
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setSuccess(true)
        // Redirect to login after 3 seconds
        setTimeout(() => {
          router.push('/login?message=password_reset_success')
        }, 3000)
      } else {
        setError(data.message || 'Failed to reset password. The link may have expired.')
      }
    } catch (error) {
      logger.error('Reset password error:', error)
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
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-md mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-8">
          {!success ? (
            <>
              {/* Icon */}
              <div className="flex justify-center mb-6">
                <div className="w-16 h-16 bg-semantic-info-bg-strong dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-admin-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
              </div>

              {/* Headline */}
              <div className="text-center mb-8">
                <h1 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
                  Create new password
                </h1>
                <p className="text-neutral-600 dark:text-neutral-400">
                  Choose a strong password for your account
                </p>
              </div>

              {/* Error Message */}
              {error && (
                <div className="mb-6 p-3 bg-semantic-error-bg dark:bg-red-900/20 border border-semantic-error-border dark:border-red-800 rounded-lg text-sm text-admin-danger dark:text-red-400 dark:text-red-400">
                  {error}
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* New Password */}
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      required
                      autoComplete="new-password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className="w-full px-4 py-3 pr-12 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:ring-2 focus:ring-admin-primary focus:border-transparent dark:bg-neutral-700 dark:text-white"
                      placeholder="Min 12 characters"
                      disabled={!token}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
                      disabled={!token}
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
                  {/* Password Strength Indicator */}
                  {formData.password.length > 0 && (
                    <div className="mt-2">
                      {passwordStrength.valid ? (
                        <p className="text-xs text-admin-success dark:text-green-400 dark:text-green-400 flex items-center gap-1">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          Strong password
                        </p>
                      ) : (
                        <div className="space-y-1">
                          {passwordStrength.errors.map((err, idx) => (
                            <p key={idx} className="text-xs text-admin-danger dark:text-red-400 dark:text-red-400">
                              • {err}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Confirm Password */}
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <input
                      id="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      autoComplete="new-password"
                      value={formData.confirmPassword}
                      onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                      className="w-full px-4 py-3 pr-12 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:ring-2 focus:ring-admin-primary focus:border-transparent dark:bg-neutral-700 dark:text-white"
                      placeholder="Re-enter your password"
                      disabled={!token}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
                      disabled={!token}
                    >
                      {showConfirmPassword ? (
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

                <Button
                  type="submit"
                  size="lg"
                  className="w-full"
                  disabled={loading || !passwordStrength.valid || !token}
                >
                  {loading ? 'Resetting password...' : 'Reset Password'}
                </Button>
              </form>

              {/* Back to login */}
              <div className="mt-6 text-center">
                <Link href="/login" className="text-sm text-neutral-600 dark:text-neutral-400 hover:text-admin-primary">
                  ← Back to sign in
                </Link>
              </div>
            </>
          ) : (
            /* Success State */
            <>
              {/* Icon */}
              <div className="flex justify-center mb-6">
                <div className="w-16 h-16 bg-semantic-success-bg-strong dark:bg-green-900/30 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-admin-success dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>

              {/* Success Message */}
              <div className="text-center mb-8">
                <h1 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
                  Password reset successful!
                </h1>
                <p className="text-neutral-600 dark:text-neutral-400">
                  Your password has been changed. You can now sign in with your new password.
                </p>
              </div>

              {/* Redirect Notice */}
              <div className="mb-6 p-4 bg-semantic-info-bg dark:bg-blue-900/20 border border-semantic-info-border dark:border-blue-800 rounded-lg text-center">
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  Redirecting to sign in page in 3 seconds...
                </p>
              </div>

              {/* Manual Link */}
              <Link href="/login">
                <Button size="lg" className="w-full">
                  Sign In Now
                </Button>
              </Link>
            </>
          )}
        </div>

        {/* Help Text */}
        {!success && !token && (
          <div className="mt-8 text-center">
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Link expired? <Link href="/forgot-password" className="text-admin-primary hover:underline">Request a new one</Link>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-admin-primary"></div>
    </div>}>
      <ResetPasswordContent />
    </Suspense>
  )
}
