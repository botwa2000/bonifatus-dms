// src/app/about/page.tsx
/**
 * About page
 */

import type { Metadata } from 'next'
import Link from 'next/link'
import PublicHeader from '@/components/PublicHeader'

export const metadata: Metadata = {
  title: 'About Us - Bonifatus DMS | AI Document Management Mission',
  description: 'Learn about Bonifatus DMS mission to revolutionize document management with AI-powered automation. Built for privacy, security, and efficiency.',
  openGraph: {
    title: 'About Bonifatus DMS',
    description: 'Our mission to revolutionize document management with AI-powered automation',
    url: 'https://bonidoc.com/about',
    siteName: 'Bonifatus DMS',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'About Bonifatus DMS',
    description: 'Our mission to revolutionize document management with AI',
  },
  alternates: {
    canonical: 'https://bonidoc.com/about'
  }
}

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-900">
      <PublicHeader />

      <div className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-4xl font-bold text-neutral-900 dark:text-white mb-8">About Bonifatus DMS</h1>

        <div className="prose prose-lg max-w-none">
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">Our Mission</h2>
            <p className="text-neutral-700 dark:text-neutral-300 mb-6">
              At Bonifatus DMS, we believe that document management should be intuitive, secure, and powerful.
              Our mission is to help individuals and organizations take control of their digital documents with
              cutting-edge AI technology and enterprise-grade security.
            </p>
          </section>

          <section className="mb-12">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">What Makes Us Different</h2>
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-3">AI-Powered Intelligence</h3>
                <p className="text-neutral-700 dark:text-neutral-300">
                  Our advanced AI automatically categorizes, tags, and organizes your documents,
                  saving you hours of manual work.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-3">Enterprise Security</h3>
                <p className="text-neutral-700 dark:text-neutral-300">
                  Bank-level encryption and security protocols ensure your sensitive documents
                  are always protected.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-3">User-Friendly Design</h3>
                <p className="text-neutral-700 dark:text-neutral-300">
                  Intuitive interface designed for both tech-savvy professionals and everyday users.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-3">Scalable Solution</h3>
                <p className="text-neutral-700 dark:text-neutral-300">
                  From personal use to enterprise deployment, our platform scales with your needs.
                </p>
              </div>
            </div>
          </section>

          <section className="mb-12">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">Our Story</h2>
            <p className="text-neutral-700 dark:text-neutral-300 mb-6">
              Founded in 2024, Bonifatus DMS was born out of frustration with existing document management solutions
              that were either too complex, too expensive, or lacking in modern features. Our team of experienced
              developers and document management experts came together to create a solution that combines the power
              of AI with the simplicity that users deserve.
            </p>
          </section>

          <section className="mb-12 bg-neutral-50 dark:bg-neutral-800 p-8 rounded-lg">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">Ready to Get Started?</h2>
            <p className="text-neutral-700 dark:text-neutral-300 mb-6">
              Create your free account and let AI organize your documents.
              No credit card required.
            </p>
            <Link
              href="/signup?tier_id=0&tier_name=Free&billing_cycle=monthly"
              className="inline-flex items-center justify-center px-6 py-3 text-base font-medium rounded-md bg-admin-primary text-white hover:bg-admin-primary/90 transition-colors"
            >
              Start Free
            </Link>
          </section>
        </div>
      </div>
    </div>
  )
}
