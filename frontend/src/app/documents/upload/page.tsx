// frontend/src/app/documents/upload/page.tsx - UPDATED FOR AI ANALYSIS FLOW
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/use-auth'
import { Card, CardHeader, CardContent, Button, Alert } from '@/components/ui'

const MAX_FILE_SIZE = 100 * 1024 * 1024
const ALLOWED_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/jpg',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/plain'
]

export default function DocumentUploadPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  
  const [mounted, setMounted] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisProgress, setAnalysisProgress] = useState(0)
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
      setMessage({ type: 'error', text: 'File type not supported. Allowed: PDF, Images, Word, Excel, Text' })
      return
    }

    setSelectedFile(file)
    setMessage(null)
  }

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setMessage({ type: 'error', text: 'Please select a file first' })
      return
    }

    setAnalyzing(true)
    setMessage(null)
    setAnalysisProgress(0)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      // Simulate progress
      const progressInterval = setInterval(() => {
        setAnalysisProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 300)

      const accessToken = localStorage.getItem('access_token')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/analyze`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        body: formData
      })

      clearInterval(progressInterval)
      setAnalysisProgress(100)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Analysis failed')
      }

      const result = await response.json()
      
      // Redirect to review page with temp_id
      setTimeout(() => {
        router.push(`/documents/upload/review?temp_id=${result.temp_id}`)
      }, 500)

    } catch (err) {
      console.error('Analysis error:', err)
      
      let errorMessage = 'Failed to analyze document'
      
      if (err && typeof err === 'object') {
        const apiError = err as {
          response?: {
            data?: {
              detail?: string
            }
          }
          message?: string
          detail?: string
        }
        
        if (apiError.response?.data?.detail) {
          errorMessage = apiError.response.data.detail
        } else if (apiError.message) {
          errorMessage = apiError.message
        } else if (typeof apiError.detail === 'string') {
          errorMessage = apiError.detail
        }
      }
      
      setMessage({ 
        type: 'error', 
        text: errorMessage
      })
      setAnalysisProgress(0)
    } finally {
      setAnalyzing(false)
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
              <p className="text-sm text-neutral-600">AI will analyze and suggest category</p>
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
          {/* File Selection */}
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
                  disabled={analyzing}
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
                    {!analyzing && (
                      <label
                        htmlFor="file-upload"
                        className="inline-flex cursor-pointer text-sm text-admin-primary hover:text-admin-primary/80"
                      >
                        Change file
                      </label>
                    )}
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
                      PDF, Images, Word, Excel, Text (max 100MB)
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* How It Works */}
          <Card>
            <CardHeader title="How It Works" />
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 h-6 w-6 rounded-full bg-admin-primary text-white flex items-center justify-center text-sm font-medium">
                    1
                  </div>
                  <div>
                    <p className="font-medium text-neutral-900">Upload Document</p>
                    <p className="text-sm text-neutral-600">Select your file (PDF, images, documents)</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 h-6 w-6 rounded-full bg-admin-primary text-white flex items-center justify-center text-sm font-medium">
                    2
                  </div>
                  <div>
                    <p className="font-medium text-neutral-900">AI Analysis</p>
                    <p className="text-sm text-neutral-600">Extract text, keywords, and suggest category</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 h-6 w-6 rounded-full bg-admin-primary text-white flex items-center justify-center text-sm font-medium">
                    3
                  </div>
                  <div>
                    <p className="font-medium text-neutral-900">Review & Confirm</p>
                    <p className="text-sm text-neutral-600">Verify or edit AI suggestions before saving</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Analysis Progress */}
          {analyzing && (
            <Card>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-neutral-700">Analyzing document...</span>
                    <span className="text-neutral-900 font-medium">{analysisProgress}%</span>
                  </div>
                  <div className="w-full bg-neutral-200 rounded-full h-2">
                    <div
                      className="bg-admin-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${analysisProgress}%` }}
                    />
                  </div>
                  <p className="text-xs text-neutral-600 text-center">
                    Extracting text, analyzing content, and detecting keywords...
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3">
            <Link href="/documents">
              <Button variant="secondary" disabled={analyzing}>
                Cancel
              </Button>
            </Link>
            <Button
              onClick={handleAnalyze}
              disabled={!selectedFile || analyzing}
            >
              {analyzing ? 'Analyzing...' : 'Analyze Document'}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}