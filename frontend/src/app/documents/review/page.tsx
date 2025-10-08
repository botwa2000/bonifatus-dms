// frontend/src/app/documents/upload/review/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/use-auth'
import { apiClient } from '@/services/api-client'
import { Card, CardHeader, CardContent, Button, Input, Alert, Select, Badge } from '@/components/ui'

interface Category {
  id: string
  name: string
  color_hex: string
}

interface Keyword {
  word: string
  count: number
  relevance: number
}

interface AnalysisResult {
  extracted_text: string
  full_text_length: number
  keywords: Keyword[]
  suggested_category_id: string | null
  confidence: number
  detected_language: string
  file_info: {
    name: string
    size: number
    type: string
  }
}

export default function DocumentReviewPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { isAuthenticated, isLoading } = useAuth()
  
  const [tempId, setTempId] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selectedCategoryId, setSelectedCategoryId] = useState('')
  const [keywords, setKeywords] = useState<string[]>([])
  const [newKeyword, setNewKeyword] = useState('')
  
  const [confirming, setConfirming] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    const id = searchParams.get('temp_id')
    if (id) {
      setTempId(id)
      loadAnalysisResult(id)
    } else {
      setMessage({ type: 'error', text: 'No document to review' })
    }
    loadCategories()
  }, [searchParams])

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  const loadAnalysisResult = async (id: string) => {
    try {
      const response = await apiClient.get<any>(`/api/v1/documents/analyze/${id}`, true)
      setAnalysis(response.analysis)
      
      // Pre-fill form with AI suggestions
      const fileName = response.file_name || response.analysis.file_info.name
      const fileNameWithoutExt = fileName.substring(0, fileName.lastIndexOf('.')) || fileName
      setTitle(fileNameWithoutExt)
      
      if (response.analysis.suggested_category_id) {
        setSelectedCategoryId(response.analysis.suggested_category_id)
      }
      
      // Pre-fill keywords (top 10)
      const topKeywords = response.analysis.keywords
        .slice(0, 10)
        .map((k: Keyword) => k.word)
      setKeywords(topKeywords)
      
    } catch (error) {
      console.error('Failed to load analysis:', error)
      setMessage({ type: 'error', text: 'Failed to load document analysis. It may have expired.' })
    }
  }

  const loadCategories = async () => {
    try {
      const data = await apiClient.get<{ categories: Category[] }>('/api/v1/categories', true)
      setCategories(data.categories)
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  const handleAddKeyword = () => {
    if (newKeyword.trim() && !keywords.includes(newKeyword.trim().toLowerCase())) {
      setKeywords([...keywords, newKeyword.trim().toLowerCase()])
      setNewKeyword('')
    }
  }

  const handleRemoveKeyword = (keyword: string) => {
    setKeywords(keywords.filter(k => k !== keyword))
  }

  const handleConfirm = async () => {
    if (!title.trim()) {
      setMessage({ type: 'error', text: 'Please enter a document title' })
      return
    }

    if (!selectedCategoryId) {
      setMessage({ type: 'error', text: 'Please select a category' })
      return
    }

    setConfirming(true)
    setMessage(null)

    try {
      const response = await apiClient.post(
        '/api/v1/documents/confirm-upload',
        {
          temp_id: tempId,
          title: title.trim(),
          description: description.trim() || null,
          category_ids: [selectedCategoryId],
          confirmed_keywords: keywords
        },
        true
      )

      setMessage({ 
        type: 'success', 
        text: 'Document uploaded successfully!' 
      })

      setTimeout(() => {
        router.push('/documents')
      }, 2000)

    } catch (error: any) {
      console.error('Upload confirmation failed:', error)
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to confirm upload' 
      })
    } finally {
      setConfirming(false)
    }
  }

  const handleCancel = async () => {
    try {
      if (tempId) {
        await apiClient.delete(`/api/v1/documents/analyze/${tempId}`, true)
      }
    } catch (error) {
      console.error('Failed to cancel upload:', error)
    }
    router.push('/documents/upload')
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 80) return 'text-green-600'
    if (confidence >= 60) return 'text-yellow-600'
    return 'text-orange-600'
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center max-w-md">
          <p className="text-neutral-600 mb-4">No document analysis available</p>
          <Link href="/documents/upload">
            <Button>Back to Upload</Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="bg-white shadow-sm border-b border-neutral-200">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-4">
            <button onClick={handleCancel} className="text-neutral-600 hover:text-neutral-900">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">Review & Confirm Upload</h1>
              <p className="text-sm text-neutral-600">Review AI suggestions and confirm document details</p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        {message && (
          <div className="mb-6">
            <Alert type={message.type} message={message.text} />
          </div>
        )}

        <div className="space-y-6">
          {/* File Information */}
          <Card>
            <CardHeader title="File Information" />
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-neutral-600">File Name:</span>
                  <p className="font-medium text-neutral-900">{analysis.file_info.name}</p>
                </div>
                <div>
                  <span className="text-neutral-600">File Size:</span>
                  <p className="font-medium text-neutral-900">{formatFileSize(analysis.file_info.size)}</p>
                </div>
                <div>
                  <span className="text-neutral-600">Detected Language:</span>
                  <p className="font-medium text-neutral-900">{analysis.detected_language.toUpperCase()}</p>
                </div>
                <div>
                  <span className="text-neutral-600">Extracted Text:</span>
                  <p className="font-medium text-neutral-900">{analysis.full_text_length} characters</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* AI Suggested Category */}
          {analysis.suggested_category_id && (
            <Card>
              <CardHeader title="AI Suggestion" />
              <CardContent>
                <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                  <div>
                    <p className="text-sm text-neutral-600">Suggested Category</p>
                    <p className="font-medium text-neutral-900">
                      {categories.find(c => c.id === analysis.suggested_category_id)?.name || 'Unknown'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-neutral-600">Confidence</p>
                    <p className={`text-lg font-bold ${getConfidenceColor(analysis.confidence)}`}>
                      {analysis.confidence}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Document Details */}
          <Card>
            <CardHeader title="Document Details" />
            <CardContent>
              <Input
                label="Title *"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter document title"
                disabled={confirming}
              />

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description"
                  rows={3}
                  disabled={confirming}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-admin-primary"
                />
              </div>

              <Select
                label="Category *"
                value={selectedCategoryId}
                onChange={(e) => setSelectedCategoryId(e.target.value)}
                options={categories.map(cat => ({
                  value: cat.id,
                  label: cat.name
                }))}
                disabled={confirming}
              />
            </CardContent>
          </Card>

          {/* Keywords */}
          <Card>
            <CardHeader title="Keywords" />
            <CardContent>
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {keywords.map(keyword => (
                    <Badge
                      key={keyword}
                      variant="default"
                      className="cursor-pointer hover:bg-red-100"
                      onClick={() => !confirming && handleRemoveKeyword(keyword)}
                    >
                      {keyword}
                      {!confirming && (
                        <svg className="ml-1 h-3 w-3 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      )}
                    </Badge>
                  ))}
                </div>

                <div className="flex space-x-2">
                  <Input
                    value={newKeyword}
                    onChange={(e) => setNewKeyword(e.target.value)}
                    placeholder="Add custom keyword"
                    disabled={confirming}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddKeyword()}
                  />
                  <Button
                    variant="secondary"
                    onClick={handleAddKeyword}
                    disabled={!newKeyword.trim() || confirming}
                  >
                    Add
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Text Preview */}
          {analysis.extracted_text && (
            <Card>
              <CardHeader title="Extracted Text Preview" />
              <CardContent>
                <div className="max-h-60 overflow-y-auto bg-neutral-50 p-4 rounded-md border border-neutral-200">
                  <p className="text-sm text-neutral-700 whitespace-pre-wrap">
                    {analysis.extracted_text}
                    {analysis.full_text_length > 5000 && (
                      <span className="text-neutral-500 italic">
                        ... (showing first 5000 characters)
                      </span>
                    )}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3">
            <Button variant="secondary" onClick={handleCancel} disabled={confirming}>
              Cancel
            </Button>
            <Button onClick={handleConfirm} disabled={confirming || !title || !selectedCategoryId}>
              {confirming ? 'Uploading...' : 'Confirm & Upload'}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}