import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Annotated
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field, model_validator
from pwdlib import PasswordHash
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import get_db
from app.modules.models import AuditEvent, Case, CaseFieldValue, CaseParticipant, CaseStatus, Comment, Environment, EnvironmentMembership, FieldDefinition, FormDefinition, FormStatus, RefreshToken, RequestType, Role, User, Visibility

router=APIRouter(prefix="/api"); oauth=OAuth2PasswordBearer(tokenUrl="/api/auth/login"); password_hash=PasswordHash.recommended(); DB=Annotated[Session,Depends(get_db)]
ALL_PERMISSIONS=["environment.read","environment.manage","request_type.read","request_type.manage","case.create","case.read","case.update","case.assign","case.comment","case.internal_comment","case.manage_participants"]
TRANSITIONS={CaseStatus.draft:{CaseStatus.submitted,CaseStatus.cancelled},CaseStatus.submitted:{CaseStatus.assigned,CaseStatus.in_progress,CaseStatus.cancelled},CaseStatus.assigned:{CaseStatus.in_progress,CaseStatus.cancelled},CaseStatus.in_progress:{CaseStatus.waiting_for_requester,CaseStatus.resolved,CaseStatus.cancelled},CaseStatus.waiting_for_requester:{CaseStatus.in_progress,CaseStatus.resolved},CaseStatus.resolved:{CaseStatus.closed,CaseStatus.in_progress},CaseStatus.closed:set(),CaseStatus.cancelled:set()}

class LoginIn(BaseModel): email: EmailStr; password: str
class TokenOut(BaseModel): access_token:str; refresh_token:str; token_type:str="bearer"
class RefreshIn(BaseModel): refresh_token:str
class UserOut(BaseModel): id:uuid.UUID; email:str; display_name:str; is_system_admin:bool; model_config={"from_attributes":True}
class EnvironmentIn(BaseModel): code:str=Field(pattern=r"^[A-Z0-9_-]+$"); name_he:str; name_en:str; description:str|None=None
class EnvironmentOut(EnvironmentIn): id:uuid.UUID; is_active:bool; model_config={"from_attributes":True}
class MembershipIn(BaseModel): user_id:uuid.UUID; role_code:str
class RequestTypeIn(BaseModel): environment_id:uuid.UUID; code:str; name_he:str; name_en:str; description:str|None=None
class RequestTypeOut(RequestTypeIn): id:uuid.UUID; is_active:bool; form_version_id:uuid.UUID|None; model_config={"from_attributes":True}
class FieldIn(BaseModel): key:str=Field(pattern=r"^[a-z][a-z0-9_]*$"); label_he:str; label_en:str; field_type:str; is_required:bool=False; is_read_only:bool=False; sort_order:int=0; configuration_json:dict[str,Any]={}
class FieldOut(FieldIn): id:uuid.UUID; model_config={"from_attributes":True}
class FormIn(BaseModel): request_type_id:uuid.UUID; fields:list[FieldIn]=[]
class FormOut(BaseModel): id:uuid.UUID; request_type_id:uuid.UUID; version:int; status:FormStatus; fields:list[FieldOut]; model_config={"from_attributes":True}
class ValueIn(BaseModel): field_definition_id:uuid.UUID; value:Any=None
class CaseIn(BaseModel): environment_id:uuid.UUID; request_type_id:uuid.UUID; title:str=Field(min_length=3,max_length=300); description:str|None=None; priority:str="normal"; values:list[ValueIn]=[]
class CommentOut(BaseModel): id:uuid.UUID; author_id:uuid.UUID; body:str; visibility:Visibility; created_at:datetime; model_config={"from_attributes":True}
class CaseOut(BaseModel): id:uuid.UUID; case_number:str; environment_id:uuid.UUID; request_type_id:uuid.UUID; form_definition_id:uuid.UUID; title:str; description:str|None; status:CaseStatus; priority:str; reporter_id:uuid.UUID; requester_id:uuid.UUID; assignee_id:uuid.UUID|None; created_at:datetime; comments:list[CommentOut]=[]; model_config={"from_attributes":True}
class CommentIn(BaseModel): body:str=Field(min_length=1); visibility:Visibility=Visibility.public
class ParticipantIn(BaseModel): user_id:uuid.UUID; participant_type:str=Field(pattern="^(watcher|mentioned|collaborator)$")
class TransitionIn(BaseModel): status:CaseStatus

