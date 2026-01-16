// src/app/page.tsx
/**
 * Bonifatus DMS Landing Page - Server Component
 * Exports SEO metadata and renders client component
 */

import type { Metadata } from 'next'
import HomePageClient from '@/components/HomePageClient'

export const metadata: Metadata = {
  title: 'Bonifatus DMS - AI-Powered Document Management System',
  description: 'Automate document organization with AI. Classify, search, and manage PDFs automatically. Google Drive integration, GDPR compliant, 50 free pages/month.',
  keywords: ['document management', 'AI document organization', 'PDF management', 'cloud storage', 'GDPR compliant DMS', 'automated document filing', 'document categorization', 'smart document search'],
  openGraph: {
    title: 'Bonifatus DMS - Never Manually File Documents Again',
    description: 'AI-powered document management that auto-categorizes, extracts, and organizes your PDFs in seconds',
    url: 'https://bonidoc.com',
    siteName: 'Bonifatus DMS',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    site: '@bonifatus',
    creator: '@bonifatus',
    title: 'Bonifatus DMS - AI-Powered Document Management',
    description: 'Never manually file documents again. AI auto-categorizes and organizes your PDFs in seconds.',
  },
  alternates: {
    canonical: 'https://bonidoc.com'
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
}

export default function HomePage() {
  return (
    <>
      {/* Structured Data - Product Schema */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Bonifatus DMS",
            "description": "AI-powered document management system that automatically categorizes and organizes your documents",
            "brand": {
              "@type": "Brand",
              "name": "Bonifatus"
            },
            "offers": {
              "@type": "AggregateOffer",
              "lowPrice": "0",
              "highPrice": "79.99",
              "priceCurrency": "USD",
              "availability": "https://schema.org/InStock"
            },
            "aggregateRating": {
              "@type": "AggregateRating",
              "ratingValue": "4.9",
              "reviewCount": "150"
            }
          })
        }}
      />

      <HomePageClient />
    </>
  )
}
