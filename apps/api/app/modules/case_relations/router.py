import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.modules.api import DB, Current, audit, case_access, require
from app.modules.case_relations.service import (
    apply_status_snapshot,
    create_relation,
    relation_case,
    status_snapshot,
)
from app.modules.models import Case, CaseRelation, CaseStatusChangePreview

router = APIRouter(prefix="/api")

class RelationIn(BaseModel):
    child_case_id: uuid.UUID

class StatusPreviewIn(BaseModel):
    target_status_id: uuid.UUID
    include_descendants: bool = False

class StatusApplyIn(BaseModel):
    preview_id: uuid.UUID


@router.get("/cases/{case_id}/relations")
def get_relations(case_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(Case, case_id)
    if not item: raise HTTPException(404, "הקריאה לא נמצאה")
    case_access(db, user, item)
    parent_relation = db.scalar(select(CaseRelation).where(CaseRelation.child_case_id == item.id))
    parent = db.get(Case, parent_relation.parent_case_id) if parent_relation else None
    if parent:
        try: case_access(db, user, parent)
        except HTTPException: parent = None
    children = []
    for relation in db.scalars(select(CaseRelation).where(CaseRelation.parent_case_id == item.id)):
        child = db.get(Case, relation.child_case_id)
        if not child: continue
        try: case_access(db, user, child)
        except HTTPException: continue
        children.append({"relation_id":str(relation.id), **relation_case(db, child)})
    return {"parent":relation_case(db,parent) if parent else None,"children":children}


@router.post("/cases/{case_id}/relations", status_code=201)
@router.post("/cases/{case_id}/children", status_code=201)
def link_child(case_id: uuid.UUID, data: RelationIn, db: DB, user: Current) -> dict[str, Any]:
    parent, child = db.get(Case, case_id), db.get(Case, data.child_case_id)
    if not parent or not child: raise HTTPException(404, "הקריאה הראשית או קריאת המשנה לא נמצאה")
    case_access(db,user,parent); case_access(db,user,child)
    require(db,user,parent.environment_id,"case.update"); require(db,user,child.environment_id,"case.update")
    relation=create_relation(db,parent,child,user)
    audit(db,user,"case",parent.id,"child_case_linked",after={"child_case_id":str(child.id)})
    db.commit(); return {"relation_id":str(relation.id),**relation_case(db,child)}


@router.delete("/cases/{case_id}/relations/{relation_id}", status_code=204)
def unlink(case_id:uuid.UUID, relation_id:uuid.UUID, db:DB, user:Current) -> None:
    parent=db.get(Case,case_id); relation=db.get(CaseRelation,relation_id)
    if not parent or not relation or relation.parent_case_id!=parent.id: raise HTTPException(404,"הקשר לא נמצא")
    require(db,user,parent.environment_id,"case.update"); child_id=relation.child_case_id; db.delete(relation)
    audit(db,user,"case",parent.id,"child_case_unlinked",after={"child_case_id":str(child_id)})
    db.commit()


@router.post("/cases/{case_id}/status-change-preview")
def preview_status(case_id:uuid.UUID,data:StatusPreviewIn,db:DB,user:Current)->dict[str,Any]:
    parent=db.get(Case,case_id)
    if not parent: raise HTTPException(404,"הקריאה לא נמצאה")
    case_access(db,user,parent); row=status_snapshot(db,parent,data.target_status_id,user,data.include_descendants)
    db.commit(); return {"preview_id":str(row.id),**row.snapshot_json}


@router.post("/cases/{case_id}/status-change")
def apply_status(case_id:uuid.UUID,data:StatusApplyIn,db:DB,user:Current)->dict[str,Any]:
    preview=db.get(CaseStatusChangePreview,data.preview_id)
    if not preview or preview.parent_case_id!=case_id: raise HTTPException(404,"תצוגת השינוי לא נמצאה")
    result=apply_status_snapshot(db,preview,user)
    audit(db,user,"case",case_id,"bulk_status_from_parent",after={"preview_id":str(preview.id),**result})
    db.commit(); return result
