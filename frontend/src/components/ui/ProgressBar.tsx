// frontend/src/components/ui/ProgressBar.tsx
export interface ProgressBarProps {
  value: number
  max: number
  label?: string
  showPercentage?: boolean
  variant?: 'primary' | 'success' | 'warning' | 'error'
}

export function ProgressBar({
  value,
  max,
  label,
  showPercentage = false,
  variant = 'primary'
}: ProgressBarProps) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0

  const variantColors = {
    primary: 'bg-admin-primary',
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500'
  }

  const barColor = percentage > 90 ? variantColors.error :
                   percentage > 75 ? variantColors.warning :
                   variantColors[variant]

  return (
    <div className="w-full">
      {(label || showPercentage) && (
        <div className="flex justify-between items-center mb-1">
          {label && <span className="text-sm text-neutral-600">{label}</span>}
          {showPercentage && (
            <span className="text-sm font-medium text-neutral-700">
              {percentage.toFixed(1)}%
            </span>
          )}
        </div>
      )}
      <div className="w-full bg-neutral-200 rounded-full h-2">
        <div
          className={`${barColor} rounded-full h-2 transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
