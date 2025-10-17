"""
OCR Service for Bonifatus DMS
Extracts text from scanned documents and images using Tesseract OCR
Language support loaded dynamically from system_settings
"""

import io
import logging
from typing import Optional, Tuple, Dict
from PIL import Image
import pytesseract
import cv2
import numpy as np
from PyPDF2 import PdfReader
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from images and scanned PDFs"""

    def __init__(self):
        """Initialize OCR service"""
        self._language_cache: Optional[Dict[str, str]] = None
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

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy
        - Convert to grayscale
        - Apply thresholding
        - Denoise
        """
        try:
            img_array = np.array(image)

            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

            _, threshold = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            preprocessed_image = Image.fromarray(threshold)

            logger.debug("Image preprocessing completed successfully")
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

    def is_scanned_pdf(self, pdf_file: bytes) -> bool:
        """
        Detect if a PDF is scanned (image-based) or native text

        Args:
            pdf_file: PDF file as bytes

        Returns:
            True if PDF is scanned, False if it contains native text
        """
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_file))

            if len(pdf_reader.pages) == 0:
                return False

            first_page = pdf_reader.pages[0]
            text = first_page.extract_text().strip()

            if len(text) < 50:
                return True

            return False

        except Exception as e:
            logger.warning(f"Could not determine if PDF is scanned: {e}")
            return True

    def extract_text_from_pdf(
        self,
        pdf_file: bytes,
        db: Session,
        language: str = 'en',
        max_pages: Optional[int] = None
    ) -> Tuple[str, float]:
        """
        Extract text from PDF (handles both native and scanned PDFs)

        Args:
            pdf_file: PDF file as bytes
            db: Database session for loading language config
            language: Language code for OCR (fallback to 'en' if not provided)
            max_pages: Maximum number of pages to process (None for all)

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            is_scanned = self.is_scanned_pdf(pdf_file)

            if not is_scanned:
                pdf_reader = PdfReader(io.BytesIO(pdf_file))
                pages_to_process = len(pdf_reader.pages) if max_pages is None else min(max_pages, len(pdf_reader.pages))

                text_parts = []
                for i in range(pages_to_process):
                    page_text = pdf_reader.pages[i].extract_text()
                    if page_text:
                        text_parts.append(page_text)

                full_text = "\n\n".join(text_parts)

                logger.info(f"Extracted text from native PDF ({pages_to_process} pages)")
                return full_text.strip(), 1.0

            else:
                from pdf2image import convert_from_bytes

                pages_to_process = max_pages if max_pages else None

                images = convert_from_bytes(
                    pdf_file,
                    first_page=1,
                    last_page=pages_to_process
                )

                text_parts = []
                confidences = []

                for i, image in enumerate(images):
                    logger.debug(f"Processing page {i+1}/{len(images)}")
                    page_text, confidence = self.extract_text_from_image(image, db, language)

                    if page_text:
                        text_parts.append(page_text)
                        confidences.append(confidence)

                full_text = "\n\n".join(text_parts)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                logger.info(f"Extracted text from scanned PDF ({len(images)} pages, {avg_confidence*100:.1f}% confidence)")

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
