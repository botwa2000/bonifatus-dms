// src/app/dashboard/page.tsx
/**
 * Main dashboard page for authenticated users
 * Shows trial status and document management interface
 */

'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useAuth } from '@/hooks/use-auth'
import { authService } from '@/services/auth.service'

export default function DashboardPage() {
  const { isAuthenticated, user, isLoading, logout } = useAuth()
  const router = useRouter()
  
  // ALL HOOKS MUST BE AT THE TOP - BEFORE ANY CONDITIONAL LOGIC
  const [trialInfo, setTrialInfo] = useState<{ days_remaining: number; expires_at: string; features: string[] } | null>(null)
  
  // Redirect unauthenticated users to login
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  // Load trial info asynchronously
  useEffect(() => {
    const loadTrialInfo = async () => {
      try {
        const info = await authService.getTrialInfo()
        setTrialInfo(info)
      } catch (error) {
        console.error('Failed to load trial info:', error)
      }
    }
    
    if (isAuthenticated) {
      loadTrialInfo()
    }
  }, [isAuthenticated])

  const isTrialActive = authService.isTrialActive()

  // CONDITIONAL RETURNS COME AFTER ALL HOOKS
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    return null // Will redirect to login
  }

  const handleLogout = async () => {
    await logout()
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-neutral-200">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="relative h-8 w-8">
                <Image
                  src="/favicon.ico"
                  alt="Bonifatus DMS"
                  fill
                  className="object-contain"
                />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">
                  Bonifatus DMS
                </h1>
                <p className="text-sm text-neutral-600">Document Management System</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Trial Status */}
              {isTrialActive && trialInfo && (
                <div className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
                  Premium Trial: {String(trialInfo.days_remaining)} days left
                </div>
              )}
              
              {/* User Menu */}
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <p className="text-sm font-medium text-neutral-900">{user.full_name}</p>
                  <p className="text-xs text-neutral-600">{user.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="text-sm text-neutral-600 hover:text-neutral-900 px-3 py-1 rounded-md border border-neutral-300 hover:bg-neutral-50"
                >
                  Sign Out
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

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

        {/* Trial Banner */}
        {isTrialActive && trialInfo && (
          <div className="mb-8 rounded-lg bg-gradient-to-r from-green-50 to-blue-50 p-6 border border-green-200">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold text-green-900 mb-2">
                  Welcome to your Premium Trial!
                </h3>
                <p className="text-green-700 mb-4">
                  You have <strong>{String(trialInfo.days_remaining)} days remaining</strong> of premium features including 
                  unlimited documents, AI-powered search, and priority support.
                </p>
                <div className="flex space-x-3">
                  <button className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 text-sm font-medium">
                    Explore Premium Features
                  </button>
                  <button className="bg-white text-green-700 px-4 py-2 rounded-md border border-green-300 hover:bg-green-50 text-sm font-medium">
                    Upgrade Now
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg border border-neutral-200 p-6 hover:shadow-md transition-shadow cursor-pointer">
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

          <div className="bg-white rounded-lg border border-neutral-200 p-6 hover:shadow-md transition-shadow cursor-pointer">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-purple-600 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-neutral-900">Organize</h3>
                <p className="text-sm text-neutral-600">Manage categories and tags</p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Document Library */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-neutral-900">Recent Documents</h3>
                <button className="text-admin-primary hover:underline text-sm font-medium">
                  View All
                </button>
              </div>
              
              <div className="text-center py-12">
                <svg className="h-16 w-16 text-neutral-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h4 className="text-lg font-medium text-neutral-900 mb-2">No documents yet</h4>
                <p className="text-neutral-600 mb-4">Upload your first document to get started</p>
                <button className="bg-admin-primary text-white px-6 py-2 rounded-md hover:bg-blue-700 font-medium">
                  Upload Document
                </button>
              </div>
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
                  <span className="font-medium text-neutral-900">
                    {isTrialActive ? 'Premium Trial' : user.tier || 'Free'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-600">Documents:</span>
                  <span className="font-medium text-neutral-900">0 / {isTrialActive ? '∞' : '100'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-600">Storage:</span>
                  <span className="font-medium text-neutral-900">0 MB / {isTrialActive ? '100 GB' : '1 GB'}</span>
                </div>
              </div>
            </div>

            {/* Quick Links */}
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <h4 className="font-semibold text-neutral-900 mb-4">Quick Links</h4>
              <div className="space-y-2">
                <a href="#" className="block text-admin-primary hover:underline text-sm">
                  Account Settings
                </a>
                <a href="#" className="block text-admin-primary hover:underline text-sm">
                  Billing & Plans
                </a>
                <a href="#" className="block text-admin-primary hover:underline text-sm">
                  Help & Support
                </a>
                <a href="#" className="block text-admin-primary hover:underline text-sm">
                  API Documentation
                </a>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}