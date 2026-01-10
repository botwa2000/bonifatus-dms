// frontend/src/components/settings/ProviderCard.tsx
'use client'

import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import type { ProviderInfo } from '@/services/storage-provider.service'

interface ProviderCardProps {
  provider: ProviderInfo
  loading: boolean
  onConnect: (type: string) => void
  onDisconnect: (type: string) => void
  onActivate: (type: string) => void
}

const PROVIDER_ICONS: Record<string, { path: string; viewBox: string }> = {
  google_drive: {
    path: 'M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a6.033 6.033 0 110-12.064c1.498 0 2.866.549 3.921 1.453l2.814-2.814A9.969 9.969 0 0012.545 2C7.021 2 2.543 6.477 2.543 12s4.478 10 10.002 10c8.396 0 10.249-7.85 9.426-11.748l-9.426-.013z',
    viewBox: '0 0 24 24'
  },
  onedrive: {
    path: 'M13.844 14.12c.195-.502.308-1.047.308-1.62 0-2.485-2.015-4.5-4.5-4.5-.512 0-1.004.086-1.464.244C7.56 6.525 5.898 5.25 3.938 5.25c-2.485 0-4.5 2.015-4.5 4.5 0 .348.04.686.116 1.008A4.123 4.123 0 00-1.562 15c0 2.277 1.845 4.125 4.124 4.125h10.875c2.485 0 4.5-2.015 4.5-4.5 0-2.277-1.69-4.148-3.867-4.424l-.226-.081z',
    viewBox: '-2 4 24 16'
  },
  dropbox: {
    path: 'M12 0L6.545 3.636 12 7.273 6.545 10.909 0 7.273 5.455 3.636 0 0 6.545 3.636 12 0zM0 14.545l5.455-3.636L12 14.545 6.545 18.182 0 14.545zm12 0l5.455-3.636L24 14.545l-6.545 3.637L12 14.545zm5.455-7.272L12 10.909l-5.455-3.636L12 3.636l5.455 3.637z',
    viewBox: '0 0 24 24'
  },
  box: {
    path: 'M2 2h20v20H2V2zm4 4v12h12V6H6z',
    viewBox: '0 0 24 24'
  }
}

const PROVIDER_DESCRIPTIONS: Record<string, string> = {
  google_drive: 'Store your documents securely with Google Drive\'s version control and easy sharing',
  onedrive: 'Save documents to Microsoft OneDrive with enterprise-grade security and collaboration',
  dropbox: 'Sync your documents across devices with Dropbox\'s reliable cloud storage',
  box: 'Securely store and manage documents with Box\'s enterprise content management'
}

export function ProviderCard({
  provider,
  loading,
  onConnect,
  onDisconnect,
  onActivate
}: ProviderCardProps) {
  const icon = PROVIDER_ICONS[provider.type] || PROVIDER_ICONS.google_drive
  const description = PROVIDER_DESCRIPTIONS[provider.type] || 'Cloud storage provider'

  // Determine card styling based on connection status
  const cardBgColor = provider.connected
    ? 'bg-semantic-success-bg dark:bg-green-900/20'
    : 'bg-white dark:bg-neutral-800'
  const cardBorderColor = provider.connected
    ? 'border-semantic-success-border dark:border-green-800'
    : 'border-neutral-200 dark:border-neutral-700'
  const iconColor = provider.connected
    ? 'text-admin-success dark:text-green-400'
    : 'text-neutral-400 dark:text-neutral-500'

  return (
    <div className="space-y-3">
      <div className={`flex items-center justify-between p-4 ${cardBgColor} border ${cardBorderColor} rounded-lg`}>
        <div className="flex items-center space-x-3 flex-1">
          <div className="flex-shrink-0">
            <svg className={`h-10 w-10 ${iconColor}`} fill="currentColor" viewBox={icon.viewBox}>
              <path d={icon.path} />
            </svg>
          </div>
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <p className="text-sm font-medium text-neutral-900 dark:text-white">
                {provider.name}
              </p>
              {provider.is_active && (
                <Badge variant="success">Active</Badge>
              )}
              {!provider.enabled && (
                <Badge variant="warning">Upgrade Required</Badge>
              )}
            </div>
            <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5">
              {provider.connected ? 'Connected' : description}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {!provider.connected ? (
            <Button
              variant="primary"
              onClick={() => onConnect(provider.type)}
              disabled={loading || !provider.enabled}
            >
              {loading ? 'Connecting...' : 'Connect'}
            </Button>
          ) : (
            <>
              {!provider.is_active && (
                <Button
                  variant="primary"
                  onClick={() => onActivate(provider.type)}
                  disabled={loading}
                >
                  {loading ? 'Setting...' : 'Set as Active'}
                </Button>
              )}
              <Button
                variant="secondary"
                onClick={() => onDisconnect(provider.type)}
                disabled={loading}
              >
                {loading ? 'Disconnecting...' : 'Disconnect'}
              </Button>
            </>
          )}
        </div>
      </div>

      {provider.connected && !provider.is_active && (
        <p className="text-xs text-neutral-600 dark:text-neutral-400 px-1">
          This provider is connected but not active. Set it as active to use it for new document uploads.
        </p>
      )}

      {provider.is_active && (
        <p className="text-xs text-neutral-600 dark:text-neutral-400 px-1">
          Your documents are automatically saved to {provider.name} with full version history and sharing capabilities.
        </p>
      )}
    </div>
  )
}
