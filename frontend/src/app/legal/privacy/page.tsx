// src/app/legal/privacy/page.tsx
/**
 * Privacy Policy page
 */

import Link from 'next/link'

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-white">
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

        <h1 className="text-4xl font-bold text-neutral-900 mb-8">Privacy Policy</h1>
        
        <div className="prose prose-lg max-w-none">
          <p className="text-neutral-600 mb-6">
            <strong>Last updated:</strong> December 2024
          </p>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">1. Information We Collect</h2>
            <p className="text-neutral-700 mb-4">
              We collect information you provide directly to us, such as when you create an account, upload documents, or contact us for support.
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>Account information (name, email address)</li>
              <li>Document metadata and content</li>
              <li>Usage data and analytics</li>
              <li>Communication preferences</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">2. How We Use Your Information</h2>
            <p className="text-neutral-700 mb-4">
              We use the information we collect to provide, maintain, and improve our services:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>To provide and operate the Bonifatus DMS service</li>
              <li>To process and store your documents securely</li>
              <li>To communicate with you about your account</li>
              <li>To improve our services and develop new features</li>
              <li>To comply with legal obligations</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">3. Data Storage and Security</h2>
            <p className="text-neutral-700 mb-4">
              We implement appropriate technical and organizational measures to protect your personal data:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>Data is encrypted in transit and at rest</li>
              <li>Regular security audits and assessments</li>
              <li>Access controls and authentication</li>
              <li>Data backup and recovery procedures</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">4. Data Sharing</h2>
            <p className="text-neutral-700 mb-4">
              We do not sell, trade, or otherwise transfer your personal information to third parties without your consent, except as described in this policy:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>With your explicit consent</li>
              <li>To comply with legal requirements</li>
              <li>To protect our rights and safety</li>
              <li>With trusted service providers under strict agreements</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">5. Your Rights (GDPR)</h2>
            <p className="text-neutral-700 mb-4">
              Under the General Data Protection Regulation (GDPR), you have the following rights:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>Right to access your personal data</li>
              <li>Right to rectification (correction) of your data</li>
              <li>Right to erasure (&quot;right to be forgotten&quot;)</li>
              <li>Right to restrict processing</li>
              <li>Right to data portability</li>
              <li>Right to object to processing</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">6. Cookies and Tracking</h2>
            <p className="text-neutral-700 mb-4">
              We use cookies and similar technologies to enhance your experience:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>Essential cookies for authentication and security</li>
              <li>Analytics cookies to understand usage patterns</li>
              <li>Preference cookies to remember your settings</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">7. Children&apos;s Privacy</h2>
            <p className="text-neutral-700 mb-4">
              Our service is not intended for children under 16 years of age. We do not knowingly collect personal information from children under 16.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">8. Changes to This Policy</h2>
            <p className="text-neutral-700 mb-4">
              We may update this privacy policy from time to time. We will notify you of any changes by posting the new policy on this page and updating the &quot;Last updated&quot; date.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">9. Contact Us</h2>
            <p className="text-neutral-700">
              If you have any questions about this Privacy Policy, please contact us at{' '}
              <Link href="/contact" className="text-admin-primary hover:underline">
                privacy@bonifatus-dms.com
              </Link>
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}