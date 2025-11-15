# backend/app/api/billing_dashboard.py
"""
Billing API - Dashboard and Settings Endpoints
Provides billing overview and settings management
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
import stripe as stripe_lib

from app.schemas.billing_schemas import (
    BillingDashboardResponse,
    BillingDetailsUpdateRequest,
    SubscriptionResponse,
    PaymentMethodResponse,
    InvoiceResponse,
    CardDetails,
    InvoiceLineItem
)
from app.database.connection import get_db
from app.database.models import User, Subscription, TierPlan, Invoice
from app.middleware.auth_middleware import get_current_active_user
from app.services.stripe_service import stripe_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/dashboard",
    response_model=BillingDashboardResponse,
    summary="Get Billing Dashboard"
)
async def get_billing_dashboard(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> BillingDashboardResponse:
    """Get complete billing overview"""
    try:
        subscription_response = None
        subscription = session.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status.in_(['active', 'trialing', 'past_due']))
        ).scalar_one_or_none()

        if subscription:
            tier = session.query(TierPlan).filter(TierPlan.id == subscription.tier_id).first()
            if tier:
                subscription_response = SubscriptionResponse(
                    id=subscription.stripe_subscription_id,
                    user_id=str(current_user.id),
                    tier_id=tier.id,
                    tier_name=tier.display_name,
                    billing_cycle=subscription.billing_cycle,
                    status=subscription.status,
                    current_period_start=subscription.current_period_start,
                    current_period_end=subscription.current_period_end,
                    trial_start=subscription.trial_start,
                    trial_end=subscription.trial_end,
                    cancel_at_period_end=subscription.cancel_at_period_end,
                    canceled_at=subscription.canceled_at,
                    amount=tier.price_monthly_cents if subscription.billing_cycle == 'monthly' else tier.price_yearly_cents,
                    currency=tier.currency,
                    created_at=subscription.created_at
                )

        payment_methods = []
        upcoming_invoice_response = None

        if current_user.stripe_customer_id:
            pms = await stripe_service.list_payment_methods(current_user.stripe_customer_id, 'card')

            customer = stripe_lib.Customer.retrieve(current_user.stripe_customer_id)
            default_payment_method_id = None
            if customer.invoice_settings and customer.invoice_settings.default_payment_method:
                default_payment_method_id = customer.invoice_settings.default_payment_method

            for pm in pms:
                card_details = None
                if pm.type == 'card' and pm.card:
                    card_details = CardDetails(
                        brand=pm.card.brand,
                        last4=pm.card.last4,
                        exp_month=pm.card.exp_month,
                        exp_year=pm.card.exp_year,
                        country=pm.card.country
                    )

                payment_methods.append(PaymentMethodResponse(
                    id=pm.id,
                    type=pm.type,
                    card=card_details,
                    is_default=(pm.id == default_payment_method_id),
                    created_at=datetime.fromtimestamp(pm.created, tz=timezone.utc)
                ))

            if subscription:
                try:
                    upcoming_invoice = await stripe_service.get_upcoming_invoice(
                        current_user.stripe_customer_id,
                        subscription.stripe_subscription_id
                    )

                    if upcoming_invoice:
                        line_items = []
                        if upcoming_invoice.lines and upcoming_invoice.lines.data:
                            for line in upcoming_invoice.lines.data:
                                line_items.append(InvoiceLineItem(
                                    description=line.description or "Subscription",
                                    amount=line.amount,
                                    quantity=line.quantity or 1,
                                    period_start=datetime.fromtimestamp(line.period.start, tz=timezone.utc) if line.period else None,
                                    period_end=datetime.fromtimestamp(line.period.end, tz=timezone.utc) if line.period else None
                                ))

                        upcoming_invoice_response = InvoiceResponse(
                            id=upcoming_invoice.id or "upcoming",
                            invoice_number="Upcoming",
                            status="draft",
                            amount_due=upcoming_invoice.amount_due,
                            amount_paid=0,
                            subtotal=upcoming_invoice.subtotal,
                            tax=upcoming_invoice.tax or 0,
                            discount=upcoming_invoice.total_discount_amounts[0].amount if upcoming_invoice.total_discount_amounts else 0,
                            currency=upcoming_invoice.currency.upper(),
                            period_start=datetime.fromtimestamp(upcoming_invoice.period_start, tz=timezone.utc) if upcoming_invoice.period_start else None,
                            period_end=datetime.fromtimestamp(upcoming_invoice.period_end, tz=timezone.utc) if upcoming_invoice.period_end else None,
                            due_date=datetime.fromtimestamp(upcoming_invoice.due_date, tz=timezone.utc) if upcoming_invoice.due_date else None,
                            paid_at=None,
                            pdf_url=None,
                            hosted_url=None,
                            line_items=line_items,
                            created_at=datetime.fromtimestamp(upcoming_invoice.created, tz=timezone.utc) if upcoming_invoice.created else datetime.now(timezone.utc)
                        )
                except Exception as e:
                    logger.warning(f"Failed to fetch upcoming invoice: {e}")

        recent_invoices = []
        invoices = session.query(Invoice).filter(
            Invoice.user_id == current_user.id
        ).order_by(Invoice.created_at.desc()).limit(5).all()

        for inv in invoices:
            line_items = []
            if inv.line_items:
                for item in inv.line_items:
                    line_items.append(InvoiceLineItem(**item))

            recent_invoices.append(InvoiceResponse(
                id=inv.stripe_invoice_id,
                invoice_number=inv.invoice_number,
                status=inv.status,
                amount_due=inv.amount_due_cents,
                amount_paid=inv.amount_paid_cents,
                subtotal=inv.subtotal_cents,
                tax=inv.tax_cents,
                discount=inv.discount_cents,
                currency=inv.currency,
                period_start=inv.period_start,
                period_end=inv.period_end,
                due_date=inv.due_date,
                paid_at=inv.paid_at,
                pdf_url=inv.pdf_url,
                hosted_url=inv.hosted_invoice_url,
                line_items=line_items,
                created_at=inv.created_at
            ))

        return BillingDashboardResponse(
            subscription=subscription_response,
            payment_methods=payment_methods,
            upcoming_invoice=upcoming_invoice_response,
            recent_invoices=recent_invoices,
            billing_email=current_user.billing_email,
            billing_name=current_user.billing_name,
            billing_address=current_user.billing_address,
            vat_id=current_user.vat_id
        )

    except Exception as e:
        logger.error(f"Get billing dashboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put(
    "/billing-details",
    status_code=status.HTTP_200_OK,
    summary="Update Billing Details"
)
async def update_billing_details(
    details_request: BillingDetailsUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Update billing contact information"""
    try:
        if details_request.billing_email is not None:
            current_user.billing_email = details_request.billing_email

        if details_request.billing_name is not None:
            current_user.billing_name = details_request.billing_name

        if details_request.billing_address is not None:
            current_user.billing_address = details_request.billing_address

        if details_request.vat_id is not None:
            current_user.vat_id = details_request.vat_id

        if current_user.stripe_customer_id:
            await stripe_service.update_customer(
                current_user.stripe_customer_id,
                email=details_request.billing_email,
                name=details_request.billing_name,
                address=details_request.billing_address
            )

        session.commit()

        logger.info(f"Updated billing details for user {current_user.email}")

        return {"message": "Billing details updated successfully"}

    except Exception as e:
        session.rollback()
        logger.error(f"Update billing details error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
