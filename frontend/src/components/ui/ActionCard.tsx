// frontend/src/components/ui/ActionCard.tsx
import { ReactNode } from 'react'
import Link from 'next/link'

interface ActionCardProps {
  icon: ReactNode
  iconBgColor?: string
  title: string
  description: string
  href?: string
  onClick?: () => void
}

export function ActionCard({
  icon,
  iconBgColor = 'bg-admin-primary',
  title,
  description,
  href,
  onClick
}: ActionCardProps) {
  const content = (
    <div className="flex items-start space-x-4">
      <div className={`flex-shrink-0 w-12 h-12 rounded-lg ${iconBgColor} flex items-center justify-center text-white`}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-1">
          {title}
        </h3>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          {description}
        </p>
      </div>
      <svg
        className="flex-shrink-0 h-5 w-5 text-neutral-400 dark:text-neutral-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </div>
  )

  const cardClasses = "bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 transition-all hover:border-admin-primary hover:shadow-md"

  if (href) {
    return (
      <Link href={href}>
        <div className={`${cardClasses} cursor-pointer`}>
          {content}
        </div>
      </Link>
    )
  }

  if (onClick) {
    return (
      <button onClick={onClick} className={`${cardClasses} w-full text-left cursor-pointer`}>
        {content}
      </button>
    )
  }

  return (
    <div className={cardClasses}>
      {content}
    </div>
  )
}
