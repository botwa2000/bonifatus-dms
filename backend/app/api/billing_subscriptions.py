# backend/app/api/billing_subscriptions.py
"""
Billing API - Subscription Management Endpoints
Handles subscription creation, updates, and cancellations
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from datetime import datetime, timezone

from app.schemas.billing_schemas import (
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
    SubscriptionResponse
)
from app.database.connection import get_db
from app.database.models import User, TierPlan, Subscription
from app.middleware.auth_middleware import get_current_active_user
from app.services.stripe_service import stripe_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.post(
    "/subscriptions/create-checkout",
    status_code=status.HTTP_200_OK,
    summary="Create Stripe Checkout Session"
)
async def create_checkout_session(
    request: dict,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout session for a paid tier subscription

    This endpoint is used during the registration flow when a user selects a paid tier.
    It creates a Stripe Checkout session and returns the checkout URL.

    After successful payment, Stripe redirects back to the success URL and
    the webhook handler will create the subscription in the database.
    """
    try:
        tier_id = request.get('tier_id')
        billing_cycle = request.get('billing_cycle', 'monthly')
        currency_code = request.get('currency')
        referral_code = request.get('referral_code')

        if not tier_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tier_id is required"
            )

        # Get tier information
        tier = session.query(TierPlan).filter(TierPlan.id == tier_id).first()
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tier {tier_id} not found"
            )

        # Currency is required - user must select one
        if not currency_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="currency is required"
            )

        # Validate currency exists in database
        from app.database.models import Currency
        currency_obj = session.query(Currency).filter(
            Currency.code == currency_code.upper(),
            Currency.is_active == True
        ).first()

        if not currency_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Currency {currency_code} is not supported"
            )

        currency = currency_code.upper()
        logger.info(f"Using user-selected currency: {currency}")

        if tier.name.lower() == 'free':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create checkout for free tier"
            )

        # Check for existing active subscription
        existing_sub = session.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status.in_(['active', 'trialing']))
        ).scalar_one_or_none()

        if existing_sub:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has an active subscription"
            )

        # Create Stripe checkout session
        from app.core.config import settings
        import stripe

        # Get or create price ID with selected currency
        price_id = await stripe_service.get_or_create_price(session, tier, billing_cycle, currency)

        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create price"
            )

        # Prepare metadata
        metadata = {
            'user_id': str(current_user.id),
            'tier_id': str(tier.id),
            'billing_cycle': billing_cycle,
            'currency': currency
        }

        # Add referral code to metadata if provided
        if referral_code:
            metadata['referral_code'] = referral_code

        # Get or create Stripe customer BEFORE checkout to prevent race conditions
        stripe_customer_id = getattr(current_user, 'stripe_customer_id', None)
        if not stripe_customer_id:
            # Create customer now, not during checkout
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={'user_id': str(current_user.id)}
            )
            stripe_customer_id = customer.id

            # Save to database immediately using direct UPDATE to avoid session state issues
            session.execute(
                update(User)
                .where(User.id == current_user.id)
                .values(stripe_customer_id=stripe_customer_id)
            )
            session.commit()
            logger.info(f"Created Stripe customer {stripe_customer_id} for user {current_user.email}")

        # Create checkout session with existing customer
        # Note: payment_method_types omitted - Stripe automatically shows all methods enabled in dashboard
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            mode='subscription',
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            success_url=f"{settings.app.app_frontend_url}/dashboard?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.app.app_frontend_url}/dashboard?checkout=cancel",
            metadata=metadata,
            subscription_data={
                'metadata': metadata  # Copy metadata to the subscription
            }
        )

        logger.info(f"Created checkout session {checkout_session.id} for user {current_user.email}")

        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create checkout session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/subscribe",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Subscription"
)
async def create_subscription(
    subscription_request: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> SubscriptionResponse:
    """Create a new subscription for the current user"""
    try:
        existing_sub = session.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status.in_(['active', 'trialing']))
        ).scalar_one_or_none()

        if existing_sub:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has an active subscription"
            )

        tier = session.query(TierPlan).filter(TierPlan.id == subscription_request.tier_id).first()
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tier {subscription_request.tier_id} not found"
            )

        if tier.name.lower() == 'free':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create subscription for free tier"
            )

        stripe_subscription = await stripe_service.create_subscription(
            db=session,
            user=current_user,
            tier=tier,
            billing_cycle=subscription_request.billing_cycle.value,
            currency=subscription_request.currency,
            payment_method_id=subscription_request.payment_method_id,
            trial_days=subscription_request.trial_days,
            discount_code=subscription_request.discount_code
        )

        if not stripe_subscription:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create subscription"
            )

        db_subscription = Subscription(
            user_id=current_user.id,
            tier_id=tier.id,
            stripe_subscription_id=stripe_subscription.id,
            stripe_price_id=stripe_subscription['items']['data'][0].price.id,
            billing_cycle=subscription_request.billing_cycle.value,
            status=stripe_subscription.status,
            current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start, tz=timezone.utc),
            current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end, tz=timezone.utc),
            trial_start=datetime.fromtimestamp(stripe_subscription.trial_start, tz=timezone.utc) if stripe_subscription.trial_start else None,
            trial_end=datetime.fromtimestamp(stripe_subscription.trial_end, tz=timezone.utc) if stripe_subscription.trial_end else None,
            cancel_at_period_end=stripe_subscription.cancel_at_period_end
        )

        session.add(db_subscription)

        current_user.tier_id = tier.id
        current_user.subscription_status = stripe_subscription.status
        current_user.billing_cycle = subscription_request.billing_cycle.value
        current_user.subscription_started_at = datetime.now(timezone.utc)
        current_user.subscription_ends_at = datetime.fromtimestamp(stripe_subscription.current_period_end, tz=timezone.utc)

        session.commit()
        session.refresh(db_subscription)

        logger.info(f"Created subscription {db_subscription.id} for user {current_user.email}")

        return SubscriptionResponse(
            id=db_subscription.stripe_subscription_id,
            user_id=str(current_user.id),
            tier_id=tier.id,
            tier_name=tier.display_name,
            billing_cycle=db_subscription.billing_cycle,
            status=db_subscription.status,
            current_period_start=db_subscription.current_period_start,
            current_period_end=db_subscription.current_period_end,
            trial_start=db_subscription.trial_start,
            trial_end=db_subscription.trial_end,
            cancel_at_period_end=db_subscription.cancel_at_period_end,
            canceled_at=db_subscription.canceled_at,
            amount=tier.price_monthly_cents if subscription_request.billing_cycle.value == 'monthly' else tier.price_yearly_cents,
            currency=tier.currency,
            created_at=db_subscription.created_at
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Create subscription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Get Current Subscription"
)
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> SubscriptionResponse:
    """Get current user's active subscription"""
    from app.database.models import Currency

    subscription = session.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status.in_(['active', 'trialing', 'past_due']))
    ).scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription"
        )

    tier = session.query(TierPlan).filter(TierPlan.id == subscription.tier_id).first()

    # Use subscription's actual currency/amount if available, otherwise fall back to tier defaults
    actual_currency = subscription.currency or tier.currency
    actual_amount = subscription.amount_cents or (tier.price_monthly_cents if subscription.billing_cycle == 'monthly' else tier.price_yearly_cents)

    # Get currency symbol from currencies table
    currency = session.query(Currency).filter(Currency.code == actual_currency).first()
    currency_symbol = currency.symbol if currency else actual_currency

    # Check for pending billing cycle changes in Stripe
    pending_billing_cycle = None
    pending_billing_cycle_date = None

    try:
        import stripe
        stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)

        # Check if there's a pending price change (items with different price at next billing)
        if stripe_sub.get('items') and stripe_sub['items'].get('data'):
            current_item = stripe_sub['items']['data'][0]
            current_price_id = current_item.get('price', {}).get('id') if isinstance(current_item.get('price'), dict) else current_item.get('price')

            # If the price ID on Stripe differs from our DB, there's a pending change
            if current_price_id and current_price_id != subscription.stripe_price_id:
                # Fetch the new price to determine billing cycle
                try:
                    new_price = stripe.Price.retrieve(current_price_id)
                    new_interval = new_price.get('recurring', {}).get('interval')
                    if new_interval == 'month':
                        pending_billing_cycle = 'monthly'
                    elif new_interval == 'year':
                        pending_billing_cycle = 'yearly'
                    pending_billing_cycle_date = subscription.current_period_end
                    logger.info(f"Detected pending billing cycle change to {pending_billing_cycle} on {pending_billing_cycle_date}")
                except Exception as e:
                    logger.warning(f"Failed to retrieve pending price details: {e}")
    except Exception as e:
        logger.warning(f"Failed to check for pending billing cycle changes: {e}")

    return SubscriptionResponse(
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
        amount=actual_amount,
        currency=actual_currency,
        currency_symbol=currency_symbol,
        created_at=subscription.created_at,
        pending_billing_cycle=pending_billing_cycle,
        pending_billing_cycle_date=pending_billing_cycle_date
    )


