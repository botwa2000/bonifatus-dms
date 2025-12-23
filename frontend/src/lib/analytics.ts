// frontend/src/lib/analytics.ts
/**
 * Analytics tracking utilities
 * Supports multiple analytics providers: Google Analytics 4, PostHog, Plausible
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import { logger } from '@/lib/logger'

// Google Analytics 4
export const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || ''

// PostHog (Product Analytics with session recordings)
export const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY || ''
export const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com'

// Plausible (Privacy-friendly analytics)
export const PLAUSIBLE_DOMAIN = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN || 'bonidoc.com'

// Check if analytics should be enabled
// In production: always enabled
// In development: only if NEXT_PUBLIC_ENABLE_ANALYTICS_DEV is true
const isProduction = process.env.NODE_ENV === 'production'
const enableInDev = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS_DEV === 'true'
const analyticsEnabled = isProduction || enableInDev

// --- Google Analytics 4 ---
declare global {
  interface Window {
    gtag?: (...args: any[]) => void
    dataLayer?: any[]
    posthog?: any
  }
}

export const pageview = (url: string) => {
  if (!analyticsEnabled || !GA_MEASUREMENT_ID) return

  if (!isProduction) {
    logger.debug('[Analytics DEV] Pageview:', url)
  }

  window.gtag?.('config', GA_MEASUREMENT_ID, {
    page_path: url,
  })
}

export const event = ({ action, category, label, value }: {
  action: string
  category: string
  label?: string
  value?: number
}) => {
  if (!analyticsEnabled || !GA_MEASUREMENT_ID) return

  if (!isProduction) {
    logger.debug('[Analytics DEV] Event:', { action, category, label, value })
  }

  window.gtag?.('event', action, {
    event_category: category,
    event_label: label,
    value: value,
  })
}

// --- Custom Event Tracking ---

// User Authentication Events
export const trackSignup = (method: 'google' | 'email') => {
  event({
    action: 'signup',
    category: 'authentication',
    label: method,
  })

  // PostHog
  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('user_signup', { method })
  }
}

export const trackLogin = (method: 'google' | 'email') => {
  event({
    action: 'login',
    category: 'authentication',
    label: method,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('user_login', { method })
  }
}

export const trackLogout = () => {
  event({
    action: 'logout',
    category: 'authentication',
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('user_logout')
  }
}

// Document Events
export const trackDocumentUpload = (fileType: string, fileSize: number) => {
  event({
    action: 'document_upload',
    category: 'documents',
    label: fileType,
    value: Math.round(fileSize / 1024), // KB
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('document_upload', {
      file_type: fileType,
      file_size_kb: Math.round(fileSize / 1024),
    })
  }
}

export const trackDocumentView = (documentId: string) => {
  event({
    action: 'document_view',
    category: 'documents',
    label: documentId,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('document_view', { document_id: documentId })
  }
}

export const trackDocumentDownload = (documentId: string, fileType: string) => {
  event({
    action: 'document_download',
    category: 'documents',
    label: fileType,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('document_download', {
      document_id: documentId,
      file_type: fileType,
    })
  }
}

export const trackDocumentDelete = (documentId: string) => {
  event({
    action: 'document_delete',
    category: 'documents',
    label: documentId,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('document_delete', { document_id: documentId })
  }
}

export const trackDocumentSearch = (query: string, resultsCount: number) => {
  event({
    action: 'document_search',
    category: 'search',
    label: query,
    value: resultsCount,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('document_search', {
      query,
      results_count: resultsCount,
    })
  }
}

// Subscription Events (Conversions)
export const trackSubscriptionStart = (tier: string, billingCycle: string) => {
  event({
    action: 'subscription_start',
    category: 'conversion',
    label: `${tier}_${billingCycle}`,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('subscription_start', {
      tier,
      billing_cycle: billingCycle,
    })
  }
}

export const trackSubscriptionComplete = (tier: string, billingCycle: string, amount: number) => {
  // GA4 Enhanced Ecommerce
  window.gtag?.('event', 'purchase', {
    transaction_id: `sub_${Date.now()}`,
    value: amount,
    currency: 'USD',
    items: [{
      item_id: tier,
      item_name: `${tier} Plan`,
      item_category: 'subscription',
      price: amount,
      quantity: 1,
    }],
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('subscription_complete', {
      tier,
      billing_cycle: billingCycle,
      amount,
      currency: 'USD',
    })
  }
}

export const trackSubscriptionCancel = (tier: string, reason?: string) => {
  event({
    action: 'subscription_cancel',
    category: 'conversion',
    label: tier,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('subscription_cancel', {
      tier,
      reason,
    })
  }
}

// Delegate Access Events
export const trackDelegateInvite = (role: string) => {
  event({
    action: 'delegate_invite',
    category: 'collaboration',
    label: role,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('delegate_invite', { role })
  }
}

export const trackDelegateAccept = (ownerName: string, role: string) => {
  event({
    action: 'delegate_accept',
    category: 'collaboration',
    label: role,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('delegate_accept', {
      owner_name: ownerName,
      role,
    })
  }
}

export const trackDelegateViewDocuments = (ownerName: string, documentCount: number) => {
  event({
    action: 'delegate_view_documents',
    category: 'collaboration',
    value: documentCount,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('delegate_view_documents', {
      owner_name: ownerName,
      document_count: documentCount,
    })
  }
}

// Feature Usage Events
export const trackFeatureUse = (featureName: string, metadata?: Record<string, unknown>) => {
  event({
    action: 'feature_use',
    category: 'engagement',
    label: featureName,
  })

  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.capture('feature_use', {
      feature_name: featureName,
      ...metadata,
    })
  }
}

// Identify user (for PostHog)
export const identifyUser = (userId: string, properties?: Record<string, unknown>) => {
  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.identify(userId, properties)
  }
}

// Reset user (on logout)
export const resetUser = () => {
  if (typeof window !== 'undefined' && window.posthog) {
    window.posthog.reset()
  }
}
