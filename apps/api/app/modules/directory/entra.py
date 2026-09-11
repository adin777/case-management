import json
import urllib.parse
import urllib.request

from app.modules.directory.provider import DirectoryBatch, NormalizedDirectoryUser


class EntraDirectoryProvider:
    name = "entra"
    def __init__(self,configuration:dict|None=None,secret:str|None=None)->None:
        self.configuration=configuration or {};self.secret=secret

    def _token(self) -> str:
        tenant=self.configuration.get("tenant_id");client=self.configuration.get("client_id")
        if not all((tenant,client,self.secret)):
            raise ValueError("חסרה תצורת Microsoft Entra")
        body = urllib.parse.urlencode({"client_id": client,
            "client_secret": self.secret, "scope": self.configuration.get("scope","https://graph.microsoft.com/.default"),
            "grant_type": "client_credentials"}).encode()
        request = urllib.request.Request(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=body)
        with urllib.request.urlopen(request, timeout=15) as response:
            return str(json.load(response)["access_token"])

    def test_connection(self) -> dict:
        configured = [("tenant", "Tenant ID מוגדר", bool(self.configuration.get("tenant_id"))), ("client", "Client ID מוגדר", bool(self.configuration.get("client_id"))), ("secret", "Client Secret מוגדר", bool(self.secret))]
        steps = [{"code": code, "label": label, "ok": ok, "message": "מוגדר" if ok else "חסר"} for code, label, ok in configured]
        if not all(ok for _, _, ok in configured): return {"ok": False, "message": "תצורת Microsoft Entra חסרה", "steps": steps}
        try:
            token = self._token(); steps.append({"code": "token", "label": "קבלת token", "ok": True, "message": "הצליחה"})
            graph=self.configuration.get("graph_base_url","https://graph.microsoft.com/v1.0").rstrip("/")
            request = urllib.request.Request(f"{graph}/users?$top=1&$select=id", headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(request, timeout=15) as response: json.load(response)
            steps.extend([{"code":"graph","label":"Microsoft Graph נגיש","ok":True,"message":"תקין"},{"code":"users","label":"Users endpoint נגיש","ok":True,"message":"תקין"}])
            return {"ok": True, "message": "החיבור ל־Microsoft Entra תקין", "steps": steps}
        except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
            steps.append({"code":"connection","label":"אימות וגישה ל־Graph","ok":False,"message":str(exc)})
            return {"ok": False, "message": "בדיקת Microsoft Entra נכשלה", "steps": steps}

    def fetch_users(self, delta_link: str | None = None) -> DirectoryBatch:
        graph=self.configuration.get("graph_base_url","https://graph.microsoft.com/v1.0").rstrip("/")
        url = delta_link or (f"{graph}/users/delta?" + urllib.parse.urlencode({
            "$select": "id,userPrincipalName,mail,displayName,givenName,surname,department,jobTitle,mobilePhone,businessPhones,accountEnabled"}))
        users: list[NormalizedDirectoryUser] = []; token = self._token(); next_url: str | None = url; final_delta = None
        while next_url:
            request = urllib.request.Request(next_url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(request, timeout=30) as response: payload = json.load(response)
            for row in payload.get("value", []):
                email = row.get("mail") or row.get("userPrincipalName")
                if email: users.append(NormalizedDirectoryUser(directory_object_id=row.get("id"),
                    user_principal_name=row.get("userPrincipalName"), email=email,
                    display_name=row.get("displayName") or email, first_name=row.get("givenName"),
                    last_name=row.get("surname"), department=row.get("department"), job_title=row.get("jobTitle"),
                    mobile_phone=row.get("mobilePhone"), phone=(row.get("businessPhones") or [None])[0],
                    directory_enabled=bool(row.get("accountEnabled", True))))
            next_url = payload.get("@odata.nextLink"); final_delta = payload.get("@odata.deltaLink") or final_delta
        return DirectoryBatch(users=users, delta_link=final_delta)
