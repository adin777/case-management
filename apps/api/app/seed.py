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
    Group,
    GroupEnvironmentRole,
    GroupMember,
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
        for code in ALL_PERMISSIONS:
            if not db.get(Permission, code):
                db.add(Permission(code=code, description=code.replace(".", " ").title()))
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

        support = db.scalar(select(Group).where(Group.name == "צוות תמיכה"))
        if not support:
            support = Group(name="צוות תמיכה", description="קבוצת תמיכה לדוגמה", is_active=True)
            db.add(support)
            db.flush()
        if not db.get(GroupMember, (support.id, users["agent@example.com"].id)):
            db.add(GroupMember(group_id=support.id, user_id=users["agent@example.com"].id,
                               added_by=users["admin@example.com"].id))
        if not db.get(GroupEnvironmentRole, (env.id, support.id, roles["agent"].id)):
            db.add(GroupEnvironmentRole(environment_id=env.id, group_id=support.id,
                                        role_id=roles["agent"].id))

        priorities: dict[str, PriorityDefinition] = {}
        for index, (code, label, color) in enumerate([
            ("low", "נמוכה", "#22c55e"), ("normal", "רגילה", "#3b82f6"),
            ("high", "גבוהה", "#f59e0b"), ("critical", "קריטית", "#ef4444"),
        ]):
            item = db.scalar(select(PriorityDefinition).where(
                PriorityDefinition.environment_id == env.id, PriorityDefinition.code == code))
            if not item:
                item = PriorityDefinition(environment_id=env.id, code=code, label_he=label,
                                          color=color, sort_order=index)
                db.add(item)
                db.flush()
            priorities[code] = item
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
