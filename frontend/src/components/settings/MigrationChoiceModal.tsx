'use client'

import { Fragment, useState } from 'react'
import { Dialog, Transition, RadioGroup } from '@headlessui/react'
import { ExclamationTriangleIcon, ArrowPathIcon, TrashIcon } from '@heroicons/react/24/outline'

interface MigrationChoiceModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (choice: 'migrate' | 'fresh') => void
  currentProvider: string
  newProvider: string
  documentCount: number
}

export default function MigrationChoiceModal({
  isOpen,
  onClose,
  onConfirm,
  currentProvider,
  newProvider,
  documentCount
}: MigrationChoiceModalProps) {
  const [selectedChoice, setSelectedChoice] = useState<'migrate' | 'fresh'>('migrate')

  const formatProviderName = (provider: string) => {
    if (provider === 'google_drive') return 'Google Drive'
    if (provider === 'onedrive') return 'OneDrive'
    return provider.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const currentProviderName = formatProviderName(currentProvider)
  const newProviderName = formatProviderName(newProvider)

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
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
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <div className="flex items-center gap-3 mb-4">
                  <ExclamationTriangleIcon className="h-6 w-6 text-amber-500" />
                  <Dialog.Title as="h3" className="text-lg font-medium text-gray-900">
                    Switching Cloud Storage
                  </Dialog.Title>
                </div>

                <div className="mb-6">
                  <p className="text-sm text-gray-500 mb-4">
                    You currently have <strong>{documentCount} document{documentCount !== 1 ? 's' : ''}</strong> stored in <strong>{currentProviderName}</strong>.
                  </p>
                  <p className="text-sm text-gray-500 mb-4">
                    What would you like to do with your existing documents?
                  </p>

                  <RadioGroup value={selectedChoice} onChange={setSelectedChoice}>
                    <RadioGroup.Label className="sr-only">Migration choice</RadioGroup.Label>
                    <div className="space-y-3">
                      {/* Option 1: Migrate */}
                      <RadioGroup.Option
                        value="migrate"
                        className={({ active, checked }) =>
                          `${
                            active
                              ? 'ring-2 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-300'
                              : ''
                          }
                          ${
                            checked ? 'bg-blue-50 border-blue-500' : 'bg-white border-gray-200'
                          }
                            relative flex cursor-pointer rounded-lg border-2 px-5 py-4 focus:outline-none`
                        }
                      >
                        {({ checked }) => (
                          <>
                            <div className="flex w-full items-start justify-between">
                              <div className="flex items-start">
                                <ArrowPathIcon className="h-5 w-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
                                <div className="text-sm">
                                  <RadioGroup.Label
                                    as="p"
                                    className={`font-medium ${
                                      checked ? 'text-blue-900' : 'text-gray-900'
                                    }`}
                                  >
                                    Migrate Everything
                                    <span className="ml-2 inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                                      Recommended
                                    </span>
                                  </RadioGroup.Label>
                                  <RadioGroup.Description
                                    as="span"
                                    className={`inline ${
                                      checked ? 'text-blue-700' : 'text-gray-500'
                                    }`}
                                  >
                                    <span className="block mt-1">
                                      Copy all {documentCount} documents to {newProviderName}, then automatically delete the {currentProviderName} app folder.
                                    </span>
                                    <span className="block mt-2 text-xs">
                                      ✓ All documents preserved<br />
                                      ✓ Old folder automatically deleted<br />
                                      ✓ Clean migration
                                    </span>
                                  </RadioGroup.Description>
                                </div>
                              </div>
                              <div className="shrink-0 text-white">
                                <div
                                  className={`h-5 w-5 rounded-full ${
                                    checked ? 'bg-blue-600' : 'bg-white border-2 border-gray-300'
                                  } flex items-center justify-center`}
                                >
                                  {checked && (
                                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 12 12">
                                      <path d="M3.707 5.293a1 1 0 00-1.414 1.414l1.414-1.414zM5 8l-.707.707a1 1 0 001.414 0L5 8zm4.707-3.293a1 1 0 00-1.414-1.414l1.414 1.414zm-7.414 2l2 2 1.414-1.414-2-2-1.414 1.414zm3.414 2l4-4-1.414-1.414-4 4 1.414 1.414z" />
                                    </svg>
                                  )}
                                </div>
                              </div>
                            </div>
                          </>
                        )}
                      </RadioGroup.Option>

                      {/* Option 2: Start Fresh */}
                      <RadioGroup.Option
                        value="fresh"
                        className={({ active, checked }) =>
                          `${
                            active
                              ? 'ring-2 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-300'
                              : ''
                          }
                          ${
                            checked ? 'bg-amber-50 border-amber-500' : 'bg-white border-gray-200'
                          }
                            relative flex cursor-pointer rounded-lg border-2 px-5 py-4 focus:outline-none`
                        }
                      >
                        {({ checked }) => (
                          <>
                            <div className="flex w-full items-start justify-between">
                              <div className="flex items-start">
                                <TrashIcon className="h-5 w-5 text-amber-600 mt-0.5 mr-3 flex-shrink-0" />
                                <div className="text-sm">
                                  <RadioGroup.Label
                                    as="p"
                                    className={`font-medium ${
                                      checked ? 'text-amber-900' : 'text-gray-900'
                                    }`}
                                  >
                                    Start Fresh
                                  </RadioGroup.Label>
                                  <RadioGroup.Description
                                    as="span"
                                    className={`inline ${
                                      checked ? 'text-amber-700' : 'text-gray-500'
                                    }`}
                                  >
                                    <span className="block mt-1">
                                      Disconnect {currentProviderName} and start empty on {newProviderName}.
                                    </span>
                                    <span className="block mt-2 text-xs">
                                      ⚠ Files remain in {currentProviderName}<br />
                                      ⚠ You'll lose search access in BoniDoc<br />
                                      ⚠ Start with 0 documents
                                    </span>
                                  </RadioGroup.Description>
                                </div>
                              </div>
                              <div className="shrink-0 text-white">
                                <div
                                  className={`h-5 w-5 rounded-full ${
                                    checked ? 'bg-amber-600' : 'bg-white border-2 border-gray-300'
                                  } flex items-center justify-center`}
                                >
                                  {checked && (
                                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 12 12">
                                      <path d="M3.707 5.293a1 1 0 00-1.414 1.414l1.414-1.414zM5 8l-.707.707a1 1 0 001.414 0L5 8zm4.707-3.293a1 1 0 00-1.414-1.414l1.414 1.414zm-7.414 2l2 2 1.414-1.414-2-2-1.414 1.414zm3.414 2l4-4-1.414-1.414-4 4 1.414 1.414z" />
                                    </svg>
                                  )}
                                </div>
                              </div>
                            </div>
                          </>
                        )}
                      </RadioGroup.Option>
                    </div>
                  </RadioGroup>
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    className="flex-1 inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                    onClick={onClose}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="flex-1 inline-flex justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                    onClick={() => onConfirm(selectedChoice)}
                  >
                    Continue
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
