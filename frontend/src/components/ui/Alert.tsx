// frontend/src/components/ui/Alert.tsx
import { ReactNode } from 'react'

export type AlertType = 'success' | 'error' | 'warning' | 'info'

export function Alert({
  type,
  message
}: {
  type: AlertType
  message: string | ReactNode
}) {
  const styles = {
    success: 'bg-semantic-success-bg dark:bg-green-900/20 border-semantic-success-border dark:border-green-800 text-semantic-success-text dark:text-green-300',
    error: 'bg-semantic-error-bg dark:bg-red-900/20 border-semantic-error-border dark:border-red-800 text-semantic-error-text dark:text-red-300',
    warning: 'bg-semantic-warning-bg dark:bg-yellow-900/20 border-semantic-warning-border dark:border-yellow-800 text-semantic-warning-text dark:text-yellow-300',
    info: 'bg-semantic-info-bg dark:bg-blue-900/20 border-semantic-info-border dark:border-blue-800 text-semantic-info-text dark:text-blue-300'
  }

  return (
    <div className={`rounded-lg border p-4 ${styles[type]}`}>
      <div className="text-sm">{message}</div>
    </div>
  )
}