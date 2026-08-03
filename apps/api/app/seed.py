from pwdlib.exceptions import PwdlibError
from sqlalchemy import select

from app.core.config import settings
from app.database.session import SessionLocal
from app.modules.api import ALL_PERMISSIONS, password_hash
from app.modules.models import (
    Environment,
    EnvironmentMembership,
    FieldDefinition,
    FormDefinition,
    FormStatus,
    Permission,
    PriorityDefinition,
    RequestType,
    Role,
    RolePermission,
    SubPriorityDefinition,
    User,
)


def run() -> None:
    if settings.environment != "development":
        return
    with SessionLocal() as db:
        role_permissions = {
            "environment_admin": [code for code in ALL_PERMISSIONS if not code.startswith("system.")],
            "agent": [
                "environment.read", "request_type.read", "case.read", "case.read_environment",
                "case.update", "case.change_status", "case.comment", "comment.public.read",
                "comment.public.create",
            ],
            "requester": [
                "environment.read", "request_type.read", "case.create", "case.read", "case.read_own",
                "case.read_participating", "case.comment", "comment.public.read", "comment.public.create",
            ],
            "viewer": [
                "environment.read", "request_type.read", "case.read", "case.read_environment",
                "comment.public.read",
            ],
        }
        permission_names = {
            "system.users.read": ("צפייה במשתמשים", "מאפשר לצפות ברשימת המשתמשים ובפרטיהם"),
            "system.users.create": ("יצירת משתמשים", "מאפשר ליצור משתמשים חדשים"),
            "system.users.update": ("עריכת משתמשים", "מאפשר לערוך פרטי משתמשים"),
            "system.users.disable": ("הפעלת והשבתת משתמשים", "מאפשר לשנות את מצב הפעילות של משתמשים"),
            "system.users.reset_password": ("איפוס סיסמה", "מאפשר לאפס סיסמת משתמש בסביבת הפיתוח"),
            "system.groups.read": ("צפייה בקבוצות משתמשים", "מאפשר לצפות בקבוצות ובחבריהן"),
            "system.groups.manage": ("ניהול קבוצות משתמשים", "מאפשר ליצור ולערוך קבוצות וחברויות"),
            "system.roles.read": ("צפייה בתפקידים", "מאפשר לצפות בתפקידים ובהרשאותיהם"),
            "system.roles.manage": ("ניהול תפקידים", "מאפשר ליצור, לערוך ולהשבית תפקידים"),
            "system.fields.read": ("צפייה בשדות משתמש", "מאפשר לצפות בהגדרות שדות משתמש"),
            "system.fields.manage": ("ניהול שדות משתמש", "מאפשר ליצור ולערוך שדות משתמש וערכיהם"),
            "system.environments.create": ("יצירת סביבות", "מאפשר ליצור סביבת עבודה חדשה"),
            "system.environments.manage": ("ניהול כלל הסביבות", "מאפשר לערוך ולהשבית כל סביבת עבודה"),
            "environment.read": ("צפייה בסביבה", "מאפשר לצפות בסביבת העבודה ובהגדרותיה"),
            "case.assign": ("הקצאת מטפל", "מאפשר לבחור משתמש או קבוצת טיפול ולהקצות להם קריאת שירות"),
            "case.manage_participants": ("ניהול משתתפים", "מאפשר להוסיף ולהסיר משתתפים בקריאת שירות"),
            "case.create": ("פתיחת קריאה", "מאפשר ליצור קריאות שירות בסביבה"),
            "case.update": ("עריכת קריאה", "מאפשר לעדכן את פרטי קריאת השירות"),
            "environment.manage": ("ניהול סביבה", "מאפשר לערוך את הגדרות סביבת העבודה"),
            "environment.users.manage": ("ניהול משתמשי סביבה", "מאפשר לשייך משתמשים ותפקידים לסביבה"),
            "environment.groups.manage": ("ניהול קבוצות בסביבה", "מאפשר לשייך קבוצות ותפקידים לסביבה"),
            "environment.fields.manage": ("ניהול שדות", "מאפשר להגדיר שדות בסביבת העבודה"),
            "environment.request_types.manage": ("ניהול סוגי קריאות", "מאפשר ליצור ולערוך סוגי קריאות"),
            "environment.forms.manage": ("ניהול טפסים", "מאפשר לערוך ולפרסם טפסי קריאה"),
            "environment.rules.manage": ("ניהול אוטומציות", "מאפשר ליצור ולערוך כללי אוטומציה"),
            "environment.audit.read": ("צפייה ביומן ביקורת", "מאפשר לצפות בפעולות שבוצעו בסביבה"),
            "request_type.read": ("צפייה בסוגי קריאות", "מאפשר לצפות בסוגי הקריאות הפעילים"),
            "request_type.manage": ("עריכת סוגי קריאות", "מאפשר לערוך הגדרות של סוגי קריאות"),
            "case.read": ("צפייה בקריאות", "מאפשר לצפות בקריאות שירות מורשות"),
            "case.read_own": ("צפייה בקריאות שלי", "מאפשר לצפות בקריאות שהמשתמש פתח"),
            "case.read_participating": ("צפייה בקריאות בהשתתפותי", "מאפשר לצפות בקריאות שבהן המשתמש משתתף"),
            "case.read_environment": ("צפייה בקריאות הסביבה", "מאפשר לצפות בכל קריאות סביבת העבודה"),
            "case.lock": ("נעילת קריאה", "מאפשר לנעול ולפתוח קריאת שירות לשינויים"),
            "case.change_status": ("שינוי סטטוס קריאה", "מאפשר להעביר קריאה בין שלבי הטיפול"),
            "case.comment": ("תגובה לקריאה", "מאפשר להוסיף תגובה לקריאת שירות"),
            "case.internal_comment": ("תגובה פנימית", "מאפשר להוסיף הודעה פנימית למנהלים"),
            "comment.public.read": ("צפייה בשיחה ציבורית", "מאפשר לקרוא תגובות ציבוריות בקריאה"),
            "comment.public.create": ("כתיבה בשיחה ציבורית", "מאפשר להוסיף תגובה ציבורית לקריאה"),
            "comment.manager.read": ("צפייה בהודעות מנהלים", "מאפשר לקרוא הודעות מנהלים בקריאה"),
            "comment.manager.create": ("כתיבת הודעת מנהלים", "מאפשר להוסיף הודעה למנהלים בלבד"),
        }
        for code in ALL_PERMISSIONS:
            permission_item = db.get(Permission, code)
            if not permission_item:
                permission_item = Permission(code=code, description=code.replace(".", " ").title())
                db.add(permission_item)
            name, description = permission_names.get(code, (code.replace(".", " "), "הרשאת מערכת מוגדרת"))
            permission_item.name_he, permission_item.description_he = name, description
            permission_item.category = (
                "קריאות שירות" if code.startswith("case.") else
                "תגובות" if code.startswith("comment.") else
                "סביבות עבודה" if code.startswith(("environment.", "request_type.")) else
                "משתמשים והרשאות"
            )
            permission_item.scope = "system" if code.startswith("system.") else "environment"
        db.flush()
        roles: dict[str, Role] = {}
        for code, permission_codes in role_permissions.items():
            role = db.scalar(select(Role).where(Role.code == code))
            if not role:
                role = Role(code=code, name=code.replace("_", " ").title(), scope="environment")
                db.add(role)
                db.flush()
            role.permissions = permission_codes
            role.scope = "environment"
            for permission_code in permission_codes:
                if not db.get(RolePermission, (role.id, permission_code)):
                    db.add(RolePermission(role_id=role.id, permission_code=permission_code))
            roles[code] = role

        users: dict[str, User] = {}
        for email, name, password, is_admin in [
            ("admin@example.com", "מנהל מערכת", "Admin123!", True),
            ("envadmin@example.com", "מנהל סביבת IT", "EnvAdmin123!", False),
            ("requester@example.com", "משתמש קצה", "Requester123!", False),
            ("agent@example.com", "מטפל", "Agent123!", False),
        ]:
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(email=email, display_name=name, password_hash=password_hash.hash(password),
                            is_system_admin=is_admin, is_active=True)
                db.add(user)
                db.flush()
            else:
                user.display_name = name
                user.is_active = True
                user.is_system_admin = is_admin
                try:
                    valid = password_hash.verify(password, user.password_hash)
                except PwdlibError:
                    valid = False
                if not valid:
                    user.password_hash = password_hash.hash(password)
            users[email] = user

        env = db.scalar(select(Environment).where(Environment.code == "IT"))
        if not env:
            env = Environment(code="IT", name_he="שירותי IT", name_en="IT Service",
                              description="סביבת שירותי טכנולוגיה")
            db.add(env)
            db.flush()
        for email, role_code in [
            ("envadmin@example.com", "environment_admin"),
            ("requester@example.com", "requester"),
            ("agent@example.com", "agent"),
        ]:
            if not db.scalar(select(EnvironmentMembership).where(
                EnvironmentMembership.environment_id == env.id,
                EnvironmentMembership.user_id == users[email].id,
                EnvironmentMembership.role_id == roles[role_code].id,
            )):
                db.add(EnvironmentMembership(environment_id=env.id, user_id=users[email].id,
                                             role_id=roles[role_code].id))

        priorities: dict[str, PriorityDefinition] = {}
        for index, (code, label, color) in enumerate([
            ("low", "נמוכה", "#22c55e"), ("normal", "רגילה", "#3b82f6"),
            ("high", "גבוהה", "#f59e0b"), ("critical", "קריטית", "#ef4444"),
        ]):
            priority_item = db.scalar(select(PriorityDefinition).where(
                PriorityDefinition.environment_id == env.id, PriorityDefinition.code == code))
            if not priority_item:
                priority_item = PriorityDefinition(environment_id=env.id, code=code, label_he=label,
                                                   color=color, sort_order=index)
                db.add(priority_item)
                db.flush()
            priorities[code] = priority_item
        for index, (code, label) in enumerate([("standard", "רגילה"), ("urgent", "דחופה")]):
            parent = priorities["high"]
            if not db.scalar(select(SubPriorityDefinition).where(
                SubPriorityDefinition.priority_id == parent.id,
                SubPriorityDefinition.code == code,
            )):
                db.add(SubPriorityDefinition(priority_id=parent.id, code=code, label_he=label,
                                             sort_order=index))

        request_type = db.scalar(select(RequestType).where(
            RequestType.environment_id == env.id, RequestType.code == "GENERAL_IT"))
        if not request_type:
            request_type = RequestType(environment_id=env.id, code="GENERAL_IT",
                                       name_he="בקשת IT כללית", name_en="General IT Request",
                                       description="בקשת שירות כללית")
            db.add(request_type)
            db.flush()
        form = db.scalar(select(FormDefinition).where(
            FormDefinition.request_type_id == request_type.id, FormDefinition.version == 1))
        if not form:
            form = FormDefinition(request_type_id=request_type.id, version=1, status=FormStatus.published)
            form.fields = [
                FieldDefinition(key="location", label_he="מיקום", label_en="Location",
                                field_type="short_text", is_required=True, sort_order=1),
                FieldDefinition(key="device_type", label_he="סוג מכשיר", label_en="Device Type",
                                field_type="single_select", is_required=True, sort_order=2,
                                configuration_json={"options": ["מחשב", "טלפון", "מדפסת"]}),
                FieldDefinition(key="details", label_he="פרטים נוספים", label_en="Additional Details",
                                field_type="long_text", sort_order=3),
            ]
            db.add(form)
            db.flush()
        request_type.form_version_id = form.id
        db.commit()


if __name__ == "__main__":
    run()
