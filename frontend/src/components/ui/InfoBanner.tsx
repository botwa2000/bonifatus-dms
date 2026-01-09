// frontend/src/components/ui/InfoBanner.tsx
import { ReactNode } from 'react'

export type InfoBannerVariant = 'success' | 'warning' | 'error' | 'info'

interface InfoBannerProps {
  variant: InfoBannerVariant
  title?: string
  message: string | ReactNode
  icon?: ReactNode
  action?: ReactNode
  dismissible?: boolean
  onDismiss?: () => void
}

export function InfoBanner({
  variant,
  title,
  message,
  icon,
  action,
  dismissible = false,
  onDismiss
}: InfoBannerProps) {
  const styles = {
    success: {
      container: 'bg-semantic-success-bg dark:bg-green-900/20 border-semantic-success-border dark:border-green-800',
      icon: 'text-admin-success dark:text-green-300',
      title: 'text-semantic-success-text dark:text-green-300',
      message: 'text-semantic-success-text dark:text-green-300'
    },
    error: {
      container: 'bg-semantic-error-bg dark:bg-red-900/20 border-semantic-error-border dark:border-red-800',
      icon: 'text-admin-danger dark:text-red-300',
      title: 'text-semantic-error-text dark:text-red-300',
      message: 'text-semantic-error-text dark:text-red-300'
    },
    warning: {
      container: 'bg-semantic-warning-bg dark:bg-yellow-900/20 border-semantic-warning-border dark:border-yellow-800',
      icon: 'text-admin-warning dark:text-yellow-300',
      title: 'text-semantic-warning-text dark:text-yellow-300',
      message: 'text-semantic-warning-text dark:text-yellow-300'
    },
    info: {
      container: 'bg-semantic-info-bg dark:bg-blue-900/20 border-semantic-info-border dark:border-blue-800',
      icon: 'text-admin-primary dark:text-blue-300',
      title: 'text-semantic-info-text dark:text-blue-300',
      message: 'text-semantic-info-text dark:text-blue-300'
    }
  }

  const style = styles[variant]

  return (
    <div className={`rounded-lg border-2 p-4 ${style.container}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start space-x-3 flex-1">
          {icon && (
            <div className={`flex-shrink-0 ${style.icon}`}>
              {icon}
            </div>
          )}
          <div className="flex-1 min-w-0">
            {title && (
              <p className={`text-sm font-medium mb-1 ${style.title}`}>
                {title}
              </p>
            )}
            <div className={`text-sm ${style.message}`}>
              {message}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 flex-shrink-0">
          {action && <div>{action}</div>}
          {dismissible && onDismiss && (
            <button
              onClick={onDismiss}
              className={`${style.icon} hover:opacity-70 transition-opacity`}
              aria-label="Dismiss"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
