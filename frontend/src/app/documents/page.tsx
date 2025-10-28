// frontend/src/app/documents/page.tsx
'use client'

import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/auth-context'
import { apiClient } from '@/services/api-client'
import { Button, Alert, Badge } from '@/components/ui'
import type { BadgeVariant } from '@/components/ui'
import AppHeader from '@/components/AppHeader'
import { useEffect, useState, useCallback } from 'react'

interface Category {
  id: string
  name: string
  color_hex: string
}

interface Document {
  id: string
  title: string
  description?: string
  file_name: string
  file_size: number
  mime_type: string
  processing_status: string
  category_id?: string
  category_name?: string
  created_at: string
  updated_at: string
}

interface DocumentsResponse {
  documents: Document[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
}

type ViewMode = 'list' | 'grid'
type SortField = 'title' | 'created_at' | 'file_size'
type SortDirection = 'asc' | 'desc'

export default function DocumentsPage() {
  const { isAuthenticated, isLoading: authLoading, loadUser } = useAuth()
  const router = useRouter()

  const [documents, setDocuments] = useState<Document[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const [deletingDocument, setDeletingDocument] = useState<Document | null>(null)

  // Load user data on mount
  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, authLoading, router])

  useEffect(() => {
    if (isAuthenticated) {
      loadCategories()
      loadDocuments()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, currentPage, searchQuery, selectedCategory, sortField, sortDirection])

  const loadCategories = async () => {
    try {
      const data = await apiClient.get<{ categories: Category[] }>('/api/v1/categories', true)
      setCategories(data.categories)
    } catch (err) {
      console.error('Failed to load categories:', err)
    }
  }

  const loadDocuments = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: '12',
        sort_by: sortField,
        sort_order: sortDirection
      })
      
      if (searchQuery) params.append('query', searchQuery)
      if (selectedCategory) params.append('category_id', selectedCategory)
      
      const data = await apiClient.get<DocumentsResponse>(
        `/api/v1/documents?${params.toString()}`,
        true
      )
      
      setDocuments(data.documents)
      setTotalCount(data.total_count)
      setTotalPages(data.total_pages)
    } catch (err) {
      setError('Failed to load documents')
      console.error('Load documents error:', err)
    } finally {
      setIsLoading(false)
    }
  }, [currentPage, searchQuery, selectedCategory, sortField, sortDirection])

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    setCurrentPage(1)
  }

  const handleCategoryFilter = (categoryId: string) => {
    setSelectedCategory(categoryId)
    setCurrentPage(1)
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
    setCurrentPage(1)
  }

  const handleDelete = async (documentId: string) => {
    try {
      await apiClient.delete(`/api/v1/documents/${documentId}`, true)
      setDeletingDocument(null)
      loadDocuments()
    } catch (err) {
      setError('Failed to delete document')
      console.error('Delete error:', err)
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }).format(date)
  }

  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes('pdf')) {
      return (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      )
    }
    if (mimeType.includes('image')) {
      return (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      )
    }
    return (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    )
  }

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; variant: BadgeVariant }> = {
      uploaded: { label: 'Uploaded', variant: 'success' },
      processing: { label: 'Processing', variant: 'warning' },
      completed: { label: 'Ready', variant: 'success' },
      failed: { label: 'Failed', variant: 'error' }
    }
    const config = statusConfig[status] || statusConfig.uploaded
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const ViewModeToggle = () => (
    <div className="flex items-center space-x-2">
      <button
        onClick={() => setViewMode('list')}
        className={`p-2 rounded ${viewMode === 'list' ? 'bg-neutral-100 text-admin-primary' : 'text-neutral-400 hover:text-neutral-600'}`}
        title="List view"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
      <button
        onClick={() => setViewMode('grid')}
        className={`p-2 rounded ${viewMode === 'grid' ? 'bg-neutral-100 text-admin-primary' : 'text-neutral-400 hover:text-neutral-600'}`}
        title="Grid view"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      </button>
    </div>
  )

  const StatsCard = ({ label, value, color, icon }: { label: string; value: string | number; color: string; icon: React.ReactNode }) => (
    <div className="bg-white rounded-lg border border-neutral-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-neutral-600">{label}</p>
          <p className="text-2xl font-bold text-neutral-900 mt-1">{value}</p>
        </div>
        <div className={`${color} p-3 rounded-lg`}>
          {icon}
        </div>
      </div>
    </div>
  )

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Loading documents...</p>
        </div>
      </div>
    )
  }

  const totalSize = documents.reduce((sum, doc) => sum + doc.file_size, 0)

  return (
    <div className="min-h-screen bg-neutral-50">
      <AppHeader title="Documents" subtitle="Manage your documents" />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6">
            <Alert type="error" message={error} />
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatsCard
            label="Total Documents"
            value={totalCount}
            color="bg-blue-100"
            icon={
              <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
          />
          
          <StatsCard
            label="Total Size"
            value={formatFileSize(totalSize)}
            color="bg-purple-100"
            icon={
              <svg className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
            }
          />
          
          <StatsCard
            label="Categories"
            value={categories.length}
            color="bg-green-100"
            icon={
              <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            }
          />
        </div>

        <div className="bg-white rounded-lg border border-neutral-200 mb-6">
          <div className="px-6 py-4 border-b border-neutral-200">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
              <div className="flex-1 max-w-md">
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
                />
              </div>
              
              <div className="flex items-center space-x-3">
                <select
                  value={selectedCategory}
                  onChange={(e) => handleCategoryFilter(e.target.value)}
                  className="rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
                >
                  <option value="">All Categories</option>
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
                
                <ViewModeToggle />
              </div>
            </div>
          </div>

          {documents.length === 0 ? (
            <div className="text-center py-12">
              <svg className="h-16 w-16 text-neutral-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-lg font-medium text-neutral-900 mb-2">No documents yet</h3>
              <p className="text-neutral-600 mb-4">Upload your first document to get started</p>
              <Link href="/documents/upload">
                <Button>Upload Document</Button>
              </Link>
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="border border-neutral-200 rounded-lg p-4 hover:border-admin-primary hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className="text-neutral-600">
                        {getFileIcon(doc.mime_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-neutral-900 truncate">{doc.title}</h3>
                        <p className="text-xs text-neutral-500">{formatFileSize(doc.file_size)}</p>
                      </div>
                    </div>
                  </div>

                  {doc.description && (
                    <p className="text-sm text-neutral-600 mb-3 line-clamp-2">{doc.description}</p>
                  )}

                  <div className="flex items-center justify-between mb-3">
                    {doc.category_name && (
                      <span className="text-xs px-2 py-1 rounded bg-neutral-100 text-neutral-700">
                        {doc.category_name}
                      </span>
                    )}
                    {getStatusBadge(doc.processing_status)}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-neutral-100">
                    <span className="text-xs text-neutral-500">{formatDate(doc.created_at)}</span>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${doc.id}/download`, '_blank')}
                        className="text-neutral-600 hover:text-admin-primary"
                        title="Download"
                      >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                      </button>
                      <button
                        onClick={() => setDeletingDocument(doc)}
                        className="text-neutral-600 hover:text-red-600"
                        title="Delete"
                      >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-neutral-200">
                <thead className="bg-neutral-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-600 uppercase tracking-wider">
                      <button
                        onClick={() => handleSort('title')}
                        className="flex items-center space-x-1 hover:text-neutral-900"
                      >
                        <span>Document</span>
                        {sortField === 'title' && (
                          <svg className={`h-4 w-4 ${sortDirection === 'desc' ? 'transform rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                          </svg>
                        )}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-600 uppercase tracking-wider">
                      Category
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-600 uppercase tracking-wider">
                      <button
                        onClick={() => handleSort('file_size')}
                        className="flex items-center space-x-1 hover:text-neutral-900"
                      >
                        <span>Size</span>
                        {sortField === 'file_size' && (
                          <svg className={`h-4 w-4 ${sortDirection === 'desc' ? 'transform rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                          </svg>
                        )}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-600 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-600 uppercase tracking-wider">
                      <button
                        onClick={() => handleSort('created_at')}
                        className="flex items-center space-x-1 hover:text-neutral-900"
                      >
                        <span>Date</span>
                        {sortField === 'created_at' && (
                          <svg className={`h-4 w-4 ${sortDirection === 'desc' ? 'transform rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                          </svg>
                        )}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-neutral-600 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-neutral-200">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-neutral-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-3">
                          <div className="text-neutral-600">
                            {getFileIcon(doc.mime_type)}
                          </div>
                          <div>
                            <div className="font-medium text-neutral-900">{doc.title}</div>
                            <div className="text-sm text-neutral-500">{doc.file_name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {doc.category_name ? (
                          <span className="text-sm px-2 py-1 rounded bg-neutral-100 text-neutral-700">
                            {doc.category_name}
                          </span>
                        ) : (
                          <span className="text-sm text-neutral-400">Uncategorized</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-600">
                        {formatFileSize(doc.file_size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(doc.processing_status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-600">
                        {formatDate(doc.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${doc.id}/download`, '_blank')}
                            className="text-neutral-600 hover:text-admin-primary"
                            title="Download"
                          >
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                          </button>
                          <button
                            onClick={() => setDeletingDocument(doc)}
                            className="text-neutral-600 hover:text-red-600"
                            title="Delete"
                          >
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between">
              <div className="text-sm text-neutral-600">
                Showing {((currentPage - 1) * 12) + 1} to {Math.min(currentPage * 12, totalCount)} of {totalCount} documents
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 rounded border border-neutral-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-neutral-50"
                >
                  Previous
                </button>
                <span className="text-sm text-neutral-600">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 rounded border border-neutral-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-neutral-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {deletingDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">Delete Document</h3>
            <p className="text-sm text-neutral-600 mb-4">
              Are you sure you want to delete &quot;{deletingDocument.title}&quot;? This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <Button variant="secondary" onClick={() => setDeletingDocument(null)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={() => handleDelete(deletingDocument.id)}>
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}