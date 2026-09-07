import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from app.modules.api import DB, Current, audit, permissions
from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.case_visibility.service import CaseVisibilityService, can_manage_locked_case
from app.modules.models import (
    BulkCaseActionPreview,
    Case,
    CaseParticipant,
    EnvironmentMembership,
    SavedCaseView,
    User,
)
from app.modules.operations.models import CaseStatusHistory
from app.modules.sla.service import SlaEngine

router = APIRouter(prefix="/api/workspace", tags=["agent-workspace"])
ALLOWED_COLUMNS = {"case_number", "title", "environment", "request_type", "status", "priority", "created_at", "updated_at", "sla_state", "sla_due_at"}
ALLOWED_SORTS = {f"{column}:{direction}" for column in ("case_number", "title", "created_at", "updated_at") for direction in ("asc", "desc")}


class SavedViewIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    filters: dict[str, Any] = Field(default_factory=dict)
    sort: str = "updated_at:desc"
    visible_columns: list[str] = Field(default_factory=lambda: list(ALLOWED_COLUMNS))
    page_size: int = Field(default=25, ge=10, le=100)
    is_default: bool = False


class BulkPreviewIn(BaseModel):
    case_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    action: str = Field(pattern="^(assign|status|priority|add_participant)$")
    target_id: uuid.UUID


class BulkApplyIn(BaseModel):
    preview_id: uuid.UUID


def serialize(row: SavedCaseView) -> dict[str, Any]:
    return {"id": row.id, "name": row.name, "filters": row.filters_json, "sort": row.sort,
            "visible_columns": row.visible_columns_json, "page_size": row.page_size,
            "is_default": row.is_default, "created_at": row.created_at, "updated_at": row.updated_at}


def validate(data: SavedViewIn) -> None:
    if data.sort not in ALLOWED_SORTS: raise HTTPException(422, "מיון התצוגה אינו נתמך")
    if not data.visible_columns or not set(data.visible_columns).issubset(ALLOWED_COLUMNS):
        raise HTTPException(422, "עמודות התצוגה אינן תקינות")


def owned(db: DB, user: Current, view_id: uuid.UUID) -> SavedCaseView:
    row = db.scalar(select(SavedCaseView).where(SavedCaseView.id == view_id, SavedCaseView.user_id == user.id))
    if not row: raise HTTPException(404, "התצוגה השמורה לא נמצאה")
    return row


@router.get("/views")
def list_views(db: DB, user: Current) -> list[dict[str, Any]]:
    return [serialize(row) for row in db.scalars(select(SavedCaseView).where(
        SavedCaseView.user_id == user.id).order_by(SavedCaseView.is_default.desc(), SavedCaseView.name))]


@router.post("/views", status_code=201)
def create_view(data: SavedViewIn, db: DB, user: Current) -> dict[str, Any]:
    validate(data)
    if data.is_default: db.execute(update(SavedCaseView).where(SavedCaseView.user_id == user.id).values(is_default=False))
    row = SavedCaseView(user_id=user.id, name=data.name.strip(), filters_json=data.filters, sort=data.sort,
                        visible_columns_json=data.visible_columns, page_size=data.page_size, is_default=data.is_default)
    db.add(row); db.flush(); audit(db, user, "saved_case_view", row.id, "created", after=data.model_dump()); db.commit(); db.refresh(row)
    return serialize(row)


@router.put("/views/{view_id}")
def update_view(view_id: uuid.UUID, data: SavedViewIn, db: DB, user: Current) -> dict[str, Any]:
    validate(data); row = owned(db, user, view_id); before = serialize(row)
    if data.is_default: db.execute(update(SavedCaseView).where(SavedCaseView.user_id == user.id, SavedCaseView.id != row.id).values(is_default=False))
    row.name=data.name.strip(); row.filters_json=data.filters; row.sort=data.sort; row.visible_columns_json=data.visible_columns; row.page_size=data.page_size; row.is_default=data.is_default
    audit(db, user, "saved_case_view", row.id, "updated", before=jsonable_encoder(before), after=data.model_dump()); db.commit(); db.refresh(row); return serialize(row)


