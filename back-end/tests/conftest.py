import base64
import datetime
from typing import Iterator
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from sqlalchemy import text
from sqlmodel import Session

from main import app
from core import postgres_helper, settings
from core.models import Student


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


@pytest.fixture(autouse=True)
def force_deterministic_offline_ai(monkeypatch):
    """Prevents tests from hitting live external APIs or spending GPU time on Ollama."""
    monkeypatch.setattr(settings.ai, "api_key", "")
    monkeypatch.setattr(settings.ai, "ollama_url", "http://127.0.0.1:11499")


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
