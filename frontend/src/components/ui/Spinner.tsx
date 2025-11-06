// frontend/src/components/ui/Spinner.tsx
export function Spinner({
  size = 'md',
  className = ''
}: {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}) {
  const sizeClasses = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-4',
    lg: 'h-12 w-12 border-4'
  }

  return (
    <div
      className={`${sizeClasses[size]} animate-spin rounded-full border-admin-primary border-t-transparent ${className}`}
      role="status"
      aria-label="Loading"
    />
  )
}

export function SpinnerOverlay({
  message = 'Loading...'
}: {
  message?: string
}) {
  return (
    <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10 rounded-lg">
      <div className="text-center">
        <Spinner className="mx-auto" />
        <p className="mt-2 text-sm text-neutral-600">{message}</p>
      </div>
    </div>
  )
}

export function SpinnerFullPage({
  message = 'Loading...'
}: {
  message?: string
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50">
      <div className="text-center">
        <Spinner className="mx-auto" />
        <p className="mt-4 text-sm text-neutral-600">{message}</p>
      </div>
    </div>
  )
}
