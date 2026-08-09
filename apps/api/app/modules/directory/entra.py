import json
import urllib.parse
import urllib.request

from app.core.config import settings
from app.modules.directory.provider import DirectoryBatch, NormalizedDirectoryUser


class EntraDirectoryProvider:
    name = "entra"

    def _token(self) -> str:
        if not all((settings.entra_tenant_id, settings.entra_client_id, settings.entra_client_secret)):
            raise ValueError("חסרה תצורת Microsoft Entra")
        body = urllib.parse.urlencode({"client_id": settings.entra_client_id,
            "client_secret": settings.entra_client_secret, "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"}).encode()
        request = urllib.request.Request(f"https://login.microsoftonline.com/{settings.entra_tenant_id}/oauth2/v2.0/token", data=body)
        with urllib.request.urlopen(request, timeout=15) as response:
            return str(json.load(response)["access_token"])

    def test_connection(self) -> dict[str, str | bool]:
        self._token(); return {"ok": True, "message": "החיבור ל־Microsoft Entra תקין"}

    def fetch_users(self, delta_link: str | None = None) -> DirectoryBatch:
        url = delta_link or ("https://graph.microsoft.com/v1.0/users/delta?" + urllib.parse.urlencode({
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
