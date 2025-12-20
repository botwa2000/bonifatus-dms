# backend/app/schemas/delegate_schemas.py
"""
Bonifatus DMS - Delegate Access Schemas
Pydantic models for delegate invitation and access management
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from uuid import UUID


class DelegateInviteRequest(BaseModel):
    """Request model for inviting a delegate"""
    email: EmailStr = Field(..., description="Email address of the delegate to invite")
    role: str = Field(default="viewer", description="Access role (viewer, editor, owner)")
    access_expires_at: Optional[datetime] = Field(None, description="Optional access expiry date")

    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['viewer', 'editor', 'owner']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "assistant@example.com",
                "role": "viewer",
                "access_expires_at": None
            }
        }


class DelegateResponse(BaseModel):
    """Response model for delegate information"""
    id: UUID = Field(..., description="Delegate ID")
    owner_user_id: UUID = Field(..., description="Owner user ID")
    delegate_user_id: Optional[UUID] = Field(None, description="Delegate user ID (null if not accepted)")
    delegate_email: str = Field(..., description="Delegate email address")
    role: str = Field(..., description="Access role")
    status: str = Field(..., description="Invitation status (pending, active, revoked)")
    invitation_sent_at: Optional[datetime] = Field(None, description="When invitation was sent")
    invitation_expires_at: Optional[datetime] = Field(None, description="When invitation expires")
    invitation_accepted_at: Optional[datetime] = Field(None, description="When invitation was accepted")
    access_expires_at: Optional[datetime] = Field(None, description="When access expires")
    last_accessed_at: Optional[datetime] = Field(None, description="Last activity timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    revoked_at: Optional[datetime] = Field(None, description="When access was revoked")

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str  # Serialize UUIDs as strings in JSON response
        }
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "owner_user_id": "123e4567-e89b-12d3-a456-426614174001",
                "delegate_user_id": "123e4567-e89b-12d3-a456-426614174002",
                "delegate_email": "assistant@example.com",
                "role": "viewer",
                "status": "active",
                "invitation_sent_at": "2025-12-15T10:00:00Z",
                "invitation_expires_at": "2025-12-22T10:00:00Z",
                "invitation_accepted_at": "2025-12-15T12:00:00Z",
                "access_expires_at": None,
                "last_accessed_at": "2025-12-15T14:30:00Z",
                "created_at": "2025-12-15T10:00:00Z",
                "updated_at": "2025-12-15T14:30:00Z",
                "revoked_at": None
            }
        }


class DelegateListResponse(BaseModel):
    """Response model for list of delegates"""
    delegates: list[DelegateResponse] = Field(..., description="List of delegates")
    total: int = Field(..., description="Total number of delegates")

    class Config:
        json_schema_extra = {
            "example": {
                "delegates": [],
                "total": 0
            }
        }


class GrantedAccessResponse(BaseModel):
    """Response model for owners who granted access to the current user"""
    id: UUID = Field(..., description="Delegate ID")
    owner_user_id: UUID = Field(..., description="Owner user ID")
    owner_email: str = Field(..., description="Owner email address")
    owner_name: str = Field(..., description="Owner full name")
    role: str = Field(..., description="Access role granted")
    status: str = Field(..., description="Access status")
    access_expires_at: Optional[datetime] = Field(None, description="When access expires")
    last_accessed_at: Optional[datetime] = Field(None, description="Last activity timestamp")
    granted_at: datetime = Field(..., description="When access was granted")

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str  # Serialize UUIDs as strings in JSON response
        }
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "owner_user_id": "123e4567-e89b-12d3-a456-426614174001",
                "owner_email": "owner@example.com",
                "owner_name": "John Doe",
                "role": "viewer",
                "status": "active",
                "access_expires_at": None,
                "last_accessed_at": "2025-12-15T14:30:00Z",
                "granted_at": "2025-12-15T10:00:00Z"
            }
        }


class GrantedAccessListResponse(BaseModel):
    """Response model for list of granted access"""
    granted_access: list[GrantedAccessResponse] = Field(..., description="List of owners who granted access")
    total: int = Field(..., description="Total number of granted access")

    class Config:
        json_schema_extra = {
            "example": {
                "granted_access": [],
                "total": 0
            }
        }


class AcceptInvitationResponse(BaseModel):
    """Response model for accepting an invitation"""
    success: bool = Field(..., description="Whether acceptance was successful")
    owner_name: str = Field(..., description="Name of the owner who granted access")
    owner_email: str = Field(..., description="Email of the owner")
    role: str = Field(..., description="Access role granted")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "owner_name": "John Doe",
                "owner_email": "owner@example.com",
                "role": "viewer",
                "message": "You now have viewer access to John Doe's documents"
            }
        }


class DelegateAccessLogResponse(BaseModel):
    """Response model for delegate access log entry"""
    id: UUID = Field(..., description="Log entry ID")
    delegate_user_id: UUID = Field(..., description="Delegate user ID")
    delegate_email: str = Field(..., description="Delegate email")
    delegate_name: str = Field(..., description="Delegate full name")
    document_id: UUID = Field(..., description="Document ID")
    document_title: str = Field(..., description="Document title")
    action: str = Field(..., description="Action performed (view, download, search)")
    accessed_at: datetime = Field(..., description="When the action was performed")
    ip_address: Optional[str] = Field(None, description="IP address")

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str  # Serialize UUIDs as strings in JSON response
        }
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "delegate_user_id": "123e4567-e89b-12d3-a456-426614174002",
                "delegate_email": "assistant@example.com",
                "delegate_name": "Assistant User",
                "document_id": "123e4567-e89b-12d3-a456-426614174003",
                "document_title": "Invoice 2025-001.pdf",
                "action": "view",
                "accessed_at": "2025-12-15T14:30:00Z",
                "ip_address": "192.168.1.1"
            }
        }


class DelegateAccessLogListResponse(BaseModel):
    """Response model for list of access logs"""
    logs: list[DelegateAccessLogResponse] = Field(..., description="List of access log entries")
    total: int = Field(..., description="Total number of log entries")

    class Config:
        json_schema_extra = {
            "example": {
                "logs": [],
                "total": 0
            }
        }


class DocumentPermissionsResponse(BaseModel):
    """Response model for document permissions when acting as delegate"""
    can_view: bool = Field(..., description="Can view documents")
    can_search: bool = Field(..., description="Can search documents")
    can_download: bool = Field(..., description="Can download documents")
    can_upload: bool = Field(..., description="Can upload documents")
    can_edit: bool = Field(..., description="Can edit documents")
    can_delete: bool = Field(..., description="Can delete documents")
    viewing_as_delegate: bool = Field(..., description="Currently viewing as delegate")
    owner_name: Optional[str] = Field(None, description="Owner name if viewing as delegate")

    class Config:
        json_schema_extra = {
            "example": {
                "can_view": True,
                "can_search": True,
                "can_download": True,
                "can_upload": False,
                "can_edit": False,
                "can_delete": False,
                "viewing_as_delegate": True,
                "owner_name": "John Doe"
            }
        }
