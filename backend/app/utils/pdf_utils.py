# backend/app/utils/pdf_utils.py
"""
PDF utility functions for document processing
"""

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def count_pdf_pages(file_content: bytes) -> int:
    """
    Count the number of pages in a PDF document

    Args:
        file_content: Raw PDF file bytes

    Returns:
        Number of pages in the PDF

    Raises:
        Exception: If PDF cannot be opened or is invalid
    """
    try:
        import fitz  # PyMuPDF

        # Open PDF from bytes
        pdf_stream = io.BytesIO(file_content)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")

        page_count = len(doc)
        doc.close()

        logger.debug(f"PDF has {page_count} pages")
        return page_count

    except Exception as e:
        logger.error(f"Failed to count PDF pages: {e}")
        # If we can't count pages, return 1 as conservative estimate
        return 1


def estimate_pages_from_size(file_size_bytes: int, mime_type: str) -> int:
    """
    Estimate number of pages based on file size (fallback method)

    Args:
        file_size_bytes: File size in bytes
        mime_type: MIME type of file

    Returns:
        Estimated number of pages
    """
    # Average bytes per page for different file types
    BYTES_PER_PAGE_ESTIMATES = {
        'application/pdf': 100_000,  # 100KB per page (with images)
        'image/jpeg': 500_000,       # 500KB per image (1 page)
        'image/png': 500_000,
        'image/tiff': 500_000,
        'image/bmp': 1_000_000,      # 1MB per image
    }

    bytes_per_page = BYTES_PER_PAGE_ESTIMATES.get(mime_type, 100_000)
    estimated_pages = max(1, file_size_bytes // bytes_per_page)

    logger.debug(f"Estimated {estimated_pages} pages for {file_size_bytes} bytes ({mime_type})")
    return estimated_pages
