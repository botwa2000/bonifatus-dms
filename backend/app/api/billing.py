# backend/app/api/billing.py
"""
Billing API - Main Router
Combines all billing-related endpoints into a single router
"""

from fastapi import APIRouter
from app.api import (
    billing_subscriptions,
    billing_payments,
    billing_invoices,
    billing_discounts,
    billing_dashboard
)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

# Include all sub-routers
router.include_router(billing_subscriptions.router)
router.include_router(billing_payments.router)
router.include_router(billing_invoices.router)
router.include_router(billing_discounts.router)
router.include_router(billing_dashboard.router)
