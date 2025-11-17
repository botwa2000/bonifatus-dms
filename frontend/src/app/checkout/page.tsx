'use client'

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { apiClient } from '@/services/api-client'
import { useCurrency } from '@/contexts/currency-context'

function CheckoutContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { selectedCurrency } = useCurrency()
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('Initializing checkout...')

  useEffect(() => {
    const initializeCheckout = async () => {
      try {
        const tierId = searchParams.get('tier_id')
        const billingCycle = searchParams.get('billing_cycle') || 'monthly'
        const isNewUser = searchParams.get('new_user') === 'true'

        if (!tierId) {
          setError('Missing tier selection')
          setTimeout(() => router.push('/'), 3000)
          return
        }

        if (!selectedCurrency) {
          setError('Currency not loaded')
          setTimeout(() => router.push('/'), 3000)
          return
        }

        setStatus(`Creating checkout session for tier ${tierId} in ${selectedCurrency.code}...`)

        // Create Stripe checkout session with selected currency
        const response = await apiClient.post<{
          checkout_url: string
          session_id: string
        }>('/api/v1/billing/subscriptions/create-checkout', {
          tier_id: parseInt(tierId),
          billing_cycle: billingCycle as 'monthly' | 'yearly',
          currency: selectedCurrency.code
        })

        if (response.checkout_url) {
          setStatus('Redirecting to payment...')
          // Redirect to Stripe checkout
          window.location.href = response.checkout_url
        } else {
          throw new Error('No checkout URL received')
        }
      } catch (err) {
        console.error('Checkout error:', err)
        const errorMessage = (err as {response?: {data?: {detail?: string}}})?.response?.data?.detail || 'Failed to initialize checkout'
        setError(errorMessage)

        // Redirect to pricing page after error
        setTimeout(() => router.push('/?error=checkout_failed'), 3000)
      }
    }

    initializeCheckout()
  }, [searchParams, router, selectedCurrency])

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-900">
      <div className="max-w-md w-full p-8 bg-white dark:bg-neutral-800 rounded-lg shadow-lg">
        {error ? (
          <div className="text-center">
            <div className="mb-4">
              <svg className="mx-auto h-12 w-12 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2">Checkout Error</h2>
            <p className="text-neutral-600 dark:text-neutral-400 mb-4">{error}</p>
            <p className="text-sm text-neutral-500">Redirecting you back...</p>
          </div>
        ) : (
          <div className="text-center">
            <div className="mb-4">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2">Setting Up Your Subscription</h2>
            <p className="text-neutral-600 dark:text-neutral-400">{status}</p>
            <p className="text-sm text-neutral-500 mt-4">Please wait while we redirect you to secure payment...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function CheckoutPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-900">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    }>
      <CheckoutContent />
    </Suspense>
  )
}
