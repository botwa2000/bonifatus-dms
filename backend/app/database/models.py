# backend/src/database/models.py
"""
Bonifatus DMS - Database Models
Core SQLAlchemy models for user management, categories, and system configuration
"""

import uuid
from datetime import datetime
from typing import Optional, List
import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Float, ForeignKey, Table, UUID as SQLUUID, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
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

    # Security columns
    drive_refresh_token_encrypted = Column(Text, nullable=True)
    drive_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    google_drive_enabled = Column(Boolean, default=False, nullable=False)
    drive_permissions_granted_at = Column(DateTime(timezone=True), nullable=True)
    last_ip_address = Column(String(45), nullable=True)
    last_user_agent = Column(Text, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", foreign_keys="[Document.user_id]", back_populates="user", cascade="all, delete-orphan")
    user_settings = relationship("UserSetting", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship('UserSession', back_populates='user', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_user_google_id', 'google_id'),
        Index('idx_user_email', 'email'),
        Index('idx_user_tier', 'tier'),
    )


class UserSession(Base):
    """User authentication sessions"""
    __tablename__ = 'user_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    refresh_token_hash = Column(String(64), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(100), nullable=True)
    
    user = relationship('User', back_populates='sessions')

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
    translations = relationship("CategoryTranslation", back_populates="category", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="category")
    keywords = relationship('CategoryKeyword', back_populates='category', cascade='all, delete-orphan')

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
    extracted_text = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=True)

    # Language detection
    primary_language = Column(String(5), nullable=True, index=True)
    detected_languages = Column(Text, nullable=True)

    # Date extraction
    document_date = Column(sa.Date, nullable=True)
    document_date_confidence = Column(Float, nullable=True)
    document_date_type = Column(String(50), nullable=True)

    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="documents")
    category = relationship("Category", back_populates="documents")
    categories = relationship("DocumentCategory", back_populates="document", cascade="all, delete-orphan")
    languages = relationship("DocumentLanguage", back_populates="document", cascade="all, delete-orphan")
    dates = relationship("DocumentDate", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_document_user_id', 'user_id'),
        Index('idx_document_category_id', 'category_id'),
        Index('idx_document_status', 'processing_status'),
        Index('idx_document_google_drive', 'google_drive_file_id'),
        Index('idx_document_primary_lang', 'primary_language'),
        Index('idx_document_date', 'document_date'),
    )

class DocumentCategory(Base):
    """Many-to-many relationship between documents and categories"""
    __tablename__ = "document_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by_ai = Column(Boolean, default=False, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="categories")
    category = relationship("Category")

    __table_args__ = (
        Index('idx_doc_cats_document', 'document_id'),
        Index('idx_doc_cats_category', 'category_id'),
        Index('idx_doc_cats_primary', 'document_id', 'is_primary'),
        sa.UniqueConstraint('document_id', 'category_id', name='uq_document_category'),
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
    security_level = Column(String(20), nullable=True)
    security_flags = Column(JSONB, nullable=True)

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

class StopWord(Base):
    """Stop words for keyword filtering"""
    __tablename__ = 'stop_words'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word = Column(String(100), nullable=False)
    language_code = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CategoryKeyword(Base):
    """Category keywords for classification"""
    __tablename__ = 'category_keywords'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    keyword = Column(String(200), nullable=False)
    language_code = Column(String(10), nullable=False)
    weight = Column(Float, nullable=False)
    match_count = Column(Integer, default=1, nullable=False)
    is_system_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_matched_at = Column(DateTime(timezone=True), nullable=True)
    
    category = relationship('Category', back_populates='keywords')



class CategoryTrainingData(Base):
    """Training data for category prediction"""
    __tablename__ = 'category_training_data'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=True)
    suggested_category_id = Column(UUID(as_uuid=True), ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    actual_category_id = Column(UUID(as_uuid=True), ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    was_correct = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=True)
    text_sample = Column(Text, nullable=True)
    language_code = Column(String(10), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NgramPattern(Base):
    """N-gram patterns for multi-word extraction"""
    __tablename__ = 'ngram_patterns'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pattern = Column(String(500), nullable=False)
    pattern_type = Column(String(50), nullable=False)
    language_code = Column(String(10), nullable=False)
    importance_score = Column(Float, default=1.0, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class LanguageDetectionPattern(Base):
    """Language detection patterns for scalable multilingual support"""
    __tablename__ = 'language_detection_patterns'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    language_code = Column(String(10), nullable=False)
    pattern = Column(String(100), nullable=False)
    pattern_type = Column(String(50), nullable=False)  # common_word, character_set, grammar
    weight = Column(Float, default=1.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DocumentDate(Base, TimestampMixin):
    """Secondary dates extracted from documents"""
    __tablename__ = "document_dates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    date_type = Column(String(50), nullable=False)
    date_value = Column(sa.Date, nullable=False)
    confidence = Column(Float, nullable=True)
    extracted_text = Column(String(200), nullable=True)

    # Relationships
    document = relationship("Document", back_populates="dates")

    __table_args__ = (
        Index('idx_document_dates_document_id', 'document_id'),
        Index('idx_document_dates_date_type', 'date_type'),
        Index('idx_document_dates_date_value', 'date_value'),
    )