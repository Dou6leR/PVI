import io
from pypdf import PdfReader
from core.logger import logger


def extract_text_from_pdf(file_bytes: bytes) -> list[dict]:
    """
    Extracts text from a PDF file buffer.
    Returns a list of dicts with 'page' number and 'text' content.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_data = []
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages_data.append({
                    "page": index + 1,
                    "text": text
                })
        logger.info(f"Successfully extracted {len(pages_data)} pages from PDF.")
        return pages_data
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        raise ValueError(f"Failed to parse PDF document: {str(e)}")
