// frontend/src/components/faq/FAQCategoryFilter.tsx
'use client'

interface FAQCategoryFilterProps {
  categories: string[]
  activeCategory: string | null
  onCategoryChange: (category: string | null) => void
  className?: string
}

export function FAQCategoryFilter({
  categories,
  activeCategory,
  onCategoryChange,
  className = ''
}: FAQCategoryFilterProps) {
  return (
    <div className={`flex flex-wrap gap-3 ${className}`}>
      {/* All Categories Button */}
      <button
        onClick={() => onCategoryChange(null)}
        className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
          activeCategory === null
            ? 'bg-admin-primary text-white shadow-md'
            : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700'
        }`}
        aria-pressed={activeCategory === null}
      >
        All
      </button>

      {/* Category Filter Buttons */}
      {categories.map((category) => (
        <button
          key={category}
          onClick={() => onCategoryChange(category)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
            activeCategory === category
              ? 'bg-admin-primary text-white shadow-md'
              : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700'
          }`}
          aria-pressed={activeCategory === category}
        >
          {category}
        </button>
      ))}
    </div>
  )
}

export default FAQCategoryFilter
