// frontend/src/app/documents/[id]/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/auth-context'
import { apiClient } from '@/services/api-client'
import AppHeader from '@/components/AppHeader'
import { Badge, Button, Alert } from '@/components/ui'
import type { BadgeVariant } from '@/components/ui'

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
  document_date?: string
  keywords?: Array<{ keyword: string; relevance: number }>
}

export default function DocumentDetailPage() {
  const { isAuthenticated, isLoading: authLoading, loadUser } = useAuth()
  const router = useRouter()
  const params = useParams()
  const documentId = params.id as string

  const [document, setDocument] = useState<Document | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Editing states
  const [isEditingCategory, setIsEditingCategory] = useState(false)
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>('')
  const [isEditingKeywords, setIsEditingKeywords] = useState(false)
  const [editedKeywords, setEditedKeywords] = useState<string[]>([])
  const [newKeyword, setNewKeyword] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [deletingDocument, setDeletingDocument] = useState(false)

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, authLoading, router])

  useEffect(() => {
    if (isAuthenticated && documentId) {
      loadDocument()
      loadCategories()
    }
  }, [isAuthenticated, documentId])

  const loadDocument = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const data = await apiClient.get<Document>(
        `/api/v1/documents/${documentId}`,
        true
      )

      console.log('[DOCUMENT DETAIL] Loaded document:', data)
      console.log('[DOCUMENT DETAIL] category_id:', data.category_id)
      console.log('[DOCUMENT DETAIL] category_name:', data.category_name)

      setDocument(data)
      setSelectedCategoryId(data.category_id || '')
      setEditedKeywords(data.keywords?.map(k => k.keyword) || [])
    } catch (err) {
      setError('Failed to load document')
      console.error('Load document error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const loadCategories = async () => {
    try {
      const data = await apiClient.get<{ categories: Category[] }>('/api/v1/categories', true)
      setCategories(data.categories)
    } catch (err) {
      console.error('Failed to load categories:', err)
    }
  }

  const handleSaveCategory = async () => {
    if (!document) return

    try {
      setIsSaving(true)
      setError(null)

      await apiClient.put(
        `/api/v1/documents/${documentId}`,
        { category_id: selectedCategoryId },
        true
      )

      setSuccess('Category updated successfully')
      setIsEditingCategory(false)
      await loadDocument()
    } catch (err) {
      setError('Failed to update category')
      console.error(err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveKeywords = async () => {
    if (!document) return

    try {
      setIsSaving(true)
      setError(null)

      await apiClient.put(
        `/api/v1/documents/${documentId}`,
        { keywords: editedKeywords },
        true
      )

      setSuccess('Keywords updated successfully')
      setIsEditingKeywords(false)
      await loadDocument()
    } catch (err) {
      setError('Failed to update keywords')
      console.error(err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleAddKeyword = () => {
    if (newKeyword.trim() && !editedKeywords.includes(newKeyword.trim())) {
      setEditedKeywords([...editedKeywords, newKeyword.trim()])
      setNewKeyword('')
    }
  }

  const handleRemoveKeyword = (keyword: string) => {
    setEditedKeywords(editedKeywords.filter(k => k !== keyword))
  }

  const handleDeleteDocument = async () => {
    if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      return
    }

    try {
      setDeletingDocument(true)
      await apiClient.delete(`/api/v1/documents/${documentId}`, true)
      router.push('/documents')
    } catch (err) {
      setError('Failed to delete document')
      console.error(err)
      setDeletingDocument(false)
    }
  }

  const getStatusBadgeVariant = (status: string): BadgeVariant => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'processing':
        return 'warning'
      case 'failed':
        return 'error'
      default:
        return 'default'
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
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 dark:bg-neutral-900">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">Loading document...</p>
        </div>
      </div>
    )
  }

  if (error && !document) {
    return (
      <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900">
        <AppHeader title="Document" />
        <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-800">{error}</p>
            <Link href="/documents">
              <button className="mt-4 text-admin-primary hover:underline">
                Back to Documents
              </button>
            </Link>
          </div>
        </main>
      </div>
    )
  }

  if (!document) {
    return null
  }

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900">
      <AppHeader title={document.title} />

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6">
          <Link href="/documents" className="text-admin-primary hover:underline text-sm font-medium">
            ← Back to Documents
          </Link>
        </div>

        {error && (
          <div className="mb-6">
            <Alert type="error" message={error} />
          </div>
        )}

        {success && (
          <div className="mb-6">
            <Alert type="success" message={success} />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Document Info */}
            <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
                    {document.title}
                  </h1>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">{document.file_name}</p>
                </div>
                <Badge variant={getStatusBadgeVariant(document.processing_status)}>
                  {document.processing_status}
                </Badge>
              </div>

              {document.description && (
                <div className="mb-4">
                  <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">Description</h2>
                  <p className="text-neutral-900 dark:text-neutral-100">{document.description}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-neutral-600 dark:text-neutral-400">File Size:</span>
                  <span className="ml-2 text-neutral-900 dark:text-neutral-100 font-medium">{formatFileSize(document.file_size)}</span>
                </div>
                <div>
                  <span className="text-neutral-600 dark:text-neutral-400">File Type:</span>
                  <span className="ml-2 text-neutral-900 dark:text-neutral-100 font-medium">{document.mime_type}</span>
                </div>
                <div>
                  <span className="text-neutral-600 dark:text-neutral-400">Uploaded:</span>
                  <span className="ml-2 text-neutral-900 dark:text-neutral-100 font-medium">{formatDate(document.created_at)}</span>
                </div>
                {document.document_date && (
                  <div>
                    <span className="text-neutral-600 dark:text-neutral-400">Document Date:</span>
                    <span className="ml-2 text-neutral-900 dark:text-neutral-100 font-medium">{formatDate(document.document_date)}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Category Section */}
            <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Category</h2>
                {!isEditingCategory && (
                  <button
                    onClick={() => setIsEditingCategory(true)}
                    className="text-sm text-admin-primary hover:underline"
                  >
                    Edit
                  </button>
                )}
              </div>

              {isEditingCategory ? (
                <div className="space-y-4">
                  <select
                    value={selectedCategoryId}
                    onChange={(e) => setSelectedCategoryId(e.target.value)}
                    className="w-full rounded-md border border-neutral-300 px-3 py-2 focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
                  >
                    <option value="">Uncategorized</option>
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.name}</option>
                    ))}
                  </select>
                  <div className="flex space-x-2">
                    <Button
                      onClick={handleSaveCategory}
                      disabled={isSaving}
                    >
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setIsEditingCategory(false)
                        setSelectedCategoryId(document.category_id || '')
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {document.categories && document.categories.length > 0 ? (
                    document.categories.map((cat) => (
                      <span
                        key={cat.id}
                        className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-medium ${
                          cat.is_primary
                            ? 'bg-admin-primary/10 text-admin-primary border border-admin-primary/20'
                            : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100'
                        }`}
                      >
                        {cat.name}
                        {cat.is_primary && <span className="ml-1 text-xs">(Primary)</span>}
                      </span>
                    ))
                  ) : document.category_name ? (
                    <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium bg-neutral-100 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100">
                      {document.category_name}
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium bg-neutral-100 dark:bg-neutral-700 text-neutral-400 dark:text-neutral-500">
                      Uncategorized
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Keywords Section */}
            <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Keywords</h2>
                {!isEditingKeywords && (
                  <button
                    onClick={() => setIsEditingKeywords(true)}
                    className="text-sm text-admin-primary hover:underline"
                  >
                    Edit
                  </button>
                )}
              </div>

              {isEditingKeywords ? (
                <div className="space-y-4">
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={newKeyword}
                      onChange={(e) => setNewKeyword(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleAddKeyword()}
                      placeholder="Add keyword..."
                      className="flex-1 rounded-md border border-neutral-300 px-3 py-2 focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
                    />
                    <Button onClick={handleAddKeyword}>Add</Button>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {editedKeywords.map((keyword, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center space-x-1 bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
                      >
                        <span>{keyword}</span>
                        <button
                          onClick={() => handleRemoveKeyword(keyword)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>

                  <div className="flex space-x-2">
                    <Button
                      onClick={handleSaveKeywords}
                      disabled={isSaving}
                    >
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setIsEditingKeywords(false)
                        setEditedKeywords(document.keywords?.map(k => k.keyword) || [])
                        setNewKeyword('')
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {document.keywords && document.keywords.length > 0 ? (
                    document.keywords.map((kw, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 px-3 py-1 rounded-full text-sm"
                      >
                        {kw.keyword}
                      </span>
                    ))
                  ) : (
                    <p className="text-sm text-neutral-500 dark:text-neutral-400">No keywords assigned</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Actions */}
            <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
              <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Actions</h2>
              <div className="space-y-3">
                <Button
                  variant="primary"
                  className="w-full space-x-2"
                  onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${documentId}/content`, '_blank')}
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <span>Preview</span>
                </Button>

                <Button
                  variant="secondary"
                  className="w-full space-x-2"
                  onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${documentId}/download`, '_blank')}
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span>Download</span>
                </Button>

                <Button
                  variant="danger"
                  className="w-full space-x-2"
                  onClick={handleDeleteDocument}
                  disabled={deletingDocument}
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span>{deletingDocument ? 'Deleting...' : 'Delete Document'}</span>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
