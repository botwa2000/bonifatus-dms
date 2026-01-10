// frontend/src/components/DocumentSourceFilter.tsx
'use client'

import { useState, useEffect } from 'react'
import { delegateService, GrantedAccess } from '@/services/delegate.service'
import { logger } from '@/lib/logger'

interface DocumentSourceFilterProps {
  onFilterChange: (includeOwn: boolean, sharedOwnerIds: string[]) => void
}

export default function DocumentSourceFilter({ onFilterChange }: DocumentSourceFilterProps) {
  const [grantedAccess, setGrantedAccess] = useState<GrantedAccess[]>([])
  const [loading, setLoading] = useState(true)
  const [includeOwn, setIncludeOwn] = useState(true)
  const [selectedOwners, setSelectedOwners] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadGrantedAccess()
  }, [])

  const loadGrantedAccess = async () => {
    try {
      setLoading(true)
      const response = await delegateService.listGrantedAccess()
      setGrantedAccess(response.granted_access)
    } catch (error) {
      logger.error('Failed to load granted access:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleOwnChange = (checked: boolean) => {
    setIncludeOwn(checked)
    onFilterChange(checked, Array.from(selectedOwners))
  }

  const handleOwnerToggle = (ownerId: string) => {
    const newSelection = new Set(selectedOwners)
    if (newSelection.has(ownerId)) {
      newSelection.delete(ownerId)
    } else {
      newSelection.add(ownerId)
    }
    setSelectedOwners(newSelection)
    onFilterChange(includeOwn, Array.from(newSelection))
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-neutral-200 p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-neutral-200 rounded w-32 mb-4"></div>
          <div className="h-8 bg-neutral-200 rounded mb-2"></div>
        </div>
      </div>
    )
  }

  // Don't show filter if no granted access
  if (grantedAccess.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-lg border border-neutral-200 p-4 mb-6">
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-white mb-3 flex items-center">
        <svg className="h-5 w-5 mr-2 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
        Document Sources
      </h3>

      <div className="space-y-2">
        {/* My Documents */}
        <label className="flex items-center space-x-3 p-2 rounded-md hover:bg-neutral-50 cursor-pointer transition-colors">
          <input
            type="checkbox"
            checked={includeOwn}
            onChange={(e) => handleOwnChange(e.target.checked)}
            className="h-4 w-4 text-blue-600 border-neutral-300 rounded focus:ring-blue-500"
          />
          <div className="flex items-center space-x-2 flex-1">
            <svg className="h-4 w-4 text-neutral-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <span className="text-sm font-medium text-neutral-900 dark:text-white">My Documents</span>
          </div>
        </label>

        {/* Shared Documents */}
        {grantedAccess.map((access) => (
          <label
            key={access.id}
            className="flex items-center space-x-3 p-2 rounded-md hover:bg-neutral-50 cursor-pointer transition-colors"
          >
            <input
              type="checkbox"
              checked={selectedOwners.has(access.owner_user_id)}
              onChange={() => handleOwnerToggle(access.owner_user_id)}
              className="h-4 w-4 text-blue-600 border-neutral-300 rounded focus:ring-blue-500"
            />
            <div className="flex items-center space-x-2 flex-1">
              <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <span className="text-sm font-medium text-neutral-900 dark:text-white">Shared: {access.owner_name}</span>
            </div>
            <span className="text-xs text-neutral-500 bg-blue-50 px-2 py-0.5 rounded">
              {access.role}
            </span>
          </label>
        ))}
      </div>

      <div className="mt-4 pt-3 border-t border-neutral-200">
        <p className="text-xs text-neutral-600">
          {includeOwn && selectedOwners.size === 0 && 'Showing your documents only'}
          {!includeOwn && selectedOwners.size > 0 && `Showing ${selectedOwners.size} shared source${selectedOwners.size > 1 ? 's' : ''}`}
          {includeOwn && selectedOwners.size > 0 && `Showing your documents + ${selectedOwners.size} shared source${selectedOwners.size > 1 ? 's' : ''}`}
          {!includeOwn && selectedOwners.size === 0 && 'No sources selected'}
        </p>
      </div>
    </div>
  )
}
