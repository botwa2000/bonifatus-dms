// frontend/src/components/ui/StatusBadge.tsx
export type Status = 'active' | 'inactive' | 'pending' | 'completed' | 'failed' | 'processing'

interface StatusBadgeProps {
  status: Status
  label?: string
  size?: 'sm' | 'md'
  showIcon?: boolean
}

export function StatusBadge({
  status,
  label,
  size = 'md',
  showIcon = false
}: StatusBadgeProps) {
  const statusStyles = {
    active: 'bg-semantic-success-bg-strong dark:bg-green-900/30 text-admin-success dark:text-green-300 border-semantic-success-border dark:border-green-800',
    inactive: 'bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-600',
    pending: 'bg-semantic-warning-bg-strong dark:bg-yellow-900/30 text-admin-warning dark:text-yellow-300 border-semantic-warning-border dark:border-yellow-800',
    completed: 'bg-semantic-success-bg-strong dark:bg-green-900/30 text-admin-success dark:text-green-300 border-semantic-success-border dark:border-green-800',
    failed: 'bg-semantic-error-bg-strong dark:bg-red-900/30 text-admin-danger dark:text-red-300 border-semantic-error-border dark:border-red-800',
    processing: 'bg-semantic-info-bg-strong dark:bg-blue-900/30 text-admin-primary dark:text-blue-300 border-semantic-info-border dark:border-blue-800'
  }

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm'
  }

  const defaultLabels: Record<Status, string> = {
    active: 'Active',
    inactive: 'Inactive',
    pending: 'Pending',
    completed: 'Completed',
    failed: 'Failed',
    processing: 'Processing'
  }

  const statusIcons = {
    active: (
      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    inactive: (
      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
      </svg>
    ),
    pending: (
      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
      </svg>
    ),
    completed: (
      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    failed: (
      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
    ),
    processing: (
      <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    )
  }

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border font-medium ${statusStyles[status]} ${sizeStyles[size]}`}>
      {showIcon && statusIcons[status]}
      {label || defaultLabels[status]}
    </span>
  )
}
