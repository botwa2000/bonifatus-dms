// src/app/legal/terms/page.tsx
/**
 * Terms of Service page
 */

import Link from 'next/link'

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-900">
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="mb-8">
          <Link 
            href="/" 
            className="text-admin-primary hover:underline flex items-center"
          >
            <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Home
          </Link>
        </div>

        <h1 className="text-4xl font-bold text-neutral-900 dark:text-white mb-8">Terms of Service</h1>
        
        <div className="prose prose-lg max-w-none">
          <p className="text-neutral-600 mb-6">
            <strong>Last updated:</strong> December 2024
          </p>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">1. Acceptance of Terms</h2>
            <p className="text-neutral-700 dark:text-neutral-300 mb-4">
              By accessing and using Bonifatus DMS (&quot;Service&quot;), you accept and agree to be bound by the terms and provision of this agreement.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">2. Service Description</h2>
            <p className="text-neutral-700 dark:text-neutral-300 mb-4">
              Bonifatus DMS is a professional document management system that provides secure storage, organization, and retrieval of digital documents.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">3. Account Terms</h2>
            <ul className="list-disc pl-6 text-neutral-700 dark:text-neutral-300 space-y-2">
              <li>You must provide accurate and complete information when creating your account</li>
              <li>You are responsible for maintaining the security of your account</li>
              <li>You must notify us immediately of any unauthorized use of your account</li>
              <li>You may not use our service for any illegal or unauthorized purpose</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">4. Free Trial Terms</h2>
            <ul className="list-disc pl-6 text-neutral-700 dark:text-neutral-300 space-y-2">
              <li>New users receive 30 days of premium features at no cost</li>
              <li>The trial period begins upon account creation</li>
              <li>No payment information is required for the trial period</li>
              <li>After the trial period, accounts revert to the free tier unless upgraded</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">5. Privacy and Data Protection</h2>
            <p className="text-neutral-700 dark:text-neutral-300 mb-4">
              Your privacy is important to us. Please review our Privacy Policy to understand how we collect, use, and protect your information.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">6. Contact Information</h2>
            <p className="text-neutral-700 dark:text-neutral-300">
              If you have any questions about these Terms of Service, please contact us at{' '}
              <Link href="/contact" className="text-admin-primary hover:underline">
                legal@bonifatus-dms.com
              </Link>
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}