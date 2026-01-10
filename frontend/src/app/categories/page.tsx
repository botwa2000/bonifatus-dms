// frontend/src/app/categories/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import {
  categoryService,
  type Category,
  type CategoryCreateData,
  type CategoryUpdateData
} from '@/services/category.service'
import { Button, Modal, ModalHeader, ModalContent, ModalFooter, Alert, Badge } from '@/components/ui'
import { CategoryStatsCard } from '@/components/categories/CategoryStatsCard'
import { CategoryForm } from '@/components/categories/CategoryForm'
import { CategoryCard } from '@/components/categories/CategoryCard'
import AppHeader from '@/components/AppHeader'
import { logger } from '@/lib/logger'

type ViewMode = 'list' | 'grid'
type SortField = 'name' | 'documents' | 'updated' | 'created'
type SortDirection = 'asc' | 'desc'

export default function CategoriesPage() {
  const { isAuthenticated, isLoading: authLoading, hasAttemptedAuth, loadUser } = useAuth()
  const router = useRouter()

  const [categories, setCategories] = useState<Category[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [deletingCategory, setDeletingCategory] = useState<Category | null>(null)

  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

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
    let timeoutId: NodeJS.Timeout

    if (isAuthenticated) {
      // Initial load
      loadCategories()

      // Only reload on visibility change if more than 5 seconds have passed
      const handleVisibilityChange = () => {
        if (document.visibilityState === 'visible') {
          clearTimeout(timeoutId)
          timeoutId = setTimeout(() => {
            loadCategories()
          }, 1000) // Debounce by 1 second
        }
      }

      document.addEventListener('visibilitychange', handleVisibilityChange)
      
      return () => {
        clearTimeout(timeoutId)
        document.removeEventListener('visibilitychange', handleVisibilityChange)
      }
    }
  }, [isAuthenticated])

  const loadCategories = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await categoryService.listCategories()
      setCategories(data.categories)
    } catch (err) {
      setError('Failed to load categories. Please try again.')
      logger.error('Load categories error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateCategory = async (categoryData: CategoryCreateData) => {
    try {
      await categoryService.createCategory(categoryData)
      setShowCreateModal(false)
      await loadCategories()
    } catch (err) {
      logger.error('Create category error:', err)
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to create category'
      setError(errorMessage)
      setTimeout(() => setError(null), 5000)
    }
  }

  const handleUpdateCategory = async (id: string, categoryData: CategoryUpdateData) => {
    try {
      await categoryService.updateCategory(id, categoryData)
      setEditingCategory(null)
      await loadCategories()
    } catch (err) {
      logger.error('Update category error:', err)
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to update category'
      setError(errorMessage)
      setTimeout(() => setError(null), 5000)
    }
  }

  const handleDeleteCategory = async (id: string) => {
    try {
      await categoryService.deleteCategory(id)
      setDeletingCategory(null)
      await loadCategories()
    } catch (err) {
      logger.error('Delete category error:', err)
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to delete category'
      setError(errorMessage)
      setTimeout(() => setError(null), 5000)
    }
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const getSortedCategories = () => {
    const sorted = [...categories].sort((a, b) => {
      let compareValue = 0

      switch (sortField) {
        case 'name':
          compareValue = a.name.localeCompare(b.name)
          break
        case 'documents':
          compareValue = (a.documents_count || 0) - (b.documents_count || 0)
          break
        case 'updated':
          compareValue = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
          break
        case 'created':
          compareValue = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          break
      }

      return sortDirection === 'asc' ? compareValue : -compareValue
    })

    return sorted
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

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Loading categories...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  const totalDocuments = categories.reduce((sum, cat) => sum + (cat.documents_count || 0), 0)
  const sortedCategories = getSortedCategories()

  return (
    <div className="min-h-screen bg-neutral-50">
      <AppHeader
        title="Categories"
        subtitle="Organize your documents"
        action={
          <Button onClick={() => setShowCreateModal(true)}>
            <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Category
          </Button>
        }
      />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6">
            <Alert type="error" message={error} />
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <CategoryStatsCard
            label="Total Categories"
            value={categories.length}
            color="bg-purple-100"
            icon={
              <svg className="h-6 w-6 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            }
          />
          
          <CategoryStatsCard
            label="Total Documents"
            value={totalDocuments}
            color="bg-semantic-info-bg-strong dark:bg-blue-900/30"
            icon={
              <svg className="h-6 w-6 text-admin-primary dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
          />
          
          <div onClick={() => setShowCreateModal(true)} className="cursor-pointer">
            <CategoryStatsCard
              label="Custom Categories"
              value={categories.filter(c => !c.is_system).length}
              color="bg-semantic-success-bg-strong dark:bg-green-900/30"
              icon={
                <svg className="h-6 w-6 text-admin-success dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              }
            />
          </div>
        </div>

        <div className="bg-white rounded-lg border border-neutral-200 mb-6">
          <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-neutral-900">
              {categories.length} {categories.length === 1 ? 'Category' : 'Categories'}
            </h2>
            <ViewModeToggle />
          </div>

          {categories.length === 0 ? (
            <div className="text-center py-12">
              <svg className="h-16 w-16 text-neutral-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              <h3 className="text-lg font-medium text-neutral-900 mb-2">No categories yet</h3>
              <p className="text-neutral-600 mb-4">Create your first category to organize documents</p>
              <Button onClick={() => setShowCreateModal(true)}>
                Create Category
              </Button>
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
              {sortedCategories.map((category) => (
                <CategoryCard
                  key={category.id}
                  category={category}
                  onEdit={() => setEditingCategory(category)}
                  onDelete={() => setDeletingCategory(category)}
                />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-neutral-50 border-b border-neutral-200">
                  <tr>
                    <th className="px-6 py-3 text-left">
                      <button
                        onClick={() => handleSort('name')}
                        className="flex items-center space-x-1 text-xs font-medium text-neutral-600 uppercase tracking-wider hover:text-neutral-900"
                      >
                        <span>Category</span>
                        {sortField === 'name' && (
                          <svg className={`h-4 w-4 ${sortDirection === 'desc' ? 'transform rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                          </svg>
                        )}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-600 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-neutral-600 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-center">
                      <button
                        onClick={() => handleSort('documents')}
                        className="flex items-center space-x-1 text-xs font-medium text-neutral-600 uppercase tracking-wider hover:text-neutral-900"
                      >
                        <span>Documents</span>
                        {sortField === 'documents' && (
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
                  {sortedCategories.map((category) => (
                    <tr key={category.id} className="hover:bg-neutral-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-3">
                          <div
                            className="h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0"
                            style={{ backgroundColor: category.color_hex + '20' }}
                          >
                            <div
                              className="h-6 w-6 rounded"
                              style={{ backgroundColor: category.color_hex }}
                            />
                          </div>
                          <div className="font-medium text-neutral-900">{category.name}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-neutral-600 max-w-md truncate">
                          {category.description || 'No description'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {category.is_system ? (
                          <Badge variant="default">System</Badge>
                        ) : (
                          <Badge variant="success">Custom</Badge>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span className="text-sm font-medium text-neutral-900">
                          {category.documents_count || 0}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => setEditingCategory(category)}
                              className="p-1 text-neutral-600 hover:text-admin-primary"
                            >
                              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                              </svg>
                            </button>
                            <button
                              onClick={() => setDeletingCategory(category)}
                              className="p-1 text-neutral-600 hover:text-admin-danger dark:text-red-400"
                            >
                              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
        </div>
      </main>

      <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)}>
        <ModalHeader title="Create New Category" onClose={() => setShowCreateModal(false)} />
        <ModalContent>
          <CategoryForm
            onSave={handleCreateCategory}
            onCancel={() => setShowCreateModal(false)}
          />
        </ModalContent>
      </Modal>

      <Modal isOpen={!!editingCategory} onClose={() => setEditingCategory(null)}>
        <ModalHeader title="Edit Category" onClose={() => setEditingCategory(null)} />
        <ModalContent>
          <CategoryForm
            category={editingCategory!}
            onSave={(data) => handleUpdateCategory(editingCategory!.id, data)}
            onCancel={() => setEditingCategory(null)}
          />
        </ModalContent>
      </Modal>

      <Modal isOpen={!!deletingCategory} onClose={() => setDeletingCategory(null)}>
        <ModalHeader title="Delete Category" onClose={() => setDeletingCategory(null)} />
        <ModalContent>
          <p className="text-neutral-600 mb-6">
            Are you sure you want to delete <strong>{deletingCategory?.name}</strong>? 
            Documents in this category will be moved to &quot;Other&quot;.
          </p>
        </ModalContent>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setDeletingCategory(null)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={() => handleDeleteCategory(deletingCategory!.id)}>
            Delete
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}