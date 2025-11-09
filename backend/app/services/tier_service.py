# backend/app/services/tier_service.py
"""
Bonifatus DMS - Tier Management Service
Business logic for user tier management, quota enforcement, and feature gating
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database.models import TierPlan, User, UserStorageQuota, Document
from app.database.connection import db_manager

logger = logging.getLogger(__name__)


class TierLimitExceeded(Exception):
    """Raised when a user exceeds their tier limits"""
    def __init__(self, message: str, limit_type: str, current: int, max_allowed: int):
        self.message = message
        self.limit_type = limit_type
        self.current = current
        self.max_allowed = max_allowed
        super().__init__(self.message)


class TierService:
    """Tier management and quota enforcement service"""

    def __init__(self):
        self._tier_cache: Dict[int, TierPlan] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes

    async def get_tier_plan(self, tier_id: int, session: Session) -> Optional[TierPlan]:
        """Get tier plan by ID with caching"""
        try:
            # Check cache validity
            if (self._cache_timestamp is None or
                (datetime.utcnow() - self._cache_timestamp).total_seconds() > self._cache_ttl_seconds):
                await self._refresh_tier_cache(session)

            return self._tier_cache.get(tier_id)

        except Exception as e:
            logger.error(f"Failed to get tier plan {tier_id}: {e}")
            return None

    async def _refresh_tier_cache(self, session: Session):
        """Refresh tier plans cache from database"""
        try:
            result = session.execute(
                select(TierPlan).where(TierPlan.is_active == True)
            )
            tier_plans = result.scalars().all()

            self._tier_cache = {tier.id: tier for tier in tier_plans}
            self._cache_timestamp = datetime.utcnow()

            logger.info(f"Tier cache refreshed with {len(tier_plans)} active plans")

        except Exception as e:
            logger.error(f"Failed to refresh tier cache: {e}")

    async def get_all_active_tiers(self, session: Session, public_only: bool = False) -> List[TierPlan]:
        """Get all active tier plans"""
        try:
            query = select(TierPlan).where(TierPlan.is_active == True)

            if public_only:
                query = query.where(TierPlan.is_public == True)

            query = query.order_by(TierPlan.sort_order)

            result = session.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get active tiers: {e}")
            return []

    async def get_user_tier(self, user_id: str, session: Session) -> Optional[TierPlan]:
        """Get user's current tier plan"""
        try:
            result = session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"User {user_id} not found")
                return None

            return await self.get_tier_plan(user.tier_id, session)

        except Exception as e:
            logger.error(f"Failed to get user tier for {user_id}: {e}")
            return None

    async def check_storage_quota(
        self,
        user_id: str,
        file_size_bytes: int,
        session: Session,
        raise_on_exceed: bool = True
    ) -> bool:
        """
        Check if user has enough storage quota for a new file

        Args:
            user_id: User ID
            file_size_bytes: Size of file to be uploaded
            session: Database session
            raise_on_exceed: If True, raises TierLimitExceeded on quota exceeded

        Returns:
            True if within quota, False otherwise

        Raises:
            TierLimitExceeded: If raise_on_exceed=True and quota exceeded
        """
        try:
            # Check if user is admin - admins have unlimited storage
            result = session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if user and user.is_admin:
                logger.debug(f"Admin user {user_id} bypassing storage quota check")
                return True

            # Get user's tier
            tier = await self.get_user_tier(user_id, session)
            if not tier:
                logger.error(f"Could not determine tier for user {user_id}")
                return False

            # Check file size limit
            if file_size_bytes > tier.max_file_size_bytes:
                msg = f"File size ({file_size_bytes / (1024*1024):.1f} MB) exceeds tier limit ({tier.max_file_size_bytes / (1024*1024):.1f} MB)"
                if raise_on_exceed:
                    raise TierLimitExceeded(
                        msg, "file_size",
                        file_size_bytes, tier.max_file_size_bytes
                    )
                logger.warning(f"User {user_id}: {msg}")
                return False

            # Get or create storage quota record
            result = session.execute(
                select(UserStorageQuota).where(UserStorageQuota.user_id == user_id)
            )
            quota = result.scalar_one_or_none()

            if not quota:
                # Create new quota record
                quota = UserStorageQuota(
                    user_id=user_id,
                    tier_id=tier.id,
                    total_quota_bytes=tier.storage_quota_bytes,
                    used_bytes=0,
                    document_count=0
                )
                session.add(quota)
                session.flush()

            # Check if adding this file would exceed quota
            new_total = quota.used_bytes + file_size_bytes

            if new_total > quota.total_quota_bytes:
                msg = f"Storage quota exceeded: {new_total / (1024*1024):.1f} MB would exceed limit of {quota.total_quota_bytes / (1024*1024):.1f} MB"
                if raise_on_exceed:
                    raise TierLimitExceeded(
                        msg, "storage_quota",
                        new_total, quota.total_quota_bytes
                    )
                logger.warning(f"User {user_id}: {msg}")
                return False

            return True

        except TierLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"Failed to check storage quota for user {user_id}: {e}")
            return False

    async def check_document_count_limit(
        self,
        user_id: str,
        session: Session,
        raise_on_exceed: bool = True
    ) -> bool:
        """
        Check if user can upload more documents

        Returns:
            True if can upload more, False otherwise
        """
        try:
            # Check if user is admin - admins have unlimited documents
            result = session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if user and user.is_admin:
                logger.debug(f"Admin user {user_id} bypassing document count limit check")
                return True

            # Get user's tier
            tier = await self.get_user_tier(user_id, session)
            if not tier:
                return False

            # If tier has no document limit, always allow
            if tier.max_documents is None:
                return True

            # Count user's documents
            result = session.execute(
                select(func.count(Document.id)).where(Document.user_id == user_id)
            )
            doc_count = result.scalar()

            if doc_count >= tier.max_documents:
                msg = f"Document limit reached: {doc_count} documents (limit: {tier.max_documents})"
                if raise_on_exceed:
                    raise TierLimitExceeded(
                        msg, "document_count",
                        doc_count, tier.max_documents
                    )
                logger.warning(f"User {user_id}: {msg}")
                return False

            return True

        except TierLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"Failed to check document count for user {user_id}: {e}")
            return False

    async def check_feature_access(
        self,
        user_id: str,
        feature: str,
        session: Session
    ) -> bool:
        """
        Check if user's tier has access to a specific feature

        Args:
            user_id: User ID
            feature: Feature name (e.g., 'bulk_operations', 'api_access', 'priority_support')
            session: Database session

        Returns:
            True if feature is enabled for user's tier, False otherwise
        """
        try:
            # Check if user is admin - admins have all features
            result = session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if user and user.is_admin:
                logger.debug(f"Admin user {user_id} granted feature access: {feature}")
                return True

            tier = await self.get_user_tier(user_id, session)
            if not tier:
                return False

            # Map feature names to tier plan columns
            feature_map = {
                'bulk_operations': tier.bulk_operations_enabled,
                'api_access': tier.api_access_enabled,
                'priority_support': tier.priority_support,
            }

            return feature_map.get(feature, False)

        except Exception as e:
            logger.error(f"Failed to check feature access for user {user_id}, feature {feature}: {e}")
            return False

    async def update_storage_usage(
        self,
        user_id: str,
        file_size_bytes: int,
        session: Session,
        increment: bool = True
    ):
        """
        Update user's storage usage after upload/delete

        Args:
            user_id: User ID
            file_size_bytes: Size of file being added or removed
            session: Database session
            increment: True to add storage, False to subtract
        """
        try:
            result = session.execute(
                select(UserStorageQuota).where(UserStorageQuota.user_id == user_id)
            )
            quota = result.scalar_one_or_none()

            if not quota:
                # Get user's tier to create quota record
                tier = await self.get_user_tier(user_id, session)
                if not tier:
                    logger.error(f"Cannot create quota for user {user_id}: tier not found")
                    return

                quota = UserStorageQuota(
                    user_id=user_id,
                    tier_id=tier.id,
                    total_quota_bytes=tier.storage_quota_bytes,
                    used_bytes=0,
                    document_count=0
                )
                session.add(quota)

            # Update storage
            if increment:
                quota.used_bytes += file_size_bytes
                quota.document_count += 1
                if file_size_bytes > quota.largest_file_bytes:
                    quota.largest_file_bytes = file_size_bytes
            else:
                quota.used_bytes = max(0, quota.used_bytes - file_size_bytes)
                quota.document_count = max(0, quota.document_count - 1)

            quota.last_calculated_at = datetime.utcnow()
            session.commit()

            logger.info(f"Updated storage for user {user_id}: {'+' if increment else '-'}{file_size_bytes} bytes")

        except Exception as e:
            logger.error(f"Failed to update storage usage for user {user_id}: {e}")
            session.rollback()

    async def upgrade_user_tier(
        self,
        user_id: str,
        new_tier_id: int,
        session: Session
    ) -> bool:
        """
        Upgrade/downgrade user's tier

        Args:
            user_id: User ID
            new_tier_id: New tier ID
            session: Database session

        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify new tier exists
            new_tier = await self.get_tier_plan(new_tier_id, session)
            if not new_tier:
                logger.error(f"Tier {new_tier_id} not found")
                return False

            # Update user tier
            result = session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {user_id} not found")
                return False

            old_tier_id = user.tier_id
            user.tier_id = new_tier_id

            # Update storage quota
            result = session.execute(
                select(UserStorageQuota).where(UserStorageQuota.user_id == user_id)
            )
            quota = result.scalar_one_or_none()

            if quota:
                quota.tier_id = new_tier_id
                quota.total_quota_bytes = new_tier.storage_quota_bytes
            else:
                # Create quota record if it doesn't exist
                quota = UserStorageQuota(
                    user_id=user_id,
                    tier_id=new_tier_id,
                    total_quota_bytes=new_tier.storage_quota_bytes,
                    used_bytes=0,
                    document_count=0
                )
                session.add(quota)

            session.commit()

            logger.info(f"User {user_id} tier changed from {old_tier_id} to {new_tier_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to upgrade user {user_id} tier: {e}")
            session.rollback()
            return False

    async def get_user_quota_info(self, user_id: str, session: Session) -> Optional[Dict[str, Any]]:
        """
        Get user's current quota information

        Returns:
            Dictionary with quota details or None if not found
        """
        try:
            tier = await self.get_user_tier(user_id, session)
            if not tier:
                return None

            result = session.execute(
                select(UserStorageQuota).where(UserStorageQuota.user_id == user_id)
            )
            quota = result.scalar_one_or_none()

            if not quota:
                return {
                    'tier_id': tier.id,
                    'tier_name': tier.display_name,
                    'used_bytes': 0,
                    'total_bytes': tier.storage_quota_bytes,
                    'used_percentage': 0,
                    'document_count': 0,
                    'max_documents': tier.max_documents,
                    'max_file_size_bytes': tier.max_file_size_bytes,
                    'features': {
                        'bulk_operations': tier.bulk_operations_enabled,
                        'api_access': tier.api_access_enabled,
                        'priority_support': tier.priority_support,
                    }
                }

            return {
                'tier_id': tier.id,
                'tier_name': tier.display_name,
                'used_bytes': quota.used_bytes,
                'total_bytes': quota.total_quota_bytes,
                'used_percentage': (quota.used_bytes / quota.total_quota_bytes * 100) if quota.total_quota_bytes > 0 else 0,
                'document_count': quota.document_count,
                'max_documents': tier.max_documents,
                'max_file_size_bytes': tier.max_file_size_bytes,
                'largest_file_bytes': quota.largest_file_bytes,
                'features': {
                    'bulk_operations': tier.bulk_operations_enabled,
                    'api_access': tier.api_access_enabled,
                    'priority_support': tier.priority_support,
                }
            }

        except Exception as e:
            logger.error(f"Failed to get quota info for user {user_id}: {e}")
            return None


# Global service instance
tier_service = TierService()
