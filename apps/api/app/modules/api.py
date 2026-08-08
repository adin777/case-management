import logging
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.modules.access.service import domain_permissions
from app.modules.approvals.service import start_matching_approvals
from app.modules.automation.service import AutomationEngine
from app.modules.models import (
    AuditEvent,
    Case,
    CaseFieldValue,
    CaseParticipant,
    CaseStatus,
    Comment,
    Environment,
    EnvironmentMembership,
    FieldDefinition,
    FormDefinition,
    FormStatus,
    GroupEnvironmentRole,
    GroupMember,
    GroupPermissionAssignment,
    PriorityDefinition,
    RefreshToken,
    RequestType,
    Role,
    RolePermission,
    SubPriorityDefinition,
    User,
    UserPermissionAssignment,
    Visibility,
)
from app.modules.numbering.service import NumberingService
from app.modules.operations.models import CaseStatusHistory, WorkflowStatus, WorkflowTransition
from app.modules.operations.service import initialize_operations, resolve_workflow

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
oauth = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
password_hash = PasswordHash.recommended()
DB = Annotated[Session, Depends(get_db)]
ALL_PERMISSIONS = [
    "system.users.read", "system.users.create", "system.users.update", "system.users.disable",
    "system.users.reset_password", "system.groups.read", "system.groups.manage", "system.roles.read",
    "system.roles.manage", "system.fields.read", "system.fields.manage", "system.environments.create",
    "system.environments.manage",
    "environment.read",
    "environment.manage",
    "environment.users.manage", "environment.groups.manage", "environment.fields.manage",
    "environment.request_types.manage", "environment.forms.manage", "environment.rules.manage",
    "environment.audit.read",
    "request_type.read",
    "request_type.manage",
    "case.create",
    "case.read", "case.read_own", "case.read_participating", "case.read_environment",
    "case.update", "case.lock",
    "case.assign",
    "case.change_status",
    "case.comment",
    "case.internal_comment",
    "case.manage_participants",
    "comment.public.read", "comment.public.create", "comment.manager.read", "comment.manager.create",
    "workflow.read", "workflow.manage", "sla.read", "sla.manage",
    "attachment.read", "attachment.upload", "attachment.delete",
    "notification.read_own", "notification.manage",
    "audit.read_system", "audit.read_environment", "case.read_status_history",
]


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_system_admin: bool
    model_config = {"from_attributes": True}


class EnvironmentIn(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9_-]+$")
    name_he: str
    name_en: str
    description: str | None = None


class EnvironmentOut(EnvironmentIn):
    id: uuid.UUID
    is_active: bool
    model_config = {"from_attributes": True}


class MembershipIn(BaseModel):
    user_id: uuid.UUID
    role_code: str


class RequestTypeIn(BaseModel):
    environment_id: uuid.UUID
    code: str
    name_he: str
    name_en: str
    description: str | None = None
    sort_order: int = 0
    requires_approval: bool = False
    workflow_definition_id: uuid.UUID | None = None
    default_priority_id: uuid.UUID | None = None
    default_sub_priority_id: uuid.UUID | None = None
    default_assignee_user_id: uuid.UUID | None = None
    default_assignee_group_id: uuid.UUID | None = None


class RequestTypeOut(RequestTypeIn):
    id: uuid.UUID
    system_number: str | None
    is_active: bool
    form_version_id: uuid.UUID | None
    model_config = {"from_attributes": True}


class FieldIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label_he: str
    label_en: str
    field_type: str
    is_required: bool = False
    is_read_only: bool = False
    sort_order: int = 0
    configuration_json: dict[str, Any] = Field(default_factory=dict)


class FieldOut(FieldIn):
    id: uuid.UUID
    model_config = {"from_attributes": True}


class FormIn(BaseModel):
    request_type_id: uuid.UUID
    fields: list[FieldIn] = Field(default_factory=list)


class FormOut(BaseModel):
    id: uuid.UUID
    request_type_id: uuid.UUID
    version: int
    status: FormStatus
    fields: list[FieldOut]
    model_config = {"from_attributes": True}


class ValueIn(BaseModel):
    field_definition_id: uuid.UUID
    value: Any = None


class CaseIn(BaseModel):
    environment_id: uuid.UUID
    request_type_id: uuid.UUID
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=1)
    workflow_status_id: uuid.UUID | None = None
    priority_id: uuid.UUID | None = None
    sub_priority_id: uuid.UUID | None = None
    participant_ids: list[uuid.UUID] = Field(default_factory=list)
    values: list[ValueIn] = Field(default_factory=list)


