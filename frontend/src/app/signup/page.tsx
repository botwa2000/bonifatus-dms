// src/app/signup/page.tsx
/**
 * Signup Page - Conversion-Optimized Registration Flow
 * Industry best practices: Clear CTAs, social + email options, trust signals
 */

'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { GoogleLoginButton } from '@/components/GoogleLoginButton'
import { FacebookLoginButton } from '@/components/FacebookLoginButton'
import { Button } from '@/components/ui/Button'
import { trackSignup } from '@/lib/analytics'
import { logger } from '@/lib/logger'

function SignupContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showEmailForm, setShowEmailForm] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Get tier selection from URL params
  const tierId = searchParams.get('tier_id') || '0'
  const tierName = searchParams.get('tier_name') || 'Free'
  const billingCycle = searchParams.get('billing_cycle') || 'monthly'

  // Form state
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    confirmPassword: ''
  })

  const [passwordStrength, setPasswordStrength] = useState({
    valid: false,
    errors: []
  })

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

  const handleEmailSignup = async (e: React.FormEvent) => {
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
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/email/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        // Track signup event for Google Ads conversion
        trackSignup('email')

        // Store tier selection for after email verification
        if (tierId) {
          sessionStorage.setItem('selected_tier_id', tierId)
          sessionStorage.setItem('selected_billing_cycle', billingCycle)
        }

        // Store email securely in sessionStorage (not in URL)
        sessionStorage.setItem('verification_email', formData.email)

        // Redirect to email verification page (no email in URL)
        router.push('/verify-email')
      } else {
        setError(data.message || 'Registration failed. Please try again.')
      }
    } catch (error) {
      logger.error('Registration error:', error)
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
              Already have an account?{' '}
              <Link href="/login" className="text-admin-primary hover:text-admin-primary-dark font-medium">
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-md mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Tier Selection Badge (if tier specified) */}
        {tierId !== '0' && (
          <div className="mb-6 p-4 bg-semantic-info-bg dark:bg-blue-900/20 border border-semantic-info-border dark:border-blue-800 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">You&apos;ve selected</p>
                <p className="text-lg font-semibold text-neutral-900 dark:text-white">
                  {tierName} Plan
                  {billingCycle === 'yearly' && <span className="text-sm text-admin-primary ml-2">(Save 20%)</span>}
                </p>
              </div>
              <Link href="/#pricing" className="text-sm text-admin-primary hover:underline">
                Change
              </Link>
            </div>
          </div>
        )}

        {/* Headline */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-neutral-900 dark:text-white mb-2">
            Create your account
          </h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            Start organizing your documents automatically
          </p>
        </div>

        {/* Auth Options */}
        <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-8">
          {!showEmailForm ? (
            <div className="space-y-4">
              {/* Google Sign Up (Primary) */}
              <GoogleLoginButton
                className="w-full"
                size="lg"
                tierId={parseInt(tierId)}
                billingCycle={billingCycle as 'monthly' | 'yearly'}
              >
                <div className="flex items-center justify-center gap-3">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Continue with Google
                </div>
              </GoogleLoginButton>

              {/* Facebook Sign Up */}
              <FacebookLoginButton
                className="w-full"
                size="lg"
                tierId={parseInt(tierId)}
                billingCycle={billingCycle as 'monthly' | 'yearly'}
              >
                <div className="flex items-center justify-center gap-3">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#1877F2" d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                  </svg>
                  Continue with Facebook
                </div>
              </FacebookLoginButton>

              {/* OR Divider */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-neutral-300 dark:border-neutral-600"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">
                    or
                  </span>
                </div>
              </div>

              {/* Email Sign Up (Secondary) */}
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
                  Continue with Email
                </div>
              </Button>
            </div>
          ) : (
            /* Email Registration Form */
            <form onSubmit={handleEmailSignup} className="space-y-4">
              {error && (
                <div className="p-3 bg-semantic-error-bg dark:bg-red-900/20 border border-semantic-error-border dark:border-red-800 rounded-lg text-sm text-admin-danger dark:text-red-400">
                  {error}
                </div>
              )}

              {/* Full Name */}
              <div>
                <label htmlFor="full_name" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                  Full Name
                </label>
                <input
                  id="full_name"
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  className="w-full px-4 py-3 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:ring-2 focus:ring-admin-primary focus:border-transparent dark:bg-neutral-700 dark:text-white"
                  placeholder="John Doe"
                />
              </div>

              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
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
                <label htmlFor="password" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                  Password
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
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
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

              {/* Submit Button */}
              <Button
                type="submit"
                size="lg"
                className="w-full"
                disabled={loading || !passwordStrength.valid}
              >
                {loading ? 'Creating account...' : 'Create Account'}
              </Button>

              {/* Back to options */}
              <button
                type="button"
                onClick={() => setShowEmailForm(false)}
                className="w-full text-sm text-neutral-600 dark:text-neutral-400 hover:text-admin-primary"
              >
                ← Back to sign up options
              </button>
            </form>
          )}

          {/* Trust Signals */}
          <div className="mt-6 pt-6 border-t border-neutral-200 dark:border-neutral-700">
            <div className="flex flex-wrap justify-center gap-4 text-xs text-neutral-500 dark:text-neutral-400">
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
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4 text-admin-success dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" clipRule="evenodd" />
                </svg>
                Your Cloud Storage
              </div>
            </div>
          </div>

          {/* Terms */}
          <p className="mt-4 text-xs text-center text-neutral-500 dark:text-neutral-400">
            By signing up, you agree to our{' '}
            <Link href="/legal/terms" className="text-admin-primary hover:underline">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link href="/legal/privacy" className="text-admin-primary hover:underline">
              Privacy Policy
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-admin-primary"></div>
    </div>}>
      <SignupContent />
    </Suspense>
  )
}
