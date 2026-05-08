"""
Reads the file at source_path and returns raw text content.
Delegates to format-specific loaders (PDF, DOCX, TXT).
Sets status to CHUNKING on success, FAILED on any read error.
"""

from __future__ import annotations
 
import logging
from pathlib import Path
 
import docx
from pypdf import PdfReader
 
from state import FileType, IngestionState, IngestionStatus
 
logger = logging.getLogger(__name__)

def _load_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)
 
 
def _load_docx(path: Path) -> str:
    doc = docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
 
 
def _load_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

_LOADERS = {
    FileType.PDF:  _load_pdf,
    FileType.DOCX: _load_docx,
    FileType.TXT:  _load_txt,
}

def load_document(state: IngestionState) -> dict:
    """
    LangGraph node — load_document.
 
    Reads the source file and returns its text content as raw bytes
    (UTF-8 encoded string stored in raw_content for downstream nodes).
 
    Returns a partial IngestionState dict.
    """
    path = Path(state["source_path"])
    file_type = state["file_type"]
 
    logger.info(
        "load_document | doc_id=%s  path=%s  type=%s",
        state["document_id"], path, file_type,
    )
 
    loader = _LOADERS.get(file_type)
    if loader is None:
        msg = f"Unsupported file type: {file_type}"
        logger.error(msg)
        return {
            "status": IngestionStatus.FAILED,
            "errors": [msg],
            "node_trace": ["load_document"],
        }
 
    if not path.exists():
        msg = f"File not found: {path}"
        logger.error(msg)
        return {
            "status": IngestionStatus.FAILED,
            "errors": [msg],
            "node_trace": ["load_document"],
        }
 
    try:
        text = loader(path)
    except Exception as exc:
        msg = f"Failed to load {file_type} file: {exc}"
        logger.exception(msg)
        return {
            "status": IngestionStatus.FAILED,
            "errors": [msg],
            "node_trace": ["load_document"],
        }
 
    if not text.strip():
        msg = f"File produced empty text after loading: {path}"
        logger.warning(msg)
        return {
            "status": IngestionStatus.FAILED,
            "errors": [msg],
            "node_trace": ["load_document"],
        }
 
    logger.info(
        "load_document | doc_id=%s  chars=%d",
        state["document_id"], len(text),
    )
 
    return {
        "raw_content": text.encode("utf-8"),   # store as bytes per state contract
        "status": IngestionStatus.CHUNKING,
        "node_trace": ["load_document"],
    }