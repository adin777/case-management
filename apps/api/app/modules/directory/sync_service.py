import secrets
import uuid
from datetime import UTC, datetime

from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.directory.provider import DirectoryBatch, NormalizedDirectoryUser
from app.modules.environment_assignments.service import apply_all_rules
from app.modules.models import DirectorySyncRun, User

password_hash = PasswordHash.recommended()
PROFILE_FIELDS = ("first_name", "last_name", "display_name", "user_principal_name", "department",
                  "job_title", "phone", "mobile_phone", "employee_id", "computer_identifier",
                  "directory_object_id", "directory_enabled")


class UserSyncService:
    def __init__(self, db: Session, source: str) -> None: self.db, self.source = db, source

    def _match(self, row: NormalizedDirectoryUser) -> User | None:
        if row.directory_object_id:
            matched = self.db.scalar(select(User).where(User.directory_object_id == row.directory_object_id))
            if matched: return matched
        if row.user_principal_name:
            matched = self.db.scalar(select(User).where(
                func.lower(User.user_principal_name) == row.user_principal_name.lower()))
            if matched: return matched
        return self.db.scalar(select(User).where(func.lower(User.email) == row.email.lower()))

    def preview(self, batch: DirectoryBatch) -> dict:
        rows = []; counts = {"created": 0, "updated": 0, "disabled": 0, "unchanged": 0, "errors": 0}
        seen: set[str] = set()
        for incoming in batch.users:
            key = incoming.directory_object_id or (incoming.user_principal_name or incoming.email).lower()
            if key in seen: action, errors = "error", ["רשומה כפולה בקלט"]
            else:
                seen.add(key); user = self._match(incoming); errors = []
                if not user: action = "created"
                elif not incoming.directory_enabled and user.status == "active": action = "disabled"
                elif any(getattr(user, field) != getattr(incoming, field) for field in PROFILE_FIELDS): action = "updated"
                else: action = "unchanged"
            counts[{"error": "errors"}.get(action, action)] += 1
            rows.append({"email": str(incoming.email), "display_name": incoming.display_name,
                         "action": action, "errors": errors, "data": incoming.model_dump(mode="json")})
        return {**counts, "rows": rows, "users": [row.model_dump(mode="json") for row in batch.users],
                "delta_link": batch.delta_link}

    def apply(self, batch: DirectoryBatch, actor_id: uuid.UUID | None = None) -> DirectorySyncRun:
        preview = self.preview(batch)
        if preview["errors"]: raise ValueError("לא ניתן להחיל סנכרון עם שגיאות")
        run = DirectorySyncRun(provider=self.source, initiated_by=actor_id, status="running")
        self.db.add(run); self.db.flush(); now = datetime.now(UTC)
        for result, incoming in zip(preview["rows"], batch.users, strict=True):
            user = self._match(incoming)
            if not user:
                user = User(email=str(incoming.email).lower(), display_name=incoming.display_name,
                    password_hash=password_hash.hash(secrets.token_urlsafe(32)), source=self.source,
                    status="active" if incoming.directory_enabled else "inactive", is_active=incoming.directory_enabled)
                self.db.add(user)
            for field in PROFILE_FIELDS: setattr(user, field, getattr(incoming, field))
            user.source = self.source; user.last_directory_sync_at = now
            if not incoming.directory_enabled and user.status == "active": user.status = "inactive"
            user.is_active = user.status == "active" and incoming.directory_enabled
        run.created_count, run.updated_count = preview["created"], preview["updated"]
        run.disabled_count, run.unchanged_count = preview["disabled"], preview["unchanged"]
        run.error_count, run.delta_reference = preview["errors"], batch.delta_link
        run.status, run.finished_at = "completed", now
        self.db.flush(); apply_all_rules(self.db); return run
