from typing import Any

from app.modules.directory.provider import DirectoryBatch, NormalizedDirectoryUser


class FakeDirectoryProvider:
    name = "fake"

    def test_connection(self) -> dict[str, Any]:
        return {"ok": True, "message": "Fake Directory זמין לבדיקות", "steps": [
            {"code": "provider", "label": "ספק בדיקות זמין", "ok": True, "message": "מוכן"},
            {"code": "users", "label": "מקור משתמשים נגיש", "ok": True, "message": "3 משתמשי בדיקה"},
        ]}

    def fetch_users(self, delta_link: str | None = None) -> DirectoryBatch:
        rows = [
            ("fake-dana", "dana.cohen@example.com", "דנה כהן", "דנה", "כהן", "procurement", "מנהלת רכש", True),
            ("fake-uri", "uri.levi@example.com", "אורי לוי", "אורי", "לוי", "IT", "Help Desk", True),
            ("fake-ronit", "ronit.israeli@example.com", "רונית ישראלי", "רונית", "ישראלי", "Finance", "חשבת", False),
        ]
        return DirectoryBatch(users=[NormalizedDirectoryUser(
            directory_object_id=row[0], user_principal_name=row[1], email=row[1], display_name=row[2],
            first_name=row[3], last_name=row[4], department=row[5], job_title=row[6], directory_enabled=row[7],
        ) for row in rows], delta_link="fake-delta-v1")