@router.put(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Update Subscription"
)
async def update_subscription(
    update_request: SubscriptionUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> SubscriptionResponse:
    """Update existing subscription (upgrade, downgrade, or cancel)"""
    try:
        subscription = session.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status.in_(['active', 'trialing']))
        ).scalar_one_or_none()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription"
            )

        # Validate subscription has Stripe ID before any Stripe operations
        if not subscription.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription has no Stripe subscription ID"
            )

        if update_request.tier_id and update_request.tier_id != subscription.tier_id:
            new_tier = session.query(TierPlan).filter(TierPlan.id == update_request.tier_id).first()
            if not new_tier:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tier {update_request.tier_id} not found"
                )

            # Get current subscription currency from Stripe price
            import stripe
            try:
                current_price = stripe.Price.retrieve(subscription.stripe_price_id)
                currency = current_price.currency.upper()
            except Exception as e:
                logger.error(f"Failed to retrieve current price currency: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve subscription currency"
                )

            billing_cycle = update_request.billing_cycle.value if update_request.billing_cycle else subscription.billing_cycle
            new_price_id = await stripe_service.get_or_create_price(session, new_tier, billing_cycle, currency)

            updated_stripe_sub = await stripe_service.update_subscription(
                subscription.stripe_subscription_id,
                new_price_id=new_price_id,
                proration_behavior='create_prorations'
            )

            if not updated_stripe_sub:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update subscription in Stripe"
                )

            subscription.tier_id = new_tier.id
            subscription.stripe_price_id = new_price_id
            subscription.billing_cycle = billing_cycle
            current_user.tier_id = new_tier.id

        if update_request.cancel_at_period_end is not None:
            updated_stripe_sub = await stripe_service.update_subscription(
                subscription.stripe_subscription_id,
                cancel_at_period_end=update_request.cancel_at_period_end
            )

            if not updated_stripe_sub:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update subscription cancellation status in Stripe"
                )

            subscription.cancel_at_period_end = update_request.cancel_at_period_end
            if update_request.cancel_at_period_end:
                subscription.canceled_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(subscription)

        tier = session.query(TierPlan).filter(TierPlan.id == subscription.tier_id).first()

        return SubscriptionResponse(
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

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Update subscription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/subscription",
    status_code=status.HTTP_200_OK,
    summary="Cancel Subscription Immediately"
)
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Cancel subscription with immediate effect"""
    try:
        subscription = session.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status.in_(['active', 'trialing']))
        ).scalar_one_or_none()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription"
            )

        canceled_sub = await stripe_service.cancel_subscription(
            subscription.stripe_subscription_id,
            cancel_immediately=True
        )

        if canceled_sub:
            subscription.status = 'canceled'
            subscription.canceled_at = datetime.now(timezone.utc)
            subscription.ended_at = datetime.now(timezone.utc)

            free_tier = session.query(TierPlan).filter(TierPlan.name == 'free').first()
            if free_tier:
                current_user.tier_id = free_tier.id
            current_user.subscription_status = 'canceled'

            session.commit()
            logger.info(f"Canceled subscription for user {current_user.email}")

        return {"message": "Subscription canceled successfully"}

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Cancel subscription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/subscriptions/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel Subscription at Period End"
)
async def cancel_subscription_at_period_end(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Cancel subscription at the end of the current billing period"""
    try:
        subscription = session.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status.in_(['active', 'trialing']))
        ).scalar_one_or_none()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription"
            )

        # Update subscription in Stripe to cancel at period end
        import stripe
        updated_sub = stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )

        # Update database
        subscription.cancel_at_period_end = True
        subscription.canceled_at = datetime.now(timezone.utc)
        session.commit()

        logger.info(f"Subscription set to cancel at period end for user {current_user.email}")

        return {
            "message": "Subscription will be cancelled at the end of the current billing period",
            "cancel_at": subscription.current_period_end
        }

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Cancel subscription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/subscriptions/portal",
    status_code=status.HTTP_200_OK,
    summary="Create Stripe Customer Portal Session"
)
async def create_portal_session(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Create a Stripe Customer Portal session for managing billing and payment methods"""
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe customer found"
            )

        import stripe
        from app.core.config import settings

        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f"{settings.app.app_frontend_url}/profile?payment_updated=true"
        )

        logger.info(f"Created portal session for user {current_user.email}")

        return {"url": portal_session.url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create portal session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/update-payment-method/setup",
    summary="Create SetupIntent for Payment Method Update",
    description="Generate a Stripe SetupIntent client secret for updating payment method in-app"
)
async def setup_payment_method_update(
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a Stripe SetupIntent for updating payment method.
    Returns client_secret for use with Stripe Elements.
    """
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe customer found. Please contact support."
            )

        import stripe
        from app.core.config import settings

        # Create SetupIntent for payment method update
        setup_intent = stripe.SetupIntent.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            usage='off_session',  # Allow charging without customer present
            metadata={
                'user_id': str(current_user.id),
                'user_email': current_user.email,
                'purpose': 'payment_method_update'
            }
        )

        logger.info(f"Created SetupIntent for user {current_user.email}")

        return {
            "client_secret": setup_intent.client_secret,
            "setup_intent_id": setup_intent.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Setup payment method error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize payment method update"
        )


