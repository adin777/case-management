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
    semantic_binding: str | None = None


class OptionIn(BaseModel):
    label_he: str = Field(min_length=1, max_length=200)
    label_en: str = Field(default="", max_length=200)
    is_active: bool = True


def admin(user: Current) -> None:
    if not user.is_system_admin:
        raise HTTPException(403, "נדרשת הרשאת מנהל מערכת")


def output(row: GlobalCaseFieldDefinition) -> dict[str, Any]:
    return {"id": row.id, "key": row.key, "label_he": row.label_he, "label_en": row.label_en,
            "field_type": row.field_type, "is_required": row.is_required, "is_active": row.is_active,
            "semantic_binding": row.semantic_binding,
            "sort_order": row.sort_order, "configuration": row.configuration_json or {},
            "options": sorted((row.configuration_json or {}).get("options", []), key=lambda item: item["sort_order"])}


@router.get("/global-case-fields")
def fields(db: DB, user: Current, include_inactive: bool = False) -> list[dict[str, Any]]:
    query = select(GlobalCaseFieldDefinition).order_by(GlobalCaseFieldDefinition.sort_order)
    if not include_inactive:
        query = query.where(GlobalCaseFieldDefinition.is_active.is_(True))
    return [output(row) for row in db.scalars(query)]


@router.post("/global-case-fields", status_code=201)
def create(data: FieldIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user)
    if data.field_type not in FIELD_TYPES:
        raise HTTPException(422, "סוג השדה אינו נתמך")
    validate_binding(db, data)
    item = GlobalCaseFieldDefinition(key=f"global_{uuid.uuid4().hex[:16]}",
        sort_order=db.scalar(select(func.count()).select_from(GlobalCaseFieldDefinition)) or 0,
        configuration_json={"options": []}, **data.model_dump())
    db.add(item);db.flush()
    if item.semantic_binding:
        for case in db.scalars(select(Case)):
            CaseSemanticFieldService(db).sync_case(case)
    audit(db,user,"global_case_field",item.id,"created");db.commit()
    return output(item)


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
    audit(db, user, "global_case_field", item.id, "updated"); db.commit(); return output(item)


@router.delete("/global-case-fields/{field_id}", status_code=204)
def remove(field_id: uuid.UUID, db: DB, user: Current) -> None:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item: raise HTTPException(404, "השדה לא נמצא")
    if db.scalar(select(func.count()).select_from(GlobalCaseFieldValue).where(GlobalCaseFieldValue.global_field_id == field_id)):
        raise HTTPException(409, "השדה נמצא בשימוש; ניתן להשבית אותו אך לא למחוק")
    db.delete(item); db.commit()


@router.put("/global-case-fields/order")
def reorder(ids: list[uuid.UUID], db: DB, user: Current) -> list[dict[str, Any]]:
    admin(user); rows = list(db.scalars(select(GlobalCaseFieldDefinition).where(GlobalCaseFieldDefinition.id.in_(ids))))
    if len(rows) != len(ids): raise HTTPException(422, "רשימת הסדר אינה תקינה")
    by_id = {row.id: row for row in rows}
    for index, field_id in enumerate(ids): by_id[field_id].sort_order = index
    db.commit(); return [output(by_id[field_id]) for field_id in ids]


@router.post("/global-case-fields/{field_id}/options", status_code=201)
def add_option(field_id: uuid.UUID, data: OptionIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item or item.field_type not in {"single_select", "multi_select"}:
        raise HTTPException(422, "השדה אינו שדה בחירה")
    configuration = dict(item.configuration_json or {}); options = list(configuration.get("options", []))
    option = {"id": str(uuid.uuid4()), "label_he": data.label_he.strip(), "label_en": data.label_en,
              "is_active": data.is_active, "sort_order": len(options)}
    options.append(option); configuration["options"] = options; item.configuration_json = configuration
    db.commit(); return option


@router.patch("/global-case-fields/{field_id}/options/{option_id}")
def update_option(field_id: uuid.UUID, option_id: uuid.UUID, data: OptionIn, db: DB, user: Current) -> dict[str, Any]:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item: raise HTTPException(404, "השדה לא נמצא")
    configuration = dict(item.configuration_json or {}); options = list(configuration.get("options", []))
    option = next((row for row in options if row["id"] == str(option_id)), None)
    if not option: raise HTTPException(404, "הערך לא נמצא")
    option.update(data.model_dump()); configuration["options"] = options; item.configuration_json = configuration
    db.commit(); return option


@router.delete("/global-case-fields/{field_id}/options/{option_id}", status_code=204)
def remove_option(field_id: uuid.UUID, option_id: uuid.UUID, db: DB, user: Current) -> None:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item: raise HTTPException(404, "השדה לא נמצא")
    if db.scalar(select(func.count()).select_from(GlobalCaseFieldValue).where(
        GlobalCaseFieldValue.global_field_id == field_id,
        GlobalCaseFieldValue.value_json.contains(str(option_id)))):
        raise HTTPException(409, "הערך נמצא בשימוש וניתן להשביתו בלבד")
    configuration = dict(item.configuration_json or {}); options = list(configuration.get("options", []))
    configuration["options"] = [row for row in options if row["id"] != str(option_id)]
    item.configuration_json = configuration; db.commit()


@router.put("/global-case-fields/{field_id}/options/order")
def reorder_options(field_id: uuid.UUID, ids: list[str], db: DB, user: Current) -> list[dict[str, Any]]:
    admin(user); item = db.get(GlobalCaseFieldDefinition, field_id)
    if not item: raise HTTPException(404, "השדה לא נמצא")
    configuration = dict(item.configuration_json or {}); options = list(configuration.get("options", [])); by_id = {row["id"]: row for row in options}
    if set(ids) != set(by_id) or len(ids) != len(set(ids)): raise HTTPException(422, "רשימת הסדר אינה תקינה")
    configuration["options"] = [{**by_id[value], "sort_order": index} for index, value in enumerate(ids)]
    item.configuration_json = configuration; db.commit(); return configuration["options"]


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
