'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import AppHeader from '@/components/AppHeader'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { apiClient } from '@/services/api-client'
import { logger } from '@/lib/logger'
import EmailHtmlEditor from '@/components/admin/EmailHtmlEditor'

interface Campaign {
  id: string
  name: string
  subject: string
  html_body?: string
  audience_filter: string
  status: string
  total_recipients: number
  sent_count: number
  failed_count: number
  sent_at: string | null
  completed_at: string | null
  created_at: string | null
  error_message: string | null
  schedule_enabled: boolean
  schedule_cron: string | null
  last_scheduled_run: string | null
}

interface CampaignSendRecord {
  id: string
  user_id: string
  user_email: string
  sent_at: string
  status: string
  error_message: string | null
}

interface RecipientCounts {
  count: number
  total_eligible: number
  already_sent: number
  new_recipients: number
  audience_filter: string
}

const AUDIENCE_OPTIONS = [
  { value: 'all', label: 'All Users' },
  { value: 'free', label: 'Free Tier' },
  { value: 'starter', label: 'Starter Tier' },
  { value: 'pro', label: 'Pro Tier' },
]

const SCHEDULE_OPTIONS = [
  { value: '', label: 'No Schedule' },
  { value: 'interval_days:1', label: 'Every day' },
  { value: 'interval_days:3', label: 'Every 3 days' },
  { value: 'interval_days:7', label: 'Every 7 days' },
  { value: 'weekday:monday', label: 'Every Monday' },
  { value: 'monthly_day:1', label: 'Every 1st of month' },
]

const STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
  draft: 'default',
  sending: 'warning',
  active: 'success',
  sent: 'success',
  failed: 'error',
  paused: 'info',
}

