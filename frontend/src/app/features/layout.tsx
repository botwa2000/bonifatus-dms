// frontend/src/app/features/layout.tsx
import type { Metadata } from 'next'

// Force dynamic rendering due to useSearchParams usage
export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Features - AI Document Management | Bonifatus DMS',
  description: 'Discover powerful features: AI auto-categorization, smart search, cloud storage integration, multilingual support, bulk upload, email processing and more',
  openGraph: {
    title: 'Bonifatus DMS Features',
    description: 'AI auto-categorization, smart search, cloud storage integration, and more',
    url: 'https://bonidoc.com/features',
    siteName: 'Bonifatus DMS',
    type: 'website',
    images: [{
      url: 'https://bonidoc.com/og-features.png',
      width: 1200,
      height: 630,
      alt: 'Bonifatus DMS Features'
    }]
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Bonifatus DMS Features',
    description: 'AI-powered document management features',
  },
  alternates: {
    canonical: 'https://bonidoc.com/features'
  }
}

export default function FeaturesLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
