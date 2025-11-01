// src/app/page.tsx
/**
 * Bonifatus DMS Landing Page
 * Professional document management system homepage
 */

'use client'

import Link from 'next/link'
import { GoogleLoginButton } from '@/components/GoogleLoginButton'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/contexts/auth-context'

export default function HomePage() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center">
              <div className="h-8 w-8 bg-admin-primary rounded-lg flex items-center justify-center">
                <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <span className="ml-3 text-xl font-bold text-neutral-900">Bonifatus DMS</span>
            </Link>

            <div className="hidden md:flex items-center space-x-8">
              <Link href="/" className="text-neutral-700 hover:text-admin-primary font-medium">Home</Link>
              <Link href="/about" className="text-neutral-600 hover:text-admin-primary">About</Link>
              <Link href="/features" className="text-neutral-600 hover:text-admin-primary">Features</Link>
              <Link href="/pricing" className="text-neutral-600 hover:text-admin-primary">Pricing</Link>
              <Link href="/contact" className="text-neutral-600 hover:text-admin-primary">Contact</Link>
              {user ? (
                <>
                  <Link href="/dashboard" className="text-neutral-600 hover:text-admin-primary">Dashboard</Link>
                  <Link href="/profile" className="text-neutral-600 hover:text-admin-primary">Profile</Link>
                </>
              ) : (
                <GoogleLoginButton size="sm">Sign In</GoogleLoginButton>
              )}
            </div>

            <div className="md:hidden">
              <button className="text-neutral-600 hover:text-neutral-900">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-neutral-50 to-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-5xl font-bold text-neutral-900 mb-6">
              Professional Document
              <span className="text-admin-primary block">Management System</span>
            </h1>
            <p className="text-xl text-neutral-600 mb-8 max-w-3xl mx-auto">
              Organize, secure, and access your documents with AI-powered categorization, 
              advanced search capabilities, and enterprise-grade security.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <GoogleLoginButton size="lg" className="min-w-[200px]">
                Start Free - 50 Pages/Month
              </GoogleLoginButton>
              <Link href="/pricing">
                <Button variant="secondary" size="lg" className="min-w-[200px]">
                  View Pricing
                  <svg className="ml-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-neutral-900 mb-4">
              Everything you need for document management
            </h2>
            <p className="text-lg text-neutral-600">
              Professional tools designed for modern businesses and individuals
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-6">
              <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <svg className="h-6 w-6 text-admin-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 mb-2">Smart Upload</h3>
              <p className="text-neutral-600">
                Drag & drop files with automatic categorization using AI technology. Supports all major file formats.
              </p>
            </div>

            <div className="text-center p-6">
              <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 mb-2">Advanced Search</h3>
              <p className="text-neutral-600">
                Find documents instantly with full-text search, metadata filtering, and intelligent suggestions.
              </p>
            </div>

            <div className="text-center p-6">
              <div className="h-12 w-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <svg className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 mb-2">Enterprise Security</h3>
              <p className="text-neutral-600">
                Bank-level encryption, secure cloud storage, and comprehensive access controls protect your data.
              </p>
            </div>

            <div className="text-center p-6">
              <div className="h-12 w-12 bg-orange-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <svg className="h-6 w-6 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 mb-2">Smart Organization</h3>
              <p className="text-neutral-600">
                AI-powered categorization automatically organizes documents into logical folders and tags.
              </p>
            </div>

            <div className="text-center p-6">
              <div className="h-12 w-12 bg-red-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 mb-2">Access Control</h3>
              <p className="text-neutral-600">
                Granular permissions and role-based access ensure the right people see the right documents.
              </p>
            </div>

            <div className="text-center p-6">
              <div className="h-12 w-12 bg-teal-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <svg className="h-6 w-6 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 mb-2">Analytics & Reports</h3>
              <p className="text-neutral-600">
                Comprehensive insights into document usage, storage trends, and team collaboration patterns.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20 bg-neutral-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-neutral-900 mb-4">
              Choose the right plan for you
            </h2>
            <p className="text-lg text-neutral-600">
              Start free, upgrade as you grow
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Free Tier */}
            <div className="bg-white rounded-xl border border-neutral-200 p-8">
              <div className="text-center mb-8">
                <h3 className="text-xl font-semibold text-neutral-900 mb-2">Free</h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold text-neutral-900">€0</span>
                  <span className="text-neutral-600">/month</span>
                </div>
                <p className="text-neutral-600">Perfect for trying it out</p>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700"><strong>50 pages/month</strong></span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Full AI features</span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Stored on your Google Drive</span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Solo user only</span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Community support</span>
                </li>
              </ul>
              <GoogleLoginButton className="w-full" variant="secondary">
                Start Free
              </GoogleLoginButton>
            </div>

            {/* Starter Tier */}
            <div className="bg-white rounded-xl border border-neutral-200 p-8">
              <div className="text-center mb-8">
                <h3 className="text-xl font-semibold text-neutral-900 mb-2">Starter</h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold text-neutral-900">€2.99</span>
                  <span className="text-neutral-600">/month</span>
                </div>
                <p className="text-neutral-600">For light personal use</p>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700"><strong>250 pages/month</strong></span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Full AI features</span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Stored on your Google Drive</span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Solo user only</span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Email support</span>
                </li>
              </ul>
              <GoogleLoginButton className="w-full" variant="secondary">
                Get Started
              </GoogleLoginButton>
            </div>

            {/* Professional Tier */}
            <div className="bg-white rounded-xl border-2 border-admin-primary p-8 relative">
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                <span className="bg-admin-primary text-white px-4 py-1 rounded-full text-sm font-medium">
                  Most Popular
                </span>
              </div>
              <div className="text-center mb-8">
                <h3 className="text-xl font-semibold text-neutral-900 mb-2">Professional</h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold text-neutral-900">€7.99</span>
                  <span className="text-neutral-600">/month</span>
                </div>
                <p className="text-neutral-600">For professionals & teams</p>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700"><strong>1,500 pages/month</strong></span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Full AI features</span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Stored on your Google Drive</span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700"><strong>+ Multi-user (3 delegates)</strong></span>
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-neutral-700">Priority support</span>
                </li>
              </ul>
              <GoogleLoginButton className="w-full">
                Get Started
              </GoogleLoginButton>
            </div>
          </div>

          <div className="mt-12 text-center">
            <p className="text-neutral-600 text-sm">
              <strong>Fair use policy:</strong> Consistent usage above 2x stated limits may require an upgrade.
              Documents stored on your own Google Drive - no storage limits from us!
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-admin-primary">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to transform your document management?
          </h2>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Start free with 50 pages/month. Upgrade anytime as you grow.
          </p>
          <GoogleLoginButton size="lg" className="bg-white text-admin-primary hover:bg-neutral-50">
            Get Started Free
          </GoogleLoginButton>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-neutral-900 text-neutral-300 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center mb-4">
                <div className="h-8 w-8 bg-admin-primary rounded-lg flex items-center justify-center">
                  <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <span className="ml-3 text-xl font-bold text-white">Bonifatus DMS</span>
              </div>
              <p className="text-neutral-400">
                Professional document management for modern businesses.
              </p>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-4">Product</h3>
              <ul className="space-y-2">
                <li><Link href="/features" className="hover:text-white transition-colors">Features</Link></li>
                <li><Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link></li>
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
                <li><Link href="/legal/gdpr" className="hover:text-white transition-colors">GDPR</Link></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-neutral-800 mt-12 pt-8 text-center">
            <p className="text-neutral-400">
              © 2024 Bonifatus DMS. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}