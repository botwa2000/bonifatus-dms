# backend/app/api/admin.py
"""
Bonifatus DMS - Admin API
Administrative endpoints for user management, tier configuration, and system monitoring
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.models import User, TierPlan, UserStorageQuota, Document, AuditLog
from app.database.connection import db_manager
from app.middleware.auth_middleware import get_current_admin_user
from app.services.clamav_health_service import clamav_health_service

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
    storage_quota_bytes: Optional[int] = Field(None, description="Storage limit in bytes")
    max_file_size_bytes: Optional[int] = Field(None, description="Max individual file size")
    max_documents: Optional[int] = Field(None, description="Max document count, null for unlimited")
    max_batch_upload_size: Optional[int] = Field(None, description="Max files per batch upload, null for unlimited")
    bulk_operations_enabled: Optional[bool] = None
    api_access_enabled: Optional[bool] = None
    priority_support: Optional[bool] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class UserTierUpdate(BaseModel):
    """Update user tier"""
    tier_id: int = Field(..., description="New tier ID (0=Free, 1=Starter, 2=Pro, 100=Admin)")


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
        # Build query
        query = select(User, TierPlan, UserStorageQuota).join(
            TierPlan, User.tier_id == TierPlan.id
        ).outerjoin(
            UserStorageQuota, UserStorageQuota.user_id == User.id
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
        for user, tier, quota in results:
            users.append({
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "tier_id": user.tier_id,
                "tier_name": tier.display_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "storage_used_bytes": quota.used_bytes if quota else 0,
                "storage_quota_bytes": quota.total_quota_bytes if quota else tier.storage_quota_bytes,
                "document_count": quota.document_count if quota else 0,
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
    session = db_manager.session_local()
    try:
        # Get user
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify new tier exists
        new_tier = session.get(TierPlan, tier_update.tier_id)
        if not new_tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier ID: {tier_update.tier_id}"
            )

        old_tier_id = user.tier_id
        user.tier_id = tier_update.tier_id

        # Update or create storage quota
        quota = session.execute(
            select(UserStorageQuota).where(UserStorageQuota.user_id == user.id)
        ).scalar_one_or_none()

        if quota:
            quota.tier_id = tier_update.tier_id
            quota.total_quota_bytes = new_tier.storage_quota_bytes
        else:
            quota = UserStorageQuota(
                user_id=user.id,
                tier_id=tier_update.tier_id,
                total_quota_bytes=new_tier.storage_quota_bytes,
                used_bytes=0,
                document_count=0
            )
            session.add(quota)

        session.commit()

        logger.info(f"Admin {current_user.email} updated user {user.email} tier: {old_tier_id} → {tier_update.tier_id}")

        return {
            "message": "User tier updated successfully",
            "user_id": user_id,
            "old_tier_id": old_tier_id,
            "new_tier_id": tier_update.tier_id,
            "new_tier_name": new_tier.display_name
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating user tier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user tier"
        )
    finally:
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
    """
    session = db_manager.session_local()
    try:
        result = session.execute(
            select(TierPlan).order_by(TierPlan.sort_order)
        )
        tiers = result.scalars().all()

        tier_list = []
        for tier in tiers:
            tier_list.append({
                "id": tier.id,
                "name": tier.name,
                "display_name": tier.display_name,
                "description": tier.description,
                "price_monthly_cents": tier.price_monthly_cents,
                "price_yearly_cents": tier.price_yearly_cents,
                "storage_quota_bytes": tier.storage_quota_bytes,
                "max_file_size_bytes": tier.max_file_size_bytes,
                "max_documents": tier.max_documents,
                "max_batch_upload_size": tier.max_batch_upload_size,
                "bulk_operations_enabled": tier.bulk_operations_enabled,
                "api_access_enabled": tier.api_access_enabled,
                "priority_support": tier.priority_support,
                "is_active": tier.is_active,
                "is_public": tier.is_public,
                "sort_order": tier.sort_order,
                "created_at": tier.created_at.isoformat(),
                "updated_at": tier.updated_at.isoformat()
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