def issue(user:User, token_type:str, expires:timedelta, token_id:uuid.UUID|None=None)->str:
    now=datetime.now(UTC); payload={"sub":str(user.id),"type":token_type,"iat":now,"exp":now+expires}
    if token_id: payload["jti"]=str(token_id)
    return jwt.encode(payload,settings.jwt_secret,algorithm="HS256")
def decode(token:str, expected:str)->dict[str,Any]:
    try: payload=jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])
    except jwt.PyJWTError as exc: raise HTTPException(401,"Invalid or expired token") from exc
    if payload.get("type")!=expected: raise HTTPException(401,"Invalid token type")
    return payload
def current_user(db:DB,token:Annotated[str,Depends(oauth)])->User:
    user=db.get(User,uuid.UUID(decode(token,"access")["sub"]))
    if not user or not user.is_active: raise HTTPException(401,"Inactive or unknown user")
    return user
Current=Annotated[User,Depends(current_user)]
def permissions(db:Session,user:User,environment_id:uuid.UUID)->set[str]:
    if user.is_system_admin:return set(ALL_PERMISSIONS)
    return set(db.scalars(select(Role.permissions).join(EnvironmentMembership,EnvironmentMembership.role_id==Role.id).where(EnvironmentMembership.environment_id==environment_id,EnvironmentMembership.user_id==user.id)).one_or_none() or [])
def require(db:Session,user:User,env:uuid.UUID,permission:str)->None:
    if permission not in permissions(db,user,env): raise HTTPException(403,f"Missing permission: {permission}")
def audit(db:Session,user:User,entity:str,entity_id:uuid.UUID,action:str,before:dict|None=None,after:dict|None=None)->None:
    db.add(AuditEvent(entity_type=entity,entity_id=str(entity_id),action=action,actor_id=user.id,before_json=before,after_json=after,metadata_json={}))
def case_access(db:Session,user:User,item:Case)->None:
    if "case.read" in permissions(db,user,item.environment_id) or item.requester_id==user.id or item.reporter_id==user.id:return
    participant=db.get(CaseParticipant,(item.id,user.id,"collaborator"))
    if participant:return
    raise HTTPException(403,"Case is not visible to this user")

@router.post("/auth/login",response_model=TokenOut)
def login(data:LoginIn,db:DB)->TokenOut:
    user=db.scalar(select(User).where(func.lower(User.email)==data.email.lower()))
    if not user or not password_hash.verify(data.password,user.password_hash) or not user.is_active: raise HTTPException(401,"Invalid credentials")
    token_id=uuid.uuid4(); db.add(RefreshToken(id=token_id,user_id=user.id,expires_at=datetime.now(UTC)+timedelta(days=settings.refresh_token_days))); db.commit()
    return TokenOut(access_token=issue(user,"access",timedelta(minutes=settings.access_token_minutes)),refresh_token=issue(user,"refresh",timedelta(days=settings.refresh_token_days),token_id))
@router.post("/auth/refresh",response_model=TokenOut)
def refresh(data:RefreshIn,db:DB)->TokenOut:
    payload=decode(data.refresh_token,"refresh"); old=db.get(RefreshToken,uuid.UUID(payload["jti"])); now=datetime.now(UTC)
    if not old or old.revoked_at or old.expires_at.replace(tzinfo=UTC)<=now: raise HTTPException(401,"Refresh token revoked")
    old.revoked_at=now; user=db.get(User,old.user_id); new_id=uuid.uuid4(); db.add(RefreshToken(id=new_id,user_id=user.id,expires_at=now+timedelta(days=settings.refresh_token_days))); db.commit()
    return TokenOut(access_token=issue(user,"access",timedelta(minutes=settings.access_token_minutes)),refresh_token=issue(user,"refresh",timedelta(days=settings.refresh_token_days),new_id))
@router.post("/auth/logout",status_code=204)
def logout(data:RefreshIn,db:DB)->None:
    row=db.get(RefreshToken,uuid.UUID(decode(data.refresh_token,"refresh")["jti"]));
    if row: row.revoked_at=datetime.now(UTC); db.commit()
@router.get("/auth/me",response_model=UserOut)
def me(user:Current)->User:return user
@router.get("/users",response_model=list[UserOut])
def users(db:DB,user:Current)->list[User]:
    if not user.is_system_admin:raise HTTPException(403,"System administrator required")
    return list(db.scalars(select(User).order_by(User.display_name)))
