from sqlalchemy import select

from app.database.session import SessionLocal
from app.modules.localization.service import LocalizationService
from app.modules.models import EntityTranslation, Language


def test_db_translation_fallback_and_third_language_without_schema_change() -> None:
    with SessionLocal() as db:
        db.add(Language(code="ar",name="Arabic",native_name="العربية",direction="rtl",is_active=True,is_default=False))
        db.flush()
        db.add_all([
            EntityTranslation(entity_type="environment",entity_id="env-1",field_name="name",language_code="he",value="סביבה"),
            EntityTranslation(entity_type="environment",entity_id="env-1",field_name="name",language_code="en",value="Environment"),
            EntityTranslation(entity_type="environment",entity_id="env-1",field_name="name",language_code="ar",value="بيئة"),
            EntityTranslation(entity_type="case_field",entity_id="field-1",field_name="label",language_code="en",value="Building"),
            EntityTranslation(entity_type="case_field_option",entity_id="field-1:floor-1",field_name="label",language_code="en",value="First floor"),
        ])
        db.flush()
        assert LocalizationService(db,"en-US").text("environment","env-1","name") == "Environment"
        assert LocalizationService(db,"ar").text("environment","env-1","name") == "بيئة"
        assert LocalizationService(db,"de").text("environment","env-1","name") == "סביבה"
        assert LocalizationService(db,"en").text("request_type","missing","name",legacy_he="ברירת מחדל") == "ברירת מחדל"
        assert LocalizationService(db,"en").text("case_field","field-1","label",legacy_he="בניין") == "Building"
        assert LocalizationService(db,"en").text("case_field_option","field-1:floor-1","label",legacy_he="קומה ראשונה") == "First floor"
        assert db.scalar(select(Language).where(Language.code=="ar")) is not None
