import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update

from app.modules.api import DB, Current, audit
from app.modules.directory.secrets import encrypt
from app.modules.models import SystemSetting
from app.modules.operations.models import Notification, NotificationPreference

router=APIRouter(prefix="/api/notifications",tags=["notifications"])

class PreferenceIn(BaseModel):
    notification_type:str;in_app_enabled:bool=True;email_enabled:bool=False;frequency:str="immediate"

class EmailSettingsIn(BaseModel):
    enabled:bool=False;host:str="";port:int=587;username:str="";password:str|None=None;from_address:str="";use_tls:bool=True

def view(row:Notification)->dict[str,Any]:
    return {"id":str(row.id),"type":row.notification_type,"title":row.title_he,"body":row.body_he,"case_id":str(row.case_id) if row.case_id else None,"environment_id":str(row.environment_id) if row.environment_id else None,"route":row.route,"is_read":row.is_read,"read_at":row.read_at,"created_at":row.created_at,"source":row.source,"metadata":row.metadata_json}

@router.get("")
def list_notifications(db:DB,user:Current,unread_only:bool=False,notification_type:str|None=None,environment_id:uuid.UUID|None=None,date_from:datetime|None=None,date_to:datetime|None=None,page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100))->dict:
    query=select(Notification).where(Notification.user_id==user.id)
    if unread_only:query=query.where(Notification.is_read.is_(False))
    if notification_type:query=query.where(Notification.notification_type==notification_type)
    if environment_id:query=query.where(Notification.environment_id==environment_id)
    if date_from:query=query.where(Notification.created_at>=date_from)
    if date_to:query=query.where(Notification.created_at<=date_to)
    total=db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows=db.scalars(query.order_by(Notification.created_at.desc()).offset((page-1)*page_size).limit(page_size))
    unread=db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id==user.id,Notification.is_read.is_(False))) or 0
    return {"items":[view(row) for row in rows],"total":total,"unread":unread,"page":page,"page_size":page_size}

@router.put("/{notification_id}/read")
def mark_read(notification_id:uuid.UUID,db:DB,user:Current,is_read:bool=True)->dict:
    row=db.get(Notification,notification_id)
    if not row or row.user_id!=user.id:raise HTTPException(404,"Notification not found")
    row.is_read=is_read;row.read_at=datetime.now(UTC) if is_read else None;db.commit();return view(row)

@router.put("/read-all",status_code=204)
def mark_all(db:DB,user:Current)->None:
    db.execute(update(Notification).where(Notification.user_id==user.id,Notification.is_read.is_(False)).values(is_read=True,read_at=datetime.now(UTC)));db.commit()

@router.get("/preferences")
def preferences(db:DB,user:Current)->list[dict]:
    return [{"notification_type":r.notification_type,"in_app_enabled":r.in_app_enabled,"email_enabled":r.email_enabled,"frequency":r.frequency} for r in db.scalars(select(NotificationPreference).where(NotificationPreference.user_id==user.id))]

@router.put("/preferences/{notification_type}")
def save_preference(notification_type:str,data:PreferenceIn,db:DB,user:Current)->dict:
    row=db.get(NotificationPreference,(user.id,notification_type)) or NotificationPreference(user_id=user.id,notification_type=notification_type)
    row.in_app_enabled=data.in_app_enabled;row.email_enabled=data.email_enabled;row.frequency=data.frequency;db.add(row);db.commit();return data.model_dump()

@router.get("/settings/email")
def get_email_settings(db:DB,user:Current)->dict:
    if not user.is_system_admin:raise HTTPException(403,"System administrator required")
    row=db.get(SystemSetting,"email_settings");value=dict(row.value_json or {}) if row and isinstance(row.value_json,dict) else {}
    configured=bool(value.pop("encrypted_password",None));value["password_configured"]=configured;return value

@router.put("/settings/email")
def put_email_settings(data:EmailSettingsIn,db:DB,user:Current)->dict:
    if not user.is_system_admin:raise HTTPException(403,"System administrator required")
    row=db.get(SystemSetting,"email_settings") or SystemSetting(key="email_settings",value_json={});current=dict(row.value_json) if isinstance(row.value_json,dict) else {}
    value=data.model_dump(exclude={"password"});value["encrypted_password"]=encrypt(data.password) if data.password else current.get("encrypted_password")
    row.value_json=value;db.add(row);audit(db,user,"system_setting",uuid.uuid5(uuid.NAMESPACE_URL,"system:email_settings"),"updated",after={key:item for key,item in value.items() if key!="encrypted_password"});db.commit();return get_email_settings(db,user)
