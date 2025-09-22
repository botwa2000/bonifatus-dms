// src/app/login/page.tsx
/**
 * Login page placeholder
 * Will implement Google OAuth in next step
 */

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-neutral-900">
            Admin Login
          </h1>
          <p className="mt-2 text-sm text-neutral-600">
            Google OAuth integration coming in Step 2
          </p>
        </div>
        
        <div className="rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="space-y-4">
            <div className="h-10 w-full rounded-md bg-neutral-100"></div>
            <p className="text-xs text-neutral-500">
              Google OAuth login will be implemented in the next step
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}