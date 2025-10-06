// frontend/src/components/categories/CategoryForm.tsx
import { useState } from 'react'
import { Input, Button } from '@/components/ui'
import type { Category, CategoryCreateData } from '@/services/category.service'

export function CategoryForm({
  category,
  onSave,
  onCancel
}: {
  category?: Category
  onSave: (data: CategoryCreateData) => void
  onCancel: () => void
}) {
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
  )
}