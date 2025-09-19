# backend/src/services/document_service.py
"""
Bonifatus DMS - Document Service
Document processing, categorization, and management business logic
OCR, keyword extraction, and AI-powered categorization
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_
from fastapi import UploadFile
from typing import Optional, Dict, Any, List
import hashlib
import os
import logging
from datetime import datetime
import fitz  # PyMuPDF for PDF processing
from PIL import Image
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import io
import re
from collections import Counter

from src.database.models import Document, User, Category, DocumentStatus, UserTier
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Download required NLTK data (run once)
try:
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk.download("wordnet", quiet=True)
    nltk.download("averaged_perceptron_tagger", quiet=True)
except Exception as e:
    logger.warning(f"NLTK download failed: {e}")


class DocumentService:
    """Service for document processing and management operations"""

    def __init__(self, db: Session):
        self.db = db
        self.lemmatizer = WordNetLemmatizer()

        # Load stopwords for multiple languages
        try:
            self.stopwords_en = set(stopwords.words("english"))
            self.stopwords_de = set(stopwords.words("german"))
        except Exception as e:
            logger.warning(f"Failed to load stopwords: {e}")
            self.stopwords_en = set()
            self.stopwords_de = set()

    async def validate_upload(
        self, user: User, file: UploadFile, max_size_mb: int = 50
    ) -> Dict[str, Any]:
        """
        Validate file upload against user limits and file constraints
        """
        try:
            # Check file size
            max_size_bytes = max_size_mb * 1024 * 1024
            if file.size and file.size > max_size_bytes:
                return {
                    "valid": False,
                    "error": f"File size exceeds {max_size_mb}MB limit",
                }

            # Check file type
            allowed_extensions = settings.app.allowed_file_types
            file_extension = os.path.splitext(file.filename)[1].lower()

            if file_extension not in allowed_extensions:
                return {
                    "valid": False,
                    "error": f"File type {file_extension} not supported",
                }

            # Check user tier limits
            tier_limits = self._get_user_tier_limits(user.tier)

            if (
                user.document_count >= tier_limits["document_limit"]
                and tier_limits["document_limit"] > 0
            ):
                return {
                    "valid": False,
                    "error": f"Document limit reached ({tier_limits['document_limit']} documents)",
                }

            # Check monthly upload limits
            if (
                user.monthly_uploads >= tier_limits["monthly_uploads"]
                and tier_limits["monthly_uploads"] > 0
            ):
                return {
                    "valid": False,
                    "error": f"Monthly upload limit reached ({tier_limits['monthly_uploads']} uploads)",
                }

            return {"valid": True}

        except Exception as e:
            logger.error(f"Upload validation failed: {e}")
            return {"valid": False, "error": "Validation failed"}

    async def create_document_record(
        self,
        user_id: int,
        file: UploadFile,
        category_id: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> Document:
        """
        Create initial document record in database
        """
        try:
            # Generate file hash for deduplication
            file.file.seek(0)
            file_content = file.file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            file.file.seek(0)  # Reset for later use

            # Generate unique filename if needed
            original_filename = file.filename
            filename = self._generate_unique_filename(original_filename)

            # Extract file extension and mime type
            file_extension = os.path.splitext(filename)[1].lower()
            mime_type = file.content_type or self._get_mime_type(file_extension)

            # Create document record
            document = Document(
                user_id=user_id,
                category_id=category_id,
                filename=filename,
                original_filename=original_filename,
                file_path="",  # Will be set after Google Drive upload
                google_drive_file_id="",  # Will be set after upload
                file_size_bytes=file.size or len(file_content),
                mime_type=mime_type,
                file_extension=file_extension,
                file_hash=file_hash,
                status=DocumentStatus.UPLOADING,
                title=title,
                description=description,
                user_keywords=keywords,
            )

            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)

            logger.info(f"Created document record {document.id} for user {user_id}")
            return document

        except Exception as e:
            logger.error(f"Failed to create document record: {e}")
            self.db.rollback()
            raise

    async def process_document_content(self, document: Document) -> bool:
        """
        Extract text, keywords, and metadata from document
        """
        try:
            # Extract text based on file type
            extracted_text = await self._extract_text_from_file(document)

            if extracted_text:
                document.extracted_text = extracted_text

                # Detect language
                document.language_detected = self._detect_language(extracted_text)

                # Extract keywords
                keywords = self._extract_keywords(
                    extracted_text, document.language_detected or "en"
                )
                document.extracted_keywords = keywords

                # Auto-generate title if not provided
                if not document.title:
                    document.title = self._generate_title_from_content(extracted_text)

                logger.info(f"Processed content for document {document.id}")
            else:
                logger.warning(f"No text extracted from document {document.id}")

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Document content processing failed for {document.id}: {e}")
            return False

    async def suggest_category(self, document: Document) -> Optional[Dict[str, Any]]:
        """
        AI-powered category suggestion based on document content
        """
        try:
            if not document.extracted_text and not document.user_keywords:
                return None

            # Get user's categories
            user_categories = (
                self.db.query(Category)
                .filter(
                    and_(
                        (
                            (Category.user_id == document.user_id)
                            | (Category.is_system_category == True)
                        ),
                        Category.is_active == True,
                    )
                )
                .all()
            )

            if not user_categories:
                return None

            # Combine text sources for analysis
            text_content = " ".join(
                filter(
                    None,
                    [
                        document.extracted_text,
                        document.title,
                        document.description,
                        " ".join(document.user_keywords or []),
                    ],
                )
            )

            # Simple keyword-based categorization
            best_category = None
            best_score = 0.0

            for category in user_categories:
                score = self._calculate_category_score(text_content, category)
                if score > best_score:
                    best_score = score
                    best_category = category

            if best_category and best_score > 0.1:  # Minimum confidence threshold
                return {
                    "category_id": best_category.id,
                    "confidence": min(best_score, 0.95),  # Cap confidence at 95%
                    "category_name": best_category.name_en,
                    "keywords_matched": self._get_matched_keywords(
                        text_content, best_category
                    ),
                }

            return None

        except Exception as e:
            logger.error(f"Category suggestion failed for document {document.id}: {e}")
            return None

    async def list_documents(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        List documents with filtering, sorting, and pagination
        """
        try:
            query = self.db.query(Document).filter(
                Document.user_id == filters["user_id"]
            )

            # Apply filters
            if filters.get("category_id"):
                query = query.filter(Document.category_id == filters["category_id"])

            if filters.get("status"):
                query = query.filter(Document.status == filters["status"])

            # Apply sorting
            sort_column = getattr(Document, filters.get("sort_by", "created_at"))
            if filters.get("sort_order", "desc") == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

            # Get total count
            total = query.count()

            # Apply pagination
            page = filters.get("page", 1)
            per_page = filters.get("per_page", 20)
            offset = (page - 1) * per_page

            documents = query.offset(offset).limit(per_page).all()

            # Format results
            formatted_documents = [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "original_filename": doc.original_filename,
                    "title": doc.title,
                    "file_size_bytes": doc.file_size_bytes,
                    "mime_type": doc.mime_type,
                    "status": doc.status.value,
                    "category": (
                        {
                            "id": doc.category.id,
                            "name_en": doc.category.name_en,
                            "name_de": doc.category.name_de,
                            "color": doc.category.color,
                        }
                        if doc.category
                        else None
                    ),
                    "is_favorite": doc.is_favorite,
                    "view_count": doc.view_count,
                    "created_at": doc.created_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat(),
                }
                for doc in documents
            ]

            return {"documents": formatted_documents, "total": total}

        except Exception as e:
            logger.error(f"List documents failed: {e}")
            return {"documents": [], "total": 0}

    async def _extract_text_from_file(self, document: Document) -> Optional[str]:
        """
        Extract text content from various file types
        """
        try:
            # For now, we'll implement PDF text extraction
            # In production, add support for other formats

            if document.mime_type == "application/pdf":
                return await self._extract_text_from_pdf(document)

            elif document.mime_type.startswith("image/"):
                # TODO: Implement OCR for images
                logger.info(f"OCR processing needed for document {document.id}")
                return None

            elif document.mime_type.startswith("text/"):
                # TODO: Handle text files
                logger.info(f"Text file processing needed for document {document.id}")
                return None

            else:
                logger.warning(
                    f"Unsupported file type for text extraction: {document.mime_type}"
                )
                return None

        except Exception as e:
            logger.error(f"Text extraction failed for document {document.id}: {e}")
            return None

    async def _extract_text_from_pdf(self, document: Document) -> Optional[str]:
        """
        Extract text from PDF using PyMuPDF
        """
        try:
            # Note: In production, download file from Google Drive
            # For now, return placeholder
            logger.info(f"PDF text extraction for document {document.id}")
            return f"Extracted text from PDF: {document.filename}"

        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return None

    def _extract_keywords(self, text: str, language: str = "en") -> List[str]:
        """
        Extract keywords using database-driven configuration and NLTK
        """
        try:
            if not text or len(text.strip()) < 10:
                return []

            # Get supported languages from database settings
            from src.database.models import SystemSettings

            system_settings = self.db.query(SystemSettings).first()
            supported_languages = (
                system_settings.supported_languages if system_settings else ["en", "de"]
            )

            # Validate language is supported
            if language not in supported_languages:
                language = system_settings.default_language if system_settings else "en"

            # Clean text and tokenize
            import re

            clean_text = re.sub(r"[^\w\s]", " ", text.lower())
            words = clean_text.split()

            # Use NLTK stopwords (not hardcoded)
            stop_words = set()
            try:
                if language == "en":
                    stop_words = self.stopwords_en
                elif language == "de":
                    stop_words = self.stopwords_de
            except Exception:
                # Fallback if NLTK not available
                pass

            # Filter meaningful words
            meaningful_words = [
                word
                for word in words
                if len(word) >= 3 and word not in stop_words and word.isalpha()
            ]

            # Get domain keywords from existing categories in database
            domain_keywords = self._get_domain_keywords_from_db()

            # Extract frequent words
            from collections import Counter

            word_counts = Counter(meaningful_words)
            frequent_keywords = [word for word, count in word_counts.most_common(10)]

            # Find domain-specific keywords from database
            found_domain_keywords = [
                word for word in meaningful_words if word in domain_keywords
            ]

            # Combine and deduplicate
            all_keywords = list(set(frequent_keywords + found_domain_keywords))

            return all_keywords[:15]  # Return up to 15 keywords

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []  # Return empty list on error

    def _get_domain_keywords_from_db(self) -> set:
        """
        Get domain-specific keywords from category keywords stored in database
        """
        try:
            from src.database.models import Category

            # Get all category keywords from database
            categories = (
                self.db.query(Category).filter(Category.keywords.isnot(None)).all()
            )

            domain_keywords = set()
            for category in categories:
                if category.keywords:
                    # Split comma-separated keywords and add to set
                    keywords = [
                        kw.strip().lower() for kw in category.keywords.split(",")
                    ]
                    domain_keywords.update(keywords)

            return domain_keywords

        except Exception as e:
            logger.error(f"Failed to get domain keywords from database: {e}")
            return set()

    def _detect_language(self, text: str) -> str:
        """
        Simple language detection for German/English
        """
        try:
            if not text:
                return "en"

            # Simple heuristic based on common words
            german_indicators = [
                "und",
                "der",
                "die",
                "das",
                "ist",
                "haben",
                "sein",
                "mit",
                "für",
            ]
            english_indicators = [
                "and",
                "the",
                "is",
                "are",
                "have",
                "with",
                "for",
                "that",
                "this",
            ]

            text_lower = text.lower()
            german_count = sum(1 for word in german_indicators if word in text_lower)
            english_count = sum(1 for word in english_indicators if word in text_lower)

            return "de" if german_count > english_count else "en"

        except Exception:
            return "en"

    def _calculate_category_score(self, text: str, category: Category) -> float:
        """
        Calculate relevance score for a category based on text content
        """
        try:
            if not category.keywords:
                return 0.0

            text_lower = text.lower()
            category_keywords = [
                kw.strip().lower() for kw in category.keywords.split(",")
            ]

            matches = 0
            total_keywords = len(category_keywords)

            for keyword in category_keywords:
                if keyword in text_lower:
                    # Weight longer keywords more heavily
                    weight = min(len(keyword) / 10, 2.0)
                    matches += weight

            # Normalize score
            if total_keywords > 0:
                score = matches / total_keywords
                return min(score, 1.0)

            return 0.0

        except Exception as e:
            logger.error(f"Category score calculation failed: {e}")
            return 0.0

    def _get_matched_keywords(self, text: str, category: Category) -> List[str]:
        """
        Get list of keywords that matched for a category
        """
        try:
            if not category.keywords:
                return []

            text_lower = text.lower()
            category_keywords = [
                kw.strip().lower() for kw in category.keywords.split(",")
            ]

            matched = [kw for kw in category_keywords if kw in text_lower]
            return matched

        except Exception:
            return []

    def _generate_title_from_content(self, text: str, max_length: int = 100) -> str:
        """
        Generate a title from document content
        """
        try:
            if not text:
                return "Untitled Document"

            # Take first sentence or first line
            first_sentence = re.split(r"[.!?]", text.strip())[0]

            if len(first_sentence) > max_length:
                first_sentence = first_sentence[:max_length].rsplit(" ", 1)[0] + "..."

            return first_sentence.strip() or "Untitled Document"

        except Exception:
            return "Untitled Document"

    def _generate_unique_filename(self, original_filename: str) -> str:
        """
        Generate unique filename to avoid conflicts
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        name, extension = os.path.splitext(original_filename)
        return f"{name}_{timestamp}{extension}"

    def _get_mime_type(self, file_extension: str) -> str:
        """
        Get MIME type from file extension
        """
        mime_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".bmp": "image/bmp",
        }
        return mime_types.get(file_extension.lower(), "application/octet-stream")

    def _get_user_tier_limits(self, tier: UserTier) -> Dict[str, int]:
        """
        Get limits based on user tier
        """
        limits = {
            UserTier.FREE: {"document_limit": 100, "monthly_uploads": 50},
            UserTier.PREMIUM_TRIAL: {"document_limit": 500, "monthly_uploads": 200},
            UserTier.PREMIUM: {
                "document_limit": 0,  # Unlimited
                "monthly_uploads": 0,  # Unlimited
            },
            UserTier.ADMIN: {
                "document_limit": 0,  # Unlimited
                "monthly_uploads": 0,  # Unlimited
            },
        }

        return limits.get(tier, limits[UserTier.FREE])
