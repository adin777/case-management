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
    RequestType,
    Role,
    User,
)


def run() -> None:
    if settings.environment != "development":
        return
    with SessionLocal() as db:
        roles = {
            "environment_admin": ALL_PERMISSIONS,
            "agent": [
                "environment.read",
                "request_type.read",
                "case.read",
                "case.update",
                "case.assign",
                "case.comment",
                "case.internal_comment",
                "case.manage_participants",
            ],
            "requester": [
                "environment.read",
                "request_type.read",
                "case.create",
                "case.read",
                "case.comment",
            ],
            "viewer": ["environment.read", "request_type.read", "case.read"],
        }
        role_rows = {}
        for code, perms in roles.items():
            role = db.scalar(select(Role).where(Role.code == code))
            if not role:
                role = Role(code=code, name=code.replace("_", " ").title(), permissions=perms)
                db.add(role)
                db.flush()
            role_rows[code] = role
        users = {}
        for email, name, password, is_admin in [
            ("admin@example.com", "מנהל מערכת", "Admin123!", True),
            ("requester@example.com", "משתמש קצה", "Requester123!", False),
            ("agent@example.com", "מטפל", "Agent123!", False),
        ]:
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(
                    email=email,
                    display_name=name,
                    password_hash=password_hash.hash(password),
                    is_system_admin=is_admin,
                )
                db.add(user)
                db.flush()
            else:
                user.is_active = True
                user.is_system_admin = is_admin
                try:
                    password_is_valid = password_hash.verify(password, user.password_hash)
                except PwdlibError:
                    password_is_valid = False
                if not password_is_valid:
                    user.password_hash = password_hash.hash(password)
            users[email] = user
        env = db.scalar(select(Environment).where(Environment.code == "IT"))
        if not env:
            env = Environment(
                code="IT", name_he="שירותי IT", name_en="IT Service", description="סביבת שירותי טכנולוגיה"
            )
            db.add(env)
            db.flush()
        for email, role_code in [("requester@example.com", "requester"), ("agent@example.com", "agent")]:
            exists = db.scalar(
                select(EnvironmentMembership).where(
                    EnvironmentMembership.environment_id == env.id,
                    EnvironmentMembership.user_id == users[email].id,
                    EnvironmentMembership.role_id == role_rows[role_code].id,
                )
            )
            if not exists:
                db.add(
                    EnvironmentMembership(
                        environment_id=env.id, user_id=users[email].id, role_id=role_rows[role_code].id
                    )
                )
        rt = db.scalar(
            select(RequestType).where(RequestType.environment_id == env.id, RequestType.code == "GENERAL_IT")
        )
        if not rt:
            rt = RequestType(
                environment_id=env.id,
                code="GENERAL_IT",
                name_he="בקשת IT כללית",
                name_en="General IT Request",
                description="בקשת שירות כללית",
            )
            db.add(rt)
            db.flush()
        form = db.scalar(
            select(FormDefinition).where(FormDefinition.request_type_id == rt.id, FormDefinition.version == 1)
        )
        if not form:
            form = FormDefinition(request_type_id=rt.id, version=1, status=FormStatus.published)
            form.fields = [
                FieldDefinition(
                    key="location",
                    label_he="מיקום",
                    label_en="Location",
                    field_type="short_text",
                    is_required=True,
                    sort_order=1,
                ),
                FieldDefinition(
                    key="device_type",
                    label_he="סוג מכשיר",
                    label_en="Device Type",
                    field_type="single_select",
                    is_required=True,
                    sort_order=2,
                    configuration_json={"options": ["מחשב", "טלפון", "מדפסת"]},
                ),
                FieldDefinition(
                    key="urgency",
                    label_he="דחיפות",
                    label_en="Urgency",
                    field_type="single_select",
                    is_required=True,
                    sort_order=3,
                    configuration_json={"options": ["נמוכה", "רגילה", "גבוהה"]},
                ),
                FieldDefinition(
                    key="details",
                    label_he="פרטים נוספים",
                    label_en="Additional Details",
                    field_type="long_text",
                    sort_order=4,
                ),
            ]
            db.add(form)
            db.flush()
        rt.form_version_id = form.id
        db.commit()


if __name__ == "__main__":
    run()
