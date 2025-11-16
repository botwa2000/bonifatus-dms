# backend/app/api/billing_subscriptions.py
"""
Billing API - Subscription Management Endpoints
Handles subscription creation, updates, and cancellations
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
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
router = APIRouter()


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

        # Get or create price ID
        price_id = await stripe_service.get_or_create_price(session, tier, billing_cycle)

        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create price"
            )

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id if current_user.stripe_customer_id else None,
            customer_email=current_user.email if not current_user.stripe_customer_id else None,
            mode='subscription',
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            success_url=f"{settings.app.app_frontend_url}/dashboard?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.app.app_frontend_url}/dashboard?checkout=cancel",
            metadata={
                'user_id': str(current_user.id),
                'tier_id': str(tier.id),
                'billing_cycle': billing_cycle
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

        if update_request.tier_id and update_request.tier_id != subscription.tier_id:
            new_tier = session.query(TierPlan).filter(TierPlan.id == update_request.tier_id).first()
            if not new_tier:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tier {update_request.tier_id} not found"
                )

            billing_cycle = update_request.billing_cycle.value if update_request.billing_cycle else subscription.billing_cycle
            new_price_id = await stripe_service.get_or_create_price(session, new_tier, billing_cycle)

            updated_stripe_sub = await stripe_service.update_subscription(
                subscription.stripe_subscription_id,
                new_price_id=new_price_id,
                proration_behavior='create_prorations'
            )

            if updated_stripe_sub:
                subscription.tier_id = new_tier.id
                subscription.stripe_price_id = new_price_id
                subscription.billing_cycle = billing_cycle
                current_user.tier_id = new_tier.id

        if update_request.cancel_at_period_end is not None:
            updated_stripe_sub = await stripe_service.update_subscription(
                subscription.stripe_subscription_id,
                cancel_at_period_end=update_request.cancel_at_period_end
            )

            if updated_stripe_sub:
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
