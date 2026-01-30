# backend/app/api/webhooks.py
"""
Webhook Endpoints - Stripe Event Processing
Handles asynchronous events from Stripe (payments, subscriptions, invoices)
"""

import logging
import asyncio
import stripe
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

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
    """
    Process checkout.session.completed event.

    This handles NEW subscriptions only (when a free user subscribes).
    Upgrades are handled via Subscription.modify() and the subscription.updated webhook.
    """
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

    # Update user's tier (subscription record will be created by subscription.created webhook)
    user.tier_id = int(tier_id)
    logger.info(f"[WEBHOOK] Updated user {user.email} tier_id to {tier_id}")

    # Process referral code if provided
    if referral_code:
        # For now, just log the referral - full implementation depends on your referral system
        logger.info(f"Referral code '{referral_code}' used by user {user.email}")
        # TODO: Create referral record when referral system is fully implemented

    # Subscription record will be created via the subscription.created webhook
    logger.info(f"[WEBHOOK] Checkout session completed for user {user.email}, tier {tier.name}")

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
        # tier_id should always be in subscription metadata (set by create-checkout or execute-upgrade)
        # Log full details for debugging if not found
        logger.error(f"[WEBHOOK] No tier_id found in subscription {stripe_sub.id}")
        logger.error(f"[WEBHOOK] Subscription metadata: {stripe_sub.metadata}")
        logger.error(f"[WEBHOOK] User: {user.email}, current tier_id: {user.tier_id}")

        # Use user's tier_id which was set by checkout.session.completed
        # This is not a guess - it was explicitly set when the checkout completed
        if user.tier_id and user.tier_id > 0:
            tier_id = str(user.tier_id)
            logger.info(f"[WEBHOOK] Using user's tier_id (set by checkout.session.completed): {tier_id}")
        else:
            logger.error(f"[WEBHOOK] Cannot determine tier for subscription {stripe_sub.id} - skipping creation")
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
    # Get billing cycle and currency from subscription metadata first (more reliable)
    # Fall back to Stripe price data if metadata is not available
    billing_cycle = None
    currency = None
    amount_cents = None

    # Check metadata first
    if hasattr(stripe_sub, 'metadata') and stripe_sub.metadata:
        billing_cycle = stripe_sub.metadata.get('billing_cycle')
        currency = stripe_sub.metadata.get('currency')
        if currency:
            currency = currency.upper()
        logger.info(f"[WEBHOOK] Got from metadata: billing_cycle={billing_cycle}, currency={currency}")

    # Fetch full subscription with items expanded
    # Webhook events don't include items.data by default
    items_data = None
    stripe_price_id = None
    try:
        logger.info(f"[WEBHOOK] Fetching full subscription {stripe_sub.id} from Stripe API")
        import stripe as stripe_lib
        full_subscription = stripe_lib.Subscription.retrieve(
            stripe_sub.id,
            expand=['items.data.price']
        )

        # Stripe v7+ returns dict-like objects, use dict access
        if 'items' in full_subscription and full_subscription['items']:
            items = full_subscription['items']
            if 'data' in items and items['data']:
                items_data = items['data']
                logger.info(f"[WEBHOOK] Successfully got items_data with {len(items_data)} items")
            else:
                logger.warning(f"[WEBHOOK] No 'data' in items response")
        else:
            logger.warning(f"[WEBHOOK] No 'items' in subscription response")
    except Exception as e:
        logger.error(f"[WEBHOOK] Failed to retrieve full subscription: {e}")
        items_data = None

    if items_data and len(items_data) > 0:
        # Extract stripe_price_id from first item
        try:
            first_item = items_data[0]
            if 'price' in first_item and first_item['price']:
                price = first_item['price']
                stripe_price_id = price.get('id') or price.id
                logger.info(f"[WEBHOOK] Extracted stripe_price_id: {stripe_price_id}")
            else:
                logger.error(f"[WEBHOOK] No 'price' in first subscription item")
        except (AttributeError, IndexError, KeyError) as e:
            logger.error(f"[WEBHOOK] Failed to extract stripe_price_id: {e}")

        # Get billing_cycle from price if not in metadata
        try:
            if not billing_cycle:
                recurring = price.get('recurring') if isinstance(price, dict) else getattr(price, 'recurring', None)
                if recurring:
                    price_interval = recurring.get('interval') if isinstance(recurring, dict) else getattr(recurring, 'interval', None)
                    if price_interval:
                        billing_cycle = 'yearly' if price_interval == 'year' else 'monthly'
                        logger.info(f"[WEBHOOK] Extracted billing_cycle from price: {billing_cycle}")
        except Exception as e:
            logger.warning(f"[WEBHOOK] Could not extract billing_cycle from price: {e}")

        # Store the actual currency and amount charged
        try:
            if not currency:
                price_currency = price.get('currency') if isinstance(price, dict) else getattr(price, 'currency', None)
                if price_currency:
                    currency = price_currency.upper()
                    logger.info(f"[WEBHOOK] Extracted currency from price: {currency}")
        except Exception as e:
            logger.warning(f"[WEBHOOK] Could not extract currency from price: {e}")

        try:
            price_amount = price.get('unit_amount') if isinstance(price, dict) else getattr(price, 'unit_amount', None)
            if price_amount:
                amount_cents = price_amount
                logger.info(f"[WEBHOOK] Extracted amount_cents from price: {amount_cents}")
        except Exception as e:
            logger.warning(f"[WEBHOOK] Could not extract amount from price: {e}")

    # Default to monthly if still not set
    if not billing_cycle:
        billing_cycle = 'monthly'
        logger.warning(f"[WEBHOOK] billing_cycle not found in metadata or items, defaulting to monthly")

    # stripe_price_id is required for subscription management features (billing cycle changes, upgrades)
    # Allow subscription creation even if missing, but log loudly for investigation
    if not stripe_price_id:
        logger.error(f"[WEBHOOK] WARNING: No stripe_price_id found for subscription {stripe_sub.id}")
        logger.error(f"[WEBHOOK] Billing cycle switch and some features will NOT work for this subscription")
        logger.error(f"[WEBHOOK] Subscription will be created but should be investigated in Stripe dashboard")

    # Calculate period dates with proper fallback
    if hasattr(stripe_sub, 'current_period_start') and stripe_sub.current_period_start:
        period_start = datetime.fromtimestamp(stripe_sub.current_period_start, tz=timezone.utc)
    else:
        period_start = datetime.now(timezone.utc)
        logger.warning(f"[WEBHOOK] No current_period_start in Stripe subscription, using now()")

    if hasattr(stripe_sub, 'current_period_end') and stripe_sub.current_period_end:
        period_end = datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc)
    else:
        # Calculate period_end based on billing_cycle
        if billing_cycle == 'yearly':
            period_end = period_start + relativedelta(years=1)
        else:  # monthly
            period_end = period_start + relativedelta(months=1)
        logger.warning(f"[WEBHOOK] No current_period_end in Stripe subscription, calculated from billing_cycle: {period_end}")

    db_subscription = Subscription(
        user_id=user.id,
        tier_id=tier.id,
        stripe_subscription_id=stripe_sub.id,
        stripe_price_id=stripe_price_id,
        billing_cycle=billing_cycle,
        status=stripe_sub.status if hasattr(stripe_sub, 'status') else 'active',
        current_period_start=period_start,
        current_period_end=period_end,
        trial_start=datetime.fromtimestamp(stripe_sub.trial_start, tz=timezone.utc) if hasattr(stripe_sub, 'trial_start') and stripe_sub.trial_start else None,
        trial_end=datetime.fromtimestamp(stripe_sub.trial_end, tz=timezone.utc) if hasattr(stripe_sub, 'trial_end') and stripe_sub.trial_end else None,
        cancel_at_period_end=stripe_sub.cancel_at_period_end if hasattr(stripe_sub, 'cancel_at_period_end') else False,
        currency=currency,
        amount_cents=amount_cents
    )

    session.add(db_subscription)

    # Update user's tier
    user.tier_id = tier.id
    user.subscription_status = stripe_sub.status if hasattr(stripe_sub, 'status') else 'active'
    user.billing_cycle = billing_cycle
    user.subscription_started_at = datetime.now(timezone.utc)
    user.subscription_ends_at = period_end

    session.commit()

    logger.info(f"[WEBHOOK] ✓ Created subscription {db_subscription.id} for user {user.email}, tier {tier.name}, currency: {currency}, amount: {amount_cents}")

    # Auto-enable email processing for Pro/Premium users
    if tier.email_to_process_enabled:
        try:
            from app.services.email_processing_service import EmailProcessingService
            email_processing_service = EmailProcessingService(session)
            success, processing_email, error = email_processing_service.auto_enable_email_processing_for_pro_user(str(user.id))

            if success:
                session.commit()  # Commit email processing changes
                logger.info(f"[WEBHOOK] ✓ Auto-enabled email processing for Pro user {user.email}: {processing_email}")
            else:
                logger.error(f"[WEBHOOK] Failed to auto-enable email processing for user {user.email}: {error}")
        except Exception as e:
            logger.error(f"[WEBHOOK] Exception while auto-enabling email processing: {e}")

    # Send subscription confirmation email
    try:
        # Use currency and amount from subscription (already extracted above)
        email_currency = db_subscription.currency or 'USD'
        email_amount = (db_subscription.amount_cents / 100) if db_subscription.amount_cents else 0

        # Get currency symbol
        from app.database.models import Currency
        currency_obj = session.query(Currency).filter(Currency.code == email_currency).first()
        currency_symbol = currency_obj.symbol if currency_obj else '$'

        # Format billing period (capitalize first letter)
        billing_period = billing_cycle.capitalize()

        # Log dates for debugging
        logger.info(f"[WEBHOOK] Email dates: period_start={period_start}, period_end={period_end}")
        logger.info(f"[WEBHOOK] Subscription dates in DB: start={db_subscription.current_period_start}, end={db_subscription.current_period_end}")

        # Format subscription dates
        start_date = db_subscription.current_period_start.strftime('%B %d, %Y')
        next_billing_date = db_subscription.current_period_end.strftime('%B %d, %Y')

        logger.info(f"[WEBHOOK] Email will use: start_date={start_date}, next_billing_date={next_billing_date}")

        # Get dashboard URL from settings
        frontend_url = settings.app.app_frontend_url
        dashboard_url = f"{frontend_url}/dashboard"
        support_url = f"{frontend_url}/support"

        # Get tier features from database (match actual tier capabilities)
        tier_feature_1 = f"{tier.max_pages_per_month if tier.max_pages_per_month else 'Unlimited'} pages per month"
        tier_feature_2 = f"{tier.max_monthly_upload_bytes // (1024**3) if tier.max_monthly_upload_bytes else 'Unlimited'} GB monthly upload volume"
        tier_feature_3 = "Advanced search and categorization"

        # Add additional features based on tier capabilities
        if tier.multi_user_enabled:
            tier_feature_3 = f"Multi-user collaboration (up to {tier.max_team_members} team members)" if tier.max_team_members else "Multi-user collaboration"
        if tier.email_to_process_enabled:
            tier_feature_3 = "Email-to-document processing (send docs via email)"

        # Send email
        asyncio.create_task(
            email_service.send_subscription_confirmation(
                session=session,
                user_email=user.email,
                user_name=user.full_name or user.email,
                plan_name=tier.display_name,
                billing_cycle=billing_cycle.capitalize(),
                amount=email_amount,
                currency_symbol=currency_symbol,
                billing_period=billing_period,
                next_billing_date=next_billing_date,
                tier_feature_1=tier_feature_1,
                tier_feature_2=tier_feature_2,
                tier_feature_3=tier_feature_3,
                dashboard_url=dashboard_url,
                support_url=support_url,
                start_date=start_date
            )
        )
        logger.info(f"Subscription confirmation email queued for {user.email}")
    except Exception as e:
        logger.error(f"Failed to send subscription confirmation email: {e}")


