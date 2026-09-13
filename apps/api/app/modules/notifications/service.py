import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.models import User
from app.modules.notifications.email import EmailProvider
from app.modules.operations.models import (
    Notification,
    NotificationDeliveryLog,
    NotificationOutbox,
    NotificationPreference,
)


class NotificationService:
    """The single persistence and channel-dispatch boundary for business notifications."""

    def __init__(self, db: Session): self.db=db

    def notify_user(self,user_id:uuid.UUID,notification_type:str,title:str,body:str,*,case_id:uuid.UUID|None=None,environment_id:uuid.UUID|None=None,route:str|None=None,source:str="business",deduplication_key:str|None=None,metadata:dict|None=None)->Notification|None:
        if deduplication_key and self.db.scalar(select(Notification.id).where(Notification.deduplication_key==deduplication_key)): return None
        preference=self.db.get(NotificationPreference,(user_id,notification_type))
        in_app=preference.in_app_enabled if preference else True
        email=preference.email_enabled if preference else False
        if not in_app and not email:return None
        item=Notification(user_id=user_id,notification_type=notification_type,title_he=title,body_he=body,entity_type="case" if case_id else "system",entity_id=str(case_id or ""),case_id=case_id,environment_id=environment_id,route=route or (f"/cases/{case_id}" if case_id else "/notifications"),source=source,deduplication_key=deduplication_key,metadata_json=metadata or {},is_read=not in_app)
        self.db.add(item);self.db.flush()
        if email:
            user=self.db.get(User,user_id)
            if user:self.db.add(NotificationOutbox(notification_id=item.id,channel="email",payload_json={"recipient":user.email,"title":title,"body":body},status="pending"))
        return item

    def notify_users(self,user_ids:Iterable[uuid.UUID],*args:str,exclude:uuid.UUID|None=None,**kwargs:Any)->list[Notification]:
        result=[]
        for user_id in dict.fromkeys(user_ids):
            if user_id==exclude:continue
            options=dict(kwargs)
            if options.get("deduplication_key"):options["deduplication_key"]=f'{options["deduplication_key"]}:{user_id}'
            item=self.notify_user(user_id,*args,**options)
            if item:result.append(item)
        return result

    def deliver_pending_email(self,provider:EmailProvider,limit:int=25)->dict[str,int]:
        counts={"sent":0,"failed":0}
        rows=list(self.db.scalars(select(NotificationOutbox).where(NotificationOutbox.channel=="email",NotificationOutbox.status.in_(["pending","failed"])).limit(limit)))
        for row in rows:
            if row.notification_id is None:continue
            payload=row.payload_json or {};recipient=str(payload.get("recipient", ""))
            try:
                message_id=provider.send(recipient,str(payload.get("title","")),str(payload.get("body","")));row.status="sent";row.error=None;counts["sent"]+=1
                self.db.add(NotificationDeliveryLog(notification_id=row.notification_id,channel="email",recipient=recipient,status="sent",provider_message_id=message_id))
            except RuntimeError as exc:  # delivery is deliberately isolated from the business mutation
                row.status="failed";row.error=str(exc)[:1000];counts["failed"]+=1
                self.db.add(NotificationDeliveryLog(notification_id=row.notification_id,channel="email",recipient=recipient,status="failed",error=str(exc)[:1000]))
        self.db.flush();return counts
