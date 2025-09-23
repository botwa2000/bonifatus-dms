// src/app/dashboard/page.tsx
import Image from 'next/image'

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="relative h-8 w-8">
                <Image
                  src="/favicon.ico"
                  alt="Bonifatus DMS"
                  fill
                  className="object-contain"
                />
              </div>
              <h1 className="text-2xl font-bold text-neutral-900">
                Admin Dashboard
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm text-neutral-600">
                Coming Soon
              </span>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="text-lg font-medium text-neutral-900 mb-4">
            Document Management System
          </h2>
          <p className="text-neutral-600">
            The admin dashboard will be implemented in Phase 3.3-3.5 with document management, 
            user administration, and system configuration features.
          </p>
        </div>
      </main>
    </div>
  )
}