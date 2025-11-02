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

      await apiClient.patch(
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

      await apiClient.patch(
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
        return 'neutral'
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
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Loading document...</p>
        </div>
      </div>
    )
  }

  if (error && !document) {
    return (
      <div className="min-h-screen bg-neutral-50">
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
    <div className="min-h-screen bg-neutral-50">
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
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-neutral-900 mb-2">
                    {document.title}
                  </h1>
                  <p className="text-sm text-neutral-600">{document.file_name}</p>
                </div>
                <Badge variant={getStatusBadgeVariant(document.processing_status)}>
                  {document.processing_status}
                </Badge>
              </div>

              {document.description && (
                <div className="mb-4">
                  <h2 className="text-sm font-semibold text-neutral-700 mb-2">Description</h2>
                  <p className="text-neutral-900">{document.description}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-neutral-600">File Size:</span>
                  <span className="ml-2 text-neutral-900 font-medium">{formatFileSize(document.file_size)}</span>
                </div>
                <div>
                  <span className="text-neutral-600">File Type:</span>
                  <span className="ml-2 text-neutral-900 font-medium">{document.mime_type}</span>
                </div>
                <div>
                  <span className="text-neutral-600">Uploaded:</span>
                  <span className="ml-2 text-neutral-900 font-medium">{formatDate(document.created_at)}</span>
                </div>
                {document.document_date && (
                  <div>
                    <span className="text-neutral-600">Document Date:</span>
                    <span className="ml-2 text-neutral-900 font-medium">{formatDate(document.document_date)}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Category Section */}
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-neutral-900">Category</h2>
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
                <div>
                  <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium bg-neutral-100 text-neutral-900">
                    {document.category_name || 'Uncategorized'}
                  </span>
                </div>
              )}
            </div>

            {/* Keywords Section */}
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-neutral-900">Keywords</h2>
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
                        className="inline-flex items-center bg-neutral-100 text-neutral-700 px-3 py-1 rounded-full text-sm"
                      >
                        {kw.keyword}
                      </span>
                    ))
                  ) : (
                    <p className="text-sm text-neutral-500">No keywords assigned</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Actions */}
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <h2 className="text-lg font-semibold text-neutral-900 mb-4">Actions</h2>
              <div className="space-y-3">
                <button
                  onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${documentId}/download`, '_blank')}
                  className="w-full flex items-center justify-center space-x-2 bg-admin-primary text-white px-4 py-2 rounded-md hover:bg-blue-700 font-medium"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span>Download</span>
                </button>

                <button
                  onClick={handleDeleteDocument}
                  disabled={deletingDocument}
                  className="w-full flex items-center justify-center space-x-2 bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 font-medium disabled:opacity-50"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span>{deletingDocument ? 'Deleting...' : 'Delete Document'}</span>
                </button>
              </div>
            </div>

            {/* Document Preview */}
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <h2 className="text-lg font-semibold text-neutral-900 mb-4">Preview</h2>
              <div className="aspect-[3/4] bg-neutral-100 rounded-lg flex items-center justify-center">
                <div className="text-center p-4">
                  <svg className="h-16 w-16 text-neutral-400 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-sm text-neutral-600">Preview not available</p>
                  <p className="text-xs text-neutral-500 mt-1">Download to view</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
