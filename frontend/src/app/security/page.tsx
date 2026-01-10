// frontend/src/app/security/page.tsx

import Link from 'next/link'

export default function SecurityPage() {
  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <Link href="/" className="text-2xl font-bold text-admin-primary">
            Bonifatus DMS
          </Link>
          <nav className="flex gap-6">
            <Link href="/features" className="text-neutral-600 hover:text-admin-primary">
              Features
            </Link>
            <Link href="/pricing" className="text-neutral-600 hover:text-admin-primary">
              Pricing
            </Link>
            <Link href="/login" className="text-neutral-600 hover:text-admin-primary">
              Sign In
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-admin-primary to-admin-secondary text-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl font-bold mb-6">Enterprise-Grade Security</h1>
          <p className="text-xl text-white/90 max-w-3xl mx-auto">
            Your documents are protected by industry-leading security practices and encryption standards
          </p>
        </div>
      </section>

      {/* Security Features */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

          {/* Data Storage & Ownership */}
          <div className="mb-16">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-neutral-900 dark:text-white mb-4">Your Data, Your Control</h2>
              <p className="text-lg text-neutral-600 max-w-2xl mx-auto">
                Unlike traditional DMS solutions, we store your documents on YOUR Google Drive.
                You maintain complete ownership and control.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-semantic-success-bg-strong dark:bg-green-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-admin-success dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Your Google Drive</h3>
                <p className="text-neutral-600">
                  Documents stored on your own Google Drive account. We never store your files on our servers.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-semantic-success-bg-strong dark:bg-green-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-admin-success dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Full Ownership</h3>
                <p className="text-neutral-600">
                  You own your data. Delete your account anytime and your documents remain safely in your Google Drive.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-semantic-success-bg-strong dark:bg-green-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-admin-success dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Encrypted Tokens</h3>
                <p className="text-neutral-600">
                  Your Google Drive access tokens are encrypted using Fernet encryption (AES-128) before storage.
                </p>
              </div>
            </div>
          </div>

          {/* Authentication & Access Control */}
          <div className="mb-16">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-neutral-900 dark:text-white mb-4">Secure Authentication</h2>
              <p className="text-lg text-neutral-600 max-w-2xl mx-auto">
                Industry-standard OAuth 2.0 authentication with Google ensures your account is protected
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-semantic-info-bg-strong dark:bg-blue-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-admin-primary dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">OAuth 2.0 Authentication</h3>
                <p className="text-neutral-600">
                  Secure login through Google OAuth 2.0. We never see or store your Google password.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-semantic-info-bg-strong dark:bg-blue-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-admin-primary dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Session Management</h3>
                <p className="text-neutral-600">
                  Secure session tokens with automatic expiration. Sessions are invalidated on logout.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-semantic-info-bg-strong dark:bg-blue-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-admin-primary dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Role-Based Access Control</h3>
                <p className="text-neutral-600">
                  Multi-user plans include granular permission controls for team collaboration.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-semantic-info-bg-strong dark:bg-blue-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-admin-primary dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Complete Audit Logs</h3>
                <p className="text-neutral-600">
                  Every action is logged with timestamp, user, and IP address for full traceability.
                </p>
              </div>
            </div>
          </div>

          {/* Data Protection */}
          <div className="mb-16">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-neutral-900 dark:text-white mb-4">Data Protection & Privacy</h2>
              <p className="text-lg text-neutral-600 max-w-2xl mx-auto">
                We take data protection seriously and comply with international privacy regulations
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-purple-600 dark:text-purple-400 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">HTTPS Everywhere</h3>
                <p className="text-neutral-600">
                  All communication between your browser and our servers is encrypted with TLS 1.3.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-purple-600 dark:text-purple-400 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Minimal Data Collection</h3>
                <p className="text-neutral-600">
                  We only collect essential data needed for service operation. No selling or sharing with third parties.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-purple-600 dark:text-purple-400 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">GDPR Compliant</h3>
                <p className="text-neutral-600">
                  Full compliance with GDPR regulations. Right to access, export, and delete your data anytime.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-purple-600 dark:text-purple-400 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Regular Backups</h3>
                <p className="text-neutral-600">
                  Database backups every 24 hours. Your documents are already backed up by Google Drive.
                </p>
              </div>
            </div>
          </div>

          {/* Infrastructure Security */}
          <div>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-neutral-900 dark:text-white mb-4">Infrastructure Security</h2>
              <p className="text-lg text-neutral-600 max-w-2xl mx-auto">
                Built on secure, reliable infrastructure with industry best practices
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Docker Containerization</h3>
                <p className="text-neutral-600">
                  Application runs in isolated Docker containers for enhanced security and reliability.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">PostgreSQL Database</h3>
                <p className="text-neutral-600">
                  Enterprise-grade PostgreSQL database with encrypted connections and access controls.
                </p>
              </div>

              <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Regular Updates</h3>
                <p className="text-neutral-600">
                  System dependencies and security patches applied regularly to protect against vulnerabilities.
                </p>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* Security Commitment */}
      <section className="bg-neutral-900 text-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold mb-4">Our Security Commitment</h2>
          <p className="text-lg text-neutral-300 mb-6">
            We are committed to maintaining the highest security standards to protect your documents.
            If you have security questions or concerns, please contact us at security@bonidoc.com.
          </p>
          <div className="flex gap-4 justify-center">
            <Link
              href="/contact"
              className="inline-block bg-white text-neutral-900 dark:text-white px-6 py-3 rounded-lg font-semibold hover:bg-neutral-100 transition-colors"
            >
              Contact Security Team
            </Link>
            <Link
              href="/login"
              className="inline-block bg-admin-primary text-white px-6 py-3 rounded-lg font-semibold hover:bg-admin-secondary transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-neutral-900 text-neutral-400 py-8 border-t border-neutral-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p>&copy; 2025 Bonifatus DMS. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
