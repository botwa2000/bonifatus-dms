// src/app/documents/layout.tsx
// Force dynamic rendering for authenticated documents page
export const dynamic = 'force-dynamic'

export default function DocumentsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
