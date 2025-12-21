// src/app/verify-email/page.tsx
/**
 * Email Verification Page
 * User enters 6-digit code sent to their email
 */

'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { Button } from '@/components/ui/Button'
import { logger } from '@/lib/logger'

function VerifyEmailContent() {
  const router = useRouter()
  const [email, setEmail] = useState('')

  const [code, setCode] = useState(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [resendLoading, setResendLoading] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)

  // Get email from sessionStorage on mount
  useEffect(() => {
    const storedEmail = sessionStorage.getItem('verification_email')
    if (!storedEmail) {
      // No email found, redirect to login
      router.push('/login')
      return
    }
    setEmail(storedEmail)
  }, [router])

  // Auto-focus first input
  useEffect(() => {
    const firstInput = document.getElementById('code-0')
    if (firstInput) {
      firstInput.focus()
    }
  }, [])

  const handleCodeChange = (index: number, value: string) => {
    // Only allow digits
    if (value && !/^\d$/.test(value)) return

    const newCode = [...code]
    newCode[index] = value

    setCode(newCode)

    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.getElementById(`code-${index + 1}`)
      if (nextInput) {
        nextInput.focus()
      }
    }

    // Auto-submit when all 6 digits entered
    if (newCode.every(digit => digit !== '')) {
      handleVerify(newCode.join(''))
    }
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    // Handle backspace
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      const prevInput = document.getElementById(`code-${index - 1}`)
      if (prevInput) {
        prevInput.focus()
      }
    }
  }

  const handleVerify = async (verificationCode?: string) => {
    const codeToVerify = verificationCode || code.join('')

    if (codeToVerify.length !== 6) {
      setError('Please enter all 6 digits')
      return
    }

    setError('')
    setLoading(true)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/email/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email: email,
          code: codeToVerify
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        // Check if user selected a tier during signup
        const selectedTierId = sessionStorage.getItem('selected_tier_id')
        const selectedBillingCycle = sessionStorage.getItem('selected_billing_cycle')

        // Clear all verification-related data from sessionStorage
        sessionStorage.removeItem('verification_email')
        sessionStorage.removeItem('selected_tier_id')
        sessionStorage.removeItem('selected_billing_cycle')

        // Redirect based on tier selection
        if (selectedTierId && selectedTierId !== '0') {
          // Paid tier selected - redirect to checkout
          router.push(`/checkout?tier_id=${selectedTierId}&billing_cycle=${selectedBillingCycle}&new_user=true`)
        } else {
          // Free tier - redirect to dashboard
          router.push('/dashboard?welcome=true')
        }
      } else {
        setError(data.message || 'Invalid verification code. Please try again.')
      }
    } catch (error) {
      logger.error('Verification error:', error)
      setError('An error occurred. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    setResendLoading(true)
    setResendSuccess(false)
    setError('')

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/email/resend-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          purpose: 'registration'
        })
      })

      if (response.ok) {
        setResendSuccess(true)
        setCode(['', '', '', '', '', ''])
        // Focus first input
        const firstInput = document.getElementById('code-0')
        if (firstInput) {
          firstInput.focus()
        }
      } else {
        setError('Failed to resend code. Please try again.')
      }
    } catch (error) {
      logger.error('Resend error:', error)
      setError('An error occurred. Please try again.')
    } finally {
      setResendLoading(false)
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
          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-admin-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
          </div>

          {/* Headline */}
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
              Check your email
            </h1>
            <p className="text-neutral-600 dark:text-neutral-400">
              We sent a 6-digit code to<br />
              <span className="font-medium text-neutral-900 dark:text-white">{email}</span>
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400 text-center">
              {error}
            </div>
          )}

          {/* Success Message */}
          {resendSuccess && (
            <div className="mb-6 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-600 dark:text-green-400 text-center">
              New code sent! Check your email.
            </div>
          )}

          {/* Code Input */}
          <div className="mb-6">
            <div className="flex justify-center gap-2">
              {code.map((digit, index) => (
                <input
                  key={index}
                  id={`code-${index}`}
                  type="text"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleCodeChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  className="w-12 h-14 text-center text-2xl font-bold border-2 border-neutral-300 dark:border-neutral-600 rounded-lg focus:ring-2 focus:ring-admin-primary focus:border-transparent dark:bg-neutral-700 dark:text-white"
                  disabled={loading}
                />
              ))}
            </div>
          </div>

          {/* Verify Button */}
          <Button
            onClick={() => handleVerify()}
            size="lg"
            className="w-full mb-4"
            disabled={loading || code.some(digit => digit === '')}
          >
            {loading ? 'Verifying...' : 'Verify Email'}
          </Button>

          {/* Resend Code */}
          <div className="text-center">
            <button
              onClick={handleResend}
              disabled={resendLoading}
              className="text-sm text-neutral-600 dark:text-neutral-400 hover:text-admin-primary disabled:opacity-50"
            >
              {resendLoading ? 'Sending...' : "Didn't receive the code? Resend"}
            </button>
          </div>

          {/* Back to signup */}
          <div className="mt-6 pt-6 border-t border-neutral-200 dark:border-neutral-700 text-center">
            <Link href="/signup" className="text-sm text-neutral-600 dark:text-neutral-400 hover:text-admin-primary">
              ← Back to sign up
            </Link>
          </div>
        </div>

        {/* Help Text */}
        <div className="mt-8 text-center">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Check your spam folder if you don&apos;t see the email.
          </p>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2">
            The code expires in 15 minutes.
          </p>
        </div>
      </div>
    </div>
  )
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-admin-primary"></div>
    </div>}>
      <VerifyEmailContent />
    </Suspense>
  )
}
