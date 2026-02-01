// frontend/src/app/features/page.tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function FeaturesPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900">
      {/* Header */}
      <header className="bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <Link href="/" className="text-2xl font-bold text-admin-primary">
              Bonifatus DMS
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex gap-6">
              <Link href="/pricing" className="text-neutral-600 dark:text-neutral-400 hover:text-admin-primary dark:hover:text-admin-primary">
                Pricing
              </Link>
              <Link href="/login" className="text-neutral-600 dark:text-neutral-400 hover:text-admin-primary dark:hover:text-admin-primary">
                Sign In
              </Link>
            </nav>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden text-neutral-600 dark:text-white hover:text-neutral-900 dark:hover:text-neutral-300 p-2 focus:outline-none focus:ring-2 focus:ring-admin-primary rounded-md"
              aria-label="Toggle mobile menu"
              type="button"
            >
              {mobileMenuOpen ? (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>

          {/* Mobile Menu */}
          {mobileMenuOpen && (
            <div className="md:hidden border-t border-neutral-200 dark:border-neutral-800 mt-4 pt-4">
              <nav className="flex flex-col space-y-2">
                <Link
                  href="/pricing"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-md text-base font-medium text-neutral-600 dark:text-neutral-400 hover:text-admin-primary dark:hover:text-admin-primary hover:bg-neutral-50 dark:hover:bg-neutral-800"
                >
                  Pricing
                </Link>
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-md text-base font-medium text-neutral-600 dark:text-neutral-400 hover:text-admin-primary dark:hover:text-admin-primary hover:bg-neutral-50 dark:hover:bg-neutral-800"
                >
                  Sign In
                </Link>
              </nav>
            </div>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-admin-primary to-admin-secondary text-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl font-bold mb-6">Powerful Features for Modern Document Management</h1>
          <p className="text-xl text-white/90 max-w-3xl mx-auto">
            AI-powered organization, intelligent search, and seamless cloud storage integration
          </p>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">

            {/* AI-Powered Categorization */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
              <div className="w-12 h-12 bg-admin-primary/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">AI-Powered Categorization</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Automatically categorize documents using advanced machine learning. The system learns from your corrections to improve accuracy over time.
              </p>
            </div>

            {/* OCR & Text Extraction */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
              <div className="w-12 h-12 bg-admin-primary/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">OCR & Text Extraction</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Extract text from scanned documents and images with Google Vision API. Make all your documents searchable, even handwritten notes.
              </p>
            </div>

            {/* Intelligent Search */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
              <div className="w-12 h-12 bg-admin-primary/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Intelligent Search</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Full-text search across all documents. Filter by category, date, language, or custom keywords to find exactly what you need instantly.
              </p>
            </div>

            {/* Google Drive Integration */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
              <div className="w-12 h-12 bg-admin-primary/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Google Drive Storage</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Documents stored securely on your own Google Drive. You maintain full ownership and control. No storage limits from us!
              </p>
            </div>

            {/* Multi-Language Support */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
              <div className="w-12 h-12 bg-admin-primary/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Multi-Language Support</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Support for English, German, Dutch, and more. Automatic language detection and categorization in multiple languages.
              </p>
            </div>

            {/* Standardized Naming */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
              <div className="w-12 h-12 bg-admin-primary/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Standardized File Naming</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Automatic file renaming with date, category code, and original name. Keep your documents organized with consistent naming conventions.
              </p>
            </div>

            {/* Duplicate Detection */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
              <div className="w-12 h-12 bg-admin-primary/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Duplicate Detection</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                SHA-256 hash-based duplicate detection prevents uploading the same document twice. Save storage and avoid confusion.
              </p>
            </div>

            {/* Audit Trail */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
              <div className="w-12 h-12 bg-admin-primary/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Complete Audit Trail</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Track every action with comprehensive audit logs. Know who uploaded, modified, or deleted documents and when.
              </p>
            </div>

            {/* Multi-User Access */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-neutral-200">
              <div className="w-12 h-12 bg-admin-primary/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-admin-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-neutral-900 dark:text-white mb-3">Multi-User Access (Pro)</h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Share access with up to 3 delegates on the Professional plan. Collaborate with your team while maintaining security.
              </p>
            </div>

          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-admin-primary text-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
          <p className="text-xl text-white/90 mb-8">
            Start with 20 pages free. No credit card required.
          </p>
          <Link
            href="/login"
            className="inline-block bg-white text-admin-primary px-8 py-3 rounded-lg font-semibold hover:bg-neutral-100 transition-colors"
          >
            Sign Up Now
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-neutral-900 text-neutral-400 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p>&copy; 2025 Bonifatus DMS. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
