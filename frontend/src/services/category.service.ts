// frontend/src/services/category.service.ts
import { apiClient } from './api-client'

export interface Category {
  id: string
  name_en: string
  name_de?: string
  name_ru?: string
  description_en?: string
  description_de?: string
  description_ru?: string
  color_hex: string
  icon_name?: string
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

export interface CategoryCreateData {
  name_en: string
  name_de?: string
  name_ru?: string
  description_en?: string
  description_de?: string
  description_ru?: string
  color_hex?: string
  icon_name?: string
  sort_order?: number
}

export interface CategoryUpdateData extends Partial<CategoryCreateData> {
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

  async createCategory(data: Partial<Category>): Promise<Category> {
    return await apiClient.post<Category>(
      '/api/v1/categories',
      data,
      true
    )
  }

  async updateCategory(id: string, data: Partial<Category>): Promise<Category> {
    return await apiClient.put<Category>(
      `/api/v1/categories/${id}`,
      data,
      true
    )
  }

  async deleteCategory(
    id: string,
    moveToCategor yId?: string,
    deleteDocuments: boolean = false
  ): Promise<void> {
    const data = {
      move_to_category_id: moveToCategoryId,
      delete_documents: deleteDocuments
    }

    await apiClient.delete(
      `/api/v1/categories/${id}`,
      data,
      true
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