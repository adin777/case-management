import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.case_visibility.service import can_manage_locked_case
from app.modules.models import (
    Case,
    CaseRelation,
    CaseStatusChangePreview,
    Environment,
    GlobalStatusDefinition,
    User,
)
from app.modules.operations.models import CaseStatusHistory


def descendants(db: Session, case_id: uuid.UUID) -> list[uuid.UUID]:
    result: list[uuid.UUID] = []; frontier = [case_id]; seen = {case_id}
    while frontier:
        child_ids = list(db.scalars(select(CaseRelation.child_case_id).where(
            CaseRelation.parent_case_id.in_(frontier), CaseRelation.relation_type == "parent_child")))
        frontier = []
        for child_id in child_ids:
            if child_id not in seen:
                seen.add(child_id); result.append(child_id); frontier.append(child_id)
    return result


def create_relation(db: Session, parent: Case, child: Case, actor: User) -> CaseRelation:
    if parent.id == child.id:
        raise HTTPException(422, {"code":"CASE_RELATION_SELF","message":"קריאה אינה יכולה להיות קריאת משנה של עצמה","details":{}})
    if parent.id in descendants(db, child.id):
        raise HTTPException(409, {"code":"CASE_RELATION_CYCLE","message":"הקשר ייצור מעגל בהיררכיית הקריאות","details":{}})
    if db.scalar(select(CaseRelation).where(CaseRelation.child_case_id == child.id)):
        raise HTTPException(409, {"code":"CASE_ALREADY_HAS_PARENT","message":"לקריאת המשנה כבר קיימת קריאה ראשית","details":{}})
    row = CaseRelation(parent_case_id=parent.id, child_case_id=child.id, created_by=actor.id)
    db.add(row); db.flush(); return row


def relation_case(db: Session, item: Case) -> dict[str, Any]:
    environment = db.get(Environment, item.environment_id)
    semantics=CaseSemanticFieldService(db)
    status_id=semantics.value_id(item,"case.status")
    return {"id":str(item.id), "case_number":item.case_number, "title":item.title,
        "environment_id":str(item.environment_id), "environment":environment.name_he if environment else "",
        "status_id":str(status_id) if status_id else None,"status":semantics.label(item,"case.status"),
        "assignee":semantics.label(item,"case.assignee") or None}


def status_snapshot(db: Session, parent: Case, target_status_id: uuid.UUID, actor: User,
                    include_descendants: bool) -> CaseStatusChangePreview:
    from app.modules.api import permissions
    target = db.get(GlobalStatusDefinition, target_status_id)
    if not target or not target.is_active:
        raise HTTPException(409, {"code":"INVALID_STATUS","message":"סטטוס היעד הגלובלי אינו פעיל","details":{}})
    candidates = [parent.id] + (descendants(db, parent.id) if include_descendants else [])
    eligible: list[str] = []; unauthorized: list[str] = []; locked: list[str] = []
    for case_id in candidates:
        item = db.get(Case, case_id)
        if not item or "case.change_status" not in permissions(db, actor, item.environment_id):
            unauthorized.append(str(case_id)); continue
        if item.is_locked and not can_manage_locked_case(db, actor, item.environment_id):
            locked.append(str(case_id)); continue
        eligible.append(str(case_id))
    snapshot = {"eligible":eligible,"unauthorized":unauthorized,"locked":locked,
        "total_descendants":max(0,len(candidates)-1)}
    row = CaseStatusChangePreview(parent_case_id=parent.id, target_status_id=target.id,
        actor_id=actor.id, include_descendants=include_descendants, snapshot_json=snapshot)
    db.add(row); db.flush(); return row


def apply_status_snapshot(db: Session, preview: CaseStatusChangePreview, actor: User) -> dict[str, Any]:
    if preview.actor_id != actor.id: raise HTTPException(403, "תצוגת השינוי שייכת למשתמש אחר")
    if preview.applied_at: raise HTTPException(409, "תצוגת השינוי כבר הוחלה")
    target = db.get(GlobalStatusDefinition, preview.target_status_id)
    if not target or not target.is_active: raise HTTPException(409, "סטטוס היעד אינו פעיל עוד")
    updated: list[str] = []
    for raw_id in preview.snapshot_json.get("eligible", []):
        item = db.get(Case, uuid.UUID(raw_id))
        if not item: continue
        previous=item.workflow_status_id;CaseSemanticFieldService(db).write(item,"case.status",target.id);item.version+=1
        if target.semantic_category == "closed" or target.is_final: item.closed_at = datetime.now(UTC)
        db.add(CaseStatusHistory(case_id=item.id, from_status_id=previous, to_status_id=target.id,
            transition_id=None, changed_by=actor.id, comment="bulk_status_from_parent"))
        updated.append(str(item.id))
    preview.applied_at = datetime.now(UTC)
    return {**preview.snapshot_json, "updated":updated, "updated_count":len(updated)}
