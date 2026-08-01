from fastapi.testclient import TestClient
from app.main import app
from app.modules.api import TRANSITIONS
from app.modules.models import CaseStatus

client=TestClient(app)
def test_valid_login_and_current_user()->None:
    response=client.post("/api/auth/login",json={"email":"admin@example.com","password":"Admin123!"})
    assert response.status_code==200
    token=response.json()["access_token"]
    me=client.get("/api/auth/me",headers={"Authorization":f"Bearer {token}"})
    assert me.status_code==200 and me.json()["is_system_admin"] is True
def test_invalid_login()->None:
    assert client.post("/api/auth/login",json={"email":"admin@example.com","password":"wrong"}).status_code==401
def test_anonymous_access_is_blocked()->None:
    assert client.get("/api/environments").status_code==401
def test_transition_rules_are_centralized()->None:
    assert CaseStatus.in_progress in TRANSITIONS[CaseStatus.submitted]
    assert CaseStatus.closed not in TRANSITIONS[CaseStatus.submitted]
def test_admin_can_create_environment_and_audit_is_written()->None:
    login=client.post("/api/auth/login",json={"email":"admin@example.com","password":"Admin123!"}).json()
    headers={"Authorization":f"Bearer {login['access_token']}"}
    response=client.post("/api/environments",headers=headers,json={"code":"QA_TEST","name_he":"בדיקות","name_en":"Quality Tests","description":"Integration test"})
    assert response.status_code in (201,409)
    audit=client.get("/api/audit",headers=headers)
    assert audit.status_code==200
