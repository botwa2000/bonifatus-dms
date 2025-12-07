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

interface Entity {
  type: string
  value: string
  confidence: number
  method: string
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
  entities?: Entity[]
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
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<string[]>([])
  const [primaryCategoryId, setPrimaryCategoryId] = useState<string>('')
  const [isEditingKeywords, setIsEditingKeywords] = useState(false)
  const [editedKeywords, setEditedKeywords] = useState<string[]>([])
  const [newKeyword, setNewKeyword] = useState('')
  const [isEditingEntities, setIsEditingEntities] = useState(false)
  const [editedEntities, setEditedEntities] = useState<Entity[]>([])
  const [newEntityValue, setNewEntityValue] = useState('')
  const [newEntityType, setNewEntityType] = useState('ORGANIZATION')
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

      // Set selected categories from the categories array
      if (data.categories && data.categories.length > 0) {
        const catIds = data.categories.map(c => c.id)
        const primaryCat = data.categories.find(c => c.is_primary)
        setSelectedCategoryIds(catIds)
        setPrimaryCategoryId(primaryCat?.id || catIds[0] || '')
      } else if (data.category_id) {
        // Fallback to backward compat field
        setSelectedCategoryIds([data.category_id])
        setPrimaryCategoryId(data.category_id)
      } else {
        setSelectedCategoryIds([])
        setPrimaryCategoryId('')
      }

      setEditedKeywords(data.keywords?.map(k => k.keyword) || [])
      setEditedEntities(data.entities || [])
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

    if (selectedCategoryIds.length === 0) {
      setError('Please select at least one category')
      return
    }

    if (!primaryCategoryId || !selectedCategoryIds.includes(primaryCategoryId)) {
      setError('Please select a primary category from the selected categories')
      return
    }

