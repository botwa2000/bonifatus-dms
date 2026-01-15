// frontend/src/app/contact/layout.tsx
import type { Metadata } from 'next'

// Force dynamic rendering due to useSearchParams usage
export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Contact Us - Get Support | Bonifatus DMS',
  description: 'Need help? Contact Bonifatus DMS support team for assistance with document management, integrations, billing, or account questions.',
  openGraph: {
    title: 'Contact Bonifatus DMS',
    description: 'Get support for document management, integrations, billing, and more',
    url: 'https://bonidoc.com/contact',
    siteName: 'Bonifatus DMS',
    type: 'website',
    images: [{
      url: 'https://bonidoc.com/og-contact.png',
      width: 1200,
      height: 630,
      alt: 'Contact Bonifatus DMS'
    }]
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Contact Bonifatus DMS',
    description: 'Get support and assistance',
  },
  alternates: {
    canonical: 'https://bonidoc.com/contact'
  }
}

export default function ContactLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
