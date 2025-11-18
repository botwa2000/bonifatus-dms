'use client'

import { useState, useEffect } from 'react'
import { Modal, ModalHeader, ModalContent, ModalFooter, Button, Select, Alert, Badge } from '@/components/ui'
import { apiClient } from '@/services/api-client'

interface CancellationReason {
  value: string
  label: string
}

interface CancellationModalProps {
  isOpen: boolean
  onClose: () => void
  subscription: {
    tier_name: string
    billing_cycle: string
    amount: number
    currency_symbol?: string
    current_period_end: string
    created_at?: string
  }
  onSuccess: () => void
}

type CancellationStep = 'retention' | 'reason' | 'confirm' | 'success'

interface CancellationResult {
  success: boolean
  message: string
  refund_issued: boolean
  refund_amount?: number
  refund_currency?: string
  access_end_date: string
  downgraded_to_free: boolean
}

export default function CancellationModal({ isOpen, onClose, subscription, onSuccess }: CancellationModalProps) {
  const [step, setStep] = useState<CancellationStep>('retention')
  const [cancelType, setCancelType] = useState<'immediate' | 'at_period_end'>('at_period_end')
  const [reasons, setReasons] = useState<CancellationReason[]>([])
  const [selectedReason, setSelectedReason] = useState('')
  const [feedback, setFeedback] = useState('')
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CancellationResult | null>(null)
  const [refundEligible, setRefundEligible] = useState(false)
  const [subscriptionAgeDays, setSubscriptionAgeDays] = useState(0)

  // Calculate subscription age and refund eligibility
  useEffect(() => {
    if (subscription.created_at) {
      const created = new Date(subscription.created_at)
      const now = new Date()
      const diffTime = Math.abs(now.getTime() - created.getTime())
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      setSubscriptionAgeDays(diffDays)
      setRefundEligible(diffDays <= 14) // 14-day money-back guarantee
    }
  }, [subscription.created_at])

  // Load cancellation reasons from database
  useEffect(() => {
    if (isOpen && step === 'reason') {
      loadCancellationReasons()
    }
  }, [isOpen, step])

  const loadCancellationReasons = async () => {
    try {
      const data = await apiClient.get<{ reasons: CancellationReason[] }>(
        '/api/v1/billing/cancellation-reasons?language=en',
        false
      )
      setReasons(data.reasons)
    } catch (error) {
      console.error('Failed to load cancellation reasons:', error)
      // Fallback reasons if API fails
      setReasons([
        { value: 'too_expensive', label: 'Too expensive' },
        { value: 'not_using', label: 'Not using it enough' },
        { value: 'other', label: 'Other reason' }
      ])
    }
  }

  const handleCancelSubscription = async () => {
    setProcessing(true)
    setError(null)

    try {
      const response = await apiClient.post<CancellationResult>(
        '/api/v1/billing/cancel-subscription',
        {
          cancellation_reason: selectedReason,
          feedback_text: feedback.trim() || null,
          cancel_type: cancelType
        },
        true
      )

      setResult(response)
      setStep('success')
      onSuccess()
    } catch (error: unknown) {
      console.error('Cancellation failed:', error)
      const errorDetail = error && typeof error === 'object' && 'detail' in error ? (error as { detail: string }).detail : null
      setError(errorDetail || 'Failed to cancel subscription. Please try again.')
    } finally {
      setProcessing(false)
    }
  }

  const handleClose = () => {
    if (!processing) {
      setStep('retention')
      setCancelType('at_period_end')
      setSelectedReason('')
      setFeedback('')
      setError(null)
      setResult(null)
      onClose()
    }
  }

  const renderRetentionStep = () => (
    <>
      <ModalHeader title="We're sorry to see you go" onClose={handleClose} />
      <ModalContent>
        <div className="space-y-6">
          {/* Current subscription info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-900 mb-2">Your current plan</h4>
            <div className="space-y-1 text-sm">
              <p className="text-blue-800">
                <span className="font-medium">{subscription.tier_name}</span> - {subscription.currency_symbol || '$'}{subscription.amount}/{subscription.billing_cycle === 'yearly' ? 'year' : 'month'}
              </p>
              <p className="text-blue-600">
                Next billing: {new Date(subscription.current_period_end).toLocaleDateString()}
              </p>
            </div>
          </div>

          {/* What they'll lose */}
          <div>
            <h4 className="font-semibold text-neutral-900 mb-3">
              What you&apos;ll miss with Free tier
            </h4>
            <ul className="space-y-2 text-sm text-neutral-700">
              <li className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mt-0.5 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Advanced document categorization with AI
              </li>
              <li className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mt-0.5 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Unlimited document uploads
              </li>
              <li className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mt-0.5 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Priority support
              </li>
              <li className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mt-0.5 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Bulk operations
              </li>
            </ul>
          </div>

          {/* Free tier features */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h4 className="font-semibold text-green-900 mb-2">What you&apos;ll keep with Free tier</h4>
            <ul className="space-y-1 text-sm text-green-800">
              <li>✓ Up to 50 documents per month</li>
              <li>✓ Basic document categorization</li>
              <li>✓ Access to your document history</li>
            </ul>
          </div>

          {/* Refund eligibility notice */}
          {refundEligible && (
            <Alert variant="info">
              <p className="font-medium">14-Day Money-Back Guarantee</p>
              <p className="text-sm mt-1">
                You subscribed {subscriptionAgeDays} day{subscriptionAgeDays !== 1 ? 's' : ''} ago.
                You&apos;re eligible for a full refund if you cancel immediately.
              </p>
            </Alert>
          )}

          {error && <Alert variant="error">{error}</Alert>}
        </div>
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={handleClose} disabled={processing}>
          Keep My Subscription
        </Button>
        <Button
          variant="danger"
          onClick={() => setStep('reason')}
          disabled={processing}
        >
          Continue to Cancel
        </Button>
      </ModalFooter>
    </>
  )

  const renderReasonStep = () => (
    <>
      <ModalHeader title="Help us improve" onClose={handleClose} />
      <ModalContent>
        <div className="space-y-6">
          <p className="text-neutral-600">
            We&apos;d love to know why you&apos;re canceling. Your feedback helps us improve.
          </p>

          {/* Cancellation type selection */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-neutral-700">
              When would you like to cancel?
            </label>
            <div className="space-y-2">
              {refundEligible && (
                <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-neutral-50 transition-colors">
                  <input
                    type="radio"
                    name="cancelType"
                    value="immediate"
                    checked={cancelType === 'immediate'}
                    onChange={() => setCancelType('immediate')}
                    className="mt-1 mr-3"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-neutral-900">Cancel immediately</div>
                    <div className="text-sm text-neutral-600 mt-1">
                      Full refund of {subscription.currency_symbol || '$'}{subscription.amount}. Access ends immediately.
                    </div>
                    <Badge variant="success" className="mt-2">Eligible for full refund</Badge>
                  </div>
                </label>
              )}
              <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-neutral-50 transition-colors">
                <input
                  type="radio"
                  name="cancelType"
                  value="at_period_end"
                  checked={cancelType === 'at_period_end'}
                  onChange={() => setCancelType('at_period_end')}
                  className="mt-1 mr-3"
                />
                <div className="flex-1">
                  <div className="font-medium text-neutral-900">Cancel at period end</div>
                  <div className="text-sm text-neutral-600 mt-1">
                    Keep access until {new Date(subscription.current_period_end).toLocaleDateString()}. No refund.
                  </div>
                  {!refundEligible && (
                    <Badge variant="default" className="mt-2">Recommended</Badge>
                  )}
                </div>
              </label>
            </div>
          </div>

          {/* Reason selection */}
          <div className="space-y-2">
            <label htmlFor="reason" className="block text-sm font-medium text-neutral-700">
              Why are you canceling? (Optional)
            </label>
            <Select
              id="reason"
              value={selectedReason}
              onChange={(e) => setSelectedReason(e.target.value)}
            >
              <option value="">Select a reason</option>
              {reasons.map(reason => (
                <option key={reason.value} value={reason.value}>
                  {reason.label}
                </option>
              ))}
            </Select>
          </div>

          {/* Feedback textarea */}
          <div className="space-y-2">
            <label htmlFor="feedback" className="block text-sm font-medium text-neutral-700">
              Additional feedback (Optional)
            </label>
            <textarea
              id="feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={4}
              maxLength={1000}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Tell us more about your experience..."
            />
            <p className="text-xs text-neutral-500 text-right">
              {feedback.length}/1000 characters
            </p>
          </div>

          {error && <Alert variant="error">{error}</Alert>}
        </div>
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={() => setStep('retention')} disabled={processing}>
          Back
        </Button>
        <Button
          variant="danger"
          onClick={() => setStep('confirm')}
          disabled={processing}
        >
          Continue
        </Button>
      </ModalFooter>
    </>
  )

  const renderConfirmStep = () => (
    <>
      <ModalHeader title="Confirm cancellation" onClose={handleClose} />
      <ModalContent>
        <div className="space-y-4">
          <Alert variant="warning">
            <p className="font-medium">Are you sure?</p>
            <p className="text-sm mt-1">
              {cancelType === 'immediate'
                ? 'Your subscription will be canceled immediately and you will receive a full refund.'
                : `Your subscription will end on ${new Date(subscription.current_period_end).toLocaleDateString()}. You&apos;ll have access until then.`
              }
            </p>
          </Alert>

          <div className="bg-neutral-50 rounded-lg p-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-neutral-600">Cancellation type:</span>
              <span className="font-medium text-neutral-900">
                {cancelType === 'immediate' ? 'Immediate' : 'At period end'}
              </span>
            </div>
            {cancelType === 'immediate' && refundEligible && (
              <div className="flex justify-between">
                <span className="text-neutral-600">Refund amount:</span>
                <span className="font-medium text-green-600">
                  {subscription.currency_symbol}{subscription.amount}
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-neutral-600">Access until:</span>
              <span className="font-medium text-neutral-900">
                {cancelType === 'immediate'
                  ? 'Immediately'
                  : new Date(subscription.current_period_end).toLocaleDateString()
                }
              </span>
            </div>
          </div>

          {error && <Alert variant="error">{error}</Alert>}
        </div>
      </ModalContent>
      <ModalFooter>
        <Button variant="ghost" onClick={() => setStep('reason')} disabled={processing}>
          Back
        </Button>
        <Button
          variant="danger"
          onClick={handleCancelSubscription}
          disabled={processing}
        >
          {processing ? 'Processing...' : 'Confirm Cancellation'}
        </Button>
      </ModalFooter>
    </>
  )

  const renderSuccessStep = () => (
    <>
      <ModalHeader title="Subscription canceled" onClose={handleClose} />
      <ModalContent>
        <div className="space-y-4">
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-lg font-medium text-neutral-900 mb-2">
              {result?.message}
            </p>
          </div>

          {result?.refund_issued && (
            <Alert variant="success">
              <p className="font-medium">Refund initiated</p>
              <p className="text-sm mt-1">
                A refund of {result.refund_currency} {result.refund_amount?.toFixed(2)} has been initiated.
                It will appear in your account within 5-10 business days.
              </p>
            </Alert>
          )}

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <span className="font-medium">Access until:</span> {result?.access_end_date}
            </p>
            {!result?.downgraded_to_free && (
              <p className="text-sm text-blue-800 mt-2">
                After this date, you&apos;ll be automatically downgraded to the Free tier.
              </p>
            )}
          </div>

          <p className="text-sm text-neutral-600 text-center">
            Changed your mind? You can reactivate your subscription anytime before {result?.access_end_date}.
          </p>
        </div>
      </ModalContent>
      <ModalFooter>
        <Button variant="primary" onClick={handleClose} className="w-full">
          Close
        </Button>
      </ModalFooter>
    </>
  )

  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="lg">
      {step === 'retention' && renderRetentionStep()}
      {step === 'reason' && renderReasonStep()}
      {step === 'confirm' && renderConfirmStep()}
      {step === 'success' && renderSuccessStep()}
    </Modal>
  )
}
