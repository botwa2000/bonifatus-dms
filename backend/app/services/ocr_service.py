"""
OCR Service for Bonifatus DMS
Extracts text from scanned documents and images using Tesseract OCR
Language support loaded dynamically from system_settings
"""

import io
import logging
import re
import subprocess
from typing import Optional, Tuple, Dict, Set
from PIL import Image
import pytesseract
import cv2
import numpy as np
import fitz  # PyMuPDF
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

    def check_spelling(self, words: Set[str], language: str = 'en') -> Set[str]:
        """
        Check spelling of words using system Hunspell command

        Args:
            words: Set of words to check
            language: Language code (en, de, ru, fr)

        Returns:
            Set of misspelled words
        """
        # Map language codes to Hunspell dictionary codes
        dict_map = {
            'en': 'en_US',
            'de': 'de_DE',
            'ru': 'ru_RU',
            'fr': 'fr'
        }

        dict_code = dict_map.get(language, 'en_US')
        misspelled = set()

        try:
            # Call hunspell with pipe mode for batch checking
            # -d specifies dictionary, -l lists only misspelled words
            process = subprocess.Popen(
                ['hunspell', '-d', dict_code, '-l'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Send all words to hunspell
            input_text = '\n'.join(words)
            stdout, stderr = process.communicate(input=input_text, timeout=5)

            # hunspell -l outputs one misspelled word per line
            if process.returncode == 0:
                misspelled = set(stdout.strip().split('\n')) if stdout.strip() else set()
                logger.debug(f"Hunspell checked {len(words)} words, found {len(misspelled)} misspelled (lang: {language})")
            else:
                logger.warning(f"Hunspell returned non-zero exit code: {process.returncode}, stderr: {stderr}")

        except FileNotFoundError:
            logger.error("Hunspell command not found - spell checking disabled")
        except subprocess.TimeoutExpired:
            logger.warning(f"Hunspell timeout checking {len(words)} words")
            process.kill()
        except Exception as e:
            logger.warning(f"Hunspell spell check failed: {e}")

        return misspelled

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
            # Use new check_spelling API that takes a set of words and returns misspelled ones
            misspelled_words = self.check_spelling(sample_words, language)

            misspelled_count = len(misspelled_words)
            error_rate = misspelled_count / len(sample_words) if sample_words else 1.0
            metrics['spelling_error_rate'] = error_rate
            metrics['total_words_checked'] = len(sample_words)
            metrics['misspelled_words'] = misspelled_count

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
        Detect if a PDF is scanned (image-based) or native text using PDF STRUCTURE analysis
        This is language-agnostic and more reliable than spell-checking

        Args:
            pdf_file: PDF file as bytes
            language: Language code (unused, kept for API compatibility)

        Returns:
            Tuple of (is_scanned, confidence_score)
            is_scanned: True if PDF is scanned/image-only, False if it contains native text
            confidence_score: Confidence in the decision (0.0-1.0)
        """
        try:
            doc = fitz.open(stream=pdf_file, filetype="pdf")

            if len(doc) == 0:
                doc.close()
                return True, 0.0

            first_page = doc[0]

            # METHOD 1: Check for embedded fonts (native text PDFs always have fonts)
            try:
                font_list = doc.get_page_fonts(0)
                font_count = len(font_list)
            except:
                font_count = 0

            # METHOD 2: Get text blocks (native PDFs have structured text blocks)
            text_blocks = first_page.get_text("blocks")
            text_block_count = len([b for b in text_blocks if len(b[4].strip()) > 0])

            # METHOD 3: Extract raw text
            text = first_page.get_text().strip()
            text_length = len(text)

            # METHOD 4: Check for images (scanned PDFs are usually 1 full-page image)
            image_list = first_page.get_images()
            image_count = len(image_list)

            doc.close()

            # DECISION LOGIC (structure-based, language-agnostic)
            # =========================================================

            # Case 1: Definitely NATIVE text PDF
            if font_count > 0 and text_block_count > 3:
                logger.info(f"PDF is NATIVE TEXT: {font_count} fonts, {text_block_count} text blocks, {text_length} chars")
                return False, 1.0

            # Case 2: Substantial text present (>200 chars) = likely native
            if text_length >= 200:
                logger.info(f"PDF has substantial text ({text_length} chars), treating as native")
                return False, 0.9

            # Case 3: Definitely SCANNED (no fonts, no text, but has images)
            if font_count == 0 and text_block_count == 0 and image_count > 0:
                logger.info(f"PDF is SCANNED: no fonts, no text blocks, {image_count} images")
                return True, 1.0

            # Case 4: Very little text (<50 chars) = likely scanned
            if text_length < 50:
                logger.info(f"PDF appears scanned: only {text_length} chars of text")
                return True, 0.8

            # Case 5: Ambiguous (has some text but no fonts) = check text amount
            if text_length >= 100:
                logger.info(f"PDF has moderate text ({text_length} chars), treating as native")
                return False, 0.7
            else:
                logger.info(f"PDF has little text ({text_length} chars), will re-OCR")
                return True, 0.6

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

                    # Check PDF metadata for rotation first
                    metadata_rotation = page.rotation
                    if metadata_rotation != 0:
                        logger.info(f"[ROTATION DEBUG] Page {i+1} has metadata rotation: {metadata_rotation}°")

                    # Extract text at current rotation
                    page_text = page.get_text()

                    # Use Tesseract OSD (Orientation and Script Detection) for rotation detection
                    if page_text and len(page_text) > 50:
                        try:
                            # Render page as image for OSD analysis
                            zoom = 2  # 144 DPI for OSD (balance speed vs accuracy)
                            mat = fitz.Matrix(zoom, zoom)
                            pix = page.get_pixmap(matrix=mat)
                            import io
                            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                            # Run Tesseract OSD (fast, analyzes structure not full text)
                            osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
                            detected_rotation = osd.get('rotate', 0)  # How much to rotate to correct
                            orientation_conf = osd.get('orientation_conf', 0)

                            logger.info(f"[ROTATION DEBUG] Page {i+1} Tesseract OSD:")
                            logger.info(f"[ROTATION DEBUG]   - Detected rotation needed: {detected_rotation}°")
                            logger.info(f"[ROTATION DEBUG]   - Confidence: {orientation_conf:.2f}")
                            logger.info(f"[ROTATION DEBUG]   - Text sample: {page_text[:50]}")

                            # Apply rotation if detected with high confidence (>2.0 is typically reliable)
                            if detected_rotation != 0 and orientation_conf > 2.0:
                                logger.info(f"[ROTATION DEBUG] ✅ Detected {detected_rotation}° rotation, re-extracting via OCR")

                                # For rotated pages, page.set_rotation() doesn't affect get_text()
                                # Solution: Rotate the image and OCR it
                                rotated_image = image.rotate(-detected_rotation, expand=True)  # PIL rotates counter-clockwise

                                # Get Tesseract language codes for OCR
                                supported_languages = self.get_supported_languages(db)
                                tesseract_lang = supported_languages.get(language, 'eng')

                                # OCR the rotated image
                                custom_config = r'--oem 3 --psm 3'
                                page_text = pytesseract.image_to_string(
                                    rotated_image,
                                    lang=tesseract_lang,
                                    config=custom_config
                                ).strip()

                                logger.info(f"[ROTATION DEBUG] ✅ Page {i+1} re-OCR'd after {detected_rotation}° rotation, new sample: {page_text[:50]}")
                            else:
                                logger.info(f"[ROTATION DEBUG] Page {i+1} appears correctly oriented (rotation: {detected_rotation}°, conf: {orientation_conf:.2f})")

                        except Exception as e:
                            # OSD can fail on pages with very little text or complex layouts
                            logger.warning(f"[ROTATION DEBUG] OSD failed for page {i+1}: {e}, using text as-is")

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
                    logger.info(f"[OCR DEBUG] Processing page {i+1}/{pages_to_process}")

                    page = doc[i]

                    # Check for embedded images (direct extraction preserves quality)
                    images = page.get_images()

                    if images:
                        # PDF has embedded image - analyze quality
                        xref = images[0][0]
                        base_image = doc.extract_image(xref)

                        # Get page dimensions in inches
                        page_rect = page.rect
                        page_width_inches = page_rect.width / 72
                        page_height_inches = page_rect.height / 72

                        # Calculate DPI
                        dpi_x = base_image['width'] / page_width_inches if page_width_inches > 0 else 0
                        dpi_y = base_image['height'] / page_height_inches if page_height_inches > 0 else 0

                        # Handle PDFs with incorrect page dimensions (common issue)
                        # If calculated DPI is suspiciously low but image resolution is high, recalculate using standard page sizes
                        if (dpi_x < 150 or dpi_y < 150) and (base_image['width'] >= 2000 or base_image['height'] >= 2000):
                            logger.info(f"[OCR DEBUG] ⚠️ PDF has incorrect page dimensions ({page_width_inches:.2f}x{page_height_inches:.2f} in), recalculating DPI")

                            # Detect orientation from image aspect ratio
                            image_aspect = base_image['width'] / base_image['height']

                            # Standard page sizes (width x height in inches): Letter, A4
                            standard_sizes = [
                                (8.5, 11.0),   # US Letter portrait
                                (11.0, 8.5),   # US Letter landscape
                                (8.27, 11.69), # A4 portrait
                                (11.69, 8.27)  # A4 landscape
                            ]

                            # Find best matching standard size
                            best_match = None
                            best_diff = float('inf')
                            for std_width, std_height in standard_sizes:
                                std_aspect = std_width / std_height
                                aspect_diff = abs(image_aspect - std_aspect)
                                if aspect_diff < best_diff:
                                    best_diff = aspect_diff
                                    best_match = (std_width, std_height)

                            # Recalculate DPI using standard page size
                            if best_match:
                                page_width_inches, page_height_inches = best_match
                                dpi_x = base_image['width'] / page_width_inches
                                dpi_y = base_image['height'] / page_height_inches
                                logger.info(f"[OCR DEBUG] ✅ Matched to standard page size: {page_width_inches}x{page_height_inches} inches, recalculated DPI: {dpi_x:.0f}x{dpi_y:.0f}")

                        logger.info(f"[OCR DEBUG] Embedded image found:")
                        logger.info(f"[OCR DEBUG]   - Resolution: {base_image['width']}x{base_image['height']} pixels")
                        logger.info(f"[OCR DEBUG]   - Page size: {page_width_inches:.2f}x{page_height_inches:.2f} inches")
                        logger.info(f"[OCR DEBUG]   - Effective DPI: {dpi_x:.0f}x{dpi_y:.0f}")
                        logger.info(f"[OCR DEBUG]   - Format: {base_image['ext']}")
                        logger.info(f"[OCR DEBUG]   - Size: {len(base_image['image']) / 1024:.1f} KB")

                        # Quality-based extraction decision
                        if dpi_x >= 200 and dpi_y >= 200:
                            # High-quality scan - extract directly without preprocessing
                            logger.info(f"[OCR DEBUG] ✅ HIGH QUALITY ({dpi_x:.0f} DPI) - Extracting image directly (no preprocessing)")
                            import io
                            image = Image.open(io.BytesIO(base_image['image']))
                            page_text, confidence = self.extract_text_from_image(image, db, language, preprocess=False)
                            logger.info(f"[OCR DEBUG] Direct extraction result: {len(page_text)} chars, {confidence*100:.1f}% confidence")
                        else:
                            # Low-quality scan - render and preprocess
                            logger.info(f"[OCR DEBUG] ⚠️ LOW QUALITY ({dpi_x:.0f} DPI) - Rendering page with preprocessing")
                            pix = page.get_pixmap(matrix=mat)
                            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            page_text, confidence = self.extract_text_from_image(image, db, language, preprocess=True)
                            logger.info(f"[OCR DEBUG] Preprocessed extraction result: {len(page_text)} chars, {confidence*100:.1f}% confidence")
                    else:
                        # No embedded images - render page
                        logger.info(f"[OCR DEBUG] No embedded images - rendering page at 300 DPI")
                        pix = page.get_pixmap(matrix=mat)
                        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        page_text, confidence = self.extract_text_from_image(image, db, language, preprocess=True)
                        logger.info(f"[OCR DEBUG] Rendered extraction result: {len(page_text)} chars, {confidence*100:.1f}% confidence")

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
