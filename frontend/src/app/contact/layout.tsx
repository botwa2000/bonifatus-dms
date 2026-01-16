// frontend/src/app/contact/layout.tsx
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Contact Us - Get Support | Bonifatus DMS',
  description: 'Need help? Contact Bonifatus DMS support team for assistance with document management, integrations, billing, or account questions.',
  openGraph: {
    title: 'Contact Bonifatus DMS',
    description: 'Get support for document management, integrations, billing, and more',
    url: 'https://bonidoc.com/contact',
    siteName: 'Bonifatus DMS',
    type: 'website',
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
