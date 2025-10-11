// frontend/src/app/documents/upload/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/use-auth'
import { Card, CardHeader, CardContent, Button, Alert, Badge, Input } from '@/components/ui'
import { categoryService, type Category } from '@/services/category.service'

interface ErrorResponse {
  detail?: string
  message?: string
  [key: string]: unknown
}

interface FileAnalysis {
  success: boolean
  temp_id: string
  original_filename: string
  standardized_filename: string
  analysis: {
    keywords: Array<{word: string, count: number, relevance: number}>
    suggested_category_id: string | null
    confidence: number
    detected_language: string
  }
  batch_id: string
}

interface FileUploadState extends FileAnalysis {
  file: File
  selected_categories: string[]
  primary_category: string | null
  confirmed_keywords: string[]
  custom_filename: string
  filename_error: string | null
}

export default function BatchUploadPage() {
  const router = useRouter()
  const { isLoading } = useAuth()
  
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [uploadStates, setUploadStates] = useState<FileUploadState[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null)
  const [maxFilenameLength, setMaxFilenameLength] = useState(200)

  useEffect(() => {
    loadCategories()
    loadConfig()
  }, [])

  const loadCategories = async () => {
    try {
      const data = await categoryService.listCategories()
      setCategories(data.categories)
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  const loadConfig = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/settings/max_filename_length`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
      })
      if (response.ok) {
        const data = await response.json()
        setMaxFilenameLength(data.value)
      }
    } catch (error) {
      console.error('Failed to load config:', error)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files))
    }
  }

  const handleAnalyzeBatch = async () => {
    if (selectedFiles.length === 0) {
      setMessage({type: 'error', text: 'Please select files first'})
      return
    }

    setAnalyzing(true)
    setMessage(null)

    try {
      const formData = new FormData()
      selectedFiles.forEach(file => {
        formData.append('files', file)
      })

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/document-analysis/analyze-batch`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: formData
      })

      if (!response.ok) {
        let errorDetail = 'Analysis failed'
        try {
          const errorData = await response.json() as ErrorResponse
          // Better error serialization
          if (typeof errorData === 'object' && errorData !== null) {
            if (errorData.detail && typeof errorData.detail === 'string') {
              errorDetail = errorData.detail
            } else if (errorData.message && typeof errorData.message === 'string') {
              errorDetail = errorData.message
            } else if (Array.isArray(errorData.detail)) {
              // Handle validation errors from FastAPI
              errorDetail = errorData.detail.map((err: { loc?: string[]; msg: string }) => 
                `${err.loc?.join('.')}: ${err.msg}`
              ).join('; ')
            } else {
              errorDetail = `Server error (${response.status}): ${JSON.stringify(errorData)}`
            }
          }
        } catch (jsonError) {
          try {
            const errorText = await response.text()
            errorDetail = errorText || `HTTP ${response.status}: ${response.statusText}`
          } catch (textError) {
            errorDetail = `HTTP ${response.status}: Unable to read error response`
          }
        }
        throw new Error(errorDetail)
      }

      const result = await response.json()
      
      // Build upload states
      const states: FileUploadState[] = result.results.map((r: FileAnalysis) => ({
        ...r,
        file: selectedFiles.find(f => f.name === r.original_filename)!,
        selected_categories: r.analysis.suggested_category_id ? [r.analysis.suggested_category_id] : [],
        primary_category: r.analysis.suggested_category_id,
        confirmed_keywords: r.analysis.keywords.slice(0, 10).map(k => k.word),
        custom_filename: r.standardized_filename,
        filename_error: null
      }))

      setUploadStates(states)
      setMessage({
        type: 'success',
        text: `Analyzed ${result.successful}/${result.total_files} files successfully`
      })

    } catch (error) {
      console.error('Batch analysis error:', error)
      let errorMessage = 'Analysis failed. Please try again.'
      
      if (error instanceof Error) {
        errorMessage = error.message
      } else if (typeof error === 'object' && error !== null) {
        const errorObj = error as ErrorResponse
        errorMessage = errorObj.detail || errorObj.message || JSON.stringify(error)
      }
      
      setMessage({
        type: 'error',
        text: errorMessage
      })
    } finally {
      setAnalyzing(false)
    }
  }

  const updateFileState = (index: number, updates: Partial<FileUploadState>) => {
    setUploadStates(prev => prev.map((state, i) => 
      i === index ? {...state, ...updates} : state
    ))
  }

  const toggleCategory = (fileIndex: number, categoryId: string) => {
    const state = uploadStates[fileIndex]
    const isSelected = state.selected_categories.includes(categoryId)
    
    let newCategories: string[]
    if (isSelected) {
      // Remove category
      newCategories = state.selected_categories.filter(id => id !== categoryId)
      
      // If removing primary, set new primary
      if (state.primary_category === categoryId && newCategories.length > 0) {
        updateFileState(fileIndex, {
          selected_categories: newCategories,
          primary_category: newCategories[0]
        })
        return
      }
    } else {
      // Add category
      newCategories = [...state.selected_categories, categoryId]
      
      // If first category, make it primary
      if (newCategories.length === 1) {
        updateFileState(fileIndex, {
          selected_categories: newCategories,
          primary_category: categoryId
        })
        return
      }
    }
    
    updateFileState(fileIndex, {selected_categories: newCategories})
  }

  const validateFilename = (filename: string): string | null => {
    if (filename.length === 0) {
      return 'Filename cannot be empty'
    }
    if (filename.length > maxFilenameLength) {
      return `Filename too long (max ${maxFilenameLength} chars)`
    }
    if (!/^[a-zA-Z0-9_\-. ]+$/.test(filename)) {
      return 'Invalid characters in filename'
    }
    return null
  }

  const handleFilenameChange = (fileIndex: number, newFilename: string) => {
    const error = validateFilename(newFilename)
    updateFileState(fileIndex, {
      custom_filename: newFilename,
      filename_error: error
    })
  }

  const handleConfirmAll = async () => {
    // Validate all files
    const invalid = uploadStates.filter(s => 
      s.selected_categories.length === 0 || s.filename_error !== null
    )
    
    if (invalid.length > 0) {
      setMessage({
        type: 'error',
        text: `${invalid.length} files have validation errors`
      })
      return
    }

    try {
      setMessage(null)
      
      // Upload all files
      const uploads = uploadStates.map(state => 
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/document-analysis/confirm-upload`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            temp_id: state.temp_id,
            title: state.custom_filename.replace(/\.[^/.]+$/, ''), // Remove extension
            description: null,
            category_ids: state.selected_categories,
            primary_category_id: state.primary_category,
            confirmed_keywords: state.confirmed_keywords
          })
        })
      )

      const results = await Promise.all(uploads)
      const successful = results.filter(r => r.ok).length

      setMessage({
        type: 'success',
        text: `Uploaded ${successful}/${uploadStates.length} documents successfully!`
      })

      setTimeout(() => {
        router.push('/documents')
      }, 2000)

    } catch (error) {
      console.error('Batch upload error:', error)
      setMessage({
        type: 'error',
        text: 'Upload failed. Please try again.'
      })
    }
  }

  const removeFile = (index: number) => {
    setUploadStates(prev => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 p-8">
      <div className="max-w-6xl mx-auto">
        <Card>
          <CardHeader title="Upload Documents" />
          
          <CardContent>
            {message && (
              <Alert type={message.type} message={message.text} />
            )}

            {uploadStates.length === 0 ? (
              <>
                {/* File Selection */}
                <div className="border-2 border-dashed border-admin-primary/30 hover:border-admin-primary/60 dark:border-admin-primary/40 dark:hover:border-admin-primary/70 rounded-xl p-12 bg-gradient-to-br from-white to-neutral-50 dark:from-neutral-800 dark:to-neutral-900 transition-all duration-200 hover:shadow-lg">
                  <input
                    type="file"
                    multiple
                    onChange={handleFileSelect}
                    accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                    className="hidden"
                    id="files-input"
                  />
                  <label htmlFor="files-input" className="cursor-pointer block">
                    {selectedFiles.length > 0 ? (
                      <div className="space-y-4">
                        <div className="flex items-center justify-center mb-4">
                          <div className="h-16 w-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                            <svg className="h-8 w-8 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        </div>
                        <p className="font-semibold text-lg text-neutral-900 dark:text-neutral-100">{selectedFiles.length} {selectedFiles.length === 1 ? 'file' : 'files'} selected</p>
                        <div className="flex flex-wrap gap-2 justify-center max-w-2xl mx-auto">
                          {selectedFiles.map((file, i) => (
                            <Badge key={i} variant="default" className="text-sm py-1.5 px-3">
                              {file.name}
                            </Badge>
                          ))}
                        </div>
                        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-4">Click to select different files</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="flex items-center justify-center mb-4">
                          <div className="h-20 w-20 rounded-full bg-admin-primary/10 dark:bg-admin-primary/20 flex items-center justify-center">
                            <svg className="h-10 w-10 text-admin-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                          </div>
                        </div>
                        <div className="text-center">
                          <p className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                            Drop your files here
                          </p>
                          <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                            or click to browse from your computer
                          </p>
                          <p className="text-sm text-neutral-500 dark:text-neutral-500">
                            Supported formats: PDF, DOC, DOCX, JPG, PNG • Max 50MB per file
                          </p>
                        </div>
                      </div>
                    )}
                  </label>
                </div>

                <Button
                  onClick={handleAnalyzeBatch}
                  disabled={selectedFiles.length === 0 || analyzing}
                  className="w-full"
                >
                  {analyzing ? 'Analyzing...' : `Analyze ${selectedFiles.length} File${selectedFiles.length !== 1 ? 's' : ''}`}
                </Button>
              </>
            ) : (
              <>
                {/* File Review Cards */}
                <div className="space-y-4">
                  {uploadStates.map((state, index) => (
                    <Card key={index} className="p-4">
                      <div className="space-y-4">
                        {/* Header */}
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h3 className="font-semibold text-neutral-900 dark:text-neutral-100">{state.original_filename}</h3>
                            <p className="text-sm text-neutral-600 dark:text-neutral-400">
                              {state.analysis.detected_language.toUpperCase()} • 
                              {state.analysis.keywords.length} keywords
                            </p>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFile(index)}
                          >
                            Remove
                          </Button>
                        </div>

                        {/* Filename Preview */}
                        <div className="space-y-2">
                          <div className="flex items-start space-x-2">
                            <div className="flex-1">
                              <Input
                                label="New Filename"
                                value={state.custom_filename}
                                onChange={(e) => handleFilenameChange(index, e.target.value)}
                                error={state.filename_error || undefined}
                              />
                              <div className="flex justify-between items-center mt-1">
                                <p className="text-xs text-neutral-600 dark:text-neutral-400">
                                  Original: {state.original_filename}
                                </p>
                                <p className="text-xs text-neutral-500 dark:text-neutral-400">
                                  {state.custom_filename.length}/{maxFilenameLength}
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Categories (select 1-5) */}
                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                            Categories (select 1-5)
                          </label>
                          {state.selected_categories.length === 0 && (
                            <p className="text-sm text-red-600 dark:text-red-400">
                              Select at least one category
                            </p>
                          )}
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                            {categories.map(category => {
                              const isSelected = state.selected_categories.includes(category.id)
                              const isPrimary = state.primary_category === category.id
                              const canSelect = isSelected || state.selected_categories.length < 5
                              
                              return (
                                <button
                                  key={category.id}
                                  onClick={() => canSelect && toggleCategory(index, category.id)}
                                  disabled={!canSelect && !isSelected}
                                  className={`
                                    p-3 rounded-lg border-2 text-left transition-all
                                    ${isSelected 
                                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' 
                                      : 'border-neutral-200 dark:border-neutral-700 hover:border-primary-300'
                                    }
                                    ${!canSelect && !isSelected ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                                    ${isPrimary ? 'ring-2 ring-primary-500' : ''}
                                  `}
                                >
                                  <div className="flex items-center justify-between">
                                    <span className="font-medium text-sm">{category.name}</span>
                                    {isPrimary && (
                                      <Badge variant="default" className="text-xs">Primary</Badge>
                                    )}
                                  </div>
                                  {isSelected && !isPrimary && (
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        updateFileState(index, {primary_category: category.id})
                                      }}
                                      className="text-xs text-primary-600 dark:text-primary-400 hover:underline mt-1"
                                    >
                                      Make primary
                                    </button>
                                  )}
                                </button>
                              )
                            })}
                          </div>
                        </div>

                        {/* Keywords */}
                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                            Keywords
                          </label>
                          {state.confirmed_keywords.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                              {state.confirmed_keywords.map((keyword, kidx) => (
                                <Badge
                                  key={kidx}
                                  variant="default"
                                  className="flex items-center gap-1"
                                >
                                  {keyword}
                                  <button
                                    onClick={() => {
                                      const newKeywords = state.confirmed_keywords.filter((_, i) => i !== kidx)
                                      updateFileState(index, {confirmed_keywords: newKeywords})
                                    }}
                                    className="ml-1 hover:text-red-600"
                                  >
                                    ×
                                  </button>
                                </Badge>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-neutral-500 dark:text-neutral-400">
                              No keywords extracted
                            </p>
                          )}
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>

                {/* Batch Actions */}
                <div className="flex space-x-4">
                  <Button
                    onClick={handleConfirmAll}
                    className="flex-1"
                  >
                    Upload All {uploadStates.length} Documents
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setUploadStates([])}
                  >
                    Cancel
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}