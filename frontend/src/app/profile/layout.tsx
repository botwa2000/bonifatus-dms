// src/app/profile/layout.tsx
// Force dynamic rendering for authenticated profile page
export const dynamic = 'force-dynamic'

export default function ProfileLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
