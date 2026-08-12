import json
import logging
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any
from typing import cast as typing_cast

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.modules.access.service import domain_permissions
from app.modules.approvals.service import start_matching_approvals
from app.modules.automation.service import AutomationEngine
from app.modules.employees.service import sync_employee_for_user
from app.modules.environment_clone.service import clone_configuration
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
    Group,
    PriorityDefinition,
    RefreshToken,
    RequestType,
    SubPriorityDefinition,
    User,
    Visibility,
)
from app.modules.numbering.service import NumberingService
from app.modules.operations.models import (
    CaseStatusHistory,
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowTransition,
)
from app.modules.operations.service import (
    ensure_environment_statuses,
    initialize_operations,
    resolve_workflow,
)

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
oauth = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
password_hash = PasswordHash.recommended()
DB = Annotated[Session, Depends(get_db)]
ALL_PERMISSIONS = [
    "system.users.read", "system.users.create", "system.users.update", "system.users.disable",
    "system.users.reset_password", "system.groups.read", "system.groups.manage", "system.roles.read",
    "system.roles.manage", "system.fields.read", "system.fields.manage", "system.environments.create",
    "system.environments.manage", "system.fields.delete",
    "environment.read",
    "environment.manage", "environment.delete", "environment.fields.delete",
    "environment.users.manage", "environment.groups.manage", "environment.fields.manage",
    "environment.request_types.manage", "environment.forms.manage", "environment.rules.manage",
    "environment.audit.read",
    "request_type.read",
    "request_type.manage",
    "case.create",
    "case.read", "case.read_own", "case.read_participating", "case.read_environment",
    "case.update", "case.lock", "case.transfer_environment",
    "knowledge.read", "knowledge.manage", "knowledge.query",
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
    "report.cases", "report.approvals", "report.users", "report.audit", "report.sla",
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


class ImpersonationIn(BaseModel):
    user_id: uuid.UUID


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_system_admin: bool
    model_config = {"from_attributes": True}


class EnvironmentIn(BaseModel):
    name_he: str
    name_en: str
    description: str | None = None


class EnvironmentOut(EnvironmentIn):
    id: uuid.UUID
    system_number: str
    code: str
    is_active: bool
    model_config = {"from_attributes": True}


class EnvironmentCloneIn(BaseModel):
    name_he: str
    name_en: str
    description: str | None = None
    copy_memberships: bool = False
    copy_knowledge: bool = False


class MembershipIn(BaseModel):
    user_id: uuid.UUID


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
    is_active: bool = True
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
    environment_name: str | None = None
    request_type_id: uuid.UUID
    form_definition_id: uuid.UUID | None
    title: str
    description: str | None
    status: CaseStatus
    priority: str
    priority_id: uuid.UUID | None
    sub_priority_id: uuid.UUID | None
    reporter_id: uuid.UUID
    requester_id: uuid.UUID
    reporter_name: str | None = None
    reporter_email: str | None = None
    assignee_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
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
    request_type_id: uuid.UUID | None = None
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


def issue(user: User, token_type: str, expires: timedelta, token_id: uuid.UUID | None = None,
          real_actor_id: uuid.UUID | None = None) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user.id), "type": token_type, "iat": now, "exp": now + expires}
    if token_id:
        payload["jti"] = str(token_id)
    if real_actor_id:
        payload["real_actor_id"] = str(real_actor_id)
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
    payload = decode(token, "access")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "Inactive or unknown user")
    if payload.get("real_actor_id"):
        typing_cast(Any, user)._real_actor_user_id = uuid.UUID(payload["real_actor_id"])
    return user


Current = Annotated[User, Depends(current_user)]


def permissions(db: Session, user: User, environment_id: uuid.UUID) -> set[str]:
    if user.is_system_admin:
        return set(ALL_PERMISSIONS)
    return domain_permissions(db, user.id, environment_id)


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
    real_actor_id = getattr(user, "_real_actor_user_id", None)
    metadata = {"real_actor_user_id": str(real_actor_id), "impersonated_user_id": str(user.id)} if real_actor_id else {}
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
            metadata_json=metadata,
        )
    )


