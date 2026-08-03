import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.config import PROJECT_ROOT, settings
from app.modules.api import DB, Current, audit, case_access, require
from app.modules.models import Case, Comment
from app.modules.operations.models import Attachment

router = APIRouter(prefix="/api", tags=["attachments"])
ATTACHMENT_ROOT = settings.attachment_directory.resolve()


def serialize(item: Attachment) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


def accessible_case(case_id: uuid.UUID, db: DB, user: Current, permission: str) -> Case:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    require(db, user, item.environment_id, permission)
    return item


@router.get("/cases/{case_id}/attachments")
def list_attachments(case_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    accessible_case(case_id, db, user, "attachment.read")
    query = select(Attachment).where(
        Attachment.case_id == case_id, Attachment.is_deleted.is_(False)
    )
    return [serialize(item) for item in db.scalars(query.order_by(Attachment.uploaded_at.desc()))]


@router.post("/cases/{case_id}/attachments", status_code=201)
async def upload_attachment(
    case_id: uuid.UUID,
    db: DB,
    user: Current,
    file: Annotated[UploadFile, File()],
    comment_id: Annotated[uuid.UUID | None, Form()] = None,
) -> dict[str, Any]:
    case = accessible_case(case_id, db, user, "attachment.upload")
    safe_name = Path(file.filename or "file").name
    if safe_name in {"", ".", ".."} or safe_name != (file.filename or "file"):
        raise HTTPException(422, "שם הקובץ אינו תקין")
    allowed = {value.strip() for value in settings.attachment_allowed_types.split(",")}
    if (file.content_type or "") not in allowed:
        raise HTTPException(415, "סוג הקובץ אינו נתמך")
    if comment_id:
        comment = db.get(Comment, comment_id)
        if not comment or comment.case_id != case_id:
            raise HTTPException(422, "התגובה אינה שייכת לקריאה")
    content = await file.read(settings.attachment_max_bytes + 1)
    if len(content) > settings.attachment_max_bytes:
        raise HTTPException(413, "הקובץ חורג ממגבלת הגודל")
    stored_name = f"{uuid.uuid4().hex}{Path(safe_name).suffix.lower()}"
    target_dir = (ATTACHMENT_ROOT / str(case.environment_id) / str(case.id)).resolve()
    if ATTACHMENT_ROOT not in target_dir.parents:
        raise HTTPException(422, "נתיב האחסון אינו תקין")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / stored_name
    target.write_bytes(content)
    item = Attachment(
        id=uuid.uuid4(),
        system_number=f"ATT-{uuid.uuid4().hex[:8].upper()}",
        case_id=case_id,
        comment_id=comment_id,
        original_file_name=safe_name,
        stored_file_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        storage_path=str(target.relative_to(PROJECT_ROOT)),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        uploaded_by=user.id,
    )
    db.add(item)
    audit(
        db,
        user,
        "attachment",
        item.id,
        "uploaded",
        after={"file_name": safe_name, "size_bytes": len(content), "case_id": str(case_id)},
    )
    db.commit()
    return serialize(item)


def get_attachment(attachment_id: uuid.UUID, db: DB, user: Current) -> Attachment:
    item = db.get(Attachment, attachment_id)
    if not item or item.is_deleted:
        raise HTTPException(404, "Attachment not found")
    accessible_case(item.case_id, db, user, "attachment.read")
    return item


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: uuid.UUID, db: DB, user: Current) -> FileResponse:
    item = get_attachment(attachment_id, db, user)
    target = (PROJECT_ROOT / item.storage_path).resolve()
    if ATTACHMENT_ROOT not in target.parents or not target.is_file():
        raise HTTPException(404, "Attachment file not found")
    return FileResponse(target, media_type=item.content_type, filename=item.original_file_name)


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: uuid.UUID, db: DB, user: Current) -> None:
    item = get_attachment(attachment_id, db, user)
    case = db.get(Case, item.case_id)
    if not case:
        raise HTTPException(409, "Case no longer exists")
    require(db, user, case.environment_id, "attachment.delete")
    item.is_deleted = True
    item.deleted_by = user.id
    item.deleted_at = datetime.now(UTC)
    audit(
        db,
        user,
        "attachment",
        item.id,
        "deleted",
        before={"is_deleted": False},
        after={"is_deleted": True},
    )
    db.commit()
