"""
Billing Cancellations API
Handles subscription cancellations with refund logic and email notifications
All configuration loaded from database - no hardcoded values
"""

import logging
import json
import stripe
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel, Field

from app.database.connection import get_db
from app.database.models import (
    User, Subscription, SubscriptionCancellation, TierPlan, Payment, SystemSetting
)
from app.middleware.auth_middleware import get_current_active_user, get_current_admin_user
from app.services.stripe_service import stripe_service
from app.services.email_service import email_service
from app.core.config import settings
from app.api.billing_subscriptions import get_active_subscription, ACTIVE_SUBSCRIPTION_STATUSES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing-cancellations"])


# ============================================================
# Request/Response Models
# ============================================================

class CancellationRequest(BaseModel):
    """Request to cancel subscription"""
    cancellation_reason: Optional[str] = Field(None, description="Reason code from system_settings")
    feedback_text: Optional[str] = Field(None, max_length=1000, description="Optional detailed feedback")
    cancel_type: str = Field("at_period_end", description="immediate or at_period_end")


class CancellationResponse(BaseModel):
    """Response after cancellation"""
    success: bool
    message: str
    refund_issued: bool
    refund_amount: Optional[float] = None
    refund_currency: Optional[str] = None
    access_end_date: Optional[str] = None
    downgraded_to_free: bool


class CancellationReason(BaseModel):
    """Cancellation reason option"""
    value: str
    label: str


class CancellationStatsResponse(BaseModel):
    """Cancellation analytics for admin"""
    total_cancellations: int
    cancellations_this_month: int
    refunds_issued: int
    total_refund_amount: float
    cancellations_by_reason: Dict[str, int]
    average_subscription_age_days: float
    cancellations_by_type: Dict[str, int]
    recent_cancellations: List[Dict[str, Any]]


# ============================================================
# Helper Functions
# ============================================================

def get_setting_value(session: Session, key: str, default: Any = None) -> Any:
    """Get value from system_settings"""
    setting = session.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
    if not setting:
        return default

    try:
        if setting.data_type == 'json':
            return json.loads(setting.setting_value)
        elif setting.data_type == 'integer':
            return int(setting.setting_value)
        elif setting.data_type == 'boolean':
            return setting.setting_value.lower() in ('true', '1', 'yes')
        else:
            return setting.setting_value
    except:
        return default


def get_refund_policy_days(session: Session) -> int:
    """Get refund policy days from database"""
    return get_setting_value(session, 'refund_policy_days', 14)


def get_free_tier_features(session: Session, language: str = 'en') -> List[str]:
    """Get free tier features from database for specified language"""
    features = get_setting_value(session, 'free_tier_features', [])
    feature_key = f'feature_{language}'
    return [f.get(feature_key, f.get('feature_en', '')) for f in features]


# ============================================================
# User-Facing Endpoints
# ============================================================

@router.get("/cancellation-reasons")
async def get_cancellation_reasons(
    language: str = Query('en', description="Language code (en, de, ru, fr)"),
    session: Session = Depends(get_db)
):
    """
    Get available cancellation reasons from database
    Returns localized labels based on language parameter
    """
    reasons = get_setting_value(session, 'subscription_cancellation_reasons', [])
    label_key = f'label_{language}'

    return {
        "reasons": [
            {
                "value": reason['value'],
                "label": reason.get(label_key, reason.get('label_en', reason['value']))
            }
            for reason in reasons
        ]
    }


