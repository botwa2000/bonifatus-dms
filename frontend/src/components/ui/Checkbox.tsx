// frontend/src/components/ui/Checkbox.tsx
interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: string
  error?: string
}

export function Checkbox({
  label,
  hint,
  error,
  className = '',
  ...props
}: CheckboxProps) {
  const checkboxElement = (
    <input
      type="checkbox"
      className={`w-4 h-4 rounded border-neutral-300 text-admin-primary focus:ring-admin-primary focus:ring-1 cursor-pointer ${error ? 'border-red-500' : ''} ${className}`}
      {...props}
    />
  )

  // If no label, just return the checkbox for inline use
  if (!label) {
    return checkboxElement
  }

  // With label, return full layout
  return (
    <div className="flex items-start">
      <div className="flex items-center h-5">
        {checkboxElement}
      </div>
      <div className="ml-3">
        <label className="text-sm font-medium text-neutral-700 dark:text-neutral-300 cursor-pointer">
          {label}
        </label>
        {hint && !error && (
          <p className="text-xs text-neutral-500 dark:text-neutral-400">{hint}</p>
        )}
        {error && (
          <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>
    </div>
  )
}
