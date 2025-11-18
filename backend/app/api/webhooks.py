# backend/app/api/webhooks.py
"""
Webhook Endpoints - Stripe Event Processing
Handles asynchronous events from Stripe (payments, subscriptions, invoices)
"""

import logging
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database.connection import get_db
from app.database.models import (
    User, Subscription, Payment, Invoice, TierPlan, DiscountCode,
    UserDiscountRedemption
)
from app.services.stripe_service import stripe_service
from app.schemas.billing_schemas import WebhookEventResponse

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

    # Extract metadata
    user_id = checkout_session.metadata.get('user_id')
    tier_id = checkout_session.metadata.get('tier_id')
    billing_cycle = checkout_session.metadata.get('billing_cycle')
    referral_code = checkout_session.metadata.get('referral_code')

    if not user_id or not tier_id:
        logger.warning(f"Missing metadata in checkout session {checkout_session.id}")
        return

    # Get user
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User {user_id} not found for checkout session {checkout_session.id}")
        return

    # Update user's Stripe customer ID if not already set
    if not user.stripe_customer_id and checkout_session.customer:
        user.stripe_customer_id = checkout_session.customer

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

    user = session.query(User).filter(
        User.stripe_customer_id == stripe_sub.customer
    ).first()

    if not user:
        logger.warning(f"User not found for customer {stripe_sub.customer}")
        return

    # Get tier from subscription metadata or price metadata
    tier_id = None
    if stripe_sub.metadata and 'tier_id' in stripe_sub.metadata:
        tier_id = stripe_sub.metadata['tier_id']
    elif stripe_sub.items and stripe_sub.items.data:
        price_metadata = stripe_sub.items.data[0].price.metadata
        if price_metadata and 'tier_id' in price_metadata:
            tier_id = price_metadata['tier_id']

    if not tier_id:
        logger.warning(f"No tier_id found in subscription {stripe_sub.id}")
        return

    tier = session.query(TierPlan).filter(TierPlan.id == tier_id).first()
    if not tier:
        logger.warning(f"Tier {tier_id} not found")
        return

    # Check if subscription already exists
    existing_sub = session.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub.id
    ).first()

    if existing_sub:
        logger.info(f"Subscription {stripe_sub.id} already exists")
        return

    # Create subscription in database
    # Get billing cycle from Stripe price interval (month -> monthly, year -> yearly)
    price_interval = None
    if stripe_sub.items.data:
        price = stripe_sub.items.data[0].price
        if price.recurring:
            price_interval = price.recurring.interval

    billing_cycle = 'yearly' if price_interval == 'year' else 'monthly'

    db_subscription = Subscription(
        user_id=user.id,
        tier_id=tier.id,
        stripe_subscription_id=stripe_sub.id,
        stripe_price_id=stripe_sub.items.data[0].price.id if stripe_sub.items.data else None,
        billing_cycle=billing_cycle,
        status=stripe_sub.status,
        current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start, tz=timezone.utc),
        current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc),
        trial_start=datetime.fromtimestamp(stripe_sub.trial_start, tz=timezone.utc) if stripe_sub.trial_start else None,
        trial_end=datetime.fromtimestamp(stripe_sub.trial_end, tz=timezone.utc) if stripe_sub.trial_end else None,
        cancel_at_period_end=stripe_sub.cancel_at_period_end
    )

    session.add(db_subscription)

    # Update user's tier
    user.tier_id = tier.id
    user.subscription_status = stripe_sub.status
    user.billing_cycle = billing_cycle
    user.subscription_started_at = datetime.now(timezone.utc)
    user.subscription_ends_at = datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc)

    session.commit()

    logger.info(f"Created subscription {db_subscription.id} for user {user.email}, tier {tier.name}")


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
    if user:
        free_tier = session.query(TierPlan).filter(TierPlan.name == 'free').first()
        if free_tier:
            user.tier_id = free_tier.id
        user.subscription_status = 'canceled'

    session.commit()
    logger.info(f"Deleted subscription {subscription.id}")


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
