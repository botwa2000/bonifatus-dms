// src/app/page.tsx
/**
 * Home page for Bonifatus DMS
 * Landing page with navigation to login
 */

import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-neutral-900">
            Bonifatus DMS
          </h1>
          <p className="mt-2 text-sm text-neutral-600">
            Professional Document Management System
          </p>
        </div>
        
        <div className="space-y-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-neutral-900">
              Admin Access
            </h2>
            <p className="mt-2 text-sm text-neutral-600">
              Access the admin interface to test document management functionality.
            </p>
            <Link
              href="/login"
              className="btn-primary mt-4 w-full"
            >
              Admin Login
            </Link>
          </div>
          
          <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
            <p className="text-xs text-neutral-500">
              Environment: {process.env.NODE_ENV}
              <br />
              API: {process.env.NEXT_PUBLIC_API_URL || 'localhost:8000'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}