@router.post("/cancel-subscription", response_model=CancellationResponse)
async def cancel_subscription(
    request: CancellationRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Cancel user's active subscription with intelligent refund logic

    Refund Policy (loaded from database):
    - Within X days (default 14): Full refund if immediate cancellation
    - After X days: No refund, cancel at period end

    All configuration values loaded from system_settings table
    """
    try:
        # Get the primary active subscription
        subscription = get_active_subscription(session, current_user.id)

        logger.info(f"Cancel subscription request from user {current_user.email}")
        logger.info(f"  Found subscription: {subscription.id if subscription else 'None'}")
        if subscription:
            logger.info(f"  Stripe subscription ID: {subscription.stripe_subscription_id}")
            logger.info(f"  Status: {subscription.status}")
            logger.info(f"  Tier ID: {subscription.tier_id}")

        if not subscription:
            logger.warning(f"No active subscription found for user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )

        # Find ALL active subscriptions for this user (handles legacy duplicates)
        all_active_subs = session.query(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES)
        ).all()
        if len(all_active_subs) > 1:
            logger.warning(f"User {current_user.email} has {len(all_active_subs)} active subscriptions - will cancel all")

        # Get refund policy from database
        refund_policy_days = get_refund_policy_days(session)

        # Calculate subscription age
        subscription_age = datetime.now(timezone.utc) - subscription.created_at
        subscription_age_days = subscription_age.days

        # Determine refund eligibility based on database policy
        refund_eligible = subscription_age_days <= refund_policy_days and request.cancel_type == "immediate"

        # Get tier information
        tier = session.query(TierPlan).filter(TierPlan.id == subscription.tier_id).first()

        refund_amount_cents = None
        refund_currency = None
        stripe_refund_id = None
        refund_issued = False

        logger.info(f"  Cancel type: {request.cancel_type}, Refund eligible: {refund_eligible}")
        logger.info(f"  Subscription age: {subscription_age_days} days, Refund policy: {refund_policy_days} days")

        # Handle immediate cancellation with refund
        if request.cancel_type == "immediate" and refund_eligible:
            payment_intent_id = None

            # First, try to find the payment intent from our Payment records
            recent_payment = session.query(Payment).filter(
                Payment.user_id == current_user.id,
                Payment.status == 'succeeded'
            ).order_by(Payment.created_at.desc()).first()

            logger.info(f"  Recent payment found: {recent_payment.id if recent_payment else 'None'}")
            if recent_payment:
                logger.info(f"  Payment intent ID from DB: {recent_payment.stripe_payment_intent_id}")
                payment_intent_id = recent_payment.stripe_payment_intent_id

            # If no Payment record, try to get the charge from Stripe directly
            # Note: Stripe deprecated invoice.payment_intent (2025-03-31 API change)
            # Instead, we find the latest charge for this customer
            if not payment_intent_id and current_user.stripe_customer_id:
                try:
                    charges = stripe.Charge.list(
                        customer=current_user.stripe_customer_id,
                        limit=1
                    )
                    if charges.data and charges.data[0].payment_intent:
                        payment_intent_id = charges.data[0].payment_intent
                        logger.info(f"  Payment intent ID from Stripe charge: {payment_intent_id}")
                    elif charges.data:
                        # If no payment_intent on charge, we can refund the charge directly
                        charge_id = charges.data[0].id
                        logger.info(f"  Using charge ID directly for refund: {charge_id}")
                        try:
                            refund = stripe.Refund.create(
                                charge=charge_id,
                                reason='requested_by_customer'
                            )
                            refund_issued = True
                            refund_amount_cents = refund.amount
                            refund_currency = refund.currency.upper()
                            stripe_refund_id = refund.id
                            logger.info(f"Refund issued via charge for user {current_user.email}: {refund_amount_cents/100} {refund_currency}")
                        except Exception as e:
                            logger.error(f"Refund via charge failed for user {current_user.email}: {e}")
                except Exception as e:
                    logger.warning(f"Could not retrieve charges from Stripe: {e}")

            if payment_intent_id:
                try:
                    # Issue refund via Stripe
                    refund = stripe.Refund.create(
                        payment_intent=payment_intent_id,
                        reason='requested_by_customer'
                    )

                    refund_issued = True
                    refund_amount_cents = refund.amount
                    refund_currency = refund.currency.upper()
                    stripe_refund_id = refund.id

                    logger.info(f"Refund issued for user {current_user.email}: {refund_amount_cents/100} {refund_currency}")
                except Exception as e:
                    logger.error(f"Refund failed for user {current_user.email}: {e}")
                    # Continue with cancellation even if refund fails
            else:
                logger.warning(f"No payment intent found for user {current_user.email}, cannot issue refund")

            # Cancel subscription immediately in Stripe
            try:
                if not subscription.stripe_subscription_id:
                    logger.error(f"No Stripe subscription ID for subscription {subscription.id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Subscription has no Stripe ID - cannot cancel"
                    )

                # Cancel in Stripe
                canceled_sub = stripe.Subscription.cancel(subscription.stripe_subscription_id)
                subscription.status = 'canceled'
                subscription.canceled_at = datetime.now(timezone.utc)
                subscription.ended_at = datetime.now(timezone.utc)

                logger.info(f"Successfully canceled Stripe subscription {subscription.stripe_subscription_id}")

            except stripe.error.InvalidRequestError as e:
                logger.error(f"Stripe invalid request error for subscription {subscription.stripe_subscription_id}: {e}")
                # If subscription doesn't exist in Stripe, mark as canceled in our DB anyway
                if 'No such subscription' in str(e):
                    logger.warning(f"Subscription {subscription.stripe_subscription_id} not found in Stripe, marking as canceled locally")
                    subscription.status = 'canceled'
                    subscription.canceled_at = datetime.now(timezone.utc)
                    subscription.ended_at = datetime.now(timezone.utc)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid Stripe request: {str(e)}"
                    )
            except stripe.error.StripeError as e:
                logger.error(f"Stripe API error during cancellation: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Stripe error: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Unexpected error during Stripe cancellation: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to cancel subscription: {str(e)}"
                )

            # Downgrade to free tier immediately
            free_tier = session.query(TierPlan).filter(TierPlan.name == 'free').first()
            if free_tier:
                current_user.tier_id = free_tier.id
            current_user.subscription_status = 'canceled'

            access_end_date = datetime.now(timezone.utc).strftime('%B %d, %Y')
            downgraded_to_free = True

        else:
            # Cancel at period end (no refund, access continues)
            try:
                if not subscription.stripe_subscription_id:
                    logger.error(f"No Stripe subscription ID for subscription {subscription.id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Subscription has no Stripe ID - cannot cancel"
                    )

                # Update subscription in Stripe to cancel at period end
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                subscription.cancel_at_period_end = True
                subscription.canceled_at = datetime.now(timezone.utc)

                logger.info(f"Scheduled cancellation at period end for subscription {subscription.stripe_subscription_id}")

            except stripe.error.InvalidRequestError as e:
                logger.error(f"Stripe invalid request error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid Stripe request: {str(e)}"
                )
            except stripe.error.StripeError as e:
                logger.error(f"Stripe API error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Stripe error: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Unexpected error scheduling cancellation: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to schedule cancellation: {str(e)}"
                )

            access_end_date = subscription.current_period_end.strftime('%B %d, %Y')
            downgraded_to_free = False

        # Cancel any OTHER active subscriptions in Stripe (handles legacy duplicates)
        for other_sub in all_active_subs:
            if other_sub.id == subscription.id:
                continue  # Already handled above
            if other_sub.stripe_subscription_id:
                try:
                    stripe.Subscription.cancel(other_sub.stripe_subscription_id)
                    logger.info(f"Also cancelled duplicate subscription {other_sub.stripe_subscription_id}")
                except Exception as e:
                    logger.warning(f"Could not cancel duplicate subscription {other_sub.stripe_subscription_id}: {e}")
            other_sub.status = 'canceled'
            other_sub.canceled_at = datetime.now(timezone.utc)
            other_sub.ended_at = datetime.now(timezone.utc)

        # Create cancellation record in database
        cancellation = SubscriptionCancellation(
            subscription_id=subscription.id,
            user_id=current_user.id,
            cancellation_reason=request.cancellation_reason,
            feedback_text=request.feedback_text,
            cancel_type=request.cancel_type,
            refund_requested=refund_eligible,
            refund_issued=refund_issued,
            refund_amount_cents=refund_amount_cents,
            refund_currency=refund_currency,
            stripe_refund_id=stripe_refund_id,
            subscription_age_days=subscription_age_days,
            cancellation_metadata={
                'tier_name': tier.name if tier else None,
                'billing_cycle': subscription.billing_cycle,
                'period_start': subscription.current_period_start.isoformat(),
                'period_end': subscription.current_period_end.isoformat(),
                'refund_policy_days': refund_policy_days
            }
        )
        session.add(cancellation)
        session.commit()

        # Send cancellation email with database-driven content
        try:
            frontend_url = settings.app.app_frontend_url
            reactivate_url = f"{frontend_url}/profile"
            feedback_url = f"{frontend_url}/feedback?reason=cancellation"
            support_url = f"{frontend_url}/support"

            # Get free tier features from database (use user's UI language if available)
            user_language = getattr(current_user, 'ui_language', 'en') or 'en'
            free_tier_features = get_free_tier_features(session, user_language)

            await email_service.send_cancellation_email(
                session=session,
                user_email=current_user.email,
                user_name=current_user.full_name or current_user.email,
                plan_name=tier.display_name,
                access_end_date=access_end_date,
                free_tier_feature_1=free_tier_features[0] if len(free_tier_features) > 0 else '',
                free_tier_feature_2=free_tier_features[1] if len(free_tier_features) > 1 else '',
                free_tier_feature_3=free_tier_features[2] if len(free_tier_features) > 2 else '',
                reactivate_url=reactivate_url,
                feedback_url=feedback_url,
                support_url=support_url
            )
            logger.info(f"Cancellation email sent to {current_user.email}")
        except Exception as e:
            logger.error(f"Failed to send cancellation email: {e}")
            # Don't fail the cancellation if email fails

        # Prepare response
        refund_display_amount = None
        if refund_amount_cents:
            refund_display_amount = refund_amount_cents / 100

        message = "Subscription canceled successfully"
        if refund_issued:
            message += f". Refund of {refund_currency} {refund_display_amount:.2f} has been initiated and will appear in 5-10 business days."
        elif request.cancel_type == "at_period_end":
            message += f". Your access continues until {access_end_date}."

        return CancellationResponse(
            success=True,
            message=message,
            refund_issued=refund_issued,
            refund_amount=refund_display_amount,
            refund_currency=refund_currency,
            access_end_date=access_end_date,
            downgraded_to_free=downgraded_to_free
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancellation error for user {current_user.email}: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while canceling your subscription"
        )


@router.post("/reactivate-subscription")
async def reactivate_subscription(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Reactivate a subscription that was set to cancel at period end
    """
    try:
        # Get subscription that's set to cancel
        subscription = session.query(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status == 'active',
            Subscription.cancel_at_period_end == True
        ).first()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No cancellation scheduled to reactivate"
            )

        # Remove cancel_at_period_end flag in Stripe
        try:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )
            subscription.cancel_at_period_end = False
            subscription.canceled_at = None
            session.commit()

            logger.info(f"Subscription reactivated for user {current_user.email}")

            return {
                "success": True,
                "message": "Your subscription has been reactivated successfully!"
            }

        except Exception as e:
            logger.error(f"Stripe reactivation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reactivate subscription"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reactivation error for user {current_user.email}: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while reactivating your subscription"
        )


