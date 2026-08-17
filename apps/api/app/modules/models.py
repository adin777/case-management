import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

UUID = Uuid


class FormStatus(str, enum.Enum):
    draft = "draft"
    published = "published"


class CaseStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    assigned = "assigned"
    in_progress = "in_progress"
    waiting_for_requester = "waiting_for_requester"
    resolved = "resolved"
    closed = "closed"
    cancelled = "cancelled"


class Visibility(str, enum.Enum):
    public = "public"
    internal = "internal"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    first_name: Mapped[str | None] = mapped_column(String(120))
    last_name: Mapped[str | None] = mapped_column(String(120))
    user_principal_name: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    department: Mapped[str | None] = mapped_column(String(200), index=True)
    job_title: Mapped[str | None] = mapped_column(String(200), index=True)
    phone: Mapped[str | None] = mapped_column(String(80))
    mobile_phone: Mapped[str | None] = mapped_column(String(80))
    employee_id: Mapped[str | None] = mapped_column(String(120), index=True)
    computer_identifier: Mapped[str | None] = mapped_column(String(200))
    directory_object_id: Mapped[str | None] = mapped_column(String(200), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(30), default="manual", index=True)
    directory_enabled: Mapped[bool | None] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_directory_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_hash: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    employee_record_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("employees.id"), unique=True)


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str | None] = mapped_column(String(120))
    last_name: Mapped[str | None] = mapped_column(String(120))
    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    department: Mapped[str | None] = mapped_column(String(200), index=True)
    job_title: Mapped[str | None] = mapped_column(String(200), index=True)
    phone: Mapped[str | None] = mapped_column(String(80))
    mobile_phone: Mapped[str | None] = mapped_column(String(80))
    employee_number: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    computer_identifier: Mapped[str | None] = mapped_column(String(200))
    directory_object_id: Mapped[str | None] = mapped_column(String(200), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(30), default="manual")
    directory_data_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="active")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Group(TimestampMixin, Base):
    __tablename__ = "groups"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system_admin_group: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    __table_args__ = (Index("ux_groups_name_ci", func.lower(name), unique=True),)


class GroupMember(Base):
    __tablename__ = "group_members"
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    added_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    name_he: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    description_he: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(20), default="environment")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Permission(Base):
    __tablename__ = "permissions"
    code: Mapped[str] = mapped_column(String(120), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    name_he: Mapped[str | None] = mapped_column(String(160))
    description_he: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    scope: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_code: Mapped[str] = mapped_column(
        ForeignKey("permissions.code", ondelete="CASCADE"), primary_key=True
    )


class GroupEnvironmentRole(Base):
    __tablename__ = "group_environment_roles"
    environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), primary_key=True)


class Environment(TimestampMixin, Base):
    __tablename__ = "environments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    system_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    name_he: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EnvironmentMembership(Base):
    __tablename__ = "environment_memberships"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    role_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roles.id"))
    source: Mapped[str] = mapped_column(String(30), default="manual")
    source_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_environment_manager: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    __table_args__ = (UniqueConstraint("environment_id", "user_id", "role_id"),)


class DirectorySyncRun(Base):
    __tablename__ = "directory_sync_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    disabled_count: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    delta_reference: Mapped[str | None] = mapped_column(Text)
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    error_summary: Mapped[str | None] = mapped_column(Text)


class EnvironmentAssignmentRule(TimestampMixin, Base):
    __tablename__ = "environment_assignment_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    conditions_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class RequestType(TimestampMixin, Base):
    __tablename__ = "request_types"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(80))
    name_he: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    form_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    default_priority_id: Mapped[uuid.UUID | None]
    default_sub_priority_id: Mapped[uuid.UUID | None]
    default_assignee_user_id: Mapped[uuid.UUID | None]
    default_assignee_group_id: Mapped[uuid.UUID | None]
    workflow_definition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    __table_args__ = (UniqueConstraint("environment_id", "code"),)


class FormDefinition(Base):
    __tablename__ = "form_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("request_types.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[FormStatus] = mapped_column(Enum(FormStatus, native_enum=False), default=FormStatus.draft)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fields: Mapped[list["FieldDefinition"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="FieldDefinition.sort_order"
    )
    __table_args__ = (UniqueConstraint("request_type_id", "version"),)


class FieldDefinition(Base):
    __tablename__ = "field_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    form_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("form_definitions.id", ondelete="CASCADE")
    )
    key: Mapped[str] = mapped_column(String(80))
    label_he: Mapped[str] = mapped_column(String(200))
    label_en: Mapped[str] = mapped_column(String(200))
    field_type: Mapped[str] = mapped_column(String(40))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer)
    configuration_json: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("form_definition_id", "key"),)