@router.post("/views/{view_id}/duplicate", status_code=201)
def duplicate_view(view_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    source=owned(db,user,view_id); base=f"{source.name} - עותק"; name=base; suffix=2
    names=set(db.scalars(select(SavedCaseView.name).where(SavedCaseView.user_id==user.id)))
    while name in names: name=f"{base} {suffix}"; suffix+=1
    row=SavedCaseView(user_id=user.id,name=name,filters_json=source.filters_json,sort=source.sort,visible_columns_json=source.visible_columns_json,page_size=source.page_size,is_default=False)
    db.add(row);db.flush();audit(db,user,"saved_case_view",row.id,"duplicated",after={"source_id":str(source.id)});db.commit();db.refresh(row);return serialize(row)


@router.post("/views/{view_id}/default")
def set_default(view_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    row=owned(db,user,view_id);db.execute(update(SavedCaseView).where(SavedCaseView.user_id==user.id).values(is_default=False));row.is_default=True;audit(db,user,"saved_case_view",row.id,"set_default");db.commit();db.refresh(row);return serialize(row)


@router.delete("/views/{view_id}", status_code=204)
def delete_view(view_id: uuid.UUID, db: DB, user: Current) -> None:
    row=owned(db,user,view_id);audit(db,user,"saved_case_view",row.id,"deleted",before=jsonable_encoder(serialize(row)));db.delete(row);db.commit()


def bulk_permission(action: str) -> str:
    return {"assign":"case.assign", "status":"case.change_status", "priority":"case.update",
            "add_participant":"case.manage_participants"}[action]


def preview_item(db: DB, user: Current, item: Case | None, action: str, target_id: uuid.UUID) -> dict[str, Any]:
    if not item or not CaseVisibilityService(db,user).can_view(item):
        return {"case_id":str(item.id) if item else None,"eligible":False,"reason":"הקריאה אינה זמינה"}
    granted=permissions(db,user,item.environment_id);required=bulk_permission(action)
    reason=None
    if required not in granted: reason="אין הרשאה לפעולה"
    elif item.is_locked and not can_manage_locked_case(db,user,item.environment_id): reason="הקריאה נעולה"
    elif action in {"status","priority"} and not CaseSemanticFieldService(db).validate_value(f"case.{action}",target_id,require_active=True): reason="הערך אינו פעיל"
    elif action in {"assign","add_participant"}:
        candidate=db.get(User,target_id);membership=db.scalar(select(EnvironmentMembership.id).where(
            EnvironmentMembership.environment_id==item.environment_id,EnvironmentMembership.user_id==target_id,
            EnvironmentMembership.is_active.is_(True)))
        if not candidate or not candidate.is_active or candidate.status!="active" or not membership: reason="המשתמש אינו פעיל או אינו משויך לסביבה"
    return {"case_id":str(item.id),"case_number":item.case_number,"version":item.version,"eligible":reason is None,"reason":reason}


@router.post("/bulk/preview", status_code=201)
def preview_bulk(data: BulkPreviewIn, db: DB, user: Current) -> dict[str, Any]:
    rows=[preview_item(db,user,db.get(Case,case_id),data.action,data.target_id) for case_id in dict.fromkeys(data.case_ids)]
    preview=BulkCaseActionPreview(user_id=user.id,action=data.action,target_value_json={"target_id":str(data.target_id)},
        snapshot_json=rows,expires_at=datetime.now(UTC)+timedelta(minutes=15))
    db.add(preview);db.flush();audit(db,user,"bulk_case_action",preview.id,"previewed",after={"action":data.action,"count":len(rows)});db.commit()
    return {"preview_id":preview.id,"action":data.action,"items":rows,"eligible":sum(row["eligible"] for row in rows),"skipped":sum(not row["eligible"] for row in rows)}


@router.post("/bulk/apply")
def apply_bulk(data: BulkApplyIn, db: DB, user: Current) -> dict[str, Any]:
    preview=db.scalar(select(BulkCaseActionPreview).where(BulkCaseActionPreview.id==data.preview_id,BulkCaseActionPreview.user_id==user.id))
    now=datetime.now(UTC)
    if not preview: raise HTTPException(404,"תצוגת הפעולה לא נמצאה")
    expires=preview.expires_at.replace(tzinfo=UTC) if preview.expires_at.tzinfo is None else preview.expires_at
    if preview.applied_at: raise HTTPException(409,"הפעולה כבר בוצעה")
    if expires<now: raise HTTPException(409,"תצוגת הפעולה פגה")
    target_id=uuid.UUID(preview.target_value_json["target_id"]);results=[];semantics=CaseSemanticFieldService(db)
    for snapshot in preview.snapshot_json:
        if not snapshot.get("eligible"): results.append({**snapshot,"result":"skipped"});continue
        item=db.get(Case,uuid.UUID(snapshot["case_id"]));current=preview_item(db,user,item,preview.action,target_id)
        if not item or not current["eligible"] or item.version!=snapshot["version"]:
            results.append({**snapshot,"result":"failed","reason":current.get("reason") or "הקריאה השתנתה מאז התצוגה"});continue
        binding={"assign":"case.assignee","status":"case.status","priority":"case.priority"}.get(preview.action)
        before=semantics.value_id(item,binding) if binding else None
        if preview.action in {"assign","priority"}: semantics.write(item,f"case.{preview.action if preview.action!='assign' else 'assignee'}",target_id)
        elif preview.action=="status":
            semantics.write(item,"case.status",target_id);target=semantics.option("case.status",target_id);SlaEngine(db).status_changed(item,target.semantic_category if target else "open",user.id);db.add(CaseStatusHistory(case_id=item.id,from_status_id=before,to_status_id=target_id,transition_id=None,changed_by=user.id,comment="bulk workspace action"))
        else:
            existing=db.get(CaseParticipant,(item.id,target_id,"participant"))
            if not existing: db.add(CaseParticipant(case_id=item.id,user_id=target_id,participant_type="participant",added_by=user.id))
        if preview.action=="priority":SlaEngine(db).relevant_field_changed(item)
        item.version+=1;audit(db,user,"case",item.id,f"bulk_{preview.action}",before={"value_id":str(before) if before else None},after={"value_id":str(target_id),"preview_id":str(preview.id)});results.append({**snapshot,"result":"succeeded"})
    preview.applied_at=now;audit(db,user,"bulk_case_action",preview.id,"applied",after={"results":results});db.commit()
    return {"preview_id":preview.id,"succeeded":sum(row["result"]=="succeeded" for row in results),"skipped":sum(row["result"]=="skipped" for row in results),"failed":sum(row["result"]=="failed" for row in results),"items":results}
