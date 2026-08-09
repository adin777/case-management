from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.models import (
    ApprovalFlowDefinition,
    ApprovalInstance,
    ApprovalStepDefinition,
    ApprovalTask,
    Case,
    EnvironmentMembership,
    GroupMember,
    RequestType,
    User,
)
from app.modules.numbering.service import NumberingService
from app.modules.operations.models import Notification


def start_matching_approvals(db: Session, item: Case) -> list[ApprovalInstance]:
    request_type = db.get(RequestType, item.request_type_id)
    if not request_type or not request_type.requires_approval:
        return []
    flow = db.scalar(select(ApprovalFlowDefinition).where(
        ApprovalFlowDefinition.environment_id == item.environment_id,
        ApprovalFlowDefinition.is_active.is_(True),
        ApprovalFlowDefinition.trigger_type == "case_created",
        ApprovalFlowDefinition.request_type_id == item.request_type_id,
    ).order_by(ApprovalFlowDefinition.system_number.desc()).limit(1))
    if not flow:
        raise HTTPException(409, "סוג הקריאה דורש אישור אך לא הוגדרה עבורו תצורת אישורים פעילה")
    existing = db.scalar(select(ApprovalInstance).where(
        ApprovalInstance.case_id == item.id,
        ApprovalInstance.approval_flow_id == flow.id))
    if existing:
        return [existing]
    instance = ApprovalInstance(system_number=NumberingService.next(db, "approval_instance", item.environment_id),
                                case_id=item.id, approval_flow_id=flow.id,
                                request_type_id=item.request_type_id,
                                approval_policy=flow.approval_policy,
                                attempt_number=1, status="pending", current_step_order=1)
    db.add(instance); db.flush()
    item.approval_status = "pending"
    item.is_approved = False
    create_step_tasks(db, instance, 1)
    return [instance]


def resubmit_approval(db: Session, item: Case) -> ApprovalInstance:
    latest = db.scalar(select(ApprovalInstance).where(
        ApprovalInstance.case_id == item.id,
    ).order_by(ApprovalInstance.attempt_number.desc(),
               func.coalesce(ApprovalInstance.completed_at, ApprovalInstance.started_at).desc()))
    if not latest or latest.status not in {"rejected", "returned"}:
        raise HTTPException(409, "ניתן לשלוח מחדש רק קריאה שנדחתה או הוחזרה לתיקון")
    pending = db.scalar(select(ApprovalInstance.id).where(
        ApprovalInstance.case_id == item.id, ApprovalInstance.status == "pending"))
    if pending:
        raise HTTPException(409, "כבר קיים ניסיון אישור פעיל לקריאה")
    flow = db.get(ApprovalFlowDefinition, latest.approval_flow_id)
    if not flow or not flow.is_active or flow.request_type_id != item.request_type_id:
        raise HTTPException(409, "תצורת האישור הרלוונטית אינה פעילה עוד")
    instance = ApprovalInstance(
        system_number=NumberingService.next(db, "approval_instance", item.environment_id),
        case_id=item.id, approval_flow_id=flow.id, request_type_id=item.request_type_id,
        approval_policy=flow.approval_policy, attempt_number=latest.attempt_number + 1,
        status="pending", current_step_order=1,
    )
    db.add(instance); db.flush()
    item.approval_status = "pending"; item.is_approved = False
    create_step_tasks(db, instance, 1)
    return instance


def create_step_tasks(db: Session, instance: ApprovalInstance, step_order: int) -> None:
    step = db.scalar(select(ApprovalStepDefinition).where(
        ApprovalStepDefinition.approval_flow_id == instance.approval_flow_id,
        ApprovalStepDefinition.step_order == step_order))
    if not step:
        instance.status = "approved"; return
    approvers = []
    if step.approver_type == "user" and step.approver_user_id:
        approvers = [step.approver_user_id]
    elif step.approver_type == "group" and step.approver_group_id:
        approvers = list(db.scalars(select(GroupMember.user_id).where(
            GroupMember.group_id == step.approver_group_id)))
    elif step.approver_type == "job_title" and step.approver_job_title:
        case_item = db.get(Case, instance.case_id)
        if case_item:
            approvers = list(db.scalars(select(EnvironmentMembership.user_id).join(
                User, EnvironmentMembership.user_id == User.id).where(
                EnvironmentMembership.environment_id == case_item.environment_id,
                EnvironmentMembership.is_active.is_(True),
                EnvironmentMembership.user_id.is_not(None),
                User.status == "active", User.is_active.is_(True),
                User.job_title == step.approver_job_title,
            )))
        if not approvers:
            raise HTTPException(409, f"לא נמצא משתמש פעיל בתפקיד '{step.approver_job_title}' בסביבה זו")
    for approver in dict.fromkeys(approvers):
        approver_user = db.get(User, approver)
        db.add(ApprovalTask(approval_instance_id=instance.id, step_definition_id=step.id,
                            approver_user_id=approver,
                            approver_name_snapshot=approver_user.display_name if approver_user else None,
                            status="pending"))
        db.add(Notification(
            user_id=approver,
            notification_type="approval_requested",
            title_he="ממתינה לך משימת אישור",
            body_he=f"נדרש אישורך בשלב {step.name}",
            entity_type="case",
            entity_id=str(instance.case_id),
        ))
