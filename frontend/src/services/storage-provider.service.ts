// frontend/src/services/storage-provider.service.ts
import { apiClient } from './api-client'
import { logger } from '@/lib/logger'

export interface ProviderInfo {
  type: string // 'google_drive', 'onedrive', 'dropbox', 'box'
  name: string // 'Google Drive', 'OneDrive', etc.
  connected: boolean
  is_active: boolean
  enabled: boolean // Whether this provider is available for user's tier
}

export interface ProvidersListResponse {
  providers: ProviderInfo[]
}

export interface AuthorizationUrlResponse {
  authorization_url: string
  state: string
}

export interface OAuthCallbackResponse {
  success: boolean
  provider: string
  message: string
}

export interface ActivateProviderResponse {
  success: boolean
  active_provider: string
  message: string
}

export interface DisconnectProviderResponse {
  success: boolean
  message: string
}

export interface ActiveProviderResponse {
  active_provider: string | null
  provider_name: string | null
}

class StorageProviderService {
  /**
   * Get list of all available storage providers with connection status
   */
  async getAvailableProviders(): Promise<ProvidersListResponse> {
    logger.debug('[StorageProviderService] Getting available providers')

    return await apiClient.get<ProvidersListResponse>(
      '/api/v1/storage/providers/available',
      true
    )
  }

  /**
   * Get OAuth authorization URL for a storage provider
   */
  async getAuthorizationUrl(providerType: string): Promise<AuthorizationUrlResponse> {
    logger.debug('[StorageProviderService] Getting authorization URL for:', providerType)

    return await apiClient.get<AuthorizationUrlResponse>(
      `/api/v1/storage/providers/${providerType}/authorize`,
      true
    )
  }

  /**
   * Handle OAuth callback from storage provider
   */
  async handleOAuthCallback(
    providerType: string,
    code: string,
    state: string
  ): Promise<OAuthCallbackResponse> {
    logger.debug('[StorageProviderService] Handling OAuth callback for:', providerType)

    return await apiClient.post<OAuthCallbackResponse>(
      `/api/v1/storage/providers/${providerType}/callback`,
      {},
      true,
      { params: { code, state } }
    )
  }

  /**
   * Set a connected provider as the active storage provider
   */
  async activateProvider(providerType: string): Promise<ActivateProviderResponse> {
    logger.debug('[StorageProviderService] Activating provider:', providerType)

    return await apiClient.post<ActivateProviderResponse>(
      `/api/v1/storage/providers/${providerType}/activate`,
      {},
      true
    )
  }

  /**
   * Disconnect a storage provider
   */
  async disconnectProvider(providerType: string): Promise<DisconnectProviderResponse> {
    logger.debug('[StorageProviderService] Disconnecting provider:', providerType)

    return await apiClient.post<DisconnectProviderResponse>(
      `/api/v1/storage/providers/${providerType}/disconnect`,
      {},
      true
    )
  }

  /**
   * Get the user's currently active storage provider
   */
  async getActiveProvider(): Promise<ActiveProviderResponse> {
    logger.debug('[StorageProviderService] Getting active provider')

    return await apiClient.get<ActiveProviderResponse>(
      '/api/v1/storage/active-provider',
      true
    )
  }
}

export const storageProviderService = new StorageProviderService()
