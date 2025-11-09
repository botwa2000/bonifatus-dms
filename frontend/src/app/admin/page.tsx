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
}

interface TierPlan {
  id: number
  name: string
  display_name: string
  price_monthly_cents: number
  storage_quota_bytes: number
  max_file_size_bytes: number
  max_documents: number | null
  bulk_operations_enabled: boolean
  is_active: boolean
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

export default function AdminDashboard() {
  const { user, isLoading, loadUser } = useAuth()
  const router = useRouter()

  const [stats, setStats] = useState<SystemStats | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [tiers, setTiers] = useState<TierPlan[]>([])
  const [clamavHealth, setClamavHealth] = useState<ClamAVHealth | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'tiers' | 'health'>('overview')
  const [loadingData, setLoadingData] = useState(true)
  const [editingTier, setEditingTier] = useState<TierPlan | null>(null)
  const [restartingClamav, setRestartingClamav] = useState(false)

  // Load user on mount to ensure fresh data
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

    if (user && user.is_admin) {
      loadData()
    }
  }, [user, isLoading, router])

  const loadData = async () => {
    try {
      setLoadingData(true)

      // Load stats
      const statsData = await apiClient.get<SystemStats>('/admin/stats')
      setStats(statsData)

      // Load users
      const usersData = await apiClient.get<{ users: User[] }>('/admin/users', false, {
        params: {
          page: '1',
          page_size: '100'
        }
      })
      setUsers(usersData.users)

      // Load tiers
      const tiersData = await apiClient.get<{ tiers: TierPlan[] }>('/admin/tiers')
      setTiers(tiersData.tiers)

      // Load ClamAV health
      const healthData = await apiClient.get<ClamAVHealth>('/admin/health/clamav')
      setClamavHealth(healthData)

    } catch (error) {
      console.error('Failed to load admin data:', error)
    } finally {
      setLoadingData(false)
    }
  }

  const checkClamavHealth = async () => {
    try {
      const healthData = await apiClient.get<ClamAVHealth>('/admin/health/clamav')
      setClamavHealth(healthData)
    } catch (error) {
      console.error('Failed to check ClamAV health:', error)
    }
  }

  const restartClamav = async () => {
    try {
      setRestartingClamav(true)
      const result = await apiClient.post<{ success: boolean; error?: string }>('/admin/health/clamav/restart', {})

      if (result.success) {
        alert('ClamAV restarted successfully!')
      } else {
        alert(`Restart failed: ${result.error}`)
      }

      // Refresh health status
      await checkClamavHealth()
    } catch (error) {
      console.error('Failed to restart ClamAV:', error)
      alert('Failed to restart ClamAV service')
    } finally {
      setRestartingClamav(false)
    }
  }

  const updateTier = async (tierId: number, updates: Partial<TierPlan>) => {
    try {
      await apiClient.patch(`/admin/tiers/${tierId}`, updates)
      await loadData()
      setEditingTier(null)
    } catch (error) {
      console.error('Failed to update tier:', error)
      alert('Failed to update tier configuration')
    }
  }

  const updateUserTier = async (userId: string, newTierId: number) => {
    try {
      await apiClient.patch(`/admin/users/${userId}/tier`, { tier_id: newTierId })
      await loadData()
    } catch (error) {
      console.error('Failed to update user tier:', error)
      alert('Failed to update user tier')
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
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'users'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
            }`}
          >
            Users
          </button>
          <button
            onClick={() => setActiveTab('tiers')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'tiers'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
            }`}
          >
            Tier Configuration
          </button>
          <button
            onClick={() => setActiveTab('health')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'health'
                ? 'text-admin-primary border-b-2 border-admin-primary'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
            }`}
          >
            System Health
            {clamavHealth && !clamavHealth.available && (
              <span className="ml-2 inline-block h-2 w-2 rounded-full bg-red-500"></span>
            )}
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
                  <div className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">
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
                  <div className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">
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
                  <div className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">
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
                      <span className="text-neutral-700 dark:text-neutral-300">{tierName}</span>
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
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-neutral-100 dark:bg-neutral-800">
                    <tr>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300">Email</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300">Name</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300">Tier</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300">Documents</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300">Storage</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300">Status</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id} className="border-t border-neutral-200 dark:border-neutral-700">
                        <td className="px-4 py-3 text-sm text-neutral-900 dark:text-white">{user.email}</td>
                        <td className="px-4 py-3 text-sm text-neutral-700 dark:text-neutral-300">{user.full_name}</td>
                        <td className="px-4 py-3 text-sm">
                          <select
                            value={user.tier_id}
                            onChange={(e) => updateUserTier(user.id, parseInt(e.target.value))}
                            className="px-2 py-1 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white text-sm"
                          >
                            {tiers.map((tier) => (
                              <option key={tier.id} value={tier.id}>{tier.display_name}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-4 py-3 text-sm text-neutral-700 dark:text-neutral-300">{user.document_count}</td>
                        <td className="px-4 py-3 text-sm text-neutral-700 dark:text-neutral-300">
                          {formatBytes(user.storage_used_bytes)} / {formatBytes(user.storage_quota_bytes)}
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
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                            Monthly Price (cents)
                          </label>
                          <input
                            type="number"
                            defaultValue={tier.price_monthly_cents}
                            onChange={(e) => setEditingTier({ ...tier, price_monthly_cents: parseInt(e.target.value) })}
                            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                            Storage Quota (bytes)
                          </label>
                          <input
                            type="number"
                            defaultValue={tier.storage_quota_bytes}
                            onChange={(e) => setEditingTier({ ...tier, storage_quota_bytes: parseInt(e.target.value) })}
                            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                            Max File Size (bytes)
                          </label>
                          <input
                            type="number"
                            defaultValue={tier.max_file_size_bytes}
                            onChange={(e) => setEditingTier({ ...tier, max_file_size_bytes: parseInt(e.target.value) })}
                            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                            Max Documents (null = unlimited)
                          </label>
                          <input
                            type="number"
                            defaultValue={tier.max_documents || ''}
                            placeholder="unlimited"
                            onChange={(e) => setEditingTier({ ...tier, max_documents: e.target.value ? parseInt(e.target.value) : null })}
                            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                          />
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={editingTier.bulk_operations_enabled}
                            onChange={(e) => setEditingTier({ ...tier, bulk_operations_enabled: e.target.checked })}
                            className="rounded"
                          />
                          <span className="text-sm text-neutral-700 dark:text-neutral-300">Bulk Operations</span>
                        </label>
                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={editingTier.is_active}
                            onChange={(e) => setEditingTier({ ...tier, is_active: e.target.checked })}
                            className="rounded"
                          />
                          <span className="text-sm text-neutral-700 dark:text-neutral-300">Active</span>
                        </label>
                      </div>
                      <Button onClick={() => updateTier(tier.id, editingTier)}>
                        Save Changes
                      </Button>
                    </div>
                  ) : (
                    /* View Mode */
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Price</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {formatPrice(tier.price_monthly_cents)}/month
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Storage Quota</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {formatBytes(tier.storage_quota_bytes)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Max File Size</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {formatBytes(tier.max_file_size_bytes)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Max Documents</div>
                        <div className="text-sm font-medium text-neutral-900 dark:text-white">
                          {tier.max_documents || 'Unlimited'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">Features</div>
                        <div className="text-sm text-neutral-700 dark:text-neutral-300 space-x-2">
                          {tier.bulk_operations_enabled && <Badge variant="success">Bulk</Badge>}
                          {tier.is_active && <Badge variant="info">Active</Badge>}
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Health Tab */}
        {activeTab === 'health' && clamavHealth && (
          <div className="space-y-6">
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
                      ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                      : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`h-3 w-3 rounded-full ${
                          clamavHealth.available ? 'bg-green-500' : 'bg-red-500'
                        } animate-pulse`}></div>
                        <div>
                          <div className={`text-lg font-semibold ${
                            clamavHealth.available
                              ? 'text-green-800 dark:text-green-300'
                              : 'text-red-800 dark:text-red-300'
                          }`}>
                            {clamavHealth.status === 'healthy' ? 'Service Healthy' :
                             clamavHealth.status === 'unavailable' ? 'Service Unavailable' : 'Service Unhealthy'}
                          </div>
                          <div className={`text-sm ${
                            clamavHealth.available
                              ? 'text-green-600 dark:text-green-400'
                              : 'text-red-600 dark:text-red-400'
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
                      <div className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">Error Details:</div>
                      <div className="text-sm text-red-600 dark:text-red-400 font-mono">
                        {clamavHealth.error}
                      </div>
                    </div>
                  )}

                  {/* Information Box */}
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <div className="text-sm text-neutral-700 dark:text-neutral-300">
                      <strong>Note:</strong> When ClamAV is unavailable, uploads continue to work using heuristic-based scanning only (PDF structure validation, macro detection).
                      Signature-based malware detection is skipped. Restart the service to enable full antivirus protection.
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
