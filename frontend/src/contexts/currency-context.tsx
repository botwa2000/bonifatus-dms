'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { apiClient } from '@/services/api-client'

interface Currency {
  code: string
  symbol: string
  name: string
  decimal_places: number
  exchange_rate: number
  is_default: boolean
}

interface CurrencyContextType {
  selectedCurrency: Currency | null
  availableCurrencies: Currency[]
  setSelectedCurrency: (currency: Currency) => void
  convertPrice: (priceInEur: number) => number
  formatPrice: (priceInEur: number) => string
  isLoading: boolean
}

const CurrencyContext = createContext<CurrencyContextType | undefined>(undefined)

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [selectedCurrency, setSelectedCurrencyState] = useState<Currency | null>(null)
  const [availableCurrencies, setAvailableCurrencies] = useState<Currency[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Load available currencies from API
  useEffect(() => {
    const loadCurrencies = async () => {
      try {
        const response = await apiClient.get<{ currencies: Currency[] }>('/api/v1/settings/currencies/available')
        setAvailableCurrencies(response.currencies)

        // Try to load saved currency from localStorage
        const savedCode = localStorage.getItem('selected_currency')
        const savedCurrency = response.currencies.find(c => c.code === savedCode)

        if (savedCurrency) {
          setSelectedCurrencyState(savedCurrency)
        } else {
          // Default to EUR or first available currency
          const defaultCurrency = response.currencies.find(c => c.is_default) || response.currencies[0]
          setSelectedCurrencyState(defaultCurrency)
        }
      } catch (error) {
        console.error('Failed to load currencies:', error)
        // Fallback to EUR
        setSelectedCurrencyState({
          code: 'EUR',
          symbol: '€',
          name: 'Euro',
          decimal_places: 2,
          exchange_rate: 1.0,
          is_default: true
        })
      } finally {
        setIsLoading(false)
      }
    }

    loadCurrencies()
  }, [])

  const setSelectedCurrency = (currency: Currency) => {
    setSelectedCurrencyState(currency)
    localStorage.setItem('selected_currency', currency.code)
  }

  const convertPrice = (priceInEur: number): number => {
    if (!selectedCurrency) return priceInEur
    return priceInEur * selectedCurrency.exchange_rate
  }

  const formatPrice = (priceInEur: number): string => {
    if (!selectedCurrency) return `€${priceInEur.toFixed(2)}`

    const convertedPrice = convertPrice(priceInEur)
    const formattedPrice = convertedPrice.toFixed(selectedCurrency.decimal_places)

    // Format with currency symbol
    if (selectedCurrency.code === 'USD' || selectedCurrency.code === 'GBP') {
      return `${selectedCurrency.symbol}${formattedPrice}`
    } else {
      return `${formattedPrice} ${selectedCurrency.symbol}`
    }
  }

  return (
    <CurrencyContext.Provider
      value={{
        selectedCurrency,
        availableCurrencies,
        setSelectedCurrency,
        convertPrice,
        formatPrice,
        isLoading
      }}
    >
      {children}
    </CurrencyContext.Provider>
  )
}

export function useCurrency() {
  const context = useContext(CurrencyContext)
  if (context === undefined) {
    throw new Error('useCurrency must be used within a CurrencyProvider')
  }
  return context
}
