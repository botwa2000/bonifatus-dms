# backend/app/services/user_service.py
"""
Bonifatus DMS - User Management Service
Business logic for user profile operations and settings management
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text, or_

from app.database.models import User, UserSetting, AuditLog, Document, Category, SystemSetting
from app.database.connection import db_manager
from app.schemas.user_schemas import (
    UserProfileUpdate, UserProfileResponse, UserStatistics,
    UserPreferences, UserPreferencesUpdate, AccountDeactivationRequest,
    AccountDeactivationResponse, UserDashboard
)
from app.services.tier_service import tier_service

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
        """Get user profile information with monthly usage stats"""
        session = db_manager.session_local()
        try:
            user = session.get(User, user_id)
            if not user:
                return None

            # Get monthly usage information
            monthly_usage = await tier_service.get_monthly_usage_info(user_id, session)

            return UserProfileResponse(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                profile_picture=user.profile_picture,
                tier=user.tier.name if user.tier else "free",
                tier_id=user.tier_id,
                is_active=user.is_active,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
                email_processing_enabled=user.email_processing_enabled,
                email_processing_address=user.email_processing_address,
                monthly_usage=monthly_usage
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
        """Update user profile information, including email and password changes"""
        session = db_manager.session_local()
        try:
            user = session.get(User, user_id)
            if not user:
                return None

            # Check if this is a Google user trying to change email/password
            if user.google_id:
                if profile_update.new_email or profile_update.new_password:
                    raise ValueError("Email and password changes are not allowed for Google-authenticated accounts")

            # Store old values for audit
            old_values = {
                "full_name": user.full_name,
                "profile_picture": user.profile_picture,
                "email": user.email
            }

            # Handle password change if requested
            if profile_update.current_password and profile_update.new_password:
                from app.services.auth_service import auth_service
                # Verify current password
                if not auth_service.verify_password(profile_update.current_password, user.password_hash):
                    raise ValueError("Current password is incorrect")

                # Hash and update new password
                user.password_hash = auth_service.get_password_hash(profile_update.new_password)
                logger.info(f"Password changed for user: {user.email}")

            # Handle email change if requested (non-Google users only)
            old_email = user.email
            if profile_update.new_email and profile_update.new_email != old_email:
                # Check if new email already exists
                existing_user = session.query(User).filter(User.email == profile_update.new_email).first()
                if existing_user:
                    raise ValueError("Email address already in use")

                # Send verification code to new email using existing methods
                from app.services.email_auth_service import email_auth_service
                from app.services.email_service import email_service

                # Generate verification code
                code_result = await email_auth_service.generate_verification_code(
                    user_id=str(user_id),
                    email=profile_update.new_email,
                    purpose='email_change',
                    session=session
                )

                # Send verification email using existing email service method
                await email_service.send_verification_code_email(
                    session=session,
                    to_email=profile_update.new_email,
                    user_name=user.full_name,
                    verification_code=code_result['code']
                )

                logger.info(f"Email change verification sent to {profile_update.new_email} for user {old_email}")

                # Don't update email yet - wait for verification
                # Store pending email in a temp field or return message to user
                raise ValueError(f"Verification code sent to {profile_update.new_email}. Please verify to complete email change.")

            # Update basic profile fields
            update_data = profile_update.dict(exclude_unset=True, exclude={'new_email', 'current_password', 'new_password'})
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

            # Get monthly usage information
            monthly_usage = await tier_service.get_monthly_usage_info(user_id, session)

            return UserProfileResponse(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                profile_picture=user.profile_picture,
                tier=user.tier.name if user.tier else "free",
                tier_id=user.tier_id,
                is_active=user.is_active,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
                email_processing_enabled=user.email_processing_enabled,
                email_processing_address=user.email_processing_address,
                monthly_usage=monthly_usage
            )

        except ValueError as e:
            # Re-raise validation errors with original message
            session.rollback()
            raise e
        except Exception as e:
            logger.error(f"Failed to update user profile {user_id}: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    async def verify_and_change_email(
        self,
        user_id: str,
        new_email: str,
        verification_code: str,
        ip_address: str = None
    ) -> bool:
        """
        Verify email change and update user email
        Also updates the allowed_sender email pair for Pro users with email processing
        """
        session = db_manager.session_local()
        try:
            from app.services.email_auth_service import email_auth_service
            from app.database.auth_models import AllowedSender

            # Verify code
            is_valid = await email_auth_service.verify_code(
                email=new_email,
                code=verification_code,
                purpose='email_change',
                session=session
            )

            if not is_valid:
                return False

            user = session.get(User, user_id)
            if not user:
                return False

            old_email = user.email

            # Update user email
            user.email = new_email
            user.updated_at = datetime.utcnow()

            # Update allowed_sender email pair if email processing is enabled
            if user.email_processing_enabled:
                # Find the allowed sender entry for the old email
                allowed_sender = session.query(AllowedSender).filter(
                    AllowedSender.user_id == user_id,
                    AllowedSender.sender_email == old_email
                ).first()

                if allowed_sender:
                    # Update to new email
                    allowed_sender.sender_email = new_email
                    allowed_sender.sender_name = user.full_name
                    logger.info(f"Updated allowed_sender email pair: {old_email} → {new_email}")
                else:
                    # If no allowed sender exists, create one (shouldn't happen for Pro users, but defensive)
                    allowed_sender = AllowedSender(
                        user_id=user_id,
                        sender_email=new_email,
                        sender_name=user.full_name,
                        is_verified=True,
                        is_active=True,
                        trust_level='high',
                        notes='Created during email change'
                    )
                    session.add(allowed_sender)
                    logger.info(f"Created new allowed_sender for email change: {new_email}")

            session.commit()

            # Log email change
            await self._log_user_action(
                user_id, "email_changed", "user", user_id,
                {"email": old_email}, {"email": new_email}, ip_address, session
            )

            logger.info(f"Email changed from {old_email} to {new_email} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to change email for user {user_id}: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    async def get_user_statistics(self, user_id: str) -> Optional[UserStatistics]:
        """Get user statistics and usage information"""
        session = db_manager.session_local()
        try:
            # Get document count
            documents_stmt = select(func.count(Document.id)).where(Document.user_id == user_id)
            documents_count = session.execute(documents_stmt).scalar() or 0

            # Get total categories count (system + custom)
            total_categories_stmt = select(func.count(Category.id)).where(
                or_(Category.user_id == user_id, Category.is_system == True)
            )
            total_categories_count = session.execute(total_categories_stmt).scalar() or 0

            # Get custom categories count only
            custom_categories_stmt = select(func.count(Category.id)).where(
                Category.user_id == user_id, Category.is_system == False
            )
            custom_categories_count = session.execute(custom_categories_stmt).scalar() or 0

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

            # Get monthly usage information
            monthly_usage = await tier_service.get_monthly_usage_info(user_id, session)

            return UserStatistics(
                documents_count=documents_count,
                total_categories_count=total_categories_count,
                custom_categories_count=custom_categories_count,
                storage_used_mb=storage_used_mb,
                last_activity=last_activity,
                monthly_usage=monthly_usage
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

            # Get user from database for preferred_doc_languages and email_marketing_enabled
            user = session.get(User, user_id)
            if user:
                if user.preferred_doc_languages:
                    preferences['preferred_doc_languages'] = user.preferred_doc_languages
                # Email marketing preference from users table
                preferences['email_marketing_enabled'] = user.email_marketing_enabled

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

            # Handle email_marketing_enabled separately (stored in users table)
            if "email_marketing_enabled" in update_data:
                email_marketing = update_data["email_marketing_enabled"]
                old_values['email_marketing_enabled'] = user.email_marketing_enabled
                user.email_marketing_enabled = email_marketing
                new_values['email_marketing_enabled'] = email_marketing

                # Remove from update_data so it doesn't go to user_settings
                del update_data["email_marketing_enabled"]

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
            from app.database.models import (
                UserSetting, Category, AuditLog, UserCorpusStats,
                KeywordTrainingData, UserDelegate
            )

            user = session.get(User, user_id)
            if not user:
                return None

            user_email = user.email
            user_name = user.full_name

            # Check for and cancel active subscriptions
            from app.database.models import Subscription
            import stripe
            from app.core.config import settings

            active_subscription = session.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status.in_(['active', 'trialing', 'past_due'])
            ).first()

            if active_subscription:
                logger.info(f"Found active subscription {active_subscription.stripe_subscription_id} for user {user_email}")
                try:
                    # Cancel subscription in Stripe
                    stripe.Subscription.modify(
                        active_subscription.stripe_subscription_id,
                        cancel_at_period_end=False  # Cancel immediately
                    )
                    stripe.Subscription.cancel(active_subscription.stripe_subscription_id)
                    logger.info(f"Canceled Stripe subscription {active_subscription.stripe_subscription_id}")

                    # Update subscription in database
                    active_subscription.status = 'canceled'
                    active_subscription.ended_at = datetime.utcnow()
                    active_subscription.canceled_at = datetime.utcnow()
                    session.commit()

                except Exception as stripe_error:
                    logger.error(f"Failed to cancel Stripe subscription: {stripe_error}")
                    # Continue with account deletion even if Stripe cancellation fails

            # Save anonymous deletion feedback for product improvement
            if deactivation_request.reason or deactivation_request.feedback:
                import hashlib
                from app.database.models import AccountDeletionFeedback, Document

                # Create anonymous ID from email hash
                anonymous_id = hashlib.sha256(user_email.encode()).hexdigest()

                # Calculate user metrics
                days_since_registration = (datetime.now(timezone.utc) - user.created_at).days if user.created_at else None
                total_documents = session.query(Document).filter(Document.user_id == user_id).count()

                # Save feedback (persists after user deletion)
                feedback_record = AccountDeletionFeedback(
                    anonymous_id=anonymous_id,
                    tier_at_deletion=user.tier.name if user.tier else 'unknown',
                    days_since_registration=days_since_registration,
                    total_documents_uploaded=total_documents,
                    had_active_subscription=active_subscription is not None,
                    reason_category=deactivation_request.reason,
                    feedback_text=deactivation_request.feedback
                )
                session.add(feedback_record)
                session.flush()  # Save before user deletion
                logger.info(f"Saved anonymous deletion feedback for {user_email}")

            # 1. Delete user settings (not cascade)
            session.query(UserSetting).filter(UserSetting.user_id == user_id).delete()
            logger.info(f"Deleted user settings for {user_email}")

            # 2. Delete custom categories created by user (not cascade)
            session.query(Category).filter(Category.user_id == user_id).delete()
            logger.info(f"Deleted custom categories for {user_email}")

            # 3. Delete all auth-related records (explicit to avoid FK issues)
            from app.database.auth_models import (
                AllowedSender, EmailProcessingLog, EmailSettings,
                EmailRateLimit, EmailVerificationCode, PasswordResetToken,
                RegisteredDevice
            )

            session.query(AllowedSender).filter(AllowedSender.user_id == user_id).delete()
            session.query(EmailProcessingLog).filter(EmailProcessingLog.user_id == user_id).delete()
            session.query(EmailSettings).filter(EmailSettings.user_id == user_id).delete()
            session.query(EmailRateLimit).filter(EmailRateLimit.user_id == user_id).delete()
            session.query(EmailVerificationCode).filter(EmailVerificationCode.user_id == user_id).delete()
            session.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()
            session.query(RegisteredDevice).filter(RegisteredDevice.user_id == user_id).delete()
            logger.info(f"Deleted all auth-related records for {user_email}")

            # 3a. Delete ML/stats tables (explicit to avoid FK issues)
            session.query(UserCorpusStats).filter(UserCorpusStats.user_id == user_id).delete()
            session.query(KeywordTrainingData).filter(KeywordTrainingData.user_id == user_id).delete()
            logger.info(f"Deleted ML/stats records for {user_email}")

            # 3b. Delete delegate relationships (both as owner and delegate)
            session.query(UserDelegate).filter(
                (UserDelegate.owner_user_id == user_id) | (UserDelegate.delegate_user_id == user_id)
            ).delete(synchronize_session=False)
            logger.info(f"Deleted delegate relationships for {user_email}")

            # 4. Delete audit logs for this user (not cascade)
            session.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
            logger.info(f"Deleted audit logs for {user_email}")

            # Send account deletion email notification (GDPR compliance)
            try:
                from app.services.email_service import email_service
                deletion_date = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")
                await email_service.send_account_deleted_notification(
                    session=session,
                    to_email=user_email,
                    user_name=user_name,
                    deletion_date=deletion_date
                )
                logger.info(f"Account deletion email sent to {user_email}")
            except Exception as email_error:
                # Don't fail deletion if email fails, but log it
                logger.error(f"Failed to send account deletion email to {user_email}: {email_error}")

            # 5. Delete user record (cascades to documents, sessions, etc.)
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