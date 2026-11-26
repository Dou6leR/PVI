from tests.conftest import make_basic_auth


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ai_status_endpoint(client):
    resp = client.get("/api/v1/ai/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mcp_enabled"] is True
    assert isinstance(data["rag_chunks_count"], int)


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
