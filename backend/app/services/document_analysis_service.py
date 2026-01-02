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
            # Get user's preferred document languages BEFORE OCR to use as language hint
            # Use Tesseract multilingual mode: all user languages simultaneously (e.g., 'eng+deu+rus+fra')
            # This allows Tesseract to automatically pick the best matching language

            # Get language mapping from database (no hardcoded values)
            lang_mapping = ocr_service.get_supported_languages(db)

            # Build multilingual language hint from user preferences
            tesseract_langs = []
            if user_id:
                from app.database.models import User
                user = db.get(User, UUID(user_id))
                if user and user.preferred_doc_languages:
                    # Only include languages that exist in database mapping
                    tesseract_langs = [lang_mapping[lang] for lang in user.preferred_doc_languages if lang in lang_mapping]

            # Build language hint string
            if tesseract_langs:
                language_hint = '+'.join(tesseract_langs)
                logger.info(f"[OCR LANG HINT] Using multilingual OCR with languages: {language_hint}")
            else:
                # Use first language from database as ultimate fallback
                language_hint = list(lang_mapping.values())[0] if lang_mapping else 'eng'
                logger.info(f"[OCR LANG HINT] No user preferences, using database default: {language_hint}")

            extracted_text, ocr_confidence = ocr_service.extract_text(
                file_content,
                mime_type,
                db,
                language=language_hint  # Pass language hint for scanned PDFs
            )

            if not extracted_text or len(extracted_text.strip()) < 10:
                raise ValueError("Unable to extract meaningful text from document")

            detected_language = await language_detection_service.detect_language(extracted_text, db)
            logger.info(f"[LANG DEBUG] Detected language: {detected_language} for document: {file_name}")

            # Check if detected language is in user's preferred languages
            language_warning = None
            if user_id:
                from app.database.models import User
                user = db.get(User, UUID(user_id))
                if user and user.preferred_doc_languages:
                    if detected_language not in user.preferred_doc_languages:
                        # Get language names from system settings
                        from app.database.models import SystemSetting
                        from sqlalchemy import select
                        import json

                        lang_metadata_result = db.execute(
                            select(SystemSetting.setting_value).where(
                                SystemSetting.setting_key == 'language_metadata'
                            )
                        ).scalar_one_or_none()

                        lang_name = detected_language.upper()
                        if lang_metadata_result:
                            try:
                                metadata = json.loads(lang_metadata_result)
                                if detected_language in metadata:
                                    lang_name = metadata[detected_language]['native_name']
                            except:
                                pass

                        language_warning = (
                            f"Document detected in {lang_name} ({detected_language}), which is not in your "
                            f"preferred document languages. You can add it in Settings."
                        )

            # STOPWORD FILTERING:
            # Use detected document language for stop word filtering, not user's preferred languages
            # User preferences are for UI/OCR hints, not for filtering keywords in an already-detected document
            logger.info(f"[STOPWORD DEBUG] Loading stopwords for detected document language: {detected_language}")

            # Load stopwords for the detected document language
            combined_stopwords = keyword_extraction_service.get_stop_words(db, detected_language)
            logger.info(f"[STOPWORD DEBUG] Loaded {len(combined_stopwords)} stopwords for language '{detected_language}'")

            # Extract named entities FIRST (people, organizations, addresses)
            # Request both accepted and rejected entities for keyword conversion
            from app.services.entity_extraction_service import entity_extraction_service
            entity_result = entity_extraction_service.extract_entities(
                text=extracted_text,
                language=detected_language,
                extract_addresses=True,
                db=db,  # Pass database session for filtering
                return_rejected=True  # Get rejected ORG entities for keyword conversion
            )

            # Extract accepted and rejected entities from result
            extracted_entities = entity_result['accepted']
            rejected_entities = entity_result['rejected']

            # Deduplicate accepted entities
            extracted_entities = entity_extraction_service.deduplicate_entities(extracted_entities)
            logger.info(f"[ENTITY DEBUG] Extracted {len(extracted_entities)} unique entities, {len(rejected_entities)} rejected for keyword conversion")
            for ent in extracted_entities[:5]:  # Log first 5 entities
                logger.info(f"[ENTITY DEBUG]   - {ent.entity_type}: {ent.entity_value} (confidence: {ent.confidence})")

            # Build exclusion set from accepted entities to prevent duplication in keywords
            # Normalize entity values to match keyword tokenization (lowercase, split multi-word entities)
            entity_exclusion_set = set()
            for entity in extracted_entities:
                # Add full entity value (for single-word entities like emails)
                entity_exclusion_set.add(entity.entity_value.lower())

                # Also add individual words from multi-word entities (e.g., "Acme Corp" → "acme", "corp")
                entity_words = re.findall(r'\b[a-zа-яäöüß]{3,}\b', entity.entity_value.lower(), re.IGNORECASE)
                entity_exclusion_set.update(entity_words)

            logger.info(f"[ENTITY EXCLUSION] Built exclusion set with {len(entity_exclusion_set)} entity-based tokens to prevent keyword duplication")

            # Extract keywords AFTER entity extraction, excluding entity values
            keywords = keyword_extraction_service.extract_keywords(
                text=extracted_text,
                db=db,
                language=detected_language,
                stopwords=combined_stopwords,
                excluded_entities=entity_exclusion_set,  # NEW: Exclude entity values from keywords
                max_keywords=50,  # Reasonable limit to prevent OCR garbage overload
                min_frequency=2,  # Filter out rare OCR errors that appear only once
                user_id=user_id,
                rejected_entities=rejected_entities  # Pass rejected ORG entities for conversion
            )

            keyword_strings = [kw[0] for kw in keywords]
            logger.info(f"[KEYWORD DEBUG] Extracted {len(keyword_strings)} keywords using combined stopwords, top 10: {keyword_strings[:10]}")

            primary_date_result = date_extraction_service.extract_primary_date(
                text=extracted_text,
                db=db,
                language=detected_language
            )

            # Convert user_id string to UUID for classification service
            user_uuid = UUID(user_id) if user_id else None

            # Classify using multi-language keywords - get ALL close matches
            classification_results = classification_service.classify_document(
                document_keywords=keyword_strings,
                db=db,
                language=detected_language,
                user_id=user_uuid
            )

            # Get multiple suggested categories if they match closely
            suggested_categories_list = classification_service.get_suggested_categories(
                classification_results=classification_results,
                db=db,
                max_categories=3
            )

            # Get primary category (fallback to OTHER if needed)
            suggested_category = None
            if suggested_categories_list:
                # Use the top category from multi-category matches
                suggested_category = suggested_categories_list[0]
                logger.info(f"[ANALYSIS DEBUG] Selected {len(suggested_categories_list)} categories for assignment")
            else:
                # No confident match - fallback to OTHER
                logger.info(f"[ANALYSIS DEBUG] No confident matches, using fallback to OTHER")
                suggested_category = classification_service.suggest_category(
                    document_keywords=keyword_strings,
                    db=db,
                    language=detected_language,
                    user_id=user_uuid,
                    fallback_to_other=True
                )
                suggested_categories_list = [suggested_category] if suggested_category else []

            # Filter and validate all keywords before creating response (no arbitrary limit)
            validated_keywords = []
            for idx, kw in enumerate(keywords):
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

            logger.info(f"Validated {len(validated_keywords)}/{len(keywords)} keywords for response")

            # Note: Standardized filename will be generated during confirmation
            # when we have the confirmed primary category code
            # Format: YYYYMMDD_HHMMSS_CategoryCode_OriginalName.ext

            analysis_result = {
                'extracted_text': extracted_text[:2000],
                'full_text_length': len(extracted_text),
                'ocr_confidence': round(ocr_confidence * 100, 1) if ocr_confidence < 1.0 else None,
                'keywords': validated_keywords,
                'detected_language': detected_language,
                'language_warning': language_warning,
                'document_date': None,
                'document_date_type': None,
                'document_date_confidence': None,
                'suggested_category_id': None,
                'suggested_category_name': None,
                'classification_confidence': None,
                'matched_keywords': [],
                'suggested_categories': [],  # NEW: All close-matching categories
                'entities': [  # NEW: Extracted named entities
                    {
                        'type': ent.entity_type,
                        'value': ent.entity_value,
                        'confidence': ent.confidence,
                        'method': ent.extraction_method
                    } for ent in extracted_entities
                ],
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

            # Add all suggested categories (multi-category support)
            if suggested_categories_list:
                # Primary category (for backward compatibility)
                cat_id, cat_name, confidence, matched = suggested_category
                analysis_result['suggested_category_id'] = str(cat_id)
                analysis_result['suggested_category_name'] = cat_name
                analysis_result['classification_confidence'] = round(confidence * 100, 1)
                analysis_result['matched_keywords'] = matched[:10]

                # All suggested categories
                analysis_result['suggested_categories'] = [
                    {
                        'category_id': str(cat[0]),
                        'category_name': cat[1],
                        'confidence': round(cat[2] * 100, 1),
                        'matched_keywords': cat[3][:5]  # Top 5 matched keywords per category
                    }
                    for cat in suggested_categories_list
                ]

                if len(suggested_categories_list) > 1:
                    logger.info(f"[ANALYSIS DEBUG] ✅ Suggested {len(suggested_categories_list)} categories (multi-match): {', '.join([c[1] for c in suggested_categories_list])}")
                    logger.info(f"[ANALYSIS DEBUG] Primary: {cat_name} (confidence: {confidence:.1%}, matched: {len(matched)})")
                else:
                    logger.info(f"[ANALYSIS DEBUG] ✅ Suggested category: {cat_name} (confidence: {confidence:.1%}, matched: {len(matched)})")
            else:
                logger.warning(f"[ANALYSIS DEBUG] ⚠️  No category suggested for document (this should never happen if fallback_to_other=True)")

            logger.info(f"Document analyzed: {file_name}, language={detected_language}, keywords={len(keywords)}")
            return analysis_result

        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            raise


# Global instance
document_analysis_service = DocumentAnalysisService()