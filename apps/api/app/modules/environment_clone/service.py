# mypy: disable-error-code="assignment,attr-defined,union-attr"
import uuid
from pathlib import Path
from shutil import copy2
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import (
    ApprovalFlowDefinition,
    ApprovalStepDefinition,
    AutomationRule,
    CaseFieldDefinition,
    Environment,
    EnvironmentMembership,
    EnvironmentUserField,
    FieldDefinition,
    FormDefinition,
    KnowledgeChunk,
    KnowledgeDocument,
    PriorityDefinition,
    RequestType,
    SubPriorityDefinition,
    UserFieldDefinition,
)
from app.modules.numbering.service import NumberingService
from app.modules.operations.models import SlaPolicy, WorkflowDefinition, WorkflowStatus, WorkflowTransition


def _values(row: Any, *excluded: str) -> dict[str, Any]:
    blocked = {"id", "created_at", "updated_at", *excluded}
    return {column.name: getattr(row, column.name) for column in row.__table__.columns if column.name not in blocked}


def clone_configuration(db: Session, source: Environment, target: Environment, actor_id: uuid.UUID,
                        copy_memberships: bool = False, copy_knowledge: bool = False) -> dict[str, int]:
    counts: dict[str, int] = {}
    priority_map: dict[uuid.UUID, uuid.UUID] = {}
    sub_map: dict[uuid.UUID, uuid.UUID] = {}
    workflow_map: dict[uuid.UUID, uuid.UUID] = {}
    status_map: dict[uuid.UUID, uuid.UUID] = {}
    request_map: dict[uuid.UUID, uuid.UUID] = {}

    for row in db.scalars(select(PriorityDefinition).where(PriorityDefinition.environment_id == source.id)):
        item = PriorityDefinition(**_values(row, "environment_id", "system_number"), environment_id=target.id,
                                  system_number=NumberingService.next(db, "priority", target.id))
        db.add(item); db.flush(); priority_map[row.id] = item.id
    for row in db.scalars(select(SubPriorityDefinition).where(SubPriorityDefinition.environment_id == source.id)):
        item = SubPriorityDefinition(**_values(row, "environment_id", "priority_id", "system_number"),
            environment_id=target.id, priority_id=priority_map.get(row.priority_id),
            system_number=NumberingService.next(db, "sub_priority", target.id))
        db.add(item); db.flush(); sub_map[row.id] = item.id
    counts["priorities"] = len(priority_map); counts["sub_priorities"] = len(sub_map)

    for row in db.scalars(select(WorkflowDefinition).where(WorkflowDefinition.environment_id == source.id)):
        item = WorkflowDefinition(**_values(row, "environment_id", "system_number", "created_by"),
            environment_id=target.id, system_number=f"WF-{uuid.uuid4().hex[:8].upper()}", created_by=actor_id)
        db.add(item); db.flush(); workflow_map[row.id] = item.id
    for row in db.scalars(select(WorkflowStatus).where(WorkflowStatus.workflow_id.in_(workflow_map))):
        item = WorkflowStatus(**_values(row, "workflow_id"), workflow_id=workflow_map[row.workflow_id])
        db.add(item); db.flush(); status_map[row.id] = item.id
    for row in db.scalars(select(WorkflowTransition).where(WorkflowTransition.workflow_id.in_(workflow_map))):
        db.add(WorkflowTransition(**_values(row, "workflow_id", "from_status_id", "to_status_id"),
            workflow_id=workflow_map[row.workflow_id], from_status_id=status_map[row.from_status_id],
            to_status_id=status_map[row.to_status_id]))
    counts["statuses"] = len(status_map)

    source_requests = list(db.scalars(select(RequestType).where(RequestType.environment_id == source.id)))
    for row in source_requests:
        item = RequestType(**_values(row, "environment_id", "system_number", "form_version_id",
            "workflow_definition_id", "default_priority_id", "default_sub_priority_id"),
            environment_id=target.id, system_number=NumberingService.next(db, "request_type", target.id),
            form_version_id=None, workflow_definition_id=workflow_map.get(row.workflow_definition_id),
            default_priority_id=priority_map.get(row.default_priority_id),
            default_sub_priority_id=sub_map.get(row.default_sub_priority_id))
        db.add(item); db.flush(); request_map[row.id] = item.id
    for old_request in source_requests:
        for form in db.scalars(select(FormDefinition).where(FormDefinition.request_type_id == old_request.id)):
            copied_form = FormDefinition(**_values(form, "request_type_id", "published_at"),
                                         request_type_id=request_map[old_request.id], published_at=form.published_at)
            db.add(copied_form); db.flush()
            for field in db.scalars(select(FieldDefinition).where(FieldDefinition.form_definition_id == form.id)):
                db.add(FieldDefinition(**_values(field, "form_definition_id"), form_definition_id=copied_form.id))
            if old_request.form_version_id == form.id:
                db.get(RequestType, request_map[old_request.id]).form_version_id = copied_form.id
    counts["request_types"] = len(request_map)

    for row in db.scalars(select(UserFieldDefinition).where(
        UserFieldDefinition.scope == "environment", UserFieldDefinition.environment_id == source.id)):
        item = UserFieldDefinition(**_values(row, "environment_id", "system_number"),
            environment_id=target.id, system_number=NumberingService.next(db, "user_field", target.id))
        db.add(item); db.flush()
        selection = db.get(EnvironmentUserField, (source.id, row.id))
        if selection:
            db.add(EnvironmentUserField(**_values(selection, "environment_id", "user_field_definition_id"),
                environment_id=target.id, user_field_definition_id=item.id))

    for row in db.scalars(select(CaseFieldDefinition).where(CaseFieldDefinition.environment_id == source.id)):
        db.add(CaseFieldDefinition(**_values(row, "environment_id", "request_type_id", "system_number", "created_by"),
            environment_id=target.id, request_type_id=request_map.get(row.request_type_id), created_by=actor_id,
            system_number=NumberingService.next(db, "case_field", target.id)))
    for row in db.scalars(select(AutomationRule).where(AutomationRule.environment_id == source.id)):
        db.add(AutomationRule(**_values(row, "environment_id", "system_number", "created_by"),
            environment_id=target.id, created_by=actor_id,
            system_number=NumberingService.next(db, "automation_rule", target.id)))
    for row in db.scalars(select(SlaPolicy).where(SlaPolicy.environment_id == source.id)):
        db.add(SlaPolicy(**_values(row, "environment_id", "request_type_id", "priority_id", "system_number"),
            environment_id=target.id, request_type_id=request_map.get(row.request_type_id),
            priority_id=priority_map.get(row.priority_id), system_number=f"SLA-{uuid.uuid4().hex[:8].upper()}"))

    flow_map: dict[uuid.UUID, uuid.UUID] = {}
    for row in db.scalars(select(ApprovalFlowDefinition).where(ApprovalFlowDefinition.environment_id == source.id)):
        item = ApprovalFlowDefinition(**_values(row, "environment_id", "request_type_id", "system_number", "created_by"),
            environment_id=target.id, request_type_id=request_map.get(row.request_type_id), created_by=actor_id,
            system_number=NumberingService.next(db, "approval_flow", target.id))
        db.add(item); db.flush(); flow_map[row.id] = item.id
    for row in db.scalars(select(ApprovalStepDefinition).where(ApprovalStepDefinition.approval_flow_id.in_(flow_map))):
        db.add(ApprovalStepDefinition(**_values(row, "approval_flow_id"), approval_flow_id=flow_map[row.approval_flow_id]))

    if copy_memberships:
        for row in db.scalars(select(EnvironmentMembership).where(EnvironmentMembership.environment_id == source.id)):
            db.add(EnvironmentMembership(**_values(row, "environment_id"), environment_id=target.id))
    counts["memberships"] = len(list(db.scalars(select(EnvironmentMembership).where(EnvironmentMembership.environment_id == target.id))))

    if copy_knowledge:
        for row in db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.environment_id == source.id)):
            new_path = str(Path(row.storage_path).with_name(f"{uuid.uuid4().hex}-{Path(row.storage_path).name}"))
            if Path(row.storage_path).exists(): copy2(row.storage_path, new_path)
            document = KnowledgeDocument(**_values(row, "environment_id", "storage_path", "uploaded_at"),
                environment_id=target.id, storage_path=new_path, uploaded_at=row.uploaded_at)
            db.add(document); db.flush()
            for chunk in db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id == row.id)):
                db.add(KnowledgeChunk(**_values(chunk, "document_id", "environment_id"),
                    document_id=document.id, environment_id=target.id))
    return counts
