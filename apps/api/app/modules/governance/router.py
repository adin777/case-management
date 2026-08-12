import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy import delete, func, or_, select

from app.modules.api import DB, Current, audit, case_access, password_hash, require
from app.modules.employees.service import sync_employee_for_user
from app.modules.models import (
    AutomationRule,
    Case,
    Comment,
    Environment,
    EnvironmentMembership,
    EnvironmentUserField,
    Group,
    GroupEnvironmentRole,
    GroupMember,
    Permission,
    PriorityDefinition,
    RequestType,
    Role,
    RolePermission,
    SubPriorityDefinition,
    User,
    UserFieldDefinition,
    UserFieldValue,
    Visibility,
)
from app.modules.numbering.service import NumberingService
from app.modules.operations.models import SlaPolicy

router = APIRouter(prefix="/api", tags=["governance"])
logger = logging.getLogger(__name__)


class UserCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    is_active: bool = True
    is_system_admin: bool = False
    first_name: str | None = None
    last_name: str | None = None
    user_principal_name: str | None = None
    department: str | None = None
    job_title: str | None = None
    phone: str | None = None
    mobile_phone: str | None = None
    employee_id: str | None = None
    computer_identifier: str | None = None


class UserPatch(BaseModel):
    display_name: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    is_system_admin: bool | None = None
    environment_id: uuid.UUID | None = None
    first_name: str | None = None
    last_name: str | None = None
    user_principal_name: str | None = None
    department: str | None = None
    job_title: str | None = None
    phone: str | None = None
    mobile_phone: str | None = None
    employee_id: str | None = None
    computer_identifier: str | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=200)


class GroupIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("יש להזין שם קבוצה הכולל לפחות שני תווים")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class GroupMemberIn(BaseModel):
    user_id: uuid.UUID


class GroupRoleIn(BaseModel):
    environment_id: uuid.UUID
    role_id: uuid.UUID


class RoleIn(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_.-]*$")
    name: str
    name_he: str | None = None
    description: str | None = None
    description_he: str | None = None
    scope: str = Field(pattern="^(system|environment)$")
    sort_order: int = 0
    permissions: list[str] = Field(default_factory=list)
    is_active: bool = True


class UserFieldOptionIn(BaseModel):
    value: str = Field(min_length=1, max_length=100)
    label_he: str = Field(min_length=1, max_length=200)
    label_en: str = ""
    is_active: bool = True
    sort_order: int = 0


class UserFieldIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label_he: str = Field(min_length=1)
    label_en: str = ""
    field_type: str = Field(
        pattern="^(short_text|long_text|number|date|boolean|single_select|multi_select|user|email|phone)$"
    )
    is_required: bool = False
    is_active: bool = True
    options_json: list[UserFieldOptionIn] = Field(default_factory=list)
    default_value_json: Any = None
    validation_json: dict = Field(default_factory=dict)
    sort_order: int = 0
    environment_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return value.strip()

    @field_validator("label_he", "label_en")
    @classmethod
    def normalize_labels(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_options(self) -> "UserFieldIn":
        if self.field_type == "single_select" and len(self.options_json) < 1:
            raise ValueError("יש להזין לפחות ערך אחד עבור שדה בחירה")
        if self.field_type == "multi_select" and len(self.options_json) < 2:
            raise ValueError("יש להזין לפחות שני ערכים עבור שדה בחירה מרובה")
        if self.field_type not in {"single_select", "multi_select"}:
            self.options_json = []
        if not self.label_en:
            self.label_en = self.label_he
        values = [option.value for option in self.options_json]
        if len(values) != len(set(values)):
            raise ValueError("ערכי הבחירה חייבים להיות ייחודיים")
        return self


class EnvironmentFieldIn(BaseModel):
    user_field_definition_id: uuid.UUID
    is_visible: bool = True
    is_required: bool = False
    is_editable_by_user: bool = False
    is_editable_by_environment_admin: bool = True
    sort_order: int = 0


class MembershipCreate(BaseModel):
    user_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None


class MembershipPatch(BaseModel):
    is_active: bool | None = None


class UserEnvironmentMembershipIn(BaseModel):
    environment_id: uuid.UUID


class CopyEnvironmentMembershipsIn(BaseModel):
    source_user_id: uuid.UUID
    target_user_ids: list[uuid.UUID] = Field(min_length=1)
    mode: str = Field(pattern="^(add_missing|replace_all)$")


class UserGroupsIn(BaseModel):
    group_ids: list[uuid.UUID] = Field(default_factory=list)


class CopyUserGroupsIn(BaseModel):
    source_user_id: uuid.UUID
    target_user_ids: list[uuid.UUID] = Field(min_length=1)
    mode: str = Field(pattern="^(add_missing|replace_all)$")


class PriorityIn(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    label_he: str
    label_en: str = ""
    description: str | None = None
    color: str = "#64748b"
    sort_order: int = 0
    is_active: bool = True


class SubPriorityIn(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    label_he: str
    label_en: str = ""
    description: str | None = None
    color: str = "#64748b"
    sort_order: int = 0
    is_active: bool = True


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class AutomationRuleIn(BaseModel):
    environment_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    is_active: bool = True
    trigger_type: str = Field(
        pattern="^(case_created|field_value_changed|request_type_selected|status_changed|priority_changed|participant_added|approval_completed)$"
    )
    conditions_json: dict = Field(default_factory=dict)
    actions_json: list[dict[str, Any]] = Field(default_factory=list)
    priority: int = 0


def system_admin(user: User) -> None:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")


def user_dict(db: DB, item: User) -> dict[str, Any]:
    groups = db.execute(
        select(Group.id, Group.name).join(GroupMember).where(GroupMember.user_id == item.id)
    ).all()
    memberships = db.execute(
        select(Environment.id, Environment.name_he, EnvironmentMembership.source)
        .join(EnvironmentMembership, EnvironmentMembership.environment_id == Environment.id)
        .where(EnvironmentMembership.user_id == item.id)
    ).all()
    return {
        "id": item.id,
        "email": item.email,
        "display_name": item.display_name,
        "is_active": item.is_active,
        "is_system_admin": item.is_system_admin,
        "first_name": item.first_name, "last_name": item.last_name,
        "user_principal_name": item.user_principal_name, "department": item.department,
        "job_title": item.job_title, "phone": item.phone, "mobile_phone": item.mobile_phone,
        "employee_id": item.employee_id, "computer_identifier": item.computer_identifier,
        "directory_object_id": item.directory_object_id, "source": item.source,
        "directory_enabled": item.directory_enabled, "status": item.status,
        "archived_at": item.archived_at, "last_directory_sync_at": item.last_directory_sync_at,
        "created_at": item.created_at,
        "last_login_at": item.last_login_at,
        "groups": [{"id": row[0], "name": row[1]} for row in groups],
        "memberships": [
            {"environment_id": row[0], "environment_name": row[1], "source": row[2]}
            for row in memberships
        ],
    }


@router.get("/users")
def list_users(
    db: DB,
    user: Current,
    search: str = "",
    environment_id: uuid.UUID | None = None,
    active_only: bool = True,
    status_filter: str | None = None,
    source: str | None = None,
    department: str | None = None,
    job_title: str | None = None,
) -> list[dict[str, Any]]:
    query = select(User).order_by(User.display_name)
    if search:
        query = query.where(or_(User.display_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"),
                                User.user_principal_name.ilike(f"%{search}%")))
    if active_only and not status_filter: query = query.where(User.status == "active")
    if status_filter: query = query.where(User.status == status_filter)
    if source: query = query.where(User.source == source)
    if department: query = query.where(User.department == department)
    if job_title: query = query.where(User.job_title == job_title)
    if environment_id and not user.is_system_admin:
        require(db, user, environment_id, "environment.users.manage")
        query = query.join(EnvironmentMembership).where(
            EnvironmentMembership.environment_id == environment_id
        )
    return [user_dict(db, item) for item in db.scalars(query).unique()]


@router.post("/users", status_code=201)
def create_user(data: UserCreate, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    if db.scalar(select(User.id).where(func.lower(User.email) == data.email.lower())):
        raise HTTPException(409, "Email already exists")
    profile = data.model_dump(exclude={"password", "is_active", "is_system_admin", "display_name", "email"})
    profile["user_principal_name"] = profile["user_principal_name"] or data.email.lower()
    item = User(
        display_name=data.display_name,
        email=data.email.lower(),
        password_hash=password_hash.hash(data.password),
        is_active=data.is_active,
        is_system_admin=data.is_system_admin,
        status="active" if data.is_active else "inactive", source="manual",
        **profile,
    )
    db.add(item)
    db.flush()
    sync_employee_for_user(db, item)
    audit(db, user, "user", item.id, "created")
    db.commit()
    return user_dict(db, item)


@router.get("/users/{user_id}")
def get_user(user_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, "User not found")
    return user_dict(db, item)


@router.put("/users/{user_id}/groups")
def set_user_groups(user_id: uuid.UUID, data: UserGroupsIn, db: DB, user: Current) -> dict[str, int]:
    system_admin(user)
    if not db.get(User, user_id):
        raise HTTPException(404, "המשתמש לא נמצא")
    known = set(db.scalars(select(Group.id).where(Group.id.in_(data.group_ids))))
    if known != set(data.group_ids):
        raise HTTPException(422, "אחת הקבוצות אינה קיימת")
    before = set(db.scalars(select(GroupMember.group_id).where(GroupMember.user_id == user_id)))
    db.execute(delete(GroupMember).where(GroupMember.user_id == user_id))
    for group_id in data.group_ids:
        db.add(GroupMember(group_id=group_id, user_id=user_id, added_by=user.id))
    audit(db, user, "user_groups", user_id, "replaced",
          before={"group_ids": [str(value) for value in before]},
          after={"group_ids": [str(value) for value in data.group_ids]})
    db.commit()
    return {"groups": len(data.group_ids)}


def _group_copy_preview(data: CopyUserGroupsIn, db: DB) -> dict[str, Any]:
    source = set(db.scalars(select(GroupMember.group_id).where(GroupMember.user_id == data.source_user_id)))
    targets = []
    for target_id in data.target_user_ids:
        current = set(db.scalars(select(GroupMember.group_id).where(GroupMember.user_id == target_id)))
        result = source if data.mode == "replace_all" else current | source
        targets.append({"user_id": target_id, "current_count": len(current),
                        "result_count": len(result), "changed": current != result})
    return {"source_group_ids": list(source), "targets": targets, "mode": data.mode}


@router.post("/user-group-memberships/copy/preview")
def copy_user_groups_preview(data: CopyUserGroupsIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    return _group_copy_preview(data, db)


@router.post("/user-group-memberships/copy")
def copy_user_groups(data: CopyUserGroupsIn, db: DB, user: Current) -> dict[str, int]:
    system_admin(user)
    preview = _group_copy_preview(data, db)
    source = set(preview["source_group_ids"])
    for target_id in data.target_user_ids:
        if not db.get(User, target_id):
            raise HTTPException(404, "אחד ממשתמשי היעד אינו קיים")
        current = set(db.scalars(select(GroupMember.group_id).where(GroupMember.user_id == target_id)))
        result = source if data.mode == "replace_all" else current | source
        db.execute(delete(GroupMember).where(GroupMember.user_id == target_id))
        for group_id in result:
            db.add(GroupMember(group_id=group_id, user_id=target_id, added_by=user.id))
    audit(db, user, "user_groups", data.source_user_id, "copied", after=data.model_dump(mode="json"))
    db.commit()
    return {"targets": len(data.target_user_ids), "groups": len(source)}


@router.patch("/users/{user_id}")
def update_user(user_id: uuid.UUID, data: UserPatch, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, "User not found")
    if not user.is_system_admin:
        if not data.environment_id:
            raise HTTPException(403, "Environment scope required")
        require(db, user, data.environment_id, "environment.users.manage")
        if data.is_system_admin is not None:
            raise HTTPException(403, "Environment administrators cannot manage system administrators")
        member = db.scalar(
            select(EnvironmentMembership.id).where(
                EnvironmentMembership.environment_id == data.environment_id,
                EnvironmentMembership.user_id == item.id,
            )
        )
        if not member:
            raise HTTPException(403, "User is outside this environment")
    for key, value in data.model_dump(exclude_unset=True, exclude={"environment_id"}).items():
        setattr(item, key, value)
    if data.status is not None:
        item.is_active = data.status == "active"
        item.archived_at = datetime.now(UTC) if data.status == "archived" else None
    elif data.is_active is not None:
        item.status = "active" if data.is_active else "inactive"
        item.archived_at = None
    audit(db, user, "user", item.id, "updated")
    db.commit()
    return user_dict(db, item)


@router.put("/users/{user_id}/environment-memberships")
def set_user_environment_memberships(
    user_id: uuid.UUID, rows: list[UserEnvironmentMembershipIn], db: DB, user: Current
) -> dict[str, Any]:
    system_admin(user)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "המשתמש לא נמצא")
    if len({row.environment_id for row in rows}) != len(rows):
        raise HTTPException(422, "ניתן לשייך משתמש פעם אחת בלבד לכל סביבת עבודה")
    for row in rows:
        if not db.get(Environment, row.environment_id):
            raise HTTPException(422, "סביבה אינה קיימת")
    before = [
        {"environment_id": str(item.environment_id)}
        for item in db.scalars(
            select(EnvironmentMembership).where(EnvironmentMembership.user_id == user_id)
        )
    ]
    db.execute(delete(EnvironmentMembership).where(EnvironmentMembership.user_id == user_id))
    for row in rows:
        db.add(EnvironmentMembership(user_id=user_id, role_id=None, source="manual", is_active=True, **row.model_dump()))
    audit(
        db,
        user,
        "user",
        user_id,
        "environment_memberships_replaced",
        before={"memberships": before},
        after={"memberships": [row.model_dump(mode="json") for row in rows]},
    )
    db.commit()
    return user_dict(db, target)


@router.post("/users/environment-memberships/copy/preview")
def copy_user_environment_memberships_preview(
    data: CopyEnvironmentMembershipsIn, db: DB, user: Current
) -> dict[str, Any]:
    system_admin(user)
    source = list(db.scalars(select(EnvironmentMembership).where(
        EnvironmentMembership.user_id == data.source_user_id,
        EnvironmentMembership.is_active.is_(True))))
    targets = []
    for target_id in data.target_user_ids:
        current = set(db.scalars(select(EnvironmentMembership.environment_id).where(
            EnvironmentMembership.user_id == target_id)))
        source_ids = {row.environment_id for row in source}
        result = source_ids if data.mode == "replace_all" else current | source_ids
        targets.append({"user_id": target_id, "current_count": len(current),
                        "result_count": len(result), "changed": current != result})
    return {"source_count": len(source), "targets": targets, "mode": data.mode}


@router.post("/users/environment-memberships/copy")
def copy_user_environment_memberships(
    data: CopyEnvironmentMembershipsIn, db: DB, user: Current
) -> dict[str, int]:
    system_admin(user)
    source_rows = list(
        db.scalars(
            select(EnvironmentMembership).where(
                EnvironmentMembership.user_id == data.source_user_id,
                EnvironmentMembership.is_active.is_(True),
            )
        )
    )
    if not source_rows:
        raise HTTPException(409, "למשתמש המקור אין סביבות עבודה פעילות להעתקה")
    copied = 0
    for target_id in set(data.target_user_ids):
        if target_id == data.source_user_id or not db.get(User, target_id):
            continue
        if data.mode == "replace_all":
            db.execute(delete(EnvironmentMembership).where(EnvironmentMembership.user_id == target_id))
        existing = set(
            db.scalars(
                select(EnvironmentMembership.environment_id).where(
                    EnvironmentMembership.user_id == target_id
                )
            )
        )
        for source in source_rows:
            if source.environment_id in existing:
                continue
            db.add(
                EnvironmentMembership(
                    environment_id=source.environment_id,
                    user_id=target_id,
                    role_id=None,
                    source="manual",
                    is_active=True,
                )
            )
            copied += 1
        audit(
            db,
            user,
            "user",
            target_id,
            "environment_memberships_copied",
            after={"source_user_id": str(data.source_user_id), "mode": data.mode},
        )
    db.commit()
    return {"copied": copied}


@router.post("/users/{user_id}/activate")
def activate_user(user_id: uuid.UUID, db: DB, user: Current) -> dict[str, bool]:
    system_admin(user)
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, "User not found")
    item.is_active = True
    audit(db, user, "user", item.id, "activated")
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: uuid.UUID, db: DB, user: Current) -> dict[str, bool]:
    system_admin(user)
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, "User not found")
    item.is_active = False
    audit(db, user, "user", item.id, "deactivated")
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/reset-development-password")
def reset_password(user_id: uuid.UUID, data: PasswordReset, db: DB, user: Current) -> dict[str, bool]:
    system_admin(user)
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, "User not found")
    item.password_hash = password_hash.hash(data.password)
    audit(db, user, "user", item.id, "development_password_reset")
    db.commit()
    return {"ok": True}


