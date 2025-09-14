# backend/src/api/users.py
"""
Bonifatus DMS - Users API
User profile management, settings, and account operations
Tier management and usage statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from src.database import get_db, User, UserSettings, Document, Category
from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()

router = APIRouter()


@router.get("/profile")
async def get_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get current user's complete profile information
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_service = UserService(db)
        profile_data = await user_service.get_complete_profile(user.id)
        
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "tier": user.tier.value,
                "preferred_language": user.preferred_language,
                "timezone": user.timezone,
                "theme": user.theme,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
            },
            "usage": {
                "document_count": user.document_count,
                "monthly_uploads": user.monthly_uploads,
                "storage_used_bytes": user.storage_used_bytes,
                "tier_limits": profile_data["tier_limits"]
            },
            "google_drive": {
                "connected": user.google_drive_connected,
                "folder_id": user.google_drive_folder_id,
                "last_sync": user.last_sync_at.isoformat() if user.last_sync_at else None
            },
            "trial_info": profile_data["trial_info"],
            "statistics": profile_data["statistics"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.put("/profile")
async def update_user_profile(
    full_name: Optional[str] = None,
    preferred_language: Optional[str] = Query(None, regex="^(en|de)$"),
    timezone: Optional[str] = None,
    theme: Optional[str] = Query(None, regex="^(light|dark|auto)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Update user profile information
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Update fields
        if full_name is not None:
            user.full_name = full_name
        if preferred_language is not None:
            user.preferred_language = preferred_language
        if timezone is not None:
            user.timezone = timezone
        if theme is not None:
            user.theme = theme
        
        user.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Profile updated successfully", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/settings")
async def get_user_settings(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get user's application settings and preferences
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Get or create user settings
        user_settings = db.query(UserSettings).filter(
            UserSettings.user_id == user.id
        ).first()
        
        if not user_settings:
            # Create default settings
            user_settings = UserSettings(user_id=user.id)
            db.add(user_settings)
            db.commit()
            db.refresh(user_settings)
        
        return {
            "document_processing": {
                "auto_categorization_enabled": user_settings.auto_categorization_enabled,
                "ocr_enabled": user_settings.ocr_enabled,
                "ai_suggestions_enabled": user_settings.ai_suggestions_enabled
            },
            "notifications": {
                "email_notifications": user_settings.email_notifications,
                "processing_notifications": user_settings.processing_notifications,
                "weekly_summary": user_settings.weekly_summary
            },
            "google_drive": {
                "sync_frequency_minutes": user_settings.sync_frequency_minutes,
                "create_subfolder_structure": user_settings.create_subfolder_structure,
                "backup_enabled": user_settings.backup_enabled
            },
            "ui_preferences": {
                "documents_per_page": user_settings.documents_per_page,
                "default_view_mode": user_settings.default_view_mode,
                "show_processing_details": user_settings.show_processing_details
            },
            "privacy": {
                "analytics_enabled": user_settings.analytics_enabled,
                "improve_ai_enabled": user_settings.improve_ai_enabled,
                "data_retention_days": user_settings.data_retention_days
            },
            "advanced": {
                "max_upload_size_mb": user_settings.max_upload_size_mb,
                "concurrent_uploads": user_settings.concurrent_uploads,
                "custom_categories_limit": user_settings.custom_categories_limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user settings failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve settings"
        )


@router.put("/settings")
async def update_user_settings(
    settings_data: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Update user's application settings
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Get or create user settings
        user_settings = db.query(UserSettings).filter(
            UserSettings.user_id == user.id
        ).first()
        
        if not user_settings:
            user_settings = UserSettings(user_id=user.id)
            db.add(user_settings)
        
        # Update settings based on provided data
        if "document_processing" in settings_data:
            dp = settings_data["document_processing"]
            if "auto_categorization_enabled" in dp:
                user_settings.auto_categorization_enabled = dp["auto_categorization_enabled"]
            if "ocr_enabled" in dp:
                user_settings.ocr_enabled = dp["ocr_enabled"]
            if "ai_suggestions_enabled" in dp:
                user_settings.ai_suggestions_enabled = dp["ai_suggestions_enabled"]
        
        if "notifications" in settings_data:
            notif = settings_data["notifications"]
            if "email_notifications" in notif:
                user_settings.email_notifications = notif["email_notifications"]
            if "processing_notifications" in notif:
                user_settings.processing_notifications = notif["processing_notifications"]
            if "weekly_summary" in notif:
                user_settings.weekly_summary = notif["weekly_summary"]
        
        if "google_drive" in settings_data:
            gd = settings_data["google_drive"]
            if "sync_frequency_minutes" in gd:
                user_settings.sync_frequency_minutes = max(15, gd["sync_frequency_minutes"])
            if "create_subfolder_structure" in gd:
                user_settings.create_subfolder_structure = gd["create_subfolder_structure"]
            if "backup_enabled" in gd:
                user_settings.backup_enabled = gd["backup_enabled"]
        
        if "ui_preferences" in settings_data:
            ui = settings_data["ui_preferences"]
            if "documents_per_page" in ui:
                user_settings.documents_per_page = min(100, max(5, ui["documents_per_page"]))
            if "default_view_mode" in ui and ui["default_view_mode"] in ["grid", "list", "timeline"]:
                user_settings.default_view_mode = ui["default_view_mode"]
            if "show_processing_details" in ui:
                user_settings.show_processing_details = ui["show_processing_details"]
        
        if "privacy" in settings_data:
            priv = settings_data["privacy"]
            if "analytics_enabled" in priv:
                user_settings.analytics_enabled = priv["analytics_enabled"]
            if "improve_ai_enabled" in priv:
                user_settings.improve_ai_enabled = priv["improve_ai_enabled"]
            if "data_retention_days" in priv:
                user_settings.data_retention_days = max(30, priv["data_retention_days"])
        
        user_settings.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Settings updated successfully", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user settings failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings"
        )


@router.get("/statistics")
async def get_user_statistics(
    period: str = Query("month", regex="^(week|month|year|all)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get detailed user usage statistics
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_service = UserService(db)
        statistics = await user_service.get_usage_statistics(user.id, period)
        
        return {
            "period": period,
            "user_id": user.id,
            "statistics": statistics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user statistics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.post("/upgrade-trial")
async def start_premium_trial(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Start premium trial for eligible free tier users
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if user.tier.value != "free":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trial only available for free tier users"
            )
        
        if user.trial_started_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trial already used"
            )
        
        user_service = UserService(db)
        trial_result = await user_service.start_premium_trial(user.id)
        
        if trial_result["success"]:
            return {
                "message": "Premium trial started successfully",
                "trial_ends_at": trial_result["trial_ends_at"],
                "success": True
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=trial_result["error"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start premium trial failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start premium trial"
        )


@router.get("/export-data")
async def export_user_data(
    format: str = Query("json", regex="^(json|csv)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Export user's data for GDPR compliance
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_service = UserService(db)
        export_data = await user_service.export_user_data(user.id, format)
        
        return {
            "user_id": user.id,
            "export_format": format,
            "generated_at": datetime.utcnow().isoformat(),
            "data": export_data,
            "gdpr_compliant": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export user data failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data"
        )


@router.delete("/account")
async def delete_user_account(
    confirmation: str,
    delete_google_drive_files: bool = Query(False, description="Also delete files from Google Drive"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Delete user account and all associated data (GDPR compliance)
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Require confirmation
        if confirmation != f"DELETE {user.email}":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Please confirm by typing 'DELETE {user.email}'"
            )
        
        user_service = UserService(db)
        deletion_result = await user_service.delete_user_account(
            user.id, 
            delete_google_drive_files
        )
        
        if deletion_result["success"]:
            return {
                "message": "Account deleted successfully",
                "deleted_documents": deletion_result["deleted_documents"],
                "deleted_categories": deletion_result["deleted_categories"],
                "google_drive_files_deleted": deletion_result["google_drive_files_deleted"],
                "success": True
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Account deletion failed: {deletion_result['error']}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user account failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )