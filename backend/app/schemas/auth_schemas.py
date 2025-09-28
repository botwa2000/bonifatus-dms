# backend/app/schemas/auth_schemas.py
"""
Bonifatus DMS - Authentication Schemas
Pydantic models for authentication requests and responses
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator


class GoogleTokenRequest(BaseModel):
    """Request model for Google OAuth token authentication"""
    google_token: str = Field(..., description="Google OAuth ID token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE2N..."
            }
        }


class TokenResponse(BaseModel):
    """Response model for successful authentication"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    tier: str = Field(..., description="User tier (free, trial, premium)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "tier": "free"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh"""
    refresh_token: str = Field(..., description="JWT refresh token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RefreshTokenResponse(BaseModel):
    """Response model for token refresh"""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    tier: str = Field(..., description="User tier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "tier": "free"
            }
        }


class UserResponse(BaseModel):
    """Response model for user information"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    tier: str = Field(..., description="User tier")
    is_active: bool = Field(..., description="User active status")
    last_login_at: Optional[str] = Field(None, description="Last login timestamp")
    created_at: str = Field(..., description="Account creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "profile_picture": "https://lh3.googleusercontent.com/...",
                "tier": "free",
                "is_active": True,
                "last_login_at": "2024-09-21T10:30:00Z",
                "created_at": "2024-09-20T15:20:00Z"
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
                "error": "authentication_failed",
                "message": "Invalid Google token",
                "details": "Token has expired or is malformed"
            }
        }


class GoogleOAuthConfigResponse(BaseModel):
    """Response model for Google OAuth configuration"""
    google_client_id: str = Field(..., description="Google OAuth client ID")
    redirect_uri: str = Field(..., description="OAuth redirect URI")
    
    class Config:
        json_schema_extra = {
            "example": {
                "google_client_id": "356302004293-example.apps.googleusercontent.com",
                "redirect_uri": "https://bonifatus-dms-356302004293.us-central1.run.app/api/v1/auth/google/callback"
            }
        }

class TokenData(BaseModel):
    """Data extracted from JWT token payload"""
    user_id: str = Field(..., description="User ID from token")
    email: Optional[str] = Field(None, description="User email from token")
    exp: Optional[int] = Field(None, description="Token expiration timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "exp": 1672531200
            }
        }


class UserCreate(BaseModel):
    """Request model for user creation/registration"""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    google_id: str = Field(..., description="Google OAuth user ID")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL from Google")
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v.strip() == "":
            raise ValueError('Full name cannot be empty')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "google_id": "108123456789012345678",
                "profile_picture": "https://lh3.googleusercontent.com/..."
            }
        }        