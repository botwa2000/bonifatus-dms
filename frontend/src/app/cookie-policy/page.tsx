// src/app/cookie-policy/page.tsx
/**
 * Cookie Policy page - Detailed cookie usage information
 */

import Link from 'next/link'

export default function CookiePolicyPage() {
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

        <h1 className="text-4xl font-bold text-neutral-900 mb-8">Cookie Policy</h1>

        <div className="prose prose-lg max-w-none">
          <p className="text-neutral-600 mb-6">
            <strong>Last updated:</strong> November 20, 2025
          </p>

          <p className="text-neutral-700 mb-6">
            This Cookie Policy explains how Bonifatus DMS uses cookies and similar tracking technologies on our website and services. This policy complies with the EU ePrivacy Directive, GDPR, and other applicable regulations.
          </p>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">1. What Are Cookies?</h2>
            <p className="text-neutral-700 mb-4">
              Cookies are small text files that are stored on your device (computer, tablet, or mobile) when you visit a website. They help websites remember your actions and preferences over time, so you don&apos;t have to re-enter information when you return to the site or browse from one page to another.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">2. How We Use Cookies</h2>
            <p className="text-neutral-700 mb-4">
              We use cookies for several purposes, which fall into the following categories:
            </p>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">2.1 Strictly Necessary Cookies (Always Active)</h3>
            <p className="text-neutral-700 mb-4">
              These cookies are essential for the website to function properly. Without these cookies, services you have requested cannot be provided. <strong>These cookies do not require your consent under GDPR.</strong>
            </p>
            <div className="bg-neutral-50 p-4 rounded mb-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200">
                    <th className="text-left py-2">Cookie Name</th>
                    <th className="text-left py-2">Purpose</th>
                    <th className="text-left py-2">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-neutral-100">
                    <td className="py-2"><code className="text-xs">access_token</code></td>
                    <td className="py-2">Authentication token for secure login</td>
                    <td className="py-2">30 minutes</td>
                  </tr>
                  <tr className="border-b border-neutral-100">
                    <td className="py-2"><code className="text-xs">refresh_token</code></td>
                    <td className="py-2">Token to refresh authentication session</td>
                    <td className="py-2">30 days</td>
                  </tr>
                  <tr>
                    <td className="py-2"><code className="text-xs">cc_cookie</code></td>
                    <td className="py-2">Stores your cookie consent preferences</td>
                    <td className="py-2">1 year</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">2.2 Analytics Cookies (Optional)</h3>
            <p className="text-neutral-700 mb-4">
              These cookies help us understand how visitors interact with our website by collecting and reporting information anonymously. We use these cookies to improve our service.
            </p>
            <p className="text-neutral-700 mb-4">
              <strong>Your consent is required for these cookies.</strong> You can enable or disable them through our cookie consent banner.
            </p>
            <div className="bg-neutral-50 p-4 rounded mb-4">
              <p className="text-neutral-700 mb-2"><strong>Provider:</strong> Google Analytics (if enabled)</p>
              <p className="text-neutral-700 mb-2"><strong>Purpose:</strong> Website usage analytics</p>
              <p className="text-neutral-700 mb-2"><strong>Data collected:</strong> Page views, session duration, bounce rate (anonymized)</p>
              <p className="text-neutral-700"><strong>Data retention:</strong> 26 months</p>
            </div>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">2.3 Functionality Cookies (Optional)</h3>
            <p className="text-neutral-700 mb-4">
              These cookies enable enhanced functionality and personalization, such as remembering your preferences and providing improved features.
            </p>
            <p className="text-neutral-700 mb-4">
              <strong>Your consent is required for these cookies.</strong>
            </p>
            <div className="bg-neutral-50 p-4 rounded mb-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200">
                    <th className="text-left py-2">Service</th>
                    <th className="text-left py-2">Purpose</th>
                    <th className="text-left py-2">Cookies</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="py-2">Stripe</td>
                    <td className="py-2">Payment processing and fraud detection</td>
                    <td className="py-2"><code className="text-xs">__stripe_mid, __stripe_sid</code></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">3. Third-Party Cookies</h2>
            <p className="text-neutral-700 mb-4">
              Some cookies are placed by third-party services that appear on our pages:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li><strong>Google OAuth:</strong> Used for secure authentication when you log in with Google</li>
              <li><strong>Stripe:</strong> Used for payment processing and fraud prevention</li>
              <li><strong>Cloudflare:</strong> Security and performance cookies (CDN, DDoS protection)</li>
            </ul>
            <p className="text-neutral-700 mt-4">
              These third-party services have their own privacy policies and cookie policies, which we encourage you to review.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">4. Managing Your Cookie Preferences</h2>
            <p className="text-neutral-700 mb-4">
              You have several options to manage or delete cookies:
            </p>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">4.1 Cookie Consent Banner</h3>
            <p className="text-neutral-700 mb-4">
              When you first visit our website, you&apos;ll see a cookie consent banner where you can:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li>Accept all cookies</li>
              <li>Reject optional cookies (only necessary cookies will be used)</li>
              <li>Manage individual cookie categories</li>
            </ul>
            <p className="text-neutral-700 mb-4">
              You can change your preferences at any time by clicking the cookie settings button (usually found in the footer or privacy settings).
            </p>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">4.2 Browser Settings</h3>
            <p className="text-neutral-700 mb-4">
              Most web browsers allow you to control cookies through their settings:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li><strong>Chrome:</strong> Settings &gt; Privacy and security &gt; Cookies and other site data</li>
              <li><strong>Firefox:</strong> Settings &gt; Privacy & Security &gt; Cookies and Site Data</li>
              <li><strong>Safari:</strong> Preferences &gt; Privacy &gt; Manage Website Data</li>
              <li><strong>Edge:</strong> Settings &gt; Cookies and site permissions</li>
            </ul>
            <p className="text-neutral-700 mt-4">
              <strong>Note:</strong> Blocking all cookies may prevent certain features of our website from working properly.
            </p>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">4.3 Do Not Track (DNT)</h3>
            <p className="text-neutral-700 mb-4">
              Our website respects the Do Not Track (DNT) browser signal. If you have DNT enabled, we will not use analytics or tracking cookies.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">5. Cookie Lifespan</h2>
            <p className="text-neutral-700 mb-4">
              Cookies can be either session cookies or persistent cookies:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li><strong>Session Cookies:</strong> Temporary cookies that expire when you close your browser</li>
              <li><strong>Persistent Cookies:</strong> Remain on your device for a specified period or until manually deleted</li>
            </ul>
            <p className="text-neutral-700 mt-4">
              See the tables above for specific cookie durations.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">6. Changes to This Cookie Policy</h2>
            <p className="text-neutral-700 mb-4">
              We may update this Cookie Policy from time to time. When we make changes:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>We will update the &quot;Last updated&quot; date at the top</li>
              <li>For significant changes, we may display a notification or request renewed consent</li>
              <li>We recommend checking this page periodically for updates</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">7. More Information</h2>
            <p className="text-neutral-700 mb-4">
              For more information about how we handle your data, please see our:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li><Link href="/legal/privacy" className="text-admin-primary hover:underline">Privacy Policy</Link> - Complete privacy information</li>
              <li><Link href="/legal/terms" className="text-admin-primary hover:underline">Terms of Service</Link> - Terms and conditions</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">8. Contact Us</h2>
            <p className="text-neutral-700 mb-4">
              If you have questions about our use of cookies, please contact:
            </p>
            <div className="bg-neutral-50 p-4 rounded">
              <p className="text-neutral-700 mb-2">
                <strong>Email:</strong>{' '}
                <Link href="/contact" className="text-admin-primary hover:underline">privacy@bonidoc.com</Link>
              </p>
              <p className="text-neutral-700">
                <strong>Subject:</strong> Cookie Policy Inquiry
              </p>
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">9. Useful Resources</h2>
            <p className="text-neutral-700 mb-4">
              For more information about cookies and online privacy:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li><Link href="https://www.allaboutcookies.org" target="_blank" rel="noopener noreferrer" className="text-admin-primary hover:underline">AllAboutCookies.org</Link> - Cookie information</li>
              <li><Link href="https://ico.org.uk/for-the-public/online/cookies/" target="_blank" rel="noopener noreferrer" className="text-admin-primary hover:underline">ICO Cookie Guidance</Link> - UK Information Commissioner</li>
              <li><Link href="https://edpb.europa.eu" target="_blank" rel="noopener noreferrer" className="text-admin-primary hover:underline">European Data Protection Board</Link> - EU guidelines</li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  )
}
