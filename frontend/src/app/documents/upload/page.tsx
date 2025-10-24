// frontend/src/app/documents/upload/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import { Card, CardHeader, CardContent, Button, Alert, Badge, Input } from '@/components/ui'
import { categoryService, type Category } from '@/services/category.service'
import { DocumentAnalysisProgress } from '@/components/DocumentAnalysisProgress'
import AppHeader from '@/components/AppHeader'

interface ErrorResponse {
  detail?: string
  message?: string
  [key: string]: unknown
}

interface FileAnalysisSuccess {
  success: true
  temp_id: string
  original_filename: string
  standardized_filename: string
  analysis: {
    keywords?: Array<{word: string, count: number, relevance: number}>
    suggested_category_id: string | null
    confidence: number
    detected_language?: string
  }
  batch_id: string
}

interface FileAnalysisFailure {
  success: false
  original_filename: string
  error: string
  batch_id: string
}

type FileAnalysisResult = FileAnalysisSuccess | FileAnalysisFailure

interface FileUploadState extends FileAnalysisSuccess {
  file: File
  selected_categories: string[]
  primary_category: string | null
  confirmed_keywords: string[]
  custom_filename: string
  filename_error: string | null
}

export default function BatchUploadPage() {
  const router = useRouter()
  useAuth() // Ensure user is authenticated
  
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisComplete, setAnalysisComplete] = useState(false)
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
        credentials: 'include'  // Send httpOnly cookies
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
    setAnalysisComplete(false)
    setMessage(null)

    try {
      const formData = new FormData()
      selectedFiles.forEach(file => {
        formData.append('files', file)
      })

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/document-analysis/analyze-batch`, {
        method: 'POST',
        credentials: 'include',  // Send httpOnly cookies
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
        } catch {
          try {
            const errorText = await response.text()
            errorDetail = errorText || `HTTP ${response.status}: ${response.statusText}`
          } catch {
            errorDetail = `HTTP ${response.status}: Unable to read error response`
          }
        }
        throw new Error(errorDetail)
      }

      const result = await response.json()

      // Filter out failed analyses and show errors
      const failedFiles = result.results.filter((r: FileAnalysisResult): r is FileAnalysisFailure => !r.success)
      if (failedFiles.length > 0) {
        const errorMessages = failedFiles.map((f: FileAnalysisFailure) => `${f.original_filename}: ${f.error}`).join('; ')
        console.error('Some files failed analysis:', errorMessages)
        setMessage({
          type: 'error',
          text: `${failedFiles.length} file(s) failed analysis: ${errorMessages}`
        })
      }

      // Build upload states only for successful analyses
      const states: FileUploadState[] = result.results
        .filter((r: FileAnalysisResult): r is FileAnalysisSuccess => r.success)
        .map((r: FileAnalysisSuccess) => ({
          ...r,
          file: selectedFiles.find(f => f.name === r.original_filename)!,
          selected_categories: r.analysis.suggested_category_id ? [r.analysis.suggested_category_id] : [],
          primary_category: r.analysis.suggested_category_id,
          confirmed_keywords: (r.analysis?.keywords && Array.isArray(r.analysis.keywords))
            ? r.analysis.keywords
                .slice(0, 10)
                .filter(k => {
                  return k !== null &&
                         k !== undefined &&
                         typeof k === 'object' &&
                         k.word !== null &&
                         k.word !== undefined &&
                         typeof k.word === 'string' &&
                         k.word.trim().length > 0
                })
                .map(k => k.word.trim())
            : [],
          custom_filename: r.standardized_filename || r.original_filename || 'untitled',
          filename_error: null
        }))

      setUploadStates(states)

      // Only show success message if there are successful analyses
      if (states.length > 0) {
        setMessage({
          type: failedFiles.length > 0 ? 'error' : 'success',
          text: failedFiles.length > 0
            ? `Analyzed ${result.successful}/${result.total_files} files successfully. ${failedFiles.length} failed.`
            : `Analyzed ${result.successful}/${result.total_files} files successfully`
        })
      }

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
      // Signal completion before hiding the progress indicator
      setAnalysisComplete(true)

      // Small delay to show 100% completion before transitioning
      setTimeout(() => {
        setAnalyzing(false)
      }, 500)
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
      
      // If removing primary, set new primary to first remaining
      if (state.primary_category === categoryId && newCategories.length > 0) {
        updateFileState(fileIndex, {
          selected_categories: newCategories,
          primary_category: newCategories[0]
        })
        return
      }
    } else {
      // Add category (no limit)
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
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900">
      <AppHeader title="Upload Documents" subtitle="Add new documents to your collection" />

      <div className="max-w-6xl mx-auto p-8">
        <Card>
          <CardHeader title="Document Upload" />
          
          <CardContent>
            {message && (
              <Alert type={message.type} message={message.text} />
            )}

            {/* Show progress indicator while analyzing */}
            {analyzing ? (
              <DocumentAnalysisProgress
                fileCount={selectedFiles.length}
                onComplete={analysisComplete}
              />
            ) : uploadStates.length === 0 ? (
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
                  {uploadStates.map((state, index) => {
                    return (
                    <Card key={index} className="p-4">
                      <div className="space-y-4">
                        {/* Header */}
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h3 className="font-semibold text-neutral-900 dark:text-neutral-100">{state.original_filename}</h3>
                            <p className="text-sm text-neutral-600 dark:text-neutral-400">
                              {state.analysis?.detected_language?.toUpperCase() || 'Unknown'} •
                              {(state.analysis?.keywords && Array.isArray(state.analysis.keywords)) ? state.analysis.keywords.length : 0} keywords
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
                                  {(state.custom_filename || '').length}/{maxFilenameLength}
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Categories multiple selection */}
                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                            Categories (select at least 1)
                          </label>
                          {state.selected_categories.length === 0 && (
                            <p className="text-sm text-red-600 dark:text-red-400">
                              Select at least one category
                            </p>
                          )}
                          
                          {/* Selected Categories */}
                          {state.selected_categories.length > 0 && (
                            <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                              <p className="text-xs font-medium text-blue-900 dark:text-blue-300 mb-2">
                                Selected ({state.selected_categories.length})
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {state.selected_categories.map(catId => {
                                  const cat = categories.find(c => c.id === catId)
                                  if (!cat || !cat.name || typeof cat.name !== 'string') {
                                    return null
                                  }
                                  const isPrimary = state.primary_category === catId

                                  return (
                                    <Badge
                                      key={catId}
                                      variant={isPrimary ? "info" : "default"}
                                      className="flex items-center gap-2 px-3 py-1"
                                    >
                                      <span>{cat.name}</span>
                                      {isPrimary && <span className="text-xs">(Primary)</span>}
                                      <button
                                        onClick={() => toggleCategory(index, catId)}
                                        className="ml-1 hover:text-red-600"
                                      >
                                        ×
                                      </button>
                                    </Badge>
                                  )
                                })}
                              </div>
                            </div>
                          )}
                          
                          {/* Category Search/List */}
                          <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg max-h-60 overflow-y-auto">
                            <div className="divide-y divide-neutral-200 dark:divide-neutral-700">
                              {categories.map((category, catIdx) => {
                                // Validate category data
                                if (!category || typeof category !== 'object' || !category.id || typeof category.id !== 'string' || !category.name || typeof category.name !== 'string') {
                                  return null
                                }

                                const isSelected = state.selected_categories.includes(category.id)
                                const isPrimary = state.primary_category === category.id

                                return (
                                  <div
                                    key={category.id}
                                    className={`
                                      p-3 hover:bg-neutral-50 dark:hover:bg-neutral-800 cursor-pointer
                                      ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : ''}
                                    `}
                                    onClick={() => toggleCategory(index, category.id)}
                                  >
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-3 flex-1">
                                        <input
                                          type="checkbox"
                                          checked={isSelected}
                                          onChange={() => {}}
                                          className="w-4 h-4 rounded"
                                        />
                                        <div className="flex-1">
                                          <div className="flex items-center gap-2">
                                            <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                                              {category.name}
                                            </span>
                                            {isPrimary && (
                                              <Badge variant="info" className="text-xs">Primary</Badge>
                                            )}
                                          </div>
                                          {category.description && (
                                            <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
                                              {category.description}
                                            </p>
                                          )}
                                        </div>
                                      </div>
                                      
                                      {isSelected && !isPrimary && (
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            updateFileState(index, {primary_category: category.id})
                                          }}
                                          className="text-xs text-primary-600 dark:text-primary-400 hover:underline px-2"
                                        >
                                          Set as primary
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        </div>

                        {/* Keywords */}
                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                            Keywords
                          </label>
                          {(state.confirmed_keywords && Array.isArray(state.confirmed_keywords) && state.confirmed_keywords.length > 0) ? (
                            <div className="flex flex-wrap gap-2">
                              {state.confirmed_keywords
                                .filter(keyword => keyword && typeof keyword === 'string' && keyword.trim().length > 0)
                                .map((keyword, kidx) => (
                                  <Badge
                                    key={kidx}
                                    variant="default"
                                    className="flex items-center gap-1"
                                  >
                                    {keyword}
                                    <button
                                      onClick={() => {
                                        const newKeywords = (state.confirmed_keywords || []).filter(kw => kw !== keyword)
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
                    )
                  })}
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