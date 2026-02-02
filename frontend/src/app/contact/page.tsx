'use client'

import { useState, useRef, useCallback } from 'react'
import { Turnstile, type TurnstileInstance } from '@marsidev/react-turnstile'
import PublicHeader from '@/components/PublicHeader'

const SUBJECT_OPTIONS = [
  'General Inquiry',
  'Technical Support',
  'Billing Question',
  'Feature Request',
  'Bug Report',
  'Partnership',
  'Other',
]

type FormStatus = 'idle' | 'submitting' | 'success' | 'error'
type TurnstileStatus = 'loading' | 'solved' | 'error' | 'expired'

export default function ContactPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [subject, setSubject] = useState(SUBJECT_OPTIONS[0])
  const [message, setMessage] = useState('')
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null)
  const [turnstileStatus, setTurnstileStatus] = useState<TurnstileStatus>('loading')
  const [status, setStatus] = useState<FormStatus>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const turnstileRef = useRef<TurnstileInstance>(null)

  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? ''

  const handleTurnstileSuccess = useCallback((token: string) => {
    setTurnstileToken(token)
    setTurnstileStatus('solved')
  }, [])

  const handleTurnstileError = useCallback(() => {
    setTurnstileToken(null)
    setTurnstileStatus('error')
  }, [])

  const handleTurnstileExpire = useCallback(() => {
    setTurnstileToken(null)
    setTurnstileStatus('expired')
  }, [])

  const canSubmit = status !== 'submitting' && turnstileStatus === 'solved'

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setStatus('submitting')
    setErrorMessage('')

    const formData = new FormData(e.currentTarget)
    const honeypot = formData.get('website') as string | null

    if (!turnstileToken) {
      setErrorMessage('Please complete the security verification.')
      setStatus('error')
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      const res = await fetch(`${apiUrl}/api/v1/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          email,
          subject,
          message,
          turnstile_token: turnstileToken,
          honeypot: honeypot || null,
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => null)
        throw new Error(data?.detail ?? 'Failed to send message')
      }

      setStatus('success')
      setName('')
      setEmail('')
      setSubject(SUBJECT_OPTIONS[0])
      setMessage('')
      setTurnstileToken(null)
      setTurnstileStatus('loading')
      turnstileRef.current?.reset()
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Something went wrong')
      setStatus('error')
      // Reset Turnstile so user gets a fresh token for retry
      setTurnstileToken(null)
      setTurnstileStatus('loading')
      turnstileRef.current?.reset()
    }
  }

  const turnstileStatusMessage = () => {
    switch (turnstileStatus) {
      case 'loading':
        return <p className="text-sm text-neutral-500 dark:text-neutral-400">Verifying you are human...</p>
      case 'error':
        return (
          <div className="text-sm text-red-600 dark:text-red-400">
            Security verification failed.{' '}
            <button
              type="button"
              onClick={() => { setTurnstileStatus('loading'); turnstileRef.current?.reset() }}
              className="underline hover:no-underline"
            >
              Try again
            </button>
          </div>
        )
      case 'expired':
        return (
          <div className="text-sm text-amber-600 dark:text-amber-400">
            Verification expired.{' '}
            <button
              type="button"
              onClick={() => { setTurnstileStatus('loading'); turnstileRef.current?.reset() }}
              className="underline hover:no-underline"
            >
              Refresh
            </button>
          </div>
        )
      case 'solved':
        return <p className="text-sm text-green-600 dark:text-green-400">Verification complete</p>
    }
  }

  return (
    <div className="min-h-screen bg-white dark:bg-neutral-900">
      <PublicHeader />

      <div className="max-w-2xl mx-auto px-4 py-16">
        <h1 className="text-4xl font-bold text-neutral-900 dark:text-white mb-4">Contact Us</h1>
        <p className="text-neutral-600 dark:text-neutral-400 mb-8">
          Have a question or feedback? Reach out to us at{' '}
          <a href="mailto:info@bonidoc.com" className="text-admin-primary hover:underline">
            info@bonidoc.com
          </a>{' '}
          or use the form below.
        </p>

        {status === 'success' ? (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-green-800 dark:text-green-300 mb-2">Message sent!</h2>
            <p className="text-green-700 dark:text-green-400">
              Thank you for reaching out. We&apos;ll get back to you as soon as possible. A confirmation email has been sent to your inbox.
            </p>
            <button
              onClick={() => setStatus('idle')}
              className="mt-4 text-sm text-green-700 dark:text-green-400 underline hover:no-underline"
            >
              Send another message
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Honeypot - hidden from users */}
            <div className="hidden" aria-hidden="true">
              <label htmlFor="website">Website</label>
              <input type="text" id="website" name="website" tabIndex={-1} autoComplete="off" />
            </div>

            <div>
              <label htmlFor="name" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Name
              </label>
              <input
                id="name"
                type="text"
                required
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-neutral-900 dark:text-white focus:ring-2 focus:ring-admin-primary focus:border-transparent"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-neutral-900 dark:text-white focus:ring-2 focus:ring-admin-primary focus:border-transparent"
              />
            </div>

            <div>
              <label htmlFor="subject" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Subject
              </label>
              <select
                id="subject"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-neutral-900 dark:text-white focus:ring-2 focus:ring-admin-primary focus:border-transparent"
              >
                {SUBJECT_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="message" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Message
              </label>
              <textarea
                id="message"
                required
                minLength={10}
                maxLength={5000}
                rows={6}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-neutral-900 dark:text-white focus:ring-2 focus:ring-admin-primary focus:border-transparent resize-y"
              />
            </div>

            {siteKey ? (
              <div>
                <Turnstile
                  ref={turnstileRef}
                  siteKey={siteKey}
                  onSuccess={handleTurnstileSuccess}
                  onError={handleTurnstileError}
                  onExpire={handleTurnstileExpire}
                  options={{
                    theme: 'auto',
                  }}
                />
                <div className="mt-2">{turnstileStatusMessage()}</div>
              </div>
            ) : (
              <p className="text-sm text-red-600 dark:text-red-400">
                Security verification is not configured. Please contact us directly at info@bonidoc.com.
              </p>
            )}

            {status === 'error' && errorMessage && (
              <div className="text-red-600 dark:text-red-400 text-sm">{errorMessage}</div>
            )}

            <button
              type="submit"
              disabled={!canSubmit || !siteKey}
              className="w-full bg-admin-primary hover:bg-admin-primary/90 text-white font-medium py-2.5 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {status === 'submitting' ? 'Sending...' : 'Send Message'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
