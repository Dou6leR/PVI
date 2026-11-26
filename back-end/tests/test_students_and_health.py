from api.v1.ai import agent as ai_agent_module
from api.v1.ai.rag import rag_store
from tests.conftest import make_basic_auth, build_minimal_pdf


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ai_status_endpoint(client):
    resp = client.get("/api/v1/ai/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mcp_enabled"] is True
    assert data["ollama_reachable"] is True
    assert data["ollama_embedding_ready"] is True
    assert data["provider"] == "Ollama (qwen3.5:4b)"
    assert isinstance(data["rag_chunks_count"], int)


def test_no_offline_fallback_returns_503_when_ai_unavailable(client, monkeypatch, isolated_students):
    s1, _ = isolated_students

    # Simulate Ollama unreachable and no Gemini API key
    monkeypatch.setattr(
        ai_agent_module.ai_agent,
        "_check_ollama_sync",
        lambda: {"reachable": False, "models": []},
    )

    def _fail_embed(_text: str):
        raise ConnectionRefusedError("Ollama is down")

    monkeypatch.setattr(rag_store, "_call_ollama_embed_sync", _fail_embed)

    status_resp = client.get("/api/v1/ai/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["ollama_reachable"] is False
    assert status_resp.json()["ollama_embedding_ready"] is False
    assert "Unavailable" in status_resp.json()["provider"]

    chat_resp = client.post("/api/v1/ai/chat", json={"message": "Привіт", "student_id": s1.id})
    assert chat_resp.status_code == 503

    pdf_resp = client.post(
        "/api/v1/ai/rag/upload-pdf",
        data={"subject": "", "chat_id": "down-chat", "student_id": str(s1.id)},
        files={"file": ("note.pdf", build_minimal_pdf("Test"), "application/pdf")},
    )
    assert pdf_resp.status_code == 503

    quiz_resp = client.post(
        "/api/v1/ai/tests/generate-quiz",
        json={"student_id": s1.id, "topic": "FastAPI", "num_questions": 2},
    )
    assert quiz_resp.status_code == 503

    coach_resp = client.post(
        "/api/v1/ai/tests/study-coach",
        json={"student_id": s1.id, "topic": "FastAPI", "score": 1, "total": 3, "mistakes": []},
    )
    assert coach_resp.status_code == 503


def test_student_login_and_auth_guard(client, isolated_students):
    s1, _ = isolated_students

    # Unauthenticated request rejected
    unauth = client.get("/api/v1/student/")
    assert unauth.status_code == 401

    # Wrong password rejected
    bad_login = client.post(
        "/api/v1/student/login",
        headers=make_basic_auth(s1.first_name, s1.last_name, "01.01.1999"),
    )
    assert bad_login.status_code == 401

    # Valid credentials succeed
    ok_login = client.post(
        "/api/v1/student/login",
        headers=make_basic_auth(s1.first_name, s1.last_name, s1.password),
    )
    assert ok_login.status_code == 200
    payload = ok_login.json()
    assert payload[0]["student_id"] == s1.id

    # Authenticated student search finds test student
    search = client.get(
        f"/api/v1/student/search?input_search={s1.first_name}",
        headers=make_basic_auth(s1.first_name, s1.last_name, s1.password),
    )
    assert search.status_code == 200
    names = [item["first_name"] for item in search.json()["data"]]
    assert s1.first_name in names
