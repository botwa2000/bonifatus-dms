// frontend/src/components/ui/Badge.tsx
export type BadgeVariant = 'default' | 'success' | 'warning' | 'danger'

export function Badge({ 
  children, 
  variant = 'default' 
}: { 
  children: React.ReactNode
  variant?: BadgeVariant
}) {
  const variants = {
    default: 'bg-neutral-100 text-neutral-800 border-neutral-300',
    success: 'bg-green-100 text-green-800 border-green-300',
    warning: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    danger: 'bg-red-100 text-red-800 border-red-300'
  }
  
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium border ${variants[variant]}`}>
      {children}
    </span>
  )
}