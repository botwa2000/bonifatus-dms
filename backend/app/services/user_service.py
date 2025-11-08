# backend/app/services/user_service.py
"""
Bonifatus DMS - User Management Service
Business logic for user profile operations and settings management
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text

from app.database.models import User, UserSetting, AuditLog, Document, Category, SystemSetting
from app.database.connection import db_manager
from app.schemas.user_schemas import (
    UserProfileUpdate, UserProfileResponse, UserStatistics, 
    UserPreferences, UserPreferencesUpdate, AccountDeactivationRequest,
    AccountDeactivationResponse, UserDashboard
)

logger = logging.getLogger(__name__)


class UserService:
    """User management business logic service"""

    def __init__(self):
        self._system_settings_cache = {}
        self._cache_timestamp = None
        self._cache_ttl_seconds = 300  # 5 minutes

    async def _get_system_setting(self, key: str, default: Any = None) -> Any:
        """Get system setting from database with caching"""
        session = db_manager.session_local()
        try:
            # Check cache validity
            if (self._cache_timestamp is None or 
                (datetime.utcnow() - self._cache_timestamp).total_seconds() > self._cache_ttl_seconds):
                await self._refresh_system_settings_cache(session)

            value = self._system_settings_cache.get(key, default)
            
            # Convert string values to appropriate types
            if isinstance(value, str):
                if value.lower() in ('true', 'false'):
                    return value.lower() == 'true'
                try:
                    return int(value)
                except ValueError:
                    try:
                        return float(value)
                    except ValueError:
                        return value
            
            return value

        except Exception as e:
            logger.error(f"Failed to get system setting {key}: {e}")
            return default
        finally:
            session.close()

    async def _refresh_system_settings_cache(self, session: Session):
        """Refresh system settings cache from database"""
        try:
            settings_stmt = select(SystemSetting)
            settings = session.execute(settings_stmt).scalars().all()
            
            self._system_settings_cache = {
                setting.setting_key: setting.setting_value 
                for setting in settings
            }
            self._cache_timestamp = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to refresh system settings cache: {e}")

    async def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences from system settings"""
        default_lang = await self._get_system_setting("default_user_language", "en")
        return {
            "language": default_lang,
            "preferred_doc_languages": [default_lang],  # Default to same as UI language
            "timezone": await self._get_system_setting("default_timezone", "UTC"),
            "notifications_enabled": await self._get_system_setting("default_notifications_enabled", True),
            "auto_categorization": await self._get_system_setting("default_auto_categorization", True)
        }

    async def _get_supported_languages(self) -> List[str]:
        """Get supported languages from system settings"""
        languages_str = await self._get_system_setting("supported_languages", "en,de,ru")
        return [lang.strip() for lang in languages_str.split(",")]

    async def _validate_language(self, language: str) -> bool:
        """Validate language against supported languages from database"""
        supported_languages = await self._get_supported_languages()
        return language in supported_languages

    async def get_user_profile(self, user_id: str) -> Optional[UserProfileResponse]:
        """Get user profile information"""
        session = db_manager.session_local()
        try:
            user = session.get(User, user_id)
            if not user:
                return None

            return UserProfileResponse(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                profile_picture=user.profile_picture,
                tier=user.tier,
                is_active=user.is_active,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at
            )

        except Exception as e:
            logger.error(f"Failed to get user profile {user_id}: {e}")
            return None
        finally:
            session.close()

    async def update_user_profile(
        self, 
        user_id: str, 
        profile_update: UserProfileUpdate,
        ip_address: str = None
    ) -> Optional[UserProfileResponse]:
        """Update user profile information"""
        session = db_manager.session_local()
        try:
            user = session.get(User, user_id)
            if not user:
                return None

            # Store old values for audit
            old_values = {
                "full_name": user.full_name,
                "profile_picture": user.profile_picture
            }

            # Update profile fields
            update_data = profile_update.dict(exclude_unset=True)
            new_values = {}

            for field, value in update_data.items():
                if hasattr(user, field) and value is not None:
                    setattr(user, field, value)
                    new_values[field] = value

            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)

            # Log profile update
            await self._log_user_action(
                user_id, "profile_update", "user", user_id,
                old_values, new_values, ip_address, session
            )

            logger.info(f"User profile updated: {user.email}")

            return UserProfileResponse(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                profile_picture=user.profile_picture,
                tier=user.tier,
                is_active=user.is_active,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at
            )

        except Exception as e:
            logger.error(f"Failed to update user profile {user_id}: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    async def get_user_statistics(self, user_id: str) -> Optional[UserStatistics]:
        """Get user statistics and usage information"""
        session = db_manager.session_local()
        try:
            # Get document count
            documents_stmt = select(func.count(Document.id)).where(Document.user_id == user_id)
            documents_count = session.execute(documents_stmt).scalar() or 0

            # Get custom categories count
            categories_stmt = select(func.count(Category.id)).where(
                Category.user_id == user_id, Category.is_system == False
            )
            categories_count = session.execute(categories_stmt).scalar() or 0

            # Get storage used (sum of file sizes)
            storage_stmt = select(func.coalesce(func.sum(Document.file_size), 0)).where(
                Document.user_id == user_id
            )
            storage_used_bytes = session.execute(storage_stmt).scalar() or 0
            storage_used_mb = int(storage_used_bytes / (1024 * 1024))

            # Get last activity from audit logs
            last_activity_stmt = select(func.max(AuditLog.created_at)).where(
                AuditLog.user_id == user_id
            )
            last_activity = session.execute(last_activity_stmt).scalar()

            return UserStatistics(
                documents_count=documents_count,
                categories_count=categories_count,
                storage_used_mb=storage_used_mb,
                last_activity=last_activity
            )

        except Exception as e:
            logger.error(f"Failed to get user statistics {user_id}: {e}")
            return None
        finally:
            session.close()

    async def get_user_preferences(self, user_id: str) -> UserPreferences:
        """Get user preferences with defaults from system settings"""
        session = db_manager.session_local()
        try:
            preferences = {}

            # Get user from database for preferred_doc_languages
            user = session.get(User, user_id)
            if user and user.preferred_doc_languages:
                preferences['preferred_doc_languages'] = user.preferred_doc_languages

            # Get user settings from database
            settings_stmt = select(UserSetting).where(UserSetting.user_id == user_id)
            user_settings = session.execute(settings_stmt).scalars().all()

            for setting in user_settings:
                if setting.data_type == "boolean":
                    preferences[setting.setting_key] = setting.setting_value.lower() == "true"
                elif setting.data_type == "integer":
                    preferences[setting.setting_key] = int(setting.setting_value)
                else:
                    preferences[setting.setting_key] = setting.setting_value

            # Apply defaults from system settings for missing preferences
            default_preferences = await self._get_default_preferences()
            final_preferences = {**default_preferences, **preferences}

            return UserPreferences(**final_preferences)

        except Exception as e:
            logger.error(f"Failed to get user preferences {user_id}: {e}")
            default_preferences = await self._get_default_preferences()
            return UserPreferences(**default_preferences)
        finally:
            session.close()

    async def update_user_preferences(
        self,
        user_id: str,
        preferences_update: UserPreferencesUpdate,
        ip_address: str = None
    ) -> Optional[UserPreferences]:
        """Update user preferences with validation from system settings"""
        session = db_manager.session_local()
        try:
            update_data = preferences_update.dict(exclude_unset=True)
            old_values = {}
            new_values = {}

            # Get user for preferred_doc_languages update
            user = session.get(User, user_id)
            if not user:
                raise ValueError("User not found")

            # Handle preferred_doc_languages separately (stored in users table)
            if "preferred_doc_languages" in update_data:
                doc_languages = update_data["preferred_doc_languages"]
                supported_languages = await self._get_supported_languages()

                # Validate each language
                if not isinstance(doc_languages, list) or len(doc_languages) == 0:
                    raise ValueError("At least one document language must be selected")

                for lang in doc_languages:
                    if lang not in supported_languages:
                        raise ValueError(f"Invalid language code '{lang}'. Supported: {', '.join(supported_languages)}")

                # Update users table
                old_values['preferred_doc_languages'] = user.preferred_doc_languages
                user.preferred_doc_languages = doc_languages
                new_values['preferred_doc_languages'] = doc_languages

                # Remove from update_data so it doesn't go to user_settings
                del update_data["preferred_doc_languages"]

            # Validate UI language if provided
            if "language" in update_data:
                if not await self._validate_language(update_data["language"]):
                    supported_languages = await self._get_supported_languages()
                    raise ValueError(f"UI language must be one of: {', '.join(supported_languages)}")

            # Handle other settings (stored in user_settings table)
            for key, value in update_data.items():
                # Get existing setting
                setting_stmt = select(UserSetting).where(
                    UserSetting.user_id == user_id,
                    UserSetting.setting_key == key
                )
                existing_setting = session.execute(setting_stmt).scalar_one_or_none()

                if existing_setting:
                    old_values[key] = existing_setting.setting_value
                    existing_setting.setting_value = str(value)
                    existing_setting.data_type = self._get_data_type(value)
                    existing_setting.updated_at = datetime.utcnow()
                else:
                    old_values[key] = None
                    new_setting = UserSetting(
                        user_id=user_id,
                        setting_key=key,
                        setting_value=str(value),
                        data_type=self._get_data_type(value)
                    )
                    session.add(new_setting)

                new_values[key] = str(value)

            session.commit()

            # Log preferences update
            await self._log_user_action(
                user_id, "preferences_update", "user_settings", user_id,
                old_values, new_values, ip_address, session
            )

            logger.info(f"User preferences updated for user: {user_id}")

            # Return updated preferences
            return await self.get_user_preferences(user_id)

        except Exception as e:
            logger.error(f"Failed to update user preferences {user_id}: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    async def deactivate_user_account(
        self,
        user_id: str,
        deactivation_request: AccountDeactivationRequest,
        ip_address: str = None
    ) -> Optional[AccountDeactivationResponse]:
        """
        Hard delete user account and all associated data

        Deletes:
        - All documents and their metadata (cascades via FK)
        - All user settings
        - All custom categories
        - All sessions (cascades via FK)
        - All audit logs for this user
        - User record itself

        Note: Google Drive files are NOT deleted - user maintains ownership
        """
        session = db_manager.session_local()
        try:
            from app.database.models import UserSetting, Category, AuditLog

            user = session.get(User, user_id)
            if not user:
                return None

            user_email = user.email

            # Log deletion before deleting (will be deleted with audit logs)
            await self._log_user_action(
                user_id, "account_deletion_hard", "user", user_id,
                {"is_active": user.is_active}, {"deleted": True},
                ip_address, session,
                extra_data={
                    "reason": deactivation_request.reason,
                    "feedback": deactivation_request.feedback
                }
            )

            # 1. Delete user settings (not cascade)
            session.query(UserSetting).filter(UserSetting.user_id == user_id).delete()
            logger.info(f"Deleted user settings for {user_email}")

            # 2. Delete custom categories created by user (not cascade)
            session.query(Category).filter(Category.user_id == user_id).delete()
            logger.info(f"Deleted custom categories for {user_email}")

            # 3. Delete audit logs for this user (not cascade)
            session.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
            logger.info(f"Deleted audit logs for {user_email}")

            # 4. Delete user record (cascades to documents, sessions, etc.)
            session.delete(user)
            session.commit()

            logger.info(f"User account HARD DELETED: {user_email}")

            return AccountDeactivationResponse(
                success=True,
                message="Account and all data permanently deleted",
                deactivated_at=datetime.utcnow(),
                data_retention_days=0  # No retention - immediate deletion
            )

        except Exception as e:
            logger.error(f"Failed to delete user account {user_id}: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    async def get_user_dashboard(self, user_id: str) -> Optional[UserDashboard]:
        """Get complete user dashboard data"""
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                return None

            statistics = await self.get_user_statistics(user_id)
            preferences = await self.get_user_preferences(user_id)
            recent_activity = await self._get_recent_activity(user_id)

            return UserDashboard(
                profile=profile,
                statistics=statistics or UserStatistics(
                    documents_count=0, categories_count=0, 
                    storage_used_mb=0, last_activity=None
                ),
                preferences=preferences,
                recent_activity=recent_activity
            )

        except Exception as e:
            logger.error(f"Failed to get user dashboard {user_id}: {e}")
            return None

    async def reset_user_preferences_to_defaults(
        self, 
        user_id: str,
        ip_address: str = None
    ) -> Optional[UserPreferences]:
        """Reset user preferences to system defaults"""
        try:
            default_preferences = await self._get_default_preferences()
            
            # Create preferences update with default values
            default_update = UserPreferencesUpdate(**default_preferences)
            
            return await self.update_user_preferences(user_id, default_update, ip_address)

        except Exception as e:
            logger.error(f"Failed to reset user preferences {user_id}: {e}")
            return None

    async def _get_recent_activity(self, user_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get recent user activity from audit logs"""
        session = db_manager.session_local()
        try:
            if limit is None:
                limit = await self._get_system_setting("default_activity_limit", 10)

            activity_stmt = select(AuditLog).where(
                AuditLog.user_id == user_id
            ).order_by(AuditLog.created_at.desc()).limit(limit)
            
            activities = session.execute(activity_stmt).scalars().all()
            
            return [
                {
                    "action": activity.action,
                    "resource_type": activity.resource_type,
                    "timestamp": activity.created_at.isoformat(),
                    "status": activity.status
                }
                for activity in activities
            ]

        except Exception as e:
            logger.error(f"Failed to get recent activity {user_id}: {e}")
            return []
        finally:
            session.close()

    async def _log_user_action(
        self, user_id: str, action: str, resource_type: str, resource_id: str,
        old_values: Dict, new_values: Dict, ip_address: str, session: Session,
        extra_data: Dict = None
    ):
        """Log user action for audit trail"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                old_values=json.dumps(old_values) if old_values else None,
                new_values=json.dumps(new_values) if new_values else None,
                status="success",
                extra_data=json.dumps(extra_data) if extra_data else None,
                endpoint="/api/v1/users"
            )
            session.add(audit_log)
            session.commit()

        except Exception as e:
            logger.error(f"Failed to log user action: {e}")

    def _get_data_type(self, value: Any) -> str:
        """Determine data type for user setting"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        else:
            return "string"


# Global user service instance
user_service = UserService()