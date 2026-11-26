import datetime
from sqlmodel import Session, select

from core import postgres_helper
from core.models import Student
from core.models.rag import KnowledgeChunk
from tests.conftest import make_basic_auth, build_minimal_pdf


def test_per_user_chats_and_pgvector_rag_isolation(client, isolated_students):
    s1, s2 = isolated_students

    # Both new students start with 0 chats
    assert client.get(f"/api/v1/message/user_chats/{s1.id}").json()["data"] == []
    assert client.get(f"/api/v1/message/user_chats/{s2.id}").json()["data"] == []

    # Student 1 creates a personal chat with empty subject (optional discipline)
    chat_resp = client.post(
        "/api/v1/message/chat",
        json={"users": [s1.id], "chat_name": "Мій конспект", "subject": "", "is_ai": True},
    )
    assert chat_resp.status_code == 201
    chat = chat_resp.json()
    chat_id = chat["id"]
    assert chat["subject"] == ""

    # Student 2 still sees 0 chats
    assert client.get(f"/api/v1/message/user_chats/{s2.id}").json()["data"] == []

    # PDF upload validation: missing student_id or non-PDF fails with 400
    pdf_bytes = build_minimal_pdf("Pgvector Isolation Token 889900")
    no_sid = client.post(
        "/api/v1/ai/rag/upload-pdf",
        data={"subject": "", "chat_id": chat_id},
        files={"file": ("notes.pdf", pdf_bytes, "application/pdf")},
    )
    assert no_sid.status_code == 400

    bad_ext = client.post(
        "/api/v1/ai/rag/upload-pdf",
        data={"subject": "", "chat_id": chat_id, "student_id": str(s1.id)},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert bad_ext.status_code == 400

    # Student 1 uploads PDF into their chat -> indexed in PostgreSQL pgvector
    up = client.post(
        "/api/v1/ai/rag/upload-pdf",
        data={"subject": "", "chat_id": chat_id, "student_id": str(s1.id)},
        files={"file": ("lecture1.pdf", pdf_bytes, "application/pdf")},
    )
    assert up.status_code == 200
    assert up.json()["chunks_indexed"] >= 1

    # Query succeeds for Student 1 in the same chat
    q_own = client.post(
        "/api/v1/ai/rag/query",
        json={"query": "Pgvector Isolation Token 889900", "student_id": s1.id, "chat_id": chat_id},
    )
    assert q_own.status_code == 200
    assert q_own.json()["results_count"] == 1
    assert "889900" in q_own.json()["results"][0]["text"]

    # Query returns 0 for Student 1 in a DIFFERENT chat_id (chat isolation)
    q_other_chat = client.post(
        "/api/v1/ai/rag/query",
        json={"query": "Pgvector Isolation Token 889900", "student_id": s1.id, "chat_id": "different-chat"},
    )
    assert q_other_chat.json()["results_count"] == 0

    # Query returns 0 for Student 2 even with the same chat_id (user isolation)
    q_other_user = client.post(
        "/api/v1/ai/rag/query",
        json={"query": "Pgvector Isolation Token 889900", "student_id": s2.id, "chat_id": chat_id},
    )
    assert q_other_user.json()["results_count"] == 0

    # AI chat uses Student 1's PDF and persists both messages into MongoDB
    chat_reply = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "What is Pgvector Isolation Token 889900?",
            "subject": "",
            "chat_id": chat_id,
            "student_id": s1.id,
        },
    )
    assert chat_reply.status_code == 200
    assert "889900" in chat_reply.json()["response"]

    fetched_chat = client.get(f"/api/v1/message/chat/{chat_id}").json()
    assert len(fetched_chat["messages"]) == 2


def test_rag_chunks_cascade_delete_when_student_deleted(client, isolated_students):
    s1, _ = isolated_students
    with Session(postgres_helper.engine) as session:
        temp_student = Student(
            group="TEST-CI",
            first_name="Cascade",
            last_name="Temp",
            gender="Other",
            birthday=datetime.date(2002, 1, 15),
            status=False,
            password="15.01.2002",
        )
        session.add(temp_student)
        session.commit()
        session.refresh(temp_student)
        temp_id = temp_student.id

    pdf_bytes = build_minimal_pdf("Cascade Delete Check 551122")
    up = client.post(
        "/api/v1/ai/rag/upload-pdf",
        data={"subject": "", "chat_id": "cascade-chat", "student_id": str(temp_id)},
        files={"file": ("cascade.pdf", pdf_bytes, "application/pdf")},
    )
    assert up.status_code == 200

    # Delete temp_student via API (authenticated as s1)
    del_resp = client.delete(
        f"/api/v1/student/{temp_id}",
        headers=make_basic_auth(s1.first_name, s1.last_name, s1.password),
    )
    assert del_resp.status_code == 200

    # Verify PostgreSQL FK ON DELETE CASCADE removed temp_student's RAG chunks
    with Session(postgres_helper.engine) as session:
        remaining = session.exec(select(KnowledgeChunk).where(KnowledgeChunk.student_id == temp_id)).all()
        assert len(remaining) == 0
