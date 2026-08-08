from fastapi import HTTPException
from sqlalchemy import select
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
    Role,
)
from app.modules.numbering.service import NumberingService
from app.modules.operations.models import Notification


def start_matching_approvals(db: Session, item: Case) -> list[ApprovalInstance]:
    request_type = db.get(RequestType, item.request_type_id)
    if not request_type or not request_type.requires_approval:
        return []
    flows = db.scalars(select(ApprovalFlowDefinition).where(
        ApprovalFlowDefinition.environment_id == item.environment_id,
        ApprovalFlowDefinition.is_active.is_(True),
        ApprovalFlowDefinition.trigger_type == "case_created",
        ApprovalFlowDefinition.request_type_id == item.request_type_id,
    )).all()
    if not flows:
        raise HTTPException(409, "סוג הקריאה דורש אישור אך לא הוגדרה עבורו תצורת אישורים פעילה")
    result = []
    for flow in flows:
        existing = db.scalar(select(ApprovalInstance).where(
            ApprovalInstance.case_id == item.id,
            ApprovalInstance.approval_flow_id == flow.id))
        if existing:
            result.append(existing); continue
        instance = ApprovalInstance(system_number=NumberingService.next(db, "approval_instance", item.environment_id),
                                    case_id=item.id, approval_flow_id=flow.id,
                                    request_type_id=item.request_type_id,
                                    approval_policy=flow.approval_policy,
                                    status="pending", current_step_order=1)
        db.add(instance); db.flush()
        item.approval_status = "pending"
        item.is_approved = False
        create_step_tasks(db, instance, 1)
        result.append(instance)
    return result


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
    elif step.approver_type == "environment_role" and step.approver_environment_role:
        case_item = db.get(Case, instance.case_id)
        if case_item:
            approvers = list(db.scalars(select(EnvironmentMembership.user_id).join(Role).where(
                EnvironmentMembership.environment_id == case_item.environment_id,
                Role.code == step.approver_environment_role,
                EnvironmentMembership.user_id.is_not(None),
            )))
    for approver in dict.fromkeys(approvers):
        db.add(ApprovalTask(approval_instance_id=instance.id, step_definition_id=step.id,
                            approver_user_id=approver, status="pending"))
        db.add(Notification(
            user_id=approver,
            notification_type="approval_requested",
            title_he="ממתינה לך משימת אישור",
            body_he=f"נדרש אישורך בשלב {step.name}",
            entity_type="case",
            entity_id=str(instance.case_id),
        ))
