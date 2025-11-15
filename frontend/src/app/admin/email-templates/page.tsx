// frontend/src/app/admin/email-templates/page.tsx
/**
 * Bonifatus DMS - Email Template Management
 * Admin page for managing transactional email templates
 */

'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import AppHeader from '@/components/AppHeader'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { apiClient } from '@/services/api-client'

interface EmailTemplate {
  id: string
  template_key: string
  language: string
  subject: string
  html_content: string
  variables: string[] | null
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function EmailTemplatesAdmin() {
  const { user, isLoading, loadUser } = useAuth()
  const router = useRouter()

  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [filteredTemplates, setFilteredTemplates] = useState<EmailTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTemplate, setSelectedTemplate] = useState<EmailTemplate | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // Filters
  const [filterLanguage, setFilterLanguage] = useState<string>('all')
  const [filterActive, setFilterActive] = useState<string>('all')

  // Form state
  const [formData, setFormData] = useState({
    subject: '',
    html_content: '',
    description: '',
    is_active: true
  })

  // Load user on mount
  useEffect(() => {
    loadUser()
  }, [loadUser])

  // Check admin access
  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login')
      return
    }

    if (!isLoading && user && !user.is_admin) {
      router.push('/dashboard')
      return
    }

    if (!isLoading && user && user.is_admin) {
      loadTemplates()
    }
  }, [user, isLoading])

  // Filter templates
  useEffect(() => {
    let filtered = templates

    if (filterLanguage !== 'all') {
      filtered = filtered.filter(t => t.language === filterLanguage)
    }

    if (filterActive !== 'all') {
      filtered = filtered.filter(t =>
        filterActive === 'active' ? t.is_active : !t.is_active
      )
    }

    setFilteredTemplates(filtered)
  }, [templates, filterLanguage, filterActive])

  const loadTemplates = async () => {
    try {
      setLoading(true)
      const data = await apiClient.get<{ templates: EmailTemplate[] }>('/api/v1/admin/email-templates')
      setTemplates(data.templates || [])
    } catch (error) {
      console.error('Error loading templates:', error)
      setMessage({ type: 'error', text: 'Error loading email templates' })
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (template: EmailTemplate) => {
    setSelectedTemplate(template)
    setFormData({
      subject: template.subject,
      html_content: template.html_content,
      description: template.description || '',
      is_active: template.is_active
    })
    setIsEditing(true)
  }

  const handleSave = async () => {
    if (!selectedTemplate) return

    try {
      setIsSaving(true)
      setMessage(null)

      await apiClient.put(
        `/api/v1/admin/email-templates/${selectedTemplate.id}`,
        formData
      )

      setMessage({ type: 'success', text: 'Template updated successfully' })
      setIsEditing(false)
      setSelectedTemplate(null)
      await loadTemplates()
    } catch (error: any) {
      console.error('Error saving template:', error)
      const errorMessage = error?.message || error?.detail || 'Error saving template'
      setMessage({ type: 'error', text: errorMessage })
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    setSelectedTemplate(null)
    setFormData({
      subject: '',
      html_content: '',
      description: '',
      is_active: true
    })
  }

  // Get unique languages from templates
  const languages = Array.from(new Set(templates.map(t => t.language)))

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  if (!user.is_admin) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Email Templates</h1>
          <p className="mt-2 text-gray-600">
            Manage transactional email templates with multilingual support
          </p>
        </div>

        {/* Message */}
        {message && (
          <div className={`mb-6 p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {message.text}
          </div>
        )}

        {/* Filters */}
        <Card className="mb-6">
          <CardHeader>
            <h2 className="text-lg font-semibold">Filters</h2>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Language
                </label>
                <select
                  value={filterLanguage}
                  onChange={(e) => setFilterLanguage(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Languages</option>
                  {languages.map(lang => (
                    <option key={lang} value={lang}>{lang.toUpperCase()}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Status
                </label>
                <select
                  value={filterActive}
                  onChange={(e) => setFilterActive(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All</option>
                  <option value="active">Active Only</option>
                  <option value="inactive">Inactive Only</option>
                </select>
              </div>

              <div className="flex items-end">
                <Button
                  onClick={() => { setFilterLanguage('all'); setFilterActive('all') }}
                  variant="secondary"
                  className="w-full"
                >
                  Reset Filters
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Templates List */}
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold">
              Templates ({filteredTemplates.length})
            </h2>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-gray-500">Loading templates...</div>
            ) : filteredTemplates.length === 0 ? (
              <div className="text-center py-8 text-gray-500">No templates found</div>
            ) : (
              <div className="space-y-4">
                {filteredTemplates.map(template => (
                  <div
                    key={template.id}
                    className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">
                            {template.template_key}
                          </h3>
                          <Badge variant={template.is_active ? 'success' : 'secondary'}>
                            {template.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                          <Badge variant="info">{template.language.toUpperCase()}</Badge>
                        </div>

                        <p className="text-sm text-gray-600 mb-2">
                          <strong>Subject:</strong> {template.subject}
                        </p>

                        {template.description && (
                          <p className="text-sm text-gray-500 mb-2">
                            {template.description}
                          </p>
                        )}

                        {template.variables && template.variables.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            <span className="text-xs text-gray-500">Variables:</span>
                            {template.variables.map(v => (
                              <code
                                key={v}
                                className="text-xs bg-gray-100 px-2 py-1 rounded"
                              >
                                {`{{${v}}}`}
                              </code>
                            ))}
                          </div>
                        )}

                        <p className="text-xs text-gray-400 mt-2">
                          Last updated: {new Date(template.updated_at).toLocaleString()}
                        </p>
                      </div>

                      <Button
                        onClick={() => handleEdit(template)}
                        variant="primary"
                        size="sm"
                      >
                        Edit
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit Modal */}
        {isEditing && selectedTemplate && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Edit Template: {selectedTemplate.template_key} ({selectedTemplate.language.toUpperCase()})
                </h2>

                <div className="space-y-4">
                  {/* Subject */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Subject *
                    </label>
                    <input
                      type="text"
                      value={formData.subject}
                      onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Email subject line"
                    />
                  </div>

                  {/* HTML Content */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      HTML Content *
                    </label>
                    <textarea
                      value={formData.html_content}
                      onChange={(e) => setFormData({ ...formData, html_content: e.target.value })}
                      rows={15}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      placeholder="HTML email content with {{variable}} placeholders"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Use {`{{variable_name}}`} for dynamic content
                    </p>
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description
                    </label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      rows={2}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Template description for admins"
                    />
                  </div>

                  {/* Active Status */}
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="is_active"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                      Template is active
                    </label>
                  </div>
                </div>

                {/* Buttons */}
                <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                  <Button
                    onClick={handleCancel}
                    variant="secondary"
                    disabled={isSaving}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSave}
                    variant="primary"
                    disabled={isSaving || !formData.subject || !formData.html_content}
                  >
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
