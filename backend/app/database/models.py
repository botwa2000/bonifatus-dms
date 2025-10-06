# backend/src/database/models.py
"""
Bonifatus DMS - Database Models
Core SQLAlchemy models for user management, categories, and system configuration
"""

import uuid
from datetime import datetime
from typing import Optional, List
import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

Base = declarative_base()


class TimestampMixin:
    """Mixin for created/updated timestamps"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(Base, TimestampMixin):
    """User account with Google OAuth integration"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    profile_picture = Column(Text, nullable=True)
    tier = Column(String(20), nullable=False, default="free")
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    
    # Relationships
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    user_settings = relationship("UserSetting", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_google_id', 'google_id'),
        Index('idx_user_email', 'email'),
        Index('idx_user_tier', 'tier'),
    )


class Category(Base, TimestampMixin):
    """Category with dynamic multilingual support"""
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_key = Column(String(100), unique=True, nullable=False, index=True)
    category_code = Column(String(3), nullable=False, index=True)
    color_hex = Column(String(7), nullable=False, default="#6B7280")
    icon_name = Column(String(50), nullable=False, default="folder")
    is_system = Column(Boolean, default=False, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="categories")
    documents = relationship("Document", back_populates="category")
    translations = relationship("CategoryTranslation", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_category_user_id', 'user_id'),
        Index('idx_category_system', 'is_system'),
        Index('idx_category_active', 'is_active'),
        Index('idx_category_reference_key', 'reference_key'),
        Index('idx_category_code', 'category_code'),
        Index('idx_category_user_code_unique', 'user_id', 'category_code', unique=True, postgresql_where=sa.text('user_id IS NOT NULL')),
    )


class CategoryTranslation(Base, TimestampMixin):
    """Category translations - only user's language returned to frontend"""
    __tablename__ = "category_translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    language_code = Column(String(5), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    category = relationship("Category", back_populates="translations")

    __table_args__ = (
        Index('idx_category_trans_category_id', 'category_id'),
        Index('idx_category_trans_lang', 'language_code'),
        Index('idx_category_trans_category_lang', 'category_id', 'language_code', unique=True),
    )


class Document(Base, TimestampMixin):
    """Document metadata and processing status"""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    google_drive_file_id = Column(String(100), nullable=False, unique=True)
    
    # Processing status
    processing_status = Column(String(20), nullable=False, default="pending")
    extracted_text = Column(Text, nullable=True)  # Primary language text
    keywords = Column(Text, nullable=True)  # Primary language keywords
    confidence_score = Column(Integer, nullable=True)
    
    # Language detection
    primary_language = Column(String(5), nullable=True, index=True)  # ISO 639-1
    detected_languages = Column(Text, nullable=True)  # JSON array of detected languages
    
    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    
    user = relationship("User", back_populates="documents")
    category = relationship("Category", back_populates="documents")
    languages = relationship("DocumentLanguage", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_document_user_id', 'user_id'),
        Index('idx_document_category_id', 'category_id'),
        Index('idx_document_status', 'processing_status'),
        Index('idx_document_google_drive', 'google_drive_file_id'),
        Index('idx_document_primary_lang', 'primary_language'),
    )


class SystemSetting(Base, TimestampMixin):
    """System-wide configuration stored in database"""
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    data_type = Column(String(20), nullable=False, default="string")
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    category = Column(String(50), nullable=False, default="general")

    __table_args__ = (
        Index('idx_system_setting_key', 'setting_key'),
        Index('idx_system_setting_category', 'category'),
    )


class UserSetting(Base, TimestampMixin):
    """User-specific settings and preferences"""
    __tablename__ = "user_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    setting_key = Column(String(100), nullable=False)
    setting_value = Column(Text, nullable=False)
    data_type = Column(String(20), nullable=False, default="string")

    # Relationships
    user = relationship("User", back_populates="user_settings")

    __table_args__ = (
        Index('idx_user_setting_user_key', 'user_id', 'setting_key'),
    )


class LocalizationString(Base, TimestampMixin):
    """Multilingual text strings for UI"""
    __tablename__ = "localization_strings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    string_key = Column(String(100), nullable=False, index=True)
    language_code = Column(String(5), nullable=False, index=True)
    string_value = Column(Text, nullable=False)
    context = Column(String(100), nullable=True)

    __table_args__ = (
        Index('idx_localization_key_lang', 'string_key', 'language_code'),
    )


class AuditLog(Base, TimestampMixin):
    """Enterprise audit logging for security and compliance"""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    endpoint = Column(String(255), nullable=True)
    
    # Audit details
    old_values = Column(Text, nullable=True)  # JSON string
    new_values = Column(Text, nullable=True)  # JSON string
    status = Column(String(20), nullable=False, default="success")
    error_message = Column(Text, nullable=True)
    
    # Multilingual context
    user_locale = Column(String(5), nullable=True)
    
    # Additional context data
    extra_data = Column(Text, nullable=True)  # JSON string for extra context

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_timestamp', 'created_at'),
        Index('idx_audit_status', 'status'),
    )


class DocumentLanguage(Base, TimestampMixin):
    """Document language detection and processing status"""
    __tablename__ = "document_languages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    language_code = Column(String(5), nullable=False, index=True)  # ISO 639-1
    confidence_score = Column(Integer, nullable=False, default=0)  # 0-100
    is_primary = Column(Boolean, default=False, nullable=False)
    
    # Language-specific processing
    extracted_text = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)  # JSON array
    processing_status = Column(String(20), nullable=False, default="pending")
    ai_category_suggestion = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    ai_confidence = Column(Integer, nullable=True)  # 0-100
    
    # Relationships
    document = relationship("Document", back_populates="languages")
    suggested_category = relationship("Category")

    __table_args__ = (
        Index('idx_doc_lang_document', 'document_id'),
        Index('idx_doc_lang_code', 'language_code'),
        Index('idx_doc_lang_primary', 'document_id', 'is_primary'),
    )