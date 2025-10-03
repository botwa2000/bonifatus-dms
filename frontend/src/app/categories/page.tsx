// src/app/categories/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/use-auth'
import { categoryService, type Category } from '@/services/category.service'

type ViewMode = 'list' | 'grid'
type SortField = 'name' | 'documents' | 'updated' | 'created'
type SortDirection = 'asc' | 'desc'

export default function CategoriesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth()
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

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, authLoading, router])

  useEffect(() => {
    if (isAuthenticated) {
      loadCategories()
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
      console.error('Load categories error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateCategory = async (categoryData: Partial<Category>) => {
    try {
      await categoryService.createCategory(categoryData)
      setShowCreateModal(false)
      await loadCategories()
    } catch (err) {
      console.error('Create category error:', err)
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to create category'
      setError(errorMessage)
      setTimeout(() => setError(null), 5000)
    }
  }

  const handleUpdateCategory = async (id: string, categoryData: Partial<Category>) => {
    try {
      await categoryService.updateCategory(id, categoryData)
      setEditingCategory(null)
      await loadCategories()
    } catch (err) {
      console.error('Update category error:', err)
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
      console.error('Delete category error:', err)
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
          compareValue = a.name_en.localeCompare(b.name_en)
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
      <header className="bg-white shadow-sm border-b border-neutral-200">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/dashboard" className="text-neutral-600 hover:text-neutral-900">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Categories</h1>
                <p className="text-sm text-neutral-600">Organize your documents</p>
              </div>
            </div>
            
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 bg-admin-primary text-white rounded-md hover:bg-blue-700 font-medium transition-colors"
            >
              <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Category
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 rounded-lg bg-red-50 border border-red-200 p-4">
            <div className="flex">
              <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="ml-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-neutral-600">Total Categories</p>
                <p className="text-3xl font-bold text-neutral-900 mt-1">{categories.length}</p>
              </div>
              <div className="h-12 w-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-neutral-600">Total Documents</p>
                <p className="text-3xl font-bold text-neutral-900 mt-1">{totalDocuments}</p>
              </div>
              <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-neutral-600">Custom Categories</p>
                <p className="text-3xl font-bold text-neutral-900 mt-1">
                  {categories.filter(c => !c.is_system).length}
                </p>
              </div>
              <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-neutral-200 mb-6">
          <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-neutral-900">
              {categories.length} {categories.length === 1 ? 'Category' : 'Categories'}
            </h2>
            
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
          </div>

          {categories.length === 0 ? (
            <div className="text-center py-12">
              <svg className="h-16 w-16 text-neutral-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              <h3 className="text-lg font-medium text-neutral-900 mb-2">No categories yet</h3>
              <p className="text-neutral-600 mb-4">Create your first category to organize documents</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center px-4 py-2 bg-admin-primary text-white rounded-md hover:bg-blue-700 font-medium"
              >
                Create Category
              </button>
            </div>
          ) : viewMode === 'list' ? (
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
                    <th className="px-6 py-3 text-left">
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
                    <th className="px-6 py-3 text-left">
                      <button
                        onClick={() => handleSort('updated')}
                        className="flex items-center space-x-1 text-xs font-medium text-neutral-600 uppercase tracking-wider hover:text-neutral-900"
                      >
                        <span>Last Updated</span>
                        {sortField === 'updated' && (
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
                          <div>
                            <div className="font-medium text-neutral-900">{category.name_en}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-neutral-600 max-w-md truncate">
                          {category.description_en || 'No description'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {category.is_system ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-800">
                            System
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            Custom
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-neutral-900">
                          {category.documents_count || 0}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-neutral-600">
                          {new Date(category.updated_at).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric'
                          })}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => setEditingCategory(category)}
                            className="p-1.5 text-neutral-400 hover:text-admin-primary transition-colors"
                            title="Edit category"
                          >
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => setDeletingCategory(category)}
                            className="p-1.5 text-neutral-400 hover:text-red-600 transition-colors"
                            title="Delete category"
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
          ) : (
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {sortedCategories.map((category) => (
                <div
                  key={category.id}
                  className="bg-white rounded-lg border border-neutral-200 p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <div
                        className="h-10 w-10 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: category.color_hex + '20' }}
                      >
                        <div
                          className="h-6 w-6 rounded"
                          style={{ backgroundColor: category.color_hex }}
                        />
                      </div>
                      <div>
                        <h3 className="font-semibold text-neutral-900">{category.name_en}</h3>
                        {category.is_system && (
                          <span className="text-xs text-neutral-500">System</span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex space-x-1">
                      <button
                        onClick={() => setEditingCategory(category)}
                        className="p-1 text-neutral-400 hover:text-admin-primary"
                      >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => setDeletingCategory(category)}
                        className="p-1 text-neutral-400 hover:text-red-600"
                      >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  <p className="text-sm text-neutral-600 mb-4 line-clamp-2">
                    {category.description_en || 'No description'}
                  </p>

                  <div className="flex items-center justify-between pt-4 border-t border-neutral-100">
                    <span className="text-sm text-neutral-600">Documents</span>
                    <span className="font-medium text-neutral-900">{category.documents_count || 0}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {showCreateModal && (
        <CategoryModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreateCategory}
          title="Create New Category"
        />
      )}

      {editingCategory && (
        <CategoryModal
          category={editingCategory}
          onClose={() => setEditingCategory(null)}
          onSave={(data) => handleUpdateCategory(editingCategory.id, data)}
          title="Edit Category"
        />
      )}

      {deletingCategory && (
        <DeleteConfirmModal
          category={deletingCategory}
          onClose={() => setDeletingCategory(null)}
          onConfirm={() => handleDeleteCategory(deletingCategory.id)}
        />
      )}
    </div>
  )
}

function CategoryModal({ 
  category, 
  onClose, 
  onSave, 
  title 
}: { 
  category?: Category
  onClose: () => void
  onSave: (data: Partial<Category>) => void
  title: string
}) {
  const [formData, setFormData] = useState({
    name_en: category?.name_en || '',
    description_en: category?.description_en || '',
    color_hex: category?.color_hex || '#6366f1',
    icon_name: category?.icon_name || 'folder'
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold text-neutral-900 mb-4">{title}</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Category Name
            </label>
            <input
              type="text"
              value={formData.name_en}
              onChange={(e) => setFormData({ ...formData, name_en: e.target.value })}
              className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-admin-primary"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description_en}
              onChange={(e) => setFormData({ ...formData, description_en: e.target.value })}
              className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-admin-primary"
              rows={3}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Color
            </label>
            <input
              type="color"
              value={formData.color_hex}
              onChange={(e) => setFormData({ ...formData, color_hex: e.target.value })}
              className="w-full h-10 border border-neutral-300 rounded-md cursor-pointer"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-neutral-300 rounded-md text-neutral-700 hover:bg-neutral-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-admin-primary text-white rounded-md hover:bg-blue-700"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function DeleteConfirmModal({ 
  category, 
  onClose, 
  onConfirm 
}: { 
  category: Category
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold text-neutral-900 mb-4">Delete Category</h2>
        
        <p className="text-neutral-600 mb-6">
          Are you sure you want to delete <strong>{category.name_en}</strong>? 
          Documents in this category will be moved to &ldquo;Other&rdquo;.
        </p>

        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-neutral-300 rounded-md text-neutral-700 hover:bg-neutral-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}