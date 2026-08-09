from typing import Protocol

from pydantic import BaseModel, EmailStr


class NormalizedDirectoryUser(BaseModel):
    directory_object_id: str | None = None
    user_principal_name: str | None = None
    email: EmailStr
    display_name: str
    first_name: str | None = None
    last_name: str | None = None
    department: str | None = None
    job_title: str | None = None
    phone: str | None = None
    mobile_phone: str | None = None
    employee_id: str | None = None
    computer_identifier: str | None = None
    directory_enabled: bool = True


class DirectoryBatch(BaseModel):
    users: list[NormalizedDirectoryUser]
    delta_link: str | None = None


class DirectoryProvider(Protocol):
    name: str
    def test_connection(self) -> dict[str, str | bool]: ...
    def fetch_users(self, delta_link: str | None = None) -> DirectoryBatch: ...
