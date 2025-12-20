// frontend/src/components/analytics/PlausibleAnalytics.tsx
'use client'

import Script from 'next/script'
import { PLAUSIBLE_DOMAIN } from '@/lib/analytics'

export default function PlausibleAnalytics() {
  const isProduction = process.env.NODE_ENV === 'production'
  const enableInDev = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS_DEV === 'true'
  const analyticsEnabled = isProduction || enableInDev

  // Only load if analytics enabled
  if (!PLAUSIBLE_DOMAIN || !analyticsEnabled) {
    return null
  }

  return (
    <Script
      defer
      data-domain={PLAUSIBLE_DOMAIN}
      src="https://plausible.io/js/script.js"
      strategy="afterInteractive"
    />
  )
}