class Case(TimestampMixin, Base):
    __tablename__ = "cases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id"))
    request_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("request_types.id"))
    form_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("form_definitions.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, native_enum=False), default=CaseStatus.submitted
    )
    priority: Mapped[str] = mapped_column(String(30), default="normal")
    priority_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("priority_definitions.id"))
    sub_priority_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sub_priority_definitions.id"))
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    requester_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    assigned_group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("groups.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    lock_reason: Mapped[str | None] = mapped_column(Text)
    workflow_status_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    sla_policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_response_status: Mapped[str] = mapped_column(String(30), default="not_started")
    sla_resolution_status: Mapped[str] = mapped_column(String(30), default="not_started")
    approval_status: Mapped[str] = mapped_column(String(30), default="not_started")
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_summary: Mapped[str | None] = mapped_column(Text)
    values: Mapped[list["CaseFieldValue"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    comments: Mapped[list["Comment"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class CaseFieldValue(Base):
    __tablename__ = "case_field_values"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    field_definition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("field_definitions.id"))
    value_text: Mapped[str | None] = mapped_column(Text)
    value_number: Mapped[Decimal | None] = mapped_column(Numeric)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean)
    value_date: Mapped[date | None] = mapped_column(Date)
    value_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    value_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    value_json: Mapped[dict | list | None] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("case_id", "field_definition_id"),)


class CaseParticipant(Base):
    __tablename__ = "case_participants"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    participant_type: Mapped[str] = mapped_column(String(30), primary_key=True)
    added_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    visibility: Mapped[Visibility] = mapped_column(Enum(Visibility, native_enum=False))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(80))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id"))
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    actor_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    actor_email_snapshot: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseNumberCounter(Base):
    __tablename__ = "case_number_counters"
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class UserFieldDefinition(TimestampMixin, Base):
    __tablename__ = "user_field_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    label_he: Mapped[str] = mapped_column(String(200))
    label_en: Mapped[str] = mapped_column(String(200))
    field_type: Mapped[str] = mapped_column(String(40))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    options_json: Mapped[list | dict] = mapped_column(JSON, default=list)
    default_value_json: Mapped[dict | list | str | int | bool | None] = mapped_column(JSON)
    validation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    scope: Mapped[str] = mapped_column(String(20), default="global")
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id"))


class UserFieldValue(Base):
    __tablename__ = "user_field_values"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_field_definitions.id", ondelete="CASCADE"), primary_key=True
    )
    value_json: Mapped[dict | list | str | int | bool | None] = mapped_column(JSON)


class EnvironmentUserField(Base):
    __tablename__ = "environment_user_fields"
    environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="CASCADE"), primary_key=True
    )
    user_field_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_field_definitions.id", ondelete="CASCADE"), primary_key=True
    )
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_editable_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    is_editable_by_environment_admin: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class AutomationRule(TimestampMixin, Base):
    __tablename__ = "automation_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_type: Mapped[str] = mapped_column(String(60))
    conditions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    actions_json: Mapped[list] = mapped_column(JSON, default=list)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class GlobalStatusDefinition(TimestampMixin, Base):
    __tablename__ = "global_status_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    label_he: Mapped[str] = mapped_column(String(200))
    label_en: Mapped[str | None] = mapped_column(String(200))
    semantic_category: Mapped[str] = mapped_column(String(30), default="open")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str | None] = mapped_column(String(20))


class GlobalPriorityDefinition(TimestampMixin, Base):
    __tablename__ = "global_priority_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    label_he: Mapped[str] = mapped_column(String(200))
    label_en: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str | None] = mapped_column(String(20))


class GlobalSubPriorityDefinition(TimestampMixin, Base):
    __tablename__ = "global_sub_priority_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    label_he: Mapped[str] = mapped_column(String(200))
    label_en: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str | None] = mapped_column(String(20))


class PriorityDefinition(Base):
    __tablename__ = "priority_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(40))
    label_he: Mapped[str] = mapped_column(String(100))
    label_en: Mapped[str | None] = mapped_column(String(100), default="")
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(20), default="#64748b")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("environment_id", "code"),)


class SubPriorityDefinition(Base):
    __tablename__ = "sub_priority_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id"), index=True)
    priority_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("priority_definitions.id"))
    code: Mapped[str] = mapped_column(String(40))
    label_he: Mapped[str] = mapped_column(String(100))
    label_en: Mapped[str | None] = mapped_column(String(100), default="")
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(20), default="#64748b")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("priority_id", "code"),)


class NumberingSeries(TimestampMixin, Base):
    __tablename__ = "numbering_series"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(40))
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id"))
    prefix: Mapped[str] = mapped_column(String(20))
    next_number: Mapped[int] = mapped_column(Integer, default=1)
    padding: Mapped[int] = mapped_column(Integer, default=6)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("entity_type", "environment_id"),)


