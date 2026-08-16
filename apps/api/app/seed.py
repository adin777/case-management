import uuid

from pwdlib.exceptions import PwdlibError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.modules.access.mapping import DOMAIN_DEFINITIONS, codes
from app.modules.access.models import AccessLevelAssignment, PermissionDomain
from app.modules.api import ALL_PERMISSIONS, password_hash
from app.modules.employees.service import sync_employee_for_user
from app.modules.models import (
    Environment,
    EnvironmentMembership,
    FieldDefinition,
    FormDefinition,
    FormStatus,
    GlobalPriorityDefinition,
    GlobalStatusDefinition,
    GlobalSubPriorityDefinition,
    Group,
    GroupMember,
    Permission,
    PriorityDefinition,
    RequestType,
    Role,
    RolePermission,
    SubPriorityDefinition,
    User,
)
from app.modules.numbering.service import NumberingService
from app.modules.operations.models import SlaPolicy, WorkflowDefinition, WorkflowStatus, WorkflowTransition


def ensure_foundation(db: Session, admin: User) -> None:
    for order, definition in enumerate(DOMAIN_DEFINITIONS):
        code, name, description, category, scope, view_codes, edit_codes = definition
        domain = db.get(PermissionDomain, code)
        if not domain:
            domain = PermissionDomain(code=code)
            db.add(domain)
        domain.name_he, domain.description_he, domain.category, domain.scope = name, description, category, scope
        domain.view_permissions, domain.edit_permissions = view_codes, edit_codes
        domain.sort_order, domain.is_active = order, True


