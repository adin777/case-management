from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SystemField:
    code: str
    label_he: str
    description_he: str
    value_source: str
    is_core: bool = True
    supports_options: bool = True
    supports_environment_scope: bool = True
    is_active: bool = True
    is_target: bool = True


SYSTEM_FIELDS = (
    SystemField("environment", "סביבה", "סביבת העבודה של הקריאה", "Environment", is_target=False),
    SystemField("request_type", "סוג קריאה", "סיווג הקריאה והגדרותיה", "RequestType", is_target=False),
    SystemField("status", "סטטוס", "שלב הקריאה בתהליך העבודה", "WorkflowStatus"),
    SystemField("priority", "עדיפות", "רמת העדיפות של הקריאה", "PriorityDefinition"),
    SystemField("sub_priority", "תת-עדיפות", "סיווג משני עצמאי בסביבה", "SubPriorityDefinition"),
    SystemField("assignee", "מטפל", "המשתמש המטפל בקריאה", "User"),
    SystemField("assignee_group", "קבוצה מטפלת", "קבוצת הטיפול בקריאה", "Group"),
    SystemField("participants", "משתתפים", "משתמשים המשתתפים בקריאה", "User"),
)
BY_CODE = {field.code: field for field in SYSTEM_FIELDS}


def registry_payload() -> list[dict]:
    return [asdict(field) for field in SYSTEM_FIELDS if field.is_active]
