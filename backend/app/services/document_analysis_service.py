# backend/app/services/document_analysis_service.py
"""
Document analysis service - database-driven, ML-powered
Zero hardcoded values, learns from user feedback
Updated to use new OCR, keyword extraction, and classification services
"""

import logging
import io
import re
from typing import Optional, Dict, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.ocr_service import ocr_service
from app.services.keyword_extraction_service import keyword_extraction_service
from app.services.classification_service import classification_service
from app.services.date_extraction_service import date_extraction_service
from app.services.language_detection_service import language_detection_service

logger = logging.getLogger(__name__)


class DocumentAnalysisService:
    """Analyzes documents with ML-based keyword extraction and categorization"""

    async def analyze_document(
        self,
        file_content: bytes,
        file_name: str,
        mime_type: str,
        db: Session,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Analyze document and extract metadata with ML

        Args:
            file_content: Raw file bytes
            file_name: Original filename
            mime_type: MIME type
            db: Database session
            user_id: User ID for custom categories (optional)

        Returns:
            Analysis result with keywords, language, suggested category, date
        """
        try:
            extracted_text, ocr_confidence = ocr_service.extract_text(
                file_content,
                mime_type,
                db
            )

            if not extracted_text or len(extracted_text.strip()) < 10:
                raise ValueError("Unable to extract meaningful text from document")

            detected_language = await language_detection_service.detect_language(extracted_text, db)

            keywords = keyword_extraction_service.extract_keywords(
                text=extracted_text,
                db=db,
                language=detected_language,
                max_keywords=50
            )

            keyword_strings = [kw[0] for kw in keywords]

            primary_date_result = date_extraction_service.extract_primary_date(
                text=extracted_text,
                db=db,
                language=detected_language
            )

            # Convert user_id string to UUID for classification service
            user_uuid = UUID(user_id) if user_id else None

            suggested_category = classification_service.suggest_category(
                document_keywords=keyword_strings,
                db=db,
                language=detected_language,
                user_id=user_uuid
            )

            # Filter and validate keywords before creating response
            validated_keywords = []
            for idx, kw in enumerate(keywords[:20]):
                if not kw or len(kw) != 3:
                    logger.warning(f"Skipping invalid keyword tuple at index {idx}: kw={repr(kw)}, type={type(kw).__name__}, len={len(kw) if kw else 'N/A'}")
                    continue

                word, count, relevance = kw[0], kw[1], kw[2]

                if not word or not isinstance(word, str) or len(word.strip()) == 0:
                    logger.warning(f"Skipping keyword at index {idx} with invalid word: word={repr(word)}, type={type(word).__name__ if word is not None else 'NoneType'}, count={count}, relevance={relevance}")
                    continue

                if count is None or not isinstance(count, int) or count < 1:
                    logger.warning(f"Skipping keyword at index {idx} '{word}' with invalid count: count={repr(count)}, type={type(count).__name__ if count is not None else 'NoneType'}, relevance={relevance}")
                    continue

                if relevance is None or not isinstance(relevance, (int, float)):
                    logger.warning(f"Skipping keyword at index {idx} '{word}' with invalid relevance: relevance={repr(relevance)}, type={type(relevance).__name__ if relevance is not None else 'NoneType'}, count={count}")
                    continue

                validated_keywords.append({'word': word, 'count': count, 'relevance': relevance})

            logger.info(f"Validated {len(validated_keywords)}/20 keywords for response")

            # Note: Standardized filename will be generated during confirmation
            # when we have the confirmed primary category code
            # Format: YYYYMMDD_HHMMSS_CategoryCode_OriginalName.ext

            analysis_result = {
                'extracted_text': extracted_text[:2000],
                'full_text_length': len(extracted_text),
                'ocr_confidence': round(ocr_confidence * 100, 1) if ocr_confidence < 1.0 else None,
                'keywords': validated_keywords,
                'detected_language': detected_language,
                'document_date': None,
                'document_date_type': None,
                'document_date_confidence': None,
                'suggested_category_id': None,
                'suggested_category_name': None,
                'classification_confidence': None,
                'matched_keywords': [],
                'original_filename': file_name,
                'file_info': {
                    'name': file_name,
                    'size': len(file_content),
                    'type': mime_type
                }
            }

            if primary_date_result:
                date_val, date_type, date_conf = primary_date_result
                analysis_result['document_date'] = date_val.isoformat()
                analysis_result['document_date_type'] = date_type
                analysis_result['document_date_confidence'] = round(date_conf * 100, 1)

            if suggested_category:
                cat_id, cat_name, confidence, matched = suggested_category
                analysis_result['suggested_category_id'] = str(cat_id)
                analysis_result['suggested_category_name'] = cat_name
                analysis_result['classification_confidence'] = round(confidence * 100, 1)
                analysis_result['matched_keywords'] = matched[:10]

            logger.info(f"Document analyzed: {file_name}, language={detected_language}, keywords={len(keywords)}")
            return analysis_result

        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            raise


# Global instance
document_analysis_service = DocumentAnalysisService()