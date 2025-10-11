# backend/app/services/document_analysis_service.py
"""
Document analysis service - database-driven, ML-powered
Zero hardcoded values, learns from user feedback
"""

import logging
import re
import tempfile
import os
from typing import Optional, Dict, List, BinaryIO
import PyPDF2
from PIL import Image
import io

from app.services.ml_keyword_service import ml_keyword_service
from app.services.ml_category_service import ml_category_service
from app.services.language_detection_service import language_detection_service
from app.services.config_service import config_service

logger = logging.getLogger(__name__)


class DocumentAnalysisService:
    """Analyzes documents with ML-based keyword extraction and categorization"""
    
    async def analyze_document(
        self,
        file_content: bytes,
        file_name: str,
        mime_type: str,
        user_categories: List[Dict]
    ) -> Dict:
        """
        Analyze document and extract metadata with ML
        
        Args:
            file_content: Raw file bytes
            file_name: Original filename
            mime_type: MIME type
            user_categories: User's available categories
            
        Returns:
            Analysis result with keywords, language, suggested category
        """
        try:
            # Extract text based on file type
            extracted_text = await self._extract_text(file_content, mime_type)
            
            if not extracted_text or len(extracted_text.strip()) < 10:
                raise ValueError("Unable to extract meaningful text from document")
            
            # Detect language using database-driven service
            detected_language = await language_detection_service.detect_language(extracted_text)
            
            # Extract keywords using ML
            keywords = await ml_keyword_service.extract_keywords(
                text=extracted_text,
                language_code=detected_language
            )
            
            # Predict category using ML
            suggested_category_id, confidence = await ml_category_service.predict_category(
                text=extracted_text,
                keywords=keywords,
                language_code=detected_language,
                user_categories=user_categories
            )
            
            # Build analysis result
            analysis_result = {
                'extracted_text': extracted_text[:2000],  # Preview only
                'full_text_length': len(extracted_text),
                'keywords': keywords,
                'suggested_category_id': suggested_category_id,
                'confidence': round(confidence * 100, 1),  # Convert to percentage
                'detected_language': detected_language,
                'file_info': {
                    'name': file_name,
                    'size': len(file_content),
                    'type': mime_type
                }
            }
            
            logger.info(f"Document analyzed: {file_name}, language={detected_language}, keywords={len(keywords)}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            raise
    
    async def _extract_text(self, file_content: bytes, mime_type: str) -> str:
        """Extract text from various file types"""
        try:
            if mime_type == 'application/pdf':
                return self._extract_text_from_pdf(file_content)
            elif mime_type.startswith('image/'):
                logger.warning(f"Image OCR not implemented, attempting fallback")
                return self._extract_text_from_image(file_content)
            elif mime_type == 'text/plain':
                return file_content.decode('utf-8', errors='ignore')
            elif 'word' in mime_type or 'document' in mime_type:
                return self._extract_text_from_word(file_content)
            else:
                logger.error(f"Unsupported MIME type: {mime_type}")
                raise ValueError(f"Unsupported file type for text extraction: {mime_type}")
        except Exception as e:
            logger.error(f"Text extraction failed for {mime_type}: {e}")
            raise
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF with comprehensive error handling"""
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            if len(pdf_reader.pages) == 0:
                raise ValueError("PDF contains no pages")
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as page_error:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {page_error}")
                    continue
            
            combined_text = "\n".join(text_parts).strip()
            
            if not combined_text or len(combined_text) < 10:
                raise ValueError("No meaningful text extracted from PDF (possible scanned document)")
            
            logger.info(f"Extracted {len(combined_text)} characters from {len(pdf_reader.pages)} PDF pages")
            return combined_text
            
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    def _extract_text_from_image(self, file_content: bytes) -> str:
        """Extract text from image - OCR not yet fully implemented"""
        logger.warning("OCR implementation pending - Google Vision API integration required")
        raise ValueError("Image OCR not yet implemented. Please upload text-based PDFs or Word documents.")
    
    def _extract_text_from_word(self, file_content: bytes) -> str:
        """Extract text from Word document"""
        try:
            import docx
            
            doc_file = io.BytesIO(file_content)
            doc = docx.Document(doc_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Word text extraction failed: {e}")
            raise ValueError("Failed to extract text from Word document")


# Global instance
document_analysis_service = DocumentAnalysisService()