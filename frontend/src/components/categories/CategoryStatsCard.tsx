// frontend/src/components/categories/CategoryStatsCard.tsx
export function CategoryStatsCard({
  label,
  value,
  icon,
  color
}: {
  label: string
  value: number | string
  icon: React.ReactNode
  color: string
}) {
  return (
    <div className="bg-white rounded-lg border border-neutral-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-neutral-600">{label}</p>
          <p className="text-3xl font-bold text-neutral-900 mt-1">{value}</p>
        </div>
        <div className={`h-12 w-12 ${color} rounded-lg flex items-center justify-center`}>
          {icon}
        </div>
      </div>
    </div>
  )
}