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
    file_name = Column(String(255), nullable=False)  # Standardized filename for Google Drive
    original_filename = Column(String(255), nullable=True)  # What user originally uploaded
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash for deduplication
    google_drive_file_id = Column(String(100), nullable=False, unique=True)
    web_view_link = Column(String(500), nullable=True)  # Google Drive web link for direct access

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

    # Duplicate detection
    is_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_of_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)

    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True)

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
        Index('idx_documents_batch', 'batch_id'),
        Index('idx_documents_duplicate_of', 'duplicate_of_document_id'),
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


# ============================================================================
# ADDITIONAL MODELS - Previously missing, restored from migrations
# ============================================================================

class UploadBatch(Base, TimestampMixin):
    """Batch upload tracking"""
    __tablename__ = "upload_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_files = Column(Integer, nullable=False)
    processed_files = Column(Integer, nullable=False, server_default='0')
    successful_files = Column(Integer, nullable=False, server_default='0')
    failed_files = Column(Integer, nullable=False, server_default='0')
    status = Column(String(50), nullable=False, server_default='processing')
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_upload_batches_user', 'user_id', 'created_at'),
    )


class Keyword(Base, TimestampMixin):
    """Keywords for document tagging and search"""
    __tablename__ = "keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(String(100), nullable=False, unique=True)
    normalized_form = Column(String(100), nullable=False)
    language_code = Column(String(5), nullable=True)
    usage_count = Column(Integer, nullable=False, server_default='0')
    category = Column(String(50), nullable=True)

    __table_args__ = (
        Index('idx_keyword_normalized', 'normalized_form'),
        Index('idx_keyword_language', 'language_code'),
        Index('idx_keyword_usage', 'usage_count'),
    )


class DocumentKeyword(Base):
    """Many-to-many relationship between documents and keywords"""
    __tablename__ = "document_keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    keyword_id = Column(UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False)
    relevance_score = Column(Float, nullable=True)
    is_auto_extracted = Column(Boolean, nullable=False, server_default='true')
    is_user_added = Column(Boolean, nullable=False, server_default='false')
    extraction_method = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    position_in_document = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_doc_keywords_doc', 'document_id'),
        Index('idx_doc_keywords_keyword', 'keyword_id'),
        Index('idx_doc_keywords_relevance', sa.text('relevance_score DESC')),
        sa.UniqueConstraint('document_id', 'keyword_id', name='uq_doc_keyword'),
    )


class DocumentEntity(Base):
    """Extracted entities from documents (names, dates, amounts, etc.)"""
    __tablename__ = "document_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    position_start = Column(Integer, nullable=True)
    position_end = Column(Integer, nullable=True)
    page_number = Column(Integer, nullable=True)
    extraction_method = Column(String(50), nullable=True)
    language_code = Column(String(5), nullable=True)
    entity_metadata = Column('metadata', Text, nullable=True)  # 'metadata' is SQLAlchemy reserved
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_doc_entities_doc', 'document_id'),
        Index('idx_doc_entities_type', 'entity_type'),
        Index('idx_doc_entities_value', 'entity_value'),
    )


class UserStorageQuota(Base, TimestampMixin):
    """Storage quota tracking per user"""
    __tablename__ = "user_storage_quotas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    tier = Column(String(20), nullable=False)
    total_quota_bytes = Column(sa.BigInteger, nullable=False)
    used_bytes = Column(sa.BigInteger, nullable=False, server_default='0')
    document_count = Column(Integer, nullable=False, server_default='0')
    largest_file_bytes = Column(sa.BigInteger, nullable=False, server_default='0')
    last_calculated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_user_quota_tier', 'tier'),
    )


class AIProcessingQueue(Base, TimestampMixin):
    """Queue for AI document processing tasks"""
    __tablename__ = "ai_processing_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, server_default='pending')
    priority = Column(Integer, nullable=False, server_default='5')
    attempts = Column(Integer, nullable=False, server_default='0')
    max_attempts = Column(Integer, nullable=False, server_default='3')
    error_message = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)
    ai_provider = Column(String(50), nullable=True)
    ai_model = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    cost_usd = Column(sa.Numeric(10, 6), nullable=True)

    __table_args__ = (
        Index('idx_ai_queue_status', 'status', sa.text('priority DESC'), 'created_at'),
        Index('idx_ai_queue_document', 'document_id'),
        Index('idx_ai_queue_task_type', 'task_type', 'status'),
        sa.CheckConstraint('priority >= 1 AND priority <= 10', name='check_priority_range'),
    )


