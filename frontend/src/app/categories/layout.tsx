// src/app/categories/layout.tsx
// Force dynamic rendering for authenticated categories page
export const dynamic = 'force-dynamic'

export default function CategoriesLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
