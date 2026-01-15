// frontend/src/app/security/layout.tsx
import type { Metadata } from 'next'

// Force dynamic rendering due to useSearchParams usage
export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Security & Privacy - GDPR Compliant | Bonifatus DMS',
  description: 'Your documents stay in your cloud. GDPR compliant, end-to-end encryption, no data storage on our servers. Enterprise-grade security for your peace of mind.',
  openGraph: {
    title: 'Bonifatus DMS Security & Privacy',
    description: 'GDPR compliant, your data stays in your cloud, enterprise-grade security',
    url: 'https://bonidoc.com/security',
    siteName: 'Bonifatus DMS',
    type: 'website',
    images: [{
      url: 'https://bonidoc.com/og-security.png',
      width: 1200,
      height: 630,
      alt: 'Bonifatus DMS Security'
    }]
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Bonifatus DMS Security',
    description: 'GDPR compliant document management with enterprise-grade security',
  },
  alternates: {
    canonical: 'https://bonidoc.com/security'
  }
}

export default function SecurityLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
