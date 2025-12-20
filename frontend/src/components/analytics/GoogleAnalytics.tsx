// frontend/src/components/analytics/GoogleAnalytics.tsx
'use client'

import Script from 'next/script'
import { GA_MEASUREMENT_ID } from '@/lib/analytics'

export default function GoogleAnalytics() {
  const isProduction = process.env.NODE_ENV === 'production'
  const enableInDev = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS_DEV === 'true'
  const analyticsEnabled = isProduction || enableInDev

  // Only load if analytics enabled and valid measurement ID
  if (!GA_MEASUREMENT_ID || !analyticsEnabled) {
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
              allow_google_signals: true,
              allow_ad_personalization_signals: false,
            });
          `,
        }}
      />
    </>
  )
}
