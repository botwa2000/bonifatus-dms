// frontend/src/app/faq/layout.tsx
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'FAQ - Frequently Asked Questions | Bonifatus DMS',
  description: 'Find answers to common questions about Bonifatus DMS document management, AI categorization, cloud storage, pricing, security, and more.',
  keywords: ['document management FAQ', 'DMS help', 'cloud storage questions', 'AI document categorization', 'bonifatus support'],
  openGraph: {
    title: 'Bonifatus DMS - Frequently Asked Questions',
    description: 'Get answers to your questions about our AI-powered document management system',
    url: 'https://bonidoc.com/faq',
    siteName: 'Bonifatus DMS',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FAQ - Bonifatus DMS',
    description: 'Find answers to common questions about document management',
  },
  alternates: {
    canonical: 'https://bonidoc.com/faq'
  }
}

export default function FAQLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
