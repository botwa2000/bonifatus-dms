// frontend/src/components/faq/FAQSearch.tsx
'use client'

import { useState, useEffect, useRef } from 'react'

interface FAQSearchProps {
  onSearch: (query: string) => void
  resultCount?: number
  className?: string
}

export function FAQSearch({ onSearch, resultCount, className = '' }: FAQSearchProps) {
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Keyboard shortcut: Cmd+K / Ctrl+K to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Debounced search
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      onSearch(query)
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [query, onSearch])

  const handleClear = () => {
    setQuery('')
    inputRef.current?.focus()
  }

  return (
    <div className={`relative ${className}`}>
      <div className="relative">
        {/* Search Icon */}
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-500">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        {/* Search Input */}
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search FAQs... (Ctrl+K)"
          className="w-full pl-12 pr-24 py-3 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-500 dark:placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-admin-primary focus:border-transparent transition-all"
          aria-label="Search FAQs"
        />

        {/* Clear Button */}
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
            aria-label="Clear search"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}

        {/* Keyboard Hint */}
        {!query && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2 hidden md:flex items-center gap-1 text-xs text-neutral-400 dark:text-neutral-500 pointer-events-none">
            <kbd className="px-2 py-1 bg-neutral-100 dark:bg-neutral-700 rounded border border-neutral-300 dark:border-neutral-600 font-mono">
              ⌘K
            </kbd>
          </div>
        )}
      </div>

      {/* Result Count */}
      {query && resultCount !== undefined && (
        <div className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
          {resultCount === 0 ? (
            <span>No results found for &quot;{query}&quot;</span>
          ) : resultCount === 1 ? (
            <span>Found 1 result</span>
          ) : (
            <span>Found {resultCount} results</span>
          )}
        </div>
      )}
    </div>
  )
}

export default FAQSearch
