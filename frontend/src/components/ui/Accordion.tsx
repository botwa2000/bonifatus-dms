// frontend/src/components/ui/Accordion.tsx
'use client'

import { useState, KeyboardEvent } from 'react'

export interface AccordionItem {
  id: string
  question: string
  answer: string | React.ReactNode
  category?: string
}

interface AccordionProps {
  items: AccordionItem[]
  defaultExpanded?: string[]
  className?: string
}

export function Accordion({ items, defaultExpanded = [], className = '' }: AccordionProps) {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set(defaultExpanded))

  const toggleItem = (id: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>, id: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      toggleItem(id)
    }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {items.map((item) => {
        const isExpanded = expandedItems.has(item.id)

        return (
          <div
            key={item.id}
            className="border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden transition-all"
          >
            <button
              onClick={() => toggleItem(item.id)}
              onKeyDown={(e) => handleKeyDown(e, item.id)}
              className="w-full px-6 py-4 flex items-center justify-between bg-white dark:bg-neutral-900 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors text-left"
              aria-expanded={isExpanded}
              aria-controls={`accordion-content-${item.id}`}
            >
              <span className="text-lg font-semibold text-neutral-900 dark:text-white pr-4">
                {item.question}
              </span>
              <svg
                className={`h-5 w-5 text-neutral-600 dark:text-neutral-400 flex-shrink-0 transition-transform duration-200 ${
                  isExpanded ? 'transform rotate-180' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <div
              id={`accordion-content-${item.id}`}
              className={`transition-all duration-200 ease-in-out ${
                isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
              } overflow-hidden`}
              role="region"
              aria-labelledby={`accordion-button-${item.id}`}
            >
              <div className="px-6 py-4 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-700 dark:text-neutral-300 leading-relaxed">
                {typeof item.answer === 'string' ? (
                  <div dangerouslySetInnerHTML={{ __html: item.answer }} />
                ) : (
                  item.answer
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default Accordion
