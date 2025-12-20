// frontend/src/components/analytics/PostHogProvider.tsx
'use client'

import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import posthog from 'posthog-js'
import { PostHogProvider as PHProvider } from 'posthog-js/react'
import { POSTHOG_KEY, POSTHOG_HOST } from '@/lib/analytics'

// Initialize PostHog
const isProduction = process.env.NODE_ENV === 'production'
const enableInDev = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS_DEV === 'true'
const analyticsEnabled = isProduction || enableInDev

if (typeof window !== 'undefined' && POSTHOG_KEY && analyticsEnabled) {
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    // Enable session recordings
    session_recording: {
      recordCrossOriginIframes: true,
    },
    // Enable autocapture for clicks, form submissions, etc.
    autocapture: true,
    // Capture pageviews automatically
    capture_pageview: false, // We'll do this manually for better control
    // Respect Do Not Track
    respect_dnt: true,
    // Privacy settings
    mask_all_text: false,
    mask_all_element_attributes: false,
  })
}

function PostHogPageView() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    const isProduction = process.env.NODE_ENV === 'production'
    const enableInDev = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS_DEV === 'true'
    const analyticsEnabled = isProduction || enableInDev

    if (pathname && POSTHOG_KEY && analyticsEnabled) {
      let url = window.origin + pathname
      if (searchParams && searchParams.toString()) {
        url = url + `?${searchParams.toString()}`
      }
      posthog.capture('$pageview', {
        $current_url: url,
      })
    }
  }, [pathname, searchParams])

  return null
}

export default function PostHogProvider({ children }: { children: React.ReactNode }) {
  const isProduction = process.env.NODE_ENV === 'production'
  const enableInDev = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS_DEV === 'true'
  const analyticsEnabled = isProduction || enableInDev

  // Only load if analytics enabled and valid key
  if (!POSTHOG_KEY || !analyticsEnabled) {
    return <>{children}</>
  }

  return (
    <PHProvider client={posthog}>
      <PostHogPageView />
      {children}
    </PHProvider>
  )
}