class Collection(Base, TimestampMixin):
    """Document collections (folders)"""
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color_hex = Column(String(7), nullable=False, server_default='#6B7280')
    icon_name = Column(String(50), nullable=False, server_default='folder')
    parent_collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=True)
    sort_order = Column(Integer, nullable=False, server_default='0')
    is_smart = Column(Boolean, nullable=False, server_default='false')
    smart_rules = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_collection_user', 'user_id'),
        Index('idx_collection_parent', 'parent_collection_id'),
        Index('idx_collection_smart', 'is_smart'),
    )


class CollectionDocument(Base):
    """Many-to-many relationship between collections and documents"""
    __tablename__ = "collection_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    added_by_rule = Column(Boolean, nullable=False, server_default='false')

    __table_args__ = (
        Index('idx_collection_docs_collection', 'collection_id'),
        Index('idx_collection_docs_document', 'document_id'),
        sa.UniqueConstraint('collection_id', 'document_id', name='uq_collection_document'),
    )


class DocumentRelationship(Base):
    """Relationships between documents"""
    __tablename__ = "document_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    child_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), nullable=False)
    relationship_metadata = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_doc_rel_parent', 'parent_document_id'),
        Index('idx_doc_rel_child', 'child_document_id'),
        Index('idx_doc_rel_type', 'relationship_type'),
        sa.CheckConstraint('parent_document_id != child_document_id', name='check_not_self_related'),
        sa.UniqueConstraint('parent_document_id', 'child_document_id', 'relationship_type', name='uq_doc_relationship'),
    )


class DocumentShare(Base, TimestampMixin):
    """Document sharing with users or via public links"""
    __tablename__ = "document_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    shared_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_with_email = Column(String(255), nullable=False)
    shared_with_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    permission_level = Column(String(20), nullable=False)
    share_token = Column(String(255), nullable=True, unique=True)
    share_url = Column(Text, nullable=True)
    is_public = Column(Boolean, nullable=False, server_default='false')
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default='true')
    access_count = Column(Integer, nullable=False, server_default='0')
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_doc_shares_doc', 'document_id'),
        Index('idx_doc_shares_by_user', 'shared_by_user_id'),
        Index('idx_doc_shares_with_email', 'shared_with_email'),
        Index('idx_doc_shares_token', 'share_token'),
        Index('idx_doc_shares_active', 'is_active', 'expires_at'),
        sa.CheckConstraint("permission_level IN ('view', 'comment', 'edit')", name='check_permission_level'),
    )


class Tag(Base):
    """User-defined tags for documents"""
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    color_hex = Column(String(7), nullable=False, server_default='#6B7280')
    usage_count = Column(Integer, nullable=False, server_default='0')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_tags_user', 'user_id'),
        Index('idx_tags_usage', 'usage_count'),
        sa.UniqueConstraint('user_id', 'name', name='uq_user_tag_name'),
    )


class DocumentTag(Base):
    """Many-to-many relationship between documents and tags"""
    __tablename__ = "document_tags"

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_doc_tags_doc', 'document_id'),
        Index('idx_doc_tags_tag', 'tag_id'),
    )


class Notification(Base):
    """User notifications"""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    action_url = Column(Text, nullable=True)
    action_text = Column(String(100), nullable=True)
    related_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    related_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, nullable=False, server_default='false')
    read_at = Column(DateTime(timezone=True), nullable=True)
    priority = Column(String(20), nullable=False, server_default='normal')
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_notifications_user', 'user_id', 'is_read', sa.text('created_at DESC')),
        Index('idx_notifications_type', 'notification_type'),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name='check_priority'),
    )


class SearchHistory(Base):
    """Search history for analytics and suggestions"""
    __tablename__ = "search_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    search_query = Column(Text, nullable=False)
    search_type = Column(String(50), nullable=True)
    filters = Column(Text, nullable=True)
    results_count = Column(Integer, nullable=True)
    clicked_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    click_position = Column(Integer, nullable=True)
    search_duration_ms = Column(Integer, nullable=True)
    no_results_found = Column(Boolean, nullable=False, server_default='false')
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_search_history_user', 'user_id', sa.text('created_at DESC')),
    )