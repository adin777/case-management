import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, or_, select

from app.modules.api import DB, Current, audit, case_access, password_hash, require
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
    Role,
    RolePermission,
    SubPriorityDefinition,
    User,
    UserFieldDefinition,
    UserFieldValue,
    Visibility,
)

router = APIRouter(prefix="/api", tags=["governance"])


class UserCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    is_active: bool = True
    is_system_admin: bool = False


class UserPatch(BaseModel):
    display_name: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    is_system_admin: bool | None = None
    environment_id: uuid.UUID | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=200)


class GroupIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    is_active: bool = True


class GroupMemberIn(BaseModel):
    user_id: uuid.UUID


class GroupRoleIn(BaseModel):
    environment_id: uuid.UUID
    role_id: uuid.UUID


class RoleIn(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    name: str
    description: str | None = None
    scope: str = Field(pattern="^(system|environment)$")
    permissions: list[str] = Field(default_factory=list)


class UserFieldIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label_he: str
    label_en: str
    field_type: str = Field(
        pattern="^(short_text|long_text|number|date|boolean|single_select|multi_select|user|email|phone)$"
    )
    is_required: bool = False
    is_active: bool = True
    options_json: list | dict = Field(default_factory=list)
    default_value_json: Any = None
    validation_json: dict = Field(default_factory=dict)
    sort_order: int = 0


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
    role_id: uuid.UUID


class MembershipPatch(BaseModel):
    role_id: uuid.UUID


class PriorityIn(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    label_he: str
    color: str = "#64748b"
    sort_order: int = 0
    is_active: bool = True


class SubPriorityIn(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    label_he: str
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
    trigger_type: str = Field(pattern="^(case_created|case_status_changed|case_priority_changed|participant_added)$")
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
        select(Environment.id, Environment.name_he, Role.id, Role.name)
        .join(EnvironmentMembership, EnvironmentMembership.environment_id == Environment.id)
        .join(Role, EnvironmentMembership.role_id == Role.id)
        .where(EnvironmentMembership.user_id == item.id)
    ).all()
    return {
        "id": item.id,
        "email": item.email,
        "display_name": item.display_name,
        "is_active": item.is_active,
        "is_system_admin": item.is_system_admin,
        "created_at": item.created_at,
        "last_login_at": item.last_login_at,
        "groups": [{"id": row[0], "name": row[1]} for row in groups],
        "memberships": [
            {"environment_id": row[0], "environment_name": row[1], "role_id": row[2], "role_name": row[3]}
            for row in memberships
        ],
    }


@router.get("/users")
def list_users(
    db: DB,
    user: Current,
    search: str = "",
    environment_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    query = select(User).order_by(User.display_name)
    if search:
        query = query.where(
            or_(User.display_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )
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
    item = User(
        display_name=data.display_name,
        email=data.email.lower(),
        password_hash=password_hash.hash(data.password),
        is_active=data.is_active,
        is_system_admin=data.is_system_admin,
    )
    db.add(item)
    db.flush()
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
    audit(db, user, "user", item.id, "updated")
    db.commit()
    return user_dict(db, item)


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
    item = Group(**data.model_dump())
    db.add(item)
    db.flush()
    audit(db, user, "group", item.id, "created")
    db.commit()
    return {"id": item.id, **data.model_dump(), "member_count": 0}


@router.get("/groups/{group_id}")
def get_group(group_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    item = db.get(Group, group_id)
    if not item:
        raise HTTPException(404, "Group not found")
    members = db.execute(
        select(User.id, User.display_name, User.email).join(GroupMember).where(GroupMember.group_id == group_id)
    ).all()
    return {"id": item.id, "name": item.name, "description": item.description, "is_active": item.is_active,
            "members": [{"id": r[0], "display_name": r[1], "email": r[2]} for r in members]}


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
    return [{"id": r.id, "code": r.code, "name": r.name, "description": r.description,
             "scope": r.scope, "permissions": sorted(permissions_for_role(db, r))}
            for r in db.scalars(select(Role).order_by(Role.name))]


def permissions_for_role(db: DB, role: Role) -> set[str]:
    normalized = set(db.scalars(select(RolePermission.permission_code).where(RolePermission.role_id == role.id)))
    return normalized | set(role.permissions or [])


@router.post("/roles", status_code=201)
def create_role(data: RoleIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    unknown = set(data.permissions) - set(db.scalars(select(Permission.code)))
    if unknown:
        raise HTTPException(422, f"Unknown permissions: {', '.join(sorted(unknown))}")
    item = Role(code=data.code, name=data.name, description=data.description, scope=data.scope,
                permissions=data.permissions)
    db.add(item)
    db.flush()
    for code in data.permissions:
        db.add(RolePermission(role_id=item.id, permission_code=code))
    audit(db, user, "role", item.id, "created")
    db.commit()
    return {"id": item.id, **data.model_dump()}


@router.get("/roles/{role_id}")
def get_role(role_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    item = db.get(Role, role_id)
    if not item:
        raise HTTPException(404, "Role not found")
    return {"id": item.id, "code": item.code, "name": item.name, "description": item.description,
            "scope": item.scope, "permissions": sorted(permissions_for_role(db, item))}


@router.patch("/roles/{role_id}")
def update_role(role_id: uuid.UUID, data: RoleIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    item = db.get(Role, role_id)
    if not item:
        raise HTTPException(404, "Role not found")
    item.code, item.name, item.description, item.scope, item.permissions = (
        data.code, data.name, data.description, data.scope, data.permissions
    )
    db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for code in data.permissions:
        db.add(RolePermission(role_id=role_id, permission_code=code))
    audit(db, user, "role", item.id, "updated")
    db.commit()
    return {"id": item.id, **data.model_dump()}


def user_field_dict(item: UserFieldDefinition) -> dict[str, Any]:
    return {"id": item.id, "key": item.key, "label_he": item.label_he, "label_en": item.label_en,
            "field_type": item.field_type, "is_required": item.is_required, "is_active": item.is_active,
            "options_json": item.options_json, "default_value_json": item.default_value_json,
            "validation_json": item.validation_json, "sort_order": item.sort_order}


@router.get("/user-fields")
def list_user_fields(db: DB, user: Current) -> list[dict[str, Any]]:
    system_admin(user)
    return [user_field_dict(item) for item in db.scalars(
        select(UserFieldDefinition).order_by(UserFieldDefinition.sort_order))]


@router.post("/user-fields", status_code=201)
def create_user_field(data: UserFieldIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    item = UserFieldDefinition(**data.model_dump())
    db.add(item)
    db.flush()
    audit(db, user, "user_field", item.id, "created")
    db.commit()
    return user_field_dict(item)


@router.patch("/user-fields/{field_id}")
def update_user_field(field_id: uuid.UUID, data: UserFieldIn, db: DB, user: Current) -> dict[str, Any]:
    system_admin(user)
    item = db.get(UserFieldDefinition, field_id)
    if not item:
        raise HTTPException(404, "User field not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    audit(db, user, "user_field", item.id, "updated")
    db.commit()
    return user_field_dict(item)


@router.get("/users/{user_id}/field-values")
def field_values(user_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    if not user.is_system_admin and user.id != user_id:
        raise HTTPException(403, "Not permitted")
    return {str(row.field_id): row.value_json for row in db.scalars(
        select(UserFieldValue).where(UserFieldValue.user_id == user_id)
    )}


@router.put("/users/{user_id}/field-values")
def save_field_values(user_id: uuid.UUID, values: dict[uuid.UUID, Any], db: DB, user: Current) -> dict[str, bool]:
    if not user.is_system_admin and user.id != user_id:
        raise HTTPException(403, "Not permitted")
    for field_id, value in values.items():
        db.merge(UserFieldValue(user_id=user_id, field_id=field_id, value_json=value))
    db.commit()
    return {"ok": True}


@router.get("/environments/{environment_id}/user-fields")
def environment_fields(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "environment.fields.manage")
    selected = {row.user_field_definition_id: row for row in db.scalars(
        select(EnvironmentUserField).where(EnvironmentUserField.environment_id == environment_id)
    )}
    result = []
    for field in db.scalars(select(UserFieldDefinition).where(
        UserFieldDefinition.is_active.is_(True)).order_by(UserFieldDefinition.sort_order)):
        selection = selected.get(field.id)
        result.append({"definition": user_field_dict(field), "selection": None if not selection else {
            "user_field_definition_id": selection.user_field_definition_id,
            "is_visible": selection.is_visible, "is_required": selection.is_required,
            "is_editable_by_user": selection.is_editable_by_user,
            "is_editable_by_environment_admin": selection.is_editable_by_environment_admin,
            "sort_order": selection.sort_order,
        }})
    return result


@router.put("/environments/{environment_id}/user-fields")
def set_environment_fields(environment_id: uuid.UUID, rows: list[EnvironmentFieldIn], db: DB,
                           user: Current) -> list[dict[str, Any]]:
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
    rows = db.execute(select(EnvironmentMembership, User, Group, Role)
        .outerjoin(User, EnvironmentMembership.user_id == User.id)
        .outerjoin(Group, EnvironmentMembership.group_id == Group.id)
        .join(Role, EnvironmentMembership.role_id == Role.id)
        .where(EnvironmentMembership.environment_id == environment_id)).all()
    return [{"id": m.id, "user_id": m.user_id, "user_name": u.display_name if u else None,
             "group_id": m.group_id, "group_name": g.name if g else None,
             "role_id": m.role_id, "role_name": r.name} for m, u, g, r in rows]


@router.post("/environments/{environment_id}/memberships", status_code=201)
def create_membership(environment_id: uuid.UUID, data: MembershipCreate, db: DB,
                      user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.users.manage")
    if bool(data.user_id) == bool(data.group_id):
        raise HTTPException(422, "Exactly one of user_id or group_id is required")
    item = EnvironmentMembership(environment_id=environment_id, **data.model_dump())
    db.add(item)
    db.flush()
    audit(db, user, "environment", environment_id, "membership_created")
    db.commit()
    return {"id": item.id}


@router.patch("/environments/{environment_id}/memberships/{membership_id}")
def update_membership(environment_id: uuid.UUID, membership_id: uuid.UUID, data: MembershipPatch,
                      db: DB, user: Current) -> dict[str, bool]:
    require(db, user, environment_id, "environment.users.manage")
    item = db.get(EnvironmentMembership, membership_id)
    if not item or item.environment_id != environment_id:
        raise HTTPException(404, "Membership not found")
    item.role_id = data.role_id
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
    for row in db.scalars(select(PriorityDefinition).where(
        PriorityDefinition.environment_id == environment_id).order_by(PriorityDefinition.sort_order)):
        children = list(db.scalars(select(SubPriorityDefinition).where(
            SubPriorityDefinition.priority_id == row.id).order_by(SubPriorityDefinition.sort_order)))
        result.append({"id": row.id, "code": row.code, "label_he": row.label_he, "color": row.color,
                       "sort_order": row.sort_order, "is_active": row.is_active,
                       "sub_priorities": [{"id": child.id, "priority_id": child.priority_id,
                           "code": child.code, "label_he": child.label_he, "color": child.color,
                           "sort_order": child.sort_order, "is_active": child.is_active}
                           for child in children]})
    return result


@router.post("/environments/{environment_id}/priorities", status_code=201, response_model=None)
def create_priority(environment_id: uuid.UUID, data: PriorityIn, db: DB,
                    user: Current) -> PriorityDefinition:
    require(db, user, environment_id, "environment.manage")
    item = PriorityDefinition(environment_id=environment_id, **data.model_dump())
    db.add(item)
    db.commit()
    return item


@router.patch("/environments/{environment_id}/priorities/{priority_id}", response_model=None)
def update_priority(environment_id: uuid.UUID, priority_id: uuid.UUID, data: PriorityIn,
                    db: DB, user: Current) -> PriorityDefinition:
    require(db, user, environment_id, "environment.manage")
    item = db.get(PriorityDefinition, priority_id)
    if not item or item.environment_id != environment_id:
        raise HTTPException(404, "Priority not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return item


@router.post("/priorities/{priority_id}/sub-priorities", status_code=201, response_model=None)
def create_sub_priority(priority_id: uuid.UUID, data: SubPriorityIn, db: DB,
                        user: Current) -> SubPriorityDefinition:
    parent = db.get(PriorityDefinition, priority_id)
    if not parent:
        raise HTTPException(404, "Priority not found")
    require(db, user, parent.environment_id, "environment.manage")
    item = SubPriorityDefinition(priority_id=priority_id, **data.model_dump())
    db.add(item)
    db.commit()
    return item


def automation_dict(item: AutomationRule) -> dict[str, Any]:
    return {"id": item.id, "environment_id": item.environment_id, "name": item.name,
            "description": item.description, "is_active": item.is_active,
            "trigger_type": item.trigger_type, "conditions_json": item.conditions_json,
            "actions_json": item.actions_json, "priority": item.priority}


@router.get("/automation-rules")
def list_automation_rules(db: DB, user: Current,
                          environment_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
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
    item = AutomationRule(**data.model_dump(), created_by=user.id)
    db.add(item)
    db.flush()
    audit(db, user, "automation_rule", item.id, "created")
    db.commit()
    return automation_dict(item)


@router.patch("/automation-rules/{rule_id}")
def update_automation_rule(rule_id: uuid.UUID, data: AutomationRuleIn, db: DB,
                           user: Current) -> dict[str, Any]:
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
    return {"id": item.id, "author_id": item.author_id,
            "author_name": author.display_name if author else "משתמש", "body": item.body,
            "visibility": item.visibility, "created_at": item.created_at}


@router.get("/cases/{case_id}/public-comments")
def public_comments(case_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    return [comment_dict(db, row) for row in db.scalars(select(Comment).where(
        Comment.case_id == case_id, Comment.visibility == Visibility.public).order_by(Comment.created_at))]


@router.post("/cases/{case_id}/public-comments", status_code=201)
def create_public_comment(case_id: uuid.UUID, data: CommentIn, db: DB,
                          user: Current) -> dict[str, Any]:
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
    return [comment_dict(db, row) for row in db.scalars(select(Comment).where(
        Comment.case_id == case_id, Comment.visibility == Visibility.internal).order_by(Comment.created_at))]


@router.post("/cases/{case_id}/manager-comments", status_code=201)
def create_manager_comment(case_id: uuid.UUID, data: CommentIn, db: DB,
                           user: Current) -> dict[str, Any]:
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
