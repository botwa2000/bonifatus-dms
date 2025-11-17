# backend/app/schemas/billing_schemas.py
"""
Bonifatus DMS - Billing and Payment Schemas
Pydantic models for subscription management, payments, and invoicing
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


# ============================================================
# Enums
# ============================================================

class BillingCycle(str, Enum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    """Stripe subscription statuses"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"


class PaymentStatus(str, Enum):
    """Payment transaction statuses"""
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class InvoiceStatus(str, Enum):
    """Invoice statuses"""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class DiscountType(str, Enum):
    """Discount code types"""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_MONTHS = "free_months"


# ============================================================
# Subscription Schemas
# ============================================================

class SubscriptionCreateRequest(BaseModel):
    """Request to create a new subscription"""
    tier_id: int = Field(..., description="Tier plan ID to subscribe to", ge=1)
    billing_cycle: BillingCycle = Field(..., description="Billing cycle (monthly or yearly)")
    currency: str = Field(..., description="Currency code (e.g., USD, EUR)", min_length=3, max_length=3)
    payment_method_id: Optional[str] = Field(None, description="Stripe payment method ID")
    discount_code: Optional[str] = Field(None, description="Discount or promo code to apply")
    trial_days: Optional[int] = Field(None, description="Number of trial days", ge=0, le=90)

    class Config:
        json_schema_extra = {
            "example": {
                "tier_id": 2,
                "billing_cycle": "monthly",
                "currency": "USD",
                "payment_method_id": "pm_1234567890",
                "discount_code": "LAUNCH25",
                "trial_days": 14
            }
        }


class SubscriptionUpdateRequest(BaseModel):
    """Request to update existing subscription"""
    tier_id: Optional[int] = Field(None, description="New tier plan ID (upgrade/downgrade)", ge=1)
    billing_cycle: Optional[BillingCycle] = Field(None, description="Change billing cycle")
    cancel_at_period_end: Optional[bool] = Field(None, description="Cancel subscription at period end")

    class Config:
        json_schema_extra = {
            "example": {
                "tier_id": 2,
                "billing_cycle": "yearly"
            }
        }


class SubscriptionResponse(BaseModel):
    """Subscription details response"""
    id: str = Field(..., description="Subscription ID")
    user_id: str = Field(..., description="User ID")
    tier_id: int = Field(..., description="Current tier ID")
    tier_name: str = Field(..., description="Current tier name")
    billing_cycle: str = Field(..., description="Billing cycle (monthly/yearly)")
    status: str = Field(..., description="Subscription status")
    current_period_start: datetime = Field(..., description="Current billing period start")
    current_period_end: datetime = Field(..., description="Current billing period end")
    trial_start: Optional[datetime] = Field(None, description="Trial start date")
    trial_end: Optional[datetime] = Field(None, description="Trial end date")
    cancel_at_period_end: bool = Field(..., description="Will cancel at period end")
    canceled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    amount: int = Field(..., description="Subscription amount in cents")
    currency: str = Field(..., description="Currency code")
    currency_symbol: Optional[str] = Field(None, description="Currency symbol")
    created_at: datetime = Field(..., description="Subscription creation date")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "sub_1234567890",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "tier_id": 2,
                "tier_name": "Professional",
                "billing_cycle": "monthly",
                "status": "active",
                "current_period_start": "2024-09-01T00:00:00Z",
                "current_period_end": "2024-10-01T00:00:00Z",
                "trial_start": None,
                "trial_end": None,
                "cancel_at_period_end": False,
                "canceled_at": None,
                "amount": 2999,
                "currency": "USD",
                "created_at": "2024-09-01T00:00:00Z"
            }
        }


# ============================================================
# Payment Method Schemas
# ============================================================

class PaymentMethodAttachRequest(BaseModel):
    """Request to attach payment method to customer"""
    payment_method_id: str = Field(..., description="Stripe payment method ID from client")
    set_as_default: bool = Field(True, description="Set as default payment method")

    class Config:
        json_schema_extra = {
            "example": {
                "payment_method_id": "pm_1234567890",
                "set_as_default": True
            }
        }


class CardDetails(BaseModel):
    """Credit card details (safe fields only)"""
    brand: str = Field(..., description="Card brand (visa, mastercard, amex)")
    last4: str = Field(..., description="Last 4 digits")
    exp_month: int = Field(..., description="Expiration month")
    exp_year: int = Field(..., description="Expiration year")
    country: Optional[str] = Field(None, description="Card issuing country")

    class Config:
        json_schema_extra = {
            "example": {
                "brand": "visa",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2025,
                "country": "US"
            }
        }


