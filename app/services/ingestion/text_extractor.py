import asyncio
import io

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.core.exceptions import ValidationError
from app.core.logger import get_logger

logger = get_logger("text_extractor.py")

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _extract_docx(file_bytes: bytes) -> str:
    doc = DocxDocument(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()


def _extract_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore").strip()


def extract_text_sync(file_bytes: bytes, file_type: str) -> str:
    file_type = file_type.lower().lstrip(".")
    if file_type == "pdf":
        return _extract_pdf(file_bytes)
    if file_type == "docx":
        return _extract_docx(file_bytes)
    if file_type == "txt":
        return _extract_txt(file_bytes)
    raise ValidationError(f"Unsupported file type: {file_type}")


async def extract_text(file_bytes: bytes, file_type: str) -> str:
    return await asyncio.to_thread(
        extract_text_sync,
        file_bytes,
        file_type,
    )