class CommentOut(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    body: str
    visibility: Visibility
    created_at: datetime
    model_config = {"from_attributes": True}


class CaseValueOut(BaseModel):
    field_definition_id: uuid.UUID
    value_text: str | None
    value_number: Decimal | None
    value_boolean: bool | None
    value_date: date | None
    value_datetime: datetime | None
    value_user_id: uuid.UUID | None
    value_json: dict | list | None

    model_config = {"from_attributes": True}


class CaseOut(BaseModel):
    id: uuid.UUID
    case_number: str
    environment_id: uuid.UUID
    request_type_id: uuid.UUID
    form_definition_id: uuid.UUID
    title: str
    description: str | None
    status: CaseStatus
    priority: str
    priority_id: uuid.UUID | None
    sub_priority_id: uuid.UUID | None
    reporter_id: uuid.UUID
    requester_id: uuid.UUID
    assignee_id: uuid.UUID | None
    created_at: datetime
    version: int
    is_locked: bool
    locked_at: datetime | None
    locked_by: uuid.UUID | None
    lock_reason: str | None
    workflow_status_id: uuid.UUID | None
    sla_policy_id: uuid.UUID | None
    response_due_at: datetime | None
    resolution_due_at: datetime | None
    first_response_at: datetime | None
    resolved_at: datetime | None
    sla_response_status: str
    sla_resolution_status: str
    approval_status: str
    is_approved: bool
    approved_at: datetime | None
    approved_by_summary: str | None
    comments: list[CommentOut] = Field(default_factory=list)
    values: list[CaseValueOut] = Field(default_factory=list)
    permissions: dict[str, bool] = Field(default_factory=dict)
    model_config = {"from_attributes": True}


class EnvironmentPatch(BaseModel):
    name_he: str | None = None
    name_en: str | None = None
    description: str | None = None
    is_active: bool | None = None


class RequestTypePatch(BaseModel):
    name_he: str | None = None
    name_en: str | None = None
    description: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    requires_approval: bool | None = None
    workflow_definition_id: uuid.UUID | None = None
    default_priority_id: uuid.UUID | None = None
    default_sub_priority_id: uuid.UUID | None = None
    default_assignee_user_id: uuid.UUID | None = None
    default_assignee_group_id: uuid.UUID | None = None


class FormPatch(BaseModel):
    fields: list[FieldIn]


class CasePatch(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    priority_id: uuid.UUID | None = None
    sub_priority_id: uuid.UUID | None = None
    values: list[ValueIn] | None = None
    version: int


class CaseLockIn(BaseModel):
    locked: bool
    reason: str | None = Field(default=None, max_length=1000)
    version: int


class AssignIn(BaseModel):
    assignee_id: uuid.UUID | None
    version: int


class CommentIn(BaseModel):
    body: str = Field(min_length=1)
    visibility: Visibility = Visibility.public


class ParticipantIn(BaseModel):
    user_id: uuid.UUID
    participant_type: str = Field(default="participant", pattern="^(participant|watcher|collaborator)$")


class TransitionIn(BaseModel):
    workflow_status_id: uuid.UUID
    comment: str | None = None


def issue(user: User, token_type: str, expires: timedelta, token_id: uuid.UUID | None = None) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user.id), "type": token_type, "iat": now, "exp": now + expires}
    if token_id:
        payload["jti"] = str(token_id)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode(token: str, expected: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "Invalid or expired token") from exc
    if payload.get("type") != expected:
        raise HTTPException(401, "Invalid token type")
    return payload