class CaseFieldDefinition(TimestampMixin, Base):
    __tablename__ = "case_field_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str] = mapped_column(String(40), unique=True)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    request_type_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("request_types.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(80))
    label_he: Mapped[str] = mapped_column(String(200))
    label_en: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str | None] = mapped_column(Text)
    field_type: Mapped[str] = mapped_column(String(40))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    options_json: Mapped[list] = mapped_column(JSON, default=list)
    default_value_json: Mapped[dict | list | str | int | bool | None] = mapped_column(JSON)
    validation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("environment_id", "request_type_id", "key"),)


class GlobalCaseFieldDefinition(TimestampMixin, Base):
    __tablename__ = "global_case_field_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    label_he: Mapped[str] = mapped_column(String(200))
    label_en: Mapped[str] = mapped_column(String(200), default="")
    field_type: Mapped[str] = mapped_column(String(40))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    configuration_json: Mapped[dict] = mapped_column(JSON, default=dict)
    semantic_binding: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)


class EnvironmentGlobalCaseField(Base):
    __tablename__ = "environment_global_case_fields"
    environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="CASCADE"), primary_key=True)
    global_field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("global_case_field_definitions.id", ondelete="CASCADE"), primary_key=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    show_on_create: Mapped[bool] = mapped_column(Boolean, default=True)
    show_on_edit: Mapped[bool] = mapped_column(Boolean, default=True)


class GlobalCaseFieldValue(Base):
    __tablename__ = "global_case_field_values"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    global_field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("global_case_field_definitions.id"), primary_key=True)
    value_json: Mapped[dict | list | str | int | bool | None] = mapped_column(JSON)


class UserImportSession(TimestampMixin, Base):
    __tablename__ = "user_import_sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    snapshot_json: Mapped[list] = mapped_column(JSON, default=list)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserPermissionAssignment(TimestampMixin, Base):
    __tablename__ = "user_permission_assignments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    permission_code: Mapped[str] = mapped_column(ForeignKey("permissions.code", ondelete="CASCADE"))
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("user_id", "permission_code", "environment_id"),)


class GroupPermissionAssignment(TimestampMixin, Base):
    __tablename__ = "group_permission_assignments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    permission_code: Mapped[str] = mapped_column(ForeignKey("permissions.code", ondelete="CASCADE"))
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("group_id", "permission_code", "environment_id"),)


class AutomationExecutionLog(Base):
    __tablename__ = "automation_execution_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("automation_rules.id", ondelete="CASCADE"))
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    trigger_type: Mapped[str] = mapped_column(String(60))
    matched: Mapped[bool] = mapped_column(Boolean)
    actions_executed: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApprovalFlowDefinition(TimestampMixin, Base):
    __tablename__ = "approval_flow_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str] = mapped_column(String(40), unique=True)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    request_type_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("request_types.id"))
    trigger_type: Mapped[str] = mapped_column(String(60), default="case_created")
    approval_policy: Mapped[str] = mapped_column(String(40), default="all_active_steps")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class ApprovalStepDefinition(Base):
    __tablename__ = "approval_step_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_flow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approval_flow_definitions.id", ondelete="CASCADE"))
    step_order: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200))
    approver_type: Mapped[str] = mapped_column(String(40))
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approver_group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("groups.id"))
    approver_field_key: Mapped[str | None] = mapped_column(String(80))
    approver_environment_role: Mapped[str | None] = mapped_column(String(80))
    approver_job_title: Mapped[str | None] = mapped_column(String(200))
    approver_user_field_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approver_case_field_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    required_approvals: Mapped[int] = mapped_column(Integer, default=1)
    approval_mode: Mapped[str] = mapped_column(String(30), default="any")
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_reject: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_return: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout_hours: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("approval_flow_id", "step_order"),)


class ApprovalInstance(Base):
    __tablename__ = "approval_instances"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_number: Mapped[str] = mapped_column(String(40), unique=True)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    approval_flow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approval_flow_definitions.id"))
    request_type_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("request_types.id"))
    approval_policy: Mapped[str] = mapped_column(String(40), default="all_active_steps")
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    current_step_order: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalTask(Base):
    __tablename__ = "approval_tasks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_instance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approval_instances.id", ondelete="CASCADE"))
    step_definition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approval_step_definitions.id"))
    approver_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    approver_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    decision: Mapped[str | None] = mapped_column(String(30))
    comment: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CaseTransferHistory(Base):
    __tablename__ = "case_transfer_histories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    from_environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id"))
    to_environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id"))
    from_request_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("request_types.id"))
    to_request_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("request_types.id"))
    from_status_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    to_status_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    transferred_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    transferred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    removed_participants: Mapped[list] = mapped_column(JSON, default=list)
    removed_assignee: Mapped[dict | None] = mapped_column(JSON)
    removed_fields_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    new_values: Mapped[list] = mapped_column(JSON, default=list)
    approval_effect: Mapped[dict] = mapped_column(JSON, default=dict)
    sla_effect: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(Text)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    size: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(500), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    embedding_json: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)
