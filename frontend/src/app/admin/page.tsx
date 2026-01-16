// frontend/src/app/admin/page.tsx
/**
 * Bonifatus DMS - Admin Dashboard
 * System management for administrators
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
import currencyList from 'currency-list'
import { logger } from '@/lib/logger'

interface SystemStats {
  total_users: number
  active_users: number
  total_documents: number
  total_storage_mb: number
  users_by_tier: Record<string, number>
  documents_last_24h: number
  signups_last_7d: number
}

interface User {
  id: string
  email: string
  full_name: string
  tier_id: number
  tier_name: string
  is_active: boolean
  is_admin: boolean
  storage_used_bytes: number
  storage_quota_bytes: number
  document_count: number
  created_at: string
  monthly_usage?: {
    month_period: string
    pages_processed: number
    pages_limit: number | null
    pages_percent: number
    volume_uploaded_bytes: number
    volume_limit_bytes: number | null
    volume_percent: number
    documents_uploaded: number
    translations_used: number
    translations_limit: number | null
    api_calls_made: number
    api_calls_limit: number | null
    period_start: string | null
    period_end: string | null
    admin_unlimited?: boolean
  }
}

interface TierPlan {
  id: number
  name: string
  display_name: string
  description: string | null
  price_monthly_cents: number
  price_yearly_cents: number
  currency: string

  // Monthly limits
  max_pages_per_month: number | null
  max_monthly_upload_bytes: number
  max_translations_per_month: number | null

  // Per-file limits
  max_file_size_bytes: number
  max_batch_upload_size: number | null

  // Legacy field (keep for compatibility)
  storage_quota_bytes?: number
  max_documents?: number | null

  // Team/multi-user limits
  multi_user_enabled: boolean
  max_team_members: number | null

  // Feature flags
  bulk_operations_enabled: boolean
  email_to_process_enabled: boolean

  // Other limits
  custom_categories_limit: number | null

  // Display
  sort_order: number
  is_active: boolean
  is_public: boolean
}

interface ClamAVHealth {
  timestamp: string
  service: string
  status: string
  available: boolean
  version: string | null
  connection_type: string | null
  restart_attempts: number
  error?: string
}

interface EmailPollerHealth {
  timestamp: string
  service: string
  status: string
  imap_available: boolean
  imap_host: string
  imap_port: number
  polling_interval_seconds: number
  polling_task_running: boolean
  scheduler_running: boolean
  next_poll_time: string | null
  last_successful_poll: string | null
  last_poll_error: string | null
  consecutive_failures: number
  total_emails_processed_today: number
  unread_emails?: number
  recent_activity: Array<{
    received_at: string
    status: string
    sender_email: string
    documents_created: number
    rejection_reason: string | null
  }>
  error?: string
  imap_error?: string
  warning?: string
}

interface Currency {
  code: string
  symbol: string
  name: string
  decimal_places: number
  exchange_rate: number | null
  is_active: boolean
  is_default: boolean
  sort_order: number
}

interface EntityQualityConfig {
  config_key: string
  config_value: number
  category: string
  description: string
  created_at: string
  updated_at: string
}

interface StorageProvider {
  provider_key: string
  display_name: string
  min_tier_id: number
  min_tier_name: string
  is_active: boolean
  sort_order: number
  icon: string
  color: string
  description: string
  capabilities: string[]
}

export default function AdminDashboard() {
  const { user, isLoading, hasAttemptedAuth, loadUser } = useAuth()
  const router = useRouter()

  const [stats, setStats] = useState<SystemStats | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [tiers, setTiers] = useState<TierPlan[]>([])
  const [currencies, setCurrencies] = useState<Currency[]>([])
  const [clamavHealth, setClamavHealth] = useState<ClamAVHealth | null>(null)
  const [emailPollerHealth, setEmailPollerHealth] = useState<EmailPollerHealth | null>(null)
  const [entityQualityConfigs, setEntityQualityConfigs] = useState<EntityQualityConfig[]>([])
  const [editingConfig, setEditingConfig] = useState<{key: string, value: string} | null>(null)
  const [storageProviders, setStorageProviders] = useState<StorageProvider[]>([])
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'tiers' | 'providers' | 'currencies' | 'health' | 'email-templates' | 'entity-quality'>('overview')
  const [loadingData, setLoadingData] = useState(true)
  const [editingTier, setEditingTier] = useState<TierPlan | null>(null)
  const [editingCurrency, setEditingCurrency] = useState<{code: string, rate: string} | null>(null)
  const [showAddCurrency, setShowAddCurrency] = useState(false)
  const [newCurrency, setNewCurrency] = useState({
    code: '',
    symbol: '',
    name: '',
    decimal_places: 2,
    exchange_rate: null as number | null,
    sort_order: 0
  })
  const [restartingClamav, setRestartingClamav] = useState(false)
  const [pollingEmail, setPollingEmail] = useState(false)
  const [refreshingEmailHealth, setRefreshingEmailHealth] = useState(false)

  // User search and sorting
  const [userSearch, setUserSearch] = useState('')
  const [userSortField, setUserSortField] = useState<'email' | 'full_name' | 'tier_name' | 'created_at'>('created_at')
  const [userSortDirection, setUserSortDirection] = useState<'asc' | 'desc'>('desc')
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null)

  // Tier editing with unit selector
  const [storageUnit, setStorageUnit] = useState<'bytes' | 'MB' | 'GB'>('GB')
  const [fileSizeUnit, setFileSizeUnit] = useState<'bytes' | 'MB' | 'GB'>('MB')

  // Load user on mount to ensure fresh data
  useEffect(() => {
    loadUser()
  }, [loadUser])

  // Check admin access
  useEffect(() => {
    // Don't check auth until we've attempted to load the user
    if (!hasAttemptedAuth) {
      return
    }

    if (!isLoading && !user) {
      router.push('/login')
      return
    }

    if (!isLoading && user && !user.is_admin) {
      router.push('/dashboard')
      return
    }

    if (user && user.is_admin) {
      loadData()
    }
  }, [user, isLoading, hasAttemptedAuth, router])

  const loadData = async () => {
    try {
      setLoadingData(true)

      // Load stats
      const statsData = await apiClient.get<SystemStats>('/api/v1/admin/stats')
      setStats(statsData)

      // Load users
      const usersData = await apiClient.get<{ users: User[] }>('/api/v1/admin/users', false, {
        params: {
          page: '1',
          page_size: '100'
        }
      })
      setUsers(usersData.users)

      // Load tiers
      const tiersData = await apiClient.get<{ tiers: TierPlan[] }>('/api/v1/admin/tiers')
      setTiers(tiersData.tiers)

      // Load storage providers
      const providersData = await apiClient.get<{ providers: StorageProvider[] }>('/api/v1/admin/providers')
      setStorageProviders(providersData.providers)

      // Load currencies
      const currenciesData = await apiClient.get<{ currencies: Currency[] }>('/api/v1/admin/currencies')
      setCurrencies(currenciesData.currencies)

      // Load ClamAV health
      const healthData = await apiClient.get<ClamAVHealth>('/api/v1/admin/health/clamav')
      setClamavHealth(healthData)

      // Load Email Poller health
      const emailHealthData = await apiClient.get<EmailPollerHealth>('/api/v1/admin/health/email-poller')
      setEmailPollerHealth(emailHealthData)

      // Load Entity Quality configs
      const entityQualityData = await apiClient.get<{ configs: EntityQualityConfig[] }>('/api/v1/entity-quality/config')
      setEntityQualityConfigs(entityQualityData.configs)

    } catch (error) {
      logger.error('Failed to load admin data:', error)
    } finally {
      setLoadingData(false)
    }
  }

  const checkClamavHealth = async () => {
    try {
      const healthData = await apiClient.get<ClamAVHealth>('/api/v1/admin/health/clamav')
      setClamavHealth(healthData)
    } catch (error) {
      logger.error('Failed to check ClamAV health:', error)
    }
  }

  const restartClamav = async () => {
    try {
      setRestartingClamav(true)
      const result = await apiClient.post<{ success: boolean; error?: string }>('/api/v1/admin/health/clamav/restart', {})

      if (result.success) {
        alert('ClamAV restarted successfully!')
      } else {
        alert(`Restart failed: ${result.error}`)
      }

      // Refresh health status
      await checkClamavHealth()
    } catch (error) {
      logger.error('Failed to restart ClamAV:', error)
      alert('Failed to restart ClamAV service')
    } finally {
      setRestartingClamav(false)
    }
  }

  const checkEmailPollerHealth = async () => {
    try {
      setRefreshingEmailHealth(true)
      const healthData = await apiClient.get<EmailPollerHealth>('/api/v1/admin/health/email-poller')
      setEmailPollerHealth(healthData)
    } catch (error) {
      logger.error('Failed to check Email Poller health:', error)
      alert('Failed to refresh Email Poller status')
    } finally {
      setRefreshingEmailHealth(false)
    }
  }

  const triggerEmailPoll = async () => {
    try {
      setPollingEmail(true)

      const result = await apiClient.post<{ success: boolean; error?: string }>('/api/v1/admin/health/email-poller/poll-now', {})

      if (result.success) {
        alert('Email poll triggered successfully! Check processing history for results.')
      } else {
        alert(`Poll failed: ${result.error}`)
      }

      // Refresh health status
      await checkEmailPollerHealth()
    } catch (error) {
      logger.error('Failed to trigger email poll:', error)
      alert('Failed to trigger email poll')
    } finally {
      setPollingEmail(false)
    }
  }

  const updateTier = async (tierId: number, updates: Partial<TierPlan>) => {
    try {
      await apiClient.patch(`/api/v1/admin/tiers/${tierId}`, updates)
      await loadData()
      setEditingTier(null)
    } catch (error) {
      logger.error('Failed to update tier:', error)
      alert('Failed to update tier configuration')
    }
  }

  const updateCurrency = async (currencyCode: string, exchangeRate: number | null) => {
    try {
      await apiClient.patch(`/api/v1/admin/currencies/${currencyCode}`, {
        exchange_rate: exchangeRate
      })
      await loadData()
      setEditingCurrency(null)
      alert(`Currency ${currencyCode} updated successfully!`)
    } catch (error) {
      logger.error('Failed to update currency:', error)
      alert('Failed to update currency exchange rate')
    }
  }

  const createCurrency = async (currencyData: {
    code: string
    symbol: string
    name: string
    decimal_places: number
    exchange_rate: number | null
    sort_order: number
  }) => {
    try {
      await apiClient.post('/api/v1/admin/currencies', currencyData)
      await loadData()
      alert(`Currency ${currencyData.code} created successfully!`)
    } catch (error) {
      logger.error('Failed to create currency:', error)
      const errorMessage = (error as {response?: {data?: {detail?: string}}})?.response?.data?.detail || 'Failed to create currency'
      alert(errorMessage)
    }
  }

  const deleteCurrency = async (currencyCode: string) => {
    if (!confirm(`Are you sure you want to delete currency ${currencyCode}? This action cannot be undone.`)) {
      return
    }

    try {
      await apiClient.delete(`/api/v1/admin/currencies/${currencyCode}`)
      await loadData()
      alert(`Currency ${currencyCode} deleted successfully!`)
    } catch (error) {
      logger.error('Failed to delete currency:', error)
      const errorMessage = (error as {response?: {data?: {detail?: string}}})?.response?.data?.detail || 'Failed to delete currency'
      alert(errorMessage)
    }
  }

  const updateUserTier = async (userId: string, newTierId: number) => {
    // Get current user for optimistic update and rollback
    const user = users.find(u => u.id === userId)
    if (!user) {
      logger.error('[DEBUG] updateUserTier: user not found:', userId)
      return
    }

    const oldTierId = user.tier_id
    const newTierName = tiers.find(t => t.id === newTierId)?.display_name || 'Unknown'

    logger.debug('[DEBUG] updateUserTier: Starting tier update', {
      userId,
      userEmail: user.email,
      oldTierId,
      newTierId,
      newTierName,
      timestamp: new Date().toISOString()
    })

    try {
      setUpdatingUserId(userId)
      logger.debug('[DEBUG] updateUserTier: Set loading state for user:', userId)

      // Make API call FIRST (removed optimistic update)
      logger.debug('[DEBUG] updateUserTier: Making API call to /api/v1/admin/users/' + userId + '/tier')
      logger.debug('[DEBUG] updateUserTier: Request body:', { tier_id: newTierId })

      const response = await apiClient.patch(
        `/api/v1/admin/users/${userId}/tier`,
        { tier_id: newTierId },
        true  // requireAuth=true for admin endpoints
      )

      logger.debug('[DEBUG] updateUserTier: API call successful, response:', response)

      // Update UI after successful API call
      setUsers(prevUsers =>
        prevUsers.map(u =>
          u.id === userId
            ? { ...u, tier_id: newTierId, tier_name: newTierName }
            : u
        )
      )
      logger.debug('[DEBUG] updateUserTier: Updated local state')

      // Reload data to ensure consistency with backend
      logger.debug('[DEBUG] updateUserTier: Reloading data from server')
      await loadData()
      logger.debug('[DEBUG] updateUserTier: Data reloaded')

      // Show success message
      alert(`✓ Successfully updated ${user.email} to ${newTierName} tier`)
      logger.debug('[DEBUG] updateUserTier: Update complete')

    } catch (error) {
      logger.error('[DEBUG] updateUserTier: ERROR occurred:', error)
      logger.error('[DEBUG] updateUserTier: Error details:', {
        name: (error as Error)?.name,
        message: (error as Error)?.message,
        status: (error as { status?: number })?.status,
        response: (error as { response?: unknown })?.response
      })

      // Show detailed error message
      const errorMessage = (error as { response?: { data?: { detail?: string } }; message?: string })
        ?.response?.data?.detail || (error as Error)?.message || 'Failed to update user tier'
      alert(`✗ Error: ${errorMessage}`)
      logger.error('[DEBUG] updateUserTier: Showed error alert:', errorMessage)

      // Reload data to sync with backend state
      try {
        logger.debug('[DEBUG] updateUserTier: Reloading data after error')
        await loadData()
        logger.debug('[DEBUG] updateUserTier: Data reloaded after error')
      } catch (reloadError) {
        logger.error('[DEBUG] updateUserTier: Failed to reload data after error:', reloadError)
      }
    } finally {
      setUpdatingUserId(null)
      logger.debug('[DEBUG] updateUserTier: Cleared loading state')
    }
  }

  const updateEntityQualityConfig = async (configKey: string, newValue: number) => {
    try {
      await apiClient.patch(`/api/v1/entity-quality/config/${configKey}`, {
        config_value: newValue
      })
      await loadData()
      setEditingConfig(null)
      alert(`Config ${configKey} updated successfully!`)
    } catch (error) {
      logger.error('Failed to update entity quality config:', error)
      alert('Failed to update configuration')
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatPrice = (cents: number) => {
    return `€${(cents / 100).toFixed(2)}`
  }

  // Unit conversion helpers
  const bytesToUnit = (bytes: number, unit: 'bytes' | 'MB' | 'GB'): number => {
    if (unit === 'bytes') return bytes
    if (unit === 'MB') return bytes / (1024 * 1024)
    return bytes / (1024 * 1024 * 1024)
  }

  const unitToBytes = (value: number, unit: 'bytes' | 'MB' | 'GB'): number => {
    if (unit === 'bytes') return value
    if (unit === 'MB') return value * 1024 * 1024
    return value * 1024 * 1024 * 1024
  }

  // Filter and sort users
  const filteredAndSortedUsers = users
    .filter(u => {
      if (!userSearch) return true
      const search = userSearch.toLowerCase()
      return (
        u.email.toLowerCase().includes(search) ||
        u.full_name.toLowerCase().includes(search)
      )
    })
    .sort((a, b) => {
      const direction = userSortDirection === 'asc' ? 1 : -1
      if (userSortField === 'created_at') {
        return direction * (new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      }
      return direction * String(a[userSortField]).localeCompare(String(b[userSortField]))
    })

  const toggleSort = (field: typeof userSortField) => {
    if (userSortField === field) {
      setUserSortDirection(userSortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setUserSortField(field)
      setUserSortDirection('asc')
    }
  }

  if (isLoading || !user) {
    return (
      <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900">
        <AppHeader title="Admin Dashboard" />
        <div className="flex items-center justify-center h-64">
          <div className="text-neutral-600 dark:text-neutral-400">Loading...</div>
        </div>
      </div>
    )
  }

  if (!user.is_admin) {
    return null // Will redirect
  }

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900">
      <AppHeader title="Admin Dashboard" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="flex space-x-4 mb-6 border-b border-neutral-200 dark:border-neutral-700">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'overview'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:text-white dark:hover:text-neutral-200'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'users'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:text-white dark:hover:text-neutral-200'
            }`}
          >
            Users
          </button>
          <button
            onClick={() => setActiveTab('tiers')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'tiers'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:text-white dark:hover:text-neutral-200'
            }`}
          >
            Tier Configuration
          </button>
          <button
            onClick={() => setActiveTab('providers')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'providers'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:text-white dark:hover:text-neutral-200'
            }`}
          >
            Storage Providers
          </button>
          <button
            onClick={() => setActiveTab('currencies')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'currencies'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:text-white dark:hover:text-neutral-200'
            }`}
          >
            Currencies
          </button>
          <button
            onClick={() => setActiveTab('health')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'health'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:text-white dark:hover:text-neutral-200'
            }`}
          >
            System Health
            {clamavHealth && !clamavHealth.available && (
              <span className="ml-2 inline-block h-2 w-2 rounded-full bg-admin-danger"></span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('email-templates')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'email-templates'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:text-white dark:hover:text-neutral-200'
            }`}
          >
            Email Templates
          </button>
          <button
            onClick={() => setActiveTab('entity-quality')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'entity-quality'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:text-white dark:hover:text-neutral-200'
            }`}
          >
            Entity Quality
          </button>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && stats && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardContent>
                  <div className="text-sm text-neutral-600 dark:text-neutral-400">Total Users</div>
                  <div className="text-3xl font-bold text-neutral-900 dark:text-white mt-2">
                    {stats.total_users}
                  </div>
                  <div className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500 mt-1">
                    {stats.active_users} active
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent>
                  <div className="text-sm text-neutral-600 dark:text-neutral-400">Total Documents</div>
                  <div className="text-3xl font-bold text-neutral-900 dark:text-white mt-2">
                    {stats.total_documents.toLocaleString()}
                  </div>
                  <div className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500 mt-1">
                    +{stats.documents_last_24h} last 24h
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent>
                  <div className="text-sm text-neutral-600 dark:text-neutral-400">Total Storage</div>
                  <div className="text-3xl font-bold text-neutral-900 dark:text-white mt-2">
                    {stats.total_storage_mb.toLocaleString()} MB
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent>
                  <div className="text-sm text-neutral-600 dark:text-neutral-400">New Signups</div>
                  <div className="text-3xl font-bold text-neutral-900 dark:text-white mt-2">
                    {stats.signups_last_7d}
                  </div>
                  <div className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500 mt-1">
                    Last 7 days
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Users by Tier */}
            <Card>
              <CardHeader title="Users by Tier" />
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(stats.users_by_tier).map(([tierName, count]) => (
                    <div key={tierName} className="flex items-center justify-between">
                      <span className="text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">{tierName}</span>
                      <Badge variant="info">{count} users</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <Card>
            <CardHeader title="User Management" />
            <CardContent>
              {/* Search Bar */}
              <div className="mb-4">
                <input
                  type="text"
                  placeholder="Search by name or email..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="w-full px-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                />
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-neutral-100 dark:bg-neutral-800">
                    <tr>
                      <th
                        onClick={() => toggleSort('email')}
                        className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 cursor-pointer hover:bg-neutral-200 dark:hover:bg-neutral-700"
                      >
                        Email {userSortField === 'email' && (userSortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th
                        onClick={() => toggleSort('full_name')}
                        className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 cursor-pointer hover:bg-neutral-200 dark:hover:bg-neutral-700"
                      >
                        Name {userSortField === 'full_name' && (userSortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th
                        onClick={() => toggleSort('tier_name')}
                        className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 cursor-pointer hover:bg-neutral-200 dark:hover:bg-neutral-700"
                      >
                        Tier {userSortField === 'tier_name' && (userSortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Documents</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Storage</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Monthly Usage</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Status</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAndSortedUsers.map((user) => (
                      <tr key={user.id} className="border-t border-neutral-200 dark:border-neutral-700">
                        <td className="px-4 py-3 text-sm text-neutral-900 dark:text-white">{user.email}</td>
                        <td className="px-4 py-3 text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">{user.full_name}</td>
                        <td className="px-4 py-3 text-sm">
                          <select
                            value={user.tier_id}
                            onChange={(e) => updateUserTier(user.id, parseInt(e.target.value))}
                            disabled={updatingUserId === user.id}
                            className={`px-2 py-1 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white text-sm ${
                              updatingUserId === user.id ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                            }`}
                            title={updatingUserId === user.id ? 'Updating...' : 'Change user tier'}
                          >
                            {tiers.map((tier) => (
                              <option key={tier.id} value={tier.id}>{tier.display_name}</option>
                            ))}
                          </select>
                          {updatingUserId === user.id && (
                            <span className="ml-2 text-xs text-admin-primary dark:text-blue-400 dark:text-blue-400">Updating...</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">{user.document_count}</td>
                        <td className="px-4 py-3 text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">
                          {formatBytes(user.storage_used_bytes)} / {formatBytes(user.storage_quota_bytes)}
                        </td>
                        <td className="px-4 py-3 text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">
                          {user.monthly_usage ? (
                            user.monthly_usage.admin_unlimited ? (
                              <span className="text-neutral-500 dark:text-neutral-400">Unlimited</span>
                            ) : (
                              <div className="space-y-1">
                                <div className="text-xs">
                                  Pages: {user.monthly_usage.pages_processed} / {user.monthly_usage.pages_limit || '∞'}
                                  <span className="text-neutral-500 dark:text-neutral-400 ml-1">({user.monthly_usage.pages_percent}%)</span>
                                </div>
                                <div className="text-xs">
                                  Volume: {formatBytes(user.monthly_usage.volume_uploaded_bytes)} / {user.monthly_usage.volume_limit_bytes ? formatBytes(user.monthly_usage.volume_limit_bytes) : '∞'}
                                  <span className="text-neutral-500 dark:text-neutral-400 ml-1">({user.monthly_usage.volume_percent}%)</span>
                                </div>
                              </div>
                            )
                          ) : (
                            <span className="text-neutral-400">No data</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {user.is_active ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="error">Inactive</Badge>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {user.is_admin && <Badge variant="warning">Admin</Badge>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Tiers Tab */}
        {activeTab === 'tiers' && (
          <div className="space-y-4">
            {tiers.map((tier) => (
              <Card key={tier.id}>
                <CardHeader
                  title={tier.display_name}
                  action={
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingTier(editingTier?.id === tier.id ? null : tier)}
                    >
                      {editingTier?.id === tier.id ? 'Cancel' : 'Edit'}
                    </Button>
                  }
                />
                <CardContent>
                  {editingTier?.id === tier.id ? (
                    /* Edit Mode */
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-1">
                            Monthly Price (€)
                          </label>
                          <input
                            type="number"
                            step="0.01"
                            defaultValue={tier.price_monthly_cents / 100}
                            onChange={(e) => setEditingTier({ ...editingTier, price_monthly_cents: Math.round(parseFloat(e.target.value) * 100) })}
                            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-1">
                            Annual Price (€)
                          </label>
                          <input
                            type="number"
                            step="0.01"
                            defaultValue={tier.price_yearly_cents / 100}
                            onChange={(e) => setEditingTier({ ...editingTier, price_yearly_cents: Math.round(parseFloat(e.target.value) * 100) })}
                            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-1">
                            Storage Quota
                          </label>
                          <div className="flex gap-2">
                            <input
                              type="number"
                              value={bytesToUnit(editingTier.storage_quota_bytes || editingTier.max_monthly_upload_bytes || 0, storageUnit)}
                              onChange={(e) => setEditingTier({ ...editingTier, storage_quota_bytes: unitToBytes(parseFloat(e.target.value) || 0, storageUnit), max_monthly_upload_bytes: unitToBytes(parseFloat(e.target.value) || 0, storageUnit) })}
                              className="flex-1 px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            />
                            <select
                              value={storageUnit}
                              onChange={(e) => setStorageUnit(e.target.value as typeof storageUnit)}
                              className="px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            >
                              <option value="bytes">Bytes</option>
                              <option value="MB">MB</option>
                              <option value="GB">GB</option>
                            </select>
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-1">
                            Max File Size
                          </label>
                          <div className="flex gap-2">
                            <input
                              type="number"
                              value={bytesToUnit(editingTier.max_file_size_bytes, fileSizeUnit)}
                              onChange={(e) => setEditingTier({ ...editingTier, max_file_size_bytes: unitToBytes(parseFloat(e.target.value) || 0, fileSizeUnit) })}
                              className="flex-1 px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            />
                            <select
                              value={fileSizeUnit}
                              onChange={(e) => setFileSizeUnit(e.target.value as typeof fileSizeUnit)}
                              className="px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            >
                              <option value="bytes">Bytes</option>
                              <option value="MB">MB</option>
                              <option value="GB">GB</option>
                            </select>
                          </div>
                        </div>
                        <div>
                          <label className="flex items-center space-x-2 mb-2">
                            <input
                              type="checkbox"
                              checked={editingTier.max_documents === null}
                              onChange={(e) => setEditingTier({ ...editingTier, max_documents: e.target.checked ? null : 100 })}
                              className="rounded"
                            />
                            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Unlimited Documents</span>
                          </label>
                          {editingTier.max_documents !== null && (
                            <input
                              type="number"
                              value={editingTier.max_documents}
                              onChange={(e) => setEditingTier({ ...editingTier, max_documents: parseInt(e.target.value) || 0 })}
                              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            />
                          )}
                        </div>
                        <div>
                          <label className="flex items-center space-x-2 mb-2">
                            <input
                              type="checkbox"
                              checked={editingTier.max_batch_upload_size === null}
                              onChange={(e) => setEditingTier({ ...editingTier, max_batch_upload_size: e.target.checked ? null : 10 })}
                              className="rounded"
                            />
                            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Unlimited Batch Size</span>
                          </label>
                          {editingTier.max_batch_upload_size !== null && (
                            <input
                              type="number"
                              value={editingTier.max_batch_upload_size}
                              onChange={(e) => setEditingTier({ ...editingTier, max_batch_upload_size: parseInt(e.target.value) || 0 })}
                              placeholder="Max files per batch"
                              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            />
                          )}
                        </div>
                        <div>
                          <label className="flex items-center space-x-2 mb-2">
                            <input
                              type="checkbox"
                              checked={editingTier.max_pages_per_month === null}
                              onChange={(e) => setEditingTier({ ...editingTier, max_pages_per_month: e.target.checked ? null : 500 })}
                              className="rounded"
                            />
                            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Unlimited Pages/Month</span>
                          </label>
                          {editingTier.max_pages_per_month !== null && (
                            <input
                              type="number"
                              value={editingTier.max_pages_per_month}
                              onChange={(e) => setEditingTier({ ...editingTier, max_pages_per_month: parseInt(e.target.value) || 0 })}
                              placeholder="Max pages per month"
                              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            />
                          )}
                        </div>
                        <div>
                          <label className="flex items-center space-x-2 mb-2">
                            <input
                              type="checkbox"
                              checked={editingTier.max_translations_per_month === null}
                              onChange={(e) => setEditingTier({ ...editingTier, max_translations_per_month: e.target.checked ? null : 100 })}
                              className="rounded"
                            />
                            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Unlimited Translations/Month</span>
                          </label>
                          {editingTier.max_translations_per_month !== null && (
                            <input
                              type="number"
                              value={editingTier.max_translations_per_month}
                              onChange={(e) => setEditingTier({ ...editingTier, max_translations_per_month: parseInt(e.target.value) || 0 })}
                              placeholder="Max translations per month"
                              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            />
                          )}
                        </div>
                        <div>
                          <label className="flex items-center space-x-2 mb-2">
                            <input
                              type="checkbox"
                              checked={editingTier.max_team_members === null}
                              onChange={(e) => setEditingTier({ ...editingTier, max_team_members: e.target.checked ? null : 3 })}
                              className="rounded"
                            />
                            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Unlimited Team Members</span>
                          </label>
                          {editingTier.max_team_members !== null && (
                            <input
                              type="number"
                              value={editingTier.max_team_members}
                              onChange={(e) => setEditingTier({ ...editingTier, max_team_members: parseInt(e.target.value) || 0 })}
                              placeholder="Max team members"
                              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            />
                          )}
                        </div>
                        <div>
                          <label className="flex items-center space-x-2 mb-2">
                            <input
                              type="checkbox"
                              checked={editingTier.custom_categories_limit === null}
                              onChange={(e) => setEditingTier({ ...editingTier, custom_categories_limit: e.target.checked ? null : 25 })}
                              className="rounded"
                            />
                            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Unlimited Categories</span>
                          </label>
                          {editingTier.custom_categories_limit !== null && (
                            <input
                              type="number"
                              value={editingTier.custom_categories_limit}
                              onChange={(e) => setEditingTier({ ...editingTier, custom_categories_limit: parseInt(e.target.value) || 0 })}
                              placeholder="Max custom categories"
                              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                            />
                          )}
                        </div>
                      </div>
                      <div className="flex items-center flex-wrap gap-4">
                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={editingTier.bulk_operations_enabled}
                            onChange={(e) => setEditingTier({ ...editingTier, bulk_operations_enabled: e.target.checked })}
                            className="rounded"
                          />
                          <span className="text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Bulk Operations</span>
                        </label>
                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={editingTier.email_to_process_enabled}
                            onChange={(e) => setEditingTier({ ...editingTier, email_to_process_enabled: e.target.checked })}
                            className="rounded"
                          />
                          <span className="text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Email-to-Document</span>
                        </label>
                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={editingTier.multi_user_enabled}
                            onChange={(e) => setEditingTier({ ...editingTier, multi_user_enabled: e.target.checked })}
                            className="rounded"
                          />
                          <span className="text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Multi-User</span>
                        </label>
                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={editingTier.is_active}
                            onChange={(e) => setEditingTier({ ...editingTier, is_active: e.target.checked })}
                            className="rounded"
                          />
                          <span className="text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Active</span>
                        </label>
                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={editingTier.is_public}
                            onChange={(e) => setEditingTier({ ...editingTier, is_public: e.target.checked })}
                            className="rounded"
                          />
                          <span className="text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">Public (shown on pricing page)</span>
                        </label>
                      </div>
                      <Button onClick={() => updateTier(tier.id, editingTier)}>
                        Save Changes
                      </Button>
                    </div>
                  ) : (
                    /* View Mode */
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <div className="text-xs text-neutral-600 dark:text-neutral-400">Monthly Price</div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-white">
                            {formatPrice(tier.price_monthly_cents)}/month
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-neutral-600 dark:text-neutral-400">Annual Price</div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-white">
                            {formatPrice(tier.price_yearly_cents)}/year
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-neutral-600 dark:text-neutral-400">Monthly Upload Volume</div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-white">
                            {formatBytes(tier.max_monthly_upload_bytes || tier.storage_quota_bytes || 0)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-neutral-600 dark:text-neutral-400">Max File Size</div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-white">
                            {formatBytes(tier.max_file_size_bytes)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-neutral-600 dark:text-neutral-400">Max Pages/Month</div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-white">
                            {tier.max_pages_per_month ?? tier.max_documents ?? 'Unlimited'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-neutral-600 dark:text-neutral-400">Max Batch Upload</div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-white">
                            {tier.max_batch_upload_size || 'Unlimited'} files
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-neutral-600 dark:text-neutral-400">Translations/Month</div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-white">
                            {tier.max_translations_per_month || 'Unlimited'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-neutral-600 dark:text-neutral-400">Team Members</div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-white">
                            {tier.max_team_members || 'Unlimited'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-neutral-600 dark:text-neutral-400">Custom Categories</div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-white">
                            {tier.custom_categories_limit || 'Unlimited'}
                          </div>
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400 mb-2">Features</div>
                        <div className="flex flex-wrap gap-2">
                          {tier.bulk_operations_enabled && <Badge variant="success">Bulk Operations</Badge>}
                          {tier.email_to_process_enabled && <Badge variant="success">Email-to-Document</Badge>}
                          {tier.multi_user_enabled && <Badge variant="success">Multi-User</Badge>}
                          {tier.is_active && <Badge variant="info">Active</Badge>}
                          {tier.is_public && <Badge variant="info">Public</Badge>}
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Storage Providers Tab */}
        {activeTab === 'providers' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Storage Provider Configuration" />
              <CardContent>
                <div className="space-y-4">
                  {/* Info Box */}
                  <div className="bg-semantic-info-bg dark:bg-blue-900/20 border border-semantic-info-border dark:border-blue-800 rounded-lg p-4 mb-6">
                    <div className="flex items-start">
                      <svg className="h-5 w-5 text-admin-primary dark:text-blue-400 mt-0.5 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <div className="text-sm text-semantic-info-text dark:text-blue-200">
                        <strong>Provider-Tier Mapping:</strong> Shows which cloud storage providers are available for each subscription tier.
                        Provider configurations are defined in <code className="bg-neutral-200 dark:bg-neutral-700 px-1 rounded">provider_registry.py</code>.
                      </div>
                    </div>
                  </div>

                  {/* Provider Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-neutral-200 dark:border-neutral-700">
                          <th className="text-left py-3 px-4 font-semibold text-neutral-900 dark:text-white">Provider</th>
                          <th className="text-left py-3 px-4 font-semibold text-neutral-900 dark:text-white">Minimum Tier</th>
                          <th className="text-left py-3 px-4 font-semibold text-neutral-900 dark:text-white">Status</th>
                          <th className="text-left py-3 px-4 font-semibold text-neutral-900 dark:text-white">Description</th>
                        </tr>
                      </thead>
                      <tbody>
                        {storageProviders.map((provider) => (
                          <tr key={provider.provider_key} className="border-b border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                            <td className="py-4 px-4">
                              <div className="flex items-center gap-3">
                                <div
                                  className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold text-sm"
                                  style={{ backgroundColor: provider.color }}
                                >
                                  {provider.display_name.charAt(0)}
                                </div>
                                <div>
                                  <div className="font-medium text-neutral-900 dark:text-white">{provider.display_name}</div>
                                  <div className="text-xs text-neutral-500 dark:text-neutral-400">{provider.provider_key}</div>
                                </div>
                              </div>
                            </td>
                            <td className="py-4 px-4">
                              <Badge variant={provider.min_tier_id === 0 ? 'success' : provider.min_tier_id === 1 ? 'info' : 'warning'}>
                                {provider.min_tier_name}
                              </Badge>
                              <div className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                                Tier ID: {provider.min_tier_id}
                              </div>
                            </td>
                            <td className="py-4 px-4">
                              {provider.is_active ? (
                                <Badge variant="success">Active</Badge>
                              ) : (
                                <Badge variant="default">Inactive</Badge>
                              )}
                            </td>
                            <td className="py-4 px-4 text-sm text-neutral-600 dark:text-neutral-400 max-w-xs">
                              {provider.description}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Tier Access Summary */}
                  <div className="mt-8">
                    <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Provider Access by Tier</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {tiers.filter(t => t.id <= 2).map((tier) => (
                        <div key={tier.id} className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-4">
                          <div className="font-medium text-neutral-900 dark:text-white mb-2">{tier.display_name}</div>
                          <div className="space-y-2">
                            {storageProviders
                              .filter(p => p.min_tier_id <= tier.id)
                              .map((provider) => (
                                <div key={provider.provider_key} className="flex items-center gap-2 text-sm">
                                  <div
                                    className="w-4 h-4 rounded flex items-center justify-center"
                                    style={{ backgroundColor: provider.color }}
                                  >
                                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                    </svg>
                                  </div>
                                  <span className={provider.is_active ? 'text-neutral-700 dark:text-neutral-300' : 'text-neutral-400 dark:text-neutral-500 line-through'}>
                                    {provider.display_name}
                                  </span>
                                  {!provider.is_active && (
                                    <span className="text-xs text-neutral-400 dark:text-neutral-500">(coming soon)</span>
                                  )}
                                </div>
                              ))}
                            {storageProviders.filter(p => p.min_tier_id <= tier.id).length === 0 && (
                              <div className="text-sm text-neutral-500 dark:text-neutral-400">No providers available</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Currencies Tab */}
        {activeTab === 'currencies' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Currency Exchange Rates" />
              <CardContent>
                <div className="space-y-4">
                  {/* Info Box */}
                  <div className="bg-semantic-info-bg dark:bg-blue-900/20 border border-semantic-info-border dark:border-blue-800 rounded-lg p-4">
                    <div className="flex items-start">
                      <svg className="h-5 w-5 text-admin-primary dark:text-blue-400 dark:text-blue-400 mt-0.5 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <div className="text-sm text-semantic-info-text dark:text-blue-100 dark:text-blue-100 dark:text-blue-200 dark:text-blue-300">
                        <strong>Exchange Rate Formula:</strong> EUR is the base currency (1.00)
                        <br />
                        <strong>Rate = units of currency per 1 EUR</strong>
                        <br />
                        Example: USD rate of 1.10 means 1 EUR = 1.10 USD
                      </div>
                    </div>
                  </div>

                  {/* Add Currency Button */}
                  <div className="flex justify-end">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setShowAddCurrency(!showAddCurrency)}
                    >
                      {showAddCurrency ? 'Cancel' : '+ Add Currency'}
                    </Button>
                  </div>

                  {/* Add Currency Form */}
                  {showAddCurrency && (
                    <div className="border border-neutral-300 dark:border-neutral-600 rounded-lg p-4 bg-neutral-50 dark:bg-neutral-800">
                      <h3 className="text-lg font-medium text-neutral-900 dark:text-white mb-4">Add New Currency</h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-1">
                            Select Currency
                          </label>
                          <select
                            value={newCurrency.code}
                            onChange={(e) => {
                              const selectedCode = e.target.value
                              const currencyData = currencyList.get(selectedCode)
                              if (currencyData) {
                                setNewCurrency({
                                  ...newCurrency,
                                  code: currencyData.code,
                                  symbol: currencyData.symbol,
                                  name: currencyData.name
                                })
                              }
                            }}
                            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white"
                          >
                            <option value="">-- Select a currency --</option>
                            {Object.values(currencyList.getAll('en_US')).map((currency: {code: string; name: string; symbol: string}) => (
                              <option key={currency.code} value={currency.code}>
                                {currency.code} - {currency.name} ({currency.symbol})
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-1">
                            Exchange Rate (per 1 EUR)
                          </label>
                          <input
                            type="number"
                            step="0.000001"
                            value={newCurrency.exchange_rate || ''}
                            onChange={(e) => setNewCurrency({...newCurrency, exchange_rate: e.target.value ? parseFloat(e.target.value) : null})}
                            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white"
                            placeholder="e.g., 1.10"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-1">
                            Selected: {newCurrency.code ? `${newCurrency.code} (${newCurrency.symbol})` : 'None'}
                          </label>
                          <div className="text-sm text-neutral-600 dark:text-neutral-400">
                            {newCurrency.name || 'Select a currency from the dropdown'}
                          </div>
                        </div>
                      </div>
                      <div className="flex justify-end mt-4 space-x-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setShowAddCurrency(false)
                            setNewCurrency({code: '', symbol: '', name: '', decimal_places: 2, exchange_rate: null, sort_order: 0})
                          }}
                        >
                          Cancel
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => {
                            if (!newCurrency.code || !newCurrency.symbol || !newCurrency.name) {
                              alert('Please fill in all required fields (Code, Symbol, Name)')
                              return
                            }
                            createCurrency(newCurrency)
                            setShowAddCurrency(false)
                            setNewCurrency({code: '', symbol: '', name: '', decimal_places: 2, exchange_rate: null, sort_order: 0})
                          }}
                        >
                          Add Currency
                        </Button>
                      </div>
                    </div>
                  )}

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
                      <thead className="bg-neutral-50 dark:bg-neutral-800">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 uppercase tracking-wider">
                            Currency
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 uppercase tracking-wider">
                            Code
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 uppercase tracking-wider">
                            Symbol
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 uppercase tracking-wider">
                            Exchange Rate (per 1 EUR)
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-neutral-900 divide-y divide-neutral-200 dark:divide-neutral-700">
                        {currencies.map((currency) => (
                          <tr key={currency.code}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-neutral-900 dark:text-white">
                              {currency.name}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-600 dark:text-neutral-300">
                              {currency.code}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-600 dark:text-neutral-300">
                              {currency.symbol}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {editingCurrency?.code === currency.code ? (
                                <input
                                  type="number"
                                  step="0.000001"
                                  value={editingCurrency.rate}
                                  onChange={(e) => setEditingCurrency({...editingCurrency, rate: e.target.value})}
                                  className="w-32 px-2 py-1 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white text-sm"
                                  placeholder="e.g., 1.10"
                                />
                              ) : (
                                <span className="text-sm text-neutral-900 dark:text-white">
                                  {currency.exchange_rate ? currency.exchange_rate.toFixed(6) : (
                                    <span className="text-neutral-400">Not set</span>
                                  )}
                                </span>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {currency.exchange_rate ? (
                                <Badge variant="success">Available</Badge>
                              ) : (
                                <Badge variant="default">Hidden</Badge>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                              {editingCurrency?.code === currency.code ? (
                                <div className="flex space-x-2">
                                  <Button
                                    variant="primary"
                                    size="sm"
                                    onClick={() => {
                                      const rate = parseFloat(editingCurrency.rate)
                                      if (!isNaN(rate) && rate > 0) {
                                        updateCurrency(currency.code, rate)
                                      } else {
                                        alert('Please enter a valid exchange rate')
                                      }
                                    }}
                                  >
                                    Save
                                  </Button>
                                  <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => setEditingCurrency(null)}
                                  >
                                    Cancel
                                  </Button>
                                </div>
                              ) : (
                                <div className="flex space-x-2">
                                  <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => setEditingCurrency({
                                      code: currency.code,
                                      rate: currency.exchange_rate?.toString() || ''
                                    })}
                                  >
                                    Edit
                                  </Button>
                                  {currency.exchange_rate && (
                                    <Button
                                      variant="danger"
                                      size="sm"
                                      onClick={() => {
                                        if (confirm(`Hide ${currency.code} from users? This will set its exchange rate to null.`)) {
                                          updateCurrency(currency.code, null)
                                        }
                                      }}
                                    >
                                      Hide
                                    </Button>
                                  )}
                                  <Button
                                    variant="danger"
                                    size="sm"
                                    onClick={() => deleteCurrency(currency.code)}
                                  >
                                    Delete
                                  </Button>
                                </div>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Health Tab */}
        {activeTab === 'health' && (
          <div className="space-y-6">
            {/* ClamAV Service */}
            {clamavHealth && (
            <Card>
              <CardHeader
                title="ClamAV Antivirus Service"
                action={
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={checkClamavHealth}
                    disabled={restartingClamav}
                  >
                    Refresh Status
                  </Button>
                }
              />
              <CardContent>
                <div className="space-y-4">
                  {/* Status Banner */}
                  <div className={`p-4 rounded-lg ${
                    clamavHealth.available
                      ? 'bg-semantic-success-bg dark:bg-green-900/20 border border-semantic-success-border dark:border-green-800'
                      : 'bg-semantic-error-bg dark:bg-red-900/20 border border-semantic-error-border dark:border-red-800'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`h-3 w-3 rounded-full ${
                          clamavHealth.available ? 'bg-admin-success' : 'bg-admin-danger'
                        } animate-pulse`}></div>
                        <div>
                          <div className={`text-lg font-semibold ${
                            clamavHealth.available
                              ? 'text-green-800 dark:text-green-300'
                              : 'text-semantic-error-text dark:text-red-300 dark:text-red-300'
                          }`}>
                            {clamavHealth.status === 'healthy' ? 'Service Healthy' :
                             clamavHealth.status === 'unavailable' ? 'Service Unavailable' : 'Service Unhealthy'}
                          </div>
                          <div className={`text-sm ${
                            clamavHealth.available
                              ? 'text-admin-success dark:text-green-400 dark:text-green-400'
                              : 'text-admin-danger dark:text-red-400 dark:text-red-400'
                          }`}>
                            {clamavHealth.available
                              ? 'Antivirus protection is active'
                              : 'Antivirus protection is DOWN - uploads using fallback scan'}
                          </div>
                        </div>
                      </div>
                      {!clamavHealth.available && (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={restartClamav}
                          disabled={restartingClamav}
                        >
                          {restartingClamav ? 'Restarting...' : 'Restart Service'}
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Service Details */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <div>
                      <div className="text-xs text-neutral-600 dark:text-neutral-400">Status</div>
                      <div className="text-sm font-medium text-neutral-900 dark:text-white">
                        {clamavHealth.status}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-neutral-600 dark:text-neutral-400">Version</div>
                      <div className="text-sm font-medium text-neutral-900 dark:text-white">
                        {clamavHealth.version || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-neutral-600 dark:text-neutral-400">Connection Type</div>
                      <div className="text-sm font-medium text-neutral-900 dark:text-white">
                        {clamavHealth.connection_type || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-neutral-600 dark:text-neutral-400">Restart Attempts</div>
                      <div className="text-sm font-medium text-neutral-900 dark:text-white">
                        {clamavHealth.restart_attempts}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-neutral-600 dark:text-neutral-400">Last Check</div>
                      <div className="text-sm font-medium text-neutral-900 dark:text-white">
                        {new Date(clamavHealth.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  {/* Error Details */}
                  {clamavHealth.error && (
                    <div className="bg-neutral-100 dark:bg-neutral-800 p-3 rounded">
                      <div className="text-xs font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-1">Error Details:</div>
                      <div className="text-sm text-admin-danger dark:text-red-400 dark:text-red-400 font-mono">
                        {clamavHealth.error}
                      </div>
                    </div>
                  )}

                  {/* Information Box */}
                  <div className="bg-semantic-info-bg dark:bg-blue-900/20 border border-semantic-info-border dark:border-blue-800 rounded-lg p-4">
                    <div className="text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">
                      <strong>Note:</strong> When ClamAV is unavailable, uploads continue to work using heuristic-based scanning only (PDF structure validation, macro detection).
                      Signature-based malware detection is skipped. Restart the service to enable full antivirus protection.
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            )}

            {/* Email Poller Service */}
            {emailPollerHealth && (
              <Card>
                <CardHeader
                  title="Email Poller Service"
                  action={
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={checkEmailPollerHealth}
                      disabled={refreshingEmailHealth}
                    >
                      {refreshingEmailHealth ? 'Refreshing...' : 'Refresh Status'}
                    </Button>
                  }
                />
                <CardContent>
                  <div className="space-y-4">
                    {/* Status Banner */}
                    <div className={`p-4 rounded-lg ${
                      emailPollerHealth.imap_available && emailPollerHealth.status === 'healthy'
                        ? 'bg-semantic-success-bg dark:bg-green-900/20 border border-semantic-success-border dark:border-green-800'
                        : 'bg-semantic-error-bg dark:bg-red-900/20 border border-semantic-error-border dark:border-red-800'
                    }`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`h-3 w-3 rounded-full ${
                            emailPollerHealth.imap_available && emailPollerHealth.status === 'healthy' ? 'bg-admin-success' : 'bg-admin-danger'
                          } animate-pulse`}></div>
                          <div>
                            <div className={`text-lg font-semibold ${
                              emailPollerHealth.imap_available && emailPollerHealth.status === 'healthy'
                                ? 'text-green-800 dark:text-green-300'
                                : 'text-semantic-error-text dark:text-red-300 dark:text-red-300'
                            }`}>
                              {emailPollerHealth.status === 'healthy' ? 'Service Healthy' :
                               emailPollerHealth.status === 'unhealthy' ? 'Service Unhealthy' :
                               emailPollerHealth.status === 'degraded' ? 'Service Degraded' : 'Service Error'}
                            </div>
                            <div className={`text-sm ${
                              emailPollerHealth.imap_available && emailPollerHealth.status === 'healthy'
                                ? 'text-admin-success dark:text-green-400 dark:text-green-400'
                                : 'text-admin-danger dark:text-red-400 dark:text-red-400'
                            }`}>
                              {!emailPollerHealth.polling_task_running
                                ? 'CRITICAL: Polling task is not running - emails will not be processed'
                                : emailPollerHealth.imap_available
                                  ? `Email processing is active - ${emailPollerHealth.unread_emails || 0} unread emails`
                                  : 'Email processing is DOWN - cannot connect to IMAP server'}
                            </div>
                          </div>
                        </div>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={triggerEmailPoll}
                          disabled={pollingEmail}
                        >
                          {pollingEmail ? 'Polling...' : 'Poll Now'}
                        </Button>
                      </div>
                    </div>

                    {/* Service Details */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Status</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {emailPollerHealth.status}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">IMAP Server</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {emailPollerHealth.imap_host}:{emailPollerHealth.imap_port}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Polling Interval</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          Every {emailPollerHealth.polling_interval_seconds}s
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Emails Today</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {emailPollerHealth.total_emails_processed_today}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Consecutive Failures</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {emailPollerHealth.consecutive_failures}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Last Successful Poll</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {emailPollerHealth.last_successful_poll
                            ? new Date(emailPollerHealth.last_successful_poll).toLocaleString()
                            : 'Never'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Polling Task</div>
                        <div className={`text-sm font-medium ${
                          emailPollerHealth.polling_task_running
                            ? 'text-admin-success dark:text-green-400 dark:text-green-400'
                            : 'text-admin-danger dark:text-red-400 dark:text-red-400'
                        }`}>
                          {emailPollerHealth.polling_task_running ? '✓ Running' : '✗ Stopped'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Next Poll</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {emailPollerHealth.next_poll_time
                            ? new Date(emailPollerHealth.next_poll_time).toLocaleTimeString()
                            : 'N/A'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Scheduler</div>
                        <div className={`text-sm font-medium ${
                          emailPollerHealth.scheduler_running
                            ? 'text-admin-success dark:text-green-400 dark:text-green-400'
                            : 'text-admin-danger dark:text-red-400 dark:text-red-400'
                        }`}>
                          {emailPollerHealth.scheduler_running ? '✓ Active' : '✗ Inactive'}
                        </div>
                      </div>
                    </div>

                    {/* Error Details */}
                    {(emailPollerHealth.error || emailPollerHealth.imap_error || emailPollerHealth.last_poll_error) && (
                      <div className="bg-neutral-100 dark:bg-neutral-800 p-3 rounded">
                        <div className="text-xs font-medium text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-1">Error Details:</div>
                        <div className="text-sm text-admin-danger dark:text-red-400 dark:text-red-400 font-mono">
                          {emailPollerHealth.error || emailPollerHealth.imap_error || emailPollerHealth.last_poll_error}
                        </div>
                      </div>
                    )}

                    {/* Warning */}
                    {emailPollerHealth.warning && (
                      <div className="bg-semantic-warning-bg dark:bg-yellow-900/20 border border-semantic-warning-border dark:border-yellow-800 p-3 rounded">
                        <div className="text-sm text-semantic-warning-text dark:text-yellow-300 dark:text-yellow-300">
                          ⚠️ {emailPollerHealth.warning}
                        </div>
                      </div>
                    )}

                    {/* Recent Activity */}
                    {emailPollerHealth.recent_activity && emailPollerHealth.recent_activity.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white mb-2">Recent Activity</div>
                        <div className="space-y-2">
                          {emailPollerHealth.recent_activity.map((activity, idx) => (
                            <div key={idx} className="bg-neutral-50 dark:bg-neutral-800 p-2 rounded text-xs">
                              <div className="flex justify-between items-center">
                                <span className="text-neutral-600 dark:text-neutral-400">
                                  {new Date(activity.received_at).toLocaleString()}
                                </span>
                                <span className={`px-2 py-0.5 rounded ${
                                  activity.status === 'completed' ? 'bg-semantic-success-bg-strong dark:bg-green-900/30 text-semantic-success-text dark:text-green-300' :
                                  activity.status === 'rejected' ? 'bg-semantic-error-bg-strong dark:bg-red-900/30 text-semantic-error-text dark:text-red-300' :
                                  'bg-semantic-warning-bg-strong dark:bg-yellow-900/30 text-semantic-warning-text dark:text-yellow-300'
                                }`}>
                                  {activity.status}
                                </span>
                              </div>
                              <div className="mt-1 text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">
                                From: {activity.sender_email} | Documents: {activity.documents_created}
                                {activity.rejection_reason && ` | Reason: ${activity.rejection_reason}`}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Information Box */}
                    <div className="bg-semantic-info-bg dark:bg-blue-900/20 border border-semantic-info-border dark:border-blue-800 rounded-lg p-4">
                      <div className="text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">
                        <strong>Note:</strong> The email poller checks for new emails every {emailPollerHealth.polling_interval_seconds} seconds.
                        Use the &quot;Poll Now&quot; button to manually trigger an immediate poll. If the service is unhealthy, check IMAP credentials and network connectivity.
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Email Templates Tab */}
        {activeTab === 'email-templates' && (
          <Card>
            <CardHeader title="Email Template Management" />
            <CardContent>
              <div className="space-y-6">
                <div className="bg-semantic-info-bg dark:bg-blue-900/20 border border-semantic-info-border dark:border-blue-800 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
                    Email Notifications
                  </h3>
                  <p className="text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300 mb-4">
                    BoniDoc sends automated email notifications for important user events. All emails are sent via Brevo with GDPR-compliant consent management.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border border-neutral-300 dark:border-neutral-600 rounded-lg p-4">
                    <h4 className="font-semibold text-neutral-900 dark:text-white mb-2">Welcome Email</h4>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
                      Sent when a new user creates an account.
                    </p>
                    <Badge variant="success">Active</Badge>
                  </div>

                  <div className="border border-neutral-300 dark:border-neutral-600 rounded-lg p-4">
                    <h4 className="font-semibold text-neutral-900 dark:text-white mb-2">Drive Connected</h4>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
                      Sent when user successfully connects Google Drive.
                    </p>
                    <Badge variant="success">Active</Badge>
                  </div>

                  <div className="border border-neutral-300 dark:border-neutral-600 rounded-lg p-4">
                    <h4 className="font-semibold text-neutral-900 dark:text-white mb-2">Account Deleted</h4>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
                      Sent when user deletes their account (GDPR mandatory).
                    </p>
                    <Badge variant="success">Active</Badge>
                  </div>

                  <div className="border border-neutral-300 dark:border-neutral-600 rounded-lg p-4">
                    <h4 className="font-semibold text-neutral-900 dark:text-white mb-2">Password Reset</h4>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
                      Sent when user requests a password reset link.
                    </p>
                    <Badge variant="success">Active</Badge>
                  </div>
                </div>

                <div className="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-4">
                  <h4 className="font-semibold text-neutral-900 dark:text-white mb-2">Configuration</h4>
                  <div className="space-y-2 text-sm text-neutral-700 dark:text-neutral-300 dark:text-neutral-300">
                    <div className="flex items-center justify-between">
                      <span>Email Service Provider:</span>
                      <span className="font-medium">Brevo (Sendinblue)</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>From Address:</span>
                      <span className="font-medium">info@bonidoc.com</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Reply-To Address:</span>
                      <span className="font-medium">info@bonidoc.com</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Marketing Emails:</span>
                      <Badge variant="info">User Opt-in Required</Badge>
                    </div>
                  </div>
                </div>

                <div className="flex justify-center pt-4">
                  <Button onClick={() => router.push('/admin/email-templates')}>
                    Go to Advanced Email Template Editor
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Entity Quality Tab */}
        {activeTab === 'entity-quality' && (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Entity Quality ML Configuration" />
              <CardContent>
                <div className="space-y-4">
                  {/* Info Box */}
                  <div className="bg-semantic-info-bg dark:bg-blue-900/20 border border-semantic-info-border dark:border-blue-800 rounded-lg p-4">
                    <div className="text-sm text-semantic-info-text dark:text-blue-100 dark:text-blue-100 dark:text-blue-200 dark:text-blue-300 space-y-3">
                      <div>
                        <strong className="text-base">📊 Entity Quality Scoring System</strong>
                        <p className="mt-1">Multi-factor confidence calculation to filter out garbage entities and keep high-quality extractions.</p>
                      </div>

                      <div>
                        <strong>How it works:</strong>
                        <div className="mt-1 font-mono text-xs bg-semantic-info-bg-strong dark:bg-blue-900 p-2 rounded">
                          Final Confidence = Base Confidence × Multiplier₁ × Multiplier₂ × ... × Multiplierₙ
                        </div>
                        <p className="mt-1">Each entity starts with a base confidence (0.85-0.95), then gets multiplied by various factors based on quality checks.</p>
                      </div>

                      <div>
                        <strong>Parameter Categories:</strong>
                        <ul className="mt-1 ml-4 space-y-1">
                          <li><strong>threshold:</strong> Minimum confidence to accept entity (e.g., ADDRESS ≥ 0.50, EMAIL ≥ 0.50, ORGANIZATION ≥ 0.85)</li>
                          <li><strong>algorithm:</strong> Base confidence for different extraction methods (libpostal: 0.90, regex: 0.70)</li>
                          <li><strong>feature:</strong> Feature flags to enable/disable extraction methods (libpostal_enabled: 1.0 = on)</li>
                          <li><strong>length:</strong> Penalties for too short/long entities (optimal range gets ×1.0, extremes get penalties)</li>
                          <li><strong>pattern:</strong> Bonuses for recognizing keywords (e.g., &quot;Bank&quot; in organization name: ×1.2)</li>
                          <li><strong>dictionary:</strong> Bonuses/penalties based on dictionary word validation (valid word: ×1.3, invalid: ×0.6)</li>
                          <li><strong>entity_type:</strong> Type-specific rules (e.g., all-caps single word ORG: ×0.4 penalty)</li>
                        </ul>
                      </div>

                      <div>
                        <strong>Multiplier Values:</strong>
                        <ul className="mt-1 ml-4 space-y-1">
                          <li>×1.0 = No change (neutral)</li>
                          <li>×1.3 = 30% bonus (rewards good quality)</li>
                          <li>×0.6 = 40% penalty (penalizes likely garbage)</li>
                          <li>×0.4 = 60% penalty (strong filter for all-caps words)</li>
                        </ul>
                      </div>

                      <div>
                        <strong>Example:</strong>
                        <div className="mt-1 font-mono text-xs bg-semantic-info-bg-strong dark:bg-blue-900 p-2 rounded space-y-1">
                          <div>&quot;Kinopolis&quot; (ORGANIZATION):</div>
                          <div>  Base: 0.85 × length_ok(1.0) × dict_valid(1.3) × proper_case(1.1) = <strong>1.00</strong> ✓ ACCEPTED</div>
                          <div className="mt-2">&quot;KINOPOLIS&quot; (ORGANIZATION):</div>
                          <div>  Base: 0.85 × length_ok(1.0) × dict_valid(1.3) × all_caps_penalty(0.4) = <strong>0.44</strong> ✗ REJECTED (&lt; 0.85)</div>
                          <div className="mt-2">&quot;info@example.com&quot; (EMAIL):</div>
                          <div>  Base: 0.95 × length_ok(1.0) × dict_invalid(0.6) = <strong>0.57</strong> ✓ ACCEPTED (≥ 0.50)</div>
                        </div>
                      </div>

                      <div className="pt-2 border-t border-blue-300 dark:border-blue-700">
                        <strong>💡 Debugging:</strong> Check dev backend logs after uploading documents to see detailed scoring for each entity.
                        <br />
                        Look for <code className="bg-semantic-info-bg-strong dark:bg-blue-900 px-1 rounded">[RULE-BASED]</code> and <code className="bg-semantic-info-bg-strong dark:bg-blue-900 px-1 rounded">[ENTITY FILTER]</code> log entries.
                      </div>
                    </div>
                  </div>

                  {/* Group configs by category */}
                  {['threshold', 'algorithm', 'feature', 'ml_threshold', 'length', 'pattern', 'dictionary', 'entity_type'].map(category => {
                    const categoryConfigs = entityQualityConfigs.filter(c => c.category === category)
                    if (categoryConfigs.length === 0) return null

                    return (
                      <div key={category} className="border border-neutral-300 dark:border-neutral-600 rounded-lg p-4">
                        <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-4 capitalize">
                          {category.replace('_', ' ')} Rules
                        </h3>
                        <div className="overflow-x-auto">
                          <table className="min-w-full">
                            <thead className="bg-neutral-50 dark:bg-neutral-800">
                              <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400">
                                  Parameter
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400">
                                  Value
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400">
                                  Description
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-400">
                                  Actions
                                </th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
                              {categoryConfigs.map(config => (
                                <tr key={config.config_key}>
                                  <td className="px-4 py-3 text-sm font-medium text-neutral-900 dark:text-white">
                                    {config.config_key.replace(/^(threshold_|pattern_|type_|length_|dict_)/, '')}
                                  </td>
                                  <td className="px-4 py-3">
                                    {editingConfig?.key === config.config_key ? (
                                      <input
                                        type="number"
                                        step="0.01"
                                        value={editingConfig.value}
                                        onChange={(e) => setEditingConfig({...editingConfig, value: e.target.value})}
                                        className="w-24 px-2 py-1 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white text-sm"
                                      />
                                    ) : (
                                      <span className="text-sm font-mono text-neutral-900 dark:text-white">
                                        {config.config_value}
                                      </span>
                                    )}
                                  </td>
                                  <td className="px-4 py-3 text-xs text-neutral-600 dark:text-neutral-400">
                                    {config.description}
                                  </td>
                                  <td className="px-4 py-3">
                                    {editingConfig?.key === config.config_key ? (
                                      <div className="flex space-x-2">
                                        <Button
                                          variant="primary"
                                          size="sm"
                                          onClick={() => {
                                            const value = parseFloat(editingConfig.value)
                                            if (!isNaN(value)) {
                                              updateEntityQualityConfig(config.config_key, value)
                                            } else {
                                              alert('Please enter a valid number')
                                            }
                                          }}
                                        >
                                          Save
                                        </Button>
                                        <Button
                                          variant="secondary"
                                          size="sm"
                                          onClick={() => setEditingConfig(null)}
                                        >
                                          Cancel
                                        </Button>
                                      </div>
                                    ) : (
                                      <Button
                                        variant="secondary"
                                        size="sm"
                                        onClick={() => setEditingConfig({
                                          key: config.config_key,
                                          value: config.config_value.toString()
                                        })}
                                      >
                                        Edit
                                      </Button>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