# ============================================================
# Admin Analytics Endpoints
# ============================================================

@router.get("/admin/cancellation-stats", response_model=CancellationStatsResponse)
async def get_cancellation_stats(
    period_days: int = Query(30, description="Period in days to analyze"),
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_db)
):
    """
    Get cancellation analytics for admin dashboard
    Shows why users are canceling, refund statistics, and trends
    """
    try:
        # Calculate date range
        start_date = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Total cancellations
        total_cancellations = session.query(func.count(SubscriptionCancellation.id)).scalar() or 0

        # Cancellations in period
        cancellations_this_period = session.query(func.count(SubscriptionCancellation.id)).filter(
            SubscriptionCancellation.canceled_at >= start_date
        ).scalar() or 0

        # Refunds issued
        refunds_issued = session.query(func.count(SubscriptionCancellation.id)).filter(
            SubscriptionCancellation.refund_issued == True
        ).scalar() or 0

        # Total refund amount
        total_refund = session.query(func.sum(SubscriptionCancellation.refund_amount_cents)).filter(
            SubscriptionCancellation.refund_issued == True
        ).scalar() or 0
        total_refund_amount = total_refund / 100  # Convert to currency units

        # Cancellations by reason
        reason_counts = session.query(
            SubscriptionCancellation.cancellation_reason,
            func.count(SubscriptionCancellation.id)
        ).group_by(SubscriptionCancellation.cancellation_reason).all()

        cancellations_by_reason = {reason or 'not_specified': count for reason, count in reason_counts}

        # Average subscription age at cancellation
        avg_age = session.query(func.avg(SubscriptionCancellation.subscription_age_days)).scalar() or 0

        # Cancellations by type
        type_counts = session.query(
            SubscriptionCancellation.cancel_type,
            func.count(SubscriptionCancellation.id)
        ).group_by(SubscriptionCancellation.cancel_type).all()

        cancellations_by_type = {cancel_type: count for cancel_type, count in type_counts}

        # Recent cancellations with details
        recent = session.query(SubscriptionCancellation).order_by(
            desc(SubscriptionCancellation.canceled_at)
        ).limit(10).all()

        recent_cancellations = []
        for c in recent:
            user = session.query(User).filter(User.id == c.user_id).first()
            recent_cancellations.append({
                'user_email': user.email if user else 'Unknown',
                'reason': c.cancellation_reason,
                'feedback': c.feedback_text,
                'cancel_type': c.cancel_type,
                'refund_issued': c.refund_issued,
                'refund_amount': c.refund_amount_cents / 100 if c.refund_amount_cents else None,
                'subscription_age_days': c.subscription_age_days,
                'canceled_at': c.canceled_at.isoformat()
            })

        return CancellationStatsResponse(
            total_cancellations=total_cancellations,
            cancellations_this_month=cancellations_this_period,
            refunds_issued=refunds_issued,
            total_refund_amount=total_refund_amount,
            cancellations_by_reason=cancellations_by_reason,
            average_subscription_age_days=float(avg_age),
            cancellations_by_type=cancellations_by_type,
            recent_cancellations=recent_cancellations
        )

    except Exception as e:
        logger.error(f"Error fetching cancellation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch cancellation statistics"
        )