def require_impersonation_permission(db: Session, user: User) -> None:
    if not user.is_system_admin and "system.impersonate_users" not in domain_permissions(db, user.id, None):
        raise HTTPException(403, "חסרה הרשאת התחזות למשתמש")


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
    if not user or not password_hash.verify(data.password, user.password_hash) or not user.is_active or user.status != "active":
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
        source="manual",
        status="active",
    )
    db.add(user)
    db.flush()
    sync_employee_for_user(db, user)
    active_environments = list(db.scalars(select(Environment).where(Environment.is_active.is_(True))))
    if len(active_environments) == 1:
        db.add(EnvironmentMembership(environment_id=active_environments[0].id, user_id=user.id,
                                     role_id=None, source="manual"))
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


@router.post("/impersonation/start")
def start_impersonation(data: ImpersonationIn, db: DB, user: Current) -> dict[str, Any]:
    if getattr(user, "_real_actor_user_id", None):
        raise HTTPException(409, "יש לסיים את ההתחזות הפעילה לפני התחזות אחרת")
    require_impersonation_permission(db, user)
    target = db.get(User, data.user_id)
    if not target or not target.is_active:
        raise HTTPException(404, "המשתמש המבוקש אינו פעיל או אינו קיים")
    audit(db, user, "user", target.id, "impersonation_started",
          after={"real_actor_user_id": str(user.id), "impersonated_user_id": str(target.id)})
    db.commit()
    return {"access_token": issue(target, "access", timedelta(minutes=settings.access_token_minutes),
                                  real_actor_id=user.id)}


@router.post("/impersonation/stop")
def stop_impersonation(db: DB, user: Current) -> dict[str, Any]:
    real_actor_id = getattr(user, "_real_actor_user_id", None)
    if not real_actor_id:
        raise HTTPException(409, "אין התחזות פעילה")
    actor = db.get(User, real_actor_id)
    if not actor or not actor.is_active:
        raise HTTPException(401, "המשתמש המקורי אינו פעיל")
    audit(db, user, "user", user.id, "impersonation_stopped")
    db.commit()
    return {"access_token": issue(actor, "access", timedelta(minutes=settings.access_token_minutes))}


@router.get("/impersonation/status")
def impersonation_status(db: DB, user: Current) -> dict[str, Any]:
    real_actor_id = getattr(user, "_real_actor_user_id", None)
    actor = db.get(User, real_actor_id) if real_actor_id else None
    return {"active": bool(real_actor_id), "real_actor_user_id": real_actor_id,
            "real_actor_name": actor.display_name if actor else None,
            "impersonated_user_id": user.id if real_actor_id else None,
            "impersonated_user_name": user.display_name if real_actor_id else None,
            "can_start": not real_actor_id and (user.is_system_admin or "system.impersonate_users" in domain_permissions(db, user.id, None))}


@router.get("/users", response_model=list[UserOut])
def users(db: DB, user: Current) -> list[User]:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")
    return list(db.scalars(select(User).order_by(User.display_name)))


@router.get("/roles")
def roles(db: DB, user: Current) -> list[dict]:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")
    raise HTTPException(410, "Role הוסר ממודל המוצר; הרשאות מנוהלות באמצעות קבוצות וחריגות משתמש")


@router.get("/groups")
def groups(db: DB, user: Current) -> list[dict]:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")
    return [{"id": row.id, "name": row.name, "description": row.description,
             "is_active": row.is_active, "member_count": 0}
            for row in db.scalars(select(Group).order_by(Group.name))]


@router.get("/environments", response_model=list[EnvironmentOut])
def environments(db: DB, user: Current) -> list[Environment]:
    query = select(Environment).order_by(Environment.name_he)
    if not user.is_system_admin:
        query = query.join(EnvironmentMembership).where(EnvironmentMembership.user_id == user.id)
    rows = list(db.scalars(query).unique())
    changed = False
    for row in rows:
        if not row.system_number:
            row.system_number = NumberingService.next(db, "environment")
            changed = True
    if changed:
        db.commit()
    return rows


