// frontend/src/components/ui/Select.tsx
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  hint?: string
  options: Array<{ value: string; label: string }>
}

export function Select({ 
  label, 
  hint, 
  options,
  className = '',
  ...props 
}: SelectProps) {
  return (
    <div>
      {label && (
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          {label}
        </label>
      )}
      <select
        className={`w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-admin-primary focus:outline-none focus:ring-1 focus:ring-admin-primary ${className}`}
        {...props}
      >
        {options.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint && (
        <p className="mt-1 text-xs text-neutral-500">{hint}</p>
      )}
    </div>
  )
}