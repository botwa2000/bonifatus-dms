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
    default: 'Bonifatus DMS - AI Document Management',
    template: '%s | Bonifatus DMS'
  },
  description: 'Professional Document Management System with AI-powered automation',
  keywords: ['document management', 'DMS', 'AI automation', 'cloud storage', 'GDPR compliant'],
  authors: [{ name: 'Bonifatus' }],
  creator: 'Bonifatus',
  publisher: 'Bonifatus',
  icons: {
    icon: '/favicon.ico',
    apple: '/logo.png',
  },
  manifest: '/manifest.json',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'Bonifatus DMS',
  },
  twitter: {
    card: 'summary_large_image',
    site: '@bonifatus',
    creator: '@bonifatus',
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
              "name": "Bonifatus DMS",
              "description": "AI-powered document management system for automated organization and categorization",
              "applicationCategory": "BusinessApplication",
              "operatingSystem": "Web",
              "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD",
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