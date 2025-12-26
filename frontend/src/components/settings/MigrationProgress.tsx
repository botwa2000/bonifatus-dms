'use client'

import { Fragment, useEffect, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/auth-context'

interface MigrationProgressProps {
  migrationId: string
  isOpen: boolean
  onClose: () => void
  fromProvider: string
  toProvider: string
}

interface MigrationStatus {
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
}

export default function MigrationProgress({
  migrationId,
  isOpen,
  onClose,
  fromProvider,
  toProvider
}: MigrationProgressProps) {
  const { getAccessToken } = useAuth()
  const [status, setStatus] = useState<MigrationStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  const formatProviderName = (provider: string) => {
    if (provider === 'google_drive') return 'Google Drive'
    if (provider === 'onedrive') return 'OneDrive'
    return provider.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  useEffect(() => {
    if (!isOpen || !migrationId) return

    const pollMigrationStatus = async () => {
      try {
        const token = await getAccessToken()
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/storage/migration-status/${migrationId}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        )

        if (!response.ok) {
          throw new Error('Failed to fetch migration status')
        }

        const data: MigrationStatus = await response.json()
        setStatus(data)

        // Continue polling if still processing
        if (data.status === 'pending' || data.status === 'processing') {
          setTimeout(pollMigrationStatus, 2000) // Poll every 2 seconds
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch migration status')
      }
    }

    pollMigrationStatus()
  }, [migrationId, isOpen, getAccessToken])

  if (!status) {
    return (
      <Transition appear show={isOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={() => {}}>
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black bg-opacity-25" />
          </Transition.Child>

          <div className="fixed inset-0 overflow-y-auto">
            <div className="flex min-h-full items-center justify-center p-4">
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-center shadow-xl transition-all">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-sm text-gray-500">Loading migration status...</p>
              </Dialog.Panel>
            </div>
          </div>
        </Dialog>
      </Transition>
    )
  }

  const percentage = status.total_documents > 0
    ? Math.round((status.processed_documents / status.total_documents) * 100)
    : 0

  const isComplete = status.status === 'completed' || status.status === 'partial' || status.status === 'failed'
  const canClose = isComplete

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={canClose ? onClose : () => {}}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 shadow-xl transition-all">
                {/* Status Icon */}
                <div className="flex justify-center mb-4">
                  {status.status === 'completed' && (
                    <CheckCircleIcon className="h-12 w-12 text-green-500" />
                  )}
                  {status.status === 'partial' && (
                    <ExclamationTriangleIcon className="h-12 w-12 text-amber-500" />
                  )}
                  {status.status === 'failed' && (
                    <XCircleIcon className="h-12 w-12 text-red-500" />
                  )}
                  {(status.status === 'pending' || status.status === 'processing') && (
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                  )}
                </div>

                {/* Title */}
                <Dialog.Title as="h3" className="text-lg font-medium text-center text-gray-900 mb-2">
                  {status.status === 'completed' && 'Migration Complete!'}
                  {status.status === 'partial' && 'Migration Partially Complete'}
                  {status.status === 'failed' && 'Migration Failed'}
                  {status.status === 'pending' && 'Preparing Migration...'}
                  {status.status === 'processing' && 'Migrating Documents...'}
                </Dialog.Title>

                {/* Provider Info */}
                <p className="text-sm text-center text-gray-500 mb-6">
                  {formatProviderName(status.from_provider)} → {formatProviderName(status.to_provider)}
                </p>

                {/* Progress Bar */}
                {!isComplete && (
                  <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-600 mb-2">
                      <span>Progress</span>
                      <span>{percentage}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div
                        className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                )}

                {/* Statistics */}
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">Total Documents</p>
                      <p className="font-semibold text-gray-900">{status.total_documents}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Processed</p>
                      <p className="font-semibold text-gray-900">{status.processed_documents}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Successful</p>
                      <p className="font-semibold text-green-600">{status.successful_documents}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Failed</p>
                      <p className="font-semibold text-red-600">{status.failed_documents}</p>
                    </div>
                  </div>
                </div>

                {/* Current Document */}
                {status.current_document && status.status === 'processing' && (
                  <div className="mb-4">
                    <p className="text-xs text-gray-500 mb-1">Currently processing:</p>
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {status.current_document}
                    </p>
                  </div>
                )}

                {/* Folder Deletion Status */}
                {isComplete && status.folder_deletion_attempted && (
                  <div className={`mb-4 p-3 rounded-lg ${
                    status.folder_deleted ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'
                  }`}>
                    <p className={`text-sm ${
                      status.folder_deleted ? 'text-green-800' : 'text-amber-800'
                    }`}>
                      {status.folder_deleted ? (
                        <>✓ Old {formatProviderName(status.from_provider)} folder deleted</>
                      ) : (
                        <>⚠ Old {formatProviderName(status.from_provider)} folder not deleted</>
                      )}
                    </p>
                  </div>
                )}

                {/* Error Message */}
                {error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                )}

                {/* Completion Message */}
                {status.status === 'completed' && (
                  <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800">
                      All documents migrated successfully! Your {formatProviderName(status.from_provider)} folder has been automatically deleted.
                    </p>
                  </div>
                )}

                {status.status === 'partial' && (
                  <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-sm text-amber-800">
                      Some documents could not be migrated. Your {formatProviderName(status.from_provider)} remains connected for the failed documents.
                    </p>
                  </div>
                )}

                {status.status === 'failed' && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-800">
                      {status.error_message || 'Migration failed. Your documents remain in ' + formatProviderName(status.from_provider) + '.'}
                    </p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  {canClose && (
                    <button
                      type="button"
                      className="flex-1 inline-flex justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                      onClick={onClose}
                    >
                      Close
                    </button>
                  )}
                  {!canClose && (
                    <div className="flex-1 text-center text-sm text-gray-500">
                      Please wait while migration is in progress...
                    </div>
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
