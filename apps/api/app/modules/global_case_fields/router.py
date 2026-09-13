import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.modules.api import DB, Current, audit
from app.modules.case_semantics.service import CaseSemanticFieldService
from app.modules.models import (
    Case,
    Environment,
    EnvironmentGlobalCaseField,
    GlobalCaseFieldDefinition,
    GlobalCaseFieldOption,
    GlobalCaseFieldValue,
)

router = APIRouter(prefix="/api", tags=["global-case-fields"])
FIELD_TYPES = {"text", "textarea", "number", "date", "datetime", "boolean", "single_select",
               "multi_select", "user", "email", "url"}


class FieldIn(BaseModel):
    label_he: str = Field(min_length=1, max_length=200)
    label_en: str = Field(default="", max_length=200)
    field_type: str
    is_required: bool = False
    is_active: bool = True
    track_history: bool = False
    semantic_binding: str | None = None


class OptionIn(BaseModel):
    label_he: str = Field(min_length=1, max_length=200)
    label_en: str = Field(default="", max_length=200)
    is_active: bool = True


def admin(user: Current) -> None:
    if not user.is_system_admin:
        raise HTTPException(403, "נדרשת הרשאת מנהל מערכת")


def option_output(row: GlobalCaseFieldOption) -> dict[str, Any]:
    return {"id":row.id, "label_he":row.label_he, "label_en":row.label_en,
            "is_active":row.is_active, "sort_order":row.sort_order,
            "metadata":row.metadata_json or {}}


def output(row: GlobalCaseFieldDefinition, db: DB | None = None) -> dict[str, Any]:
    options = list(db.scalars(select(GlobalCaseFieldOption).where(
        GlobalCaseFieldOption.global_field_id == row.id).order_by(
            GlobalCaseFieldOption.sort_order))) if db else []
    return {"id": row.id, "key": row.key, "label_he": row.label_he, "label_en": row.label_en,
            "field_type": row.field_type, "is_required": row.is_required, "is_active": row.is_active,
            "track_history": row.track_history,
            "semantic_binding": row.semantic_binding,
            "sort_order": row.sort_order, "configuration": row.configuration_json or {},
            "options": [option_output(option) for option in options]}


@router.get("/global-case-fields")
def fields(db: DB, user: Current, include_inactive: bool = False) -> list[dict[str, Any]]:
    query = select(GlobalCaseFieldDefinition).order_by(GlobalCaseFieldDefinition.sort_order)
    if not include_inactive:
        query = query.where(GlobalCaseFieldDefinition.is_active.is_(True))
    return [output(row, db) for row in db.scalars(query)]


@router.post("/global-case-fields", status_code=201)
def create(data: FieldIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user)
    if data.field_type not in FIELD_TYPES:
        raise HTTPException(422, "סוג השדה אינו נתמך")
    validate_binding(db, data)
    item = GlobalCaseFieldDefinition(key=f"global_{uuid.uuid4().hex[:16]}",
        sort_order=db.scalar(select(func.count()).select_from(GlobalCaseFieldDefinition)) or 0,
        configuration_json={}, **data.model_dump())
    db.add(item);db.flush()
    if item.semantic_binding:
        for case in db.scalars(select(Case)):
            CaseSemanticFieldService(db).sync_case(case)
    audit(db,user,"global_case_field",item.id,"created");db.commit()
    return output(item, db)


