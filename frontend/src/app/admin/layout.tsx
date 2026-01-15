// src/app/admin/layout.tsx
// Force dynamic rendering for authenticated admin pages
export const dynamic = 'force-dynamic'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
