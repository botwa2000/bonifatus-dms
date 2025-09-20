# backend/src/services/user_service.py
"""
Bonifatus DMS - User Service
User profile management, statistics, and tier operations
Data export, account deletion, and usage analytics
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta, timezone
import json
import csv
import io

from src.database.models import (
    User,
    UserSettings,
    Document,
    Category,
    AuditLog,
    UserTier,
)
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UserService:
    """Service for user profile and account management operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_complete_profile(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive user profile with statistics and tier info
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {}

            # Get tier limits
            tier_limits = self._get_tier_limits(user.tier)

            # Get trial information
            trial_info = self._get_trial_info(user)

            # Get usage statistics
            statistics = self.get_usage_statistics(user_id, "month")

            return {
                "tier_limits": tier_limits,
                "trial_info": trial_info,
                "statistics": statistics,
            }

        except Exception as e:
            logger.error(f"Failed to get complete profile for user {user_id}: {e}")
            return {}

    def get_usage_statistics(self, user_id: int, period: str = "month") -> Dict[str, Any]:
        """
        Get detailed usage statistics for specified period
        FIXED: Removed async - this method doesn't need to be async
        """
        try:
            # Calculate date range
            now = datetime.utcnow()
            if period == "week":
                start_date = now - timedelta(days=7)
            elif period == "month":
                start_date = now - timedelta(days=30)
            elif period == "year":
                start_date = now - timedelta(days=365)
            else:  # all
                start_date = datetime.min

            # Document statistics
            total_documents = (
                self.db.query(Document).filter(Document.user_id == user_id).count()
            )

            period_documents = (
                self.db.query(Document)
                .filter(
                    and_(Document.user_id == user_id, Document.created_at >= start_date)
                )
                .count()
            )

            # Storage statistics
            storage_query = self.db.query(
                func.coalesce(func.sum(Document.file_size_bytes), 0).label(
                    "total_storage"
                )
            ).filter(Document.user_id == user_id)

            total_storage = storage_query.scalar() or 0

            # Category usage
            category_stats = (
                self.db.query(
                    Category.name_en,
                    Category.color,
                    func.count(Document.id).label("document_count"),
                )
                .outerjoin(
                    Document,
                    and_(
                        Document.category_id == Category.id, Document.user_id == user_id
                    ),
                )
                .filter(
                    or_(
                        Category.user_id == user_id, Category.is_system_category == True
                    )
                )
                .group_by(Category.id, Category.name_en, Category.color)
                .all()
            )

            # Recent activity
            recent_uploads = (
                self.db.query(Document)
                .filter(
                    and_(
                        Document.user_id == user_id,
                        Document.created_at >= now - timedelta(days=7),
                    )
                )
                .order_by(desc(Document.created_at))
                .limit(10)
                .all()
            )

            # Most viewed documents
            popular_docs = (
                self.db.query(Document)
                .filter(Document.user_id == user_id)
                .order_by(desc(Document.view_count))
                .limit(5)
                .all()
            )

            return {
                "period": period,
                "documents": {
                    "total": total_documents,
                    "period_uploads": period_documents,
                    "storage_bytes": total_storage,
                    "storage_mb": round(total_storage / (1024 * 1024), 2),
                },
                "categories": [
                    {
                        "name": cat.name_en,
                        "color": cat.color,
                        "document_count": cat.document_count,
                    }
                    for cat in category_stats
                ],
                "recent_activity": [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "title": doc.title,
                        "uploaded_at": doc.created_at.isoformat(),
                    }
                    for doc in recent_uploads
                ],
                "popular_documents": [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "title": doc.title,
                        "view_count": doc.view_count,
                    }
                    for doc in popular_docs
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get usage statistics for user {user_id}: {e}")
            return {}

    def start_premium_trial(self, user_id: int) -> Dict[str, Any]:
        """
        Start premium trial for eligible user
        FIXED: Removed async - doesn't need to be async
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            if user.tier != UserTier.FREE:
                return {
                    "success": False,
                    "error": "Trial only available for free users",
                }

            if user.trial_started_at:
                return {"success": False, "error": "Trial already used"}

            # Start trial
            trial_start = datetime.utcnow()
            trial_end = trial_start + timedelta(days=30)

            user.tier = UserTier.PREMIUM_TRIAL
            user.trial_started_at = trial_start
            user.trial_ended_at = trial_end

            self.db.commit()

            logger.info(f"Started premium trial for user {user_id}")
            return {"success": True, "trial_ends_at": trial_end.isoformat()}

        except Exception as e:
            logger.error(f"Failed to start premium trial for user {user_id}: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def export_user_data(self, user_id: int, format: str = "json") -> Dict[str, Any]:
        """
        Export all user data for GDPR compliance
        FIXED: Removed async - doesn't need to be async
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Get all user documents
            documents = (
                self.db.query(Document)
                .filter(Document.user_id == user_id)
                .all()
            )

            # Get user categories
            categories = (
                self.db.query(Category)
                .filter(Category.user_id == user_id)
                .all()
            )

            # Get user settings
            settings = (
                self.db.query(UserSettings)
                .filter(UserSettings.user_id == user_id)
                .first()
            )

            # Prepare export data
            export_data = {
                "user_profile": {
                    "email": user.email,
                    "full_name": user.full_name,
                    "tier": user.tier.value,
                    "created_at": user.created_at.isoformat(),
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                },
                "documents": [
                    {
                        "filename": doc.filename,
                        "title": doc.title,
                        "description": doc.description,
                        "created_at": doc.created_at.isoformat(),
                        "file_size_bytes": doc.file_size_bytes,
                    }
                    for doc in documents
                ],
                "categories": [
                    {
                        "name_en": cat.name_en,
                        "name_de": cat.name_de,
                        "description_en": cat.description_en,
                        "description_de": cat.description_de,
                        "color": cat.color,
                    }
                    for cat in categories
                ],
                "settings": {
                    "auto_categorization_enabled": settings.auto_categorization_enabled if settings else True,
                    "ocr_enabled": settings.ocr_enabled if settings else True,
                    "documents_per_page": settings.documents_per_page if settings else 20,
                } if settings else {},
            }

            if format == "csv":
                # Convert to CSV format
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write documents CSV
                writer.writerow(["Type", "Filename", "Title", "Created At", "Size"])
                for doc in documents:
                    writer.writerow([
                        "Document",
                        doc.filename,
                        doc.title,
                        doc.created_at.isoformat(),
                        doc.file_size_bytes
                    ])
                
                return {
                    "success": True,
                    "format": "csv",
                    "data": output.getvalue(),
                    "filename": f"user_data_{user_id}.csv"
                }
            else:
                return {
                    "success": True,
                    "format": "json",
                    "data": export_data,
                    "filename": f"user_data_{user_id}.json"
                }

        except Exception as e:
            logger.error(f"Failed to export user data for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    async def delete_user_account(
        self, user_id: int, delete_google_drive_files: bool = False
    ) -> Dict[str, Any]:
        """
        Permanently delete user account and all associated data
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Count items to be deleted for reporting
            document_count = (
                self.db.query(Document).filter(Document.user_id == user_id).count()
            )

            category_count = (
                self.db.query(Category).filter(Category.user_id == user_id).count()
            )

            drive_files_deleted = 0

            # Delete from Google Drive if requested
            if delete_google_drive_files:
                try:
                    from src.integrations.google_drive import GoogleDriveClient

                    drive_client = GoogleDriveClient(user_id, self.db)

                    # Get all user documents with Google Drive file IDs
                    documents = (
                        self.db.query(Document)
                        .filter(
                            and_(
                                Document.user_id == user_id,
                                Document.google_drive_file_id.isnot(None),
                            )
                        )
                        .all()
                    )

                    for doc in documents:
                        if await drive_client.delete_file(doc.google_drive_file_id):
                            drive_files_deleted += 1

                except Exception as drive_error:
                    logger.warning(
                        f"Google Drive deletion failed for user {user_id}: {drive_error}"
                    )

            # Delete database records (cascade will handle related data)
            self.db.delete(user)
            self.db.commit()

            logger.info(
                f"Deleted user account {user_id} with {document_count} documents"
            )

            return {
                "success": True,
                "deleted_documents": document_count,
                "deleted_categories": category_count,
                "google_drive_files_deleted": drive_files_deleted,
            }

        except Exception as e:
            logger.error(f"Failed to delete user account {user_id}: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _get_tier_limits(self, tier: UserTier) -> Dict[str, int]:
        """
        Get tier-specific limits and quotas
        """
        limits = {
            UserTier.FREE: {
                "document_limit": 100,
                "monthly_uploads": 50,
                "max_file_size_mb": 50,
                "custom_categories": 10,
                "ai_processing": 10,
            },
            UserTier.PREMIUM_TRIAL: {
                "document_limit": 500,
                "monthly_uploads": 200,
                "max_file_size_mb": 100,
                "custom_categories": 25,
                "ai_processing": 50,
            },
            UserTier.PREMIUM: {
                "document_limit": 0,  # Unlimited
                "monthly_uploads": 0,  # Unlimited
                "max_file_size_mb": 200,
                "custom_categories": 100,
                "ai_processing": 0,  # Unlimited
            },
            UserTier.ADMIN: {
                "document_limit": 0,  # Unlimited
                "monthly_uploads": 0,  # Unlimited
                "max_file_size_mb": 500,
                "custom_categories": 0,  # Unlimited
                "ai_processing": 0,  # Unlimited
            },
        }

        return limits.get(tier, limits[UserTier.FREE])

    def _get_trial_info(self, user: User) -> Dict[str, Any]:
        """
        Get trial status and information
        """
        if not user.trial_started_at:
            return {
                "has_used_trial": False,
                "trial_available": user.tier == UserTier.FREE,
            }

        now = datetime.utcnow()
        is_trial_active = (
            user.tier == UserTier.PREMIUM_TRIAL
            and user.trial_ended_at
            and now < user.trial_ended_at
        )

        days_remaining = 0
        if is_trial_active and user.trial_ended_at:
            days_remaining = (user.trial_ended_at - now).days

        return {
            "has_used_trial": True,
            "trial_available": False,
            "trial_active": is_trial_active,
            "trial_started": user.trial_started_at.isoformat(),
            "trial_ends": (
                user.trial_ended_at.isoformat() if user.trial_ended_at else None
            ),
            "days_remaining": max(0, days_remaining),
        }

    def _format_data_as_csv(self, data: Dict[str, Any]) -> str:
        """
        Format exported data as CSV string
        """
        try:
            output = io.StringIO()

            # Write profile data
            output.write("=== USER PROFILE ===\n")
            profile_writer = csv.writer(output)
            profile_writer.writerow(["Field", "Value"])

            for key, value in data.get("profile", {}).items():
                profile_writer.writerow([key, str(value)])

            # Write documents data
            output.write("\n=== DOCUMENTS ===\n")
            if data.get("documents"):
                doc_writer = csv.DictWriter(
                    output, fieldnames=data["documents"][0].keys()
                )
                doc_writer.writeheader()
                doc_writer.writerows(data["documents"])

            # Write categories data
            output.write("\n=== CATEGORIES ===\n")
            if data.get("categories"):
                cat_writer = csv.DictWriter(
                    output, fieldnames=data["categories"][0].keys()
                )
                cat_writer.writeheader()
                cat_writer.writerows(data["categories"])

            return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to format data as CSV: {e}")
            return "Error formatting data as CSV"
