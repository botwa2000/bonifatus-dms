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
                return self._extract_text_from_image(file_content)
            elif mime_type == 'text/plain':
                return file_content.decode('utf-8', errors='ignore')
            elif 'word' in mime_type:
                return self._extract_text_from_word(file_content)
            else:
                raise ValueError(f"Unsupported file type for text extraction: {mime_type}")
                
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        text = ""
        
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            raise ValueError("Failed to extract text from PDF")
    
    def _extract_text_from_image(self, file_content: bytes) -> str:
        """Extract text from image using OCR"""
        try:
            # TODO: Implement proper OCR using Google Vision API or Tesseract
            # For now, return placeholder
            logger.warning("OCR not yet implemented - returning placeholder")
            return "OCR text extraction not yet implemented"
            
        except Exception as e:
            logger.error(f"Image text extraction failed: {e}")
            raise ValueError("Failed to extract text from image")
    
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