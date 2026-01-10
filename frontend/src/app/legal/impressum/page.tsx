// src/app/legal/impressum/page.tsx
/**
 * Impressum (Legal Notice) page - Required for German companies
 */

import Link from 'next/link'

export default function ImpressumPage() {
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

        <h1 className="text-4xl font-bold text-neutral-900 dark:text-white mb-8">Impressum</h1>
        
        <div className="prose prose-lg max-w-none">
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">Company Information</h2>
            <div className="text-neutral-700 dark:text-neutral-300 space-y-2">
              <p><strong>Company Name:</strong> Bonifatus DMS GmbH</p>
              <p><strong>Address:</strong> Business District<br />12345 Berlin, Germany</p>
              <p><strong>Email:</strong> info@bonifatus-dms.com</p>
              <p><strong>Phone:</strong> +49 (0)30 12345678</p>
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">Legal Information</h2>
            <div className="text-neutral-700 dark:text-neutral-300 space-y-2">
              <p><strong>Managing Director:</strong> [Director Name]</p>
              <p><strong>Commercial Register:</strong> HRB [Number] Berlin</p>
              <p><strong>VAT ID:</strong> DE[Number]</p>
              <p><strong>Tax Number:</strong> [Tax Number]</p>
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">Responsible for Content</h2>
            <div className="text-neutral-700 dark:text-neutral-300">
              <p>According to § 55 Abs. 2 RStV:</p>
              <p>
                [Director Name]<br />
                Business District<br />
                12345 Berlin, Germany
              </p>
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">Disclaimer</h2>
            <p className="text-neutral-700 dark:text-neutral-300 mb-4">
              The contents of our pages have been created with the utmost care. However, we cannot guarantee 
              the contents&apos; accuracy, completeness or topicality. According to statutory provisions, we are 
              furthermore responsible for our own content on these web pages.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">Contact</h2>
            <p className="text-neutral-700 dark:text-neutral-300">
              For questions regarding this legal notice, please contact us at{' '}
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