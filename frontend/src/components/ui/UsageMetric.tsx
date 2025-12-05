// frontend/src/components/ui/UsageMetric.tsx
import { ProgressBar } from './ProgressBar'

export interface UsageMetricProps {
  label: string
  value: number
  limit: number | null
  unit: string
  remaining?: number
}

export function UsageMetric({
  label,
  value,
  limit,
  unit,
  remaining
}: UsageMetricProps) {
  const isUnlimited = limit === null

  return (
    <div className="bg-neutral-50 rounded-lg p-4">
      <p className="text-sm text-neutral-600 mb-2">{label}</p>
      <div className="space-y-2">
        <div className="flex justify-between items-baseline">
          <span className="text-2xl font-bold text-neutral-900">
            {value} {unit}
          </span>
          <span className="text-sm text-neutral-600">
            / {isUnlimited ? 'Unlimited' : `${limit} ${unit}`}
          </span>
        </div>
        {!isUnlimited && limit && (
          <>
            <ProgressBar value={value} max={limit} />
            {remaining !== undefined && (
              <p className="text-xs text-neutral-600">
                {remaining} {unit} remaining
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
