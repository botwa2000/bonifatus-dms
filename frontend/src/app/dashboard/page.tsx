// src/app/dashboard/page.tsx
/**
 * Main dashboard page for authenticated users
 * Shows document overview and quick actions
 */

'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import { apiClient } from '@/services/api-client'
import Link from 'next/link'
import AppHeader from '@/components/AppHeader'

interface Document {
  id: string
  title: string
  file_name: string
  file_size: number
  category_name?: string
  created_at: string
}

export default function DashboardPage() {
  const { user, isLoading, loadUser, logout } = useAuth()
  const router = useRouter()

  // ALL HOOKS MUST BE AT THE TOP - BEFORE ANY CONDITIONAL LOGIC
  const [recentDocuments, setRecentDocuments] = useState<Document[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(true)
  const [isProcessingTier, setIsProcessingTier] = useState(false)
  const [tierProcessed, setTierProcessed] = useState(false)

  // Load user data on mount (passive auth context requires explicit call)
  useEffect(() => {
    loadUser()
  }, [loadUser])

  // Check if user selected a paid tier before login and redirect to checkout
  useEffect(() => {
    const handleTierSelection = async () => {
      if (!user || tierProcessed || isProcessingTier) return

      // Get selected tier and billing cycle from sessionStorage
      const selectedTierId = sessionStorage.getItem('selected_tier_id')
      const selectedBillingCycle = sessionStorage.getItem('selected_billing_cycle')
      const referralCode = sessionStorage.getItem('referral_code')

      if (!selectedTierId) {
        setTierProcessed(true)
        return
      }

      const tierId = parseInt(selectedTierId, 10)

      // Clear the tier selection from sessionStorage (keep referral for future use)
      sessionStorage.removeItem('selected_tier_id')
      sessionStorage.removeItem('selected_billing_cycle')

      // If user selected free tier (id: 0), they're already on free tier
      if (tierId === 0) {
        setTierProcessed(true)
        return
      }

      // User selected a paid tier - initiate Stripe checkout
      setIsProcessingTier(true)

      try {
        // Create Stripe checkout session
        const checkoutResponse = await apiClient.post<{ checkout_url: string }>(
          '/api/v1/billing/subscriptions/create-checkout',
          {
            tier_id: tierId,
            billing_cycle: selectedBillingCycle || 'yearly',  // Default to yearly for better conversion
            referral_code: referralCode || undefined
          },
          true
        )

        // Redirect to Stripe checkout
        window.location.href = checkoutResponse.checkout_url

      } catch (error) {
        console.error('Failed to process tier selection:', error)
        setTierProcessed(true)
        setIsProcessingTier(false)
        // Continue to dashboard even if checkout fails
      }
    }

    if (user && !tierProcessed && !isProcessingTier) {
      handleTierSelection()
    }
  }, [user, tierProcessed, isProcessingTier])

  // Load recent documents
  useEffect(() => {
    const loadRecentDocuments = async () => {
      try {
        setDocumentsLoading(true)
        const response = await apiClient.get<{ documents: Document[] }>(
          '/api/v1/documents?page=1&page_size=5&sort_by=created_at&sort_order=desc',
          true
        )
        setRecentDocuments(response.documents || [])
      } catch (error) {
        // Silently handle - empty state will show
      } finally {
        setDocumentsLoading(false)
      }
    }

    if (user) {
      loadRecentDocuments()
    }
  }, [user])


  // Show loading state while user data loads or processing tier selection
  if (isLoading || !user || isProcessingTier) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">
            {isProcessingTier ? 'Setting up your subscription...' : 'Loading dashboard...'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      <AppHeader title="Dashboard" subtitle="Overview of your documents" />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-neutral-900 mb-2">
            Welcome back, {user.full_name?.split(' ')[0] || 'User'}!
          </h2>
          <p className="text-lg text-neutral-600">
            Manage your documents with professional-grade tools and AI-powered organization.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Link href="/documents/upload">
            <div className="bg-white rounded-lg border border-neutral-200 p-6 hover:border-admin-primary hover:shadow-md transition-all cursor-pointer">
              <div className="flex items-center space-x-4">
                <div className="h-12 w-12 bg-admin-primary rounded-lg flex items-center justify-center">
                  <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-neutral-900">Upload Documents</h3>
                  <p className="text-sm text-neutral-600">Add new files to your library</p>
                </div>
              </div>
            </div>
          </Link>

          <div className="bg-white rounded-lg border border-neutral-200 p-6 hover:shadow-md transition-shadow cursor-pointer">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-green-600 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-neutral-900">Search Documents</h3>
                <p className="text-sm text-neutral-600">Find files with AI-powered search</p>
              </div>
            </div>
          </div>

          <Link href="/categories">
            <div className="bg-white rounded-lg border border-neutral-200 p-6 hover:border-purple-500 hover:shadow-md transition-all cursor-pointer">
              <div className="flex items-center space-x-4">
                <div className="bg-purple-100 rounded-lg p-3">
                  <svg className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-neutral-900">Organize</h3>
                  <p className="text-sm text-neutral-600">Manage categories and tags</p>
                </div>
              </div>
            </div>
          </Link>
        </div>

        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Document Library */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-neutral-900">Recent Documents</h3>
                <Link href="/documents" className="text-admin-primary hover:underline text-sm font-medium">
                  View All
                </Link>
              </div>

              {documentsLoading ? (
                <div className="text-center py-12">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
                  <p className="mt-4 text-sm text-neutral-600">Loading documents...</p>
                </div>
              ) : recentDocuments.length > 0 ? (
                <div className="space-y-3">
                  {recentDocuments.map((doc) => (
                    <Link
                      key={doc.id}
                      href={`/documents/${doc.id}`}
                      className="block p-4 border border-neutral-200 rounded-lg hover:border-admin-primary hover:shadow-sm transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3 flex-1 min-w-0">
                          <svg className="h-8 w-8 text-blue-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-neutral-900 truncate">{doc.title || doc.file_name}</h4>
                            <div className="flex items-center space-x-2 text-sm text-neutral-600">
                              {doc.category_name && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                  {doc.category_name}
                                </span>
                              )}
                              <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                              <span>•</span>
                              <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                            </div>
                          </div>
                        </div>
                        <svg className="h-5 w-5 text-neutral-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <svg className="h-16 w-16 text-neutral-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <h4 className="text-lg font-medium text-neutral-900 mb-2">No documents yet</h4>
                  <p className="text-neutral-600 mb-4">Upload your first document to get started</p>
                  <Link href="/documents/upload">
                    <button className="bg-admin-primary text-white px-6 py-2 rounded-md hover:bg-blue-700 font-medium">
                      Upload Document
                    </button>
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Account Status */}
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <h4 className="font-semibold text-neutral-900 mb-4">Account Status</h4>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-neutral-600">Plan:</span>
                  <span className="font-medium text-neutral-900 capitalize">
                    {user.tier || 'Basic'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-600">Documents:</span>
                  <span className="font-medium text-neutral-900">{recentDocuments.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-600">Storage Used:</span>
                  <span className="font-medium text-neutral-900">
                    {(recentDocuments.reduce((sum, doc) => sum + doc.file_size, 0) / (1024 * 1024)).toFixed(2)} MB
                  </span>
                </div>
              </div>
              <Link href="/profile">
                <button className="w-full mt-4 bg-admin-primary text-white px-4 py-2 rounded-md hover:bg-blue-700 font-medium text-sm">
                  Manage Plan
                </button>
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}