// frontend/src/components/ui/Modal.tsx
export function Modal({ 
  isOpen, 
  children,
  maxWidth = 'max-w-lg'
}: { 
  isOpen: boolean
  children: React.ReactNode
  maxWidth?: string
}) {
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className={`bg-white rounded-lg ${maxWidth} w-full p-6`}>
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
    <div className="flex items-center justify-between mb-4">
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
  return <div className="space-y-4">{children}</div>
}

export function ModalFooter({ 
  children 
}: { 
  children: React.ReactNode 
}) {
  return <div className="flex space-x-3 pt-4">{children}</div>
}