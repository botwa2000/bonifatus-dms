// frontend/src/components/ui/FeatureCard.tsx
import { ReactNode } from 'react'
import Link from 'next/link'

export type FeatureIconColor = 'automation' | 'search' | 'cloud' | 'upload' | 'email' | 'language'

interface FeatureCardProps {
  icon: ReactNode
  iconColor?: FeatureIconColor
  title: string
  description: string
  href?: string
}

export function FeatureCard({
  icon,
  iconColor = 'automation',
  title,
  description,
  href
}: FeatureCardProps) {
  const iconColorStyles = {
    automation: 'bg-blue-100 dark:bg-blue-900/30 text-feature-automation',
    search: 'bg-green-100 dark:bg-green-900/30 text-feature-search',
    cloud: 'bg-purple-100 dark:bg-purple-900/30 text-feature-cloud',
    upload: 'bg-orange-100 dark:bg-orange-900/30 text-feature-upload',
    email: 'bg-red-100 dark:bg-red-900/30 text-feature-email',
    language: 'bg-teal-100 dark:bg-teal-900/30 text-feature-language'
  }

  const content = (
    <div className="flex flex-col h-full">
      <div className={`w-12 h-12 rounded-lg flex items-center justify-center mb-4 ${iconColorStyles[iconColor]}`}>
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
        {title}
      </h3>
      <p className="text-neutral-600 dark:text-neutral-400 text-sm">
        {description}
      </p>
    </div>
  )

  if (href) {
    return (
      <Link href={href}>
        <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 h-full transition-all hover:border-admin-primary hover:shadow-md cursor-pointer">
          {content}
        </div>
      </Link>
    )
  }

  return (
    <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 h-full">
      {content}
    </div>
  )
}
