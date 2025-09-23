// frontend/src/app/login/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '../../hooks/use-auth';

declare global {
  interface Window {
    google: any;
  }
}

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated, isLoading, error, clearError } = useAuth();
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  
  const redirectPath = searchParams.get('redirect') || '/dashboard';

  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirectPath);
    }
  }, [isAuthenticated, router, redirectPath]);

  useEffect(() => {
    const loadGoogleScript = () => {
      if (window.google) {
        initializeGoogleSignIn();
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = initializeGoogleSignIn;
      document.head.appendChild(script);
    };

    const initializeGoogleSignIn = () => {
      if (!window.google) {
        console.error('Google API not loaded');
        return;
      }

      const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
      if (!clientId) {
        console.error('NEXT_PUBLIC_GOOGLE_CLIENT_ID environment variable not found');
        return;
      }

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleCallback,
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      window.google.accounts.id.renderButton(
        document.getElementById('google-signin-button'),
        {
          theme: 'outline',
          size: 'large',
          width: '100%',
          text: 'signin_with',
          shape: 'rectangular',
        }
      );
    };

    loadGoogleScript();
  }, []);

  const handleGoogleCallback = async (response: any) => {
    try {
      setIsGoogleLoading(true);
      clearError();
      
      await login(response.credential);
    } catch (error) {
      console.error('Google authentication failed:', error);
    } finally {
      setIsGoogleLoading(false);
    }
  };

  if (isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-admin-primary mx-auto"></div>
          <p className="mt-2 text-sm text-neutral-600">Redirecting...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50">
      <div className="w-full max-w-md space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-neutral-900">
            Admin Login
          </h1>
          <p className="mt-2 text-sm text-neutral-600">
            Sign in with your Google account to access the admin dashboard
          </p>
        </div>
        
        <div className="rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
          {error && (
            <div className="mb-4 rounded-md bg-red-50 border border-red-200 p-4">
              <div className="text-sm text-red-700">
                <p className="font-medium">{error.error}</p>
                <p className="mt-1">{error.message}</p>
                {error.details && (
                  <p className="mt-1 text-xs text-red-600">{error.details}</p>
                )}
              </div>
            </div>
          )}
          
          <div className="space-y-4">
            <div 
              id="google-signin-button"
              className={`w-full min-h-[40px] ${(isLoading || isGoogleLoading) ? 'opacity-50 pointer-events-none' : ''}`}
            ></div>
            
            {(isLoading || isGoogleLoading) && (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-admin-primary"></div>
                <span className="ml-2 text-sm text-neutral-600">Authenticating...</span>
              </div>
            )}
            
            <p className="text-xs text-neutral-500 text-center">
              By signing in, you agree to access the admin interface for document management.
            </p>
          </div>
        </div>
        
        <div className="text-center">
          <button
            onClick={() => router.push('/')}
            className="text-sm text-neutral-600 hover:text-neutral-900 transition-colors"
          >
            ← Back to home
          </button>
        </div>
      </div>
    </div>
  );
}