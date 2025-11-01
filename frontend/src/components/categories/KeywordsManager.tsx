// frontend/src/components/categories/KeywordsManager.tsx
'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui'
import { categoryService } from '@/services/category.service'
import type { CategoryKeyword, KeywordOverlap } from '@/services/category.service'

interface KeywordsManagerProps {
  categoryId: string
  languageCode?: string
}

export function KeywordsManager({ categoryId, languageCode }: KeywordsManagerProps) {
  const [keywords, setKeywords] = useState<CategoryKeyword[]>([])
  const [overlaps, setOverlaps] = useState<KeywordOverlap[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [newKeyword, setNewKeyword] = useState('')
  const [newWeight, setNewWeight] = useState(1.0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadKeywords()
    loadOverlaps()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryId, languageCode])

  const loadKeywords = async () => {
    try {
      setLoading(true)
      console.log('[KeywordsManager DEBUG] Loading keywords:', {
        categoryId,
        languageCode,
        languageCodeType: typeof languageCode,
        isUndefined: languageCode === undefined
      })
      const data = await categoryService.getKeywords(categoryId, languageCode)
      console.log('[KeywordsManager DEBUG] Received keywords:', {
        count: data.keywords.length,
        languages: [...new Set(data.keywords.map(k => k.language_code))],
        sample: data.keywords.slice(0, 3).map(k => ({ keyword: k.keyword, lang: k.language_code }))
      })
      setKeywords(data.keywords)
      setError(null)
    } catch (err) {
      console.error('[KeywordsManager DEBUG] Failed to load keywords:', err)
      setError('Failed to load keywords')
    } finally {
      setLoading(false)
    }
  }

  const loadOverlaps = async () => {
    try {
      const data = await categoryService.getKeywordOverlaps(languageCode)
      setOverlaps(data.overlaps.filter(o =>
        o.categories.some(c => c.category_id === categoryId)
      ))
    } catch (err) {
      console.error('Failed to load overlaps:', err)
    }
  }

  const handleAddKeyword = async () => {
    if (!newKeyword.trim() || newKeyword.length < 2) {
      setError('Keyword must be at least 2 characters')
      return
    }

    try {
      setError(null)
      await categoryService.addKeyword(categoryId, {
        keyword: newKeyword.trim(),
        language_code: languageCode || 'en', // Default to 'en' when adding new keywords
        weight: newWeight
      })

      setNewKeyword('')
      setNewWeight(1.0)
      setAdding(false)

      await loadKeywords()
      await loadOverlaps()
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to add keyword')
    }
  }

  const handleUpdateWeight = async (keywordId: string, weight: number) => {
    try {
      await categoryService.updateKeywordWeight(categoryId, keywordId, weight)
      await loadKeywords()
      await loadOverlaps()
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to update weight')
    }
  }

  const handleDeleteKeyword = async (keywordId: string, isSystem: boolean) => {
    if (isSystem) {
      setError('Cannot delete system keywords')
      return
    }

    if (!confirm('Are you sure you want to delete this keyword?')) {
      return
    }

    try {
      await categoryService.deleteKeyword(categoryId, keywordId)
      await loadKeywords()
      await loadOverlaps()
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to delete keyword')
    }
  }

  const getOverlapForKeyword = (keyword: string): KeywordOverlap | undefined => {
    return overlaps.find(o => o.keyword.toLowerCase() === keyword.toLowerCase())
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'medium':
        return 'text-orange-600 bg-orange-50 border-orange-200'
      case 'low':
        return 'text-green-600 bg-green-50 border-green-200'
      default:
        return 'text-neutral-600 bg-neutral-50 border-neutral-200'
    }
  }

  const getWeightBarWidth = (weight: number) => {
    // Weight range: 0.1 to 10.0, map to 10% to 100%
    return Math.min(100, Math.max(10, (weight / 10.0) * 100))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-neutral-500">Loading keywords...</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Keywords Table */}
      <div className="border border-neutral-200 rounded-md overflow-hidden">
        <div className="max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
          <thead className="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-neutral-700">Keyword</th>
              <th className="px-4 py-3 text-left font-medium text-neutral-700">Language</th>
              <th className="px-4 py-3 text-left font-medium text-neutral-700">Weight</th>
              <th className="px-4 py-3 text-center font-medium text-neutral-700">Matches</th>
              <th className="px-4 py-3 text-center font-medium text-neutral-700">Type</th>
              <th className="px-4 py-3 text-center font-medium text-neutral-700">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200">
            {keywords.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-neutral-500">
                  No keywords yet. Add your first keyword to improve document classification.
                </td>
              </tr>
            ) : (
              keywords.map((kw) => {
                const overlap = getOverlapForKeyword(kw.keyword)
                return (
                  <tr key={kw.id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <div>
                        <div className="font-medium text-neutral-900">{kw.keyword}</div>
                        {overlap && (
                          <div className={`mt-1 inline-flex items-center px-2 py-0.5 rounded text-xs border ${getSeverityColor(overlap.severity)}`}>
                            ⚠ Used in {overlap.category_count} categories ({overlap.severity} risk)
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-neutral-100 text-neutral-700 uppercase">
                        {kw.language_code}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <input
                          type="range"
                          min="0.1"
                          max="10.0"
                          step="0.1"
                          value={kw.weight}
                          onChange={(e) => handleUpdateWeight(kw.id, parseFloat(e.target.value))}
                          className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer"
                          style={{
                            background: `linear-gradient(to right, #4f46e5 0%, #4f46e5 ${getWeightBarWidth(kw.weight)}%, #e5e7eb ${getWeightBarWidth(kw.weight)}%, #e5e7eb 100%)`
                          }}
                        />
                        <div className="text-xs text-neutral-500 text-center">{kw.weight.toFixed(1)}</div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center text-neutral-600">
                      {kw.match_count}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                        kw.is_system_default
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-neutral-100 text-neutral-700'
                      }`}>
                        {kw.is_system_default ? 'System' : 'Custom'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleDeleteKeyword(kw.id, kw.is_system_default)}
                        disabled={kw.is_system_default}
                        className={`text-sm ${
                          kw.is_system_default
                            ? 'text-neutral-400 cursor-not-allowed'
                            : 'text-red-600 hover:text-red-700'
                        }`}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
        </div>
      </div>

      {/* Add Keyword Section */}
      {!adding ? (
        <Button
          type="button"
          variant="secondary"
          onClick={() => setAdding(true)}
          className="w-full"
        >
          + Add Keyword
        </Button>
      ) : (
        <div className="border border-neutral-200 rounded-md p-4 bg-neutral-50 space-y-3">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Keyword
            </label>
            <input
              type="text"
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              placeholder="e.g., insurance, policy, premium"
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Weight (0.1 - 10.0)
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="range"
                min="0.1"
                max="10.0"
                step="0.1"
                value={newWeight}
                onChange={(e) => setNewWeight(parseFloat(e.target.value))}
                className="flex-1 h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer"
              />
              <span className="text-sm text-neutral-600 font-medium w-12 text-right">
                {newWeight.toFixed(1)}
              </span>
            </div>
          </div>

          <div className="flex justify-end space-x-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setAdding(false)
                setNewKeyword('')
                setNewWeight(1.0)
                setError(null)
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={handleAddKeyword}
            >
              Add Keyword
            </Button>
          </div>
        </div>
      )}

      {/* Help Text */}
      <div className="text-xs text-neutral-500 space-y-1">
        <p>• Higher weights (5.0-10.0) make keywords more important for classification</p>
        <p>• Lower weights (0.1-0.5) reduce keyword importance without deleting</p>
        <p>• System keywords cannot be deleted but weights can be adjusted</p>
        <p>• Overlap warnings help avoid ambiguous classification</p>
      </div>
    </div>
  )
}
