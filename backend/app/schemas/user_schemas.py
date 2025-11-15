# backend/app/schemas/user_schemas.py
"""
Bonifatus DMS - User Management Schemas
Pydantic models for user profile and settings operations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


class UserProfileUpdate(BaseModel):
    """Request model for updating user profile"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User full name")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError('Full name cannot be empty')
        return v.strip() if v else v
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "profile_picture": "https://lh3.googleusercontent.com/..."
            }
        }


class UserProfileResponse(BaseModel):
    """Response model for user profile data"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    tier: str = Field(..., description="User tier name")
    tier_id: int = Field(..., description="User tier ID")
    is_active: bool = Field(..., description="User active status")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last profile update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "profile_picture": "https://lh3.googleusercontent.com/...",
                "tier": "free",
                "tier_id": 0,
                "is_active": True,
                "last_login_at": "2024-09-21T10:30:00Z",
                "created_at": "2024-09-20T15:20:00Z",
                "updated_at": "2024-09-21T08:15:00Z"
            }
        }


class UserStatistics(BaseModel):
    """User statistics and usage information"""
    documents_count: int = Field(..., description="Total documents uploaded")
    categories_count: int = Field(..., description="Custom categories created")
    storage_used_mb: int = Field(..., description="Storage used in megabytes")
    last_activity: Optional[datetime] = Field(None, description="Last user activity")
    
    class Config:
        json_schema_extra = {
            "example": {
                "documents_count": 25,
                "categories_count": 3,
                "storage_used_mb": 1024,
                "last_activity": "2024-09-21T14:30:00Z"
            }
        }


class UserPreferences(BaseModel):
    """User preferences and settings"""
    language: str = Field(..., description="Preferred UI language")
    preferred_doc_languages: List[str] = Field(..., description="Preferred document processing languages")
    timezone: str = Field(..., description="User timezone")
    theme: Optional[str] = Field(None, description="Preferred theme (light/dark)")
    notifications_enabled: bool = Field(..., description="Email notifications enabled")
    auto_categorization: bool = Field(..., description="AI auto-categorization enabled")
    email_marketing_enabled: bool = Field(..., description="Marketing/promotional emails enabled (GDPR compliance)")

    class Config:
        json_schema_extra = {
            "example": {
                "language": "en",
                "preferred_doc_languages": ["en", "de"],
                "timezone": "Europe/Berlin",
                "theme": "light",
                "notifications_enabled": True,
                "auto_categorization": True,
                "email_marketing_enabled": True
            }
        }


class UserPreferencesUpdate(BaseModel):
    """Request model for updating user preferences"""
    language: Optional[str] = Field(None, description="Preferred UI language")
    preferred_doc_languages: Optional[List[str]] = Field(None, description="Preferred document processing languages")
    timezone: Optional[str] = Field(None, description="User timezone")
    theme: Optional[str] = Field(None, description="Preferred theme (light/dark)")
    notifications_enabled: Optional[bool] = Field(None, description="Email notifications")
    auto_categorization: Optional[bool] = Field(None, description="AI auto-categorization")
    email_marketing_enabled: Optional[bool] = Field(None, description="Marketing/promotional emails (GDPR compliance)")

    class Config:
        json_schema_extra = {
            "example": {
                "language": "de",
                "preferred_doc_languages": ["de", "en", "ru"],
                "timezone": "Europe/Berlin",
                "theme": "dark",
                "notifications_enabled": False,
                "email_marketing_enabled": True
            }
        }


class AccountDeactivationRequest(BaseModel):
    """Request model for account deactivation"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for deactivation")
    feedback: Optional[str] = Field(None, max_length=1000, description="User feedback")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reason": "No longer need the service",
                "feedback": "Great service, but switching to internal solution"
            }
        }


class AccountDeactivationResponse(BaseModel):
    """Response model for account deactivation"""
    success: bool = Field(..., description="Deactivation successful")
    message: str = Field(..., description="Deactivation message")
    deactivated_at: datetime = Field(..., description="Deactivation timestamp")
    data_retention_days: int = Field(..., description="Days until data deletion")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Account deactivated successfully",
                "deactivated_at": "2024-09-21T15:00:00Z",
                "data_retention_days": 30
            }
        }


class UserDashboard(BaseModel):
    """User dashboard overview data"""
    profile: UserProfileResponse
    statistics: UserStatistics
    preferences: UserPreferences
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Recent user activity")
    
    class Config:
        json_schema_extra = {
            "example": {
                "profile": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "tier": "free"
                },
                "statistics": {
                    "documents_count": 25,
                    "categories_count": 3,
                    "storage_used_mb": 1024
                },
                "preferences": {
                    "language": "en",
                    "timezone": "UTC"
                },
                "recent_activity": []
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Invalid user data provided",
                "details": "Full name cannot be empty"
            }
        }