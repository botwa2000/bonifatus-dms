'use client'

import { useCurrency } from '@/contexts/currency-context'

export default function CurrencySelector() {
  const { selectedCurrency, availableCurrencies, setSelectedCurrency, isLoading } = useCurrency()

  if (isLoading || availableCurrencies.length === 0) {
    return null
  }

  return (
    <div className="relative">
      <select
        value={selectedCurrency?.code || 'EUR'}
        onChange={(e) => {
          const currency = availableCurrencies.find(c => c.code === e.target.value)
          if (currency) {
            setSelectedCurrency(currency)
          }
        }}
        className="appearance-none bg-transparent border border-neutral-300 dark:border-neutral-600 rounded-md px-3 py-1.5 pr-8 text-sm text-neutral-700 dark:text-neutral-300 hover:border-neutral-400 dark:hover:border-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors cursor-pointer"
        aria-label="Select currency"
      >
        {availableCurrencies.map((currency) => (
          <option key={currency.code} value={currency.code}>
            {currency.code}
          </option>
        ))}
      </select>
      <svg
        className="absolute right-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-neutral-500 pointer-events-none"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </div>
  )
}
