# backend/app/api/webhooks.py
"""
Webhook Endpoints - Stripe Event Processing
Handles asynchronous events from Stripe (payments, subscriptions, invoices)
"""

import logging
import asyncio
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database.connection import get_db
from app.database.models import (
    User, Subscription, Payment, Invoice, TierPlan, DiscountCode,
    UserDiscountRedemption
)
from app.services.stripe_service import stripe_service
from app.services.email_service import email_service
from app.schemas.billing_schemas import WebhookEventResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post(
    "/stripe",
    response_model=WebhookEventResponse,
    summary="Stripe Webhook Handler"
)
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_db)
) -> WebhookEventResponse:
    """
    Handle incoming Stripe webhook events

    Events processed:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    - invoice.finalized
    - payment_intent.succeeded
    - payment_intent.payment_failed
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')

        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )

        event = stripe_service.construct_webhook_event(payload, sig_header)

        if not event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )

        logger.info(f"Received Stripe webhook: {event.type} - {event.id}")

        if event.type == 'checkout.session.completed':
            await handle_checkout_session_completed(event, session)
        elif event.type == 'customer.subscription.created':
            await handle_subscription_created(event, session)
        elif event.type == 'customer.subscription.updated':
            await handle_subscription_updated(event, session)
        elif event.type == 'customer.subscription.deleted':
            await handle_subscription_deleted(event, session)
        elif event.type == 'invoice.payment_succeeded':
            await handle_invoice_payment_succeeded(event, session)
        elif event.type == 'invoice.payment_failed':
            await handle_invoice_payment_failed(event, session)
        elif event.type == 'invoice.finalized':
            await handle_invoice_finalized(event, session)
        elif event.type == 'payment_intent.succeeded':
            await handle_payment_intent_succeeded(event, session)
        elif event.type == 'payment_intent.payment_failed':
            await handle_payment_intent_failed(event, session)
        else:
            logger.info(f"Unhandled webhook event type: {event.type}")

        return WebhookEventResponse(
            received=True,
            event_id=event.id,
            event_type=event.type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def handle_checkout_session_completed(event, session: Session):
    """Process checkout.session.completed event"""
    checkout_session = event.data.object
    logger.info(f"[WEBHOOK] Processing checkout.session.completed: {checkout_session.id}")

    # Extract metadata
    user_id = checkout_session.metadata.get('user_id')
    tier_id = checkout_session.metadata.get('tier_id')
    billing_cycle = checkout_session.metadata.get('billing_cycle')
    referral_code = checkout_session.metadata.get('referral_code')

    logger.info(f"[WEBHOOK] Metadata: user_id={user_id}, tier_id={tier_id}, billing_cycle={billing_cycle}")

    if not user_id or not tier_id:
        logger.warning(f"[WEBHOOK] Missing metadata in checkout session {checkout_session.id}")
        return

    # Get user
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"[WEBHOOK] User {user_id} not found for checkout session {checkout_session.id}")
        return

    logger.info(f"[WEBHOOK] Found user: {user.email}, current stripe_customer_id: {user.stripe_customer_id}")

    # Update user's Stripe customer ID if not already set
    if not user.stripe_customer_id and checkout_session.customer:
        user.stripe_customer_id = checkout_session.customer
        logger.info(f"[WEBHOOK] Updated user {user.email} with stripe_customer_id: {checkout_session.customer}")

    # Get tier
    tier = session.query(TierPlan).filter(TierPlan.id == tier_id).first()
    if not tier:
        logger.warning(f"Tier {tier_id} not found for checkout session {checkout_session.id}")
        return

    # Process referral code if provided
    if referral_code:
        from app.database.models import Referral
        from datetime import datetime, timezone

        # Find the referrer by their referral code (assuming users have a referral_code field)
        # For now, just log the referral - full implementation depends on your referral system
        logger.info(f"Referral code '{referral_code}' used by user {user.email}")

        # TODO: Create referral record when referral system is fully implemented
        # referrer = session.query(User).filter(User.referral_code == referral_code).first()
        # if referrer:
        #     referral = Referral(
        #         referrer_id=referrer.id,
        #         referred_id=user.id,
        #         code=referral_code,
        #         status='completed',
        #         completed_at=datetime.now(timezone.utc)
        #     )
        #     session.add(referral)

    # Subscription will be created via the subscription.created webhook
    # Just log the successful checkout here
    logger.info(f"Checkout session completed for user {user.email}, tier {tier.name}")

    session.commit()


async def handle_subscription_created(event, session: Session):
    """Process subscription.created event"""
    stripe_sub = event.data.object
    logger.info(f"[WEBHOOK] Processing customer.subscription.created: {stripe_sub.id}, customer: {stripe_sub.customer}")

    user = session.query(User).filter(
        User.stripe_customer_id == stripe_sub.customer
    ).first()

    if not user:
        logger.warning(f"[WEBHOOK] User not found for customer {stripe_sub.customer}")
        return

    logger.info(f"[WEBHOOK] Found user: {user.email}")

    # Get tier from subscription metadata or price metadata
    tier_id = None
    if stripe_sub.metadata and 'tier_id' in stripe_sub.metadata:
        tier_id = stripe_sub.metadata['tier_id']
        logger.info(f"[WEBHOOK] Got tier_id from subscription metadata: {tier_id}")
    elif hasattr(stripe_sub, 'items') and stripe_sub.items:
        try:
            if hasattr(stripe_sub.items, 'data') and stripe_sub.items.data:
                items_data = stripe_sub.items.data
                if len(items_data) > 0:
                    item = items_data[0]
                    if hasattr(item, 'price') and item.price:
                        price = item.price
                        if hasattr(price, 'metadata') and price.metadata and 'tier_id' in price.metadata:
                            tier_id = price.metadata['tier_id']
                            logger.info(f"[WEBHOOK] Got tier_id from price metadata: {tier_id}")
        except Exception as e:
            logger.warning(f"[WEBHOOK] Error extracting tier_id from items: {e}")

    if not tier_id:
        logger.warning(f"[WEBHOOK] No tier_id found in subscription {stripe_sub.id}, metadata: {stripe_sub.metadata}")
        return

    tier = session.query(TierPlan).filter(TierPlan.id == tier_id).first()
    if not tier:
        logger.warning(f"[WEBHOOK] Tier {tier_id} not found")
        return

    logger.info(f"[WEBHOOK] Found tier: {tier.name}")

    # Check if subscription already exists
    existing_sub = session.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub.id
    ).first()

    if existing_sub:
        logger.info(f"[WEBHOOK] Subscription {stripe_sub.id} already exists")
        return

    logger.info(f"[WEBHOOK] Creating new subscription for user {user.email}")

    # Create subscription in database
    # Get billing cycle and currency from Stripe price
    price_interval = None
    currency = None
    amount_cents = None
    items_data = None
    if hasattr(stripe_sub, 'items') and hasattr(stripe_sub.items, 'data'):
        items_data = stripe_sub.items.data
        if items_data and len(items_data) > 0:
            price = items_data[0].price
            if hasattr(price, 'recurring') and price.recurring:
                price_interval = price.recurring.interval
            # Store the actual currency and amount charged
            currency = price.currency.upper() if hasattr(price, 'currency') and price.currency else None
            amount_cents = price.unit_amount if hasattr(price, 'unit_amount') and price.unit_amount else None

    billing_cycle = 'yearly' if price_interval == 'year' else 'monthly'

    db_subscription = Subscription(
        user_id=user.id,
        tier_id=tier.id,
        stripe_subscription_id=stripe_sub.id,
        stripe_price_id=items_data[0].price.id if items_data and len(items_data) > 0 else None,
        billing_cycle=billing_cycle,
        status=stripe_sub.status,
        current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start, tz=timezone.utc),
        current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc),
        trial_start=datetime.fromtimestamp(stripe_sub.trial_start, tz=timezone.utc) if stripe_sub.trial_start else None,
        trial_end=datetime.fromtimestamp(stripe_sub.trial_end, tz=timezone.utc) if stripe_sub.trial_end else None,
        cancel_at_period_end=stripe_sub.cancel_at_period_end,
        currency=currency,
        amount_cents=amount_cents
    )

    session.add(db_subscription)

    # Update user's tier
    user.tier_id = tier.id
    user.subscription_status = stripe_sub.status
    user.billing_cycle = billing_cycle
    user.subscription_started_at = datetime.now(timezone.utc)
    user.subscription_ends_at = datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc)

    session.commit()

    logger.info(f"[WEBHOOK] ✓ Created subscription {db_subscription.id} for user {user.email}, tier {tier.name}, currency: {currency}, amount: {amount_cents}")

    # Send subscription confirmation email
    try:
        # Get currency from price (reuse items_data from above)
        price = items_data[0].price if items_data and len(items_data) > 0 else None
        currency = price.currency.upper() if price and hasattr(price, 'currency') and price.currency else 'USD'
        amount = (price.unit_amount / 100) if price and hasattr(price, 'unit_amount') and price.unit_amount else 0

        # Get currency symbol
        from app.database.models import Currency
        currency_obj = session.query(Currency).filter(Currency.code == currency).first()
        currency_symbol = currency_obj.symbol if currency_obj else '$'

        # Format billing period
        billing_period = 'year' if billing_cycle == 'yearly' else 'month'

        # Format next billing date
        next_billing_date = db_subscription.current_period_end.strftime('%B %d, %Y')

        # Get dashboard URL from settings
        frontend_url = settings.app.app_frontend_url
        dashboard_url = f"{frontend_url}/dashboard"
        support_url = f"{frontend_url}/support"

        # Send email
        asyncio.create_task(
            email_service.send_subscription_confirmation(
                session=session,
                user_email=user.email,
                user_name=user.full_name or user.email,
                plan_name=tier.name,
                billing_cycle=billing_cycle,
                amount=amount,
                currency_symbol=currency_symbol,
                billing_period=billing_period,
                next_billing_date=next_billing_date,
                dashboard_url=dashboard_url,
                support_url=support_url
            )
        )
        logger.info(f"Subscription confirmation email queued for {user.email}")
    except Exception as e:
        logger.error(f"Failed to send subscription confirmation email: {e}")


async def handle_subscription_updated(event, session: Session):
    """Process subscription.updated event"""
    stripe_sub = event.data.object

    subscription = session.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub.id
    ).first()

    if not subscription:
        logger.warning(f"Subscription {stripe_sub.id} not found in database")
        return

    subscription.status = stripe_sub.status
    subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start, tz=timezone.utc)
    subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc)
    subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end

    if stripe_sub.canceled_at:
        subscription.canceled_at = datetime.fromtimestamp(stripe_sub.canceled_at, tz=timezone.utc)

    user = session.query(User).filter(User.id == subscription.user_id).first()
    if user:
        user.subscription_status = stripe_sub.status
        user.subscription_ends_at = datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc)

    session.commit()
    logger.info(f"Updated subscription {subscription.id} to status {stripe_sub.status}")


async def handle_subscription_deleted(event, session: Session):
    """Process subscription.deleted event"""
    stripe_sub = event.data.object

    subscription = session.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub.id
    ).first()

    if not subscription:
        logger.warning(f"Subscription {stripe_sub.id} not found in database")
        return

    subscription.status = 'canceled'
    subscription.ended_at = datetime.now(timezone.utc)

    user = session.query(User).filter(User.id == subscription.user_id).first()
    tier = session.query(TierPlan).filter(TierPlan.id == subscription.tier_id).first()

    if user:
        free_tier = session.query(TierPlan).filter(TierPlan.name == 'free').first()
        if free_tier:
            user.tier_id = free_tier.id
        user.subscription_status = 'canceled'

    session.commit()
    logger.info(f"Deleted subscription {subscription.id}")

    # Send cancellation confirmation email
    try:
        # Access ends at current_period_end (user keeps access until then)
        access_end_date = subscription.current_period_end.strftime('%B %d, %Y')

        # Get frontend URL
        frontend_url = settings.app.app_frontend_url
        reactivate_url = f"{frontend_url}/profile/subscription"
        feedback_url = f"{frontend_url}/feedback?reason=cancellation"
        support_url = f"{frontend_url}/support"

        # Free tier features (you can customize these)
        free_tier_features = [
            "Upload up to 50 documents per month",
            "Basic document categorization",
            "Access to your document history"
        ]

        # Send email
        asyncio.create_task(
            email_service.send_cancellation_email(
                session=session,
                user_email=user.email,
                user_name=user.full_name or user.email,
                plan_name=tier.name if tier else 'Premium',
                access_end_date=access_end_date,
                free_tier_feature_1=free_tier_features[0],
                free_tier_feature_2=free_tier_features[1],
                free_tier_feature_3=free_tier_features[2],
                reactivate_url=reactivate_url,
                feedback_url=feedback_url,
                support_url=support_url
            )
        )
        logger.info(f"Cancellation email queued for {user.email}")
    except Exception as e:
        logger.error(f"Failed to send cancellation email: {e}")


async def handle_invoice_payment_succeeded(event, session: Session):
    """Process invoice.payment_succeeded event"""
    stripe_invoice = event.data.object

    user = session.query(User).filter(
        User.stripe_customer_id == stripe_invoice.customer
    ).first()

    if not user:
        logger.warning(f"User not found for customer {stripe_invoice.customer}")
        return

    existing_invoice = session.query(Invoice).filter(
        Invoice.stripe_invoice_id == stripe_invoice.id
    ).first()

    if existing_invoice:
        existing_invoice.status = 'paid'
        existing_invoice.amount_paid_cents = stripe_invoice.amount_paid
        existing_invoice.paid_at = datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at, tz=timezone.utc) if stripe_invoice.status_transitions.paid_at else datetime.now(timezone.utc)
    else:
        subscription = session.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_invoice.subscription
        ).first() if stripe_invoice.subscription else None

        line_items = []
        if stripe_invoice.lines and stripe_invoice.lines.data:
            for line in stripe_invoice.lines.data:
                line_items.append({
                    'description': line.description or 'Subscription',
                    'amount': line.amount,
                    'quantity': line.quantity or 1,
                    'period_start': datetime.fromtimestamp(line.period.start, tz=timezone.utc).isoformat() if line.period else None,
                    'period_end': datetime.fromtimestamp(line.period.end, tz=timezone.utc).isoformat() if line.period else None
                })

        invoice = Invoice(
            user_id=user.id,
            subscription_id=subscription.id if subscription else None,
            stripe_invoice_id=stripe_invoice.id,
            invoice_number=stripe_invoice.number or f"INV-{stripe_invoice.id[-8:]}",
            status='paid',
            amount_due_cents=stripe_invoice.amount_due,
            amount_paid_cents=stripe_invoice.amount_paid,
            amount_remaining_cents=stripe_invoice.amount_remaining,
            subtotal_cents=stripe_invoice.subtotal,
            tax_cents=stripe_invoice.tax or 0,
            discount_cents=stripe_invoice.total_discount_amounts[0].amount if stripe_invoice.total_discount_amounts else 0,
            currency=stripe_invoice.currency.upper(),
            billing_reason=stripe_invoice.billing_reason,
            period_start=datetime.fromtimestamp(stripe_invoice.period_start, tz=timezone.utc) if stripe_invoice.period_start else None,
            period_end=datetime.fromtimestamp(stripe_invoice.period_end, tz=timezone.utc) if stripe_invoice.period_end else None,
            due_date=datetime.fromtimestamp(stripe_invoice.due_date, tz=timezone.utc) if stripe_invoice.due_date else None,
            paid_at=datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at, tz=timezone.utc) if stripe_invoice.status_transitions.paid_at else datetime.now(timezone.utc),
            pdf_url=stripe_invoice.invoice_pdf,
            hosted_invoice_url=stripe_invoice.hosted_invoice_url,
            line_items=line_items
        )

        session.add(invoice)

    session.commit()
    logger.info(f"Invoice {stripe_invoice.id} payment succeeded for user {user.email}")

    # Send invoice email
    try:
        # Get subscription and tier information
        subscription = session.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_invoice.subscription
        ).first() if stripe_invoice.subscription else None

        tier = None
        if subscription:
            tier = session.query(TierPlan).filter(TierPlan.id == subscription.tier_id).first()

        # Get currency
        currency = stripe_invoice.currency.upper()
        from app.database.models import Currency
        currency_obj = session.query(Currency).filter(Currency.code == currency).first()
        currency_symbol = currency_obj.symbol if currency_obj else '$'

        # Format dates
        invoice_date = datetime.fromtimestamp(stripe_invoice.created, tz=timezone.utc).strftime('%B %d, %Y')
        period_start = datetime.fromtimestamp(stripe_invoice.period_start, tz=timezone.utc).strftime('%B %d, %Y') if stripe_invoice.period_start else 'N/A'
        period_end = datetime.fromtimestamp(stripe_invoice.period_end, tz=timezone.utc).strftime('%B %d, %Y') if stripe_invoice.period_end else 'N/A'

        # Calculate amount
        amount = stripe_invoice.amount_paid / 100

        # Get frontend URL
        frontend_url = settings.app.app_frontend_url
        support_url = f"{frontend_url}/support"

        # Send email
        asyncio.create_task(
            email_service.send_invoice_email(
                session=session,
                user_email=user.email,
                user_name=user.full_name or user.email,
                plan_name=tier.name if tier else 'Subscription',
                invoice_number=stripe_invoice.number or f"INV-{stripe_invoice.id[-8:]}",
                invoice_date=invoice_date,
                period_start=period_start,
                period_end=period_end,
                amount=amount,
                currency_symbol=currency_symbol,
                invoice_pdf_url=stripe_invoice.invoice_pdf or stripe_invoice.hosted_invoice_url or '#',
                support_url=support_url
            )
        )
        logger.info(f"Invoice email queued for {user.email}")
    except Exception as e:
        logger.error(f"Failed to send invoice email: {e}")


async def handle_invoice_payment_failed(event, session: Session):
    """Process invoice.payment_failed event"""
    stripe_invoice = event.data.object

    user = session.query(User).filter(
        User.stripe_customer_id == stripe_invoice.customer
    ).first()

    if not user:
        logger.warning(f"User not found for customer {stripe_invoice.customer}")
        return

    invoice = session.query(Invoice).filter(
        Invoice.stripe_invoice_id == stripe_invoice.id
    ).first()

    if invoice:
        invoice.status = 'open'

    if user.subscription_status == 'active':
        user.subscription_status = 'past_due'
        session.commit()

    logger.warning(f"Invoice {stripe_invoice.id} payment failed for user {user.email}")


async def handle_invoice_finalized(event, session: Session):
    """Process invoice.finalized event"""
    stripe_invoice = event.data.object

    user = session.query(User).filter(
        User.stripe_customer_id == stripe_invoice.customer
    ).first()

    if not user:
        logger.warning(f"User not found for customer {stripe_invoice.customer}")
        return

    logger.info(f"Invoice {stripe_invoice.id} finalized for user {user.email}")


async def handle_payment_intent_succeeded(event, session: Session):
    """Process payment_intent.succeeded event"""
    payment_intent = event.data.object

    user = session.query(User).filter(
        User.stripe_customer_id == payment_intent.customer
    ).first()

    if not user:
        logger.warning(f"User not found for customer {payment_intent.customer}")
        return

    existing_payment = session.query(Payment).filter(
        Payment.stripe_payment_intent_id == payment_intent.id
    ).first()

    if not existing_payment:
        payment = Payment(
            user_id=user.id,
            stripe_payment_intent_id=payment_intent.id,
            stripe_invoice_id=payment_intent.invoice if hasattr(payment_intent, 'invoice') else None,
            amount_cents=payment_intent.amount,
            amount_refunded_cents=payment_intent.amount_refunded or 0,
            currency=payment_intent.currency.upper(),
            status='succeeded',
            payment_method=payment_intent.payment_method_types[0] if payment_intent.payment_method_types else None,
            receipt_url=payment_intent.charges.data[0].receipt_url if payment_intent.charges and payment_intent.charges.data else None
        )

        if payment_intent.charges and payment_intent.charges.data:
            charge = payment_intent.charges.data[0]
            if charge.payment_method_details and charge.payment_method_details.card:
                card = charge.payment_method_details.card
                payment.card_brand = card.brand
                payment.card_last4 = card.last4
                payment.card_exp_month = card.exp_month
                payment.card_exp_year = card.exp_year

        session.add(payment)
        session.commit()

    logger.info(f"Payment intent {payment_intent.id} succeeded for user {user.email}")


async def handle_payment_intent_failed(event, session: Session):
    """Process payment_intent.payment_failed event"""
    payment_intent = event.data.object

    user = session.query(User).filter(
        User.stripe_customer_id == payment_intent.customer
    ).first()

    if not user:
        logger.warning(f"User not found for customer {payment_intent.customer}")
        return

    existing_payment = session.query(Payment).filter(
        Payment.stripe_payment_intent_id == payment_intent.id
    ).first()

    if existing_payment:
        existing_payment.status = 'failed'
        existing_payment.failure_code = payment_intent.last_payment_error.code if payment_intent.last_payment_error else None
        existing_payment.failure_message = payment_intent.last_payment_error.message if payment_intent.last_payment_error else None
    else:
        payment = Payment(
            user_id=user.id,
            stripe_payment_intent_id=payment_intent.id,
            amount_cents=payment_intent.amount,
            currency=payment_intent.currency.upper(),
            status='failed',
            payment_method=payment_intent.payment_method_types[0] if payment_intent.payment_method_types else None,
            failure_code=payment_intent.last_payment_error.code if payment_intent.last_payment_error else None,
            failure_message=payment_intent.last_payment_error.message if payment_intent.last_payment_error else None
        )
        session.add(payment)

    session.commit()
    logger.warning(f"Payment intent {payment_intent.id} failed for user {user.email}")
