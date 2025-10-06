// frontend/src/components/ui/Alert.tsx
export type AlertType = 'success' | 'error' | 'warning' | 'info'

export function Alert({ 
  type, 
  message 
}: { 
  type: AlertType
  message: string
}) {
  const styles = {
    success: 'bg-green-50 border-green-200 text-green-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800'
  }
  
  return (
    <div className={`rounded-lg border p-4 ${styles[type]}`}>
      <p className="text-sm">{message}</p>
    </div>
  )
}