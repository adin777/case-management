DOMAIN_DEFINITIONS = [
    ("users", "משתמשים", "ניהול זהויות, מצב משתמש וסיסמאות", "system", "system.users.read", "system.users.create,system.users.update,system.users.disable,system.users.reset_password"),
    ("groups", "קבוצות משתמשים", "ניהול קבוצות וחברויות", "system", "system.groups.read", "system.groups.manage"),
    ("access", "הרשאות", "ניהול רמות גישה והעתקת הרשאות", "system", "system.roles.read", "system.roles.manage"),
    ("environments", "סביבות עבודה", "צפייה וניהול סביבות", "environment", "environment.read", "environment.manage"),
    ("request_types", "סוגי קריאות", "ניהול קטלוג סוגי הקריאות", "environment", "request_type.read", "request_type.manage,environment.request_types.manage"),
    ("case_fields", "שדות קריאה", "ניהול שדות וערכי בחירה", "environment", "environment.read", "environment.fields.manage,environment.forms.manage"),
    ("user_fields", "שדות משתמש", "ניהול שדות משתמש וערכיהם", "system", "system.fields.read", "system.fields.manage"),
    ("priorities", "עדיפויות", "ניהול עדיפויות ותת־עדיפויות", "environment", "environment.read", "environment.manage"),
    ("workflows", "סטטוסים ותהליכי עבודה", "ניהול Workflow, סטטוסים ומעברים", "environment", "workflow.read", "workflow.manage"),
    ("automation", "כללים אוטומטיים", "ניהול טריגרים, תנאים ופעולות", "environment", "environment.read", "environment.rules.manage"),
    ("cases", "קריאות שירות", "צפייה או ניהול קריאות", "environment", "case.read,case.read_environment", "case.create,case.update,case.assign,case.change_status,case.lock"),
    ("public_comments", "תגובות ציבוריות", "צפייה וכתיבה בשיחה הציבורית", "environment", "comment.public.read", "comment.public.create,case.comment"),
    ("manager_comments", "הודעות מנהלים", "צפייה וכתיבה בשיחה פנימית", "environment", "comment.manager.read", "comment.manager.create,case.internal_comment"),
    ("participants", "משתתפים", "צפייה וניהול משתתפי קריאה", "environment", "case.read_participating", "case.manage_participants"),
    ("approvals", "סבבי אישורים", "הגדרה וצפייה בסבבי אישורים", "environment", "environment.read", "environment.manage"),
    ("reports", "דוחות", "צפייה וייצוא דוחות", "environment", "case.read_environment", "case.read_environment"),
    ("attachments", "קבצים מצורפים", "צפייה וניהול קבצים", "environment", "attachment.read", "attachment.upload,attachment.delete"),
    ("notifications", "התראות", "צפייה וניהול התראות", "environment", "notification.read_own", "notification.manage"),
    ("audit", "יומן ביקורת", "צפייה באירועי מערכת או סביבה", "environment", "audit.read_environment", "audit.read_system"),
    ("sla", "SLA", "צפייה וניהול יעדי שירות", "environment", "sla.read", "sla.manage"),
]


def codes(value: str) -> set[str]:
    return {code for code in value.split(",") if code}
