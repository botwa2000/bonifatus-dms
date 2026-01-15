// src/app/dashboard/layout.tsx
// Force dynamic rendering for authenticated dashboard
export const dynamic = 'force-dynamic'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
