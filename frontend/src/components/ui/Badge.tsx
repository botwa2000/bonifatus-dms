// frontend/src/components/ui/Badge.tsx
export type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
}

export function Badge({ children, variant = 'default' }: BadgeProps) {
  const variants = {
    default: 'bg-neutral-100 text-neutral-700',
    success: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    error: 'bg-red-100 text-red-700',
    info: 'bg-blue-100 text-blue-700'
  }
  
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${variants[variant]}`}>
      {children}
    </span>
  )
}