@router.get("/case-creation/environments", response_model=list[EnvironmentOut])
def case_creation_environments(db: DB, user: Current) -> list[Environment]:
    query = select(Environment).where(Environment.is_active.is_(True)).order_by(Environment.name_he)
    if not user.is_system_admin:
        query = query.join(EnvironmentMembership).where(
            EnvironmentMembership.user_id == user.id,
            EnvironmentMembership.is_active.is_(True),
        )
    rows = list(db.scalars(query).unique())
    changed = False
    for row in rows:
        if not row.system_number:
            row.system_number = NumberingService.next(db, "environment")
            changed = True
    if changed:
        db.commit()
    return rows


@router.get("/case-creation/environments/{environment_id}/configuration")
def case_creation_environment_configuration(
    environment_id: uuid.UUID, db: DB, user: Current
) -> dict[str, Any]:
    require(db, user, environment_id, "case.create")
    environment = db.get(Environment, environment_id)
    if not environment or not environment.is_active:
        raise HTTPException(404, "הסביבה אינה זמינה לפתיחת קריאה")
    request_types = list(db.scalars(select(RequestType).where(
        RequestType.environment_id == environment_id, RequestType.is_active.is_(True)
    ).order_by(RequestType.sort_order, RequestType.name_he)))
    priorities = list(db.scalars(select(PriorityDefinition).where(
        PriorityDefinition.environment_id == environment_id, PriorityDefinition.is_active.is_(True)
    ).order_by(PriorityDefinition.sort_order)))
    sub_priorities = list(db.scalars(select(SubPriorityDefinition).where(
        SubPriorityDefinition.environment_id == environment_id, SubPriorityDefinition.is_active.is_(True)
    ).order_by(SubPriorityDefinition.sort_order)))
    type_rows = []
    for request_type in request_types:
        workflow, initial = resolve_workflow(db, request_type)
        statuses = list(db.scalars(select(WorkflowStatus).where(
            WorkflowStatus.workflow_id == workflow.id, WorkflowStatus.is_active.is_(True)
        ).order_by(WorkflowStatus.sort_order)))
        form = db.get(FormDefinition, request_type.form_version_id) if request_type.form_version_id else None
        type_rows.append({
            "id": request_type.id, "environment_id": request_type.environment_id,
            "name_he": request_type.name_he, "is_active": True,
            "default_priority_id": request_type.default_priority_id,
            "default_sub_priority_id": request_type.default_sub_priority_id,
            "initial_status_id": initial.id,
            "can_choose_status": "case.change_status" in permissions(db, user, environment_id),
            "statuses": [{"id": row.id, "label_he": row.label_he,
                          "is_initial": row.is_initial} for row in statuses],
            "form": FormOut.model_validate(form).model_dump() if form else None,
        })
    participant_rows = []
    if "case.manage_participants" in permissions(db, user, environment_id):
        participant_rows = [{"id": row.id, "display_name": row.display_name, "email": row.email}
                            for row in db.scalars(select(User).join(
                                EnvironmentMembership, EnvironmentMembership.user_id == User.id
                            ).where(EnvironmentMembership.environment_id == environment_id,
                                    EnvironmentMembership.is_active.is_(True), User.is_active.is_(True),
                                    User.status == "active").order_by(User.display_name)).unique()]
    return {
        "environment_id": environment.id, "request_types": type_rows,
        "priorities": [{"id": row.id, "label_he": row.label_he, "is_active": True}
                       for row in priorities],
        "sub_priorities": [{"id": row.id, "priority_id": row.priority_id,
                            "label_he": row.label_he, "is_active": True} for row in sub_priorities],
        "participants": participant_rows,
    }


@router.post("/environments", response_model=EnvironmentOut, status_code=201)
def create_environment(data: EnvironmentIn, db: DB, user: Current) -> Environment:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")
    system_number = NumberingService.next(db, "environment")
    item = Environment(code=system_number, system_number=system_number, **data.model_dump())
    db.add(item)
    db.flush()
    ensure_environment_statuses(db, item.id, user.id)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Environment code already exists") from exc
    audit(db, user, "environment", item.id, "created", after=data.model_dump())
    db.commit()
    db.refresh(item)
    return item


