// src/app/settings/layout.tsx
// Force dynamic rendering for authenticated settings page
export const dynamic = 'force-dynamic'

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
