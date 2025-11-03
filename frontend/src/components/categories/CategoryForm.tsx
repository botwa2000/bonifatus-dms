// frontend/src/components/categories/CategoryForm.tsx
import { useState } from 'react'
import { Input, Button } from '@/components/ui'
import { KeywordsManager } from './KeywordsManager'
import type { Category, CategoryCreateData } from '@/services/category.service'

type TabType = 'general' | 'keywords'

export function CategoryForm({
  category,
  onSave,
  onCancel
}: {
  category?: Category
  onSave: (data: CategoryCreateData) => void
  onCancel: () => void
}) {
  const [activeTab, setActiveTab] = useState<TabType>('general')
  const [formData, setFormData] = useState({
    name: category?.name || '',
    description: category?.description || '',
    color_hex: category?.color_hex || '#6366f1',
    icon_name: category?.icon_name || 'folder'
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const userLanguage = 'en'
    
    const submitData = {
      translations: {
        [userLanguage]: {
          name: formData.name,
          description: formData.description || undefined
        }
      },
      color_hex: formData.color_hex,
      icon_name: formData.icon_name,
      sort_order: category?.sort_order || 999,
      is_active: category?.is_active !== undefined ? category.is_active : true
    }
    
    onSave(submitData)
  }

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="border-b border-neutral-200 dark:border-neutral-700">
        <nav className="-mb-px flex space-x-8">
          <button
            type="button"
            onClick={() => setActiveTab('general')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'general'
                ? 'border-admin-primary text-admin-primary dark:border-admin-primary dark:text-admin-primary'
                : 'border-transparent text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 hover:border-neutral-300 dark:hover:border-neutral-600'
            }`}
          >
            General
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('keywords')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'keywords'
                ? 'border-admin-primary text-admin-primary dark:border-admin-primary dark:text-admin-primary'
                : 'border-transparent text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 hover:border-neutral-300 dark:hover:border-neutral-600'
            }`}
          >
            Keywords
          </button>
        </nav>
      </div>

      {/* General Tab */}
      {activeTab === 'general' && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Category Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
              rows={3}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
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
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save
            </Button>
          </div>
        </form>
      )}

      {/* Keywords Tab */}
      {activeTab === 'keywords' && (
        <div>
          {category?.id ? (
            <>
              <KeywordsManager categoryId={category.id} />
              <div className="flex justify-end pt-4">
                <Button type="button" variant="secondary" onClick={onCancel}>
                  Close
                </Button>
              </div>
            </>
          ) : (
            <div className="py-12 text-center">
              <svg
                className="mx-auto h-12 w-12 text-neutral-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1}
                  d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Save Category First
              </h3>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                Create the category first, then you can add keywords to improve document classification.
              </p>
              <div className="mt-6">
                <Button type="button" onClick={() => setActiveTab('general')}>
                  Go to General Tab
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}