from typing import Any

from app.modules.directory.provider import DirectoryBatch, NormalizedDirectoryUser


class ActiveDirectoryProvider:
    name = "active_directory"
    def __init__(self,configuration:dict|None=None,secret:str|None=None)->None:
        self.configuration=configuration or {};self.secret=secret

    def _connection(self) -> Any:
        if not all((self.configuration.get("host"),self.configuration.get("base_dn"),
                    self.configuration.get("bind_username"),self.secret)):
            raise ValueError("חסרה תצורת Active Directory מקומי")
        try:
            from ldap3 import ALL, Connection, Server
        except ImportError as exc:
            raise ValueError("המחבר ldap3 אינו מותקן") from exc
        server = Server(self.configuration["host"],port=int(self.configuration.get("port",636 if self.configuration.get("use_ssl",True) else 389)),use_ssl=bool(self.configuration.get("use_ssl",True)),get_info=ALL)
        return Connection(server,user=self.configuration["bind_username"],password=self.secret,auto_bind=True)

    def test_connection(self) -> dict:
        checks = [("server", "שרת מוגדר", bool(self.configuration.get("host"))), ("base_dn", "Base DN מוגדר", bool(self.configuration.get("base_dn"))), ("bind", "פרטי Bind מוגדרים", bool(self.configuration.get("bind_username") and self.secret))]
        steps = [{"code": code, "label": label, "ok": ok, "message": "מוגדר" if ok else "חסר"} for code, label, ok in checks]
        if not all(ok for _, _, ok in checks): return {"ok": False, "message": "תצורת Active Directory חסרה", "steps": steps}
        try:
            connection = self._connection(); steps.extend([{"code":"reachable","label":"השרת נגיש","ok":True,"message":"LDAP/LDAPS מחובר"},{"code":"bind_success","label":"Bind הצליח","ok":True,"message":"תקין"}])
            found = connection.search(self.configuration["base_dn"], "(objectClass=*)", attributes=[], size_limit=1)
            steps.extend([{"code":"base_dn_access","label":"Base DN נגיש","ok":bool(found),"message":"תקין" if found else "לא נגיש"},{"code":"user_query","label":"שאילתת משתמשים","ok":bool(found),"message":"הצליחה" if found else "נכשלה"}])
            connection.unbind(); return {"ok": bool(found), "message": "החיבור ל־Active Directory תקין" if found else "Base DN אינו נגיש", "steps": steps}
        except (ValueError, ImportError, OSError) as exc:
            steps.append({"code":"connection","label":"חיבור LDAP/LDAPS ו־Bind","ok":False,"message":str(exc)})
            return {"ok": False, "message": "בדיקת Active Directory נכשלה", "steps": steps}

    def fetch_users(self, delta_link: str | None = None) -> DirectoryBatch:
        connection = self._connection()
        attributes = ["objectGUID", "userPrincipalName", "mail", "displayName", "givenName", "sn",
                      "department", "title", "telephoneNumber", "mobile", "employeeID", "userAccountControl"]
        connection.search(self.configuration.get("user_search_base") or self.configuration["base_dn"],self.configuration.get("user_filter") or "(&(objectClass=user)(objectCategory=person))",
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
