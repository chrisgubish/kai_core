from fastapi.testclient import TestClient
from backend.api.persona_api import app

client = TestClient(app)

def test_chat_endpoint_kai():
    resp = client.post("/chat", json={"user_input": "Hello Kai!", "persona": "kai"})
    assert resp.status_code == 200
    assert "response" in resp.json()

def test_chat_endpoint_eden():
    resp = client.post("/chat", json={"user_input": "Hello Eden!", "persona": "eden"})
    assert resp.status_code == 200
    assert "response" in resp.json()

def test_chat_endpoint_empty():
    resp = client.post("/chat", json={"user_input": ""})
    assert resp.status_code == 200
    assert "error" in resp.json()

def test_chat_endpoint_invalid_persona():
    resp = client.post("/chat", json={"user_input": "Test unknown persona", "persona": "unknown"})
    assert resp.status_code == 200
    assert "response" in resp.json() or "error" in resp.json()

def test_chat_endpoint_abuse_filter():
    resp = client.post("/chat", json={"user_input": "Let's talk about sex"})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "not the space" in data["response"] or "support emotional" in data["response"]

def test_memory_endpoint():
    resp = client.get("/memory")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list) or isinstance(resp.json(), dict)

def test_dreamlog_endpoint():
    resp = client.get("/dreamlog?n=2")
    assert resp.status_code == 200
    assert "logs" in resp.json() or "error" in resp.json()

def test_clear_session_endpoint():
    resp = client.post("/clear_session", json={"session_id": "testsession"})
    assert resp.status_code == 200
    assert "status" in resp.json()
