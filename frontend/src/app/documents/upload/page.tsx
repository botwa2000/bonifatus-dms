// frontend/src/app/documents/upload/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/use-auth'
import { Card, CardHeader, CardContent, Button, Alert, Badge, Input } from '@/components/ui'
import { categoryService, type Category } from '@/services/category.service'

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
  const { isAuthenticated } = useAuth()
  
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
        const error = await response.json()
        throw new Error(error.detail || 'Analysis failed')
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
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Analysis failed'
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
                <div className="border-2 border-dashed border-neutral-300 dark:border-neutral-600 rounded-lg p-8 bg-white dark:bg-neutral-800">
                  <input
                    type="file"
                    multiple
                    onChange={handleFileSelect}
                    accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                    className="hidden"
                    id="files-input"
                  />
                  <label htmlFor="files-input" className="cursor-pointer block text-center">
                    {selectedFiles.length > 0 ? (
                      <div className="space-y-2">
                        <p className="font-medium">{selectedFiles.length} files selected</p>
                        <div className="flex flex-wrap gap-2 justify-center">
                          {selectedFiles.map((file, i) => (
                            <Badge key={i} variant="default">
                              {file.name}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-neutral-600 dark:text-neutral-300">
                        Click to select files or drag and drop
                      </p>
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

                        {/* Categories - Multiple Selection */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                            Categories (select 1-5)
                            {state.analysis.confidence > 0 && (
                              <Badge variant="info" className="ml-2">
                                AI: {state.analysis.confidence}% confident
                              </Badge>
                            )}
                          </label>
                          <div className="grid grid-cols-2 gap-2">
                            {categories.map(cat => {
                              const isSelected = state.selected_categories.includes(cat.id)
                              const isPrimary = state.primary_category === cat.id
                              
                              return (
                                <div
                                  key={cat.id}
                                  className={`flex items-center space-x-2 p-2 border rounded-md cursor-pointer ${
                                    isSelected 
                                      ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-600' 
                                      : 'border-neutral-200 dark:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-700'
                                  }`}
                                  onClick={() => toggleCategory(index, cat.id)}
                                >
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => toggleCategory(index, cat.id)}
                                    className="w-4 h-4 rounded border-gray-300"
                                  />
                                  <div className="flex-1">
                                    <div className="flex items-center space-x-2">
                                      <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{cat.name}</span>
                                      {isPrimary && (
                                        <Badge variant="default">Primary</Badge>
                                      )}
                                    </div>
                                  </div>
                                  {isSelected && !isPrimary && (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        updateFileState(index, {primary_category: cat.id})
                                      }}
                                    >
                                      Set Primary
                                    </Button>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                          {state.selected_categories.length === 0 && (
                            <p className="text-xs text-red-600 dark:text-red-400">Select at least one category</p>
                          )}
                        </div>

                        {/* Keywords */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Keywords</label>
                          <div className="flex flex-wrap gap-2">
                            {state.confirmed_keywords.map((keyword, i) => (
                              <Badge key={i} variant="default">
                              {keyword}
                            </Badge>
                            ))}
                          </div>
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