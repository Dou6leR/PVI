from api.v1.ai.quiz import _extract_json_payload, _normalize_questions
from tests.conftest import build_minimal_pdf


def test_extract_json_payload_handles_fences():
    fenced = 'Ось результат:\n```json\n{"questions": [{"question": "Q1?"}]}\n```'
    parsed = _extract_json_payload(fenced)
    assert parsed is not None
    assert parsed["questions"][0]["question"] == "Q1?"


def test_normalize_questions_deduplicates_and_preserves_correct_answer():
    raw = [
        {
            "question": "Вже існуюче питання?",
            "options": ["A", "B", "C", "D"],
            "correct_index": 0,
            "explanation": "Exp 0",
        },
        {
            "question": "Нове унікальне питання?",
            "options": ["Хибний 1", "Правильний варіант", "Хибний 2", "Хибний 3"],
            "correct_index": 1,
            "explanation": "Правильна логіка",
        },
        {
            "question": "Ще одне питання?",
            "options": ["Opt 1", "Opt 2", "Opt 3", "Opt 4"],
            "correct_index": 99,  # Out-of-bounds index should clamp safely to 0
            "explanation": "",
        },
    ]
    normalized = _normalize_questions(raw, previous_questions=["Вже існуюче питання?"], limit=5)
    assert len(normalized) == 2
    assert normalized[0]["question"] == "Нове унікальне питання?"
    # Even after random shuffling of options, correct_index must still point to 'Правильний варіант'
    assert normalized[0]["options"][normalized[0]["correct_index"]] == "Правильний варіант"


def test_quiz_generation_and_study_coach_mongodb_isolation(client, isolated_students):
    s1, s2 = isolated_students

    # Generating with neither chat PDF nor topic returns 400
    empty_req = client.post(
        "/api/v1/ai/tests/generate-quiz",
        json={"student_id": s1.id, "chat_id": None, "subject": "", "topic": "", "num_questions": 3},
    )
    assert empty_req.status_code == 400

    # Upload a PDF and generate quiz in fallback mode
    pdf_bytes = build_minimal_pdf("FastAPI dependency injection works cleanly via Depends.")
    client.post(
        "/api/v1/ai/rag/upload-pdf",
        data={"subject": "", "chat_id": "quiz-chat", "student_id": str(s1.id)},
        files={"file": ("fastapi.pdf", pdf_bytes, "application/pdf")},
    )
    quiz_resp = client.post(
        "/api/v1/ai/tests/generate-quiz",
        json={"student_id": s1.id, "chat_id": "quiz-chat", "subject": "", "topic": "FastAPI", "num_questions": 2},
    )
    assert quiz_resp.status_code == 200
    assert len(quiz_resp.json()["questions"]) >= 1

    # Study Coach: score < 70% -> remedial branch; score >= 70% -> advanced branch
    remedial = client.post(
        "/api/v1/ai/tests/study-coach",
        json={
            "student_id": s1.id,
            "chat_id": "quiz-chat",
            "subject": "",
            "topic": "FastAPI",
            "score": 1,
            "total": 3,
            "mistakes": [{"question": "Q?", "user_answer": "Wrong", "correct_answer": "Right", "explanation": ""}],
        },
    )
    assert remedial.status_code == 200
    rem_note = remedial.json()
    assert rem_note["coach_mode"] == "remedial"
    assert rem_note["percent"] == 33

    advanced = client.post(
        "/api/v1/ai/tests/study-coach",
        json={
            "student_id": s1.id,
            "chat_id": "quiz-chat",
            "subject": "",
            "topic": "FastAPI",
            "score": 3,
            "total": 3,
            "mistakes": [],
        },
    )
    assert advanced.status_code == 200
    assert advanced.json()["coach_mode"] == "advanced"

    # Per-student StudyNote isolation
    s1_notes = client.get(f"/api/v1/ai/tests/study-notes?student_id={s1.id}").json()
    s2_notes = client.get(f"/api/v1/ai/tests/study-notes?student_id={s2.id}").json()
    assert s1_notes["count"] == 2
    assert s2_notes["count"] == 0

    # Student 2 cannot delete Student 1's study note (403)
    forbidden = client.delete(f"/api/v1/ai/tests/study-notes/{rem_note['id']}?student_id={s2.id}")
    assert forbidden.status_code == 403

    # Student 1 deletes their study note successfully
    deleted = client.delete(f"/api/v1/ai/tests/study-notes/{rem_note['id']}?student_id={s1.id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
