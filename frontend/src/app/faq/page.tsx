// frontend/src/app/faq/page.tsx
'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { Accordion } from '@/components/ui/Accordion'
import { FAQSearch } from '@/components/faq/FAQSearch'
import { FAQCategoryFilter } from '@/components/faq/FAQCategoryFilter'
import { faqs, getCategories } from '@/data/faq-data'
import PublicHeader from '@/components/PublicHeader'

export default function FAQPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const categories = getCategories()

  // Filter FAQs based on search and category
  const filteredFAQs = useMemo(() => {
    let filtered = faqs

    // Filter by category
    if (activeCategory) {
      filtered = filtered.filter(faq => faq.category === activeCategory)
    }

    // Filter by search query
    if (searchQuery) {
      const lowerQuery = searchQuery.toLowerCase()
      filtered = filtered.filter(
        faq =>
          faq.question.toLowerCase().includes(lowerQuery) ||
          faq.answer.toLowerCase().includes(lowerQuery)
      )
    }

    return filtered
  }, [searchQuery, activeCategory])

  // Group FAQs by category for display
  const groupedFAQs = useMemo(() => {
    const groups: Record<string, typeof faqs> = {}
    filteredFAQs.forEach(faq => {
      if (!groups[faq.category]) {
        groups[faq.category] = []
      }
      groups[faq.category].push(faq)
    })
    return groups
  }, [filteredFAQs])

  return (
    <div className="min-h-screen bg-white dark:bg-neutral-900">
      {/* Schema.org FAQPage Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faqs.map(faq => ({
              "@type": "Question",
              "name": faq.question,
              "acceptedAnswer": {
                "@type": "Answer",
                "text": faq.answer.replace(/<[^>]*>/g, '')
              }
            }))
          })
        }}
      />

      <PublicHeader />

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-neutral-50 to-white dark:from-neutral-800 dark:to-neutral-900 py-12 border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl font-bold text-neutral-900 dark:text-white mb-4">
            Frequently Asked Questions
          </h1>
          <p className="text-lg text-neutral-600 dark:text-neutral-400">
            Find answers to common questions about Bonifatus DMS features, pricing, security, and more
          </p>
        </div>
      </section>

      {/* Main Content */}
      <section className="py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Search Bar */}
          <FAQSearch
            onSearch={setSearchQuery}
            resultCount={filteredFAQs.length}
            className="mb-8"
          />

          {/* Category Filter */}
          <FAQCategoryFilter
            categories={categories}
            activeCategory={activeCategory}
            onCategoryChange={setActiveCategory}
            className="mb-12"
          />

          {/* FAQ Accordion by Category */}
          {Object.keys(groupedFAQs).length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <p className="text-lg text-neutral-600 dark:text-neutral-400 mb-2">No FAQs found</p>
              <p className="text-sm text-neutral-500 dark:text-neutral-500">
                Try adjusting your search or filter to find what you&apos;re looking for
              </p>
            </div>
          ) : (
            <div className="space-y-12">
              {Object.entries(groupedFAQs).map(([category, categoryFAQs]) => (
                <div key={category}>
                  <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-6">
                    {category}
                  </h2>
                  <Accordion
                    items={categoryFAQs.map(faq => ({
                      id: faq.id,
                      question: faq.question,
                      answer: faq.answer,
                      category: faq.category
                    }))}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Contact CTA Section */}
      <section className="bg-neutral-50 dark:bg-neutral-800 py-12 border-t border-neutral-200 dark:border-neutral-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-4">
            Can&apos;t find what you&apos;re looking for?
          </h2>
          <p className="text-lg text-neutral-600 dark:text-neutral-400 mb-6">
            Our support team is here to help. Get in touch and we&apos;ll answer your questions.
          </p>
          <Link
            href="/contact"
            className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-admin-primary hover:bg-admin-primary/90 transition-colors"
          >
            Contact Support
            <svg className="ml-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-neutral-900 text-neutral-300 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center mb-4">
                <div className="h-8 w-8 bg-admin-primary rounded-lg flex items-center justify-center">
                  <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <span className="ml-3 text-xl font-bold text-white">Bonifatus DMS</span>
              </div>
              <p className="text-neutral-400">
                AI-powered document management for modern professionals.
              </p>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-4">Product</h3>
              <ul className="space-y-2">
                <li><Link href="/#features" className="hover:text-white transition-colors">Features</Link></li>
                <li><Link href="/#pricing" className="hover:text-white transition-colors">Pricing</Link></li>
                <li><Link href="/faq" className="hover:text-white transition-colors">FAQ</Link></li>
                <li><Link href="/security" className="hover:text-white transition-colors">Security</Link></li>
              </ul>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-4">Company</h3>
              <ul className="space-y-2">
                <li><Link href="/about" className="hover:text-white transition-colors">About</Link></li>
                <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
              </ul>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-4">Legal</h3>
              <ul className="space-y-2">
                <li><Link href="/legal/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
                <li><Link href="/legal/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
                <li><Link href="/legal/impressum" className="hover:text-white transition-colors">Impressum</Link></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-neutral-800 mt-12 pt-8 text-center">
            <p className="text-neutral-400">
              © 2024 Bonifatus DMS. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
