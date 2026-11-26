import base64
import datetime
import hashlib
import json
import re
from typing import Iterator
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from sqlalchemy import text
from sqlmodel import Session

from main import app
from core import postgres_helper, settings
from core.models import Student
from core.models.rag import EMBEDDING_DIM
from api.v1.ai import agent as ai_agent_module
from api.v1.ai import quiz as ai_quiz_module
from api.v1.ai.rag import rag_store


def make_basic_auth(first_name: str, last_name: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{first_name} {last_name}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def build_minimal_pdf(text_content: str) -> bytes:
    """Builds a minimal single-page readable PDF in memory for pypdf extraction tests."""
    safe_text = text_content.replace("(", "[").replace(")", "]")
    stream_body = f"BT /F1 12 Tf 10 100 Td ({safe_text}) Tj ET".encode("latin-1", errors="replace")
    obj5 = b"5 0 obj << /Length " + str(len(stream_body)).encode() + b" >> stream\n" + stream_body + b"\nendstream endobj\n"
    parts = [
        b"%PDF-1.4\n",
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 300 144] /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        obj5,
    ]
    offsets = []
    pos = len(parts[0])
    for obj in parts[1:]:
        offsets.append(pos)
        pos += len(obj)
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    for off in offsets:
        xref.append(f"{off:010d} 00000 n \n".encode())
    trailer = f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF".encode()
    return b"".join(parts + xref + [trailer])


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """FastAPI TestClient running full lifespan (PostgreSQL + pgvector + MongoDB Beanie)."""
    with TestClient(app) as tc:
        yield tc


def _deterministic_test_embedding(text_input: str) -> np.ndarray:
    """Test-only deterministic 1024-dim vector simulating Ollama bge-m3 without GPU calls."""
    vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    words = re.findall(r"\w+", (text_input or "").lower())
    for w in words:
        idx = int.from_bytes(hashlib.blake2b(w.encode("utf-8"), digest_size=4).digest(), "little") % EMBEDDING_DIM
        vec[idx] += 1.0
    for i in range(max(0, len(text_input) - 2)):
        tri = text_input[i : i + 3].lower()
        idx = int.from_bytes(hashlib.blake2b(tri.encode("utf-8"), digest_size=4).digest(), "little") % EMBEDDING_DIM
        vec[idx] += 0.5
    norm = float(np.linalg.norm(vec))
    return (vec / norm) if norm > 0 else vec


@pytest.fixture(autouse=True)
def mock_ollama_transport(monkeypatch):
    """Mocks Ollama HTTP transport in tests while exercising full pgvector, MongoDB, and agent pipelines."""
    monkeypatch.setattr(settings.ai, "api_key", "")
    monkeypatch.setattr(settings.ai, "ollama_url", "http://127.0.0.1:11499")

    monkeypatch.setattr(rag_store, "_call_ollama_embed_sync", _deterministic_test_embedding)
    monkeypatch.setattr(
        ai_agent_module.ai_agent,
        "_check_ollama_sync",
        lambda: {"reachable": True, "models": ["qwen3.5:4b", "bge-m3:latest"]},
    )

    def _fake_ollama_chat(model: str, messages: list[dict]) -> str:
        user_content = messages[-1].get("content", "") if messages else ""
        if "пройшов тест" in user_content:
            return "### Шпаргалка (Ollama mock)\n- Повторіть ключові визначення з теми."
        return f"Відповідь Ollama ({model}) з урахуванням контексту:\n{user_content[:500]}"

    def _fake_ollama_quiz(model: str, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(
            {
                "questions": [
                    {
                        "question": "Яка роль FastAPI Depends у прикладі?",
                        "options": [
                            "Впровадження залежностей",
                            "Стиснення зображень",
                            "Рендеринг CSS",
                            "Міграція Docker-томів",
                        ],
                        "correct_index": 0,
                        "explanation": "Depends реалізує dependency injection.",
                    },
                    {
                        "question": "Яке розширення зберігає вектори в PostgreSQL?",
                        "options": ["pg_trgm", "pgvector", "postgis", "pgcrypto"],
                        "correct_index": 1,
                        "explanation": "pgvector додає тип vector та індекс HNSW.",
                    },
                ]
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(ai_agent_module.ai_agent, "_call_ollama_chat_sync", _fake_ollama_chat)
    monkeypatch.setattr(ai_quiz_module, "_call_ollama_json_sync", _fake_ollama_quiz)


@pytest.fixture()
def isolated_students(client: TestClient):
    """Creates two temporary students and cleans up all their Postgres + MongoDB data after the test."""
    with Session(postgres_helper.engine) as session:
        s1 = Student(
            group="TEST-CI",
            first_name="PytestAlpha",
            last_name="Tester",
            gender="Male",
            birthday=datetime.date(2000, 5, 10),
            status=False,
            password="10.05.2000",
        )
        s2 = Student(
            group="TEST-CI",
            first_name="PytestBeta",
            last_name="Tester",
            gender="Female",
            birthday=datetime.date(2001, 8, 20),
            status=False,
            password="20.08.2001",
        )
        session.add(s1)
        session.add(s2)
        session.commit()
        session.refresh(s1)
        session.refresh(s2)
        sids = [s1.id, s2.id]

    try:
        yield s1, s2
    finally:
        # Clean up MongoDB chats, messages, and study_notes for test students
        sync_mongo = MongoClient(settings.mongo_db.url)
        db = sync_mongo[settings.mongo_db.database_name]
        for sid in sids:
            chat_docs = list(db["chats"].find({"users": sid}))
            for cdoc in chat_docs:
                for mref in cdoc.get("messages", []):
                    mid = mref.id if hasattr(mref, "id") else (mref.get("$id") if isinstance(mref, dict) else None)
                    if mid:
                        db["messages"].delete_one({"_id": mid})
            db["chats"].delete_many({"users": sid})
            db["study_notes"].delete_many({"student_id": sid})
        sync_mongo.close()

        # Clean up PostgreSQL test students (rag_chunks cascade automatically via FK)
        with postgres_helper.engine.begin() as conn:
            conn.execute(text("DELETE FROM student WHERE id = ANY(:ids)"), {"ids": sids})