class PaymentMethodResponse(BaseModel):
    """Payment method details response"""
    id: str = Field(..., description="Payment method ID")
    type: str = Field(..., description="Payment method type (card, sepa_debit, etc)")
    card: Optional[CardDetails] = Field(None, description="Card details if type is card")
    is_default: bool = Field(..., description="Is default payment method")
    created_at: datetime = Field(..., description="Payment method creation date")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "pm_1234567890",
                "type": "card",
                "card": {
                    "brand": "visa",
                    "last4": "4242",
                    "exp_month": 12,
                    "exp_year": 2025,
                    "country": "US"
                },
                "is_default": True,
                "created_at": "2024-09-01T00:00:00Z"
            }
        }


# ============================================================
# Invoice Schemas
# ============================================================

class InvoiceLineItem(BaseModel):
    """Invoice line item"""
    description: str = Field(..., description="Line item description")
    amount: int = Field(..., description="Amount in cents")
    quantity: int = Field(..., description="Quantity")
    period_start: Optional[datetime] = Field(None, description="Service period start")
    period_end: Optional[datetime] = Field(None, description="Service period end")

    class Config:
        json_schema_extra = {
            "example": {
                "description": "BoniDoc Professional - Monthly",
                "amount": 2999,
                "quantity": 1,
                "period_start": "2024-09-01T00:00:00Z",
                "period_end": "2024-10-01T00:00:00Z"
            }
        }


class InvoiceResponse(BaseModel):
    """Invoice details response"""
    id: str = Field(..., description="Invoice ID")
    invoice_number: str = Field(..., description="Human-readable invoice number")
    status: str = Field(..., description="Invoice status")
    amount_due: int = Field(..., description="Amount due in cents")
    amount_paid: int = Field(..., description="Amount paid in cents")
    subtotal: int = Field(..., description="Subtotal in cents")
    tax: int = Field(..., description="Tax amount in cents")
    discount: int = Field(..., description="Discount amount in cents")
    currency: str = Field(..., description="Currency code")
    period_start: Optional[datetime] = Field(None, description="Billing period start")
    period_end: Optional[datetime] = Field(None, description="Billing period end")
    due_date: Optional[datetime] = Field(None, description="Payment due date")
    paid_at: Optional[datetime] = Field(None, description="Payment timestamp")
    pdf_url: Optional[str] = Field(None, description="Invoice PDF download URL")
    hosted_url: Optional[str] = Field(None, description="Stripe hosted invoice page URL")
    line_items: List[InvoiceLineItem] = Field(default_factory=list, description="Invoice line items")
    created_at: datetime = Field(..., description="Invoice creation date")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "in_1234567890",
                "invoice_number": "BONIDOC-2024-001",
                "status": "paid",
                "amount_due": 2999,
                "amount_paid": 2999,
                "subtotal": 2999,
                "tax": 0,
                "discount": 0,
                "currency": "USD",
                "period_start": "2024-09-01T00:00:00Z",
                "period_end": "2024-10-01T00:00:00Z",
                "due_date": "2024-09-01T00:00:00Z",
                "paid_at": "2024-09-01T10:30:00Z",
                "pdf_url": "https://pay.stripe.com/invoice/...",
                "hosted_url": "https://invoice.stripe.com/i/...",
                "line_items": [],
                "created_at": "2024-09-01T00:00:00Z"
            }
        }


class InvoiceListResponse(BaseModel):
    """List of invoices with pagination"""
    invoices: List[InvoiceResponse] = Field(..., description="List of invoices")
    has_more: bool = Field(..., description="More invoices available")
    total_count: int = Field(..., description="Total number of invoices")

    class Config:
        json_schema_extra = {
            "example": {
                "invoices": [],
                "has_more": False,
                "total_count": 5
            }
        }


# ============================================================
# Discount Code Schemas
# ============================================================