@router.get("/groups")
def list_groups(db: DB, user: Current) -> list[dict[str, Any]]:
    system_admin(user)
    rows = db.scalars(select(Group).order_by(Group.name))
    return [
        {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "is_active": row.is_active,
            "member_count": db.scalar(
                select(func.count()).select_from(GroupMember).where(GroupMember.group_id == row.id)
            ),
        }
        for row in rows
    ]


@router.post("/groups", status_code=201)
def create_group(data: GroupIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    if db.scalar(select(Group.id).where(func.lower(Group.name) == data.name.lower())):
        raise HTTPException(409, "כבר קיימת קבוצת משתמשים בשם זה")
    try:
        item = Group(system_number=NumberingService.next(db, "user_group"), **data.model_dump())
        db.add(item)
        db.flush()
        audit(db, user, "group", item.id, "created")
        db.commit()
        return {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "is_active": item.is_active,
            "member_count": 0,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while creating user group")
        db.rollback()
        raise


@router.get("/groups/{group_id}")
def get_group(group_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    item = db.get(Group, group_id)
    if not item:
        raise HTTPException(404, "Group not found")
    members = db.execute(
        select(User.id, User.display_name, User.email)
        .join(GroupMember)
        .where(GroupMember.group_id == group_id)
    ).all()
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "is_active": item.is_active,
        "members": [{"id": r[0], "display_name": r[1], "email": r[2]} for r in members],
    }


@router.patch("/groups/{group_id}")
def update_group(group_id: uuid.UUID, data: GroupIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    item = db.get(Group, group_id)
    if not item:
        raise HTTPException(404, "Group not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, "group", item.id, "updated")
    db.commit()
    return {"id": item.id, **data.model_dump()}


@router.post("/groups/{group_id}/members", status_code=201)
def add_group_member(group_id: uuid.UUID, data: GroupMemberIn, db: DB, user: Current) -> dict[str, bool]:
    system_admin(user)
    if not db.get(Group, group_id) or not db.get(User, data.user_id):
        raise HTTPException(404, "Group or user not found")
    exists = db.get(GroupMember, (group_id, data.user_id))
    if not exists:
        db.add(GroupMember(group_id=group_id, user_id=data.user_id, added_by=user.id))
        audit(db, user, "group", group_id, "member_added", after={"user_id": str(data.user_id)})
        db.commit()
    return {"ok": True}


@router.delete("/groups/{group_id}/members/{user_id}", status_code=204)
def remove_group_member(group_id: uuid.UUID, user_id: uuid.UUID, db: DB, user: Current) -> None:
    system_admin(user)
    item = db.get(GroupMember, (group_id, user_id))
    if not item:
        raise HTTPException(404, "Membership not found")
    db.delete(item)
    audit(db, user, "group", group_id, "member_removed", after={"user_id": str(user_id)})
    db.commit()


@router.post("/groups/{group_id}/roles", status_code=201)
def assign_group_role(group_id: uuid.UUID, data: GroupRoleIn, db: DB, user: Current) -> dict[str, bool]:
    system_admin(user)
    raise HTTPException(410, "מנגנון התפקידים הישן בוטל; הרשאות מנוהלות באמצעות קבוצות וחריגות משתמש")
    row = GroupEnvironmentRole(group_id=group_id, **data.model_dump())
    db.merge(row)
    audit(db, user, "group", group_id, "environment_role_assigned")
    db.commit()
    return {"ok": True}


@router.get("/permissions")
def list_permissions(db: DB, user: Current) -> list[dict[str, Any]]:
    system_admin(user)
    return [{"code": row.code, "description": row.description} for row in db.scalars(select(Permission))]


@router.get("/roles")
def list_roles(db: DB, user: Current) -> list[dict[str, Any]]:
    system_admin(user)
    raise HTTPException(410, "מנגנון התפקידים הישן בוטל")
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "name_he": r.name_he or r.name,
            "description": r.description,
            "scope": r.scope,
            "permissions": sorted(permissions_for_role(db, r)),
            "is_active": r.is_active,
            "sort_order": r.sort_order,
        }
        for r in db.scalars(select(Role).order_by(Role.name))
    ]


def permissions_for_role(db: DB, role: Role) -> set[str]:
    normalized = set(
        db.scalars(select(RolePermission.permission_code).where(RolePermission.role_id == role.id))
    )
    return normalized | set(role.permissions or [])


@router.post("/roles", status_code=201)
def create_role(data: RoleIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    raise HTTPException(410, "מנגנון התפקידים הישן בוטל")
    unknown = set(data.permissions) - set(db.scalars(select(Permission.code)))
    if unknown:
        raise HTTPException(422, f"Unknown permissions: {', '.join(sorted(unknown))}")
    generated_code = data.code or f"role_{uuid.uuid4().hex[:10]}"
    item = Role(
        system_number=f"ROLE-{uuid.uuid4().hex[:8].upper()}",
        code=generated_code,
        name=data.name,
        name_he=data.name_he or data.name,
        description=data.description,
        description_he=data.description_he or data.description,
        scope=data.scope,
        sort_order=data.sort_order,
        permissions=data.permissions,
        is_active=data.is_active,
    )
    db.add(item)
    db.flush()
    for code in data.permissions:
        db.add(RolePermission(role_id=item.id, permission_code=code))
    audit(db, user, "role", item.id, "created")
    db.commit()
    return {"id": item.id, **data.model_dump(), "code": generated_code}


@router.get("/roles/{role_id}")
def get_role(role_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    raise HTTPException(410, "מנגנון התפקידים הישן בוטל")
    item = db.get(Role, role_id)
    if not item:
        raise HTTPException(404, "Role not found")
    return {
        "id": item.id,
        "code": item.code,
        "name": item.name,
        "name_he": item.name_he or item.name,
        "description": item.description,
        "scope": item.scope,
        "permissions": sorted(permissions_for_role(db, item)),
        "is_active": item.is_active,
        "sort_order": item.sort_order,
    }


@router.patch("/roles/{role_id}")
def update_role(role_id: uuid.UUID, data: RoleIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    raise HTTPException(410, "מנגנון התפקידים הישן בוטל")
    item = db.get(Role, role_id)
    if not item:
        raise HTTPException(404, "Role not found")
    item.code, item.name, item.name_he, item.description, item.description_he, item.scope, item.sort_order, item.permissions, item.is_active = (
        data.code or item.code,
        data.name,
        data.name_he or data.name,
        data.description,
        data.description_he or data.description,
        data.scope,
        data.sort_order,
        data.permissions,
        data.is_active,
    )
    db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for code in data.permissions:
        db.add(RolePermission(role_id=role_id, permission_code=code))
    audit(db, user, "role", item.id, "updated")
    db.commit()
    return {"id": item.id, **data.model_dump()}


def user_field_dict(item: UserFieldDefinition) -> dict[str, Any]:
    return {
        "id": item.id,
        "key": item.key,
        "label_he": item.label_he,
        "label_en": item.label_en,
        "field_type": item.field_type,
        "is_required": item.is_required,
        "is_active": item.is_active,
        "options_json": item.options_json,
        "default_value_json": item.default_value_json,
        "validation_json": item.validation_json,
        "sort_order": item.sort_order,
        "scope": item.scope,
        "environment_id": item.environment_id,
    }


def validate_environments(db: DB, environment_ids: list[uuid.UUID]) -> list[Environment]:
    unique_ids = list(dict.fromkeys(environment_ids))
    environments = list(db.scalars(select(Environment).where(Environment.id.in_(unique_ids))))
    found = {item.id for item in environments}
    missing = [str(item) for item in unique_ids if item not in found]
    inactive = [item.name_he for item in environments if not item.is_active]
    if missing:
        raise HTTPException(
            422, {"field": "environment_ids", "message": f"הסביבות הבאות אינן קיימות: {', '.join(missing)}"}
        )
    if inactive:
        raise HTTPException(
            422,
            {
                "field": "environment_ids",
                "message": f"לא ניתן לשייך שדה לסביבה לא פעילה: {', '.join(inactive)}",
            },
        )
    return environments


@router.get("/user-fields")
def list_user_fields(db: DB, user: Current) -> list[dict[str, Any]]:
    system_admin(user)
    result = []
    for item in db.scalars(select(UserFieldDefinition).where(
        UserFieldDefinition.scope == "global"
    ).order_by(UserFieldDefinition.sort_order)):
        environment_ids = list(
            db.scalars(
                select(EnvironmentUserField.environment_id).where(
                    EnvironmentUserField.user_field_definition_id == item.id
                )
            )
        )
        result.append({**user_field_dict(item), "environment_ids": environment_ids})
    return result


@router.post("/user-fields", status_code=201)
def create_user_field(data: UserFieldIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    environments = validate_environments(db, data.environment_ids)
    payload = data.model_dump(exclude={"environment_ids"})
    payload["options_json"] = [option.model_dump() for option in data.options_json]
    item = UserFieldDefinition(system_number=NumberingService.next(db, "user_field"),
                               scope="global", environment_id=None, **payload)
    db.add(item)
    db.flush()
    for environment in environments:
        db.add(
            EnvironmentUserField(
                environment_id=environment.id,
                user_field_definition_id=item.id,
                is_visible=True,
                is_required=False,
                is_editable_by_user=False,
                is_editable_by_environment_admin=True,
                sort_order=item.sort_order,
            )
        )
    audit(db, user, "user_field", item.id, "created")
    db.commit()
    return {**user_field_dict(item), "environment_ids": [environment.id for environment in environments]}


@router.patch("/user-fields/{field_id}")
def update_user_field(field_id: uuid.UUID, data: UserFieldIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    item = db.get(UserFieldDefinition, field_id)
    if not item:
        raise HTTPException(404, "User field not found")
    if item.field_type != data.field_type and db.scalar(
        select(UserFieldValue.user_id).where(UserFieldValue.field_id == field_id).limit(1)
    ):
        raise HTTPException(409, "לא ניתן לשנות סוג שדה לאחר שנשמרו בו ערכים")
    environments = validate_environments(db, data.environment_ids)
    payload = data.model_dump(exclude={"environment_ids"})
    payload["options_json"] = [option.model_dump() for option in data.options_json]
    for key, value in payload.items():
        setattr(item, key, value)
    selected_ids = {environment.id for environment in environments}
    existing = {
        row.environment_id: row
        for row in db.scalars(
            select(EnvironmentUserField).where(EnvironmentUserField.user_field_definition_id == field_id)
        )
    }
    for environment_id, row in existing.items():
        if environment_id not in selected_ids:
            db.delete(row)
    for environment in environments:
        if environment.id not in existing:
            db.add(
                EnvironmentUserField(
                    environment_id=environment.id,
                    user_field_definition_id=item.id,
                    is_visible=True,
                    is_required=False,
                    is_editable_by_user=False,
                    is_editable_by_environment_admin=True,
                    sort_order=item.sort_order,
                )
            )
    audit(db, user, "user_field", item.id, "updated")
    db.commit()
    return {**user_field_dict(item), "environment_ids": list(selected_ids)}


@router.get("/users/{user_id}/field-values")
def field_values(user_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    if not user.is_system_admin and user.id != user_id:
        raise HTTPException(403, "Not permitted")
    return {
        str(row.field_id): row.value_json
        for row in db.scalars(select(UserFieldValue).where(UserFieldValue.user_id == user_id))
    }


@router.put("/users/{user_id}/field-values")
def save_field_values(
    user_id: uuid.UUID, values: dict[uuid.UUID, Any], db: DB, user: Current
) -> dict[str, bool]:
    if not user.is_system_admin and user.id != user_id:
        raise HTTPException(403, "Not permitted")
    for field_id, value in values.items():
        db.merge(UserFieldValue(user_id=user_id, field_id=field_id, value_json=value))
    db.commit()
    return {"ok": True}


@router.get("/environments/{environment_id}/user-fields")
def environment_fields(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.fields.manage")
    selected = {
        row.user_field_definition_id: row
        for row in db.scalars(
            select(EnvironmentUserField).where(EnvironmentUserField.environment_id == environment_id)
        )
    }
    result = []
    for field in db.scalars(
        select(UserFieldDefinition)
        .where(UserFieldDefinition.is_active.is_(True), or_(
            UserFieldDefinition.scope == "global",
            UserFieldDefinition.environment_id == environment_id,
        ))
        .order_by(UserFieldDefinition.sort_order)
    ):
        selection = selected.get(field.id)
        result.append(
            {
                "definition": user_field_dict(field),
                "selection": None
                if not selection
                else {
                    "user_field_definition_id": selection.user_field_definition_id,
                    "is_visible": selection.is_visible,
                    "is_required": selection.is_required,
                    "is_editable_by_user": selection.is_editable_by_user,
                    "is_editable_by_environment_admin": selection.is_editable_by_environment_admin,
                    "sort_order": selection.sort_order,
                },
            }
        )
    return result


@router.post("/environments/{environment_id}/user-field-definitions", status_code=201)
def create_environment_user_field(environment_id: uuid.UUID, data: UserFieldIn, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.fields.manage")
    if not db.get(Environment, environment_id):
        raise HTTPException(404, "Environment not found")
    payload = data.model_dump(exclude={"environment_ids"})
    payload["options_json"] = [option.model_dump() for option in data.options_json]
    item = UserFieldDefinition(system_number=NumberingService.next(db, "user_field"),
        scope="environment", environment_id=environment_id, **payload)
    db.add(item); db.flush()
    db.add(EnvironmentUserField(environment_id=environment_id, user_field_definition_id=item.id,
        is_visible=True, is_required=item.is_required, is_editable_by_user=False,
        is_editable_by_environment_admin=True, sort_order=item.sort_order))
    audit(db, user, "user_field", item.id, "created", after={"scope": "environment"})
    db.commit()
    return user_field_dict(item)


@router.put("/environments/{environment_id}/user-fields")
def set_environment_fields(
    environment_id: uuid.UUID, rows: list[EnvironmentFieldIn], db: DB, user: Current
) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.fields.manage")
    db.execute(delete(EnvironmentUserField).where(EnvironmentUserField.environment_id == environment_id))
    for row in rows:
        db.add(EnvironmentUserField(environment_id=environment_id, **row.model_dump()))
    audit(db, user, "environment", environment_id, "user_fields_updated")
    db.commit()
    return environment_fields(environment_id, db, user)


@router.get("/environments/{environment_id}/memberships")
def list_memberships(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.users.manage")
    rows = db.execute(
        select(EnvironmentMembership, User, Group)
        .outerjoin(User, EnvironmentMembership.user_id == User.id)
        .outerjoin(Group, EnvironmentMembership.group_id == Group.id)
        .where(EnvironmentMembership.environment_id == environment_id)
    ).all()
    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "user_name": u.display_name if u else None,
            "group_id": m.group_id,
            "group_name": g.name if g else None,
            "source": m.source,
            "source_rule_id": m.source_rule_id,
            "is_active": m.is_active,
        }
        for m, u, g in rows
    ]


@router.post("/environments/{environment_id}/memberships", status_code=201)
def create_membership(
    environment_id: uuid.UUID, data: MembershipCreate, db: DB, user: Current
) -> dict[str, Any]:
    require(db, user, environment_id, "environment.users.manage")
    if bool(data.user_id) == bool(data.group_id):
        raise HTTPException(422, "Exactly one of user_id or group_id is required")
    item = EnvironmentMembership(environment_id=environment_id, role_id=None, source="manual", **data.model_dump())
    db.add(item)
    db.flush()
    audit(db, user, "environment", environment_id, "membership_created")
    db.commit()
    return {"id": item.id}


@router.patch("/environments/{environment_id}/memberships/{membership_id}")
def update_membership(
    environment_id: uuid.UUID, membership_id: uuid.UUID, data: MembershipPatch, db: DB, user: Current
) -> dict[str, bool]:
    require(db, user, environment_id, "environment.users.manage")
    item = db.get(EnvironmentMembership, membership_id)
    if not item or item.environment_id != environment_id:
        raise HTTPException(404, "Membership not found")
    if data.is_active is not None: item.is_active = data.is_active
    audit(db, user, "environment", environment_id, "membership_updated")
    db.commit()
    return {"ok": True}


@router.delete("/environments/{environment_id}/memberships/{membership_id}", status_code=204)
def remove_membership(environment_id: uuid.UUID, membership_id: uuid.UUID, db: DB, user: Current) -> None:
    require(db, user, environment_id, "environment.users.manage")
    item = db.get(EnvironmentMembership, membership_id)
    if not item or item.environment_id != environment_id:
        raise HTTPException(404, "Membership not found")
    db.delete(item)
    audit(db, user, "environment", environment_id, "membership_removed")
    db.commit()


@router.get("/environments/{environment_id}/priorities")
def list_priorities(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.read")
    result = []
    for row in db.scalars(
        select(PriorityDefinition)
        .where(PriorityDefinition.environment_id == environment_id)
        .order_by(PriorityDefinition.sort_order)
    ):
        children = list(
            db.scalars(
                select(SubPriorityDefinition)
                .where(SubPriorityDefinition.priority_id == row.id)
                .order_by(SubPriorityDefinition.sort_order)
            )
        )
        result.append(
            {
                "id": row.id,
                "system_number": row.system_number,
                "code": row.code,
                "label_he": row.label_he,
                "color": row.color,
                "sort_order": row.sort_order,
                "is_active": row.is_active,
                "sub_priorities": [
                    {
                        "id": child.id,
                        "system_number": child.system_number,
                        "priority_id": child.priority_id,
                        "code": child.code,
                        "label_he": child.label_he,
                        "color": child.color,
                        "sort_order": child.sort_order,
                        "is_active": child.is_active,
                    }
                    for child in children
                ],
            }
        )
    return result


@router.post("/environments/{environment_id}/priorities", status_code=201, response_model=None)
def create_priority(environment_id: uuid.UUID, data: PriorityIn, db: DB, user: Current) -> PriorityDefinition:
    require(db, user, environment_id, "environment.manage")
    item = PriorityDefinition(
        system_number=NumberingService.next(db, "priority", environment_id),
        environment_id=environment_id,
        **data.model_dump(),
    )
    db.add(item)
    db.commit()
    return item


@router.patch("/environments/{environment_id}/priorities/{priority_id}", response_model=None)
def update_priority(
    environment_id: uuid.UUID, priority_id: uuid.UUID, data: PriorityIn, db: DB, user: Current
) -> PriorityDefinition:
    require(db, user, environment_id, "environment.manage")
    item = db.get(PriorityDefinition, priority_id)
    if not item or item.environment_id != environment_id:
        raise HTTPException(404, "Priority not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return item


def _configuration_reference_count(db: DB, value_id: uuid.UUID) -> int:
    needle = str(value_id)
    rules = db.scalars(select(AutomationRule)).all()
    return sum(
        1
        for rule in rules
        if needle in json.dumps(
            {"conditions": rule.conditions_json, "actions": rule.actions_json}, default=str
        )
    )


@router.delete("/priorities/{priority_id}", status_code=204)
def delete_priority(priority_id: uuid.UUID, db: DB, user: Current) -> None:
    item = db.get(PriorityDefinition, priority_id)
    if not item:
        raise HTTPException(404, "העדיפות לא נמצאה")
    require(db, user, item.environment_id, "environment.manage")
    usage = {
        "קריאות שירות": db.scalar(select(func.count(Case.id)).where(Case.priority_id == item.id)) or 0,
        "ברירות מחדל של סוגי קריאה": db.scalar(
            select(func.count(RequestType.id)).where(RequestType.default_priority_id == item.id)
        ) or 0,
        "תתי-עדיפויות": db.scalar(
            select(func.count(SubPriorityDefinition.id)).where(SubPriorityDefinition.priority_id == item.id)
        ) or 0,
        "מדיניות SLA": db.scalar(select(func.count(SlaPolicy.id)).where(SlaPolicy.priority_id == item.id)) or 0,
        "כללי אוטומציה": _configuration_reference_count(db, item.id),
    }
    used = {label: count for label, count in usage.items() if count}
    if used:
        summary = ", ".join(f"{count} {label}" for label, count in used.items())
        raise HTTPException(
            409,
            f'לא ניתן למחוק את הערך "{item.label_he}". הוא נמצא בשימוש ב-{summary}. '
            "ניתן להשבית אותו במקום למחוק.",
        )
    audit(db, user, "priority", item.id, "deleted", before={"label_he": item.label_he})
    db.delete(item)
    db.commit()


@router.post("/priorities/{priority_id}/sub-priorities", status_code=201, response_model=None)
def create_sub_priority(
    priority_id: uuid.UUID, data: SubPriorityIn, db: DB, user: Current
) -> SubPriorityDefinition:
    parent = db.get(PriorityDefinition, priority_id)
    if not parent:
        raise HTTPException(404, "Priority not found")
    require(db, user, parent.environment_id, "environment.manage")
    item = SubPriorityDefinition(
        system_number=NumberingService.next(db, "sub_priority", parent.environment_id),
        environment_id=parent.environment_id,
        priority_id=priority_id,
        **data.model_dump(),
    )
    db.add(item)
    db.commit()
    return item


@router.patch("/sub-priorities/{sub_priority_id}", response_model=None)
def update_sub_priority(sub_priority_id: uuid.UUID, data: SubPriorityIn, db: DB, user: Current) -> SubPriorityDefinition:
    item = db.get(SubPriorityDefinition, sub_priority_id)
    if not item:
        raise HTTPException(404, "Sub-priority not found")
    environment_id = item.environment_id
    if not environment_id and item.priority_id:
        parent = db.get(PriorityDefinition, item.priority_id)
        environment_id = parent.environment_id if parent else None
    if not environment_id:
        raise HTTPException(409, "Sub-priority environment is unavailable")
    require(db, user, environment_id, "environment.manage")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, "sub_priority", item.id, "updated")
    db.commit()
    return item


@router.delete("/sub-priorities/{sub_priority_id}", status_code=204)
def delete_sub_priority(sub_priority_id: uuid.UUID, db: DB, user: Current) -> None:
    item = db.get(SubPriorityDefinition, sub_priority_id)
    if not item or not item.environment_id:
        raise HTTPException(404, "תת-העדיפות לא נמצאה")
    require(db, user, item.environment_id, "environment.manage")
    usage = {
        "קריאות שירות": db.scalar(select(func.count(Case.id)).where(Case.sub_priority_id == item.id)) or 0,
        "ברירות מחדל של סוגי קריאה": db.scalar(
            select(func.count(RequestType.id)).where(RequestType.default_sub_priority_id == item.id)
        ) or 0,
        "כללי אוטומציה": _configuration_reference_count(db, item.id),
    }
    used = {label: count for label, count in usage.items() if count}
    if used:
        summary = ", ".join(f"{count} {label}" for label, count in used.items())
        raise HTTPException(
            409,
            f'לא ניתן למחוק את הערך "{item.label_he}". הוא נמצא בשימוש ב-{summary}. '
            "ניתן להשבית אותו במקום למחוק.",
        )
    audit(db, user, "sub_priority", item.id, "deleted", before={"label_he": item.label_he})
    db.delete(item)
    db.commit()


@router.get("/environments/{environment_id}/sub-priorities")
def list_environment_sub_priorities(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.read")
    rows = db.scalars(select(SubPriorityDefinition).where(
        SubPriorityDefinition.environment_id == environment_id).order_by(SubPriorityDefinition.sort_order))
    return [{column.name: getattr(row, column.name) for column in row.__table__.columns} for row in rows]


@router.post("/environments/{environment_id}/sub-priorities", status_code=201)
def create_environment_sub_priority(environment_id: uuid.UUID, data: SubPriorityIn,
                                    db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.manage")
    item = SubPriorityDefinition(system_number=NumberingService.next(db, "sub_priority", environment_id),
                                 environment_id=environment_id, priority_id=None, **data.model_dump())
    db.add(item); db.flush()
    audit(db, user, "sub_priority", item.id, "created")
    db.commit()
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


def automation_dict(item: AutomationRule) -> dict[str, Any]:
    return {
        "id": item.id,
        "system_number": item.system_number,
        "environment_id": item.environment_id,
        "name": item.name,
        "description": item.description,
        "is_active": item.is_active,
        "trigger_type": item.trigger_type,
        "conditions_json": item.conditions_json,
        "actions_json": item.actions_json,
        "priority": item.priority,
    }


@router.get("/automation-rules")
def list_automation_rules(
    db: DB, user: Current, environment_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    if environment_id:
        require(db, user, environment_id, "environment.rules.manage")
    else:
        system_admin(user)
    query = select(AutomationRule).where(AutomationRule.environment_id == environment_id)
    return [automation_dict(item) for item in db.scalars(query.order_by(AutomationRule.priority))]


@router.post("/automation-rules", status_code=201)
def create_automation_rule(data: AutomationRuleIn, db: DB, user: Current) -> dict[str, Any]:
    if data.environment_id:
        require(db, user, data.environment_id, "environment.rules.manage")
    else:
        system_admin(user)
    item = AutomationRule(
        system_number=NumberingService.next(db, "automation_rule", data.environment_id),
        **data.model_dump(),
        created_by=user.id,
    )
    db.add(item)
    db.flush()
    audit(db, user, "automation_rule", item.id, "created")
    db.commit()
    return automation_dict(item)


@router.patch("/automation-rules/{rule_id}")
def update_automation_rule(
    rule_id: uuid.UUID, data: AutomationRuleIn, db: DB, user: Current
) -> dict[str, Any]:
    item = db.get(AutomationRule, rule_id)
    if not item:
        raise HTTPException(404, "Automation rule not found")
    if item.environment_id:
        require(db, user, item.environment_id, "environment.rules.manage")
    else:
        system_admin(user)
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, "automation_rule", item.id, "updated")
    db.commit()
    return automation_dict(item)


def comment_dict(db: DB, item: Comment) -> dict[str, Any]:
    author = db.get(User, item.author_id)
    return {
        "id": item.id,
        "author_id": item.author_id,
        "author_name": author.display_name if author else "משתמש",
        "body": item.body,
        "visibility": item.visibility,
        "created_at": item.created_at,
    }


@router.get("/cases/{case_id}/public-comments")
def public_comments(case_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    return [
        comment_dict(db, row)
        for row in db.scalars(
            select(Comment)
            .where(Comment.case_id == case_id, Comment.visibility == Visibility.public)
            .order_by(Comment.created_at)
        )
    ]


@router.post("/cases/{case_id}/public-comments", status_code=201)
def create_public_comment(case_id: uuid.UUID, data: CommentIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    row = Comment(case_id=case_id, author_id=user.id, body=data.body, visibility=Visibility.public)
    db.add(row)
    db.flush()
    audit(db, user, "case", case_id, "public_comment_created")
    db.commit()
    return comment_dict(db, row)


@router.get("/cases/{case_id}/manager-comments")
def manager_comments(case_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    require(db, user, item.environment_id, "comment.manager.read")
    return [
        comment_dict(db, row)
        for row in db.scalars(
            select(Comment)
            .where(Comment.case_id == case_id, Comment.visibility == Visibility.internal)
            .order_by(Comment.created_at)
        )
    ]


@router.post("/cases/{case_id}/manager-comments", status_code=201)
def create_manager_comment(case_id: uuid.UUID, data: CommentIn, db: DB, user: Current) -> dict[str, Any]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    require(db, user, item.environment_id, "comment.manager.create")
    row = Comment(case_id=case_id, author_id=user.id, body=data.body, visibility=Visibility.internal)
    db.add(row)
    db.flush()
    audit(db, user, "case", case_id, "manager_comment_created")
    db.commit()
    return comment_dict(db, row)