@router.post("/environments/{environment_id}/clone", status_code=201)
def clone_environment(environment_id: uuid.UUID, data: EnvironmentCloneIn, db: DB, user: Current) -> dict[str, Any]:
    if not user.is_system_admin:
        raise HTTPException(403, "System administrator required")
    source = db.get(Environment, environment_id)
    if not source:
        raise HTTPException(404, "Environment not found")
    system_number = NumberingService.next(db, "environment")
    target = Environment(code=system_number, system_number=system_number, name_he=data.name_he,
        name_en=data.name_en, description=data.description, is_active=True)
    db.add(target); db.flush()
    counts = clone_configuration(db, source, target, user.id, data.copy_memberships, data.copy_knowledge)
    ensure_environment_statuses(db, target.id, user.id)
    audit(db, user, "environment", target.id, "cloned", after={
        "source_environment_id": str(source.id), **counts,
        "copy_memberships": data.copy_memberships, "copy_knowledge": data.copy_knowledge,
    })
    db.commit(); db.refresh(target)
    return {"environment": EnvironmentOut.model_validate(target), "summary": counts}


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


@router.post("/environments/{environment_id}/archive", response_model=EnvironmentOut)
def archive_environment(environment_id: uuid.UUID, db: DB, user: Current) -> Environment:
    require(db, user, environment_id, "environment.manage")
    item = db.get(Environment, environment_id)
    if not item:
        raise HTTPException(404, "הסביבה לא נמצאה")
    before = {"is_active": item.is_active}
    item.is_active = False
    audit(db, user, "environment", item.id, "archived", before, {"is_active": False})
    db.commit()
    return item


@router.post("/environments/{environment_id}/restore", response_model=EnvironmentOut)
def restore_environment(environment_id: uuid.UUID, db: DB, user: Current) -> Environment:
    require(db, user, environment_id, "environment.manage")
    item = db.get(Environment, environment_id)
    if not item:
        raise HTTPException(404, "הסביבה לא נמצאה")
    before = {"is_active": item.is_active}
    item.is_active = True
    audit(db, user, "environment", item.id, "restored", before, {"is_active": True})
    db.commit()
    return item


@router.get("/environments/{environment_id}/delete-impact")
def environment_delete_impact(environment_id: uuid.UUID, db: DB, user: Current) -> dict[str, Any]:
    require(db, user, environment_id, "environment.delete")
    item = db.get(Environment, environment_id)
    if not item:
        raise HTTPException(404, "הסביבה לא נמצאה")
    case_count = db.scalar(select(func.count()).select_from(Case).where(Case.environment_id == item.id)) or 0
    dependency_count = db.scalar(select(func.count()).select_from(RequestType).where(RequestType.environment_id == item.id)) or 0
    return {"environment_id": item.id, "name": item.name_he, "cases": case_count,
            "dependencies": dependency_count, "can_delete": case_count == 0 and dependency_count == 0}


@router.delete("/environments/{environment_id}", status_code=204)
def delete_environment(environment_id: uuid.UUID, confirmation: str, db: DB, user: Current) -> None:
    require(db, user, environment_id, "environment.delete")
    item = db.get(Environment, environment_id)
    if not item:
        raise HTTPException(404, "הסביבה לא נמצאה")
    if confirmation != item.name_he:
        raise HTTPException(422, "יש להקליד את שם הסביבה במדויק")
    impact = environment_delete_impact(environment_id, db, user)
    if not impact["can_delete"]:
        raise HTTPException(409, detail={"message": "לסביבה קיימות תלויות ולכן ניתן להעביר אותה לארכיון בלבד", **impact})
    audit(db, user, "environment", item.id, "deleted", before={"name_he": item.name_he})
    db.flush()
    db.delete(item)
    db.commit()


