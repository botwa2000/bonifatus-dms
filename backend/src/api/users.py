# backend/src/api/users.py
"""
Bonifatus DMS - Users API
User profile management, settings, statistics, and account operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from src.database import get_db, User, UserSettings
from src.services.auth_service import AuthService
from src.services.user_service import UserService

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter()


@router.get("/profile")
def get_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get user profile with complete information
    FIXED: Removed async and await - AuthService.get_current_user() is synchronous
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user_service = UserService(db)
        profile_data = user_service.get_complete_profile(user.id)  # REMOVED await

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
                "google_drive_connected": user.google_drive_connected,
                "created_at": user.created_at.isoformat(),
                "last_login_at": (
                    user.last_login_at.isoformat() if user.last_login_at else None
                ),
            },
            "usage": profile_data.get("tier_limits", {}),
            "trial_info": profile_data.get("trial_info", {}),
            "statistics": profile_data.get("statistics", {}),
            "google_drive": {
                "connected": user.google_drive_connected,
                "folder_id": getattr(user, "google_drive_folder_id", None),
                "last_sync": getattr(user, "last_sync_at", None),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile",
        )


@router.put("/profile")
def update_user_profile(
    full_name: Optional[str] = Query(None),
    preferred_language: Optional[str] = Query(None, pattern="^(en|de)$"),
    timezone: Optional[str] = Query(None),
    theme: Optional[str] = Query(None, pattern="^(light|dark|auto)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Update user profile information
    FIXED: Removed async and await
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Update user fields
        update_data = {}
        if full_name is not None:
            update_data["full_name"] = full_name
        if preferred_language is not None:
            update_data["preferred_language"] = preferred_language
        if timezone is not None:
            update_data["timezone"] = timezone
        if theme is not None:
            update_data["theme"] = theme

        # Apply updates
        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()

        return {
            "message": "Profile updated successfully",
            "updated_fields": list(update_data.keys()),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


@router.get("/settings")
def get_user_settings(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get user settings
    FIXED: Removed async and await
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Get user settings
        settings = (
            db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        )

        if not settings:
            # Create default settings
            settings = UserSettings(
                user_id=user.id,
                auto_categorization_enabled=True,
                ocr_enabled=True,
                documents_per_page=20,
                default_view_mode="grid",
                notification_enabled=True,
                privacy_level="standard",
            )
            db.add(settings)
            db.commit()

        return {
            "document_processing": {
                "auto_categorization_enabled": settings.auto_categorization_enabled,
                "ocr_enabled": settings.ocr_enabled,
            },
            "ui_preferences": {
                "documents_per_page": settings.documents_per_page,
                "default_view_mode": settings.default_view_mode,
            },
            "notifications": {"enabled": settings.notification_enabled},
            "privacy": {"level": settings.privacy_level},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user settings failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve settings",
        )


@router.put("/settings")
def update_user_settings(
    settings_data: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Update user settings
    FIXED: Removed async and await
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Get or create settings
        settings = (
            db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        )
        if not settings:
            settings = UserSettings(user_id=user.id)
            db.add(settings)

        # Update settings based on provided data
        if "document_processing" in settings_data:
            proc_settings = settings_data["document_processing"]
            if "auto_categorization_enabled" in proc_settings:
                settings.auto_categorization_enabled = proc_settings[
                    "auto_categorization_enabled"
                ]
            if "ocr_enabled" in proc_settings:
                settings.ocr_enabled = proc_settings["ocr_enabled"]

        if "ui_preferences" in settings_data:
            ui_settings = settings_data["ui_preferences"]
            if "documents_per_page" in ui_settings:
                settings.documents_per_page = ui_settings["documents_per_page"]
            if "default_view_mode" in ui_settings:
                settings.default_view_mode = ui_settings["default_view_mode"]

        db.commit()

        return {"message": "Settings updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user settings failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings",
        )


@router.get("/statistics")
def get_user_statistics(
    period: str = Query("month", pattern="^(week|month|year|all)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get user usage statistics
    FIXED: Removed async and await
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user_service = UserService(db)
        statistics = user_service.get_usage_statistics(user.id, period)  # REMOVED await

        return {"period": period, "user_id": user.id, "statistics": statistics}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user statistics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        )


@router.post("/upgrade-trial")
def start_premium_trial(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Start premium trial for eligible free tier users
    FIXED: Removed async and await
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        if user.tier.value != "free":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trial only available for free tier users",
            )

        if user.trial_started_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Trial already used"
            )

        user_service = UserService(db)
        trial_result = user_service.start_premium_trial(user.id)  # REMOVED await

        if trial_result["success"]:
            return {
                "message": "Premium trial started successfully",
                "trial_ends_at": trial_result["trial_ends_at"],
                "success": True,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=trial_result["error"]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start premium trial failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start premium trial",
        )


@router.get("/export-data")
def export_user_data(
    format: str = Query("json", pattern="^(json|csv)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Export user's data for GDPR compliance
    FIXED: Removed async and await
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user_service = UserService(db)
        export_data = user_service.export_user_data(user.id, format)  # REMOVED await

        return {"user_id": user.id, "format": format, "data": export_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export user data failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export data",
        )


@router.delete("/account")
def delete_user_account(
    confirmation: str = Query(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Delete user account and all associated data
    FIXED: Removed async and await
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Verify confirmation string
        expected_confirmation = f"DELETE {user.email}"
        if confirmation != expected_confirmation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Confirmation must be: {expected_confirmation}",
            )

        user_service = UserService(db)
        deletion_result = user_service.delete_user_account(user.id)  # REMOVED await

        return {
            "message": "Account deleted successfully",
            "user_id": user.id,
            "deletion_summary": deletion_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user account failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account",
        )
