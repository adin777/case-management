from typing import Any

from app.core.config import settings
from app.modules.directory.provider import DirectoryBatch, NormalizedDirectoryUser


class ActiveDirectoryProvider:
    name = "active_directory"

    def _connection(self) -> Any:
        if not all((settings.active_directory_server, settings.active_directory_base_dn,
                    settings.active_directory_bind_user, settings.active_directory_bind_password)):
            raise ValueError("חסרה תצורת Active Directory מקומי")
        try:
            from ldap3 import ALL, Connection, Server
        except ImportError as exc:
            raise ValueError("המחבר ldap3 אינו מותקן") from exc
        server = Server(settings.active_directory_server, use_ssl=settings.active_directory_use_ssl, get_info=ALL)
        return Connection(server, user=settings.active_directory_bind_user,
                          password=settings.active_directory_bind_password, auto_bind=True)

    def test_connection(self) -> dict[str, str | bool]:
        connection = self._connection()
        connection.unbind()
        return {"ok": True, "message": "החיבור ל־Active Directory תקין"}

    def fetch_users(self, delta_link: str | None = None) -> DirectoryBatch:
        connection = self._connection()
        attributes = ["objectGUID", "userPrincipalName", "mail", "displayName", "givenName", "sn",
                      "department", "title", "telephoneNumber", "mobile", "employeeID", "userAccountControl"]
        connection.search(settings.active_directory_base_dn, "(&(objectClass=user)(objectCategory=person))",
                          attributes=attributes, paged_size=500)
        users: list[NormalizedDirectoryUser] = []
        for entry in connection.entries:
            values = entry.entry_attributes_as_dict
            email = self._first(values, "mail") or self._first(values, "userPrincipalName")
            if not email:
                continue
            account_control = int(self._first(values, "userAccountControl") or 0)
            users.append(NormalizedDirectoryUser(
                directory_object_id=str(self._first(values, "objectGUID") or "") or None,
                user_principal_name=self._first(values, "userPrincipalName"), email=email,
                display_name=self._first(values, "displayName") or email,
                first_name=self._first(values, "givenName"), last_name=self._first(values, "sn"),
                department=self._first(values, "department"), job_title=self._first(values, "title"),
                phone=self._first(values, "telephoneNumber"), mobile_phone=self._first(values, "mobile"),
                employee_id=self._first(values, "employeeID"), directory_enabled=not bool(account_control & 2)))
        connection.unbind()
        return DirectoryBatch(users=users)

    @staticmethod
    def _first(values: dict[str, Any], key: str) -> Any:
        value = values.get(key)
        return value[0] if isinstance(value, list) and value else value