@router.get("/admin/cancellation-feedback")
async def get_cancellation_feedback(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    reason_filter: Optional[str] = Query(None, description="Filter by reason"),
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_db)
):
    """
    Get detailed cancellation feedback for analysis
    Allows admin to read user feedback and understand cancellation patterns
    """
    try:
        query = session.query(SubscriptionCancellation).filter(
            SubscriptionCancellation.feedback_text.isnot(None)
        )

        if reason_filter:
            query = query.filter(SubscriptionCancellation.cancellation_reason == reason_filter)

        total = query.count()

        cancellations = query.order_by(
            desc(SubscriptionCancellation.canceled_at)
        ).offset((page - 1) * page_size).limit(page_size).all()

        feedback_items = []
        for c in cancellations:
            user = session.query(User).filter(User.id == c.user_id).first()
            tier = session.query(Subscription, TierPlan).join(
                TierPlan, Subscription.tier_id == TierPlan.id
            ).filter(Subscription.id == c.subscription_id).first()

            feedback_items.append({
                'id': str(c.id),
                'user_email': user.email if user else 'Unknown',
                'reason': c.cancellation_reason,
                'feedback': c.feedback_text,
                'cancel_type': c.cancel_type,
                'tier_name': tier[1].name if tier else 'Unknown',
                'subscription_age_days': c.subscription_age_days,
                'refund_issued': c.refund_issued,
                'canceled_at': c.canceled_at.isoformat()
            })

        return {
            'feedback': feedback_items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

    except Exception as e:
        logger.error(f"Error fetching cancellation feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch cancellation feedback"
        )