@router.get("/environments/{environment_id}/memberships")
def memberships(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict]:
    require(db, user, environment_id, "environment.manage")
    rows = db.execute(
        select(EnvironmentMembership, User)
        .join(User, EnvironmentMembership.user_id == User.id)
        .where(EnvironmentMembership.environment_id == environment_id)
    ).all()
    return [
        {
            "id": str(m.id),
            "user_id": str(u.id),
            "display_name": u.display_name,
            "email": u.email,
            "source": m.source,
        }
        for m, u in rows
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
    item = EnvironmentMembership(environment_id=environment_id, user_id=data.user_id,
                                 role_id=None, source="manual")
    db.add(item)
    db.commit()
    return {"id": str(item.id)}


@router.get("/request-types", response_model=list[RequestTypeOut])
def request_types(db: DB, user: Current, environment_id: Annotated[uuid.UUID, Query()],
                  active_only: bool = False) -> list[RequestType]:
    require(db, user, environment_id, "request_type.read")
    query = select(RequestType).where(RequestType.environment_id == environment_id)
    if active_only:
        query = query.where(RequestType.is_active.is_(True))
    return list(db.scalars(query.order_by(RequestType.sort_order, RequestType.name_he)))


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
    if not rt or rt.environment_id != data.environment_id or not rt.is_active:
        raise HTTPException(422, "סוג הקריאה שנבחר אינו תקף בסביבה זו")
    form = db.get(FormDefinition, rt.form_version_id) if rt.form_version_id else None
    if rt.form_version_id and not form:
        raise HTTPException(409, "הטופס המקושר לסוג הקריאה אינו קיים")
    priority_id = data.priority_id or rt.default_priority_id
    if not priority_id:
        raise HTTPException(422, "לא הוגדרה עדיפות ברירת מחדל; יש לבחור עדיפות")
    priority = db.get(PriorityDefinition, priority_id)
    if not priority or priority.environment_id != data.environment_id or not priority.is_active:
        raise HTTPException(422, "Priority does not belong to the selected environment")
    sub_priority_id = data.sub_priority_id or rt.default_sub_priority_id
    if sub_priority_id:
        sub_priority = db.get(SubPriorityDefinition, sub_priority_id)
        if (not sub_priority or sub_priority.environment_id != data.environment_id
                or (sub_priority.priority_id is not None and sub_priority.priority_id != priority.id)
                or not sub_priority.is_active):
            raise HTTPException(422, "Sub-priority does not belong to the selected priority")
    provided = {v.field_definition_id: v.value for v in data.values}
    active_fields = [field for field in form.fields if field.is_active] if form else []
    missing = [f.label_he for f in active_fields if f.is_required and provided.get(f.id) in (None, "")]
    if missing:
        raise HTTPException(422, {"missing_required_fields": missing})
    item = Case(
        case_number=NumberingService.next(db, "case", data.environment_id),
        form_definition_id=form.id if form else None,
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
    item.values = [typed_value(item.id, f, provided.get(f.id)) for f in active_fields if f.id in provided]
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
        for env_id in db.scalars(select(EnvironmentMembership.environment_id).where(
            EnvironmentMembership.user_id == user.id,
            EnvironmentMembership.is_active.is_(True),
        )):
            if "case.read_environment" in permissions(db, user, env_id):
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


@router.get("/cases/workspace/query")
def workspace_cases(
    db: DB,
    user: Current,
    view: str = Query("my", pattern="^(my|assigned)$"),
    activity_state: str = Query("active", pattern="^(active|inactive|all)$"),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    title: str = "",
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
    environment_id: uuid.UUID | None = None,
    dynamic_filters: str | None = None,
    include_participating: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort: str = "updated_at:desc",
) -> dict[str, Any]:
    active_memberships = list(
        db.scalars(
            select(EnvironmentMembership.environment_id).where(
                EnvironmentMembership.user_id == user.id,
                EnvironmentMembership.is_active.is_(True),
            )
        )
    )
    can_view_assigned = user.is_system_admin or any(
        "case.assign" in permissions(db, user, environment_id_) for environment_id_ in active_memberships
    )
    if view == "assigned" and not can_view_assigned:
        raise HTTPException(403, "אין הרשאה לצפות בקריאות בטיפולי")
    query = select(Case)
    if view == "my":
        own_filter = or_(Case.reporter_id == user.id, Case.requester_id == user.id)
        if include_participating:
            own_filter = or_(own_filter, Case.id.in_(select(CaseParticipant.case_id).where(
                CaseParticipant.user_id == user.id
            )))
        query = query.where(own_filter)
    else:
        query = query.where(Case.assignee_id == user.id)
    if environment_id:
        query = query.where(Case.environment_id == environment_id)
    if title.strip():
        query = query.where(Case.title.ilike(f"%{title.strip()}%"))
    if created_from:
        query = query.where(Case.created_at >= created_from)
    if created_to:
        query = query.where(Case.created_at <= created_to)
    if updated_from:
        query = query.where(Case.updated_at >= updated_from)
    if updated_to:
        query = query.where(Case.updated_at <= updated_to)
    if activity_state != "all":
        inactive_statuses = select(WorkflowStatus.id).where(
            WorkflowStatus.semantic_category.in_(["resolved", "closed"])
        )
        query = query.where(
            Case.workflow_status_id.not_in(inactive_statuses)
            if activity_state == "active"
            else Case.workflow_status_id.in_(inactive_statuses)
        )
    if dynamic_filters:
        try:
            supplied_filters = json.loads(dynamic_filters)
        except json.JSONDecodeError as exc:
            raise HTTPException(422, "מסנני הסביבה אינם תקינים") from exc
        for field_id, value in supplied_filters.items():
            try:
                parsed_field_id = uuid.UUID(field_id)
            except ValueError as exc:
                raise HTTPException(422, "מזהה שדה סביבה אינו תקין") from exc
            query = query.where(
                Case.id.in_(
                    select(CaseFieldValue.case_id).where(
                        CaseFieldValue.field_definition_id == parsed_field_id,
                        or_(
                            CaseFieldValue.value_text == str(value),
                            cast(CaseFieldValue.value_number, String) == str(value),
                            cast(CaseFieldValue.value_boolean, String) == str(value),
                            cast(CaseFieldValue.value_json, String).contains(str(value)),
                        ),
                    )
                )
            )
    sort_field, _, direction = sort.partition(":")
    allowed_sort = {
        "case_number": Case.case_number,
        "title": Case.title,
        "created_at": Case.created_at,
        "updated_at": Case.updated_at,
    }
    column = allowed_sort.get(sort_field, Case.updated_at)
    query = query.order_by(column.asc() if direction == "asc" else column.desc())
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = list(db.scalars(query.offset((page - 1) * page_size).limit(page_size)))
    environments_by_id = {
        row.id: row.name_he for row in db.scalars(select(Environment).where(Environment.id.in_({x.environment_id for x in rows})))
    } if rows else {}
    request_types_by_id = {
        row.id: row.name_he for row in db.scalars(select(RequestType).where(RequestType.id.in_({x.request_type_id for x in rows})))
    } if rows else {}
    statuses_by_id = {
        row.id: row.label_he for row in db.scalars(select(WorkflowStatus).where(WorkflowStatus.id.in_({x.workflow_status_id for x in rows if x.workflow_status_id})))
    } if rows else {}
    priorities_by_id = {
        row.id: row.label_he for row in db.scalars(select(PriorityDefinition).where(PriorityDefinition.id.in_({x.priority_id for x in rows if x.priority_id})))
    } if rows else {}
    return {
        "items": [
            {
                "id": row.id,
                "case_number": row.case_number,
                "title": row.title,
                "environment": environments_by_id.get(row.environment_id, ""),
                "request_type": request_types_by_id.get(row.request_type_id, ""),
                "status": statuses_by_id.get(row.workflow_status_id, "") if row.workflow_status_id else "",
                "priority": priorities_by_id.get(row.priority_id, row.priority) if row.priority_id else row.priority,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "can_view_assigned_cases": can_view_assigned,
    }


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
    can_override_lock = user.is_system_admin or "environment.manage" in granted
    reporter = db.get(User, item.reporter_id)
    environment = db.get(Environment, item.environment_id)
    return CaseOut.model_validate(item).model_copy(
        update={
            "reporter_name": reporter.display_name if reporter else None,
            "reporter_email": reporter.email if reporter else None,
            "environment_name": environment.name_he if environment else None,
            "comments": [CommentOut.model_validate(c) for c in visible_comments],
            "permissions": {
                "can_edit": "case.update" in granted and (not item.is_locked or can_override_lock),
                "can_lock": can_override_lock,
                "can_assign": "case.assign" in granted,
                "can_change_status": ("case.change_status" in granted or "case.update" in granted) and (not item.is_locked or can_override_lock),
                "can_manage_participants": "case.manage_participants" in granted and (not item.is_locked or can_override_lock),
                "can_transfer": "case.transfer_environment" in granted and (not item.is_locked or can_override_lock),
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
    granted = permissions(db, user, item.environment_id)
    if item.is_locked and not (user.is_system_admin or "environment.manage" in granted):
        raise HTTPException(403, "הקריאה נעולה; רק מנהל מערכת או מנהל הסביבה רשאי לערוך אותה")
    if item.version != data.version:
        raise HTTPException(409, "Case was updated by another user")
    changes = data.model_dump(exclude={"version", "values"}, exclude_unset=True)
    if data.request_type_id and data.request_type_id != item.request_type_id:
        current_type = db.get(RequestType, item.request_type_id)
        target_type = db.get(RequestType, data.request_type_id)
        if not target_type or target_type.environment_id != item.environment_id or not target_type.is_active:
            raise HTTPException(422, "סוג הקריאה אינו פעיל באותה סביבת עבודה")
        if not current_type or target_type.workflow_definition_id != current_type.workflow_definition_id:
            raise HTTPException(409, "לא ניתן לשנות לסוג קריאה עם תהליך עבודה שונה")
        if target_type.form_version_id != item.form_definition_id:
            raise HTTPException(409, "לא ניתן לשנות לסוג קריאה עם טופס שונה בלי תהליך המרה מפורש")
        if target_type.requires_approval != current_type.requires_approval:
            raise HTTPException(409, "לא ניתן לשנות לסוג קריאה עם מדיניות אישורים שונה")
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
            if not field.is_active or field.is_read_only:
                raise HTTPException(422, "השדה הדינמי אינו זמין לעריכה")
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
    granted = permissions(db, user, item.environment_id)
    if not user.is_system_admin and "environment.manage" not in granted:
        raise HTTPException(403, "רק מנהל מערכת או מנהל הסביבה רשאי לנעול קריאה")
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
    granted = permissions(db, user, item.environment_id)
    if item.is_locked and not (user.is_system_admin or "environment.manage" in granted):
        raise HTTPException(403, "הקריאה נעולה; רק מנהל מערכת או מנהל הסביבה רשאי לשנות מטפל")
    if item.version != data.version:
        raise HTTPException(409, "Case was updated by another user")
    if data.assignee_id:
        candidate = db.get(User, data.assignee_id)
        membership = db.scalar(select(EnvironmentMembership.id).where(
            EnvironmentMembership.environment_id == item.environment_id,
            EnvironmentMembership.user_id == data.assignee_id,
            EnvironmentMembership.is_active.is_(True)))
        if not candidate or candidate.status != "active" or not candidate.is_active or not membership:
            raise HTTPException(422, "ניתן לשייך רק משתמש פעיל המשויך לסביבת הקריאה")
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


@router.get("/environments/{environment_id}/eligible-assignees")
def eligible_assignees(environment_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    require(db, user, environment_id, "case.assign")
    rows = db.scalars(select(User).join(EnvironmentMembership,
        EnvironmentMembership.user_id == User.id).where(
        EnvironmentMembership.environment_id == environment_id,
        EnvironmentMembership.is_active.is_(True), User.is_active.is_(True),
        User.status == "active").distinct().order_by(User.display_name))
    return [{"id": row.id, "display_name": row.display_name, "email": row.email} for row in rows]


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
    if rows:
        return [{"id": status.id, "label_he": status.label_he, "transition_id": transition.id,
                 "requires_comment": transition.requires_comment} for transition, status in rows]
    statuses = db.scalars(select(WorkflowStatus).join(
        WorkflowDefinition, WorkflowStatus.workflow_id == WorkflowDefinition.id,
    ).where(
        WorkflowDefinition.environment_id == item.environment_id,
        WorkflowStatus.is_active.is_(True),
        WorkflowStatus.id != item.workflow_status_id,
    ).order_by(WorkflowStatus.sort_order))
    return [{"id": status.id, "label_he": status.label_he, "transition_id": None,
             "requires_comment": False} for status in statuses]


@router.get("/cases/{case_id}/status-options")
def status_options(case_id: uuid.UUID, db: DB, user: Current) -> list[dict[str, Any]]:
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    case_access(db, user, item)
    statuses = list(db.scalars(select(WorkflowStatus).join(
        WorkflowDefinition, WorkflowStatus.workflow_id == WorkflowDefinition.id,
    ).where(
        WorkflowDefinition.environment_id == item.environment_id,
        WorkflowStatus.is_active.is_(True),
    ).order_by(WorkflowStatus.sort_order)))
    allowed_rows = db.execute(select(WorkflowTransition).where(
        WorkflowTransition.from_status_id == item.workflow_status_id,
        WorkflowTransition.is_active.is_(True),
    )).scalars().all()
    allowed_ids = {row.to_status_id for row in allowed_rows}
    unrestricted = not allowed_ids
    can_change = "case.change_status" in permissions(db, user, item.environment_id)
    return [{
        "id": str(status.id),
        "label_he": status.label_he,
        "current": status.id == item.workflow_status_id,
        "allowed": can_change and status.id != item.workflow_status_id and (unrestricted or status.id in allowed_ids),
        "reason": None if can_change and status.id != item.workflow_status_id and (unrestricted or status.id in allowed_ids) else (
            "זהו הסטטוס הנוכחי" if status.id == item.workflow_status_id
            else "לא ניתן לעבור ישירות מהסטטוס הנוכחי"
        ),
    } for status in statuses]


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
    if item.is_locked and not (user.is_system_admin or "environment.manage" in permissions(db, user, item.environment_id)):
        raise HTTPException(403, "הקריאה נעולה לשינוי משתתפים")
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
    if item.is_locked and not (user.is_system_admin or "environment.manage" in permissions(db, user, item.environment_id)):
        raise HTTPException(403, "הקריאה נעולה לשינוי משתתפים")
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
    if item.is_locked and not (user.is_system_admin or "environment.manage" in permissions(db, user, item.environment_id)):
        raise HTTPException(403, "הקריאה נעולה לשינוי סטטוס")
    transition_row = db.scalar(select(WorkflowTransition).where(
        WorkflowTransition.from_status_id == item.workflow_status_id,
        WorkflowTransition.to_status_id == data.workflow_status_id,
        WorkflowTransition.is_active.is_(True),
    ))
    target = db.get(WorkflowStatus, data.workflow_status_id)
    configured_transitions = db.scalar(select(func.count()).select_from(WorkflowTransition).where(
        WorkflowTransition.from_status_id == item.workflow_status_id,
        WorkflowTransition.is_active.is_(True),
    ))
    if (configured_transitions and not transition_row) or not target or not target.is_active:
        raise HTTPException(409, "מעבר הסטטוס אינו חוקי בתהליך העבודה")
    current_status = db.get(WorkflowStatus, item.workflow_status_id)
    if not current_status or target.workflow_id != current_status.workflow_id:
        raise HTTPException(409, "סטטוס היעד אינו שייך לסביבה")
    if transition_row and transition_row.required_permission_code:
        require(db, user, item.environment_id, transition_row.required_permission_code)
    if transition_row and transition_row.requires_comment and not (data.comment or "").strip():
        raise HTTPException(422, "המעבר מחייב הערה")
    before = item.workflow_status_id
    item.workflow_status_id = target.id
    item.version += 1
    if target.is_closed:
        item.closed_at = datetime.now(UTC)
    db.add(CaseStatusHistory(case_id=item.id, from_status_id=before, to_status_id=target.id,
                             transition_id=transition_row.id if transition_row else None, changed_by=user.id,
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
