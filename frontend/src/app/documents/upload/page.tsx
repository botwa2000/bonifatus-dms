// frontend/src/app/documents/upload/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/use-auth'
import { apiClient } from '@/services/api-client'
import { Card, CardHeader, CardContent, Button, Input, Alert } from '@/components/ui'

interface Category {
  id: string
  name: string
  color_hex: string
  icon_name: string
}

interface UploadedDocument {
  id: string
  title: string
  file_name: string
  file_size: number
  web_view_link?: string
}

const MAX_FILE_SIZE = 100 * 1024 * 1024
const ALLOWED_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/jpg',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
]

export default function DocumentUploadPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [dragActive, setDragActive] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  useEffect(() => {
    if (isAuthenticated) {
      loadCategories()
    }
  }, [isAuthenticated])

  const loadCategories = async () => {
    try {
      const data = await apiClient.get<{ categories: Category[] }>('/api/v1/categories', true)
      setCategories(data.categories)
    } catch (error) {
      console.error('Failed to load categories:', error)
      setMessage({ type: 'error', text: 'Failed to load categories' })
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0])
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelection(e.target.files[0])
    }
  }

  const handleFileSelection = (file: File) => {
    if (file.size > MAX_FILE_SIZE) {
      setMessage({ type: 'error', text: 'File size exceeds 100MB limit' })
      return
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      setMessage({ type: 'error', text: 'File type not supported' })
      return
    }

    setSelectedFile(file)
    setMessage(null)
    
    if (!title) {
      const nameWithoutExt = file.name.substring(0, file.name.lastIndexOf('.')) || file.name
      setTitle(nameWithoutExt)
    }
  }

  const handleCategoryToggle = (categoryId: string) => {
    setSelectedCategories(prev => {
      if (prev.includes(categoryId)) {
        return prev.filter(id => id !== categoryId)
      } else {
        return [...prev, categoryId]
      }
    })
  }

  const handleUpload = async () => {
    if (!selectedFile || selectedCategories.length === 0) {
      setMessage({ type: 'error', text: 'Please select a file and at least one category' })
      return
    }

    setUploading(true)
    setMessage(null)
    setUploadProgress(0)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('title', title || selectedFile.name)
      formData.append('description', description || '')
      selectedCategories.forEach(catId => {
        formData.append('category_ids', catId)
      })

      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: formData
      })

      clearInterval(progressInterval)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const uploadedDoc: UploadedDocument = await response.json()
      setUploadProgress(100)
      
      setMessage({ 
        type: 'success', 
        text: `Document "${uploadedDoc.title}" uploaded successfully!` 
      })

      setTimeout(() => {
        router.push('/documents')
      }, 2000)

    } catch (error) {
      console.error('Upload error:', error)
      setMessage({ 
        type: 'error', 
        text: error instanceof Error ? error.message : 'Upload failed' 
      })
      setUploadProgress(0)
    } finally {
      setUploading(false)
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  if (isLoading || !mounted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-admin-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-sm text-neutral-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="bg-white shadow-sm border-b border-neutral-200">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-4">
            <Link href="/documents" className="text-neutral-600 hover:text-neutral-900">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">Upload Document</h1>
              <p className="text-sm text-neutral-600">Add files to your library</p>
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
          <Card>
            <CardHeader title="Select File" />
            <CardContent>
              <div
                className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive 
                    ? 'border-admin-primary bg-blue-50' 
                    : 'border-neutral-300 hover:border-neutral-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  id="file-upload"
                  className="hidden"
                  onChange={handleFileInput}
                  accept={ALLOWED_TYPES.join(',')}
                  disabled={uploading}
                />
                
                {selectedFile ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-center text-admin-primary">
                      <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-neutral-900">{selectedFile.name}</p>
                      <p className="text-xs text-neutral-500">{formatFileSize(selectedFile.size)}</p>
                    </div>
                    <label
                      htmlFor="file-upload"
                      className="inline-flex cursor-pointer text-sm text-admin-primary hover:text-admin-primary/80"
                    >
                      Change file
                    </label>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center justify-center text-neutral-400">
                      <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div>
                      <label
                        htmlFor="file-upload"
                        className="cursor-pointer text-sm font-medium text-admin-primary hover:text-admin-primary/80"
                      >
                        Click to upload
                      </label>
                      <span className="text-sm text-neutral-500"> or drag and drop</span>
                    </div>
                    <p className="text-xs text-neutral-500">
                      PDF, Images, Word, Excel (max 100MB)
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Document Details" />
            <CardContent>
              <Input
                label="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Document title"
                disabled={uploading}
              />
              
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Description <span className="text-neutral-500">(optional)</span>
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Document description"
                  rows={3}
                  disabled={uploading}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary disabled:bg-neutral-100 disabled:cursor-not-allowed"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Assign Categories" />
            <CardContent>
              <p className="text-sm text-neutral-600 mb-4">
                Select one or more categories for this document
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {categories.map((category) => (
                  <label
                    key={category.id}
                    className={`flex items-center space-x-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedCategories.includes(category.id)
                        ? 'border-admin-primary bg-blue-50'
                        : 'border-neutral-300 hover:border-neutral-400'
                    } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedCategories.includes(category.id)}
                      onChange={() => handleCategoryToggle(category.id)}
                      disabled={uploading}
                      className="h-4 w-4 text-admin-primary focus:ring-admin-primary border-neutral-300 rounded"
                    />
                    <div className="flex items-center space-x-2 flex-1">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: category.color_hex }}
                      />
                      <span className="text-sm font-medium text-neutral-900">
                        {category.name}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
              {categories.length === 0 && (
                <p className="text-sm text-neutral-500 text-center py-4">
                  No categories available. Please create categories first.
                </p>
              )}
            </CardContent>
          </Card>

          {uploading && (
            <Card>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-neutral-700">Uploading...</span>
                    <span className="text-neutral-900 font-medium">{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-neutral-200 rounded-full h-2">
                    <div
                      className="bg-admin-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="flex justify-end space-x-3">
            <Link href="/documents">
              <Button variant="secondary" disabled={uploading}>
                Cancel
              </Button>
            </Link>
            <Button
              onClick={handleUpload}
              disabled={!selectedFile || selectedCategories.length === 0 || uploading}
            >
              {uploading ? 'Uploading...' : 'Upload Document'}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}