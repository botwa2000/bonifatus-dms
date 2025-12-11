// src/app/forgot-password/page.tsx
/**
 * Forgot Password Page
 * User requests password reset link via email
 */

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { Button } from '@/components/ui/Button'

export default function ForgotPasswordPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/email/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      })

      const data = await response.json()

      if (response.ok) {
        setSuccess(true)
      } else {
        setError(data.message || 'Failed to send reset link. Please try again.')
      }
    } catch (error) {
      console.error('Forgot password error:', error)
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
              Remember your password?{' '}
              <Link href="/login" className="text-admin-primary hover:text-admin-primary-dark font-medium">
                Sign in
              </Link>
            </div>
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
                <div className="w-16 h-16 bg-orange-100 dark:bg-orange-900/30 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-admin-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                </div>
              </div>

              {/* Headline */}
              <div className="text-center mb-8">
                <h1 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
                  Forgot your password?
                </h1>
                <p className="text-neutral-600 dark:text-neutral-400">
                  No worries! Enter your email and we&apos;ll send you reset instructions.
                </p>
              </div>

              {/* Error Message */}
              {error && (
                <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400">
                  {error}
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                    Email Address
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-3 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:ring-2 focus:ring-admin-primary focus:border-transparent dark:bg-neutral-700 dark:text-white"
                    placeholder="you@example.com"
                  />
                </div>

                <Button
                  type="submit"
                  size="lg"
                  className="w-full"
                  disabled={loading}
                >
                  {loading ? 'Sending...' : 'Send Reset Link'}
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
                <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>

              {/* Success Message */}
              <div className="text-center mb-8">
                <h1 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
                  Check your email
                </h1>
                <p className="text-neutral-600 dark:text-neutral-400">
                  If an account exists for <span className="font-medium text-neutral-900 dark:text-white">{email}</span>, you&apos;ll receive password reset instructions shortly.
                </p>
              </div>

              {/* Info Box */}
              <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  <strong className="text-neutral-900 dark:text-white">Didn&apos;t receive the email?</strong><br />
                  Check your spam folder. The link expires in 1 hour.
                </p>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3">
                <Button
                  onClick={() => setSuccess(false)}
                  variant="secondary"
                  size="lg"
                  className="w-full"
                >
                  Try another email
                </Button>

                <Link href="/login">
                  <Button
                    variant="secondary"
                    size="lg"
                    className="w-full"
                  >
                    Back to sign in
                  </Button>
                </Link>
              </div>
            </>
          )}
        </div>

        {/* Help Text */}
        {!success && (
          <div className="mt-8 text-center">
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Need help? <Link href="/contact" className="text-admin-primary hover:underline">Contact support</Link>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
