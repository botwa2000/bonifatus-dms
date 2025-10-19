// src/app/login/page.tsx
import LoginPageContent from './LoginPageContent'

// Force dynamic rendering since this page uses useSearchParams()
export const dynamic = 'force-dynamic'

export default function LoginPage() {
  return <LoginPageContent />
}