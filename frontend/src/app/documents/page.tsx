// frontend/src/app/documents/page.tsx
'use client'

import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/auth-context'
import { useDelegate } from '@/contexts/delegate-context'
import { apiClient } from '@/services/api-client'
import { Button, Alert, Badge, SpinnerFullPage, SpinnerOverlay } from '@/components/ui'
import type { BadgeVariant } from '@/components/ui'
import AppHeader from '@/components/AppHeader'
import DocumentSourceFilter from '@/components/DocumentSourceFilter'
import { useEffect, useState, useCallback } from 'react'
import { logger } from '@/lib/logger'
interface Category {
  id: string
  name: string
  color_hex: string
}

interface CategoryInfo {
  id: string
  name: string
  is_primary: boolean
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
  categories?: CategoryInfo[]
  created_at: string
  updated_at: string
  // Owner metadata for multi-user delegate access
  owner_type?: 'own' | 'shared'
  owner_user_id?: string
  owner_name?: string
  can_edit?: boolean
  can_delete?: boolean
}

interface DocumentsResponse {
  documents: Document[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
}

type ViewMode = 'list' | 'grid'
type SortField = 'title' | 'created_at' | 'file_size' | 'category_name' | 'mime_type'
type SortDirection = 'asc' | 'desc'

export default function DocumentsPage() {
  const { isAuthenticated, isLoading: authLoading, hasAttemptedAuth, loadUser } = useAuth()
  const { isActingAsDelegate, actingAsUser, switchToAccount } = useDelegate()
  const router = useRouter()

  const [documents, setDocuments] = useState<Document[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [isInitialLoad, setIsInitialLoad] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchInput, setSearchInput] = useState('') // Immediate input state
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  // Document source filter state
  const [includeOwn, setIncludeOwn] = useState(true)
  const [sharedOwnerIds, setSharedOwnerIds] = useState<string[]>([])

  const [deletingDocument, setDeletingDocument] = useState<Document | null>(null)

  // Load user data on mount
  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    // Don't check auth until we've attempted to load the user
    if (!hasAttemptedAuth) {
      return
    }

    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, authLoading, hasAttemptedAuth, router])

  useEffect(() => {
    if (isAuthenticated) {
      loadCategories()
    }
  }, [isAuthenticated])

  // Debounce search input (wait 500ms after user stops typing)
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchQuery(searchInput)
      setCurrentPage(1)
    }, 500)

    return () => clearTimeout(timer)
  }, [searchInput])

  const loadCategories = async () => {
    try {
      const data = await apiClient.get<{ categories: Category[] }>('/api/v1/categories', true)
      setCategories(data.categories)
    } catch (err) {
      logger.error('Failed to load categories:', err)
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
        sort_order: sortDirection,
        include_own: includeOwn.toString()
      })

      if (searchQuery) params.append('query', searchQuery)
      if (selectedCategory) params.append('category_id', selectedCategory)
      if (sharedOwnerIds.length > 0) {
        params.append('include_shared', sharedOwnerIds.join(','))
      }

      const data = await apiClient.get<DocumentsResponse>(
        `/api/v1/documents?${params.toString()}`,
        true
      )

      setDocuments(data.documents)
      setTotalCount(data.total_count)
      setTotalPages(data.total_pages)
    } catch (err) {
      setError('Failed to load documents')
      logger.error('Load documents error:', err)
    } finally {
      setIsLoading(false)
      setIsInitialLoad(false)
    }
  }, [currentPage, searchQuery, selectedCategory, sortField, sortDirection, includeOwn, sharedOwnerIds])

  // Load documents when user is authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadDocuments()
    }
  }, [isAuthenticated, loadDocuments])

  const handleSearch = (query: string) => {
    setSearchInput(query) // Debounced via useEffect
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

  const handleFilterChange = (includeOwnDocs: boolean, selectedOwnerIds: string[]) => {
    setIncludeOwn(includeOwnDocs)
    setSharedOwnerIds(selectedOwnerIds)
    setCurrentPage(1) // Reset to page 1 when filter changes
  }

  const handleDelete = async (documentId: string) => {
    logger.debug('[DELETE DEBUG] === Frontend Delete Started ===')
    logger.debug('[DELETE DEBUG] Document ID:', documentId)
    logger.debug('[DELETE DEBUG] Document ID type:', typeof documentId)

    try {
      logger.debug('[DELETE DEBUG] Calling API delete endpoint:', `/api/v1/documents/${documentId}`)

      // Optimistic update: remove document from UI immediately
      setDocuments(prev => prev.filter(doc => doc.id !== documentId))
      setDeletingDocument(null)

      const response = await apiClient.delete(`/api/v1/documents/${documentId}`, true)
      logger.debug('[DELETE DEBUG] ✅ Delete API response:', response)

      // Reload to get accurate count and sync with server
      logger.debug('[DELETE DEBUG] Reloading documents list...')
      await loadDocuments()
      logger.debug('[DELETE DEBUG] ✅✅✅ Delete completed successfully')
    } catch (err) {
      logger.error('[DELETE DEBUG] ❌ Delete failed:', err)
      logger.error('[DELETE DEBUG] Error details:', JSON.stringify(err, null, 2))

      // Close modal on error to prevent double-delete attempts
      setDeletingDocument(null)

      // Reload documents to restore correct state after failed delete
      await loadDocuments()

      setError('Failed to delete document. It may have already been deleted.')
      logger.error('Delete error:', err)
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

  const getDocumentType = (mimeType: string, fileName: string) => {
    // Extract file extension from mime type or filename
    let type = 'FILE'

    if (mimeType.includes('pdf')) {
      type = 'PDF'
    } else if (mimeType.includes('image/jpeg') || mimeType.includes('image/jpg')) {
      type = 'JPG'
    } else if (mimeType.includes('image/png')) {
      type = 'PNG'
    } else if (mimeType.includes('image/gif')) {
      type = 'GIF'
    } else if (mimeType.includes('image/')) {
      type = 'IMAGE'
    } else if (mimeType.includes('word') || mimeType.includes('msword')) {
      type = 'DOC'
    } else if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) {
      type = 'XLS'
    } else if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) {
      type = 'PPT'
    } else if (mimeType.includes('text/plain')) {
      type = 'TXT'
    } else {
      // Fallback to file extension
      const ext = fileName.split('.').pop()?.toUpperCase()
      if (ext) type = ext
    }

    return (
      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200">
        {type}
      </span>
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

  if (authLoading || isInitialLoad) {
    return <SpinnerFullPage message="Loading documents..." />
  }

  const totalSize = documents.reduce((sum, doc) => sum + doc.file_size, 0)

  return (
    <div className="min-h-screen bg-neutral-50">
      <AppHeader title="Documents" subtitle="Manage your documents" />

      {/* Delegate Banner */}
      {isActingAsDelegate && actingAsUser && (
        <div className="bg-indigo-600 text-white">
          <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <div>
                  <span className="font-medium">Viewing {actingAsUser.owner_name}'s documents</span>
                  <span className="text-indigo-200 ml-2">({actingAsUser.role} access)</span>
                </div>
              </div>
              <button
                onClick={() => switchToAccount(null)}
                className="text-sm bg-white bg-opacity-20 hover:bg-opacity-30 px-3 py-1 rounded transition-colors"
              >
                Switch to My Account
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6">
            <Alert type="error" message={error} />
          </div>
        )}

        {/* Document Source Filter */}
        <DocumentSourceFilter onFilterChange={handleFilterChange} />

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

        <div className="bg-white rounded-lg border border-neutral-200 mb-6 relative">
          {isLoading && <SpinnerOverlay message="Updating..." />}

          <div className="px-6 py-4 border-b border-neutral-200">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
              <div className="flex-1 max-w-md relative">
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={searchInput}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 pr-10 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary dark:bg-neutral-800 dark:border-neutral-600 dark:text-neutral-100"
                />
                {searchInput && (
                  <button
                    onClick={() => handleSearch('')}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                    title="Clear search"
                    type="button"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
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
                  className={`border border-neutral-200 rounded-lg p-4 hover:border-admin-primary hover:shadow-md transition-all ${
                    doc.owner_type === 'shared' ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3 flex-1">
                      <div className="text-neutral-600">
                        {getFileIcon(doc.mime_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h3 className="font-medium text-neutral-900 truncate">{doc.title}</h3>
                          {doc.owner_type === 'own' && (
                            <svg className="h-4 w-4 text-neutral-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-label="My Document">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                            </svg>
                          )}
                          {doc.owner_type === 'shared' && (
                            <svg className="h-4 w-4 text-blue-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-label={`Shared by ${doc.owner_name}`}>
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                            </svg>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          <p className="text-xs text-neutral-500">{formatFileSize(doc.file_size)}</p>
                          {doc.owner_type === 'shared' && doc.owner_name && (
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                              {doc.owner_name}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {doc.description && (
                    <p className="text-sm text-neutral-600 mb-3 line-clamp-2">{doc.description}</p>
                  )}

                  <div className="flex items-center justify-between mb-3">
                    <div className="flex flex-wrap gap-1">
                      {doc.categories && doc.categories.length > 0 ? (
                        doc.categories.map((cat) => (
                          <span
                            key={cat.id}
                            className={`text-xs px-2 py-1 rounded ${
                              cat.is_primary
                                ? 'bg-admin-primary/10 text-admin-primary border border-admin-primary/20'
                                : 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200'
                            }`}
                          >
                            {cat.name}
                          </span>
                        ))
                      ) : doc.category_name ? (
                        <span className="text-xs px-2 py-1 rounded bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200">
                          {doc.category_name}
                        </span>
                      ) : null}
                    </div>
                    {getDocumentType(doc.mime_type, doc.file_name)}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-neutral-100">
                    <span className="text-xs text-neutral-500">{formatDate(doc.created_at)}</span>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${doc.id}/content`, '_blank')}
                        className="text-neutral-600 hover:text-admin-primary"
                        title="Preview"
                      >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => doc.can_edit !== false && router.push(`/documents/${doc.id}`)}
                        className={`${
                          doc.can_edit === false
                            ? 'text-neutral-300 cursor-not-allowed'
                            : 'text-neutral-600 hover:text-blue-600'
                        }`}
                        title={doc.can_edit === false ? 'Cannot edit shared documents' : 'Edit'}
                        disabled={doc.can_edit === false}
                      >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${doc.id}/download`, '_blank')}
                        className="text-neutral-600 hover:text-green-600"
                        title="Download"
                      >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                      </button>
                      <button
                        onClick={() => doc.can_delete !== false && setDeletingDocument(doc)}
                        className={`${
                          doc.can_delete === false
                            ? 'text-neutral-300 cursor-not-allowed'
                            : 'text-neutral-600 hover:text-red-600'
                        }`}
                        title={doc.can_delete === false ? 'Cannot delete shared documents' : 'Delete'}
                        disabled={doc.can_delete === false}
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
                      <button
                        onClick={() => handleSort('category_name')}
                        className="flex items-center space-x-1 hover:text-neutral-900"
                      >
                        <span>Category</span>
                        {sortField === 'category_name' && (
                          <svg className={`h-4 w-4 ${sortDirection === 'desc' ? 'transform rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                          </svg>
                        )}
                      </button>
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
                      <button
                        onClick={() => handleSort('mime_type')}
                        className="flex items-center space-x-1 hover:text-neutral-900"
                      >
                        <span>Type</span>
                        {sortField === 'mime_type' && (
                          <svg className={`h-4 w-4 ${sortDirection === 'desc' ? 'transform rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                          </svg>
                        )}
                      </button>
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
                    <tr
                      key={doc.id}
                      className={`hover:bg-neutral-50 transition-colors ${
                        doc.owner_type === 'shared' ? 'bg-blue-50' : ''
                      }`}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-3">
                          <div className="text-neutral-600">
                            {getFileIcon(doc.mime_type)}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center space-x-2">
                              <div className="font-medium text-neutral-900">{doc.title}</div>
                              {doc.owner_type === 'own' && (
                                <svg className="h-4 w-4 text-neutral-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-label="My Document">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                </svg>
                              )}
                              {doc.owner_type === 'shared' && (
                                <>
                                  <svg className="h-4 w-4 text-blue-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-label={`Shared by ${doc.owner_name}`}>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                                  </svg>
                                  {doc.owner_name && (
                                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                                      {doc.owner_name}
                                    </span>
                                  )}
                                </>
                              )}
                            </div>
                            <div className="text-sm text-neutral-500">{doc.file_name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {doc.categories && doc.categories.length > 0 ? (
                            doc.categories.map((cat) => (
                              <span
                                key={cat.id}
                                className={`text-sm px-2 py-1 rounded ${
                                  cat.is_primary
                                    ? 'bg-admin-primary/10 text-admin-primary border border-admin-primary/20'
                                    : 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200'
                                }`}
                              >
                                {cat.name}
                              </span>
                            ))
                          ) : doc.category_name ? (
                            <span className="text-sm px-2 py-1 rounded bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200">
                              {doc.category_name}
                            </span>
                          ) : (
                            <span className="text-sm text-neutral-400 dark:text-neutral-500">Uncategorized</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-600">
                        {formatFileSize(doc.file_size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getDocumentType(doc.mime_type, doc.file_name)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-600">
                        {formatDate(doc.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${doc.id}/content`, '_blank')}
                            className="text-neutral-600 hover:text-admin-primary"
                            title="Preview"
                          >
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => doc.can_edit !== false && router.push(`/documents/${doc.id}`)}
                            className={`${
                              doc.can_edit === false
                                ? 'text-neutral-300 cursor-not-allowed'
                                : 'text-neutral-600 hover:text-blue-600'
                            }`}
                            title={doc.can_edit === false ? 'Cannot edit shared documents' : 'Edit'}
                            disabled={doc.can_edit === false}
                          >
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${doc.id}/download`, '_blank')}
                            className="text-neutral-600 hover:text-green-600"
                            title="Download"
                          >
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                          </button>
                          <button
                            onClick={() => doc.can_delete !== false && setDeletingDocument(doc)}
                            className={`${
                              doc.can_delete === false
                                ? 'text-neutral-300 cursor-not-allowed'
                                : 'text-neutral-600 hover:text-red-600'
                            }`}
                            title={doc.can_delete === false ? 'Cannot delete shared documents' : 'Delete'}
                            disabled={doc.can_delete === false}
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