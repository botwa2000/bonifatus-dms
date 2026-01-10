// frontend/src/components/categories/CategoryCard.tsx
import type { Category } from '@/services/category.service'
import { Badge } from '@/components/ui'

export function CategoryCard({
  category,
  onEdit,
  onDelete
}: {
  category: Category
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <div className="bg-white rounded-lg border border-neutral-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div
            className="h-12 w-12 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: category.color_hex + '20' }}
          >
            <div
              className="h-8 w-8 rounded"
              style={{ backgroundColor: category.color_hex }}
            />
          </div>
          <div>
            <h3 className="font-semibold text-neutral-900 dark:text-white">{category.name}</h3>
            {category.is_system && (
              <Badge variant="default">System</Badge>
            )}
          </div>
        </div>

        {!category.is_system && (
          <div className="flex space-x-1">
            <button
              onClick={onEdit}
              className="p-2 text-neutral-600 hover:text-admin-primary hover:bg-neutral-100 rounded transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button
              onClick={onDelete}
              className="p-2 text-neutral-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        )}
      </div>

      <p className="text-sm text-neutral-600 mb-4 line-clamp-2">
        {category.description || 'No description'}
      </p>

      <div className="flex items-center justify-between pt-4 border-t border-neutral-100">
        <span className="text-sm text-neutral-600">Documents</span>
        <span className="font-medium text-neutral-900 dark:text-white">{category.documents_count || 0}</span>
      </div>
    </div>
  )
}