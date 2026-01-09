// frontend/src/components/ui/Card.tsx
export function Card({
  children,
  className = ''
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={`bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({
  title,
  action
}: {
  title: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between mb-6">
      <h2 className="text-lg font-semibold text-neutral-900 dark:text-white">{title}</h2>
      {action}
    </div>
  )
}

export function CardContent({ 
  children 
}: { 
  children: React.ReactNode 
}) {
  return <div className="space-y-4">{children}</div>
}