@router.patch("/global-case-fields/{field_id}")
def update(field_id: uuid.UUID, data: FieldIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item: raise HTTPException(404, "השדה לא נמצא")
    if data.field_type not in FIELD_TYPES: raise HTTPException(422, "סוג השדה אינו נתמך")
    validate_binding(db, data, field_id)
    for key, value in data.model_dump().items(): setattr(item, key, value)
    if item.semantic_binding:
        for case in db.scalars(select(Case)):
            CaseSemanticFieldService(db).sync_case(case)
    audit(db, user, "global_case_field", item.id, "updated"); db.commit(); return output(item, db)


@router.delete("/global-case-fields/{field_id}")
def remove(field_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item: raise HTTPException(404, "השדה לא נמצא")
    value_count = db.scalar(select(func.count()).select_from(GlobalCaseFieldValue).where(
        GlobalCaseFieldValue.global_field_id == field_id)) or 0
    warning = None
    if item.semantic_binding:
        warning = "השדה משמש כערך מערכת. השבתתו תשבית פעולות התלויות במשמעות העסקית שלו."
    if value_count:
        item.is_active = False
        audit(db, user, "global_case_field", item.id, "deactivated", {"value_count": value_count})
        db.commit()
        return {"action": "deactivated", "value_count": value_count, "warning": warning}
    db.delete(item); audit(db, user, "global_case_field", item.id, "deleted"); db.commit()
    return {"action": "deleted", "value_count": 0, "warning": warning}


@router.put("/global-case-fields/order")
def reorder(ids: list[uuid.UUID], db: DB, user: Current) -> list[dict[str, Any]]:
    admin(user); rows = list(db.scalars(select(GlobalCaseFieldDefinition).where(GlobalCaseFieldDefinition.id.in_(ids))))
    if len(rows) != len(ids): raise HTTPException(422, "רשימת הסדר אינה תקינה")
    by_id = {row.id: row for row in rows}
    for index, field_id in enumerate(ids): by_id[field_id].sort_order = index
    db.commit(); return [output(by_id[field_id], db) for field_id in ids]


@router.post("/global-case-fields/{field_id}/options", status_code=201)
def add_option(field_id: uuid.UUID, data: OptionIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item or item.field_type not in {"single_select", "multi_select"}:
        raise HTTPException(422, "השדה אינו שדה בחירה")
    option = GlobalCaseFieldOption(id=uuid.uuid4(), global_field_id=field_id,
        label_he=data.label_he.strip(), label_en=data.label_en, is_active=data.is_active,
        sort_order=db.scalar(select(func.count()).select_from(GlobalCaseFieldOption).where(
            GlobalCaseFieldOption.global_field_id == field_id)) or 0, metadata_json={})
    db.add(option); db.commit(); return option_output(option)


@router.patch("/global-case-fields/{field_id}/options/{option_id}")
def update_option(field_id: uuid.UUID, option_id: uuid.UUID, data: OptionIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item: raise HTTPException(404, "השדה לא נמצא")
    option = db.get(GlobalCaseFieldOption, option_id)
    if not option or option.global_field_id != field_id: raise HTTPException(404, "הערך לא נמצא")
    for key, value in data.model_dump().items(): setattr(option, key, value)
    db.commit(); return option_output(option)


@router.delete("/global-case-fields/{field_id}/options/{option_id}")
def remove_option(field_id: uuid.UUID, option_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item: raise HTTPException(404, "השדה לא נמצא")
    used = db.scalar(select(func.count()).select_from(GlobalCaseFieldValue).where(
        GlobalCaseFieldValue.global_field_id == field_id,
        GlobalCaseFieldValue.value_json.contains(str(option_id)))) or 0
    option = db.get(GlobalCaseFieldOption, option_id)
    if not option or option.global_field_id != field_id: raise HTTPException(404, "הערך לא נמצא")
    if used:
        option.is_active = False; db.commit()
        return {"action": "deactivated", "value_count": used}
    db.delete(option); db.commit()
    return {"action": "deleted", "value_count": 0}


@router.put("/global-case-fields/{field_id}/options/order")
def reorder_options(field_id: uuid.UUID, ids: list[str], db: DB, user: Current) -> list[dict[str, Any]]:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item: raise HTTPException(404, "השדה לא נמצא")
    options = list(db.scalars(select(GlobalCaseFieldOption).where(
        GlobalCaseFieldOption.global_field_id == field_id))); by_id = {str(row.id): row for row in options}
    if set(ids) != set(by_id) or len(ids) != len(set(ids)): raise HTTPException(422, "רשימת הסדר אינה תקינה")
    for index, value in enumerate(ids): by_id[value].sort_order = index
    db.commit(); return [option_output(by_id[value]) for value in ids]


class EnvironmentFieldConfigIn(BaseModel):
    is_visible: bool = True
    is_required: bool = False
    show_on_create: bool = True
    show_on_edit: bool = True


@router.get("/environments/{environment_id}/global-case-fields/configuration")
def environment_configuration(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    admin(user)
    saved = {row.global_field_id: row for row in db.scalars(select(EnvironmentGlobalCaseField).where(
        EnvironmentGlobalCaseField.environment_id == environment_id))}
    return [{"global_field_id": field.id,
             "is_visible": saved[field.id].is_visible if field.id in saved else True,
             "is_required": saved[field.id].is_required if field.id in saved else False,
             "show_on_create": saved[field.id].show_on_create if field.id in saved else True,
             "show_on_edit": saved[field.id].show_on_edit if field.id in saved else True}
            for field in db.scalars(select(GlobalCaseFieldDefinition).order_by(
                GlobalCaseFieldDefinition.sort_order))]


def validate_binding(db: DB, data: FieldIn, current_id: uuid.UUID | None = None) -> None:
    supported = {None,"none","case.status","case.priority","case.sub_priority","case.assignee"}
    if data.semantic_binding not in supported:
        raise HTTPException(422, "החיבור הסמנטי אינו נתמך")
    expected_types={"case.status":"single_select","case.priority":"single_select",
        "case.sub_priority":"single_select","case.assignee":"user"}
    if data.semantic_binding in expected_types:
        if data.field_type != expected_types[data.semantic_binding]:
            raise HTTPException(422, "סוג השדה אינו מתאים לחיבור הסמנטי")
        duplicate = db.scalar(select(GlobalCaseFieldDefinition.id).where(
            GlobalCaseFieldDefinition.semantic_binding == data.semantic_binding,
            GlobalCaseFieldDefinition.is_active.is_(True),
            GlobalCaseFieldDefinition.id != current_id if current_id else GlobalCaseFieldDefinition.id.is_not(None),
        ))
        if duplicate and data.is_active:
            raise HTTPException(409, "כבר קיים שדה פעיל המחובר למטפל")


@router.put("/environments/{environment_id}/global-case-fields/{field_id}/configuration")
def configure(environment_id: uuid.UUID, field_id: uuid.UUID, data: EnvironmentFieldConfigIn,
              db: DB, user: Current) -> dict[str, bool]:
    admin(user)
    if not db.get(Environment, environment_id) or not db.get(GlobalCaseFieldDefinition, field_id):
        raise HTTPException(404, "הסביבה או השדה לא נמצאו")
    row = db.get(EnvironmentGlobalCaseField, (environment_id, field_id))
    if not row: row = EnvironmentGlobalCaseField(environment_id=environment_id, global_field_id=field_id); db.add(row)
    for key, value in data.model_dump().items(): setattr(row, key, value)
    db.commit()
    return data.model_dump()


@router.put("/environments/{environment_id}/global-case-fields/{field_id}/visibility")
def visibility(environment_id: uuid.UUID, field_id: uuid.UUID, is_visible: bool, db: DB, user: Current) -> dict[str, bool]:
    return configure(environment_id, field_id, EnvironmentFieldConfigIn(is_visible=is_visible), db, user)