export default function CampaignsAdmin() {
  const { user, isLoading, loadUser } = useAuth()
  const router = useRouter()

  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Form state
  const [isEditing, setIsEditing] = useState(false)
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    subject: '',
    html_body: '',
    audience_filter: 'all',
  })

  // Preview / Send
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [previewSubject, setPreviewSubject] = useState('')
  const [showSendConfirm, setShowSendConfirm] = useState(false)
  const [recipientCounts, setRecipientCounts] = useState<RecipientCounts | null>(null)
  const [isSending, setIsSending] = useState(false)

  // Send history
  const [showSendHistory, setShowSendHistory] = useState(false)
  const [sendHistory, setSendHistory] = useState<CampaignSendRecord[]>([])
  const [sendHistoryTotal, setSendHistoryTotal] = useState(0)
  const [sendHistoryLoading, setSendHistoryLoading] = useState(false)
  const [sendHistoryCampaign, setSendHistoryCampaign] = useState<Campaign | null>(null)

  // Schedule
  const [showSchedule, setShowSchedule] = useState(false)
  const [scheduleCampaign, setScheduleCampaign] = useState<Campaign | null>(null)
  const [scheduleValue, setScheduleValue] = useState('')
  const [isSavingSchedule, setIsSavingSchedule] = useState(false)

  useEffect(() => {
    loadUser()
  }, [loadUser])

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
      loadCampaigns()
    }
  }, [user, isLoading])

  const loadCampaigns = async () => {
    try {
      setLoading(true)
      const data = await apiClient.get<{ campaigns: Campaign[] }>('/api/v1/admin/campaigns')
      setCampaigns(data.campaigns || [])
    } catch (error) {
      logger.error('Error loading campaigns:', error)
      setMessage({ type: 'error', text: 'Error loading campaigns' })
    } finally {
      setLoading(false)
    }
  }

  const handleNew = () => {
    setSelectedCampaign(null)
    setFormData({ name: '', subject: '', html_body: '', audience_filter: 'all' })
    setIsEditing(true)
  }

  const handleEdit = async (campaign: Campaign) => {
    try {
      const full = await apiClient.get<Campaign>(`/api/v1/admin/campaigns/${campaign.id}`)
      setSelectedCampaign(full)
      setFormData({
        name: full.name,
        subject: full.subject,
        html_body: full.html_body || '',
        audience_filter: full.audience_filter,
      })
      setIsEditing(true)
    } catch (error) {
      logger.error('Error loading campaign details:', error)
      setMessage({ type: 'error', text: 'Error loading campaign' })
    }
  }

  const handleSave = async () => {
    if (!formData.name || !formData.subject || !formData.html_body) return
    setIsSaving(true)
    setMessage(null)

    try {
      if (selectedCampaign) {
        await apiClient.put(`/api/v1/admin/campaigns/${selectedCampaign.id}`, formData)
        setMessage({ type: 'success', text: 'Campaign updated' })
      } else {
        await apiClient.post('/api/v1/admin/campaigns', formData)
        setMessage({ type: 'success', text: 'Campaign created' })
      }
      setIsEditing(false)
      setSelectedCampaign(null)
      await loadCampaigns()
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Error saving campaign'
      setMessage({ type: 'error', text: errorMessage })
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (campaign: Campaign) => {
    if (!confirm(`Delete campaign "${campaign.name}"?`)) return
    try {
      await apiClient.delete(`/api/v1/admin/campaigns/${campaign.id}`)
      setMessage({ type: 'success', text: 'Campaign deleted' })
      await loadCampaigns()
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Error deleting campaign'
      setMessage({ type: 'error', text: errorMessage })
    }
  }

  const handlePreview = async (campaign: Campaign) => {
    try {
      const data = await apiClient.get<{ subject: string; html_body: string }>(
        `/api/v1/admin/campaigns/${campaign.id}/preview`
      )
      setPreviewSubject(data.subject)
      setPreviewHtml(data.html_body)
    } catch (error) {
      logger.error('Error previewing campaign:', error)
      setMessage({ type: 'error', text: 'Error loading preview' })
    }
  }

  const handleSendClick = async (campaign: Campaign) => {
    try {
      const data = await apiClient.get<RecipientCounts>(
        `/api/v1/admin/campaigns/${campaign.id}/recipient-count`
      )
      setRecipientCounts(data)
      setSelectedCampaign(campaign)
      setShowSendConfirm(true)
    } catch (error) {
      logger.error('Error getting recipient count:', error)
      setMessage({ type: 'error', text: 'Error getting recipient count' })
    }
  }

  const handleConfirmSend = async () => {
    if (!selectedCampaign) return
    setIsSending(true)
    try {
      await apiClient.post(`/api/v1/admin/campaigns/${selectedCampaign.id}/send`, {})
      setMessage({ type: 'success', text: `Campaign sending started to ${recipientCounts?.new_recipients || 0} new recipients` })
      setShowSendConfirm(false)
      setSelectedCampaign(null)
      setRecipientCounts(null)
      await loadCampaigns()
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Error sending campaign'
      setMessage({ type: 'error', text: errorMessage })
    } finally {
      setIsSending(false)
    }
  }

  const handleViewSendHistory = async (campaign: Campaign) => {
    setSendHistoryCampaign(campaign)
    setSendHistoryLoading(true)
    setShowSendHistory(true)
    try {
      const data = await apiClient.get<{ sends: CampaignSendRecord[]; total: number }>(
        `/api/v1/admin/campaigns/${campaign.id}/sends`
      )
      setSendHistory(data.sends || [])
      setSendHistoryTotal(data.total)
    } catch (error) {
      logger.error('Error loading send history:', error)
      setMessage({ type: 'error', text: 'Error loading send history' })
    } finally {
      setSendHistoryLoading(false)
    }
  }

  const handleScheduleClick = (campaign: Campaign) => {
    setScheduleCampaign(campaign)
    // Parse existing schedule
    if (campaign.schedule_enabled && campaign.schedule_cron) {
      try {
        const config = JSON.parse(campaign.schedule_cron)
        setScheduleValue(`${config.type}:${config.value}`)
      } catch {
        setScheduleValue('')
      }
    } else {
      setScheduleValue('')
    }
    setShowSchedule(true)
  }

  const handleSaveSchedule = async () => {
    if (!scheduleCampaign) return
    setIsSavingSchedule(true)
    try {
      if (!scheduleValue) {
        await apiClient.put(`/api/v1/admin/campaigns/${scheduleCampaign.id}/schedule`, {
          schedule_enabled: false,
        })
      } else {
        const [type, value] = scheduleValue.split(':')
        const parsedValue = type === 'weekday' ? value : parseInt(value, 10)
        await apiClient.put(`/api/v1/admin/campaigns/${scheduleCampaign.id}/schedule`, {
          schedule_enabled: true,
          schedule_type: type,
          schedule_value: parsedValue,
        })
      }
      setMessage({ type: 'success', text: 'Schedule updated' })
      setShowSchedule(false)
      setScheduleCampaign(null)
      await loadCampaigns()
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Error updating schedule'
      setMessage({ type: 'error', text: errorMessage })
    } finally {
      setIsSavingSchedule(false)
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    setSelectedCampaign(null)
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      draft: 'Draft',
      sending: 'Sending',
      active: 'Active',
      sent: 'Sent',
      failed: 'Failed',
      paused: 'Paused',
    }
    return labels[status] || status.charAt(0).toUpperCase() + status.slice(1)
  }

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  if (!user.is_admin) return null

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-neutral-900">
      <AppHeader />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-neutral-100">Marketing Campaigns</h1>
            <p className="mt-2 text-gray-600 dark:text-neutral-400">
              Send promotional emails to users
            </p>
          </div>
          <Button onClick={handleNew} variant="primary">New Campaign</Button>
        </div>

        {message && (
          <div className={`mb-6 p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-semantic-success-bg dark:bg-green-900/20 text-semantic-success-text dark:text-green-300 border border-semantic-success-border dark:border-green-800'
              : 'bg-semantic-error-bg dark:bg-red-900/20 text-semantic-error-text dark:text-red-300 border border-semantic-error-border dark:border-red-800'
          }`}>
            {message.text}
          </div>
        )}

        {/* Campaign List */}
        <Card>
          <CardHeader title={`Campaigns (${campaigns.length})`} />
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-gray-500 dark:text-neutral-400">Loading campaigns...</div>
            ) : campaigns.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-neutral-400">No campaigns yet. Create your first one.</div>
            ) : (
              <div className="space-y-4">
                {campaigns.map((c) => (
                  <div
                    key={c.id}
                    className="border border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 rounded-lg p-4 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900 dark:text-neutral-100">{c.name}</h3>
                          <Badge variant={STATUS_BADGE[c.status] || 'default'}>
                            {getStatusLabel(c.status)}
                          </Badge>
                          <Badge variant="info">
                            {AUDIENCE_OPTIONS.find((a) => a.value === c.audience_filter)?.label || c.audience_filter}
                          </Badge>
                          {c.schedule_enabled && (
                            <Badge variant="info">Scheduled</Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 dark:text-neutral-300 mb-1">
                          <strong>Subject:</strong> {c.subject}
                        </p>
                        {(c.status === 'active' || c.status === 'sent' || c.status === 'sending') && (
                          <p className="text-sm text-gray-500 dark:text-neutral-400">
                            Sent: {c.sent_count} / {c.total_recipients}
                            {c.failed_count > 0 && <span className="text-red-500"> ({c.failed_count} failed)</span>}
                          </p>
                        )}
                        {c.error_message && (
                          <p className="text-sm text-red-500 mt-1">{c.error_message}</p>
                        )}
                        <p className="text-xs text-gray-400 dark:text-neutral-500 mt-2">
                          {c.sent_at
                            ? `Last sent: ${new Date(c.sent_at).toLocaleString()}`
                            : `Created: ${c.created_at ? new Date(c.created_at).toLocaleString() : '-'}`}
                          {c.last_scheduled_run && (
                            <span> | Last scheduled run: {new Date(c.last_scheduled_run).toLocaleString()}</span>
                          )}
                        </p>
                      </div>
                      <div className="flex gap-2 ml-4 flex-wrap justify-end">
                        <Button onClick={() => handlePreview(c)} variant="secondary" size="sm">Preview</Button>
                        {(c.status === 'active' || c.sent_count > 0) && (
                          <Button onClick={() => handleViewSendHistory(c)} variant="secondary" size="sm">History</Button>
                        )}
                        {(c.status === 'draft' || c.status === 'active') && (
                          <>
                            <Button onClick={() => handleEdit(c)} variant="primary" size="sm">Edit</Button>
                            <Button onClick={() => handleSendClick(c)} variant="primary" size="sm">
                              {c.status === 'active' ? 'Re-send' : 'Send'}
                            </Button>
                            <Button onClick={() => handleScheduleClick(c)} variant="secondary" size="sm">Schedule</Button>
                          </>
                        )}
                        {c.status === 'draft' && (
                          <Button onClick={() => handleDelete(c)} variant="secondary" size="sm">Delete</Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit/Create Modal */}
        {isEditing && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
                  {selectedCampaign ? 'Edit Campaign' : 'New Campaign'}
                </h2>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">
                      Campaign Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-gray-900 dark:text-neutral-100 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Internal name (e.g. First Upload Nudge)"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">
                      Subject *
                    </label>
                    <input
                      type="text"
                      value={formData.subject}
                      onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-gray-900 dark:text-neutral-100 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Email subject line (supports {{user_name}} etc.)"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">
                      Audience
                    </label>
                    <select
                      value={formData.audience_filter}
                      onChange={(e) => setFormData({ ...formData, audience_filter: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {AUDIENCE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">
                      Email Body *
                    </label>
                    <EmailHtmlEditor
                      value={formData.html_body}
                      onChange={(v) => setFormData({ ...formData, html_body: v })}
                      placeholder="Compose your campaign email..."
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 mt-6 pt-4 border-t dark:border-neutral-700">
                  <Button onClick={handleCancel} variant="secondary" disabled={isSaving}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSave}
                    variant="primary"
                    disabled={isSaving || !formData.name || !formData.subject || !formData.html_body}
                  >
                    {isSaving ? 'Saving...' : selectedCampaign ? 'Save Changes' : 'Create Campaign'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Preview Modal */}
        {previewHtml !== null && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold text-gray-900 dark:text-neutral-100">Email Preview</h2>
                  <Button onClick={() => setPreviewHtml(null)} variant="secondary" size="sm">Close</Button>
                </div>
                <p className="text-sm text-gray-600 dark:text-neutral-300 mb-4">
                  <strong>Subject:</strong> {previewSubject}
                </p>
                <div
                  className="border border-gray-200 dark:border-neutral-600 rounded p-4 bg-white"
                  dangerouslySetInnerHTML={{ __html: previewHtml }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Send Confirmation Modal */}
        {showSendConfirm && recipientCounts && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full">
              <div className="p-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-neutral-100 mb-4">Confirm Send</h2>
                <p className="text-gray-700 dark:text-neutral-300 mb-2">
                  Campaign: <strong>&quot;{selectedCampaign?.name}&quot;</strong>
                </p>
                <div className="bg-gray-50 dark:bg-neutral-700/50 rounded-lg p-3 mb-4 space-y-1">
                  <p className="text-sm text-gray-600 dark:text-neutral-300">
                    Total eligible: <strong>{recipientCounts.total_eligible}</strong>
                  </p>
                  {recipientCounts.already_sent > 0 && (
                    <p className="text-sm text-gray-500 dark:text-neutral-400">
                      Already sent: {recipientCounts.already_sent}
                    </p>
                  )}
                  <p className="text-sm font-medium text-gray-900 dark:text-neutral-100">
                    New recipients: <strong>{recipientCounts.new_recipients}</strong>
                  </p>
                </div>
                <p className="text-sm text-gray-500 dark:text-neutral-400 mb-6">
                  Only users with marketing emails enabled will receive this.
                  {recipientCounts.already_sent > 0 && ' Users who already received this campaign will be skipped.'}
                </p>
                <div className="flex justify-end gap-3">
                  <Button
                    onClick={() => { setShowSendConfirm(false); setSelectedCampaign(null); setRecipientCounts(null) }}
                    variant="secondary"
                    disabled={isSending}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleConfirmSend} variant="primary" disabled={isSending}>
                    {isSending ? 'Sending...' : `Send to ${recipientCounts.new_recipients} New Users`}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Send History Modal */}
        {showSendHistory && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold text-gray-900 dark:text-neutral-100">
                    Send History: {sendHistoryCampaign?.name}
                  </h2>
                  <Button onClick={() => { setShowSendHistory(false); setSendHistoryCampaign(null) }} variant="secondary" size="sm">Close</Button>
                </div>
                <p className="text-sm text-gray-500 dark:text-neutral-400 mb-4">
                  Total sends: {sendHistoryTotal}
                </p>
                {sendHistoryLoading ? (
                  <div className="text-center py-8 text-gray-500 dark:text-neutral-400">Loading...</div>
                ) : sendHistory.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-neutral-400">No sends yet.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b dark:border-neutral-700">
                          <th className="text-left py-2 px-3 text-gray-600 dark:text-neutral-400">Email</th>
                          <th className="text-left py-2 px-3 text-gray-600 dark:text-neutral-400">Status</th>
                          <th className="text-left py-2 px-3 text-gray-600 dark:text-neutral-400">Sent At</th>
                          <th className="text-left py-2 px-3 text-gray-600 dark:text-neutral-400">Error</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sendHistory.map((s) => (
                          <tr key={s.id} className="border-b dark:border-neutral-700/50">
                            <td className="py-2 px-3 text-gray-900 dark:text-neutral-100">{s.user_email}</td>
                            <td className="py-2 px-3">
                              <Badge variant={s.status === 'sent' ? 'success' : 'error'}>
                                {s.status}
                              </Badge>
                            </td>
                            <td className="py-2 px-3 text-gray-600 dark:text-neutral-300">
                              {new Date(s.sent_at).toLocaleString()}
                            </td>
                            <td className="py-2 px-3 text-red-500 text-xs">{s.error_message || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Schedule Modal */}
        {showSchedule && scheduleCampaign && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full">
              <div className="p-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
                  Schedule: {scheduleCampaign.name}
                </h2>
                <p className="text-sm text-gray-600 dark:text-neutral-300 mb-4">
                  Scheduled campaigns automatically send to new eligible users on the configured frequency.
                  Users who already received this campaign will be skipped.
                </p>
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">
                    Send Frequency
                  </label>
                  <select
                    value={scheduleValue}
                    onChange={(e) => setScheduleValue(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-700 text-gray-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {SCHEDULE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div className="flex justify-end gap-3">
                  <Button
                    onClick={() => { setShowSchedule(false); setScheduleCampaign(null) }}
                    variant="secondary"
                    disabled={isSavingSchedule}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleSaveSchedule} variant="primary" disabled={isSavingSchedule}>
                    {isSavingSchedule ? 'Saving...' : 'Save Schedule'}
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
