# backend/src/database/models.py
"""
Bonifatus DMS - Database Models
SQLAlchemy models for Supabase PostgreSQL
Production-ready models with proper relationships and indexes
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
import uuid

Base = declarative_base()


class UserTier(str, Enum):
    """User subscription tiers"""

    FREE = "free"
    PREMIUM_TRIAL = "premium_trial"
    PREMIUM = "premium"
    ADMIN = "admin"


class DocumentStatus(str, Enum):
    """Document processing status"""

    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    ARCHIVED = "archived"


class User(Base):
    """User model with Google OAuth integration and tier management"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Google OAuth fields
    google_id = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)

    # User tier and limits
    tier = Column(SQLEnum(UserTier), default=UserTier.FREE, nullable=False)
    document_count = Column(Integer, default=0, nullable=False)
    monthly_uploads = Column(Integer, default=0, nullable=False)
    storage_used_bytes = Column(Integer, default=0, nullable=False)

    # Trial management
    trial_started_at = Column(DateTime(timezone=True), nullable=True)
    trial_ended_at = Column(DateTime(timezone=True), nullable=True)

    # Google Drive integration
    google_drive_token = Column(JSON, nullable=True)  # Encrypted OAuth token
    google_drive_folder_id = Column(String(255), nullable=True)
    google_drive_connected = Column(Boolean, default=False, nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    # User preferences
    preferred_language = Column(String(10), default="en", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    theme = Column(String(20), default="light", nullable=False)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    documents = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )
    categories = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    user_settings = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_google_id", "google_id"),
        Index("idx_user_tier", "tier"),
        Index("idx_user_active", "is_active"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', tier='{self.tier}')>"


class Category(Base):
    """Document category model with multilingual support"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # NULL for system categories

    # Multilingual names and descriptions
    name_en = Column(String(100), nullable=False)
    name_de = Column(String(100), nullable=False)
    description_en = Column(Text, nullable=True)
    description_de = Column(Text, nullable=True)

    # Visual and organizational
    color = Column(String(7), default="#6B7280", nullable=False)  # Hex color
    icon = Column(String(50), nullable=True)  # Icon name or path
    sort_order = Column(Integer, default=0, nullable=False)

    # Category properties
    is_system_category = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    keywords = Column(
        Text, nullable=True
    )  # Comma-separated keywords for auto-categorization

    # Usage statistics
    document_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="categories")
    documents = relationship("Document", back_populates="category")

    # Indexes
    __table_args__ = (
        Index("idx_category_user", "user_id"),
        Index("idx_category_system", "is_system_category"),
        Index("idx_category_active", "is_active"),
        Index("idx_category_sort", "sort_order"),
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name_en='{self.name_en}', system={self.is_system_category})>"


class Document(Base):
    """Document model with Google Drive integration and metadata"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # File identification
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)  # User's original filename
    file_path = Column(String(500), nullable=False)  # Path in Google Drive
    google_drive_file_id = Column(String(255), unique=True, nullable=False)

    # File metadata
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_extension = Column(String(10), nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication

    # Processing status
    status = Column(
        SQLEnum(DocumentStatus), default=DocumentStatus.UPLOADING, nullable=False
    )
    processing_error = Column(Text, nullable=True)

    # Content and metadata
    title = Column(String(255), nullable=True)  # User-defined or extracted title
    description = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)  # OCR/extraction result
    extracted_keywords = Column(JSON, nullable=True)  # List of extracted keywords
    language_detected = Column(String(10), nullable=True)  # Detected document language

    # AI processing results
    ai_confidence_score = Column(
        Float, nullable=True
    )  # Confidence in categorization (0.0-1.0)
    ai_suggested_category = Column(Integer, nullable=True)  # AI suggested category ID
    ai_extracted_entities = Column(JSON, nullable=True)  # Named entities, dates, etc.

    # User interaction
    user_keywords = Column(JSON, nullable=True)  # User-added keywords
    notes = Column(Text, nullable=True)  # User notes
    is_favorite = Column(Boolean, default=False, nullable=False)
    view_count = Column(Integer, default=0, nullable=False)
    last_viewed_at = Column(DateTime(timezone=True), nullable=True)

    # Google Drive sync
    google_drive_modified_time = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_version = Column(Integer, default=1, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="documents")
    category = relationship("Category", back_populates="documents")

    # Indexes for performance
    __table_args__ = (
        Index("idx_document_user", "user_id"),
        Index("idx_document_category", "category_id"),
        Index("idx_document_status", "status"),
        Index("idx_document_google_id", "google_drive_file_id"),
        Index("idx_document_filename", "filename"),
        Index("idx_document_created", "created_at"),
        Index("idx_document_favorite", "is_favorite"),
        Index("idx_document_text_search", "extracted_text"),  # For full-text search
    )

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class UserSettings(Base):
    """User-specific settings and preferences"""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Document processing preferences
    auto_categorization_enabled = Column(Boolean, default=True, nullable=False)
    ocr_enabled = Column(Boolean, default=True, nullable=False)
    ai_suggestions_enabled = Column(Boolean, default=True, nullable=False)

    # Notification preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    processing_notifications = Column(Boolean, default=True, nullable=False)
    weekly_summary = Column(Boolean, default=True, nullable=False)

    # Google Drive preferences
    sync_frequency_minutes = Column(
        Integer, default=60, nullable=False
    )  # Auto-sync interval
    create_subfolder_structure = Column(Boolean, default=True, nullable=False)
    backup_enabled = Column(Boolean, default=True, nullable=False)

    # UI preferences
    documents_per_page = Column(Integer, default=20, nullable=False)
    default_view_mode = Column(
        String(20), default="grid", nullable=False
    )  # grid, list, timeline
    show_processing_details = Column(Boolean, default=False, nullable=False)

    # Privacy and data preferences
    analytics_enabled = Column(Boolean, default=True, nullable=False)
    improve_ai_enabled = Column(
        Boolean, default=True, nullable=False
    )  # Use data to improve AI
    data_retention_days = Column(Integer, default=365, nullable=False)

    # Advanced settings
    max_upload_size_mb = Column(Integer, default=50, nullable=False)
    concurrent_uploads = Column(Integer, default=3, nullable=False)
    custom_categories_limit = Column(Integer, default=20, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="user_settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id})>"


class SystemSettings(Base):
    """System-wide configuration and settings"""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Tier limits
    free_tier_document_limit = Column(Integer, default=100, nullable=False)
    premium_trial_document_limit = Column(Integer, default=500, nullable=False)
    premium_document_limit = Column(Integer, default=0, nullable=False)  # 0 = unlimited
    free_tier_monthly_uploads = Column(Integer, default=50, nullable=False)
    premium_monthly_uploads = Column(
        Integer, default=0, nullable=False
    )  # 0 = unlimited

    # File processing limits
    max_file_size_mb = Column(Integer, default=50, nullable=False)
    max_concurrent_processing = Column(Integer, default=5, nullable=False)
    ocr_monthly_limit = Column(Integer, default=1000, nullable=False)
    ai_processing_monthly_limit = Column(Integer, default=500, nullable=False)

    # Feature flags
    ocr_enabled = Column(Boolean, default=True, nullable=False)
    ai_categorization_enabled = Column(Boolean, default=True, nullable=False)
    google_drive_enabled = Column(Boolean, default=True, nullable=False)
    user_registration_enabled = Column(Boolean, default=True, nullable=False)
    maintenance_mode = Column(Boolean, default=False, nullable=False)

    # Localization
    default_language = Column(String(10), default="en", nullable=False)
    supported_languages = Column(JSON, default=["en", "de"], nullable=False)

    # API and integration settings
    google_api_rate_limit = Column(
        Integer, default=100, nullable=False
    )  # requests per minute
    session_timeout_minutes = Column(Integer, default=60, nullable=False)

    # Maintenance and monitoring
    database_backup_enabled = Column(Boolean, default=True, nullable=False)
    error_reporting_enabled = Column(Boolean, default=True, nullable=False)
    performance_monitoring_enabled = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<SystemSettings(id={self.id})>"


class AuditLog(Base):
    """Audit log for user actions and system events"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # NULL for system events

    # Event details
    action = Column(
        String(100), nullable=False
    )  # e.g., 'document_upload', 'login', 'category_create'
    resource_type = Column(
        String(50), nullable=True
    )  # e.g., 'document', 'user', 'category'
    resource_id = Column(String(50), nullable=True)  # ID of affected resource

    # Request details
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(100), nullable=True)  # Request tracing ID

    # Event data
    event_data = Column(JSON, nullable=True)  # Additional event context
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_created", "created_at"),
        Index("idx_audit_success", "success"),
    )

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', user_id={self.user_id})>"
        )


class SearchHistory(Base):
    """Search history for analytics and user experience"""

    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Search details
    query = Column(String(500), nullable=False)
    entity_type = Column(String(50), nullable=False)  # 'documents', 'categories', etc.
    results_count = Column(Integer, default=0, nullable=False)

    # Timestamp
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User")

    # Indexes for performance
    __table_args__ = (
        Index("idx_search_history_user", "user_id"),
        Index("idx_search_history_query", "query"),
        Index("idx_search_history_created", "created_at"),
        Index("idx_search_history_user_query", "user_id", "query"),
    )

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, user_id={self.user_id}, query='{self.query}')>"
