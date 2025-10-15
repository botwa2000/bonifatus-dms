// frontend/src/app/pricing/page.tsx
import Link from 'next/link'

export default function PricingPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">Pricing Coming Soon</h1>
        <p className="text-gray-600">This page is under construction.</p>
        <Link href="/" className="text-blue-600 hover:underline mt-4 inline-block">
          Return Home
        </Link>
      </div>
    </div>
  )
}