async def handle_subscription_updated(event, session: Session):
    """Process subscription.updated event"""
    import stripe as stripe_lib

    stripe_sub = event.data.object

    subscription = session.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub.id
    ).first()

    if not subscription:
        logger.warning(f"Subscription {stripe_sub.id} not found in database")
        return

    old_tier_id = subscription.tier_id
    old_price_id = subscription.stripe_price_id

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

    # Check if the price has changed (upgrade/downgrade)
    tier_changed = False
    new_tier = None

    try:
        current_price_id = stripe_sub['items']['data'][0]['price']['id']
        current_price = stripe_sub['items']['data'][0]['price']

        # Update price ID and amount
        if subscription.stripe_price_id != current_price_id:
            logger.info(f"[WEBHOOK] Subscription price changed from {subscription.stripe_price_id} to {current_price_id}")
            subscription.stripe_price_id = current_price_id

            # Update amount from the new price
            if isinstance(current_price, dict) and 'unit_amount' in current_price:
                subscription.amount_cents = current_price['unit_amount']
                logger.info(f"[WEBHOOK] Updated amount_cents to {subscription.amount_cents}")

            # Update currency if available
            if isinstance(current_price, dict) and 'currency' in current_price:
                subscription.currency = current_price['currency'].upper()
                logger.info(f"[WEBHOOK] Updated currency to {subscription.currency}")

            # First, try to get tier_id from subscription metadata (set by execute-upgrade)
            if stripe_sub.metadata and 'tier_id' in stripe_sub.metadata:
                new_tier_id = int(stripe_sub.metadata['tier_id'])
                new_tier = session.query(TierPlan).filter(TierPlan.id == new_tier_id).first()
                if new_tier:
                    logger.info(f"[WEBHOOK] Found tier {new_tier.name} from subscription metadata")

            # Fallback: search for tier by price ID in stripe_price_ids
            if not new_tier:
                all_tiers = session.query(TierPlan).all()
                for tier in all_tiers:
                    if tier.stripe_price_ids:
                        for billing_cycle, currencies in tier.stripe_price_ids.items():
                            if isinstance(currencies, dict):
                                for currency, price_id in currencies.items():
                                    if price_id == current_price_id:
                                        new_tier = tier
                                        logger.info(f"[WEBHOOK] Found tier {tier.name} from stripe_price_ids")
                                        break
                            if new_tier:
                                break
                    if new_tier:
                        break

            # Update tier if found and different
            if new_tier and subscription.tier_id != new_tier.id:
                logger.info(f"[WEBHOOK] Updating tier from {subscription.tier_id} to {new_tier.id} ({new_tier.name})")
                subscription.tier_id = new_tier.id
                if user:
                    user.tier_id = new_tier.id
                tier_changed = True
    except Exception as e:
        logger.error(f"[WEBHOOK] Error checking for tier change: {e}")

    session.commit()
    logger.info(f"[WEBHOOK] Updated subscription {subscription.id} to status {stripe_sub.status}")

    # Send upgrade confirmation email if tier changed to a higher tier
    if tier_changed and new_tier and new_tier.id > old_tier_id:
        try:
            # Get billing cycle from price interval
            billing_cycle = 'yearly'
            try:
                price_obj = stripe_lib.Price.retrieve(subscription.stripe_price_id)
                if price_obj.recurring and price_obj.recurring.interval == 'month':
                    billing_cycle = 'monthly'
            except Exception:
                pass

            # Get amount paid (proration amount from latest invoice)
            amount_paid = 0
            try:
                stripe_sub_obj = stripe_lib.Subscription.retrieve(stripe_sub.id)
                if stripe_sub_obj.latest_invoice:
                    invoice = stripe_lib.Invoice.retrieve(stripe_sub_obj.latest_invoice)
                    amount_paid = invoice.amount_paid / 100 if invoice.amount_paid else 0
            except Exception:
                amount_paid = subscription.amount_cents / 100 if subscription.amount_cents else 0

            logger.info(f"[WEBHOOK] Sending upgrade confirmation email to {user.email}")
            asyncio.create_task(
                email_service.send_subscription_upgraded_email(
                    user.email,
                    user.full_name or user.email,
                    new_tier.display_name,
                    billing_cycle,
                    amount_paid,
                    subscription.currency or 'EUR'
                )
            )
        except Exception as email_err:
            logger.error(f"[WEBHOOK] Failed to send upgrade email: {email_err}")


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

    # Check if this is an upgrade cancellation (user has another active subscription)
    # or if the subscription was marked as upgrade cancellation
    is_upgrade_cancellation = False

    # Check if user has another active subscription (they upgraded)
    if user:
        other_active_sub = session.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status.in_(['active', 'trialing']),
            Subscription.id != subscription.id
        ).first()
        if other_active_sub:
            is_upgrade_cancellation = True
            logger.info(f"[WEBHOOK] User {user.email} has another active subscription - this is an upgrade cancellation")

    if user and not is_upgrade_cancellation:
        # Only reset to free tier if this is NOT an upgrade
        free_tier = session.query(TierPlan).filter(TierPlan.name == 'free').first()
        if free_tier:
            user.tier_id = free_tier.id
        user.subscription_status = 'canceled'

    session.commit()
    logger.info(f"Deleted subscription {subscription.id}")

    # Only send cancellation email if this is NOT an upgrade cancellation
    if is_upgrade_cancellation:
        logger.info(f"[WEBHOOK] Skipping cancellation email - this is an upgrade")
        return

    # Check if cancellation was initiated by our API (SubscriptionCancellation record exists)
    # If so, the API endpoint already sent the email - skip to avoid duplicate
    from app.database.models import SubscriptionCancellation
    existing_cancellation = session.query(SubscriptionCancellation).filter(
        SubscriptionCancellation.subscription_id == subscription.id
    ).first()

    if existing_cancellation:
        logger.info(f"[WEBHOOK] Cancellation record already exists for subscription {subscription.id} - skipping email (already sent by API)")
        return

    # Send cancellation confirmation email only for Stripe-dashboard-initiated cancellations
    logger.info(f"[WEBHOOK] No cancellation record found - sending email for Stripe-initiated cancellation")
    try:
        access_end_date = subscription.current_period_end.strftime('%B %d, %Y') if subscription.current_period_end else 'today'

        frontend_url = settings.app.app_frontend_url
        reactivate_url = f"{frontend_url}/profile"
        feedback_url = f"{frontend_url}/feedback?reason=cancellation"
        support_url = f"{frontend_url}/support"

        asyncio.create_task(
            email_service.send_cancellation_email(
                session=session,
                user_email=user.email,
                user_name=user.full_name or user.email,
                plan_name=tier.display_name if tier else 'Premium',
                access_end_date=access_end_date,
                free_tier_feature_1='',
                free_tier_feature_2='',
                free_tier_feature_3='',
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

    # Extract subscription ID early (handle both string and object forms)
    # Stripe API changes may return objects instead of string IDs
    sub_id = None
    try:
        sub_val = getattr(stripe_invoice, 'subscription', None)
        if isinstance(sub_val, str):
            sub_id = sub_val
        elif hasattr(sub_val, 'id'):
            sub_id = sub_val.id
    except Exception:
        pass

    # Fallback: get subscription ID from line items
    if not sub_id:
        try:
            if stripe_invoice.lines and stripe_invoice.lines.data:
                for line in stripe_invoice.lines.data:
                    if hasattr(line, 'subscription') and line.subscription:
                        sub_id = line.subscription if isinstance(line.subscription, str) else line.subscription.id
                        break
        except Exception:
            pass

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
        ).first() if hasattr(stripe_invoice, 'subscription') and stripe_invoice.subscription else None

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
            tax_cents=stripe_invoice.tax if hasattr(stripe_invoice, 'tax') and stripe_invoice.tax else 0,
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

    # Also create a Payment record for refund tracking
    # Note: Stripe deprecated invoice.payment_intent (2025-03-31 API change)
    # Use Charge.list to find the charge associated with this invoice
    try:
        charges = stripe.Charge.list(
            customer=stripe_invoice.customer,
            limit=5
        )
        for charge in charges.data:
            if charge.invoice == stripe_invoice.id and charge.paid:
                existing_payment = session.query(Payment).filter(
                    Payment.stripe_payment_intent_id == charge.payment_intent
                ).first() if charge.payment_intent else None

                if not existing_payment:
                    payment = Payment(
                        user_id=user.id,
                        stripe_payment_intent_id=charge.payment_intent,
                        stripe_invoice_id=stripe_invoice.id,
                        amount_cents=charge.amount,
                        amount_refunded_cents=charge.amount_refunded or 0,
                        currency=charge.currency.upper(),
                        status='succeeded',
                        payment_method='card',
                        card_brand=charge.payment_method_details.card.brand if charge.payment_method_details and charge.payment_method_details.card else None,
                        card_last4=charge.payment_method_details.card.last4 if charge.payment_method_details and charge.payment_method_details.card else None,
                        receipt_url=charge.receipt_url
                    )
                    session.add(payment)
                    logger.info(f"Created Payment record for invoice {stripe_invoice.id} with payment_intent {charge.payment_intent}")
                break
    except Exception as e:
        logger.warning(f"Could not create Payment record from charge: {e}")

    session.commit()
    logger.info(f"Invoice {stripe_invoice.id} payment succeeded for user {user.email}")

    # Check if this is an upgrade invoice - if so, update the tier
    if stripe_invoice.billing_reason in ('subscription_update', 'subscription_create') and sub_id:
        try:
            logger.info(f"Checking for upgrade on subscription {sub_id}")

            # Get the subscription from Stripe to check the current price
            stripe_sub = stripe.Subscription.retrieve(sub_id)
            current_price_id = stripe_sub['items']['data'][0]['price']['id']

            # Find the tier for this price by checking all tiers' stripe_price_ids
            subscription = session.query(Subscription).filter(
                Subscription.stripe_subscription_id == sub_id
            ).first()

            if subscription and subscription.stripe_price_id != current_price_id:
                # Price changed - this is an upgrade
                logger.info(f"Detected price change from {subscription.stripe_price_id} to {current_price_id}")

                # Find the tier that matches this new price
                # We need to search all tiers for this price ID
                all_tiers = session.query(TierPlan).all()
                new_tier = None

                for tier in all_tiers:
                    if tier.stripe_price_ids:
                        for billing_cycle, currencies in tier.stripe_price_ids.items():
                            if isinstance(currencies, dict):
                                for currency, price_id in currencies.items():
                                    if price_id == current_price_id:
                                        new_tier = tier
                                        break
                            if new_tier:
                                break
                    if new_tier:
                        break

                if new_tier:
                    logger.info(f"Updating user {user.email} tier from {subscription.tier_id} to {new_tier.id} ({new_tier.name})")
                    subscription.tier_id = new_tier.id
                    subscription.stripe_price_id = current_price_id
                    user.tier_id = new_tier.id
                    session.commit()

                    # Send upgrade confirmation email
                    try:
                        billing_cycle = 'yearly' if 'year' in str(stripe_sub['items']['data'][0]['price'].get('recurring', {}).get('interval', '')) else 'monthly'
                        asyncio.create_task(
                            email_service.send_subscription_upgraded_email(
                                user.email,
                                user.full_name or user.email,
                                new_tier.display_name,
                                billing_cycle,
                                stripe_invoice.amount_paid / 100,
                                stripe_invoice.currency.upper()
                            )
                        )
                    except Exception as email_err:
                        logger.error(f"Failed to send upgrade email: {email_err}")
                else:
                    logger.warning(f"Could not find tier for price_id {current_price_id}")
        except Exception as upgrade_err:
            logger.error(f"Error checking for upgrade: {upgrade_err}")

    # Send invoice email
    try:
        # Get subscription and tier information
        subscription = session.query(Subscription).filter(
            Subscription.stripe_subscription_id == sub_id
        ).first() if sub_id else None

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

        # Get billing period from the best source:
        # 1. Invoice line items (most accurate for subscription billing period)
        # 2. Subscription current period dates
        # 3. Fall back to invoice period dates (can be same for checkout invoices)
        period_start_dt = None
        period_end_dt = None

        # Try to get from invoice line items first (most accurate for subscriptions)
        if stripe_invoice.lines and stripe_invoice.lines.data:
            for line in stripe_invoice.lines.data:
                if line.period:
                    period_start_dt = datetime.fromtimestamp(line.period.start, tz=timezone.utc)
                    period_end_dt = datetime.fromtimestamp(line.period.end, tz=timezone.utc)
                    break

        # If line items don't have it, try subscription
        if not period_end_dt and subscription:
            if subscription.current_period_start:
                period_start_dt = subscription.current_period_start
            if subscription.current_period_end:
                period_end_dt = subscription.current_period_end

        # Fall back to invoice period dates as last resort
        if not period_start_dt and stripe_invoice.period_start:
            period_start_dt = datetime.fromtimestamp(stripe_invoice.period_start, tz=timezone.utc)
        if not period_end_dt and stripe_invoice.period_end:
            period_end_dt = datetime.fromtimestamp(stripe_invoice.period_end, tz=timezone.utc)

        period_start = period_start_dt.strftime('%B %d, %Y') if period_start_dt else 'N/A'
        period_end = period_end_dt.strftime('%B %d, %Y') if period_end_dt else 'N/A'

        logger.info(f"[WEBHOOK] Invoice email dates: period_start={period_start}, period_end={period_end}")

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
