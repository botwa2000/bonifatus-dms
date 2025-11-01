// frontend/src/components/ui/Modal.tsx
export function Modal({
  isOpen,
  onClose,
  children,
  maxWidth = 'max-w-lg'
}: {
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
  maxWidth?: string
}) {
  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className={`bg-white rounded-lg ${maxWidth} w-full max-h-[90vh] flex flex-col`}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}

export function ModalHeader({
  title,
  onClose
}: {
  title: string
  onClose?: () => void
}) {
  return (
    <div className="flex items-center justify-between p-6 pb-4 flex-shrink-0">
      <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
      {onClose && (
        <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  )
}

export function ModalContent({
  children
}: {
  children: React.ReactNode
}) {
  return <div className="px-6 pb-6 overflow-y-auto flex-1 space-y-4">{children}</div>
}

export function ModalFooter({
  children
}: {
  children: React.ReactNode
}) {
  return <div className="flex space-x-3 px-6 pb-6 pt-4 flex-shrink-0 border-t border-neutral-200">{children}</div>
}