def run(*, include_demo_data: bool = False) -> None:
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
            "workflow.read": ("צפייה בתהליכי עבודה", "מאפשר צפייה בתהליכי העבודה של הסביבה"),
            "workflow.manage": ("ניהול תהליכי עבודה", "מאפשר יצירה ועריכה של סטטוסים ומעברים"),
            "sla.read": ("צפייה במדיניות SLA", "מאפשר צפייה בזמני השירות שהוגדרו"),
            "sla.manage": ("ניהול מדיניות SLA", "מאפשר יצירה ועריכה של יעדי תגובה ופתרון"),
            "attachment.read": ("צפייה בקבצים מצורפים", "מאפשר צפייה והורדה של קבצים בקריאה מורשית"),
            "attachment.upload": ("העלאת קבצים", "מאפשר צירוף קבצים לקריאה או לתגובה"),
            "attachment.delete": ("מחיקת קבצים", "מאפשר מחיקה לוגית של קבצים מצורפים"),
            "notification.read_own": ("צפייה בהתראות שלי", "מאפשר צפייה וסימון התראות אישיות"),
            "notification.manage": ("ניהול התראות", "מאפשר ניהול הגדרות ותשתית ההתראות"),
            "audit.read_system": ("צפייה ביומן מערכת", "מאפשר צפייה באירועי ביקורת מכל הסביבות"),
            "audit.read_environment": ("צפייה ביומן סביבה", "מאפשר צפייה באירועי ביקורת בסביבה מורשית"),
            "case.read_status_history": ("צפייה בהיסטוריית טיפול", "מאפשר צפייה במעברי הסטטוס של הקריאה"),
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
        seed_users = [("admin@example.com", "מנהל מערכת", "Admin123!", True)]
        if include_demo_data:
            seed_users += [
                ("envadmin@example.com", "מנהל סביבת IT", "EnvAdmin123!", False),
                ("requester@example.com", "משתמש קצה", "Requester123!", False),
                ("agent@example.com", "מטפל", "Agent123!", False),
            ]
        for email, name, password, is_admin in seed_users:
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
            sync_employee_for_user(db, user)
            users[email] = user

        ensure_foundation(db, users["admin@example.com"])
        if not include_demo_data:
            db.commit()
            return

        env = db.scalar(select(Environment).where(Environment.code == "IT"))
        if not env:
            env = Environment(code="IT", system_number=NumberingService.next(db, "environment"),
                              name_he="שירותי IT", name_en="IT Service",
                              description="סביבת שירותי טכנולוגיה")
            db.add(env)
            db.flush()
        elif not env.system_number:
            env.system_number = NumberingService.next(db, "environment")
        for email, role_code in ([
            ("envadmin@example.com", "environment_admin"),
            ("requester@example.com", "requester"),
            ("agent@example.com", "agent"),
        ] if include_demo_data else []):
            if not db.scalar(select(EnvironmentMembership).where(
                EnvironmentMembership.environment_id == env.id,
                EnvironmentMembership.user_id == users[email].id,
                EnvironmentMembership.role_id == roles[role_code].id,
            )):
                db.add(EnvironmentMembership(environment_id=env.id, user_id=users[email].id,
                                             role_id=roles[role_code].id))

        base_groups: dict[str, Group] = {}
        for name, description in [
            ("אדמין", "מנהלי מערכת בעלי גישה מלאה"),
            ("מנהל סביבה", "מנהלים לפי שיוך לסביבה"),
            ("משתמש", "משתמשים בעלי הרשאות בסיס שהוגדרו במפורש"),
        ]:
            group = db.scalar(select(Group).where(Group.name == name))
            if not group:
                group = Group(system_number=f"UG-{uuid.uuid4().hex[:8].upper()}", name=name, description=description, is_active=True)
                db.add(group)
                db.flush()
            base_groups[name] = group
        if not db.get(GroupMember, (base_groups["אדמין"].id, users["admin@example.com"].id)):
            db.add(GroupMember(group_id=base_groups["אדמין"].id, user_id=users["admin@example.com"].id, added_by=users["admin@example.com"].id))

        for order, definition in enumerate(DOMAIN_DEFINITIONS):
            code, name, description, category, scope, view_codes, edit_codes = definition
            domain = db.get(PermissionDomain, code)
            if not domain:
                domain = PermissionDomain(code=code)
                db.add(domain)
            domain.name_he = name
            domain.description_he = description
            domain.category = category
            domain.scope = scope
            domain.view_permissions = view_codes
            domain.edit_permissions = edit_codes
            domain.sort_order = order
            domain.is_active = True

        db.flush()
        for membership in db.scalars(select(EnvironmentMembership)):
            role = db.get(Role, membership.role_id)
            role_codes = set(role.permissions or []) if role else set()
            for domain in db.scalars(select(PermissionDomain).where(PermissionDomain.is_active.is_(True))):
                level = "edit" if role_codes & codes(domain.edit_permissions) else (
                    "view" if role_codes & codes(domain.view_permissions) else None
                )
                if level and not db.scalar(select(AccessLevelAssignment.id).where(
                    AccessLevelAssignment.user_id == membership.user_id,
                    AccessLevelAssignment.domain_code == domain.code,
                    AccessLevelAssignment.environment_id == membership.environment_id,
                )):
                    db.add(AccessLevelAssignment(domain_code=domain.code, user_id=membership.user_id,
                        group_id=None, environment_id=membership.environment_id,
                        access_level=level, created_by=users["admin@example.com"].id))

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
        workflow = db.scalar(
            select(WorkflowDefinition).where(
                WorkflowDefinition.environment_id == env.id,
                WorkflowDefinition.name_he == "טיפול בבקשת הרשאה",
            )
        )
        if not workflow:
            workflow = WorkflowDefinition(
                system_number=f"WF-{uuid.uuid4().hex[:8].upper()}",
                environment_id=env.id,
                name_he="טיפול בבקשת הרשאה",
                name_en="Access request handling",
                description="תהליך ברירת מחדל לטיפול מסודר בקריאות שירות",
                is_default=True,
                created_by=users["admin@example.com"].id,
            )
            db.add(workflow)
            db.flush()
        statuses: dict[str, WorkflowStatus] = {}
        definitions = [
            ("new", "חדש", False, False),
            ("review", "בבדיקה", False, False),
            ("approval", "ממתין לאישור", False, False),
            ("implementation", "בביצוע", False, False),
            ("completed", "הושלם", True, True),
        ]
        for order, (code, label, is_final, is_closed) in enumerate(definitions):
            status = db.scalar(
                select(WorkflowStatus).where(
                    WorkflowStatus.workflow_id == workflow.id, WorkflowStatus.code == code
                )
            )
            if not status:
                status = WorkflowStatus(
                    workflow_id=workflow.id,
                    code=code,
                    label_he=label,
                    sort_order=order,
                    is_initial=order == 0,
                    is_final=is_final,
                    is_closed=is_closed,
                )
                db.add(status)
                db.flush()
            statuses[code] = status
        for order, (source, target, label) in enumerate(
            [
                ("new", "review", "העבר לבדיקה"),
                ("review", "approval", "בקש אישור"),
                ("approval", "implementation", "העבר לביצוע"),
                ("implementation", "completed", "סמן כהושלם"),
            ]
        ):
            if not db.scalar(
                select(WorkflowTransition).where(
                    WorkflowTransition.workflow_id == workflow.id,
                    WorkflowTransition.from_status_id == statuses[source].id,
                    WorkflowTransition.to_status_id == statuses[target].id,
                )
            ):
                db.add(
                    WorkflowTransition(
                        workflow_id=workflow.id,
                        from_status_id=statuses[source].id,
                        to_status_id=statuses[target].id,
                        label_he=label,
                        sort_order=order,
                    )
                )
        for priority_row in priorities.values():
            if not db.get(GlobalPriorityDefinition, priority_row.id):
                db.add(GlobalPriorityDefinition(id=priority_row.id, code=f"legacy_{priority_row.code}_{str(priority_row.id).replace('-', '')[:8]}",
                    label_he=priority_row.label_he, label_en=priority_row.label_en, is_active=priority_row.is_active,
                    sort_order=priority_row.sort_order, color=priority_row.color))
        for sub_priority_row in db.scalars(select(SubPriorityDefinition).where(SubPriorityDefinition.environment_id == env.id)):
            if not db.get(GlobalSubPriorityDefinition, sub_priority_row.id):
                db.add(GlobalSubPriorityDefinition(id=sub_priority_row.id, code=f"legacy_{sub_priority_row.code}_{str(sub_priority_row.id).replace('-', '')[:8]}",
                    label_he=sub_priority_row.label_he, label_en=sub_priority_row.label_en, is_active=sub_priority_row.is_active,
                    sort_order=sub_priority_row.sort_order, color=sub_priority_row.color))
        has_initial = bool(db.scalar(select(GlobalStatusDefinition).where(GlobalStatusDefinition.is_initial.is_(True))))
        for index, status_row in enumerate(statuses.values()):
            if not db.get(GlobalStatusDefinition, status_row.id):
                db.add(GlobalStatusDefinition(id=status_row.id, code=f"legacy_{status_row.code}_{str(status_row.id).replace('-', '')[:8]}",
                    label_he=status_row.label_he, label_en=status_row.label_en,
                    semantic_category="closed" if status_row.is_closed else ("resolved" if status_row.is_final else "open"),
                    is_active=status_row.is_active, is_initial=not has_initial and index == 0,
                    is_final=status_row.is_final, sort_order=status_row.sort_order, color=status_row.color))
        request_type.workflow_definition_id = workflow.id
        if not db.scalar(select(SlaPolicy).where(SlaPolicy.environment_id == env.id)):
            db.add(
                SlaPolicy(
                    system_number=f"SLA-{uuid.uuid4().hex[:8].upper()}",
                    environment_id=env.id,
                    request_type_id=request_type.id,
                    priority_id=priorities["critical"].id,
                    name_he="תגובה תוך 30 דקות, פתרון תוך 4 שעות",
                    response_minutes=30,
                    resolution_minutes=240,
                )
            )
        db.commit()


if __name__ == "__main__":
    run()
