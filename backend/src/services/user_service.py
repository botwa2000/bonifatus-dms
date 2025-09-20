# backend/src/services/user_service.py

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from src.database.models import User, Document, Category, UserSettings, UserActivity

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Get complete user profile information"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            settings = (
                self.db.query(UserSettings)
                .filter(UserSettings.user_id == user_id)
                .first()
            )

            profile_data = {
                "timezone": settings.timezone if settings else "UTC",
                "language": settings.language if settings else "en",
                "notification_preferences": (
                    settings.notification_preferences if settings else {}
                ),
                "created_at": user.created_at.isoformat(),
                "last_login_at": (
                    user.last_login_at.isoformat() if user.last_login_at else None
                ),
            }

            storage_usage = self._calculate_storage_usage(user_id)
            subscription_status = self._get_subscription_status(user)

            return {
                "success": True,
                "profile": profile_data,
                "storage_usage": storage_usage,
                "subscription_status": subscription_status,
            }

        except Exception as e:
            logger.error(f"Get user profile failed: {e}")
            return {"success": False, "error": "Failed to retrieve profile"}

    def update_user_profile(
        self, user_id: int, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user profile information"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            if "full_name" in updates:
                user.full_name = updates["full_name"]

            settings = (
                self.db.query(UserSettings)
                .filter(UserSettings.user_id == user_id)
                .first()
            )

            if not settings:
                settings = UserSettings(user_id=user_id)
                self.db.add(settings)

            if "timezone" in updates:
                settings.timezone = updates["timezone"]
            if "language" in updates:
                settings.language = updates["language"]
            if "notification_preferences" in updates:
                settings.notification_preferences = updates["notification_preferences"]

            user.updated_at = datetime.utcnow()
            self.db.commit()

            self._log_user_activity(user_id, "profile_updated", {"updates": list(updates.keys())})

            return {"success": True}

        except Exception as e:
            logger.error(f"Update user profile failed: {e}")
            self.db.rollback()
            return {"success": False, "error": "Failed to update profile"}

    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Get user settings and preferences"""
        try:
            settings = (
                self.db.query(UserSettings)
                .filter(UserSettings.user_id == user_id)
                .first()
            )

            if not settings:
                return {
                    "auto_categorization_enabled": True,
                    "ocr_enabled": True,
                    "documents_per_page": 20,
                    "default_view": "grid",
                    "theme": "light",
                    "timezone": "UTC",
                    "language": "en",
                    "notification_preferences": {},
                }

            return {
                "auto_categorization_enabled": settings.auto_categorization_enabled,
                "ocr_enabled": settings.ocr_enabled,
                "documents_per_page": settings.documents_per_page,
                "default_view": settings.default_view,
                "theme": settings.theme,
                "timezone": settings.timezone,
                "language": settings.language,
                "notification_preferences": settings.notification_preferences or {},
            }

        except Exception as e:
            logger.error(f"Get user settings failed: {e}")
            return {}

    def update_user_settings(
        self, user_id: int, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user settings and preferences"""
        try:
            settings = (
                self.db.query(UserSettings)
                .filter(UserSettings.user_id == user_id)
                .first()
            )

            if not settings:
                settings = UserSettings(user_id=user_id)
                self.db.add(settings)

            for field, value in updates.items():
                if hasattr(settings, field):
                    setattr(settings, field, value)

            settings.updated_at = datetime.utcnow()
            self.db.commit()

            self._log_user_activity(user_id, "settings_updated", {"updates": list(updates.keys())})

            return {"success": True}

        except Exception as e:
            logger.error(f"Update user settings failed: {e}")
            self.db.rollback()
            return {"success": False, "error": "Failed to update settings"}

    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user usage statistics"""
        try:
            total_documents = (
                self.db.query(Document)
                .filter(Document.user_id == user_id)
                .count()
            )

            total_storage = (
                self.db.query(func.sum(Document.file_size_bytes))
                .filter(Document.user_id == user_id)
                .scalar() or 0
            )

            documents_by_status = (
                self.db.query(Document.status, func.count())
                .filter(Document.user_id == user_id)
                .group_by(Document.status)
                .all()
            )

            recent_uploads = (
                self.db.query(func.count())
                .filter(
                    Document.user_id == user_id,
                    Document.created_at >= datetime.utcnow() - timedelta(days=30)
                )
                .scalar() or 0
            )

            most_used_categories = (
                self.db.query(Category.name_en, func.count(Document.id))
                .join(Document, Category.id == Document.category_id)
                .filter(Document.user_id == user_id)
                .group_by(Category.id, Category.name_en)
                .order_by(desc(func.count(Document.id)))
                .limit(5)
                .all()
            )

            return {
                "total_documents": total_documents,
                "total_storage_bytes": total_storage,
                "storage_formatted": self._format_file_size(total_storage),
                "documents_by_status": {
                    str(status): count for status, count in documents_by_status
                },
                "recent_uploads_30_days": recent_uploads,
                "most_used_categories": [
                    {"name": name, "count": count}
                    for name, count in most_used_categories
                ],
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Get user statistics failed: {e}")
            return {}

    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """Export user data for GDPR compliance"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            documents = (
                self.db.query(Document).filter(Document.user_id == user_id).all()
            )

            categories = (
                self.db.query(Category).filter(Category.user_id == user_id).all()
            )

            settings = (
                self.db.query(UserSettings)
                .filter(UserSettings.user_id == user_id)
                .first()
            )

            export_data = {
                "user_profile": {
                    "email": user.email,
                    "full_name": user.full_name,
                    "tier": user.tier.value,
                    "created_at": user.created_at.isoformat(),
                    "last_login_at": (
                        user.last_login_at.isoformat() if user.last_login_at else None
                    ),
                },
                "documents": [
                    {
                        "filename": doc.filename,
                        "title": doc.title,
                        "description": doc.description,
                        "created_at": doc.created_at.isoformat(),
                        "file_size_bytes": doc.file_size_bytes,
                        "mime_type": doc.mime_type,
                        "status": doc.status.value,
                        "extracted_keywords": doc.extracted_keywords,
                        "language_detected": doc.language_detected,
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
                        "keywords": cat.keywords,
                    }
                    for cat in categories
                ],
                "settings": (
                    {
                        "auto_categorization_enabled": settings.auto_categorization_enabled,
                        "ocr_enabled": settings.ocr_enabled,
                        "documents_per_page": settings.documents_per_page,
                        "default_view": settings.default_view,
                        "theme": settings.theme,
                        "timezone": settings.timezone,
                        "language": settings.language,
                        "notification_preferences": settings.notification_preferences,
                    }
                    if settings
                    else {}
                ),
            }

            self._log_user_activity(user_id, "data_exported", {})

            return {
                "success": True,
                "export_data": export_data,
                "exported_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Export user data failed: {e}")
            return {"success": False, "error": "Failed to export data"}

    def delete_user_account(self, user_id: int) -> Dict[str, Any]:
        """Delete user account and all associated data"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            self.db.query(Document).filter(Document.user_id == user_id).delete()
            self.db.query(Category).filter(Category.user_id == user_id).delete()
            self.db.query(UserSettings).filter(UserSettings.user_id == user_id).delete()
            self.db.query(UserActivity).filter(UserActivity.user_id == user_id).delete()

            self.db.delete(user)
            self.db.commit()

            logger.info(f"User account {user_id} deleted successfully")

            return {
                "success": True,
                "deleted_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Delete user account failed: {e}")
            self.db.rollback()
            return {"success": False, "error": "Failed to delete account"}

    def get_user_activity(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user activity log"""
        try:
            activities = (
                self.db.query(UserActivity)
                .filter(UserActivity.user_id == user_id)
                .order_by(desc(UserActivity.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": activity.id,
                    "action": activity.action,
                    "details": activity.details,
                    "ip_address": activity.ip_address,
                    "user_agent": activity.user_agent,
                    "created_at": activity.created_at.isoformat(),
                }
                for activity in activities
            ]

        except Exception as e:
            logger.error(f"Get user activity failed: {e}")
            return []

    def submit_feedback(self, user_id: int, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Submit user feedback"""
        try:
            feedback_data = {
                "user_id": user_id,
                "type": feedback.get("type", "general"),
                "rating": feedback.get("rating"),
                "message": feedback.get("message", ""),
                "page": feedback.get("page"),
                "feature": feedback.get("feature"),
            }

            self._log_user_activity(
                user_id, "feedback_submitted", {"type": feedback_data["type"]}
            )

            logger.info(f"Feedback submitted by user {user_id}: {feedback_data['type']}")

            return {
                "success": True,
                "feedback_id": f"feedback_{user_id}_{datetime.now().timestamp()}",
            }

        except Exception as e:
            logger.error(f"Submit feedback failed: {e}")
            return {"success": False, "error": "Failed to submit feedback"}

    def _calculate_storage_usage(self, user_id: int) -> Dict[str, Any]:
        """Calculate user's storage usage"""
        try:
            total_size = (
                self.db.query(func.sum(Document.file_size_bytes))
                .filter(Document.user_id == user_id)
                .scalar() or 0
            )

            document_count = (
                self.db.query(Document)
                .filter(Document.user_id == user_id)
                .count()
            )

            return {
                "total_bytes": total_size,
                "total_formatted": self._format_file_size(total_size),
                "document_count": document_count,
                "average_file_size": (
                    total_size // document_count if document_count > 0 else 0
                ),
            }

        except Exception as e:
            logger.error(f"Calculate storage usage failed: {e}")
            return {
                "total_bytes": 0,
                "total_formatted": "0 B",
                "document_count": 0,
                "average_file_size": 0,
            }

    def _get_subscription_status(self, user: User) -> Dict[str, Any]:
        """Get user's subscription status"""
        try:
            return {
                "tier": user.tier.value,
                "is_active": True,
                "expires_at": None,
                "features": self._get_tier_features(user.tier.value),
            }

        except Exception as e:
            logger.error(f"Get subscription status failed: {e}")
            return {
                "tier": "free",
                "is_active": True,
                "expires_at": None,
                "features": [],
            }

    def _get_tier_features(self, tier: str) -> List[str]:
        """Get features available for user tier"""
        if tier == "premium":
            return [
                "unlimited_storage",
                "advanced_search",
                "ai_categorization",
                "priority_support",
                "api_access",
            ]
        elif tier == "pro":
            return [
                "extended_storage",
                "advanced_search",
                "ai_categorization",
                "email_support",
            ]
        else:  # free
            return [
                "basic_storage",
                "basic_search",
                "manual_categorization",
            ]

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        try:
            if size_bytes == 0:
                return "0 B"

            size_names = ["B", "KB", "MB", "GB", "TB"]
            import math
            i = int(math.floor(math.log(size_bytes, 1024)))
            power = math.pow(1024, i)
            size = round(size_bytes / power, 2)
            return f"{size} {size_names[i]}"

        except Exception:
            return f"{size_bytes} B"

    def _log_user_activity(
        self, user_id: int, action: str, details: Dict[str, Any]
    ):
        """Log user activity"""
        try:
            activity = UserActivity(
                user_id=user_id,
                action=action,
                details=details,
                ip_address="127.0.0.1",  # Would be populated from request
                user_agent="Unknown",     # Would be populated from request
            )

            self.db.add(activity)
            self.db.commit()

        except Exception as e:
            logger.warning(f"Failed to log user activity: {e}")
            self.db.rollback()