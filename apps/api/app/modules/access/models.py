import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PermissionDomain(Base):
    __tablename__ = "permission_domains"
    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    name_he: Mapped[str] = mapped_column(String(200))
    description_he: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(30), default="environment")
    view_permissions: Mapped[str] = mapped_column(Text, default="")
    edit_permissions: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AccessLevelAssignment(Base):
    __tablename__ = "access_level_assignments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_code: Mapped[str] = mapped_column(ForeignKey("permission_domains.code"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    access_level: Mapped[str] = mapped_column(String(10))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("domain_code", "user_id", "environment_id"),
        UniqueConstraint("domain_code", "group_id", "environment_id"),
    )