class DiscountCodeCreateRequest(BaseModel):
    """Admin request to create discount code"""
    code: str = Field(..., description="Discount code (uppercase, alphanumeric)", min_length=3, max_length=50)
    discount_type: DiscountType = Field(..., description="Type of discount")
    discount_value: int = Field(..., description="Discount value (percentage as whole number or cents)", gt=0)
    currency: Optional[str] = Field(None, description="Currency for fixed_amount discounts")
    duration: str = Field(..., description="Duration: once, repeating, forever")
    duration_in_months: Optional[int] = Field(None, description="Months for repeating duration", ge=1, le=36)
    max_redemptions: Optional[int] = Field(None, description="Maximum number of redemptions (null = unlimited)")
    valid_from: Optional[datetime] = Field(None, description="Valid from date")
    valid_until: Optional[datetime] = Field(None, description="Valid until date")
    applicable_tiers: Optional[List[int]] = Field(None, description="Tier IDs this code applies to (null = all)")
    description: Optional[str] = Field(None, description="Internal description")

    @validator('code')
    def validate_code(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Code must be alphanumeric (hyphens and underscores allowed)')
        return v.upper()

    class Config:
        json_schema_extra = {
            "example": {
                "code": "LAUNCH25",
                "discount_type": "percentage",
                "discount_value": 25,
                "duration": "once",
                "max_redemptions": 100,
                "valid_from": "2024-09-01T00:00:00Z",
                "valid_until": "2024-12-31T23:59:59Z",
                "applicable_tiers": [1, 2],
                "description": "Launch promotion - 25% off"
            }
        }


class DiscountCodeResponse(BaseModel):
    """Discount code details response"""
    id: str = Field(..., description="Discount code ID")
    code: str = Field(..., description="Discount code")
    discount_type: str = Field(..., description="Type of discount")
    discount_value: int = Field(..., description="Discount value")
    currency: Optional[str] = Field(None, description="Currency code")
    duration: str = Field(..., description="Duration type")
    duration_in_months: Optional[int] = Field(None, description="Duration in months")
    times_redeemed: int = Field(..., description="Number of times redeemed")
    max_redemptions: Optional[int] = Field(None, description="Maximum redemptions")
    valid_from: Optional[datetime] = Field(None, description="Valid from date")
    valid_until: Optional[datetime] = Field(None, description="Valid until date")
    applicable_tiers: Optional[List[int]] = Field(None, description="Applicable tier IDs")
    is_active: bool = Field(..., description="Is code active")
    description: Optional[str] = Field(None, description="Description")
    created_at: datetime = Field(..., description="Creation date")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "code": "LAUNCH25",
                "discount_type": "percentage",
                "discount_value": 25,
                "currency": None,
                "duration": "once",
                "duration_in_months": None,
                "times_redeemed": 15,
                "max_redemptions": 100,
                "valid_from": "2024-09-01T00:00:00Z",
                "valid_until": "2024-12-31T23:59:59Z",
                "applicable_tiers": [1, 2],
                "is_active": True,
                "description": "Launch promotion",
                "created_at": "2024-09-01T00:00:00Z"
            }
        }


class DiscountCodeValidateRequest(BaseModel):
    """Request to validate a discount code"""
    code: str = Field(..., description="Discount code to validate")
    tier_id: int = Field(..., description="Tier ID to apply discount to")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "LAUNCH25",
                "tier_id": 2
            }
        }


class DiscountCodeValidateResponse(BaseModel):
    """Discount code validation response"""
    valid: bool = Field(..., description="Is code valid")
    discount_code: Optional[DiscountCodeResponse] = Field(None, description="Discount code details if valid")
    error_message: Optional[str] = Field(None, description="Error message if invalid")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "discount_code": {
                    "code": "LAUNCH25",
                    "discount_type": "percentage",
                    "discount_value": 25
                },
                "error_message": None
            }
        }


# ============================================================
# Billing Dashboard Schemas
# ============================================================

class BillingDashboardResponse(BaseModel):
    """Complete billing dashboard data"""
    subscription: Optional[SubscriptionResponse] = Field(None, description="Current subscription")
    payment_methods: List[PaymentMethodResponse] = Field(default_factory=list, description="Payment methods")
    upcoming_invoice: Optional[InvoiceResponse] = Field(None, description="Upcoming invoice preview")
    recent_invoices: List[InvoiceResponse] = Field(default_factory=list, description="Recent invoices")
    billing_email: Optional[str] = Field(None, description="Billing email")
    billing_name: Optional[str] = Field(None, description="Billing name")
    billing_address: Optional[Dict[str, Any]] = Field(None, description="Billing address")
    vat_id: Optional[str] = Field(None, description="VAT ID")

    class Config:
        json_schema_extra = {
            "example": {
                "subscription": None,
                "payment_methods": [],
                "upcoming_invoice": None,
                "recent_invoices": [],
                "billing_email": "billing@example.com",
                "billing_name": "John Doe",
                "billing_address": {
                    "line1": "123 Main St",
                    "city": "San Francisco",
                    "country": "US"
                },
                "vat_id": None
            }
        }


class BillingDetailsUpdateRequest(BaseModel):
    """Request to update billing details"""
    billing_email: Optional[str] = Field(None, description="Billing email")
    billing_name: Optional[str] = Field(None, description="Billing name")
    billing_address: Optional[Dict[str, Any]] = Field(None, description="Billing address")
    vat_id: Optional[str] = Field(None, description="VAT ID")

    class Config:
        json_schema_extra = {
            "example": {
                "billing_email": "billing@company.com",
                "billing_name": "Company LLC",
                "billing_address": {
                    "line1": "123 Business Ave",
                    "line2": "Suite 100",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94105",
                    "country": "US"
                },
                "vat_id": "DE123456789"
            }
        }


# ============================================================
# Webhook Schemas
# ============================================================

class WebhookEventResponse(BaseModel):
    """Webhook event processing response"""
    received: bool = Field(..., description="Event received and queued")
    event_id: str = Field(..., description="Stripe event ID")
    event_type: str = Field(..., description="Event type")

    class Config:
        json_schema_extra = {
            "example": {
                "received": True,
                "event_id": "evt_1234567890",
                "event_type": "invoice.payment_succeeded"
            }
        }
