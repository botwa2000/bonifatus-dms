// frontend/src/components/analytics/GoogleAnalytics.tsx
'use client'

import Script from 'next/script'
import { useEffect, useState } from 'react'
import { GA_MEASUREMENT_ID } from '@/lib/analytics'
import * as CookieConsent from 'vanilla-cookieconsent'

export default function GoogleAnalytics() {
  const [consentGiven, setConsentGiven] = useState(false)
  const isProduction = process.env.NODE_ENV === 'production'
  const enableInDev = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS_DEV === 'true'
  const analyticsEnabled = isProduction || enableInDev

  useEffect(() => {
    // Check if user has already consented to analytics
    const checkConsent = () => {
      if (typeof window !== 'undefined') {
        try {
          const hasConsent = CookieConsent.acceptedCategory('analytics')
          setConsentGiven(hasConsent)
        } catch (error) {
          // CookieConsent not initialized yet
          setConsentGiven(false)
        }
      }
    }

    // Check immediately
    checkConsent()

    // Listen for consent changes
    window.addEventListener('cc:onConsent', checkConsent)
    window.addEventListener('cc:onChange', checkConsent)

    return () => {
      window.removeEventListener('cc:onConsent', checkConsent)
      window.removeEventListener('cc:onChange', checkConsent)
    }
  }, [])

  // Only load if analytics enabled, valid measurement ID, AND user consented
  if (!GA_MEASUREMENT_ID || !analyticsEnabled || !consentGiven) {
    return null
  }

  return (
    <>
      <Script
        strategy="afterInteractive"
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
      />
      <Script
        id="google-analytics"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{
          __html: `
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());

            gtag('config', '${GA_MEASUREMENT_ID}', {
              page_path: window.location.pathname,
              cookie_flags: 'SameSite=None;Secure',
              anonymize_ip: true,
              allow_google_signals: false,
              allow_ad_personalization_signals: false,
            });
          `,
        }}
      />
    </>
  )
}
