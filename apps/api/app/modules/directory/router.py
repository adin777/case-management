import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.core.config import settings
from app.modules.api import DB, Current, audit
from app.modules.directory.active_directory import ActiveDirectoryProvider
from app.modules.directory.entra import EntraDirectoryProvider
from app.modules.directory.excel import EXPORT_HEADERS, HEADERS, parse, workbook
from app.modules.directory.fake import FakeDirectoryProvider
from app.modules.directory.provider import DirectoryBatch, DirectoryProvider, NormalizedDirectoryUser
from app.modules.directory.sync_service import UserSyncService
from app.modules.models import (
    DirectorySyncRun,
    Environment,
    EnvironmentMembership,
    Group,
    GroupMember,
    User,
    UserImportSession,
)

router = APIRouter(prefix="/api", tags=["directory"])


class ApplyIn(BaseModel):
    provider: str
    users: list[NormalizedDirectoryUser]
    delta_link: str | None = None


class ImportApplyIn(BaseModel):
    import_session_id: uuid.UUID


def admin(user: Current) -> None:
    if not user.is_system_admin: raise HTTPException(403, "נדרשת הרשאת מנהל מערכת")


def provider(name: str) -> DirectoryProvider:
    if name == "fake": return FakeDirectoryProvider()
    if name == "entra": return EntraDirectoryProvider()
    if name == "active_directory": return ActiveDirectoryProvider()
    raise HTTPException(422, "ספק Directory אינו נתמך")


@router.get("/directory/status")
def status(db: DB, user: Current) -> dict[str, Any]:
    admin(user); latest = db.scalar(select(DirectorySyncRun).order_by(DirectorySyncRun.started_at.desc()))
    return {"mode": settings.directory_mode, "last_run": None if not latest else run_dict(latest)}


@router.post("/directory/{name}/test")
def test_provider(name: str, user: Current) -> dict[str, Any]: admin(user); return provider(name).test_connection()


@router.post("/directory/{name}/preview")
def preview(name: str, db: DB, user: Current) -> dict[str, Any]:
    admin(user); batch = provider(name).fetch_users(); return UserSyncService(db, name).preview(batch)


@router.post("/directory/apply")
def apply(data: ApplyIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user)
    try: run = UserSyncService(db, data.provider).apply(DirectoryBatch(users=data.users, delta_link=data.delta_link), user.id)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    audit(db, user, "directory_sync_run", run.id, "applied", after=run_dict(run)); db.commit(); return run_dict(run)


@router.get("/directory/runs")
def runs(db: DB, user: Current) -> list[dict[str, Any]]:
    admin(user); return [run_dict(row) for row in db.scalars(select(DirectorySyncRun).order_by(DirectorySyncRun.started_at.desc()).limit(50))]


def run_dict(row: DirectorySyncRun) -> dict[str, Any]:
    return jsonable_encoder({column.name: getattr(row, column.name) for column in row.__table__.columns})


@router.get("/users/import/template")
def user_template(user: Current) -> Response:
    admin(user); return Response(workbook([HEADERS], "User Import"), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=user-import-template.xlsx"})


@router.post("/users/import/preview")
async def import_preview(db: DB, user: Current, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    admin(user)
    try: batch = DirectoryBatch(users=parse(await file.read()))
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    result = UserSyncService(db, "excel").preview(batch)
    session = UserImportSession(created_by=user.id, snapshot_json=result["users"])
    db.add(session); db.commit()
    return {**result, "import_session_id": session.id}


@router.post("/users/import/apply")
def import_apply(data: ImportApplyIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user)
    session = db.get(UserImportSession, data.import_session_id)
    if not session or session.created_by != user.id:
        raise HTTPException(404, "תצוגת הייבוא אינה קיימת")
    if session.applied_at:
        raise HTTPException(409, "תצוגת הייבוא כבר הוחלה")
    users = [NormalizedDirectoryUser.model_validate(row) for row in session.snapshot_json]
    run = UserSyncService(db, "excel").apply(DirectoryBatch(users=users), user.id)
    session.applied_at = datetime.now(UTC)
    audit(db, user, "directory_sync_run", run.id, "excel_import_applied")
    db.commit()
    created_or_updated = [{"email":str(row.email),"display_name":row.display_name,
        "is_active":row.directory_enabled} for row in users]
    return {**run_dict(run), "users":created_or_updated}


@router.get("/users-export")
def export_users(db: DB, user: Current, status_filter: str | None = Query(None),
                 source: str | None = Query(None), department: str | None = Query(None),
                 job_title: str | None = Query(None), search: str | None = Query(None)) -> Response:
    admin(user); query = select(User).order_by(User.display_name)
    if status_filter: query = query.where(User.status == status_filter)
    if source: query = query.where(User.source == source)
    if department: query = query.where(User.department == department)
    if job_title: query = query.where(User.job_title == job_title)
    if search:
        term = f"%{search.lower()}%"
        query = query.where(or_(func.lower(User.display_name).like(term), func.lower(User.email).like(term),
                                func.lower(User.user_principal_name).like(term)))
    export_headers = EXPORT_HEADERS
    rows = [export_headers]
    for row in db.scalars(query):
        groups = db.scalars(select(Group.name).join(GroupMember, GroupMember.group_id == Group.id).where(
            GroupMember.user_id == row.id).order_by(Group.name)).all()
        environments = db.scalars(select(Environment.name_he).join(
            EnvironmentMembership, EnvironmentMembership.environment_id == Environment.id).where(
            EnvironmentMembership.user_id == row.id, EnvironmentMembership.is_active.is_(True)).order_by(
            Environment.name_he)).all()
        rows.append([getattr(row, field) for field in export_headers[:-2]] + [", ".join(groups), ", ".join(environments)])
    return Response(workbook(rows), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=users.xlsx"})
