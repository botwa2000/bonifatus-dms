// frontend/src/components/analytics/PostHogProvider.tsx
'use client'

import { useEffect, useState } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import posthog from 'posthog-js'
import { PostHogProvider as PHProvider } from 'posthog-js/react'
import { POSTHOG_KEY, POSTHOG_HOST } from '@/lib/analytics'

declare global {
  interface Window {
    CookieConsentApi?: {
      acceptedCategory: (category: string) => boolean
    }
  }
}

const isProduction = process.env.NODE_ENV === 'production'
const enableInDev = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS_DEV === 'true'
const analyticsEnabled = isProduction || enableInDev

// Initialize PostHog only after consent is given
let posthogInitialized = false

function initializePostHog() {
  if (posthogInitialized || !POSTHOG_KEY || !analyticsEnabled) {
    return
  }

  if (typeof window !== 'undefined') {
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      session_recording: {
        recordCrossOriginIframes: true,
      },
      autocapture: true,
      capture_pageview: false,
      respect_dnt: true,
      mask_all_text: false,
      mask_all_element_attributes: false,
    })
    posthogInitialized = true
  }
}

function PostHogPageView() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [consentGiven, setConsentGiven] = useState(false)

  useEffect(() => {
    // Check consent
    const checkConsent = () => {
      if (typeof window !== 'undefined' && window.CookieConsentApi) {
        const hasConsent = window.CookieConsentApi.acceptedCategory('analytics')
        setConsentGiven(hasConsent)
        if (hasConsent) {
          initializePostHog()
        }
      }
    }

    checkConsent()
    window.addEventListener('cc:onConsent', checkConsent)
    window.addEventListener('cc:onChange', checkConsent)

    return () => {
      window.removeEventListener('cc:onConsent', checkConsent)
      window.removeEventListener('cc:onChange', checkConsent)
    }
  }, [])

  useEffect(() => {
    if (pathname && consentGiven && posthogInitialized) {
      let url = window.origin + pathname
      if (searchParams && searchParams.toString()) {
        url = url + `?${searchParams.toString()}`
      }
      posthog.capture('$pageview', {
        $current_url: url,
      })
    }
  }, [pathname, searchParams, consentGiven])

  return null
}

export default function PostHogProvider({ children }: { children: React.ReactNode }) {
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
