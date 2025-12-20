// frontend/src/services/delegate.service.ts
import { apiClient } from './api-client'

// Types
export interface DelegateInviteRequest {
  email: string
  role: 'viewer' | 'editor' | 'owner'
  access_expires_at?: string
  allow_unregistered?: boolean
}

export interface Delegate {
  id: string
  owner_user_id: string
  delegate_user_id: string | null
  delegate_email: string
  role: string
  status: 'pending' | 'active' | 'revoked'
  invitation_sent_at: string | null
  invitation_expires_at: string | null
  invitation_accepted_at: string | null
  access_expires_at: string | null
  last_accessed_at: string | null
  created_at: string
  updated_at: string
  revoked_at: string | null
}

export interface GrantedAccess {
  id: string
  owner_user_id: string
  owner_email: string
  owner_name: string
  role: string
  status: string
  access_expires_at: string | null
  last_accessed_at: string | null
  granted_at: string
}

export interface DelegateListResponse {
  delegates: Delegate[]
  total: number
}

export interface PendingInvitation {
  id: string
  owner_user_id: string
  owner_email: string
  owner_name: string
  role: string
  status: string
  invitation_sent_at: string | null
  invitation_expires_at: string | null
}

export interface PendingInvitationListResponse {
  invitations: PendingInvitation[]
  total: number
}

export interface GrantedAccessListResponse {
  granted_access: GrantedAccess[]
  total: number
}

export interface AcceptInvitationResponse {
  success: boolean
  owner_name: string
  owner_email: string
  role: string
  message: string
}

class DelegateService {
  /**
   * Invite a delegate to access your documents (Pro tier only)
   */
  async inviteDelegate(request: DelegateInviteRequest): Promise<Delegate> {
    return apiClient.post<Delegate>('/api/v1/delegates/invite', request, true)
  }

  /**
   * List all delegates you have invited
   */
  async listMyDelegates(): Promise<DelegateListResponse> {
    return apiClient.get<DelegateListResponse>('/api/v1/delegates', true)
  }

  /**
   * List all owners who have granted you access to their documents
   */
  async listGrantedAccess(): Promise<GrantedAccessListResponse> {
    return apiClient.get<GrantedAccessListResponse>('/api/v1/delegates/granted-to-me', true)
  }

  /**
   * Accept a delegate invitation
   */
  async acceptInvitation(token: string): Promise<AcceptInvitationResponse> {
    return apiClient.post<AcceptInvitationResponse>(
      `/api/v1/delegates/accept/${token}`,
      {},
      true
    )
  }

  /**
   * Revoke a delegate's access to your documents
   */
  async revokeAccess(delegateId: string): Promise<{ success: boolean; message: string }> {
    return apiClient.delete<{ success: boolean; message: string }>(
      `/api/v1/delegates/${delegateId}`,
      true
    )
  }

  /**
   * Get all pending invitations for the current user
   */
  async getPendingInvitations(): Promise<PendingInvitationListResponse> {
    return apiClient.get<PendingInvitationListResponse>('/api/v1/delegates/pending-invitations', true)
  }

  /**
   * Accept or decline a delegate invitation
   */
  async respondToInvitation(
    invitationId: string,
    action: 'accept' | 'decline'
  ): Promise<{ success: boolean; message: string; owner_name: string; owner_email: string; role?: string }> {
    return apiClient.post(
      `/api/v1/delegates/respond/${invitationId}`,
      { action },
      true
    )
  }
}

export const delegateService = new DelegateService()
