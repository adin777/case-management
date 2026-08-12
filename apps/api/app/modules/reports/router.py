import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select

from app.modules.access.service import EffectivePermissionService, domain_permissions
from app.modules.api import DB, Current
from app.modules.models import (
    ApprovalInstance,
    ApprovalStepDefinition,
    ApprovalTask,
    AuditEvent,
    Case,
    Environment,
    EnvironmentMembership,
    Group,
    GroupMember,
    RequestType,
    User,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])
REPORTS = [
    ("cases", "דוח קריאות שירות", "report.cases"),
    ("approvals", "דוח אישורים", "report.approvals"),
    ("users", "דוח משתמשים והרשאות", "report.users"),
    ("audit", "דוח Audit", "report.audit"),
]


def allowed(db: DB, user: Current, permission: str, environment_id: uuid.UUID | None = None) -> bool:
    return user.is_system_admin or permission in domain_permissions(db, user.id, environment_id)


def guard(db: DB, user: Current, permission: str, environment_id: uuid.UUID | None = None) -> None:
    if not allowed(db, user, permission, environment_id):
        raise HTTPException(403, "אין הרשאה לצפות בדוח")


@router.get("/available")
def available(db: DB, user: Current) -> list[dict[str, str]]:
    permissions = domain_permissions(db, user.id, None)
    return [
        {"code": code, "name": name, "permission": permission}
        for code, name, permission in REPORTS
        if user.is_system_admin or permission in permissions
    ]


@router.get("/approvals")
def approvals(
    db: DB,
    user: Current,
    environment_id: uuid.UUID | None = None,
    case_number: str | None = None,
    subject: str | None = None,
    request_type_id: uuid.UUID | None = None,
    approver_id: uuid.UUID | None = None,
    step: str | None = None,
    status: str | None = None,
    requested_from: datetime | None = None,
    requested_to: datetime | None = None,
    decided_from: datetime | None = None,
    decided_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    guard(db, user, "report.approvals", environment_id)
    query = (
        select(ApprovalTask, ApprovalInstance, ApprovalStepDefinition, Case, Environment, RequestType)
        .join(ApprovalInstance, ApprovalTask.approval_instance_id == ApprovalInstance.id)
        .join(ApprovalStepDefinition, ApprovalTask.step_definition_id == ApprovalStepDefinition.id)
        .join(Case, ApprovalInstance.case_id == Case.id)
        .join(Environment, Case.environment_id == Environment.id)
        .join(RequestType, Case.request_type_id == RequestType.id)
    )
    if environment_id:
        query = query.where(Case.environment_id == environment_id)
    if case_number:
        query = query.where(Case.case_number.ilike(f"%{case_number}%"))
    if subject:
        query = query.where(Case.title.ilike(f"%{subject}%"))
    if request_type_id:
        query = query.where(Case.request_type_id == request_type_id)
    if approver_id:
        query = query.where(ApprovalTask.approver_user_id == approver_id)
    if step:
        query = query.where(ApprovalStepDefinition.name.ilike(f"%{step}%"))
    if status:
        query = query.where(ApprovalTask.status == status)
    if requested_from:
        query = query.where(ApprovalInstance.started_at >= requested_from)
    if requested_to:
        query = query.where(ApprovalInstance.started_at <= requested_to)
    if decided_from:
        query = query.where(ApprovalTask.decided_at >= decided_from)
    if decided_to:
        query = query.where(ApprovalTask.decided_at <= decided_to)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(ApprovalInstance.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [
        {
            "task_id": str(task.id),
            "case_number": case.case_number,
            "subject": case.title,
            "environment": env.name_he,
            "request_type": request_type.name_he,
            "approver": task.approver_name_snapshot,
            "step": step_row.name,
            "status": task.status,
            "requested_at": instance.started_at,
            "decided_at": task.decided_at,
            "comment": task.comment,
            "can_decide": task.status == "pending" and task.approver_user_id == user.id,
        }
        for task, instance, step_row, case, env, request_type in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/users")
def users(
    db: DB,
    user: Current,
    search: str | None = None,
    status: str | None = None,
    source: str | None = None,
    department: str | None = None,
    job_title: str | None = None,
    group_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    environment_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    guard(db, user, "report.users")
    query = select(User)
    if search:
        query = query.where(or_(User.display_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    if status:
        query = query.where(User.status == status)
    if source:
        query = query.where(User.source == source)
    if department:
        query = query.where(User.department == department)
    if job_title:
        query = query.where(User.job_title == job_title)
    for group_id in group_ids or []:
        query = query.where(User.id.in_(select(GroupMember.user_id).where(GroupMember.group_id == group_id)))
    if environment_id:
        query = query.where(
            User.id.in_(
                select(EnvironmentMembership.user_id).where(
                    EnvironmentMembership.environment_id == environment_id,
                    EnvironmentMembership.is_active.is_(True),
                )
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = []
    for row in db.scalars(query.order_by(User.display_name).offset((page - 1) * page_size).limit(page_size)):
        groups = db.scalars(select(Group.name).join(GroupMember).where(GroupMember.user_id == row.id)).all()
        envs = db.scalars(
            select(Environment.name_he)
            .join(EnvironmentMembership)
            .where(EnvironmentMembership.user_id == row.id, EnvironmentMembership.is_active.is_(True))
        ).all()
        permissions = [
            item["domain_name"]
            for item in EffectivePermissionService(db).explain_all(row, None)
            if item["effective_level"] != "none"
        ]
        items.append(
            {
                "user": row.display_name,
                "email": row.email,
                "status": row.status,
                "source": row.source,
                "department": row.department,
                "job_title": row.job_title,
                "groups": ", ".join(groups),
                "environments": ", ".join(envs),
                "permissions": ", ".join(permissions),
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/audit")
def audit_report(
    db: DB,
    user: Current,
    user_id: uuid.UUID | None = None,
    effective_user_id: uuid.UUID | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    environment_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    guard(db, user, "report.audit", environment_id)
    query = select(AuditEvent)
    if user_id:
        query = query.where(AuditEvent.actor_id == user_id)
    if effective_user_id:
        query = query.where(
            AuditEvent.metadata_json["effective_user_id"].as_string() == str(effective_user_id)
        )
    if action:
        query = query.where(AuditEvent.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditEvent.entity_id.ilike(f"%{entity_id}%"))
    if environment_id:
        query = query.where(AuditEvent.environment_id == environment_id)
    if date_from:
        query = query.where(AuditEvent.created_at >= date_from)
    if date_to:
        query = query.where(AuditEvent.created_at <= date_to)
    if search:
        query = query.where(
            or_(
                AuditEvent.action.ilike(f"%{search}%"),
                AuditEvent.entity_type.ilike(f"%{search}%"),
                AuditEvent.entity_id.ilike(f"%{search}%"),
                AuditEvent.actor_name_snapshot.ilike(f"%{search}%"),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [
        {
            "user": row.actor_name_snapshot or row.actor_email_snapshot,
            "action": row.action,
            "entity": row.entity_type,
            "entity_id": row.entity_id,
            "environment_id": str(row.environment_id or ""),
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
