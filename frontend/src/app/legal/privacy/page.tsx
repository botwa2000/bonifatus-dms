// src/app/legal/privacy/page.tsx
/**
 * Privacy Policy page - GDPR, CCPA, and internationally compliant
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
            <strong>Last updated:</strong> November 20, 2025
          </p>

          <p className="text-neutral-700 mb-6">
            Bonifatus DMS (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our document management service (the &quot;Service&quot;). This policy complies with the General Data Protection Regulation (GDPR), California Consumer Privacy Act (CCPA), and other applicable data protection laws.
          </p>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">1. Information We Collect</h2>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">1.1 Information You Provide</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li><strong>Account Information:</strong> When you create an account using Google OAuth, we collect your name, email address, and profile picture from your Google account.</li>
              <li><strong>Document Content:</strong> Documents you upload, including metadata, file names, and document text extracted through OCR (Optical Character Recognition).</li>
              <li><strong>Payment Information:</strong> When you subscribe to paid tiers, billing information is processed by Stripe. We do not store your complete credit card numbers.</li>
              <li><strong>Communication Data:</strong> Messages you send through our contact forms or support channels.</li>
            </ul>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">1.2 Automatically Collected Information</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li><strong>Usage Data:</strong> Information about how you use the Service, including pages viewed, features accessed, and actions taken.</li>
              <li><strong>Device Information:</strong> IP address, browser type, operating system, device identifiers.</li>
              <li><strong>Cookies and Tracking:</strong> See our <Link href="/cookie-policy" className="text-admin-primary hover:underline">Cookie Policy</Link> for detailed information.</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">2. How We Use Your Information</h2>
            <p className="text-neutral-700 mb-4">We process your personal data for the following purposes:</p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li><strong>Service Provision:</strong> To operate, maintain, and provide the features of our Service.</li>
              <li><strong>Authentication:</strong> To verify your identity using Google OAuth.</li>
              <li><strong>Document Processing:</strong> To perform OCR, translation, categorization, and other document analysis features.</li>
              <li><strong>Storage Integration:</strong> To sync your documents with Google Drive when you enable this feature.</li>
              <li><strong>Payment Processing:</strong> To process subscriptions and handle billing through Stripe.</li>
              <li><strong>Communication:</strong> To send transactional emails (account notifications, password resets, payment confirmations) via Brevo.</li>
              <li><strong>Service Improvement:</strong> To analyze usage patterns and improve our Service.</li>
              <li><strong>Legal Compliance:</strong> To comply with applicable laws and regulations.</li>
              <li><strong>Security:</strong> To detect, prevent, and address fraud, security incidents, and technical issues.</li>
            </ul>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3 mt-6">Legal Bases for Processing (GDPR)</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li><strong>Contract Performance:</strong> Processing necessary to provide the Service you requested.</li>
              <li><strong>Consent:</strong> Where you have given explicit consent (e.g., cookie preferences, Google Drive sync).</li>
              <li><strong>Legitimate Interests:</strong> For service improvement, security, and fraud prevention.</li>
              <li><strong>Legal Obligation:</strong> To comply with applicable laws and regulations.</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">3. Third-Party Service Providers</h2>
            <p className="text-neutral-700 mb-4">
              We use the following third-party services to operate our platform. Each has their own privacy policy:
            </p>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">3.1 Google Services</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li><strong>Google OAuth 2.0:</strong> For secure authentication (<Link href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-admin-primary hover:underline">Google Privacy Policy</Link>)</li>
              <li><strong>Google Drive API:</strong> For optional document synchronization (only when you explicitly enable this feature)</li>
              <li>We only request the minimum necessary permissions (email, profile, and Drive access if enabled)</li>
            </ul>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">3.2 Cloudflare</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li>We use Cloudflare for CDN services, DDoS protection, and web application firewall</li>
              <li>Cloudflare may process IP addresses and HTTP headers for security purposes</li>
              <li><Link href="https://www.cloudflare.com/privacypolicy/" target="_blank" rel="noopener noreferrer" className="text-admin-primary hover:underline">Cloudflare Privacy Policy</Link></li>
            </ul>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">3.3 Stripe</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li>Payment processing for subscriptions</li>
              <li>Stripe processes payment information according to PCI DSS standards</li>
              <li>We do not store complete credit card numbers</li>
              <li><Link href="https://stripe.com/privacy" target="_blank" rel="noopener noreferrer" className="text-admin-primary hover:underline">Stripe Privacy Policy</Link></li>
            </ul>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">3.4 Brevo (formerly Sendinblue)</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li>Transactional email delivery (account notifications, password resets, receipts)</li>
              <li><Link href="https://www.brevo.com/legal/privacypolicy/" target="_blank" rel="noopener noreferrer" className="text-admin-primary hover:underline">Brevo Privacy Policy</Link></li>
            </ul>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">3.5 LibreTranslate</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li>Self-hosted translation service for document text translation</li>
              <li>No data is sent to external translation services</li>
            </ul>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">3.6 Hetzner</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li>Infrastructure hosting (servers located in Germany and Finland)</li>
              <li><Link href="https://www.hetzner.com/legal/privacy-policy" target="_blank" rel="noopener noreferrer" className="text-admin-primary hover:underline">Hetzner Privacy Policy</Link></li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">4. Data Storage and Security</h2>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li><strong>Encryption:</strong> All data is encrypted in transit (TLS 1.3) and at rest (AES-256).</li>
              <li><strong>Server Location:</strong> Data is stored on servers in the European Union (Germany and Finland).</li>
              <li><strong>Access Controls:</strong> Strict access controls limit who can access your data.</li>
              <li><strong>Virus Scanning:</strong> All uploaded files are scanned for malware using ClamAV.</li>
              <li><strong>Backups:</strong> Regular encrypted backups with secure storage and retention policies.</li>
              <li><strong>Security Monitoring:</strong> Continuous monitoring for security threats and vulnerabilities.</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">5. Data Retention</h2>
            <p className="text-neutral-700 mb-4">
              We retain your personal data only for as long as necessary:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li><strong>Active Accounts:</strong> Data is retained while your account is active.</li>
              <li><strong>Inactive Accounts:</strong> Accounts inactive for 24 months may be deleted after notification.</li>
              <li><strong>Deleted Accounts:</strong> Data is permanently deleted within 90 days of account deletion, except where required by law.</li>
              <li><strong>Backups:</strong> Backup copies are retained for up to 90 days before permanent deletion.</li>
              <li><strong>Legal Requirements:</strong> Some data may be retained longer if required by law (e.g., tax records, payment history).</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">6. Your Privacy Rights</h2>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">6.1 GDPR Rights (European Users)</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li><strong>Right to Access:</strong> Request a copy of your personal data.</li>
              <li><strong>Right to Rectification:</strong> Correct inaccurate or incomplete data.</li>
              <li><strong>Right to Erasure:</strong> Request deletion of your data (&quot;right to be forgotten&quot;).</li>
              <li><strong>Right to Restrict Processing:</strong> Limit how we use your data.</li>
              <li><strong>Right to Data Portability:</strong> Receive your data in a structured, machine-readable format.</li>
              <li><strong>Right to Object:</strong> Object to processing based on legitimate interests.</li>
              <li><strong>Right to Withdraw Consent:</strong> Withdraw consent at any time where processing is based on consent.</li>
              <li><strong>Right to Lodge a Complaint:</strong> File a complaint with your local data protection authority.</li>
            </ul>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">6.2 CCPA Rights (California Residents)</h3>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2 mb-4">
              <li><strong>Right to Know:</strong> What personal information we collect, use, and disclose.</li>
              <li><strong>Right to Delete:</strong> Request deletion of your personal information.</li>
              <li><strong>Right to Opt-Out:</strong> Opt-out of the sale of personal information (we do not sell your data).</li>
              <li><strong>Right to Non-Discrimination:</strong> Equal service regardless of exercising privacy rights.</li>
            </ul>

            <h3 className="text-xl font-semibold text-neutral-900 mb-3">6.3 How to Exercise Your Rights</h3>
            <p className="text-neutral-700 mb-2">
              To exercise any of these rights, contact us at:{' '}
              <Link href="/contact" className="text-admin-primary hover:underline">privacy@bonidoc.com</Link>
            </p>
            <p className="text-neutral-700">
              We will respond to your request within 30 days (or as required by applicable law).
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">7. Cookies and Tracking Technologies</h2>
            <p className="text-neutral-700 mb-4">
              We use cookies and similar tracking technologies. For detailed information, please see our <Link href="/cookie-policy" className="text-admin-primary hover:underline">Cookie Policy</Link>.
            </p>
            <p className="text-neutral-700 mb-4">
              You can manage your cookie preferences through our cookie consent banner. Note that disabling necessary cookies may prevent you from using certain features of the Service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">8. International Data Transfers</h2>
            <p className="text-neutral-700 mb-4">
              Your data is primarily processed and stored within the European Union. When we transfer data outside the EU, we use appropriate safeguards:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>Standard Contractual Clauses approved by the European Commission</li>
              <li>Adequacy decisions where applicable</li>
              <li>Other legally approved transfer mechanisms</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">9. Children&apos;s Privacy</h2>
            <p className="text-neutral-700 mb-4">
              Our Service is not intended for children under 16 years of age (or under 13 in the United States). We do not knowingly collect personal information from children. If you are a parent or guardian and believe your child has provided us with personal information, please contact us immediately.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">10. Data Breach Notification</h2>
            <p className="text-neutral-700 mb-4">
              In the event of a data breach that poses a risk to your rights and freedoms, we will:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>Notify affected users within 72 hours of discovery (as required by GDPR)</li>
              <li>Notify relevant data protection authorities</li>
              <li>Provide information about the breach and steps taken to mitigate harm</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">11. Do Not Track Signals</h2>
            <p className="text-neutral-700 mb-4">
              Some browsers support &quot;Do Not Track&quot; (DNT) signals. Our Service respects these signals and will not track users who have DNT enabled.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">12. Changes to This Privacy Policy</h2>
            <p className="text-neutral-700 mb-4">
              We may update this Privacy Policy from time to time. When we make material changes, we will:
            </p>
            <ul className="list-disc pl-6 text-neutral-700 space-y-2">
              <li>Update the &quot;Last updated&quot; date at the top of this policy</li>
              <li>Notify you by email (for significant changes)</li>
              <li>Display a prominent notice on our Service</li>
              <li>Request renewed consent where required by law</li>
            </ul>
            <p className="text-neutral-700 mt-4">
              Your continued use of the Service after changes take effect constitutes acceptance of the updated policy.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">13. Contact Information</h2>
            <p className="text-neutral-700 mb-4">
              For questions, concerns, or requests regarding this Privacy Policy or our data practices, please contact:
            </p>
            <div className="bg-neutral-50 p-4 rounded">
              <p className="text-neutral-700 mb-2"><strong>Email:</strong>{' '}
                <Link href="/contact" className="text-admin-primary hover:underline">privacy@bonidoc.com</Link>
              </p>
              <p className="text-neutral-700 mb-2"><strong>Data Protection Officer:</strong> Available upon request</p>
              <p className="text-neutral-700"><strong>Response Time:</strong> Within 30 days</p>
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-bold text-neutral-900 mb-4">14. Supervisory Authority</h2>
            <p className="text-neutral-700 mb-4">
              If you are located in the European Union and have concerns about our data processing practices, you have the right to lodge a complaint with your local data protection authority.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