    try {
      setIsSaving(true)
      setError(null)

      // Put primary category first in the array
      const orderedCategoryIds = [
        primaryCategoryId,
        ...selectedCategoryIds.filter(id => id !== primaryCategoryId)
      ]

      await apiClient.put(
        `/api/v1/documents/${documentId}`,
        { category_ids: orderedCategoryIds },
        true
      )

      setSuccess('Categories updated successfully')
      setIsEditingCategory(false)
      await loadDocument()
    } catch (err) {
      setError('Failed to update categories')
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

  const handleSaveEntities = async () => {
    if (!document) return

    try {
      setIsSaving(true)
      setError(null)

      await apiClient.put(
        `/api/v1/documents/${documentId}/entities`,
        { entities: editedEntities },
        true
      )

      setSuccess('Entities updated successfully')
      setIsEditingEntities(false)
      await loadDocument()
    } catch (err) {
      setError('Failed to update entities')
      console.error(err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleAddEntity = () => {
    if (newEntityValue.trim()) {
      const newEntity: Entity = {
        type: newEntityType,
        value: newEntityValue.trim(),
        confidence: 1.0, // User-added entities have full confidence
        method: 'manual'
      }
      setEditedEntities([...editedEntities, newEntity])
      setNewEntityValue('')
    }
  }

  const handleRemoveEntity = (entity: Entity) => {
    setEditedEntities(editedEntities.filter(e =>
      !(e.type === entity.type && e.value === entity.value)
    ))
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

  const toggleCategorySelection = (categoryId: string) => {
    if (selectedCategoryIds.includes(categoryId)) {
      // Deselecting - remove from array
      const newSelection = selectedCategoryIds.filter(id => id !== categoryId)
      setSelectedCategoryIds(newSelection)

      // If deselecting the primary category, set new primary to first remaining
      if (categoryId === primaryCategoryId) {
        setPrimaryCategoryId(newSelection[0] || '')
      }
    } else {
      // Selecting - add to array
      const newSelection = [...selectedCategoryIds, categoryId]
      setSelectedCategoryIds(newSelection)

      // If this is the first category, make it primary
      if (newSelection.length === 1) {
        setPrimaryCategoryId(categoryId)
      }
    }
  }

  const setPrimaryCategorySelection = (categoryId: string) => {
    // Only allow setting primary if category is selected
    if (selectedCategoryIds.includes(categoryId)) {
      setPrimaryCategoryId(categoryId)
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
                  <div className="space-y-2">
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
                      Select one or more categories. Click the radio button to set the primary category.
                    </p>
                    {categories.length === 0 ? (
                      <p className="text-sm text-neutral-500 dark:text-neutral-400">No categories available</p>
                    ) : (
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {categories.map(cat => {
                          const isSelected = selectedCategoryIds.includes(cat.id)
                          const isPrimary = cat.id === primaryCategoryId

                          return (
                            <div
                              key={cat.id}
                              className={`flex items-center justify-between p-3 border rounded-lg transition-colors ${
                                isSelected
                                  ? 'border-admin-primary bg-admin-primary/5 dark:bg-admin-primary/10'
                                  : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'
                              }`}
                            >
                              <div className="flex items-center space-x-3 flex-1">
                                <input
                                  type="checkbox"
                                  id={`cat-${cat.id}`}
                                  checked={isSelected}
                                  onChange={() => toggleCategorySelection(cat.id)}
                                  className="h-4 w-4 rounded border-neutral-300 text-admin-primary focus:ring-admin-primary"
                                />
                                <label
                                  htmlFor={`cat-${cat.id}`}
                                  className="flex-1 text-sm font-medium text-neutral-900 dark:text-neutral-100 cursor-pointer"
                                >
                                  {cat.name}
                                </label>
                              </div>
                              {isSelected && (
                                <div className="flex items-center space-x-2">
                                  <input
                                    type="radio"
                                    id={`primary-${cat.id}`}
                                    name="primary-category"
                                    checked={isPrimary}
                                    onChange={() => setPrimaryCategorySelection(cat.id)}
                                    className="h-4 w-4 border-neutral-300 text-admin-primary focus:ring-admin-primary"
                                  />
                                  <label
                                    htmlFor={`primary-${cat.id}`}
                                    className="text-xs text-neutral-600 dark:text-neutral-400 cursor-pointer"
                                  >
                                    Primary
                                  </label>
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      onClick={handleSaveCategory}
                      disabled={isSaving || selectedCategoryIds.length === 0}
                    >
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setIsEditingCategory(false)
                        // Restore original values
                        if (document.categories && document.categories.length > 0) {
                          const catIds = document.categories.map(c => c.id)
                          const primaryCat = document.categories.find(c => c.is_primary)
                          setSelectedCategoryIds(catIds)
                          setPrimaryCategoryId(primaryCat?.id || catIds[0] || '')
                        } else if (document.category_id) {
                          setSelectedCategoryIds([document.category_id])
                          setPrimaryCategoryId(document.category_id)
                        } else {
                          setSelectedCategoryIds([])
                          setPrimaryCategoryId('')
                        }
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

            {/* Entities Section */}
            <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  Extracted Information
                </h2>
                {!isEditingEntities && (
                  <button
                    onClick={() => setIsEditingEntities(true)}
                    className="text-sm text-admin-primary hover:underline"
                  >
                    Edit
                  </button>
                )}
              </div>

              {isEditingEntities ? (
                <div className="space-y-4">
                  <div className="flex space-x-2">
                    <select
                      value={newEntityType}
                      onChange={(e) => setNewEntityType(e.target.value)}
                      className="rounded-md border border-neutral-300 px-3 py-2 focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
                    >
                      <option value="ORGANIZATION">Organization</option>
                      <option value="PERSON">Person</option>
                      <option value="LOCATION">Location</option>
                      <option value="ADDRESS">Address</option>
                      <option value="EMAIL">Email</option>
                      <option value="URL">Website</option>
                    </select>
                    <input
                      type="text"
                      value={newEntityValue}
                      onChange={(e) => setNewEntityValue(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleAddEntity()}
                      placeholder="Add entity value..."
                      className="flex-1 rounded-md border border-neutral-300 px-3 py-2 focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
                    />
                    <Button onClick={handleAddEntity}>Add</Button>
                  </div>

                  <div className="space-y-3">
                    {Object.entries(
                      editedEntities.reduce((acc, entity) => {
                        if (!acc[entity.type]) acc[entity.type] = []
                        acc[entity.type].push(entity)
                        return acc
                      }, {} as Record<string, Entity[]>)
                    ).map(([type, entities]) => (
                      <div key={type}>
                        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
                          {type.replace(/_/g, ' ')}
                        </h3>
                        <div className="flex flex-wrap gap-2">
                          {entities.map((entity, index) => (
                            <span
                              key={index}
                              className="inline-flex items-center space-x-1 bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
                            >
                              <span>{entity.value}</span>
                              <button
                                onClick={() => handleRemoveEntity(entity)}
                                className="text-blue-600 hover:text-blue-800"
                              >
                                ×
                              </button>
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex space-x-2">
                    <Button
                      onClick={handleSaveEntities}
                      disabled={isSaving}
                    >
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setIsEditingEntities(false)
                        setEditedEntities(document.entities || [])
                        setNewEntityValue('')
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                {(document.entities && document.entities.length > 0) ? (
                <div className="space-y-4">
                  {(() => {
                    // Group entities by type
                    const entityGroups = document.entities?.reduce((acc, entity) => {
                      if (!acc[entity.type]) {
                        acc[entity.type] = []
                      }
                      acc[entity.type].push(entity)
                      return acc
                    }, {} as Record<string, Entity[]>) || {}

                    // Entity type display configuration
                    const entityConfig: Record<string, { label: string; icon: string; variant: BadgeVariant }> = {
                      ORGANIZATION: { label: 'Organizations', icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4', variant: 'info' },
                      PERSON: { label: 'People', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z', variant: 'default' },
                      LOCATION: { label: 'Locations', icon: 'M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z', variant: 'success' },
                      ADDRESS: { label: 'Addresses', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6', variant: 'warning' },
                      ADDRESS_COMPONENT: { label: 'Address Components', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6', variant: 'warning' },
                      EMAIL: { label: 'Email Addresses', icon: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z', variant: 'info' },
                      URL: { label: 'Websites', icon: 'M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9', variant: 'default' },
                      SENDER: { label: 'Senders', icon: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z', variant: 'info' },
                      RECIPIENT: { label: 'Recipients', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z', variant: 'default' },
                    }

                    return Object.entries(entityGroups).map(([type, entities]) => {
                      const config = entityConfig[type] || {
                        label: type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                        icon: 'M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z',
                        variant: 'default' as BadgeVariant
                      }

                      return (
                        <div key={type}>
                          <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 flex items-center">
                            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={config.icon} />
                            </svg>
                            {config.label}
                          </h3>
                          <div className="flex flex-wrap gap-2">
                            {entities.map((entity, index) => {
                              const displayValue = entity.value
                              const isUrl = type === 'URL'

                              if (isUrl) {
                                return (
                                  <a
                                    key={index}
                                    href={displayValue.startsWith('http') ? displayValue : `https://${displayValue}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center hover:opacity-80 transition-opacity"
                                    title={`Confidence: ${Math.round(entity.confidence * 100)}% | Method: ${entity.method}`}
                                  >
                                    <Badge variant={config.variant}>
                                      {displayValue}
                                      <svg className="w-3 h-3 ml-1 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                      </svg>
                                    </Badge>
                                  </a>
                                )
                              }

                              return (
                                <span
                                  key={index}
                                  title={`Confidence: ${Math.round(entity.confidence * 100)}% | Method: ${entity.method}`}
                                >
                                  <Badge variant={config.variant}>{displayValue}</Badge>
                                </span>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })
                  })()}
                </div>
                ) : (
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">No entities extracted</p>
                )}
                </>
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
