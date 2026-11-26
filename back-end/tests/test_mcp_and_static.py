import json
from pathlib import Path


def _mcp(client, method: str, params: dict | None = None) -> dict:
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )
    assert resp.status_code == 200
    return resp.json()


def test_mcp_protocol_and_student_isolation(client, isolated_students):
    s1, s2 = isolated_students

    init_res = _mcp(client, "initialize")
    assert init_res["result"]["protocolVersion"] == "2024-11-05"

    tools = _mcp(client, "tools/list")["result"]["tools"]
    tool_names = {t["name"] for t in tools}
    assert {
        "search_students",
        "get_group_students",
        "get_system_stats",
        "list_student_documents",
        "query_subject_knowledge",
        "add_knowledge",
    }.issubset(tool_names)

    # Stats tool
    stats_text = _mcp(client, "tools/call", {"name": "get_system_stats", "arguments": {}})["result"]["content"][0]["text"]
    stats = json.loads(stats_text)
    assert stats["total_students"] >= 2

    # Private add_knowledge + list + search + resources/list isolation
    add_text = _mcp(
        client,
        "tools/call",
        {
            "name": "add_knowledge",
            "arguments": {
                "student_id": s1.id,
                "chat_id": "mcp-ci-chat",
                "title": "CI Note",
                "content": "MCP Vector Verification 991144",
            },
        },
    )["result"]["content"][0]["text"]
    assert json.loads(add_text)["status"] == "success"

    docs_s1 = json.loads(
        _mcp(client, "tools/call", {"name": "list_student_documents", "arguments": {"student_id": s1.id, "chat_id": "mcp-ci-chat"}})["result"]["content"][0]["text"]
    )
    assert len(docs_s1) == 1

    hits_s1 = json.loads(
        _mcp(client, "tools/call", {"name": "query_subject_knowledge", "arguments": {"query": "Verification 991144", "student_id": s1.id, "chat_id": "mcp-ci-chat"}})["result"]["content"][0]["text"]
    )
    hits_s2 = json.loads(
        _mcp(client, "tools/call", {"name": "query_subject_knowledge", "arguments": {"query": "Verification 991144", "student_id": s2.id, "chat_id": "mcp-ci-chat"}})["result"]["content"][0]["text"]
    )
    assert len(hits_s1) == 1 and "991144" in hits_s1[0]["text"]
    assert len(hits_s2) == 0

    resources = _mcp(client, "resources/list", {"student_id": s1.id, "chat_id": "mcp-ci-chat"})["result"]["resources"]
    assert len(resources) == 1
    assert resources[0]["uri"].startswith(f"cms://rag/{s1.id}/mcp-ci-chat/")

    # Unknown tool returns JSON-RPC -32601 error
    err = _mcp(client, "tools/call", {"name": "nonexistent_tool", "arguments": {}})
    assert err["error"]["code"] == -32601


def test_n8n_workflow_json_validity():
    repo_root = Path(__file__).resolve().parents[2]
    wf_path = repo_root / "n8n" / "workflows" / "study_coach.json"
    if not wf_path.exists():
        # Inside Docker container only /app/app and /app/tests are copied
        return
    data = json.loads(wf_path.read_text(encoding="utf-8"))
    node_names = {n["name"] for n in data.get("nodes", [])}
    assert {"Webhook Trigger", "IF Score < 70%", "Ollama GPU", "Respond to Webhook"}.issubset(node_names)
