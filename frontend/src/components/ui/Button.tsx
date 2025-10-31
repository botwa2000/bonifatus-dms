// frontend/src/components/ui/Button.tsx
export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  children: React.ReactNode
}

export function Button({ 
  variant = 'primary', 
  size = 'md', 
  children, 
  className = '',
  disabled,
  ...props 
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  
  const variants = {
    primary: 'bg-admin-primary text-white hover:bg-admin-primary/90 dark:bg-admin-primary dark:hover:bg-admin-primary/80',
    secondary: 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-700',
    danger: 'bg-red-600 text-white hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800',
    ghost: 'text-admin-primary hover:underline dark:text-blue-400'
  }
  
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base'
  }
  
  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
}