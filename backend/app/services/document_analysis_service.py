# backend/app/services/document_analysis_service.py
"""
Document analysis service for OCR, keyword extraction, and category suggestion.
Provides AI-powered document processing before final storage.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import PyPDF2
from io import BytesIO

logger = logging.getLogger(__name__)


class DocumentAnalysisService:
    """Service for analyzing documents and extracting metadata"""

    def __init__(self):
        # Common stop words to filter from keywords
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'der', 'die', 'das', 'und', 'oder', 'aber', 'in', 'auf', 'von',  # German
            'и', 'или', 'но', 'в', 'на', 'от', 'для', 'с'  # Russian
        }

        # Category keywords mapping for suggestion
        self.category_keywords = {
            'insurance': [
                'insurance', 'policy', 'premium', 'coverage', 'claim', 'benefit',
                'policyholder', 'insured', 'deductible', 'liability',
                'versicherung', 'police', 'prämie', 'deckung', 'anspruch',  # German
                'страховка', 'полис', 'премия', 'покрытие', 'претензия'  # Russian
            ],
            'legal': [
                'contract', 'agreement', 'legal', 'court', 'lawsuit', 'attorney',
                'law', 'regulation', 'compliance', 'litigation', 'settlement',
                'vertrag', 'vereinbarung', 'gericht', 'klage', 'rechtsanwalt',  # German
                'договор', 'соглашение', 'суд', 'иск', 'адвокат', 'закон'  # Russian
            ],
            'real_estate': [
                'property', 'real estate', 'lease', 'rent', 'mortgage', 'deed',
                'apartment', 'house', 'building', 'landlord', 'tenant',
                'immobilie', 'miete', 'hypothek', 'wohnung', 'haus',  # German
                'недвижимость', 'аренда', 'ипотека', 'квартира', 'дом'  # Russian
            ],
            'banking': [
                'bank', 'account', 'transaction', 'payment', 'transfer', 'loan',
                'credit', 'debit', 'balance', 'statement', 'finance',
                'konto', 'überweisung', 'zahlung', 'kredit', 'saldo',  # German
                'банк', 'счет', 'платеж', 'перевод', 'кредит', 'баланс'  # Russian
            ]
        }

    async def analyze_document(
        self,
        file_content: bytes,
        file_name: str,
        mime_type: str,
        user_categories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze document and extract metadata
        
        Args:
            file_content: Binary file content
            file_name: Original filename
            mime_type: MIME type of file
            user_categories: User's available categories
            
        Returns:
            Dictionary with extracted_text, keywords, suggested_category, confidence
        """
        try:
            # Extract text based on file type
            extracted_text = await self._extract_text(file_content, mime_type)
            
            # Extract keywords from text
            keywords = self._extract_keywords(extracted_text)
            
            # Suggest category based on keywords and content
            suggested_category, confidence = self._suggest_category(
                extracted_text, 
                keywords,
                user_categories
            )
            
            # Detect language
            detected_language = self._detect_language(extracted_text)
            
            return {
                'extracted_text': extracted_text[:5000],  # First 5000 chars for preview
                'full_text_length': len(extracted_text),
                'keywords': keywords[:20],  # Top 20 keywords
                'suggested_category_id': suggested_category,
                'confidence': confidence,
                'detected_language': detected_language,
                'file_info': {
                    'name': file_name,
                    'size': len(file_content),
                    'type': mime_type
                }
            }
            
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return {
                'extracted_text': '',
                'full_text_length': 0,
                'keywords': [],
                'suggested_category_id': None,
                'confidence': 0.0,
                'detected_language': 'unknown',
                'error': str(e),
                'file_info': {
                    'name': file_name,
                    'size': len(file_content),
                    'type': mime_type
                }
            }

    async def _extract_text(self, file_content: bytes, mime_type: str) -> str:
        """Extract text from document based on file type"""
        try:
            if mime_type == 'application/pdf':
                return self._extract_text_from_pdf(file_content)
            elif mime_type.startswith('text/'):
                return file_content.decode('utf-8', errors='ignore')
            else:
                # For images and other formats, return empty for now
                # TODO: Implement Google Vision OCR
                logger.warning(f"Text extraction not supported for {mime_type}")
                return ""
                
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""

    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return ""

    def _extract_keywords(self, text: str, max_keywords: int = 30) -> List[Dict[str, Any]]:
        """Extract keywords from text using frequency analysis"""
        if not text:
            return []
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter stop words
        filtered_words = [w for w in words if w not in self.stop_words]
        
        # Count word frequency
        word_counts = Counter(filtered_words)
        
        # Get top keywords with relevance scores
        total_words = len(filtered_words)
        keywords = []
        
        for word, count in word_counts.most_common(max_keywords):
            relevance = round(count / total_words * 100, 2)
            keywords.append({
                'word': word,
                'count': count,
                'relevance': relevance
            })
        
        return keywords

    def _suggest_category(
        self,
        text: str,
        keywords: List[Dict[str, Any]],
        user_categories: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], float]:
        """
        Suggest category based on text content and keywords
        
        Returns:
            Tuple of (category_id, confidence_score)
        """
        if not text or not user_categories:
            return None, 0.0
        
        text_lower = text.lower()
        category_scores = {}
        
        # Calculate scores for each category
        for category in user_categories:
            category_id = category.get('id')
            category_ref = category.get('reference_key', '').lower()
            
            # Get keywords for this category type
            category_keywords = self.category_keywords.get(category_ref, [])
            
            # Count keyword matches
            matches = sum(1 for kw in category_keywords if kw in text_lower)
            
            if matches > 0:
                # Calculate confidence based on matches
                confidence = min(matches / len(category_keywords) * 100, 95)
                category_scores[category_id] = confidence
        
        # Return category with highest score
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            return best_category[0], round(best_category[1], 2)
        
        # Default to "Other" category if available
        other_category = next(
            (cat for cat in user_categories if cat.get('reference_key') == 'other'),
            None
        )
        
        if other_category:
            return other_category['id'], 50.0
        
        # Return first category as fallback
        if user_categories:
            return user_categories[0]['id'], 40.0
        
        return None, 0.0

    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns"""
        if not text:
            return 'unknown'
        
        # Check for Cyrillic characters (Russian)
        cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        if cyrillic_count > len(text) * 0.1:
            return 'ru'
        
        # Check for German umlauts and ß
        german_chars = sum(1 for c in text if c in 'äöüßÄÖÜ')
        if german_chars > len(text) * 0.01:
            return 'de'
        
        # Default to English
        return 'en'


# Global service instance
document_analysis_service = DocumentAnalysisService()