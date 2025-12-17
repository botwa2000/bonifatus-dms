// frontend/src/contexts/delegate-context.tsx
'use client'

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { delegateService, type GrantedAccess } from '@/services/delegate.service'
import { useAuth } from './auth-context'

interface DelegateContextType {
  actingAsUserId: string | null
  actingAsUser: GrantedAccess | null
  grantedAccess: GrantedAccess[]
  isLoadingAccess: boolean
  switchToAccount: (userId: string | null) => void
  loadGrantedAccess: () => Promise<void>
  isActingAsDelegate: boolean
}

const DelegateContext = createContext<DelegateContextType | undefined>(undefined)

export function DelegateProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated } = useAuth()
  const [actingAsUserId, setActingAsUserId] = useState<string | null>(null)
  const [grantedAccess, setGrantedAccess] = useState<GrantedAccess[]>([])
  const [isLoadingAccess, setIsLoadingAccess] = useState(false)

  // Load granted access when user logs in
  const loadGrantedAccess = useCallback(async () => {
    if (!isAuthenticated) {
      setGrantedAccess([])
      return
    }

    try {
      setIsLoadingAccess(true)
      const response = await delegateService.listGrantedAccess()
      setGrantedAccess(response.granted_access)
    } catch (error) {
      console.error('Failed to load granted access:', error)
      setGrantedAccess([])
    } finally {
      setIsLoadingAccess(false)
    }
  }, [isAuthenticated])

  // Load granted access on auth change
  useEffect(() => {
    if (isAuthenticated && user) {
      loadGrantedAccess()
    } else {
      setGrantedAccess([])
      setActingAsUserId(null)
    }
  }, [isAuthenticated, user, loadGrantedAccess])

  // Switch to a different account (or back to own account)
  const switchToAccount = useCallback((userId: string | null) => {
    setActingAsUserId(userId)

    // Store in localStorage for persistence across page loads
    if (userId) {
      localStorage.setItem('actingAsUserId', userId)
    } else {
      localStorage.removeItem('actingAsUserId')
    }
  }, [])

  // Restore acting-as state from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('actingAsUserId')
    if (stored && isAuthenticated) {
      setActingAsUserId(stored)
    }
  }, [isAuthenticated])

  // Find the current acting-as user details
  const actingAsUser = actingAsUserId
    ? grantedAccess.find(access => access.owner_user_id === actingAsUserId) || null
    : null

  const isActingAsDelegate = actingAsUserId !== null && actingAsUser !== null

  const value: DelegateContextType = {
    actingAsUserId,
    actingAsUser,
    grantedAccess,
    isLoadingAccess,
    switchToAccount,
    loadGrantedAccess,
    isActingAsDelegate
  }

  return (
    <DelegateContext.Provider value={value}>
      {children}
    </DelegateContext.Provider>
  )
}

export function useDelegate() {
  const context = useContext(DelegateContext)
  if (context === undefined) {
    throw new Error('useDelegate must be used within a DelegateProvider')
  }
  return context
}
