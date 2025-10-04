// frontend/src/services/category.service.ts
import { apiClient } from './api-client'

export interface Category {
  id: string
  reference_key: string
  name: string
  description?: string
  color_hex: string
  icon_name: string
  sort_order: number
  is_active: boolean
  is_system: boolean
  user_id?: string
  documents_count?: number
  created_at: string
  updated_at: string
}

export interface CategoryListResponse {
  categories: Category[]
  total_count: number
}

export interface CategoryTranslation {
  name: string
  description?: string
}

export interface CategoryCreateData {
  translations: Record<string, CategoryTranslation>
  color_hex: string
  icon_name: string
  sort_order?: number
  is_active?: boolean
}

export interface CategoryUpdateData {
  translations?: Record<string, CategoryTranslation>
  color_hex?: string
  icon_name?: string
  sort_order?: number
  is_active?: boolean
}

class CategoryService {
  async listCategories(
    includeSystem: boolean = true,
    includeDocumentsCount: boolean = true
  ): Promise<CategoryListResponse> {
    const params: Record<string, string> = {
      include_system: String(includeSystem),
      include_documents_count: String(includeDocumentsCount)
    }

    return await apiClient.get<CategoryListResponse>(
      '/api/v1/categories',
      true,
      { params }
    )
  }

  async createCategory(data: CategoryCreateData): Promise<Category> {
    return await apiClient.post<Category>(
      '/api/v1/categories',
      data,
      true
    )
  }

  async updateCategory(id: string, data: CategoryUpdateData): Promise<Category> {
    return await apiClient.put<Category>(
      `/api/v1/categories/${id}`,
      data,
      true
    )
  }

  async deleteCategory(
    id: string,
    moveToCategoryId?: string,
    deleteDocuments: boolean = false
  ): Promise<void> {
    const params: Record<string, string> = {}
    
    if (moveToCategoryId) {
      params.move_to_category_id = moveToCategoryId
    }
    if (deleteDocuments) {
      params.delete_documents = String(deleteDocuments)
    }

    await apiClient.delete(
      `/api/v1/categories/${id}`,
      true,
      { params }
    )
  }

  async restoreDefaults(): Promise<void> {
    await apiClient.post(
      '/api/v1/categories/restore-defaults',
      {},
      true
    )
  }
}

export const categoryService = new CategoryService()