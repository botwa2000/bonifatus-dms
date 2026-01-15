// src/app/delegates/layout.tsx
// Force dynamic rendering for authenticated delegates page
export const dynamic = 'force-dynamic'

export default function DelegatesLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
