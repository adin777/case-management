import re
import uuid
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.knowledge.providers import ExtractiveLLMProvider, LocalHashEmbeddingProvider, similarity
from app.modules.models import KnowledgeChunk, KnowledgeDocument

ALLOWED = {".pdf", ".docx", ".xlsx", ".txt", ".md"}


def safe_name(name: str) -> str:
    value = Path(name).name
    if Path(value).suffix.lower() not in ALLOWED:
        raise HTTPException(422, "סוג הקובץ אינו נתמך. ניתן להעלות PDF, DOCX, XLSX, TXT או MD")
    return re.sub(r"[^\w.\-\u0590-\u05ff]", "_", value)


def extract_text(name: str, data: bytes) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in {".txt", ".md"}:
        return data.decode("utf-8-sig", errors="replace")
    if suffix in {".docx", ".xlsx"}:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            files = [
                item
                for item in archive.namelist()
                if (suffix == ".docx" and item == "word/document.xml")
                or (
                    suffix == ".xlsx"
                    and (item.startswith("xl/worksheets/") or item == "xl/sharedStrings.xml")
                )
            ]
            parts: list[str] = []
            for file_name in files:
                root = ElementTree.fromstring(archive.read(file_name))
                parts.extend(node.text or "" for node in root.iter() if node.text)
            return " ".join(parts)
    # PDF text streams are normalized without executing embedded content.
    decoded = data.decode("latin-1", errors="ignore")
    return " ".join(re.findall(r"\(([^()]*)\)\s*Tj", decoded))


def index_document(db: Session, document: KnowledgeDocument, data: bytes | None = None) -> None:
    document.status = "processing"
    document.error_message = None
    try:
        raw = data if data is not None else Path(document.storage_path).read_bytes()
        text = re.sub(r"\s+", " ", extract_text(document.original_filename, raw)).strip()
        if not text:
            raise ValueError("לא נמצא טקסט שניתן לאינדקס במסמך")
        db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
        embedder = LocalHashEmbeddingProvider()
        chunks = [text[index : index + 1200] for index in range(0, len(text), 1000)]
        for index, content in enumerate(chunks):
            db.add(
                KnowledgeChunk(
                    document_id=document.id,
                    environment_id=document.environment_id,
                    chunk_index=index,
                    section=None,
                    content=content,
                    embedding_json=embedder.embed(content),
                )
            )
        document.status = "ready"
        document.indexed_at = datetime.now(UTC)
    except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        document.status = "failed"
        document.error_message = str(exc)


def query(db: Session, environment_id: uuid.UUID, question: str) -> dict:
    embedder = LocalHashEmbeddingProvider()
    vector = embedder.embed(question)
    rows = db.execute(
        select(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(
            KnowledgeChunk.environment_id == environment_id,
            KnowledgeDocument.environment_id == environment_id,
            KnowledgeDocument.is_active.is_(True),
            KnowledgeDocument.status == "ready",
        )
    ).all()
    ranked = sorted(rows, key=lambda row: similarity(vector, row[0].embedding_json), reverse=True)[:5]
    answer = ExtractiveLLMProvider().answer(question, [row[0].content for row in ranked])
    sources = [
        {
            "document_id": str(document.id),
            "filename": document.original_filename,
            "section": chunk.section,
            "chunk_index": chunk.chunk_index,
        }
        for chunk, document in ranked
        if similarity(vector, chunk.embedding_json) > 0
    ]
    return {"answer": answer, "sources": sources, "provider": "local-extractive"}
