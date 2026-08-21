from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import EntityTranslation, Language


class LocalizationService:
    def __init__(self, db: Session, requested_language: str | None = None) -> None:
        self.db = db
        requested = (requested_language or "").split(",", 1)[0].split("-", 1)[0].strip().lower()
        active = db.get(Language, requested) if requested else None
        default = db.scalar(select(Language).where(Language.is_default.is_(True), Language.is_active.is_(True)))
        self.language = active.code if active and active.is_active else (default.code if default else "he")
        self.default_language = default.code if default else "he"

    def text(self, entity_type: str, entity_id: object, field_name: str, *,
             legacy_he: str | None = None, legacy_en: str | None = None,
             technical_fallback: str | None = None) -> str:
        entity_id_string = str(entity_id)
        rows = {row.language_code: row.value for row in self.db.scalars(select(EntityTranslation).where(
            EntityTranslation.entity_type == entity_type, EntityTranslation.entity_id == entity_id_string,
            EntityTranslation.field_name == field_name))}
        legacy = {"he":legacy_he or "", "en":legacy_en or ""}
        return (rows.get(self.language) or legacy.get(self.language) or
                rows.get(self.default_language) or legacy.get(self.default_language) or
                technical_fallback or f"{entity_type}:{entity_id_string}:{field_name}")

    def translations(self, entity_type: str, entity_id: object, field_name: str) -> dict[str, str]:
        return {row.language_code:row.value for row in self.db.scalars(select(EntityTranslation).where(
            EntityTranslation.entity_type == entity_type, EntityTranslation.entity_id == str(entity_id),
            EntityTranslation.field_name == field_name))}