@router.get("/roles")
def roles(db:DB,user:Current)->list[dict]: return [{"id":str(r.id),"code":r.code,"name":r.name,"permissions":r.permissions} for r in db.scalars(select(Role))]
@router.get("/groups")
def groups(user:Current)->list[dict]: return []
@router.get("/environments",response_model=list[EnvironmentOut])
def environments(db:DB,user:Current)->list[Environment]:
    query=select(Environment).order_by(Environment.name_he)
    if not user.is_system_admin: query=query.join(EnvironmentMembership).where(EnvironmentMembership.user_id==user.id)
    return list(db.scalars(query).unique())
@router.post("/environments",response_model=EnvironmentOut,status_code=201)
def create_environment(data:EnvironmentIn,db:DB,user:Current)->Environment:
    if not user.is_system_admin:raise HTTPException(403,"System administrator required")
    item=Environment(**data.model_dump());db.add(item);db.flush();audit(db,user,"environment",item.id,"created",after=data.model_dump());db.commit();db.refresh(item);return item
@router.post("/environments/{environment_id}/memberships",status_code=201)
def add_membership(environment_id:uuid.UUID,data:MembershipIn,db:DB,user:Current)->dict:
    require(db,user,environment_id,"environment.manage");role=db.scalar(select(Role).where(Role.code==data.role_code));
    if not role:raise HTTPException(404,"Role not found")
    item=EnvironmentMembership(environment_id=environment_id,user_id=data.user_id,role_id=role.id);db.add(item);db.commit();return {"id":str(item.id)}
@router.get("/request-types",response_model=list[RequestTypeOut])
def request_types(db:DB,user:Current,environment_id:uuid.UUID=Query(...))->list[RequestType]:require(db,user,environment_id,"request_type.read");return list(db.scalars(select(RequestType).where(RequestType.environment_id==environment_id)))
@router.post("/request-types",response_model=RequestTypeOut,status_code=201)
def create_request_type(data:RequestTypeIn,db:DB,user:Current)->RequestType:require(db,user,data.environment_id,"request_type.manage");item=RequestType(**data.model_dump());db.add(item);db.flush();audit(db,user,"request_type",item.id,"created",after=data.model_dump(mode="json"));db.commit();return item
@router.post("/forms",response_model=FormOut,status_code=201)
def create_form(data:FormIn,db:DB,user:Current)->FormDefinition:
    rt=db.get(RequestType,data.request_type_id)
    if not rt:raise HTTPException(404,"Request type not found")
    require(db,user,rt.environment_id,"request_type.manage");version=(db.scalar(select(func.max(FormDefinition.version)).where(FormDefinition.request_type_id==rt.id)) or 0)+1;form=FormDefinition(request_type_id=rt.id,version=version)
    form.fields=[FieldDefinition(**field.model_dump()) for field in data.fields];db.add(form);db.flush();audit(db,user,"form",form.id,"created");db.commit();return form
@router.get("/forms/{form_id}",response_model=FormOut)
def get_form(form_id:uuid.UUID,db:DB,user:Current)->FormDefinition:
    form=db.get(FormDefinition,form_id)
    if not form:raise HTTPException(404,"Form not found")
    rt=db.get(RequestType,form.request_type_id);require(db,user,rt.environment_id,"request_type.read");return form
@router.post("/forms/{form_id}/publish",response_model=FormOut)
def publish(form_id:uuid.UUID,db:DB,user:Current)->FormDefinition:
    form=db.get(FormDefinition,form_id)
    if not form:raise HTTPException(404,"Form not found")
    rt=db.get(RequestType,form.request_type_id);require(db,user,rt.environment_id,"request_type.manage")
    if form.status!=FormStatus.draft:raise HTTPException(409,"Published forms are immutable")
    form.status=FormStatus.published;form.published_at=datetime.now(UTC);rt.form_version_id=form.id;audit(db,user,"form",form.id,"published");db.commit();return form
def typed_value(case_id:uuid.UUID,field:FieldDefinition,value:Any)->CaseFieldValue:
    row=CaseFieldValue(case_id=case_id,field_definition_id=field.id)
    if value is None:return row
    if field.field_type in {"short_text","long_text","single_select"}:row.value_text=str(value)
    elif field.field_type=="number":row.value_number=Decimal(str(value))
    elif field.field_type=="boolean":row.value_boolean=bool(value)
    elif field.field_type=="date":row.value_date=date.fromisoformat(value)
    elif field.field_type=="datetime":row.value_datetime=datetime.fromisoformat(value)
    elif field.field_type=="user":row.value_user_id=uuid.UUID(value)
    else:row.value_json=value
    return row
