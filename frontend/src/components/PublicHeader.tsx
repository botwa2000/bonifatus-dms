'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'

export default function PublicHeader() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <nav className="bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 md:h-20">
          <Link href="/" className="flex items-center">
            <div className="relative h-12 w-48 md:h-14 md:w-56">
              <Image
                src="/logo-header.png"
                alt="Bonidoc - AI Document Management"
                fill
                className="object-contain object-left"
                priority
              />
            </div>
          </Link>

          <div className="hidden md:flex items-center space-x-8">
            <a href="/#features" className="text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400">Features</a>
            <a href="/#how-it-works" className="text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400">How It Works</a>
            <a href="/#pricing" className="text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400">Pricing</a>
            <Link href="/faq" className="text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400">FAQ</Link>
            <Link href="/about" className="text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400">About</Link>
            <Link href="/contact" className="text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400">Contact</Link>
            <Link href="/login" className="inline-flex items-center justify-center font-medium rounded-md transition-colors px-3 py-1.5 text-sm bg-admin-primary text-white hover:bg-admin-primary/90 dark:bg-admin-primary dark:hover:bg-admin-primary/80">
              Sign In
            </Link>
          </div>

          <div className="md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              onTouchEnd={(e) => {
                e.preventDefault()
                setMobileMenuOpen(!mobileMenuOpen)
              }}
              className="text-neutral-600 dark:text-white hover:text-neutral-900 dark:hover:text-neutral-300 p-3 focus:outline-none focus:ring-2 focus:ring-admin-primary rounded-md touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center relative z-50"
              aria-label="Toggle mobile menu"
              aria-expanded={mobileMenuOpen}
              type="button"
            >
              {mobileMenuOpen ? (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden border-t border-neutral-200 dark:border-neutral-800">
            <div className="px-2 pt-2 pb-3 space-y-1">
              <a
                href="/#features"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-md text-base font-medium text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                Features
              </a>
              <a
                href="/#how-it-works"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-md text-base font-medium text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                How It Works
              </a>
              <a
                href="/#pricing"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-md text-base font-medium text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                Pricing
              </a>
              <Link
                href="/faq"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-md text-base font-medium text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                FAQ
              </Link>
              <Link
                href="/about"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-md text-base font-medium text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                About
              </Link>
              <Link
                href="/contact"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-md text-base font-medium text-neutral-600 dark:text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                Contact
              </Link>
              <Link
                href="/login"
                className="block mx-3 my-2 px-4 py-2 rounded-md text-sm font-medium text-center bg-admin-primary text-white hover:bg-admin-primary/90 dark:bg-admin-primary dark:hover:bg-admin-primary/80 transition-colors"
              >
                Sign In
              </Link>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
