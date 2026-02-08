// frontend/src/components/FacebookLoginButton.tsx

'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/auth-context'
import { logger } from '@/lib/logger'

interface FacebookLoginButtonProps {
  variant?: 'primary' | 'secondary'
  size?: 'sm' | 'md' | 'lg'
  className?: string
  children?: React.ReactNode
  tierId?: number
  billingCycle?: 'monthly' | 'yearly'
}

export function FacebookLoginButton({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  tierId,
  billingCycle
}: FacebookLoginButtonProps) {
  const { initializeFacebookAuth } = useAuth()
  const [isRedirecting, setIsRedirecting] = useState(false)

  const handleLogin = async () => {
    try {
      setIsRedirecting(true)
      await initializeFacebookAuth(tierId, billingCycle)
    } catch (error) {
      logger.error('Facebook login failed:', error)
      setIsRedirecting(false)
    }
  }

  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg'
  }

  const variantClasses = {
    primary: 'bg-white border border-neutral-300 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-400',
    secondary: 'bg-neutral-100 border border-neutral-200 text-neutral-600 hover:bg-neutral-200'
  }

  const isButtonLoading = isRedirecting

  return (
    <button
      onClick={handleLogin}
      disabled={isButtonLoading}
      className={`
        inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200
        ${sizeClasses[size]}
        ${variantClasses[variant]}
        ${isButtonLoading ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md active:scale-[0.98]'}
        ${className}
      `}
    >
      {isButtonLoading ? (
        <>
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-600 mr-3"></div>
          {isRedirecting ? 'Redirecting...' : 'Connecting...'}
        </>
      ) : (
        <>
          <svg className="h-5 w-5 mr-3" viewBox="0 0 24 24">
            <path fill="#1877F2" d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
          </svg>
          {children || 'Continue with Facebook'}
        </>
      )}
    </button>
  )
}