@router.post("/cases",response_model=CaseOut,status_code=201)
def create_case(data:CaseIn,db:DB,user:Current)->Case:
    require(db,user,data.environment_id,"case.create");rt=db.get(RequestType,data.request_type_id)
    if not rt or rt.environment_id!=data.environment_id or not rt.form_version_id:raise HTTPException(400,"Published form is required")
    form=db.get(FormDefinition,rt.form_version_id);provided={v.field_definition_id:v.value for v in data.values}
    missing=[f.label_he for f in form.fields if f.is_required and provided.get(f.id) in (None,"")]
    if missing:raise HTTPException(422,{"missing_required_fields":missing})
    number=(db.scalar(select(func.count()).select_from(Case)) or 0)+1;item=Case(case_number=f"CASE-{datetime.now().year}-{number:06d}",form_definition_id=form.id,reporter_id=user.id,requester_id=user.id,**data.model_dump(exclude={"values"}));db.add(item);db.flush();item.values=[typed_value(item.id,f,provided.get(f.id)) for f in form.fields if f.id in provided];audit(db,user,"case",item.id,"created",after={"status":item.status.value});db.commit();return item
@router.get("/cases",response_model=list[CaseOut])
def cases(db:DB,user:Current,assigned:bool=False)->list[Case]:
    query=select(Case).order_by(Case.created_at.desc())
    if assigned:query=query.where(Case.assignee_id==user.id)
    elif not user.is_system_admin:query=query.where(or_(Case.requester_id==user.id,Case.reporter_id==user.id,Case.environment_id.in_(select(EnvironmentMembership.environment_id).where(EnvironmentMembership.user_id==user.id))))
    return list(db.scalars(query).unique())
@router.get("/cases/{case_id}",response_model=CaseOut)
def get_case(case_id:uuid.UUID,db:DB,user:Current)->Case:
    item=db.get(Case,case_id)
    if not item:raise HTTPException(404,"Case not found")
    case_access(db,user,item)
    item.comments=[c for c in item.comments if c.visibility==Visibility.public or "case.internal_comment" in permissions(db,user,item.environment_id)]
    return item
@router.post("/cases/{case_id}/comments",response_model=CommentOut,status_code=201)
def add_comment(case_id:uuid.UUID,data:CommentIn,db:DB,user:Current)->Comment:
    item=db.get(Case,case_id)
    if not item:raise HTTPException(404,"Case not found")
    case_access(db,user,item);require(db,user,item.environment_id,"case.internal_comment" if data.visibility==Visibility.internal else "case.comment");comment=Comment(case_id=item.id,author_id=user.id,**data.model_dump());db.add(comment);db.flush();audit(db,user,"case",item.id,"commented",after={"visibility":data.visibility.value});db.commit();return comment
@router.post("/cases/{case_id}/participants",status_code=201)
def add_participant(case_id:uuid.UUID,data:ParticipantIn,db:DB,user:Current)->dict:
    item=db.get(Case,case_id)
    if not item:raise HTTPException(404,"Case not found")
    require(db,user,item.environment_id,"case.manage_participants");row=CaseParticipant(case_id=case_id,user_id=data.user_id,participant_type=data.participant_type,added_by=user.id);db.add(row);audit(db,user,"case",item.id,"participant_added");db.commit();return {"ok":True}
@router.post("/cases/{case_id}/transitions",response_model=CaseOut)
def transition(case_id:uuid.UUID,data:TransitionIn,db:DB,user:Current)->Case:
    item=db.get(Case,case_id)
    if not item:raise HTTPException(404,"Case not found")
    require(db,user,item.environment_id,"case.update")
    if data.status not in TRANSITIONS[item.status]:raise HTTPException(409,f"Transition {item.status.value} -> {data.status.value} is not allowed")
    before=item.status;item.status=data.status;item.version+=1
    if data.status==CaseStatus.closed:item.closed_at=datetime.now(UTC)
    audit(db,user,"case",item.id,"status_changed",{"status":before.value},{"status":data.status.value});db.commit();return item
@router.get("/audit")
def audit_events(db:DB,user:Current)->list[dict]:
    if not user.is_system_admin:raise HTTPException(403,"System administrator required")
    return [{"entity_type":a.entity_type,"entity_id":a.entity_id,"action":a.action,"created_at":a.created_at} for a in db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(200))]
