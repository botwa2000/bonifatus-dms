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

export interface CategoryKeyword {
  id: string
  keyword: string
  language_code: string
  weight: number
  match_count: number
  last_matched_at: string | null
  is_system_default: boolean
  created_at: string | null
}

export interface KeywordListResponse {
  keywords: CategoryKeyword[]
}

export interface KeywordCreateRequest {
  keyword: string
  language_code: string
  weight: number
}

export interface KeywordUpdateRequest {
  weight: number
}

export interface KeywordOverlapCategory {
  category_id: string
  reference_key: string
  weight: number
  match_count: number
  is_system_default: boolean
}

export interface KeywordOverlap {
  keyword: string
  categories: KeywordOverlapCategory[]
  severity: 'low' | 'medium' | 'high'
  category_count: number
}

export interface KeywordOverlapResponse {
  overlaps: KeywordOverlap[]
  total_overlaps: number
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

  // Keyword Management Methods

  async getKeywords(
    categoryId: string,
    languageCode?: string
  ): Promise<KeywordListResponse> {
    // Only include language_code param if specified, otherwise backend returns ALL languages
    const params = languageCode ? { language_code: languageCode } : {}

    return await apiClient.get<KeywordListResponse>(
      `/api/v1/categories/${categoryId}/keywords`,
      true,
      { params }
    )
  }

  async addKeyword(
    categoryId: string,
    data: KeywordCreateRequest
  ): Promise<CategoryKeyword> {
    return await apiClient.post<CategoryKeyword>(
      `/api/v1/categories/${categoryId}/keywords`,
      data,
      true
    )
  }

  async updateKeywordWeight(
    categoryId: string,
    keywordId: string,
    weight: number
  ): Promise<CategoryKeyword> {
    return await apiClient.put<CategoryKeyword>(
      `/api/v1/categories/${categoryId}/keywords/${keywordId}`,
      { weight },
      true
    )
  }

  async deleteKeyword(
    categoryId: string,
    keywordId: string
  ): Promise<void> {
    await apiClient.delete(
      `/api/v1/categories/${categoryId}/keywords/${keywordId}`,
      true
    )
  }

  async getKeywordOverlaps(
    languageCode?: string
  ): Promise<KeywordOverlapResponse> {
    // For overlaps, default to 'en' if not specified (overlap check is language-specific)
    const lang = languageCode || 'en'

    return await apiClient.get<KeywordOverlapResponse>(
      '/api/v1/categories/keywords/overlaps',
      true,
      { params: { language_code: lang } }
    )
  }
}

export const categoryService = new CategoryService()