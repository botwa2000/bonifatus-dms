// src/app/dashboard/page.tsx
/**
 * Main dashboard page for authenticated users
 * Shows document overview and quick actions
 */

'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useAuth } from '@/contexts/auth-context'
import { apiClient } from '@/services/api-client'
import Link from 'next/link'

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
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Load user data on mount (passive auth context requires explicit call)
  useEffect(() => {
    loadUser()
  }, [loadUser])

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

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Show loading state while user data loads
  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  const handleLogout = async () => {
    await logout()
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
              {/* User Menu */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setShowDropdown(!showDropdown)}
                  className="flex items-center space-x-3 px-3 py-2 rounded-md hover:bg-neutral-100 transition-colors"
                >
                  <div className="text-right">
                    <p className="text-sm font-medium text-neutral-900">{user.full_name}</p>
                    <p className="text-xs text-neutral-600">{user.email}</p>
                  </div>
                  <div className="h-8 w-8 rounded-full bg-admin-primary flex items-center justify-center text-white font-medium">
                    {user.full_name?.charAt(0) || 'U'}
                  </div>
                  <svg
                    className={`h-4 w-4 text-neutral-600 transition-transform ${showDropdown ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Dropdown Menu */}
                {showDropdown && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-neutral-200 py-1 z-50">
                    <button
                      onClick={() => {
                        setShowDropdown(false)
                        router.push('/settings')
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100 flex items-center space-x-2"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <span>Settings</span>
                    </button>
                    <button
                      onClick={() => {
                        setShowDropdown(false)
                        router.push('/profile')
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100 flex items-center space-x-2"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                      <span>Profile</span>
                    </button>
                    <hr className="my-1 border-neutral-200" />
                    <button
                      onClick={() => {
                        setShowDropdown(false)
                        handleLogout()
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                      <span>Sign Out</span>
                    </button>
                  </div>
                )}
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