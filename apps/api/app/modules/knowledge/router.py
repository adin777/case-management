import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.config import settings
from app.modules.api import DB, Current, audit, require
from app.modules.knowledge.service import index_document, query, safe_name
from app.modules.models import KnowledgeDocument

router = APIRouter(prefix="/api")


class QuestionIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


def output(row: KnowledgeDocument) -> dict:
    return {
        "id": str(row.id),
        "environment_id": str(row.environment_id),
        "filename": row.filename,
        "original_filename": row.original_filename,
        "mime_type": row.mime_type,
        "size": row.size,
        "status": row.status,
        "uploaded_at": row.uploaded_at,
        "indexed_at": row.indexed_at,
        "version": row.version,
        "is_active": row.is_active,
        "error_message": row.error_message,
    }


@router.get("/environments/{environment_id}/knowledge/documents")
def documents(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict]:
    require(db, user, environment_id, "knowledge.read")
    return [
        output(row)
        for row in db.scalars(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.environment_id == environment_id)
            .order_by(KnowledgeDocument.uploaded_at.desc())
        )
    ]


@router.post("/environments/{environment_id}/knowledge/documents", status_code=201)
async def upload(environment_id: uuid.UUID, db: DB, user: Current,
                 file: Annotated[UploadFile, File()]) -> dict:
    require(db, user, environment_id, "knowledge.manage")
    original = safe_name(file.filename or "document")
    data = await file.read()
    if not data or len(data) > settings.knowledge_max_bytes:
        raise HTTPException(422, "הקובץ ריק או חורג ממגבלת הגודל")
    version = (
        db.scalar(
            select(func.max(KnowledgeDocument.version)).where(
                KnowledgeDocument.environment_id == environment_id,
                KnowledgeDocument.original_filename == original,
            )
        )
        or 0
    ) + 1
    for prior in db.scalars(
        select(KnowledgeDocument).where(
            KnowledgeDocument.environment_id == environment_id,
            KnowledgeDocument.original_filename == original,
            KnowledgeDocument.is_active.is_(True),
        )
    ):
        prior.is_active = False
    storage = settings.knowledge_directory / str(environment_id)
    storage.mkdir(parents=True, exist_ok=True)
    document_id = uuid.uuid4()
    path = storage / f"{document_id.hex}{Path(original).suffix.lower()}"
    path.write_bytes(data)
    document = KnowledgeDocument(
        id=document_id,
        environment_id=environment_id,
        filename=original,
        original_filename=original,
        mime_type=file.content_type or "application/octet-stream",
        size=len(data),
        storage_path=str(path),
        uploaded_by=user.id,
        version=version,
    )
    db.add(document)
    db.flush()
    index_document(db, document, data)
    audit(db, user, "knowledge_document", document.id, "uploaded", after={"filename": original})
    db.commit()
    return output(document)


@router.post("/environments/{environment_id}/knowledge/documents/{document_id}/reindex")
def reindex(environment_id: uuid.UUID, document_id: uuid.UUID, db: DB, user: Current) -> dict:
    require(db, user, environment_id, "knowledge.manage")
    row = db.get(KnowledgeDocument, document_id)
    if not row or row.environment_id != environment_id:
        raise HTTPException(404, "המסמך לא נמצא")
    index_document(db, row)
    db.commit()
    return output(row)


@router.patch("/environments/{environment_id}/knowledge/documents/{document_id}/active")
def active(environment_id: uuid.UUID, document_id: uuid.UUID, enabled: bool, db: DB, user: Current) -> dict:
    require(db, user, environment_id, "knowledge.manage")
    row = db.get(KnowledgeDocument, document_id)
    if not row or row.environment_id != environment_id:
        raise HTTPException(404, "המסמך לא נמצא")
    row.is_active = enabled
    db.commit()
    return output(row)


@router.get("/environments/{environment_id}/knowledge/documents/{document_id}/download")
def download(environment_id: uuid.UUID, document_id: uuid.UUID, db: DB, user: Current) -> FileResponse:
    require(db, user, environment_id, "knowledge.read")
    row = db.get(KnowledgeDocument, document_id)
    if not row or row.environment_id != environment_id or not Path(row.storage_path).is_file():
        raise HTTPException(404, "המסמך לא נמצא")
    return FileResponse(row.storage_path, filename=row.original_filename, media_type=row.mime_type)


@router.post("/environments/{environment_id}/knowledge/query")
def ask(environment_id: uuid.UUID, data: QuestionIn, db: DB, user: Current) -> dict:
    require(db, user, environment_id, "knowledge.query")
    return query(db, environment_id, data.question)


@router.get("/system/ai-settings")
def ai_settings(user: Current) -> dict:
    if not user.is_system_admin:
        raise HTTPException(403, "נדרשת הרשאת מנהל מערכת")
    return {
        "provider": settings.ai_provider,
        "model": settings.ai_model,
        "embedding_model": settings.embedding_model,
        "api_key_configured": bool(settings.openai_api_key),
    }