def current_user(db: DB, token: Annotated[str, Depends(oauth)]) -> User:
    user = db.get(User, uuid.UUID(decode(token, "access")["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "Inactive or unknown user")
    return user


Current = Annotated[User, Depends(current_user)]


def permissions(db: Session, user: User, environment_id: uuid.UUID) -> set[str]:
    if user.is_system_admin:
        return set(ALL_PERMISSIONS)
    role_ids = set(db.scalars(select(EnvironmentMembership.role_id).where(
        EnvironmentMembership.environment_id == environment_id,
        EnvironmentMembership.user_id == user.id,
    )))
    group_ids = select(GroupMember.group_id).where(GroupMember.user_id == user.id)
    role_ids.update(db.scalars(select(GroupEnvironmentRole.role_id).where(
        GroupEnvironmentRole.environment_id == environment_id,
        GroupEnvironmentRole.group_id.in_(group_ids),
    )))
    result: set[str] = set()
    for role in db.scalars(select(Role).where(Role.id.in_(role_ids))):
        result.update(role.permissions or [])
    result.update(db.scalars(select(RolePermission.permission_code).where(
        RolePermission.role_id.in_(role_ids)
    )))
    direct = list(db.scalars(select(UserPermissionAssignment).where(
        UserPermissionAssignment.user_id == user.id,
        or_(UserPermissionAssignment.environment_id == environment_id,
            UserPermissionAssignment.environment_id.is_(None)),
    )))
    group_direct = list(db.scalars(select(GroupPermissionAssignment).where(
        GroupPermissionAssignment.group_id.in_(group_ids),
        or_(GroupPermissionAssignment.environment_id == environment_id,
            GroupPermissionAssignment.environment_id.is_(None)),
    )))
    result.update(row.permission_code for row in direct + group_direct if row.is_allowed)
    result.update(domain_permissions(db, user.id, environment_id))
    result.difference_update(row.permission_code for row in direct + group_direct if not row.is_allowed)
    return result


def require(db: Session, user: User, env: uuid.UUID, permission: str) -> None:
    if permission not in permissions(db, user, env):
        raise HTTPException(403, f"Missing permission: {permission}")


def audit(
    db: Session,
    user: User,
    entity: str,
    entity_id: uuid.UUID,
    action: str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            entity_type=entity,
            entity_id=str(entity_id),
            action=action,
            actor_id=user.id,
            actor_name_snapshot=user.display_name,
            actor_email_snapshot=user.email,
            before_json=before,
            after_json=after,
            metadata_json={},
        )
    )


def case_access(db: Session, user: User, item: Case) -> None:
    if (
        "case.read" in permissions(db, user, item.environment_id)
        or item.requester_id == user.id
        or item.reporter_id == user.id
    ):
        return
    participant = db.scalar(select(CaseParticipant).where(
        CaseParticipant.case_id == item.id, CaseParticipant.user_id == user.id
    ))
    if participant:
        return
    raise HTTPException(403, "Case is not visible to this user")


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: DB) -> TokenOut:
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    if not user or not password_hash.verify(data.password, user.password_hash) or not user.is_active:
        raise HTTPException(401, "Invalid credentials")
    user.last_login_at = datetime.now(UTC)
    token_id = uuid.uuid4()
    db.add(
        RefreshToken(
            id=token_id,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    return TokenOut(
        access_token=issue(user, "access", timedelta(minutes=settings.access_token_minutes)),
        refresh_token=issue(user, "refresh", timedelta(days=settings.refresh_token_days), token_id),
    )


@router.post("/auth/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, db: DB) -> TokenOut:
    # TODO: Production registration will use email verification and a one-time password setup link.
    if not re.search(r"[A-Za-z]", data.password) or not re.search(r"\d", data.password):
        raise HTTPException(422, "Password must contain at least one letter and one number")
    if db.scalar(select(User.id).where(func.lower(User.email) == data.email.lower())):
        raise HTTPException(409, "Unable to register with this email address")
    user = User(
        email=data.email.lower(),
        display_name=data.display_name,
        password_hash=password_hash.hash(data.password),
        is_active=True,
        is_system_admin=False,
    )
    db.add(user)
    db.flush()
    active_environments = list(db.scalars(select(Environment).where(Environment.is_active.is_(True))))
    if len(active_environments) == 1:
        requester_role = db.scalar(select(Role).where(Role.code == "requester"))
        if requester_role:
            db.add(
                EnvironmentMembership(
                    environment_id=active_environments[0].id,
                    user_id=user.id,
                    role_id=requester_role.id,
                )
            )
    else:
        logger.warning(
            "New user %s was not assigned automatically: active environment count is %s",
            user.id,
            len(active_environments),
        )
    audit(db, user, "user", user.id, "registered", after={"auto_membership": len(active_environments) == 1})
    refresh_id = uuid.uuid4()
    db.add(
        RefreshToken(
            id=refresh_id,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    return TokenOut(
        access_token=issue(user, "access", timedelta(minutes=settings.access_token_minutes)),
        refresh_token=issue(user, "refresh", timedelta(days=settings.refresh_token_days), refresh_id),
    )


@router.post("/auth/refresh", response_model=TokenOut)
def refresh(data: RefreshIn, db: DB) -> TokenOut:
    payload = decode(data.refresh_token, "refresh")
    old = db.get(RefreshToken, uuid.UUID(payload["jti"]))
    now = datetime.now(UTC)
    if not old or old.revoked_at or old.expires_at.replace(tzinfo=UTC) <= now:
        raise HTTPException(401, "Refresh token revoked")
    old.revoked_at = now
    user = db.get(User, old.user_id)
    if not user:
        raise HTTPException(401, "Refresh-token user no longer exists")
    new_id = uuid.uuid4()
    db.add(
        RefreshToken(id=new_id, user_id=user.id, expires_at=now + timedelta(days=settings.refresh_token_days))
    )
    db.commit()
    return TokenOut(
        access_token=issue(user, "access", timedelta(minutes=settings.access_token_minutes)),
        refresh_token=issue(user, "refresh", timedelta(days=settings.refresh_token_days), new_id),
    )


@router.post("/auth/logout", status_code=204)
def logout(data: RefreshIn, db: DB) -> None:
    row = db.get(RefreshToken, uuid.UUID(decode(data.refresh_token, "refresh")["jti"]))
    if row:
        row.revoked_at = datetime.now(UTC)
        db.commit()


@router.get("/auth/me", response_model=UserOut)
def me(user: Current) -> User:
    return user


@router.get("/users", response_model=list[UserOut])
def users(db: DB, user: Current) -> list[User]:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")
    return list(db.scalars(select(User).order_by(User.display_name)))


@router.get("/roles")
def roles(db: DB, user: Current) -> list[dict]:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")
    return [
        {"id": str(r.id), "code": r.code, "name": r.name, "permissions": r.permissions}
        for r in db.scalars(select(Role))
    ]


@router.get("/groups")
def groups(user: Current) -> list[dict]:
    return []


@router.get("/environments", response_model=list[EnvironmentOut])
def environments(db: DB, user: Current) -> list[Environment]:
    query = select(Environment).order_by(Environment.name_he)
    if not user.is_system_admin:
        query = query.join(EnvironmentMembership).where(EnvironmentMembership.user_id == user.id)
    return list(db.scalars(query).unique())


@router.post("/environments", response_model=EnvironmentOut, status_code=201)
def create_environment(data: EnvironmentIn, db: DB, user: Current) -> Environment:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")
    item = Environment(**data.model_dump())
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Environment code already exists") from exc
    audit(db, user, "environment", item.id, "created", after=data.model_dump())
    db.commit()
    db.refresh(item)
    return item


@router.get("/environments/{environment_id}", response_model=EnvironmentOut)
def get_environment(environment_id: uuid.UUID, db: DB, user: Current) -> Environment:
    require(db, user, environment_id, "environment.read")
    item = db.get(Environment, environment_id)
    if not item:
        raise HTTPException(404, "Environment not found")
    return item


@router.patch("/environments/{environment_id}", response_model=EnvironmentOut)
def update_environment(
    environment_id: uuid.UUID, data: EnvironmentPatch, db: DB, user: Current
) -> Environment:
    require(db, user, environment_id, "environment.manage")
    item = db.get(Environment, environment_id)
    if not item:
        raise HTTPException(404, "Environment not found")
    before = {"name_he": item.name_he, "name_en": item.name_en, "is_active": item.is_active}
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    audit(db, user, "environment", item.id, "updated", before, data.model_dump(exclude_unset=True))
    db.commit()
    return item


@router.get("/environments/{environment_id}/memberships")
def memberships(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict]:
    require(db, user, environment_id, "environment.manage")
    rows = db.execute(
        select(EnvironmentMembership, User, Role)
        .join(User, EnvironmentMembership.user_id == User.id)
        .join(Role, EnvironmentMembership.role_id == Role.id)
        .where(EnvironmentMembership.environment_id == environment_id)
    ).all()
    return [
        {
            "id": str(m.id),
            "user_id": str(u.id),
            "display_name": u.display_name,
            "email": u.email,
            "role_code": r.code,
        }
        for m, u, r in rows
    ]


@router.delete("/environments/{environment_id}/memberships/{membership_id}", status_code=204)
def delete_membership(environment_id: uuid.UUID, membership_id: uuid.UUID, db: DB, user: Current) -> None:
    require(db, user, environment_id, "environment.manage")
    item = db.get(EnvironmentMembership, membership_id)
    if not item or item.environment_id != environment_id:
        raise HTTPException(404, "Membership not found")
    db.delete(item)
    db.commit()


@router.post("/environments/{environment_id}/memberships", status_code=201)
def add_membership(environment_id: uuid.UUID, data: MembershipIn, db: DB, user: Current) -> dict:
    require(db, user, environment_id, "environment.manage")
    role = db.scalar(select(Role).where(Role.code == data.role_code))
    if not role:
        raise HTTPException(404, "Role not found")
    item = EnvironmentMembership(environment_id=environment_id, user_id=data.user_id, role_id=role.id)
    db.add(item)
    db.commit()
    return {"id": str(item.id)}


@router.get("/request-types", response_model=list[RequestTypeOut])
def request_types(db: DB, user: Current, environment_id: Annotated[uuid.UUID, Query()]) -> list[RequestType]:
    require(db, user, environment_id, "request_type.read")
    return list(db.scalars(select(RequestType).where(RequestType.environment_id == environment_id)))


@router.post("/request-types", response_model=RequestTypeOut, status_code=201)
def create_request_type(data: RequestTypeIn, db: DB, user: Current) -> RequestType:
    require(db, user, data.environment_id, "request_type.manage")
    item = RequestType(system_number=NumberingService.next(db, "request_type", data.environment_id),
                       **data.model_dump())
    db.add(item)
    db.flush()
    form = FormDefinition(request_type_id=item.id, version=1, status=FormStatus.published,
                          published_at=datetime.now(UTC), fields=[])
    db.add(form)
    db.flush()
    item.form_version_id = form.id
    audit(db, user, "request_type", item.id, "created", after=data.model_dump(mode="json"))
    db.commit()
    return item


@router.get("/request-types/{request_type_id}", response_model=RequestTypeOut)
def get_request_type(request_type_id: uuid.UUID, db: DB, user: Current) -> RequestType:
    item = db.get(RequestType, request_type_id)
    if not item:
        raise HTTPException(404, "Request type not found")
    require(db, user, item.environment_id, "request_type.read")
    return item


@router.patch("/request-types/{request_type_id}", response_model=RequestTypeOut)
def update_request_type(
    request_type_id: uuid.UUID, data: RequestTypePatch, db: DB, user: Current
) -> RequestType:
    item = db.get(RequestType, request_type_id)
    if not item:
        raise HTTPException(404, "Request type not found")
    require(db, user, item.environment_id, "request_type.manage")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    audit(db, user, "request_type", item.id, "updated")
    db.commit()
    return item


@router.post("/forms", response_model=FormOut, status_code=201)
def create_form(data: FormIn, db: DB, user: Current) -> FormDefinition:
    rt = db.get(RequestType, data.request_type_id)
    if not rt:
        raise HTTPException(404, "Request type not found")
    require(db, user, rt.environment_id, "request_type.manage")
    version = (
        db.scalar(select(func.max(FormDefinition.version)).where(FormDefinition.request_type_id == rt.id))
        or 0
    ) + 1
    form = FormDefinition(request_type_id=rt.id, version=version)
    form.fields = [FieldDefinition(**field.model_dump()) for field in data.fields]
    db.add(form)
    db.flush()
    audit(db, user, "form", form.id, "created")
    db.commit()
    return form


@router.get("/forms/{form_id}", response_model=FormOut)
def get_form(form_id: uuid.UUID, db: DB, user: Current) -> FormDefinition:
    form = db.get(FormDefinition, form_id)
    if not form:
        raise HTTPException(404, "Form not found")
    rt = db.get(RequestType, form.request_type_id)
    if not rt:
        raise HTTPException(409, "Form request type no longer exists")
    require(db, user, rt.environment_id, "request_type.read")
    return form


@router.get("/forms", response_model=list[FormOut])
def list_forms(request_type_id: uuid.UUID, db: DB, user: Current) -> list[FormDefinition]:
    rt = db.get(RequestType, request_type_id)
    if not rt:
        raise HTTPException(404, "Request type not found")
    require(db, user, rt.environment_id, "request_type.read")
    return list(
        db.scalars(
            select(FormDefinition)
            .where(FormDefinition.request_type_id == request_type_id)
            .order_by(FormDefinition.version.desc())
        )
    )


@router.post("/forms/{form_id}/clone-draft", response_model=FormOut, status_code=201)
def clone_draft(form_id: uuid.UUID, db: DB, user: Current) -> FormDefinition:
    source = db.get(FormDefinition, form_id)
    if not source or source.status != FormStatus.published:
        raise HTTPException(409, "Only a published form can be cloned")
    rt = db.get(RequestType, source.request_type_id)
    if not rt:
        raise HTTPException(409, "Form request type no longer exists")
    require(db, user, rt.environment_id, "request_type.manage")
    version = (
        db.scalar(select(func.max(FormDefinition.version)).where(FormDefinition.request_type_id == rt.id))
        or 0
    ) + 1
    draft = FormDefinition(
        request_type_id=rt.id,
        version=version,
        status=FormStatus.draft,
        fields=[
            FieldDefinition(
                key=f.key,
                label_he=f.label_he,
                label_en=f.label_en,
                field_type=f.field_type,
                is_required=f.is_required,
                is_read_only=f.is_read_only,
                sort_order=f.sort_order,
                configuration_json=f.configuration_json,
            )
            for f in source.fields
        ],
    )
    db.add(draft)
    db.commit()
    return draft


@router.patch("/forms/{form_id}", response_model=FormOut)
def update_form(form_id: uuid.UUID, data: FormPatch, db: DB, user: Current) -> FormDefinition:
    form = db.get(FormDefinition, form_id)
    if not form:
        raise HTTPException(404, "Form not found")
    if form.status != FormStatus.draft:
        raise HTTPException(409, "Published forms are immutable")
    rt = db.get(RequestType, form.request_type_id)
    if not rt:
        raise HTTPException(409, "Form request type no longer exists")
    require(db, user, rt.environment_id, "request_type.manage")
    form.fields = [FieldDefinition(**f.model_dump()) for f in data.fields]
    db.commit()
    return form


@router.post("/forms/{form_id}/publish", response_model=FormOut)
def publish(form_id: uuid.UUID, db: DB, user: Current) -> FormDefinition:
    form = db.get(FormDefinition, form_id)
    if not form:
        raise HTTPException(404, "Form not found")
    rt = db.get(RequestType, form.request_type_id)
    if not rt:
        raise HTTPException(409, "Form request type no longer exists")
    require(db, user, rt.environment_id, "request_type.manage")
    if form.status != FormStatus.draft:
        raise HTTPException(409, "Published forms are immutable")
    form.status = FormStatus.published
    form.published_at = datetime.now(UTC)
    rt.form_version_id = form.id
    audit(db, user, "form", form.id, "published")
    db.commit()
    return form


def typed_value(case_id: uuid.UUID, field: FieldDefinition, value: Any) -> CaseFieldValue:
    row = CaseFieldValue(case_id=case_id, field_definition_id=field.id)
    if value is None:
        return row
    if field.field_type in {"short_text", "long_text", "single_select"}:
        row.value_text = str(value)
    elif field.field_type == "number":
        row.value_number = Decimal(str(value))
    elif field.field_type == "boolean":
        row.value_boolean = bool(value)
    elif field.field_type == "date":
        row.value_date = date.fromisoformat(value)
    elif field.field_type == "datetime":
        row.value_datetime = datetime.fromisoformat(value)
    elif field.field_type == "user":
        row.value_user_id = uuid.UUID(value)
    else:
        row.value_json = value
    return row


@router.post("/cases", response_model=CaseOut, status_code=201)
def create_case(data: CaseIn, db: DB, user: Current) -> Case:
    require(db, user, data.environment_id, "case.create")
    rt = db.get(RequestType, data.request_type_id)
    if not rt or rt.environment_id != data.environment_id or not rt.form_version_id:
        raise HTTPException(400, "Published form is required")
    form = db.get(FormDefinition, rt.form_version_id)
    if not form:
        raise HTTPException(409, "Published form no longer exists")
    priority_id = data.priority_id or rt.default_priority_id
    if not priority_id:
        raise HTTPException(422, "לא הוגדרה עדיפות ברירת מחדל; יש לבחור עדיפות")
    priority = db.get(PriorityDefinition, priority_id)
    if not priority or priority.environment_id != data.environment_id or not priority.is_active:
        raise HTTPException(422, "Priority does not belong to the selected environment")
    sub_priority_id = data.sub_priority_id or rt.default_sub_priority_id
    if sub_priority_id:
        sub_priority = db.get(SubPriorityDefinition, sub_priority_id)
        if not sub_priority or sub_priority.environment_id != data.environment_id or not sub_priority.is_active:
            raise HTTPException(422, "Sub-priority does not belong to the selected priority")
    provided = {v.field_definition_id: v.value for v in data.values}
    missing = [f.label_he for f in form.fields if f.is_required and provided.get(f.id) in (None, "")]
    if missing:
        raise HTTPException(422, {"missing_required_fields": missing})
    item = Case(
        case_number=NumberingService.next(db, "case", data.environment_id),
        form_definition_id=form.id,
        reporter_id=user.id,
        requester_id=user.id,
        environment_id=data.environment_id,
        request_type_id=data.request_type_id,
        title=data.title,
        description=data.description,
        priority=priority.code,
        priority_id=priority.id,
        sub_priority_id=sub_priority_id,
    )
    db.add(item)
    db.flush()
    initial_status = initialize_operations(db, item, rt)
    if data.workflow_status_id and data.workflow_status_id != initial_status.id:
        workflow, _ = resolve_workflow(db, rt)
        selected_status = db.get(WorkflowStatus, data.workflow_status_id)
        if not selected_status or selected_status.workflow_id != workflow.id or not selected_status.is_active:
            raise HTTPException(422, "הסטטוס אינו שייך לתהליך העבודה של סוג הקריאה")
        if "case.change_status" not in permissions(db, user, data.environment_id):
            raise HTTPException(403, "אין הרשאה לשנות סטטוס בעת פתיחת קריאה")
        item.workflow_status_id = selected_status.id
    item.values = [typed_value(item.id, f, provided.get(f.id)) for f in form.fields if f.id in provided]
    for participant_id in set(data.participant_ids):
        participant_user = db.get(User, participant_id)
        if participant_id != user.id and participant_user:
            db.add(CaseParticipant(case_id=item.id, user_id=participant_id,
                                   participant_type="participant", added_by=user.id))
    audit(
        db,
        user,
        "case",
        item.id,
        "created",
        after={"status": item.status.value, "workflow_status_id": str(initial_status.id)},
    )
    AutomationEngine.run(db, item, "request_type_selected",
                         {"request_type": str(item.request_type_id), "request_type_id": str(item.request_type_id)})
    AutomationEngine.run(db, item, "case_created", {"request_type": str(item.request_type_id)})
    start_matching_approvals(db, item)
    db.commit()
    return item


@router.get("/request-types/{request_type_id}/case-config")
def case_creation_config(request_type_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    request_type = db.get(RequestType, request_type_id)
    if not request_type or not request_type.is_active:
        raise HTTPException(404, "סוג הקריאה לא נמצא")
    require(db, user, request_type.environment_id, "case.create")
    workflow, initial = resolve_workflow(db, request_type)
    statuses = list(db.scalars(select(WorkflowStatus).where(
        WorkflowStatus.workflow_id == workflow.id,
        WorkflowStatus.is_active.is_(True),
    ).order_by(WorkflowStatus.sort_order)))
    return {
        "workflow_id": workflow.id,
        "initial_status_id": initial.id,
        "can_choose_status": "case.change_status" in permissions(db, user, request_type.environment_id),
        "statuses": [{"id": row.id, "label_he": row.label_he, "is_initial": row.is_initial} for row in statuses],
        "default_priority_id": request_type.default_priority_id,
        "default_sub_priority_id": request_type.default_sub_priority_id,
    }


@router.get("/cases", response_model=list[CaseOut])
def cases(
    db: DB,
    user: Current,
    assigned: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Case]:
    query = select(Case).order_by(Case.created_at.desc())
    if assigned:
        query = query.where(Case.assignee_id == user.id)
    elif not user.is_system_admin:
        broad_environment_ids = []
        for env_id, role in db.execute(
            select(EnvironmentMembership.environment_id, Role)
            .join(Role, EnvironmentMembership.role_id == Role.id)
            .where(EnvironmentMembership.user_id == user.id)
        ):
            if "case.assign" in role.permissions or role.code == "viewer":
                broad_environment_ids.append(env_id)
        query = query.where(
            or_(
                Case.requester_id == user.id,
                Case.reporter_id == user.id,
                Case.assignee_id == user.id,
                Case.environment_id.in_(broad_environment_ids),
                Case.id.in_(select(CaseParticipant.case_id).where(CaseParticipant.user_id == user.id)),
            )
        )
    return list(db.scalars(query.offset(offset).limit(limit)).unique())


@router.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: uuid.UUID, db: DB, user: Current) -> CaseOut:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    visible_comments = [
        c
        for c in item.comments
        if c.visibility == Visibility.public
        or "comment.manager.read" in permissions(db, user, item.environment_id)
    ]
    granted = permissions(db, user, item.environment_id)
    can_override_lock = user.is_system_admin or "case.lock" in granted
    return CaseOut.model_validate(item).model_copy(
        update={
            "comments": [CommentOut.model_validate(c) for c in visible_comments],
            "permissions": {
                "can_edit": "case.update" in granted and (not item.is_locked or can_override_lock),
                "can_lock": can_override_lock,
                "can_assign": "case.assign" in granted,
                "can_change_status": "case.change_status" in granted or "case.update" in granted,
                "can_manage_participants": "case.manage_participants" in granted,
                "can_read_manager_comments": "comment.manager.read" in granted,
                "can_create_manager_comments": "comment.manager.create" in granted,
            },
        }
    )


@router.patch("/cases/{case_id}", response_model=CaseOut)
def update_case(case_id: uuid.UUID, data: CasePatch, db: DB, user: Current) -> Case:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    require(db, user, item.environment_id, "case.update")
    if item.is_locked and not (user.is_system_admin or "case.lock" in permissions(db, user, item.environment_id)):
        raise HTTPException(423, "הקריאה נעולה לשינויים")
    if item.version != data.version:
        raise HTTPException(409, "Case was updated by another user")
    changes = data.model_dump(exclude={"version", "values"}, exclude_unset=True)
    if data.priority_id:
        priority = db.get(PriorityDefinition, data.priority_id)
        if not priority or priority.environment_id != item.environment_id or not priority.is_active:
            raise HTTPException(422, "העדיפות אינה שייכת לסביבה")
    if data.sub_priority_id:
        sub_priority = db.get(SubPriorityDefinition, data.sub_priority_id)
        if not sub_priority or sub_priority.environment_id != item.environment_id or not sub_priority.is_active:
            raise HTTPException(422, "תת-העדיפות אינה שייכת לעדיפות")
    for key, value in changes.items():
        setattr(item, key, value)
    if data.values is not None:
        fields = {field.id: field for field in db.scalars(select(FieldDefinition).where(
            FieldDefinition.form_definition_id == item.form_definition_id))}
        for supplied in data.values:
            field = fields.get(supplied.field_definition_id)
            if not field:
                raise HTTPException(422, "השדה הדינמי אינו שייך לטופס הקריאה")
            db.execute(delete(CaseFieldValue).where(
                CaseFieldValue.case_id == item.id,
                CaseFieldValue.field_definition_id == supplied.field_definition_id,
            ))
            db.add(typed_value(item.id, field, supplied.value))
    item.version += 1
    audit(db, user, "case", item.id, "updated")
    db.commit()
    return item


@router.post("/cases/{case_id}/lock", response_model=CaseOut)
def set_case_lock(case_id: uuid.UUID, data: CaseLockIn, db: DB, user: Current) -> Case:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "הקריאה לא נמצאה")
    require(db, user, item.environment_id, "case.lock")
    if item.version != data.version:
        raise HTTPException(409, "הקריאה עודכנה על ידי משתמש אחר")
    if data.locked and not (data.reason or "").strip():
        raise HTTPException(422, "יש להזין סיבה לנעילת הקריאה")
    item.is_locked = data.locked
    item.locked_at = datetime.now(UTC) if data.locked else None
    item.locked_by = user.id if data.locked else None
    item.lock_reason = data.reason.strip() if data.locked and data.reason else None
    item.version += 1
    audit(db, user, "case", item.id, "locked" if data.locked else "unlocked",
          after={"reason": item.lock_reason})
    db.commit()
    return item


@router.post("/cases/{case_id}/assign", response_model=CaseOut)
def assign_case(case_id: uuid.UUID, data: AssignIn, db: DB, user: Current) -> Case:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    require(db, user, item.environment_id, "case.assign")
    if item.version != data.version:
        raise HTTPException(409, "Case was updated by another user")
    if data.assignee_id and not db.get(User, data.assignee_id):
        raise HTTPException(404, "Assignee not found")
    item.assignee_id = data.assignee_id
    item.version += 1
    if item.status == CaseStatus.submitted:
        item.status = CaseStatus.assigned
    audit(
        db,
        user,
        "case",
        item.id,
        "assigned",
        after={"assignee_id": str(data.assignee_id) if data.assignee_id else None},
    )
    db.commit()
    return item


@router.get("/cases/{case_id}/allowed-transitions")
def allowed_transitions(case_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    if "case.change_status" not in permissions(db, user, item.environment_id):
        return []
    rows = db.execute(select(WorkflowTransition, WorkflowStatus).join(
        WorkflowStatus, WorkflowTransition.to_status_id == WorkflowStatus.id).where(
        WorkflowTransition.from_status_id == item.workflow_status_id,
        WorkflowTransition.is_active.is_(True),
        WorkflowStatus.is_active.is_(True),
    ).order_by(WorkflowTransition.sort_order)).all()
    return [{"id": status.id, "label_he": status.label_he, "transition_id": transition.id,
             "requires_comment": transition.requires_comment} for transition, status in rows]


@router.post("/cases/{case_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(case_id: uuid.UUID, data: CommentIn, db: DB, user: Current) -> Comment:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    require(
        db,
        user,
        item.environment_id,
        "case.internal_comment" if data.visibility == Visibility.internal else "case.comment",
    )
    comment = Comment(case_id=item.id, author_id=user.id, **data.model_dump())
    db.add(comment)
    db.flush()
    audit(db, user, "case", item.id, "commented", after={"visibility": data.visibility.value})
    db.commit()
    return comment


@router.post("/cases/{case_id}/participants", status_code=201)
def add_participant(case_id: uuid.UUID, data: ParticipantIn, db: DB, user: Current) -> dict:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    require(db, user, item.environment_id, "case.manage_participants")
    row = CaseParticipant(
        case_id=case_id, user_id=data.user_id, participant_type=data.participant_type, added_by=user.id
    )
    db.add(row)
    audit(db, user, "case", item.id, "participant_added")
    db.commit()
    return {"ok": True}


@router.get("/cases/{case_id}/participants")
def list_participants(case_id: uuid.UUID, db: DB, user: Current) -> list[dict]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    rows = db.execute(
        select(CaseParticipant, User)
        .join(User, CaseParticipant.user_id == User.id)
        .where(CaseParticipant.case_id == case_id)
    ).all()
    return [
        {"user_id": str(u.id), "display_name": u.display_name, "participant_type": p.participant_type}
        for p, u in rows
    ]


@router.delete("/cases/{case_id}/participants/{participant_user_id}", status_code=204)
def remove_participant(case_id: uuid.UUID, participant_user_id: uuid.UUID, db: DB, user: Current) -> None:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    require(db, user, item.environment_id, "case.manage_participants")
    if participant_user_id in {item.requester_id, item.reporter_id}:
        raise HTTPException(409, "לא ניתן להסיר את פותח הקריאה")
    if participant_user_id == item.assignee_id:
        raise HTTPException(409, "לא ניתן להסיר את המטפל הנוכחי")
    rows = list(
        db.scalars(
            select(CaseParticipant).where(
                CaseParticipant.case_id == case_id, CaseParticipant.user_id == participant_user_id
            )
        )
    )
    if not rows:
        raise HTTPException(404, "Participant not found")
    for row in rows:
        db.delete(row)
    audit(db, user, "case", item.id, "participant_removed",
          after={"user_id": str(participant_user_id)})
    db.commit()


@router.get("/cases/{case_id}/timeline")
def timeline(case_id: uuid.UUID, db: DB, user: Current) -> list[dict]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_type == "case", AuditEvent.entity_id == str(case_id))
        .order_by(AuditEvent.created_at.desc())
    )
    return [
        {
            "action": e.action,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "before": e.before_json,
            "after": e.after_json,
            "created_at": e.created_at,
        }
        for e in events
    ]


@router.post("/cases/{case_id}/transitions", response_model=CaseOut)
def transition(case_id: uuid.UUID, data: TransitionIn, db: DB, user: Current) -> Case:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    require(db, user, item.environment_id, "case.change_status")
    transition_row = db.scalar(select(WorkflowTransition).where(
        WorkflowTransition.from_status_id == item.workflow_status_id,
        WorkflowTransition.to_status_id == data.workflow_status_id,
        WorkflowTransition.is_active.is_(True),
    ))
    target = db.get(WorkflowStatus, data.workflow_status_id)
    if not transition_row or not target or not target.is_active:
        raise HTTPException(409, "מעבר הסטטוס אינו חוקי בתהליך העבודה")
    if transition_row.required_permission_code:
        require(db, user, item.environment_id, transition_row.required_permission_code)
    if transition_row.requires_comment and not (data.comment or "").strip():
        raise HTTPException(422, "המעבר מחייב הערה")
    before = item.workflow_status_id
    item.workflow_status_id = target.id
    item.version += 1
    if target.is_closed:
        item.closed_at = datetime.now(UTC)
    db.add(CaseStatusHistory(case_id=item.id, from_status_id=before, to_status_id=target.id,
                             transition_id=transition_row.id, changed_by=user.id,
                             comment=(data.comment or "").strip() or None))
    AutomationEngine.run(db, item, "status_changed", {
        "status": str(target.id), "status_id": str(target.id),
        "request_type": str(item.request_type_id), "request_type_id": str(item.request_type_id),
    })
    audit(
        db, user, "case", item.id, "status_changed",
        {"workflow_status_id": str(before) if before else None},
        {"workflow_status_id": str(target.id), "label": target.label_he},
    )
    db.commit()
    return item


@router.get("/audit")
def audit_events(db: DB, user: Current) -> list[dict]:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")
    return [
        {
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "action": a.action,
            "created_at": a.created_at,
        }
        for a in db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(200))
    ]
