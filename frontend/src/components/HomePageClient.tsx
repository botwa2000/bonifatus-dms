// src/components/HomePageClient.tsx
/**
 * Bonifatus DMS Landing Page - Client Component
 * Contains all interactive homepage functionality
 */

'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Button, FeatureCard } from '@/components/ui'
import { useAuth } from '@/contexts/auth-context'
import { useCurrency } from '@/contexts/currency-context'
import AppHeader from '@/components/AppHeader'
import PublicHeader from '@/components/PublicHeader'
import CurrencySelector from '@/components/CurrencySelector'
import { logger } from '@/lib/logger'

interface TierPlan {
  id: number
  name: string
  display_name: string
  description: string | null
  price_monthly_cents: number
  price_yearly_cents: number
  currency: string
  currency_symbol: string
  storage_quota_bytes: number
  max_file_size_bytes: number
  max_documents: number | null
  max_pages_per_month: number | null
  max_batch_upload_size: number | null
  bulk_operations_enabled: boolean
  api_access_enabled: boolean
  priority_support: boolean
  custom_categories_limit: number | null
  email_to_process_enabled?: boolean
  provider_settings?: Record<string, boolean>
  provider_display_names?: Record<string, string>
}

export default function HomePageClient() {
  const { user } = useAuth()
  const { formatPrice } = useCurrency()
  const [tiers, setTiers] = useState<TierPlan[]>([])
  const [loading, setLoading] = useState(true)
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('yearly')

  useEffect(() => {
    const fetchTiers = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/settings/tiers/public`)
        if (response.ok) {
          const data = await response.json()
          setTiers(data.tiers || [])
        }
      } catch (error) {
        logger.error('Failed to fetch tier plans:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchTiers()
  }, [])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search)
      const referralCode = urlParams.get('ref')
      if (referralCode) {
        sessionStorage.setItem('referral_code', referralCode)
      }
    }
  }, [])

  const formatCentsToEur = (cents: number): number => {
    return cents / 100
  }

  const formatStorage = (bytes: number): string => {
    const gb = bytes / (1024 * 1024 * 1024)
    const mb = bytes / (1024 * 1024)

    if (gb >= 1) {
      return `${gb.toFixed(0)} GB`
    } else if (mb >= 1) {
      return `${mb.toFixed(0)} MB`
    } else {
      return `${bytes} bytes`
    }
  }

  const calculateYearlySavings = (): string => {
    const paidTier = tiers.find(t => t.price_monthly_cents > 0 && t.price_yearly_cents > 0)
    if (!paidTier) return ''

    const monthlyCost = paidTier.price_monthly_cents * 12
    const yearlyCost = paidTier.price_yearly_cents
    const savings = ((monthlyCost - yearlyCost) / monthlyCost) * 100

    return savings > 0 ? `Save ${Math.round(savings)}%` : ''
  }

  return (
    <div className="min-h-screen bg-white dark:bg-neutral-900">
      {user ? (
        <AppHeader title="" showNav={true} />
      ) : (
        <PublicHeader />
      )}

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-neutral-50 to-white dark:from-neutral-900 dark:to-neutral-900 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-5xl font-bold text-neutral-900 dark:text-white mb-6">
              Your Documents,
              <span className="text-admin-primary block">Organized Automatically</span>
            </h1>
            <p className="text-xl text-neutral-600 dark:text-neutral-400 mb-8 max-w-3xl mx-auto">
              AI-powered document management that classifies, extracts, and organizes your PDFs in seconds.
              No manual filing, ever again.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link href="/signup?tier_id=0&tier_name=Free&billing_cycle=monthly">
                <Button size="lg" className="min-w-[200px]">
                  Start free
                </Button>
              </Link>
              <a href="#pricing">
                <Button variant="secondary" size="lg" className="min-w-[200px]">
                  View Pricing
                  <svg className="ml-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </Button>
              </a>
            </div>

            {/* Trust Badges */}
            <div className="mt-12 flex flex-wrap justify-center items-center gap-8 text-sm text-neutral-600 dark:text-neutral-400">
              <div className="flex items-center gap-2">
                <svg className="h-5 w-5 text-admin-success" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">GDPR Compliant</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="h-5 w-5 text-admin-success" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">Your Cloud, Your Control</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="h-5 w-5 text-admin-success" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                </svg>
                <span className="font-medium">99% AI Accuracy</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-12 bg-white dark:bg-neutral-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-neutral-900 dark:text-white mb-4">
              Stop Manual Filing Forever
            </h2>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">
              AI that understands your documents and organizes them automatically
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard
              iconColor="automation"
              icon={
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              }
              title="AI Auto-Categorization"
              description="Invoices, contracts, receipts, taxes - automatically sorted into the right folders"
            />

            <FeatureCard
              iconColor="search"
              icon={
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              }
              title="Find Anything Instantly"
              description="Smart search across all documents - even finds text in handwritten notes"
            />

            <FeatureCard
              iconColor="cloud"
              icon={
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                </svg>
              }
              title="Your Cloud, Your Control"
              description={<>Files stored safely in <strong>your Google Drive</strong> - we never store your documents on our servers</>}
            />

            <FeatureCard
              iconColor="upload"
              icon={
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              }
              title="Bulk Upload & Process"
              description="Upload hundreds of documents at once - AI processes them all automatically (Starter+)"
            />

            <FeatureCard
              iconColor="email"
              icon={
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              }
              title="Email Your Documents"
              description="Forward to your@docs.bonidoc.com - we'll process and organize it automatically (Pro)"
            />

            <FeatureCard
              iconColor="language"
              icon={
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
              }
              title="Multilingual Document Analysis"
              description={<>AI automatically detects and processes documents in <strong>multiple languages</strong> - analyze international documents effortlessly</>}
            />
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 bg-neutral-50 dark:bg-neutral-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-neutral-900 dark:text-white mb-4">
              How It Works
            </h2>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">
              Three simple steps to organized documents
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="h-16 w-16 bg-admin-primary text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                1
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2">Upload or Email</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Drag & drop files, email them, or bulk upload hundreds at once
              </p>
            </div>

            <div className="text-center">
              <div className="h-16 w-16 bg-admin-primary text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                2
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2">AI Processes</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                AI extracts text, identifies document type, and auto-categorizes
              </p>
            </div>

            <div className="text-center">
              <div className="h-16 w-16 bg-admin-primary text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                3
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2">Find Instantly</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Search, filter, access from anywhere - perfectly organized forever
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-20 bg-white dark:bg-neutral-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-neutral-900 dark:text-white mb-4">
              Perfect For
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 border border-neutral-200 dark:border-neutral-800 rounded-lg">
              <div className="text-4xl mb-4">🏢</div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2">Small Business Owners</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Invoices, contracts, receipts, employee documents - all organized automatically
              </p>
            </div>

            <div className="p-6 border border-neutral-200 dark:border-neutral-800 rounded-lg">
              <div className="text-4xl mb-4">💼</div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2">Freelancers & Consultants</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Client documents, invoices, project files, taxes - find anything in seconds
              </p>
            </div>

            <div className="p-6 border border-neutral-200 dark:border-neutral-800 rounded-lg">
              <div className="text-4xl mb-4">🏠</div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2">Personal Use</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Medical records, warranties, bills, important documents - never lose anything again
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-neutral-50 dark:bg-neutral-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-neutral-900 dark:text-white mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">
              Start free, upgrade as you grow. Cancel anytime.
            </p>

            {/* Pricing Controls */}
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setBillingCycle('monthly')}
                  className={`px-6 py-2 rounded-lg font-medium transition-all ${
                    billingCycle === 'monthly'
                      ? 'bg-admin-primary text-white shadow-md'
                      : 'bg-white dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-600'
                  }`}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBillingCycle('yearly')}
                  className={`px-6 py-2 rounded-lg font-medium transition-all relative ${
                    billingCycle === 'yearly'
                      ? 'bg-admin-primary text-white shadow-md'
                      : 'bg-white dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-600'
                  }`}
                >
                  Annual
                  {calculateYearlySavings() && (
                    <span className="ml-2 text-xs bg-admin-success text-white px-2 py-0.5 rounded-full">
                      {calculateYearlySavings()}
                    </span>
                  )}
                </button>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-neutral-600 dark:text-neutral-400">Currency:</span>
                <CurrencySelector />
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {loading ? (
              <div className="col-span-3 text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 dark:border-orange-400 mx-auto"></div>
                <p className="mt-4 text-neutral-600 dark:text-neutral-400">Loading pricing plans...</p>
              </div>
            ) : tiers.length === 0 ? (
              <div className="col-span-3 text-center py-12">
                <p className="text-neutral-600 dark:text-neutral-400">No pricing plans available</p>
              </div>
            ) : (
              tiers.map((tier) => {
                const isPro = tier.id === 2
                const isFree = tier.id === 0
                const isStarter = tier.id === 1
                const storageDisplay = tier.storage_quota_bytes >= 1000000000000 || tier.storage_quota_bytes === null
                  ? 'Unlimited'
                  : formatStorage(tier.storage_quota_bytes)
                const pagesDisplay = tier.max_pages_per_month === null
                  ? 'Unlimited pages'
                  : `${tier.max_pages_per_month} pages/month`

                return (
                  <div
                    key={tier.id}
                    className={`bg-white dark:bg-neutral-900 rounded-xl p-8 relative ${
                      isPro
                        ? 'border-2 border-orange-500 dark:border-orange-400'
                        : 'border border-neutral-200 dark:border-neutral-700'
                    }`}
                  >

                    <div className="text-center mb-8">
                      <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-2">
                        {tier.display_name}
                      </h3>
                      <div className="mb-4">
                        <span className="text-3xl font-bold text-neutral-900 dark:text-white">
                          {formatPrice(
                            formatCentsToEur(
                              billingCycle === 'yearly'
                                ? Math.round(tier.price_yearly_cents / 12)
                                : tier.price_monthly_cents
                            )
                          )}
                        </span>
                        <span className="text-neutral-600 dark:text-neutral-400">/month</span>
                        {!isFree && billingCycle === 'yearly' && (
                          <div className="text-sm text-admin-success dark:text-green-400 mt-1">
                            {formatPrice(formatCentsToEur(tier.price_yearly_cents))} billed annually
                          </div>
                        )}
                      </div>
                      <p className="text-neutral-600 dark:text-neutral-400">
                        {tier.description || (isFree ? 'Perfect for trying it out' : isStarter ? 'For light personal use' : 'For professionals & teams')}
                      </p>
                    </div>

                    <ul className="space-y-3 mb-8">
                      <li className="flex items-start">
                        <svg className="h-5 w-5 text-admin-success mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span className="text-neutral-700 dark:text-neutral-300">
                          <strong>{pagesDisplay}</strong>
                        </span>
                      </li>

                      <li className="flex items-start">
                        <svg className="h-5 w-5 text-admin-success mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span className="text-neutral-700 dark:text-neutral-300">
                          <strong>{storageDisplay}</strong> storage{storageDisplay !== 'Unlimited' ? ' limit' : ''}
                        </span>
                      </li>

                      <li className="flex items-start">
                        <svg className="h-5 w-5 text-admin-success mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span className="text-neutral-700 dark:text-neutral-300">
                          {isPro ? 'Unlimited users' : '1 user'}
                        </span>
                      </li>

                      <li className="flex items-start">
                        <svg className="h-5 w-5 text-admin-success mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span className="text-neutral-700 dark:text-neutral-300">
                          {tier.bulk_operations_enabled ? <strong>✨ Bulk processing</strong> : 'AI-powered categorization'}
                        </span>
                      </li>

                      <li className="flex items-start">
                        <svg className="h-5 w-5 text-admin-success mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span className="text-neutral-700 dark:text-neutral-300">
                          Multilingual {tier.bulk_operations_enabled ? 'analysis' : 'document analysis'}
                        </span>
                      </li>

                      {isFree && (
                        <li className="flex items-start">
                          <svg className="h-5 w-5 text-admin-success mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                          <span className="text-neutral-700 dark:text-neutral-300">One-by-one processing</span>
                        </li>
                      )}

                      {tier.email_to_process_enabled && (
                        <li className="flex items-start">
                          <svg className="h-5 w-5 text-admin-success mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                          <span className="text-neutral-700 dark:text-neutral-300">
                            <strong>✨ Email-to-process</strong>
                          </span>
                        </li>
                      )}

                      {tier.provider_settings && (() => {
                        const enabledProviders = Object.entries(tier.provider_settings)
                          .filter(([, enabled]) => enabled)
                          .map(([key]) => tier.provider_display_names?.[key] || key.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()))
                        const providerCount = enabledProviders.length
                        if (providerCount === 0) return null
                        const label = providerCount >= 2 ? 'Multi-cloud' : 'Single cloud'
                        return (
                          <li className="flex items-start">
                            <svg className="h-5 w-5 text-admin-success mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                            <span className="text-neutral-700 dark:text-neutral-300">
                              {providerCount >= 2 ? <strong>✨ {label}:</strong> : <>{label}:</>} {enabledProviders.join(', ')}
                            </span>
                          </li>
                        )
                      })()}
                    </ul>

                    <Link href={`/signup?tier_id=${tier.id}&tier_name=${encodeURIComponent(tier.display_name)}&billing_cycle=${billingCycle}`}>
                      <Button
                        className="w-full"
                        variant="secondary"
                      >
                        {isFree ? 'Start Free' : 'Get Started'}
                      </Button>
                    </Link>

                    <p className="text-center text-xs text-neutral-500 dark:text-neutral-400 mt-4">
                      Risk-free • Cancel anytime
                    </p>
                  </div>
                )
              })
            )}
          </div>

          <div className="mt-12 text-center space-y-3">
            <div className="inline-block bg-semantic-success-bg dark:bg-green-900/20 border border-semantic-success-border dark:border-green-800 rounded-lg px-6 py-3">
              <p className="text-sm text-neutral-700 dark:text-neutral-300">
                <svg className="inline h-5 w-5 text-admin-success mr-2 -mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <strong>Your Documents Stay in Your Cloud:</strong> Files are stored in your personal Google Drive. We never store your documents on our servers.
              </p>
            </div>
            <p className="text-neutral-600 dark:text-neutral-400 text-sm">
              <strong>Fair use policy:</strong> Consistent usage above 2x stated limits may require an upgrade.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-admin-primary">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Never Manually File Documents Again?
          </h2>
          <p className="text-xl text-blue-100 dark:text-blue-200 dark:text-blue-300 mb-8 max-w-2xl mx-auto">
            Start free with 20 pages/month. No credit card required.
          </p>
          <Link href="/signup?tier_id=0&tier_name=Free&billing_cycle=monthly">
            <Button size="lg" className="!bg-white !text-admin-primary hover:!bg-neutral-50">
              Start free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-neutral-900 text-neutral-300 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center mb-4">
                <Image
                  src="/logo-medium.png"
                  alt="Bonidoc"
                  width={160}
                  height={40}
                  className="object-contain"
                />
              </div>
              <p className="text-neutral-400">
                AI-powered document management for modern professionals.
              </p>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-4">Product</h3>
              <ul className="space-y-2">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><Link href="/faq" className="hover:text-white transition-colors">FAQ</Link></li>
                <li><Link href="/security" className="hover:text-white transition-colors">Security</Link></li>
              </ul>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-4">Company</h3>
              <ul className="space-y-2">
                <li><Link href="/about" className="hover:text-white transition-colors">About</Link></li>
                <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
              </ul>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-4">Legal</h3>
              <ul className="space-y-2">
                <li><Link href="/legal/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
                <li><Link href="/legal/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
                <li><Link href="/legal/impressum" className="hover:text-white transition-colors">Impressum</Link></li>
                <li><Link href="/legal/privacy" className="hover:text-white transition-colors">GDPR & Privacy</Link></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-neutral-800 mt-12 pt-8 text-center">
            <p className="text-neutral-400">
              © {new Date().getFullYear()} Bonidoc. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
