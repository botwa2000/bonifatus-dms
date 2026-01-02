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

export interface ConnectIntentResponse {
  needs_migration: boolean
  current_provider: string | null
  document_count: number
}

export interface MigrationStatusResponse {
  migration_id: string
  status: 'pending' | 'processing' | 'completed' | 'partial' | 'failed'
  from_provider: string
  to_provider: string
  total_documents: number
  processed_documents: number
  successful_documents: number
  failed_documents: number
  current_document: string | null
  folder_deleted?: boolean
  folder_deletion_attempted?: boolean
  error_message?: string
  started_at?: string
  completed_at?: string
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
   * Check if connecting this provider requires migration
   */
  async checkConnectIntent(providerType: string): Promise<ConnectIntentResponse> {
    logger.debug('[StorageProviderService] Checking connect intent for:', providerType)

    return await apiClient.get<ConnectIntentResponse>(
      `/api/v1/storage/providers/${providerType}/connect-intent`,
      true
    )
  }

  /**
   * Handle OAuth callback from storage provider
   */
  async handleOAuthCallback(
    providerType: string,
    code: string,
    state: string,
    migrationChoice?: 'migrate' | 'fresh'
  ): Promise<OAuthCallbackResponse & { migration_id?: string; migration_status?: string }> {
    logger.debug('[StorageProviderService] Handling OAuth callback for:', providerType)
    logger.debug('[StorageProviderService] Migration choice:', migrationChoice)

    const params: Record<string, string> = { code, state }
    if (migrationChoice) {
      params.migration_choice = migrationChoice
    }

    return await apiClient.post<OAuthCallbackResponse & { migration_id?: string; migration_status?: string }>(
      `/api/v1/storage/providers/${providerType}/callback`,
      {},
      true,
      { params }
    )
  }

  /**
   * Get migration status by ID
   */
  async getMigrationStatus(migrationId: string): Promise<MigrationStatusResponse> {
    logger.debug('[StorageProviderService] Getting migration status for:', migrationId)

    return await apiClient.get<MigrationStatusResponse>(
      `/api/v1/storage/migration-status/${migrationId}`,
      true
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

  /**
   * Get document counts by storage provider
   */
  async getDocumentCounts(): Promise<{ document_counts: Record<string, number>, total_documents: number }> {
    logger.debug('[StorageProviderService] Getting document counts')

    return await apiClient.get(
      '/api/v1/storage/providers/document-counts',
      true
    )
  }

  /**
   * Initiate migration between already-connected providers
   */
  async initiateMigration(fromProvider: string, toProvider: string): Promise<{
    success: boolean
    migration_id: string
    status: string
    from_provider: string
    to_provider: string
    document_count: number
  }> {
    logger.debug('[StorageProviderService] Initiating migration:', { fromProvider, toProvider })

    return await apiClient.post(
      '/api/v1/storage/providers/migrate',
      { from_provider: fromProvider, to_provider: toProvider },
      true
    )
  }
}

export const storageProviderService = new StorageProviderService()