@router.post(
    "/update-payment-method/confirm",
    summary="Confirm Payment Method Update",
    description="Set the new payment method as default for subscription"
)
async def confirm_payment_method_update(
    payment_method_id: str,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Set the new payment method as default for the customer and their subscriptions.
    """
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe customer found"
            )

        import stripe

        # Attach payment method to customer
        payment_method = stripe.PaymentMethod.attach(
            payment_method_id,
            customer=current_user.stripe_customer_id
        )

        # Set as default payment method
        stripe.Customer.modify(
            current_user.stripe_customer_id,
            invoice_settings={
                'default_payment_method': payment_method_id
            }
        )

        # Update all active subscriptions to use this payment method
        subscriptions = stripe.Subscription.list(
            customer=current_user.stripe_customer_id,
            status='active'
        )

        for sub in subscriptions.data:
            stripe.Subscription.modify(
                sub.id,
                default_payment_method=payment_method_id
            )

        logger.info(f"Updated payment method for user {current_user.email} to {payment_method_id}")

        return {
            "success": True,
            "message": "Payment method updated successfully",
            "card_brand": payment_method.card.brand if hasattr(payment_method, 'card') else None,
            "last4": payment_method.card.last4 if hasattr(payment_method, 'card') else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Confirm payment method error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update payment method"
        )


@router.post(
    "/subscriptions/preview-upgrade",
    status_code=status.HTTP_200_OK,
    summary="Preview Tier Upgrade Details"
)
async def preview_upgrade(
    request: dict,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Preview the details of a tier upgrade without executing it.
    Returns current subscription, new tier details, and proration amounts.
    """
    try:
        tier_id = request.get('tier_id')
        new_billing_cycle = request.get('billing_cycle')

        if not tier_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tier_id is required"
            )

        # Get active subscription
        subscription = session.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status.in_(['active', 'trialing']))
        ).scalar_one_or_none()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )

        # Validate subscription has Stripe ID
        if not subscription.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription has no Stripe subscription ID"
            )

        # Get new tier information
        new_tier = session.query(TierPlan).filter(TierPlan.id == tier_id).first()
        if not new_tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tier {tier_id} not found"
            )

        # Check if already on requested tier
        # Use user's tier_id as source of truth (not subscription.tier_id which may be stale)
        if current_user.tier_id == tier_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already on this tier"
            )

        # Get current tier information (from user's tier_id as source of truth)
        current_tier = session.query(TierPlan).filter(TierPlan.id == current_user.tier_id).first()
        if not current_tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Current tier not found"
            )

        import stripe
        from app.database.models import Currency

        # Get subscription's currency from Stripe price
        if not subscription.stripe_price_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription has no Stripe price ID"
            )

        try:
            current_price = stripe.Price.retrieve(subscription.stripe_price_id)
            currency = current_price.currency.upper()
        except Exception as e:
            logger.error(f"Failed to retrieve current price {subscription.stripe_price_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve subscription price"
            )

        # Get currency symbol
        currency_obj = session.query(Currency).filter(Currency.code == currency).first()
        currency_symbol = currency_obj.symbol if currency_obj else currency

        # Determine billing cycle
        billing_cycle = new_billing_cycle if new_billing_cycle else subscription.billing_cycle

        # Get or create new price ID for the new tier
        new_price_id = await stripe_service.get_or_create_price(
            session, new_tier, billing_cycle, currency
        )

        if not new_price_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get price for new tier"
            )

        # Get new price details
        try:
            new_price_obj = stripe.Price.retrieve(new_price_id)
            new_amount = new_price_obj.unit_amount
        except Exception as e:
            logger.error(f"Failed to retrieve new price {new_price_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve new price details"
            )

        # Get proration preview from Stripe using Invoice.create_preview
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            subscription_item_id = stripe_sub['items']['data'][0]['id']

            # Preview the upcoming invoice with the new price
            # Note: Stripe SDK v14+ uses create_preview instead of upcoming
            # Prorations are calculated automatically when previewing subscription changes
            upcoming_invoice = stripe.Invoice.create_preview(
                customer=current_user.stripe_customer_id,
                subscription=subscription.stripe_subscription_id,
                subscription_details={
                    'items': [{
                        'id': subscription_item_id,
                        'price': new_price_id,
                    }]
                }
            )

            # Calculate proration details
            # In Stripe API 2025+, proration info is nested in parent.subscription_item_details
            def is_proration_line(line):
                try:
                    parent = getattr(line, 'parent', None)
                    if parent:
                        sub_details = getattr(parent, 'subscription_item_details', None)
                        if sub_details:
                            return getattr(sub_details, 'proration', False)
                    # Fallback for older API versions
                    return getattr(line, 'proration', False)
                except Exception:
                    return False

            proration_lines = [line for line in upcoming_invoice.lines.data if is_proration_line(line)]

            credit_amount = 0
            charge_amount = 0

            for line in proration_lines:
                if line.amount < 0:
                    credit_amount += abs(line.amount)
                else:
                    charge_amount += line.amount

            # Net amount due now (immediate charge)
            net_amount = upcoming_invoice.amount_due

        except stripe.error.StripeError as e:
            logger.error(f"Failed to preview invoice: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to preview upgrade: {str(e)}"
            )

        # Get current amount
        current_amount = subscription.amount_cents or (
            current_tier.price_monthly_cents if subscription.billing_cycle == 'monthly' else current_tier.price_yearly_cents
        )

        return {
            "success": True,
            "current_subscription": {
                "tier_name": current_tier.display_name,
                "tier_id": current_tier.id,
                "billing_cycle": subscription.billing_cycle,
                "amount": current_amount,
                "currency": currency,
                "currency_symbol": currency_symbol,
                "period_end": subscription.current_period_end.isoformat()
            },
            "new_subscription": {
                "tier_name": new_tier.display_name,
                "tier_id": new_tier.id,
                "billing_cycle": billing_cycle,
                "amount": new_amount,
                "currency": currency,
                "currency_symbol": currency_symbol
            },
            "proration_details": {
                "credit_for_unused_time": credit_amount,
                "prorated_charge": charge_amount,
                "net_amount_due": net_amount,
                "currency": currency,
                "currency_symbol": currency_symbol,
                "immediate_charge": True,
                "description": "Your card will be charged immediately for the prorated difference."
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview upgrade error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/subscriptions/preview-billing-cycle-change",
    status_code=status.HTTP_200_OK,
    summary="Preview Billing Cycle Change Details"
)
async def preview_billing_cycle_change(
    request: dict,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Preview the details of a billing cycle change without executing it.
    Returns current and new subscription details for user confirmation.
    """
    try:
        new_billing_cycle = request.get('billing_cycle')

        if not new_billing_cycle or new_billing_cycle not in ['monthly', 'yearly']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="billing_cycle must be 'monthly' or 'yearly'"
            )

        # Get active subscription
        subscription = session.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status.in_(['active', 'trialing']))
        ).scalar_one_or_none()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )

        # Check if already on requested billing cycle
        if subscription.billing_cycle == new_billing_cycle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Already on {new_billing_cycle} billing cycle"
            )

        # Get tier information
        tier = session.query(TierPlan).filter(TierPlan.id == subscription.tier_id).first()
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tier not found"
            )

        # Get subscription's currency and current price
        import stripe
        from app.database.models import Currency

        if not subscription.stripe_price_id:
            logger.error(f"Subscription {subscription.id} has no stripe_price_id")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription has no Stripe price ID"
            )

        try:
            current_price = stripe.Price.retrieve(subscription.stripe_price_id)
            currency = current_price.currency.upper()
        except Exception as e:
            logger.error(f"Failed to retrieve current price {subscription.stripe_price_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve subscription price: {str(e)}"
            )

        # Get currency symbol
        currency_obj = session.query(Currency).filter(Currency.code == currency).first()
        currency_symbol = currency_obj.symbol if currency_obj else currency

        # Get or create new price ID for the new billing cycle
        new_price_id = await stripe_service.get_or_create_price(
            session, tier, new_billing_cycle, currency
        )

        if not new_price_id:
            logger.error(f"get_or_create_price returned None for tier {tier.id}, cycle {new_billing_cycle}, currency {currency}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get price for new billing cycle"
            )

        # Get new price details
        try:
            new_price_obj = stripe.Price.retrieve(new_price_id)
            new_amount = new_price_obj.unit_amount  # in cents
        except Exception as e:
            logger.error(f"Failed to retrieve new price {new_price_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve new price details: {str(e)}"
            )

        # Get current amount
        current_amount = subscription.amount_cents or (
            tier.price_monthly_cents if subscription.billing_cycle == 'monthly' else tier.price_yearly_cents
        )

        # Format the response with all details for user confirmation
        return {
            "success": True,
            "current_subscription": {
                "tier_name": tier.display_name,
                "billing_cycle": subscription.billing_cycle,
                "amount": current_amount,
                "currency": currency,
                "currency_symbol": currency_symbol,
                "period_end": subscription.current_period_end.isoformat()
            },
            "new_subscription": {
                "tier_name": tier.display_name,
                "billing_cycle": new_billing_cycle,
                "amount": new_amount,
                "currency": currency,
                "currency_symbol": currency_symbol,
                "effective_date": subscription.current_period_end.isoformat()
            },
            "change_details": {
                "change_effective_date": subscription.current_period_end.strftime('%B %d, %Y'),
                "proration_info": "No immediate charge. Change takes effect at the end of your current billing period.",
                "next_billing_date": subscription.current_period_end.strftime('%B %d, %Y')
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview billing cycle change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/subscriptions/schedule-billing-cycle-change",
    status_code=status.HTTP_200_OK,
    summary="Schedule Billing Cycle Change at Period End"
)
async def schedule_billing_cycle_change(
    request: dict,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Schedule a billing cycle change (yearly ↔ monthly) to take effect at the end of the current period.

    This is the cleanest approach because:
    - User gets full value of what they paid for
    - No complex refund/proration calculations
    - Simple one-API-call implementation
    - Clear user experience
    - Automatic execution by Stripe
    """
    try:
        new_billing_cycle = request.get('billing_cycle')

        if not new_billing_cycle or new_billing_cycle not in ['monthly', 'yearly']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="billing_cycle must be 'monthly' or 'yearly'"
            )

        # Get active subscription
        subscription = session.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status.in_(['active', 'trialing']))
        ).scalar_one_or_none()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )

        # Check if already on requested billing cycle
        if subscription.billing_cycle == new_billing_cycle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Already on {new_billing_cycle} billing cycle"
            )

        # Get tier information
        tier = session.query(TierPlan).filter(TierPlan.id == subscription.tier_id).first()
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tier not found"
            )

        # Get subscription's currency
        import stripe

        if not subscription.stripe_price_id:
            logger.error(f"Subscription {subscription.id} has no stripe_price_id")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription has no Stripe price ID"
            )

        try:
            current_price = stripe.Price.retrieve(subscription.stripe_price_id)
            currency = current_price.currency.upper()
        except Exception as e:
            logger.error(f"Failed to retrieve current price {subscription.stripe_price_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve subscription price: {str(e)}"
            )

        # Get or create new price ID for the new billing cycle
        new_price_id = await stripe_service.get_or_create_price(
            session, tier, new_billing_cycle, currency
        )

        if not new_price_id:
            logger.error(f"get_or_create_price returned None for tier {tier.id}, cycle {new_billing_cycle}, currency {currency}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create price for new billing cycle"
            )

        logger.info(f"Current price ID: {subscription.stripe_price_id}, New price ID: {new_price_id}")

        # Update subscription to change billing cycle at period end
        # Simple approach: Update subscription item with new price + proration_behavior='none'
        try:
            # Get subscription items to update
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            subscription_items = stripe_sub.get('items', {}).get('data', [])

            if not subscription_items:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Subscription has no items"
                )

            # Update the subscription with new price, change takes effect at period end
            # Note: Cannot use billing_cycle_anchor='unchanged' when changing intervals
            # proration_behavior='none' ensures change happens at period end
            updated_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    'id': subscription_items[0]['id'],  # Item ID from Stripe
                    'price': str(new_price_id),
                }],
                proration_behavior='none',  # No proration - change at period end
            )

            logger.info(
                f"Updated subscription {subscription.stripe_subscription_id} "
                f"to change from {subscription.billing_cycle} to {new_billing_cycle} "
                f"at {subscription.current_period_end}"
            )

            # Get new price details for email
            try:
                new_price_obj = stripe.Price.retrieve(new_price_id)
                new_amount = new_price_obj.unit_amount / 100  # Convert cents to currency units
            except Exception as e:
                logger.warning(f"Failed to retrieve new price for email: {e}")
                new_amount = 0

            # Send notification email
            try:
                from app.services.email_service import email_service
                from app.core.config import settings

                billing_period = 'year' if new_billing_cycle == 'yearly' else 'month'

                await email_service.send_billing_cycle_change_email(
                    session=session,
                    user_email=current_user.email,
                    user_name=current_user.full_name,
                    plan_name=tier.display_name,
                    old_billing_cycle=subscription.billing_cycle,
                    new_billing_cycle=new_billing_cycle,
                    new_amount=new_amount,
                    currency=currency,
                    billing_period=billing_period,
                    change_effective_date=subscription.current_period_end.strftime('%B %d, %Y'),
                    next_billing_date=subscription.current_period_end.strftime('%B %d, %Y'),
                    dashboard_url=f"{settings.app.app_frontend_url}/profile"
                )
                logger.info(f"Billing cycle change notification email sent to {current_user.email}")
            except Exception as e:
                logger.error(f"Failed to send billing cycle change notification email: {e}")
                # Don't fail the request if email fails

            return {
                "success": True,
                "message": f"Billing cycle will change from {subscription.billing_cycle} to {new_billing_cycle} on {subscription.current_period_end.strftime('%B %d, %Y')}",
                "current_billing_cycle": subscription.billing_cycle,
                "new_billing_cycle": new_billing_cycle,
                "change_effective_date": subscription.current_period_end.isoformat()
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription schedule error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to schedule billing cycle change: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Schedule billing cycle change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
