"""
OCR Service for Bonifatus DMS
Extracts text from scanned documents and images using Tesseract OCR
Language support loaded dynamically from system_settings
"""

import io
import logging
import re
from typing import Optional, Tuple, Dict
from PIL import Image
import pytesseract
import cv2
import numpy as np
import fitz  # PyMuPDF
from spellchecker import SpellChecker
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from images and scanned PDFs"""

    def __init__(self):
        """Initialize OCR service"""
        self._language_cache: Optional[Dict[str, str]] = None
        self._spell_checkers: Dict[str, SpellChecker] = {}
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Tesseract: {e}")
            raise

    def get_supported_languages(self, db: Session) -> Dict[str, str]:
        """
        Load supported OCR languages from system_settings table
        Returns dict mapping language codes to Tesseract language codes
        Example: {'en': 'eng', 'de': 'deu', 'ru': 'rus'}
        """
        if self._language_cache is not None:
            return self._language_cache

        try:
            from app.database.models import SystemSetting

            result = db.query(SystemSetting).filter(
                SystemSetting.setting_key == 'ocr_supported_languages'
            ).first()

            if result:
                import json
                self._language_cache = json.loads(result.setting_value)
                logger.info(f"Loaded OCR languages from database: {list(self._language_cache.keys())}")
            else:
                self._language_cache = {'en': 'eng', 'de': 'deu', 'ru': 'rus'}
                logger.warning("OCR languages not found in database, using defaults")

            return self._language_cache

        except Exception as e:
            logger.error(f"Failed to load OCR languages from database: {e}")
            return {'en': 'eng', 'de': 'deu', 'ru': 'rus'}

    def clear_language_cache(self):
        """Clear cached language mappings (useful after database updates)"""
        self._language_cache = None

    def get_spell_checker(self, language: str) -> SpellChecker:
        """
        Get or create spell checker for a language
        Caches spell checkers for performance

        Args:
            language: Language code (en, de, ru)

        Returns:
            SpellChecker instance
        """
        # Map language codes to pyspellchecker codes
        lang_map = {
            'en': 'en',
            'de': 'de',
            'ru': 'ru',
            'es': 'es',
            'fr': 'fr',
            'pt': 'pt',
            'it': 'it'
        }

        spell_lang = lang_map.get(language, 'en')

        if spell_lang not in self._spell_checkers:
            try:
                self._spell_checkers[spell_lang] = SpellChecker(language=spell_lang)
                logger.debug(f"Initialized spell checker for language: {spell_lang}")
            except Exception as e:
                logger.warning(f"Failed to initialize spell checker for {spell_lang}, using 'en': {e}")
                self._spell_checkers[spell_lang] = SpellChecker(language='en')

        return self._spell_checkers[spell_lang]

    def assess_text_quality(self, text: str, language: str = 'en') -> Tuple[float, Dict[str, float]]:
        """
        Assess the quality of extracted text using spell-checking
        Detects OCR errors by checking for misspelled words

        Args:
            text: Extracted text to assess
            language: Language code for spell checking

        Returns:
            Tuple of (quality_score, metrics_dict)
            quality_score: 1.0 = perfect, 0.0 = garbage
        """
        if not text or len(text.strip()) < 10:
            return 0.0, {"reason": "text_too_short"}

        metrics = {}

        # Basic character validation (fast check)
        total_chars = len(text)
        letters = len(re.findall(r'[a-zA-ZäöüßÄÖÜа-яА-Я]', text))
        digits = len(re.findall(r'\d', text))
        spaces = len(re.findall(r'\s', text))
        punctuation = len(re.findall(r'[.,!?;:()\-"]', text))

        valid_chars = letters + digits + spaces + punctuation
        valid_ratio = valid_chars / total_chars if total_chars > 0 else 0
        metrics['valid_char_ratio'] = valid_ratio

        # If too many invalid characters, fail fast
        if valid_ratio < 0.7:
            metrics['quality_score'] = valid_ratio * 0.5
            logger.debug(f"Text quality (fast fail): {metrics['quality_score']:.2f}")
            return metrics['quality_score'], metrics

        # Extract words for spell checking (min 3 chars)
        words = re.findall(r'\b[a-zA-ZäöüßÄÖÜа-яА-Я]{3,}\b', text.lower())

        if len(words) < 5:
            metrics['quality_score'] = 0.5
            metrics['reason'] = 'too_few_words'
            return 0.5, metrics

        # Spell check (sample up to 100 words for performance)
        sample_size = min(100, len(words))
        sample_words = set(words[:sample_size])  # Use set to avoid duplicates

        try:
            spell = self.get_spell_checker(language)
            misspelled = spell.unknown(sample_words)

            error_rate = len(misspelled) / len(sample_words) if sample_words else 1.0
            metrics['spelling_error_rate'] = error_rate
            metrics['total_words_checked'] = len(sample_words)
            metrics['misspelled_words'] = len(misspelled)

            # Quality score based on spelling accuracy
            # < 15% errors = excellent (0.95-1.0)
            # 15-30% errors = good (0.7-0.95)
            # 30-50% errors = poor (0.5-0.7)
            # > 50% errors = garbage (0.0-0.5)

            if error_rate < 0.15:
                spelling_score = 1.0 - (error_rate * 0.33)  # 0.95-1.0
            elif error_rate < 0.30:
                spelling_score = 0.95 - ((error_rate - 0.15) * 1.67)  # 0.7-0.95
            elif error_rate < 0.50:
                spelling_score = 0.7 - ((error_rate - 0.30) * 1.0)  # 0.5-0.7
            else:
                spelling_score = max(0.0, 0.5 - (error_rate - 0.5))  # 0.0-0.5

            metrics['spelling_score'] = spelling_score

        except Exception as e:
            logger.warning(f"Spell check failed: {e}")
            # Fall back to basic word validation
            valid_words = [w for w in words if re.search(r'[aeiouäöüАЕИОУЫЭЮЯаеиоуыэюя]', w, re.IGNORECASE)]
            word_quality = len(valid_words) / len(words) if words else 0
            spelling_score = word_quality
            metrics['spelling_score'] = spelling_score
            metrics['spelling_error_rate'] = 1.0 - word_quality

        # Final quality score: weighted combination
        quality_score = (
            valid_ratio * 0.2 +      # Basic char validation
            spelling_score * 0.8      # Spelling accuracy (most important)
        )

        metrics['quality_score'] = quality_score

        logger.debug(f"Text quality: {quality_score:.2f} (spelling: {spelling_score:.2f}, error_rate: {error_rate:.2%})")

        return quality_score, metrics

    def preprocess_image(self, image: Image.Image, enhance: bool = False) -> Image.Image:
        """
        Preprocess image for better OCR accuracy
        - Convert to grayscale
        - Apply denoising
        - Apply adaptive thresholding
        - Optional: morphological operations for enhanced preprocessing
        """
        try:
            img_array = np.array(image)

            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

            # Apply adaptive thresholding (better for varying lighting)
            threshold = cv2.adaptiveThreshold(
                denoised,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=11,
                C=2
            )

            # Enhanced preprocessing: morphological operations
            if enhance:
                # Remove small noise
                kernel = np.ones((1, 1), np.uint8)
                threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
                threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)

            preprocessed_image = Image.fromarray(threshold)

            logger.debug(f"Image preprocessing completed (enhanced={enhance})")
            return preprocessed_image

        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {e}")
            return image

    def extract_text_from_image(
        self,
        image: Image.Image,
        db: Session,
        language: str = 'en',
        preprocess: bool = True
    ) -> Tuple[str, float]:
        """
        Extract text from an image using Tesseract OCR

        Args:
            image: PIL Image object
            db: Database session for loading language config
            language: Language code (fallback to 'en' if not provided)
            preprocess: Whether to preprocess the image

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            supported_languages = self.get_supported_languages(db)
            tesseract_lang = supported_languages.get(language, 'eng')

            if preprocess:
                image = self.preprocess_image(image)

            custom_config = r'--oem 3 --psm 3'

            text = pytesseract.image_to_string(
                image,
                lang=tesseract_lang,
                config=custom_config
            )

            data = pytesseract.image_to_data(
                image,
                lang=tesseract_lang,
                output_type=pytesseract.Output.DICT
            )

            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            text = text.strip()

            logger.info(f"Extracted {len(text)} characters with {avg_confidence:.1f}% confidence (lang: {language})")

            return text, avg_confidence / 100.0

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", 0.0

    def is_scanned_pdf(self, pdf_file: bytes, language: str = 'en') -> Tuple[bool, float]:
        """
        Detect if a PDF is scanned (image-based) or native text
        Also returns text quality score if text is found

        Args:
            pdf_file: PDF file as bytes
            language: Language code for spell checking

        Returns:
            Tuple of (is_scanned, text_quality_score)
            is_scanned: True if PDF is scanned/poor quality, False if it contains good native text
            text_quality_score: Quality score of extracted text (0.0-1.0)
        """
        try:
            doc = fitz.open(stream=pdf_file, filetype="pdf")

            if len(doc) == 0:
                doc.close()
                return True, 0.0

            # Extract text from first page
            first_page = doc[0]
            text = first_page.get_text().strip()
            doc.close()

            if len(text) < 50:
                logger.debug("PDF appears to be scanned (< 50 chars)")
                return True, 0.0

            # Assess text quality with spell checking
            quality_score, metrics = self.assess_text_quality(text, language)

            logger.info(f"PDF text quality: {quality_score:.2f} (spelling errors: {metrics.get('spelling_error_rate', 0):.1%})")

            # Two-stage decision:
            # Stage 1: High quality (>0.85) - use embedded text (fast path)
            # Stage 2: Medium quality (0.6-0.85) - could go either way, use embedded for speed
            # Stage 3: Low quality (<0.6) - re-OCR for better results

            if quality_score < 0.6:
                logger.info(f"PDF has poor text quality ({quality_score:.2f}), will re-OCR")
                return True, quality_score

            logger.info(f"PDF has acceptable text quality ({quality_score:.2f}), using embedded text")
            return False, quality_score

        except Exception as e:
            logger.warning(f"Could not determine if PDF is scanned: {e}")
            return True, 0.0

    def extract_text_from_pdf(
        self,
        pdf_file: bytes,
        db: Session,
        language: str = 'en',
        max_pages: Optional[int] = None
    ) -> Tuple[str, float]:
        """
        Extract text from PDF (handles both native and scanned PDFs)
        Uses PyMuPDF for high-quality native text extraction
        Falls back to Tesseract OCR for scanned or poor-quality PDFs

        Args:
            pdf_file: PDF file as bytes
            db: Database session for loading language config
            language: Language code for OCR (fallback to 'en' if not provided)
            max_pages: Maximum number of pages to process (None for all)

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            is_scanned, text_quality = self.is_scanned_pdf(pdf_file, language)

            if not is_scanned:
                # Use PyMuPDF for native PDF text extraction (fast & high quality)
                doc = fitz.open(stream=pdf_file, filetype="pdf")
                pages_to_process = len(doc) if max_pages is None else min(max_pages, len(doc))

                text_parts = []
                for i in range(pages_to_process):
                    page = doc[i]
                    page_text = page.get_text()
                    if page_text:
                        text_parts.append(page_text)

                doc.close()
                full_text = "\n\n".join(text_parts)

                logger.info(f"Extracted text from native PDF ({pages_to_process} pages, quality: {text_quality:.2f})")
                return full_text.strip(), text_quality

            else:
                # Use Tesseract OCR for scanned/poor quality PDFs
                # Use PyMuPDF to render pages to images (no poppler dependency)
                doc = fitz.open(stream=pdf_file, filetype="pdf")
                pages_to_process = len(doc) if max_pages is None else min(max_pages, len(doc))

                text_parts = []
                confidences = []

                # Render at 300 DPI for better OCR quality
                zoom = 300 / 72
                mat = fitz.Matrix(zoom, zoom)

                for i in range(pages_to_process):
                    logger.debug(f"OCR processing page {i+1}/{pages_to_process}")

                    page = doc[i]

                    # Render page to image
                    pix = page.get_pixmap(matrix=mat)

                    # Convert to PIL Image
                    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    # Run OCR with preprocessing
                    page_text, confidence = self.extract_text_from_image(image, db, language, preprocess=True)

                    if page_text:
                        text_parts.append(page_text)
                        confidences.append(confidence)

                doc.close()

                full_text = "\n\n".join(text_parts)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                logger.info(f"OCR extracted text from scanned PDF ({pages_to_process} pages, {avg_confidence*100:.1f}% confidence)")

                return full_text.strip(), avg_confidence

        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return "", 0.0

    def extract_text(
        self,
        file_content: bytes,
        mime_type: str,
        db: Session,
        language: str = 'en'
    ) -> Tuple[str, float]:
        """
        Extract text from any supported document type

        Args:
            file_content: File content as bytes
            mime_type: MIME type of the file
            db: Database session for loading language config
            language: Language code for OCR (fallback to 'en' if detection fails)

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            if mime_type == 'application/pdf':
                return self.extract_text_from_pdf(file_content, db, language)

            elif mime_type.startswith('image/'):
                image = Image.open(io.BytesIO(file_content))

                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')

                return self.extract_text_from_image(image, db, language)

            else:
                logger.warning(f"Unsupported MIME type for OCR: {mime_type}")
                return "", 0.0

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return "", 0.0


ocr_service = OCRService()
