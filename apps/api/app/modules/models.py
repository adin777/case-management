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
    password_hash: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class GroupMember(Base):
    __tablename__ = "group_members"
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)


class Environment(TimestampMixin, Base):
    __tablename__ = "environments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)
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
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    __table_args__ = (UniqueConstraint("environment_id", "user_id", "role_id"),)


class RequestType(TimestampMixin, Base):
    __tablename__ = "request_types"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(80))
    name_he: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    form_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
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
    sort_order: Mapped[int] = mapped_column(Integer)
    configuration_json: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("form_definition_id", "key"),)


class Case(TimestampMixin, Base):
    __tablename__ = "cases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id"))
    request_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("request_types.id"))
    form_definition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("form_definitions.id"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, native_enum=False), default=CaseStatus.submitted
    )
    priority: Mapped[str] = mapped_column(String(30), default="normal")
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    requester_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    assigned_group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("groups.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
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
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
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
