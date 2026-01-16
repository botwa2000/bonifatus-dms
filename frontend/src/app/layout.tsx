// frontend/src/app/layout.tsx

import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/contexts/theme-context'
import { AuthProvider } from '@/contexts/auth-context'
import { DelegateProvider } from '@/contexts/delegate-context'
import { CurrencyProvider } from '@/contexts/currency-context'
import CookieConsent from '@/components/CookieConsent'
import { GoogleAnalytics, PostHogProvider, PlausibleAnalytics } from '@/components/analytics'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-geist-sans',
})

// Force dynamic rendering - required due to useSearchParams in global components
export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  metadataBase: new URL('https://bonidoc.com'),
  title: {
    default: 'Bonidoc - AI Document Management',
    template: '%s | Bonidoc'
  },
  description: 'Professional Document Management System with AI-powered automation',
  keywords: ['document management', 'DMS', 'AI automation', 'cloud storage', 'GDPR compliant'],
  authors: [{ name: 'Bonidoc' }],
  creator: 'Bonidoc',
  publisher: 'Bonidoc',
  icons: {
    icon: [
      { url: '/favicon.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-96x96.png', sizes: '96x96', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
    other: [
      { rel: 'icon', url: '/favicon-192x192.png', sizes: '192x192', type: 'image/png' },
    ],
  },
  manifest: '/site.webmanifest',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'Bonidoc',
  },
  twitter: {
    card: 'summary_large_image',
    site: '@bonidoc',
    creator: '@bonidoc',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        {/* Theme color for browser chrome */}
        <meta name="theme-color" content="#1e40af" />

        {/* Preconnect to external domains for faster loading */}
        <link rel="preconnect" href="https://api.bonidoc.com" />
        <link rel="preconnect" href="https://accounts.google.com" />
        <link rel="dns-prefetch" href="https://www.googletagmanager.com" />

        {/* Structured Data - Organization/SoftwareApplication */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              "name": "Bonidoc",
              "description": "AI-powered document management system for automated organization and categorization",
              "applicationCategory": "BusinessApplication",
              "operatingSystem": "Web",
              "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "EUR",
                "availability": "https://schema.org/InStock"
              },
              "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": "4.9",
                "ratingCount": "150"
              },
              "featureList": [
                "AI Auto-Categorization",
                "Smart Document Search",
                "Cloud Storage Integration",
                "Multilingual Support",
                "Bulk Processing",
                "Email-to-Process"
              ]
            })
          }}
        />

        {/* Theme detection script */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('theme');
                  if (theme === 'dark' || theme === 'light') {
                    document.documentElement.classList.add(theme);
                  } else {
                    document.documentElement.classList.add('light');
                  }
                } catch (e) {
                  document.documentElement.classList.add('light');
                }
              })();
            `,
          }}
        />

        <script src="https://accounts.google.com/gsi/client" async defer></script>
        <GoogleAnalytics />
        <PlausibleAnalytics />
      </head>
      <body className={inter.className}>
        <PostHogProvider>
          <ThemeProvider>
            <AuthProvider>
              <DelegateProvider>
                <CurrencyProvider>
                  {children}
                  <CookieConsent language="en" />
                </CurrencyProvider>
              </DelegateProvider>
            </AuthProvider>
          </ThemeProvider>
        </PostHogProvider>
      </body>
    </html>
  )
}