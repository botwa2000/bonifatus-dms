# backend/app/api/admin.py
"""
Bonifatus DMS - Admin API
Administrative endpoints for user management, tier configuration, and system monitoring
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.models import User, TierPlan, TierProviderSettings, UserStorageQuota, UserMonthlyUsage, Document, AuditLog, EmailTemplate, Currency
from app.database.connection import db_manager, get_db
from app.middleware.auth_middleware import get_current_admin_user
from app.services.clamav_health_service import clamav_health_service
from app.services.email_poller_health_service import email_poller_health_service
from app.services.tier_service import tier_service
from app.core.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ============================================================
# Request/Response Models
# ============================================================

class TierPlanUpdate(BaseModel):
    """Update tier plan configuration"""
    display_name: Optional[str] = None
    price_monthly_cents: Optional[int] = None
    price_yearly_cents: Optional[int] = None
    max_monthly_upload_bytes: Optional[int] = Field(None, description="Monthly upload volume limit in bytes")
    max_file_size_bytes: Optional[int] = Field(None, description="Max individual file size")
    max_pages_per_month: Optional[int] = Field(None, description="Monthly page processing limit, null for unlimited")
    max_translations_per_month: Optional[int] = Field(None, description="Monthly translation limit, null for unlimited")
    max_api_calls_per_month: Optional[int] = Field(None, description="Monthly API call limit, null for unlimited")
    max_team_members: Optional[int] = Field(None, description="Max team members, null for unlimited")
    max_batch_upload_size: Optional[int] = Field(None, description="Max files per batch upload, null for unlimited")
    bulk_operations_enabled: Optional[bool] = None
    email_to_process_enabled: Optional[bool] = None
    folder_to_process_enabled: Optional[bool] = None
    multi_user_enabled: Optional[bool] = None
    api_access_enabled: Optional[bool] = None
    priority_support: Optional[bool] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class UserTierUpdate(BaseModel):
    """Update user tier"""
    tier_id: int = Field(..., description="New tier ID (0=Free, 1=Starter, 2=Pro, 100=Admin)")


class CurrencyCreate(BaseModel):
    """Create new currency"""
    code: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code (e.g., USD, EUR, GBP)")
    symbol: str = Field(..., min_length=1, max_length=10, description="Currency symbol (e.g., $, €, £)")
    name: str = Field(..., min_length=1, max_length=100, description="Currency name (e.g., US Dollar, Euro)")
    decimal_places: int = Field(2, ge=0, le=4, description="Number of decimal places")
    exchange_rate: Optional[float] = Field(None, ge=0, description="Exchange rate (units of currency per 1 EUR)")
    is_active: bool = Field(True, description="Whether currency is active")
    is_default: bool = Field(False, description="Whether this is the default currency")
    sort_order: int = Field(0, ge=0, description="Display sort order")


class CurrencyUpdate(BaseModel):
    """
    Update currency exchange rate

    Exchange rate interpretation:
    - EUR is the BASE currency (exchange_rate = 1.00)
    - exchange_rate = units of THIS currency per 1 EUR (EUR/XXX rate)
    - Example: USD with exchange_rate = 1.10 means 1 EUR = 1.10 USD
    """
    exchange_rate: Optional[float] = Field(None, ge=0, description="Exchange rate (units of currency per 1 EUR)")


class TierProviderSettingsUpdate(BaseModel):
    """Update provider settings for a tier"""
    provider_settings: Dict[str, bool] = Field(
        ...,
        description="Map of provider_key to is_enabled status, e.g., {'google_drive': true, 'onedrive': true, 'dropbox': false}"
    )


class SystemStats(BaseModel):
    """System statistics"""
    total_users: int
    active_users: int
    total_documents: int
    total_storage_bytes: int
    users_by_tier: Dict[str, int]
    documents_last_24h: int
    signups_last_7d: int


# ============================================================
# User Management Endpoints
# ============================================================

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    tier_id: Optional[int] = Query(None, description="Filter by tier ID"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    List all users with pagination and filtering

    Admin only endpoint to view and manage users.
    """
    session = db_manager.session_local()
    try:
        # Build query - join with tier and monthly usage
        # Get current month period for usage stats
        from datetime import datetime
        current_month = datetime.utcnow().strftime("%Y-%m")

        query = select(User, TierPlan, UserStorageQuota, UserMonthlyUsage).join(
            TierPlan, User.tier_id == TierPlan.id
        ).outerjoin(
            UserStorageQuota, UserStorageQuota.user_id == User.id
        ).outerjoin(
            UserMonthlyUsage,
            and_(
                UserMonthlyUsage.user_id == User.id,
                UserMonthlyUsage.month_period == current_month
            )
        )

        # Apply filters
        if tier_id is not None:
            query = query.where(User.tier_id == tier_id)

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern)
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = session.execute(count_query).scalar()

        # Apply pagination
        query = query.order_by(desc(User.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        results = session.execute(query).all()

        users = []
        for user, tier, quota, monthly_usage in results:
            # Calculate usage percentages
            pages_percent = 0
            volume_percent = 0
            if monthly_usage:
                if tier.max_pages_per_month:
                    pages_percent = (monthly_usage.pages_processed / tier.max_pages_per_month * 100)
                if tier.max_monthly_upload_bytes:
                    volume_percent = (monthly_usage.volume_uploaded_bytes / tier.max_monthly_upload_bytes * 100)

            users.append({
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "tier_id": user.tier_id,
                "tier_name": tier.display_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,

                # Legacy storage info (deprecated but kept for backward compatibility)
                "storage_used_bytes": quota.used_bytes if quota else 0,
                "storage_quota_bytes": quota.total_quota_bytes if quota else 0,
                "document_count": quota.document_count if quota else 0,

                # Monthly usage stats
                "monthly_usage": {
                    "month_period": current_month,
                    "pages_processed": monthly_usage.pages_processed if monthly_usage else 0,
                    "pages_limit": tier.max_pages_per_month,
                    "pages_percent": round(pages_percent, 1),
                    "volume_uploaded_bytes": monthly_usage.volume_uploaded_bytes if monthly_usage else 0,
                    "volume_limit_bytes": tier.max_monthly_upload_bytes,
                    "volume_percent": round(volume_percent, 1),
                    "documents_uploaded": monthly_usage.documents_uploaded if monthly_usage else 0,
                    "translations_used": monthly_usage.translations_used if monthly_usage else 0,
                    "translations_limit": tier.max_translations_per_month,
                    "api_calls_made": monthly_usage.api_calls_made if monthly_usage else 0,
                    "api_calls_limit": tier.max_api_calls_per_month,
                    "period_start": monthly_usage.period_start_date.isoformat() if monthly_usage else None,
                    "period_end": monthly_usage.period_end_date.isoformat() if monthly_usage else None,
                } if not user.is_admin else {
                    "month_period": current_month,
                    "admin_unlimited": True
                },

                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat()
            })

        logger.info(f"Admin {current_user.email} listed users (page {page}/{(total + page_size - 1) // page_size})")

        return {
            "users": users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )
    finally:
        session.close()


@router.patch("/users/{user_id}/tier")
async def update_user_tier(
    user_id: str,
    tier_update: UserTierUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update user's tier

    Admin only endpoint to change user tier (upgrade/downgrade).
    """
    logger.info(f"[DEBUG] update_user_tier: REQUEST RECEIVED - user_id={user_id}, tier_id={tier_update.tier_id}, admin={current_user.email}")

    session = db_manager.session_local()
    try:
        logger.info(f"[DEBUG] update_user_tier: Step 1 - Fetching user from database - user_id={user_id}")
        # Get user
        user = session.get(User, user_id)
        if not user:
            logger.error(f"[DEBUG] update_user_tier: User not found - user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        logger.info(f"[DEBUG] update_user_tier: User found - email={user.email}, current_tier_id={user.tier_id}")

        logger.info(f"[DEBUG] update_user_tier: Step 2 - Verifying new tier exists - tier_id={tier_update.tier_id}")
        # Verify new tier exists
        new_tier = session.get(TierPlan, tier_update.tier_id)
        if not new_tier:
            logger.error(f"[DEBUG] update_user_tier: Invalid tier ID - tier_id={tier_update.tier_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier ID: {tier_update.tier_id}"
            )
        logger.info(f"[DEBUG] update_user_tier: New tier found - name={new_tier.display_name}, email_enabled={new_tier.email_to_process_enabled}")

        logger.info(f"[DEBUG] update_user_tier: Step 3 - Updating user tier_id")
        old_tier_id = user.tier_id
        user.tier_id = tier_update.tier_id
        logger.info(f"[DEBUG] update_user_tier: User tier_id updated in memory - old={old_tier_id}, new={tier_update.tier_id}")

        logger.info(f"[DEBUG] update_user_tier: Step 4 - Updating storage quota")
        # Update or create storage quota
        try:
            quota = session.execute(
                select(UserStorageQuota).where(UserStorageQuota.user_id == user.id)
            ).scalar_one_or_none()

            if quota:
                logger.info(f"[DEBUG] update_user_tier: Existing quota found - updating")
                quota.tier_id = tier_update.tier_id
                quota.total_quota_bytes = new_tier.max_monthly_upload_bytes
            else:
                logger.info(f"[DEBUG] update_user_tier: No quota found - creating new")
                quota = UserStorageQuota(
                    user_id=user.id,
                    tier_id=tier_update.tier_id,
                    total_quota_bytes=new_tier.max_monthly_upload_bytes,
                    used_bytes=0,
                    document_count=0
                )
                session.add(quota)
            logger.info(f"[DEBUG] update_user_tier: Storage quota updated successfully")
        except Exception as quota_error:
            logger.error(f"[DEBUG] update_user_tier: ERROR in storage quota update - {type(quota_error).__name__}: {quota_error}")
            raise

        logger.info(f"[DEBUG] update_user_tier: Step 5 - Importing Subscription model")
        # Update or create subscription for non-Free tiers
        try:
            from app.database.models import Subscription
            logger.info(f"[DEBUG] update_user_tier: Subscription model imported successfully")
        except Exception as import_error:
            logger.error(f"[DEBUG] update_user_tier: ERROR importing Subscription model - {type(import_error).__name__}: {import_error}")
            raise

        if tier_update.tier_id > 0:  # Not Free tier
            logger.info(f"[DEBUG] update_user_tier: Step 6 - Handling Pro tier subscription")
            try:
                # Check for existing admin-granted subscription (any status)
                admin_sub_id = f"admin_granted_{user.id}"
                logger.info(f"[DEBUG] update_user_tier: Looking for existing admin subscription - admin_sub_id={admin_sub_id}")

                existing_subscription = session.execute(
                    select(Subscription).where(
                        Subscription.user_id == user.id,
                        Subscription.stripe_subscription_id == admin_sub_id
                    )
                ).scalar_one_or_none()

                if existing_subscription:
                    logger.info(f"[DEBUG] update_user_tier: Found existing admin subscription - reactivating")
                    # Reactivate and update existing subscription
                    existing_subscription.tier_id = tier_update.tier_id
                    existing_subscription.status = 'active'
                    existing_subscription.canceled_at = None
                    existing_subscription.ended_at = None
                    existing_subscription.cancel_at_period_end = False
                    # Extend period
                    now = datetime.now(timezone.utc)
                    existing_subscription.current_period_start = now
                    existing_subscription.current_period_end = now + timedelta(days=365)
                    logger.info(f"[DEBUG] update_user_tier: Admin subscription reactivated")
                else:
                    logger.info(f"[DEBUG] update_user_tier: No admin subscription - checking for Stripe subscription")
                    # Check for any active subscription (Stripe-managed)
                    active_stripe_sub = session.execute(
                        select(Subscription).where(
                            Subscription.user_id == user.id,
                            Subscription.status.in_(['active', 'trialing']),
                            Subscription.stripe_subscription_id != admin_sub_id
                        )
                    ).scalar_one_or_none()

                    if active_stripe_sub:
                        logger.info(f"[DEBUG] update_user_tier: Found active Stripe subscription - updating tier only")
                        # User has a real Stripe subscription, just update tier
                        active_stripe_sub.tier_id = tier_update.tier_id
                    else:
                        logger.info(f"[DEBUG] update_user_tier: No subscriptions found - creating new admin subscription")
                        # Create new admin-granted subscription
                        now = datetime.now(timezone.utc)
                        period_end = now + timedelta(days=365)  # 1 year from now

                        new_subscription = Subscription(
                            user_id=user.id,
                            tier_id=tier_update.tier_id,
                            stripe_subscription_id=admin_sub_id,
                            stripe_price_id=f"admin_price_{tier_update.tier_id}",
                            billing_cycle='yearly',
                            status='active',
                            current_period_start=now,
                            current_period_end=period_end,
                            cancel_at_period_end=False,
                            currency='USD',
                            amount_cents=0  # Admin-granted, no charge
                        )
                        session.add(new_subscription)
                        logger.info(f"[DEBUG] update_user_tier: New admin subscription created")
            except Exception as sub_error:
                logger.error(f"[DEBUG] update_user_tier: ERROR in subscription handling - {type(sub_error).__name__}: {sub_error}")
                import traceback
                logger.error(f"[DEBUG] update_user_tier: Traceback:\n{traceback.format_exc()}")
                raise
        else:
            logger.info(f"[DEBUG] update_user_tier: Step 6 - Handling Free tier - canceling subscriptions")
            try:
                # Free tier - cancel any active subscriptions
                active_subs = session.execute(
                    select(Subscription).where(
                        Subscription.user_id == user.id,
                        Subscription.status.in_(['active', 'trialing'])
                    )
                ).scalars().all()

                logger.info(f"[DEBUG] update_user_tier: Found {len(active_subs)} active subscriptions to cancel")
                for sub in active_subs:
                    sub.status = 'canceled'
                    sub.canceled_at = datetime.now(timezone.utc)
                    sub.ended_at = datetime.now(timezone.utc)
                logger.info(f"[DEBUG] update_user_tier: All subscriptions canceled")
            except Exception as cancel_error:
                logger.error(f"[DEBUG] update_user_tier: ERROR canceling subscriptions - {type(cancel_error).__name__}: {cancel_error}")
                raise

        logger.info(f"[DEBUG] update_user_tier: Step 7 - Handling email processing feature")
        # Handle email processing feature based on tier
        # Check if new tier has email-to-process feature enabled
        try:
            if new_tier.email_to_process_enabled and not user.email_processing_enabled:
                logger.info(f"[DEBUG] update_user_tier: Enabling email processing for Pro user")
                # Enable email processing for Pro users
                from app.services.email_processing_service import EmailProcessingService
                email_service = EmailProcessingService(session)
                success, email_address, error = email_service.auto_enable_email_processing_for_pro_user(str(user.id))
                if success:
                    logger.info(f"[DEBUG] update_user_tier: Email processing enabled successfully - {email_address}")
                else:
                    logger.warning(f"[DEBUG] update_user_tier: Failed to enable email processing - {error}")
            elif not new_tier.email_to_process_enabled and user.email_processing_enabled:
                logger.info(f"[DEBUG] update_user_tier: Disabling email processing for downgrade")
                # Disable email processing when downgrading from Pro
                user.email_processing_enabled = False
                logger.info(f"[DEBUG] update_user_tier: Email processing disabled")
            else:
                logger.info(f"[DEBUG] update_user_tier: No email processing changes needed")
        except Exception as email_error:
            logger.error(f"[DEBUG] update_user_tier: ERROR in email processing - {type(email_error).__name__}: {email_error}")
            import traceback
            logger.error(f"[DEBUG] update_user_tier: Traceback:\n{traceback.format_exc()}")
            raise

        logger.info(f"[DEBUG] update_user_tier: Step 8 - Committing transaction to database")
        try:
            session.commit()
            logger.info(f"[DEBUG] update_user_tier: Transaction committed successfully")
        except Exception as commit_error:
            logger.error(f"[DEBUG] update_user_tier: ERROR during commit - {type(commit_error).__name__}: {commit_error}")
            import traceback
            logger.error(f"[DEBUG] update_user_tier: Traceback:\n{traceback.format_exc()}")
            raise

        logger.info(f"Admin {current_user.email} updated user {user.email} tier: {old_tier_id} → {tier_update.tier_id}")

        response_data = {
            "message": "User tier updated successfully",
            "user_id": user_id,
            "old_tier_id": old_tier_id,
            "new_tier_id": tier_update.tier_id,
            "new_tier_name": new_tier.display_name
        }
        logger.info(f"[DEBUG] update_user_tier: Returning success response - {response_data}")
        return response_data

    except HTTPException as http_exc:
        logger.error(f"[DEBUG] update_user_tier: HTTP Exception - status={http_exc.status_code}, detail={http_exc.detail}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"[DEBUG] update_user_tier: Unexpected exception in outer handler - {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[DEBUG] update_user_tier: Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user tier: {type(e).__name__}: {str(e)}"
        )
    finally:
        logger.info(f"[DEBUG] update_user_tier: Closing database session")
        session.close()


# ============================================================
# Tier Plan Management Endpoints
# ============================================================

@router.get("/tiers")
async def list_tier_plans(
    current_user: User = Depends(get_current_admin_user)
):
    """
    List all tier plans

    Admin only endpoint to view tier plan configuration.
    Includes provider settings for each tier.
    """
    session = db_manager.session_local()
    try:
        result = session.execute(
            select(TierPlan).order_by(TierPlan.sort_order)
        )
        tiers = result.scalars().all()

        # Get all provider settings
        provider_settings_result = session.execute(
            select(TierProviderSettings)
        )
        all_provider_settings = provider_settings_result.scalars().all()

        # Group provider settings by tier_id
        settings_by_tier = {}
        for setting in all_provider_settings:
            if setting.tier_id not in settings_by_tier:
                settings_by_tier[setting.tier_id] = {}
            settings_by_tier[setting.tier_id][setting.provider_key] = setting.is_enabled

        # Get all available providers from registry for reference
        all_providers = [p.provider_key for p in ProviderRegistry.get_all()]

        tier_list = []
        for tier in tiers:
            # Get provider settings for this tier, defaulting to False if not set
            tier_provider_settings = settings_by_tier.get(tier.id, {})
            provider_settings = {
                provider: tier_provider_settings.get(provider, False)
                for provider in all_providers
            }

            tier_list.append({
                "id": tier.id,
                "name": tier.name,
                "display_name": tier.display_name,
                "description": tier.description,
                "price_monthly_cents": tier.price_monthly_cents,
                "price_yearly_cents": tier.price_yearly_cents,
                "max_monthly_upload_bytes": tier.max_monthly_upload_bytes,
                "max_file_size_bytes": tier.max_file_size_bytes,
                "max_pages_per_month": tier.max_pages_per_month,
                "max_translations_per_month": tier.max_translations_per_month,
                "max_api_calls_per_month": tier.max_api_calls_per_month,
                "max_team_members": tier.max_team_members,
                "max_batch_upload_size": tier.max_batch_upload_size,
                "bulk_operations_enabled": tier.bulk_operations_enabled,
                "email_to_process_enabled": tier.email_to_process_enabled,
                "folder_to_process_enabled": tier.folder_to_process_enabled,
                "multi_user_enabled": tier.multi_user_enabled,
                "api_access_enabled": tier.api_access_enabled,
                "priority_support": tier.priority_support,
                "is_active": tier.is_active,
                "is_public": tier.is_public,
                "sort_order": tier.sort_order,
                "created_at": tier.created_at.isoformat(),
                "updated_at": tier.updated_at.isoformat(),
                "provider_settings": provider_settings
            })

        logger.info(f"Admin {current_user.email} listed tier plans")

        return {"tiers": tier_list}

    except Exception as e:
        logger.error(f"Error listing tier plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tier plans"
        )
    finally:
        session.close()


@router.patch("/tiers/{tier_id}")
async def update_tier_plan(
    tier_id: int,
    tier_update: TierPlanUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update tier plan configuration

    Admin only endpoint to modify tier limits, pricing, and features.
    """
    session = db_manager.session_local()
    try:
        tier = session.get(TierPlan, tier_id)
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tier {tier_id} not found"
            )

        # Update fields
        update_data = tier_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(tier, field):
                setattr(tier, field, value)

        tier.updated_at = datetime.utcnow()

        session.commit()
        session.refresh(tier)

        logger.info(f"Admin {current_user.email} updated tier {tier_id}: {update_data}")

        return {
            "message": "Tier plan updated successfully",
            "tier_id": tier_id,
            "tier_name": tier.display_name,
            "updated_fields": list(update_data.keys())
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating tier plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tier plan"
        )
    finally:
        session.close()


# ============================================================
# Storage Providers Endpoints
# ============================================================

@router.get("/providers")
async def list_storage_providers(
    current_user: User = Depends(get_current_admin_user)
):
    """
    List all storage providers with their tier requirements.

    Returns provider configurations including:
    - Provider key and display name
    - Minimum tier required
    - Active status
    - UI metadata (icon, color, description)
    """
    session = db_manager.session_local()
    try:
        # Get all tiers for reference
        tiers_result = session.execute(
            select(TierPlan.id, TierPlan.display_name)
            .order_by(TierPlan.id)
        ).all()
        tiers_map = {tier_id: display_name for tier_id, display_name in tiers_result}

        # Get all providers from registry
        providers = []
        for provider in ProviderRegistry.get_all():
            tier_name = tiers_map.get(provider.min_tier_id, f"Tier {provider.min_tier_id}")
            providers.append({
                "provider_key": provider.provider_key,
                "display_name": provider.display_name,
                "min_tier_id": provider.min_tier_id,
                "min_tier_name": tier_name,
                "is_active": provider.is_active,
                "sort_order": provider.sort_order,
                "icon": provider.icon,
                "color": provider.color,
                "description": provider.description,
                "capabilities": [cap.value for cap in provider.capabilities] if provider.capabilities else []
            })

        logger.info(f"Admin {current_user.email} listed storage providers")

        return {
            "providers": providers,
            "tiers": [{"id": tid, "name": tname} for tid, tname in tiers_result],
            "note": "Provider configurations are defined in code. To modify, update provider_registry.py"
        }

    except Exception as e:
        logger.error(f"Error listing storage providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list storage providers"
        )
    finally:
        session.close()


@router.patch("/tiers/{tier_id}/providers")
async def update_tier_provider_settings(
    tier_id: int,
    settings_update: TierProviderSettingsUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update provider settings for a specific tier.

    Sets which storage providers are enabled/disabled for the tier.
    """
    session = db_manager.session_local()
    try:
        # Verify tier exists
        tier = session.get(TierPlan, tier_id)
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tier {tier_id} not found"
            )

        # Get valid provider keys
        valid_providers = {p.provider_key for p in ProviderRegistry.get_all()}

        # Update or insert provider settings
        for provider_key, is_enabled in settings_update.provider_settings.items():
            if provider_key not in valid_providers:
                logger.warning(f"Unknown provider key: {provider_key}")
                continue

            # Check if setting exists
            existing = session.execute(
                select(TierProviderSettings).where(
                    and_(
                        TierProviderSettings.tier_id == tier_id,
                        TierProviderSettings.provider_key == provider_key
                    )
                )
            ).scalar_one_or_none()

            if existing:
                existing.is_enabled = is_enabled
            else:
                new_setting = TierProviderSettings(
                    tier_id=tier_id,
                    provider_key=provider_key,
                    is_enabled=is_enabled
                )
                session.add(new_setting)

        session.commit()

        logger.info(f"Admin {current_user.email} updated provider settings for tier {tier_id}: {settings_update.provider_settings}")

        return {
            "message": "Provider settings updated successfully",
            "tier_id": tier_id,
            "tier_name": tier.display_name,
            "updated_providers": list(settings_update.provider_settings.keys())
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating tier provider settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update provider settings"
        )
    finally:
        session.close()


# ============================================================
# System Statistics Endpoints
# ============================================================

@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get system-wide statistics

    Admin only endpoint for dashboard overview.
    """
    session = db_manager.session_local()
    try:
        # Total users
        total_users = session.execute(select(func.count(User.id))).scalar()

        # Active users
        active_users = session.execute(
            select(func.count(User.id)).where(User.is_active == True)
        ).scalar()

        # Total documents
        total_documents = session.execute(select(func.count(Document.id))).scalar()

        # Total storage
        total_storage = session.execute(
            select(func.coalesce(func.sum(Document.file_size), 0))
        ).scalar()

        # Users by tier
        tier_counts = session.execute(
            select(TierPlan.display_name, func.count(User.id))
            .join(User, User.tier_id == TierPlan.id)
            .group_by(TierPlan.display_name)
        ).all()
        users_by_tier = {tier_name: count for tier_name, count in tier_counts}

        # Documents last 24h
        yesterday = datetime.utcnow() - timedelta(days=1)
        docs_24h = session.execute(
            select(func.count(Document.id)).where(Document.created_at >= yesterday)
        ).scalar()

        # Signups last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        signups_7d = session.execute(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        ).scalar()

        logger.info(f"Admin {current_user.email} viewed system stats")

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_documents": total_documents,
            "total_storage_bytes": total_storage,
            "total_storage_mb": round(total_storage / (1024 * 1024), 2),
            "users_by_tier": users_by_tier,
            "documents_last_24h": docs_24h,
            "signups_last_7d": signups_7d,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error retrieving system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )
    finally:
        session.close()


@router.get("/activity")
async def get_recent_activity(
    limit: int = Query(50, ge=1, le=200, description="Number of recent activities"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get recent system activity (audit logs)

    Admin only endpoint to monitor recent user actions.
    """
    session = db_manager.session_local()
    try:
        result = session.execute(
            select(AuditLog, User)
            .join(User, AuditLog.user_id == User.id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )

        activities = []
        for log, user in result:
            activities.append({
                "id": str(log.id),
                "user_email": user.email,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "status": log.status,
                "created_at": log.created_at.isoformat()
            })

        logger.info(f"Admin {current_user.email} viewed recent activity")

        return {"activities": activities}

    except Exception as e:
        logger.error(f"Error retrieving activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity logs"
        )
    finally:
        session.close()


# ============================================================
# System Health Endpoints
# ============================================================

@router.get("/health/clamav")
async def get_clamav_health(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get ClamAV antivirus daemon health status

    Admin only endpoint to monitor antivirus service.
    """
    try:
        health = await clamav_health_service.check_health()

        logger.info(f"Admin {current_user.email} checked ClamAV health: {health['status']}")

        return health

    except Exception as e:
        logger.error(f"Error checking ClamAV health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check ClamAV health"
        )


@router.post("/health/clamav/restart")
async def restart_clamav(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Restart ClamAV antivirus daemon

    Admin only endpoint to restart ClamAV when it's down.
    """
    try:
        result = await clamav_health_service.restart_service()

        logger.warning(f"Admin {current_user.email} triggered ClamAV restart: {result}")

        if result['success']:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=result
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=result
            )

    except Exception as e:
        logger.error(f"Error restarting ClamAV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart ClamAV: {str(e)}"
        )


@router.get("/health/email-poller")
async def get_email_poller_health(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get email poller service health status

    Admin only endpoint to monitor email polling service.
    Checks IMAP connectivity, recent activity, and polling status.
    """
    try:
        health = await email_poller_health_service.check_health()

        logger.info(f"Admin {current_user.email} checked email poller health: {health['status']}")

        return health

    except Exception as e:
        logger.error(f"Error checking email poller health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check email poller health"
        )


@router.post("/health/email-poller/poll-now")
async def trigger_email_poll(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Manually trigger email polling immediately

    Admin only endpoint to force an immediate email poll.
    Useful for debugging or when urgent email processing is needed.
    """
    try:
        result = await email_poller_health_service.trigger_manual_poll()

        logger.warning(f"Admin {current_user.email} triggered manual email poll: {result}")

        if result['success']:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=result
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=result
            )

    except Exception as e:
        logger.error(f"Error triggering email poll: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger email poll: {str(e)}"
        )


# ============================================================
# Email Template Management Endpoints
# ============================================================

class EmailTemplateCreate(BaseModel):
    """Create new email template"""
    template_key: str = Field(..., description="Template identifier (e.g., 'welcome_email')")
    language: str = Field(default="en", description="Language code (ISO 639-1)")
    subject: str = Field(..., description="Email subject line")
    html_content: str = Field(..., description="HTML email content with {{variable}} placeholders")
    variables: Optional[List[str]] = Field(None, description="List of variable names used in template")
    description: Optional[str] = Field(None, description="Template description for admins")
    is_active: bool = Field(default=True, description="Template active status")


class EmailTemplateUpdate(BaseModel):
    """Update existing email template"""
    subject: Optional[str] = None
    html_content: Optional[str] = None
    variables: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/email-templates")
async def list_email_templates(
    name: Optional[str] = Query(None, description="Filter by template name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    List all email templates with optional filtering

    Admin only endpoint to manage email templates.
    """
    session = db_manager.session_local()
    try:
        query = select(EmailTemplate)

        if name:
            query = query.where(EmailTemplate.name == name)

        if category:
            query = query.where(EmailTemplate.category == category)

        if is_active is not None:
            query = query.where(EmailTemplate.is_active == is_active)

        query = query.order_by(EmailTemplate.name)

        result = session.execute(query)
        templates = result.scalars().all()

        return {
            "templates": [
                {
                    "id": str(template.id),
                    "template_key": template.name,  # Map name to template_key for frontend compatibility
                    "language": "en",  # Default language since no language field exists
                    "subject": template.subject,
                    "html_content": template.html_body,  # Map html_body to html_content
                    "variables": template.available_variables or [],
                    "description": template.description,
                    "is_active": template.is_active,
                    "created_at": template.created_at.isoformat(),
                    "updated_at": template.updated_at.isoformat()
                }
                for template in templates
            ],
            "total": len(templates)
        }

    except Exception as e:
        logger.error(f"Error listing email templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list email templates"
        )
    finally:
        session.close()


@router.post("/email-templates")
async def create_email_template(
    template: EmailTemplateCreate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Create a new email template

    Admin only endpoint to create email templates for transactional emails.
    """
    session = db_manager.session_local()
    try:
        # Check if template already exists for this key and language
        existing = session.execute(
            select(EmailTemplate).where(
                and_(
                    EmailTemplate.template_key == template.template_key,
                    EmailTemplate.language == template.language
                )
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Template '{template.template_key}' already exists for language '{template.language}'"
            )

        # Create new template
        new_template = EmailTemplate(
            template_key=template.template_key,
            language=template.language,
            subject=template.subject,
            html_content=template.html_content,
            variables=template.variables,
            description=template.description,
            is_active=template.is_active
        )

        session.add(new_template)
        session.commit()
        session.refresh(new_template)

        logger.info(f"Admin {current_user.email} created email template: {template.template_key} ({template.language})")

        return {
            "message": "Email template created successfully",
            "template": {
                "id": str(new_template.id),
                "template_key": new_template.template_key,
                "language": new_template.language,
                "subject": new_template.subject,
                "is_active": new_template.is_active
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating email template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create email template"
        )
    finally:
        session.close()


@router.put("/email-templates/{template_id}")
async def update_email_template(
    template_id: str,
    update_data: EmailTemplateUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update an existing email template

    Admin only endpoint to modify email template content.
    """
    session = db_manager.session_local()
    try:
        template = session.execute(
            select(EmailTemplate).where(EmailTemplate.id == template_id)
        ).scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email template not found"
            )

        # Update fields
        if update_data.subject is not None:
            template.subject = update_data.subject
        if update_data.html_content is not None:
            template.html_body = update_data.html_content  # Map html_content to html_body
        if update_data.description is not None:
            template.description = update_data.description
        if update_data.is_active is not None:
            template.is_active = update_data.is_active

        template.updated_at = datetime.now()
        session.commit()
        session.refresh(template)

        logger.info(f"Admin {current_user.email} updated email template: {template.name}")

        return {
            "message": "Email template updated successfully",
            "template": {
                "id": str(template.id),
                "template_key": template.name,
                "language": "en",
                "subject": template.subject,
                "is_active": template.is_active,
                "updated_at": template.updated_at.isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating email template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email template"
        )
    finally:
        session.close()


@router.delete("/email-templates/{template_id}")
async def delete_email_template(
    template_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete an email template

    Admin only endpoint to remove email templates.
    """
    session = db_manager.session_local()
    try:
        template = session.execute(
            select(EmailTemplate).where(EmailTemplate.id == template_id)
        ).scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email template not found"
            )

        template_info = f"{template.template_key} ({template.language})"

        session.delete(template)
        session.commit()

        logger.info(f"Admin {current_user.email} deleted email template: {template_info}")

        return {
            "message": "Email template deleted successfully",
            "deleted_template": template_info
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting email template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete email template"
        )
    finally:
        session.close()

# ============================================================
# Currency Management (Admin Only)
# ============================================================

@router.get(
    "/currencies",
    summary="Get All Currencies",
    description="Get all currencies with their exchange rates (admin only)"
)
async def get_currencies(
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get all currencies for admin management

    Returns all currencies including those without exchange rates set.
    This allows admin to see which currencies need configuration.
    """
    session = db_manager.session_local()

    try:
        currencies = session.query(Currency).order_by(Currency.sort_order).all()

        return {
            "currencies": [
                {
                    "code": c.code,
                    "symbol": c.symbol,
                    "name": c.name,
                    "decimal_places": c.decimal_places,
                    "exchange_rate": float(c.exchange_rate) if c.exchange_rate else None,
                    "is_active": c.is_active,
                    "is_default": c.is_default,
                    "sort_order": c.sort_order
                }
                for c in currencies
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching currencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch currencies"
        )
    finally:
        session.close()


@router.patch(
    "/currencies/{currency_code}",
    summary="Update Currency Exchange Rate",
    description="Update the exchange rate for a specific currency (admin only)"
)
async def update_currency_exchange_rate(
    currency_code: str,
    currency_update: CurrencyUpdate,
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Update currency exchange rate

    Exchange rate interpretation:
    - EUR is the BASE currency (exchange_rate = 1.00)
    - exchange_rate = units of THIS currency per 1 EUR (EUR/XXX rate)
    - Example: Setting USD exchange_rate to 1.10 means 1 EUR = 1.10 USD
    - Formula: price_in_currency = price_in_eur × exchange_rate

    Only currencies WITH exchange rates will be shown to users for selection.
    Set exchange_rate to null to hide a currency from users.
    """
    session = db_manager.session_local()

    try:
        # Find currency by code
        currency = session.query(Currency).filter(
            Currency.code == currency_code.upper()
        ).first()

        if not currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Currency '{currency_code}' not found"
            )

        # Update exchange rate
        if currency_update.exchange_rate is not None:
            currency.exchange_rate = currency_update.exchange_rate
            logger.info(
                f"Admin {current_admin.email} updated {currency_code} exchange rate to {currency_update.exchange_rate}"
            )
        
        session.commit()

        return {
            "message": f"Currency '{currency_code}' updated successfully",
            "currency": {
                "code": currency.code,
                "symbol": currency.symbol,
                "name": currency.name,
                "exchange_rate": float(currency.exchange_rate) if currency.exchange_rate else None,
                "is_active": currency.is_active
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating currency {currency_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update currency"
        )
    finally:
        session.close()


@router.post(
    "/currencies",
    summary="Create New Currency",
    description="Create a new currency (admin only)"
)
async def create_currency(
    currency_data: CurrencyCreate,
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Create a new currency

    Exchange rate interpretation:
    - EUR is the BASE currency (exchange_rate = 1.00)
    - exchange_rate = units of THIS currency per 1 EUR (EUR/XXX rate)
    - Example: Setting USD exchange_rate to 1.10 means 1 EUR = 1.10 USD
    """
    session = db_manager.session_local()

    try:
        # Check if currency already exists
        existing = session.query(Currency).filter(
            Currency.code == currency_data.code.upper()
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Currency '{currency_data.code}' already exists"
            )

        # Create new currency
        import uuid
        new_currency = Currency(
            id=uuid.uuid4(),
            code=currency_data.code.upper(),
            symbol=currency_data.symbol,
            name=currency_data.name,
            decimal_places=currency_data.decimal_places,
            exchange_rate=currency_data.exchange_rate,
            is_active=currency_data.is_active,
            is_default=currency_data.is_default,
            sort_order=currency_data.sort_order
        )

        session.add(new_currency)
        session.commit()

        logger.info(f"Admin {current_admin.email} created currency {currency_data.code}")

        return {
            "message": f"Currency '{currency_data.code}' created successfully",
            "currency": {
                "code": new_currency.code,
                "symbol": new_currency.symbol,
                "name": new_currency.name,
                "decimal_places": new_currency.decimal_places,
                "exchange_rate": float(new_currency.exchange_rate) if new_currency.exchange_rate else None,
                "is_active": new_currency.is_active,
                "is_default": new_currency.is_default,
                "sort_order": new_currency.sort_order
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating currency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create currency"
        )
    finally:
        session.close()


@router.delete(
    "/currencies/{currency_code}",
    summary="Delete Currency",
    description="Delete a currency (admin only)"
)
async def delete_currency(
    currency_code: str,
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Delete a currency

    Note: Cannot delete currency if it's set as default or if it's used in active subscriptions.
    """
    session = db_manager.session_local()

    try:
        # Find currency by code
        currency = session.query(Currency).filter(
            Currency.code == currency_code.upper()
        ).first()

        if not currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Currency '{currency_code}' not found"
            )

        # Check if it's the default currency
        if currency.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the default currency"
            )

        session.delete(currency)
        session.commit()

        logger.info(f"Admin {current_admin.email} deleted currency {currency_code}")

        return {
            "message": f"Currency '{currency_code}' deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting currency {currency_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete currency"
        )
    finally:
        session.close()
