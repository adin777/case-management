from sqlalchemy import select
from app.core.config import settings
from app.database.session import SessionLocal
from app.modules.api import ALL_PERMISSIONS, password_hash
from app.modules.models import Environment, EnvironmentMembership, FieldDefinition, FormDefinition, FormStatus, RequestType, Role, User

def run()->None:
    if settings.environment!="development":return
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)):return
        roles={
            "environment_admin":ALL_PERMISSIONS,
            "agent":["environment.read","request_type.read","case.read","case.update","case.assign","case.comment","case.internal_comment","case.manage_participants"],
            "requester":["environment.read","request_type.read","case.create","case.read","case.comment"],
            "viewer":["environment.read","request_type.read","case.read"],
        }
        role_rows={code:Role(code=code,name=code.replace("_"," ").title(),permissions=perms) for code,perms in roles.items()};db.add_all(role_rows.values())
        admin=User(email="admin@example.com",display_name="מנהל מערכת",password_hash=password_hash.hash("Admin123!"),is_system_admin=True)
        requester=User(email="requester@example.com",display_name="משתמש קצה",password_hash=password_hash.hash("Requester123!"))
        agent=User(email="agent@example.com",display_name="מטפל",password_hash=password_hash.hash("Agent123!"));db.add_all([admin,requester,agent]);db.flush()
        env=Environment(code="IT",name_he="שירותי IT",name_en="IT Service",description="סביבת שירותי טכנולוגיה");db.add(env);db.flush()
        db.add_all([EnvironmentMembership(environment_id=env.id,user_id=requester.id,role_id=role_rows["requester"].id),EnvironmentMembership(environment_id=env.id,user_id=agent.id,role_id=role_rows["agent"].id)])
        rt=RequestType(environment_id=env.id,code="GENERAL_IT",name_he="בקשת IT כללית",name_en="General IT Request",description="בקשת שירות כללית");db.add(rt);db.flush()
        form=FormDefinition(request_type_id=rt.id,version=1,status=FormStatus.published)
        form.fields=[FieldDefinition(key="location",label_he="מיקום",label_en="Location",field_type="short_text",is_required=True,sort_order=1),FieldDefinition(key="device_type",label_he="סוג מכשיר",label_en="Device Type",field_type="single_select",is_required=True,sort_order=2,configuration_json={"options":["מחשב","טלפון","מדפסת"]}),FieldDefinition(key="urgency",label_he="דחיפות",label_en="Urgency",field_type="single_select",is_required=True,sort_order=3,configuration_json={"options":["נמוכה","רגילה","גבוהה"]}),FieldDefinition(key="details",label_he="פרטים נוספים",label_en="Additional Details",field_type="long_text",sort_order=4)];db.add(form);db.flush();rt.form_version_id=form.id;db.commit()
if __name__=="__main__":run()
