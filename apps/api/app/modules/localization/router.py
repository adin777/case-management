from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.modules.api import DB, Current
from app.modules.localization.service import LocalizationService
from app.modules.models import EntityTranslation, Language

router = APIRouter(prefix="/api", tags=["localization"])
LanguageHeader = Annotated[str | None, Header(alias="Accept-Language")]

class TranslationIn(BaseModel):
    translations: dict[str, str] = Field(min_length=1)

@router.get("/languages")
def languages(db: DB) -> list[dict]:
    return [{"code":row.code,"name":row.name,"native_name":row.native_name,"direction":row.direction,
        "is_active":row.is_active,"is_default":row.is_default} for row in db.scalars(
        select(Language).where(Language.is_active.is_(True)).order_by(Language.code))]

@router.get("/localization/{entity_type}/{entity_id}/{field_name}")
def localized(entity_type:str,entity_id:str,field_name:str,db:DB,accept_language:LanguageHeader=None)->dict:
    service=LocalizationService(db,accept_language)
    return {"language":service.language,"value":service.text(entity_type,entity_id,field_name),
        "translations":service.translations(entity_type,entity_id,field_name)}

@router.put("/localization/{entity_type}/{entity_id}/{field_name}")
def save_translations(entity_type:str,entity_id:str,field_name:str,data:TranslationIn,db:DB,user:Current)->dict:
    if not user.is_system_admin: raise HTTPException(403,"נדרשת הרשאת מנהל מערכת")
    active={row.code for row in db.scalars(select(Language).where(Language.is_active.is_(True)))}
    if set(data.translations)-active: raise HTTPException(422,"אחת השפות אינה פעילה")
    for code,value in data.translations.items():
        row=db.scalar(select(EntityTranslation).where(EntityTranslation.entity_type==entity_type,
            EntityTranslation.entity_id==entity_id,EntityTranslation.field_name==field_name,
            EntityTranslation.language_code==code))
        if row: row.value=value.strip()
        else: db.add(EntityTranslation(entity_type=entity_type,entity_id=entity_id,field_name=field_name,
            language_code=code,value=value.strip()))
    db.commit(); return {"translations":LocalizationService(db).translations(entity_type,entity_id,field_name)}
