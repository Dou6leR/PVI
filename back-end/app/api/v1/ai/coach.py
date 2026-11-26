import asyncio
import json
import urllib.error
import urllib.request
from typing import Optional, List
from beanie import PydanticObjectId
from fastapi import HTTPException

from core import settings
from core.logger import logger
from core.models import StudyNote
from api.v1.ai.agent import ai_agent


def _build_coach_prompts(
    topic: str,
    score: int,
    total: int,
    percent: int,
    mistakes: list[dict],
) -> tuple[str, str, str]:
    """Builds (coach_mode, system_prompt, user_prompt) following the IF < 70% rule."""
    if percent < 70:
        coach_mode = "remedial"
        mistakes_text = (
            "\n\n".join(
                f"{i + 1}. Питання: {m.get('question', '')}\n"
                f"   Обрано студентом: {m.get('user_answer') or 'Не обрано'}\n"
                f"   Правильно: {m.get('correct_answer', '')}"
                for i, m in enumerate(mistakes)
            )
            if mistakes
            else "Помилок не вказано."
        )
        system_prompt = (
            "Ти — доброзичливий AI Study Coach університету. Пиши виключно чистою українською мовою у форматі Markdown. "
            "Склади структуровану, коротку і практичну шпаргалку для підготовки."
        )
        user_prompt = (
            f'Студент пройшов тест з теми "{topic}" з результатом {score}/{total} ({percent}%).\n\n'
            f"Питання, де були помилки:\n{mistakes_text}\n\n"
            f"Завдання:\n"
            f"1. Коротко поясни кожну помилку простими словами.\n"
            f"2. Склади стислу шпаргалку (ключові тези та правила по цих слабких місцях), щоб студент легко повторив тему."
        )
    else:
        coach_mode = "advanced"
        mistakes_note = ""
        if mistakes:
            mistakes_note = "\nНевеликі неточності:\n" + "\n".join(
                f"{i + 1}. {m.get('question', '')} -> Правильно: {m.get('correct_answer', '')}"
                for i, m in enumerate(mistakes)
            )
        system_prompt = "Ти — AI Study Coach університету. Пиши виключно чистою українською мовою у форматі Markdown."
        user_prompt = (
            f'Студент чудово пройшов тест з теми "{topic}" із результатом {score}/{total} ({percent}%).{mistakes_note}\n\n'
            f"Завдання:\n"
            f"1. Коротко похвали за гарний результат і зафіксуй 3-4 ключові тези теми у форматі шпаргалки."
            f"{chr(10) + '2. Поясни ті дрібні помилки, що трапилися.' if mistakes else ''}\n"
            f"3. Запропонуй 1 цікаве поглиблене питання для самостійного роздуму (без варіантів відповіді, з короткою підказкою)."
        )
    return coach_mode, system_prompt, user_prompt


def _call_n8n_study_coach_sync(payload: dict) -> Optional[dict]:
    """Calls the n8n Study Coach webhook inside the Docker network."""
    candidate_urls = [
        "http://n8n:5678/webhook/study-coach",
        "http://127.0.0.1:5678/webhook/study-coach",
    ]
    data = json.dumps(payload).encode("utf-8")
    for url in candidate_urls:
        try:
            req = urllib.request.Request(
                url=url,
                data=data,
                method="POST",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120.0) as resp:
                if resp.status == 200:
                    parsed = json.loads(resp.read().decode("utf-8"))
                    if parsed and parsed.get("study_note_md"):
                        return parsed
        except Exception as e:
            logger.debug(f"n8n study-coach call to {url} unavailable: {e}")
    return None


async def _generate_coach_fallback(
    topic: str,
    score: int,
    total: int,
    percent: int,
    mistakes: list[dict],
) -> tuple[str, str, str]:
    """Mirrors the n8n IF workflow using active Gemini / Ollama / offline summary when n8n webhook is inactive."""
    coach_mode, system_prompt, user_prompt = _build_coach_prompts(topic, score, total, percent, mistakes)
    pref = settings.ai.provider.strip().lower()
    order = ["ollama", "gemini"] if pref == "ollama" else ["gemini", "ollama"]

    for candidate in order:
        if candidate == "gemini" and ai_agent._is_live_gemini_available():
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.ai.api_key.strip())
                resp = await asyncio.to_thread(
                    client.models.generate_content,
                    model=settings.ai.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.4),
                )
                if resp.text and resp.text.strip():
                    return coach_mode, f"CMS Study Coach · Gemini ({settings.ai.model})", resp.text.strip()
            except Exception as e:
                logger.warning(f"Gemini coach fallback failed: {e}")
        elif candidate == "ollama":
            try:
                ollama_info = await ai_agent.get_ollama_status()
                model = ai_agent._resolve_ollama_model(ollama_info["models"])
                if ollama_info["reachable"] and model:
                    text = await asyncio.to_thread(
                        ai_agent._call_ollama_chat_sync,
                        model,
                        [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    )
                    if text:
                        return coach_mode, f"CMS Study Coach · Ollama ({model})", text
            except Exception as e:
                logger.warning(f"Ollama coach fallback failed: {e}")

    # Pure offline deterministic summary if both LLMs are offline
    lines = [f"### Шпаргалка: {topic}", f"**Результат:** {score}/{total} ({percent}%)", ""]
    if mistakes:
        lines.append("**Що варто повторити:**")
        for m in mistakes:
            lines.append(f"- **{m.get('question', '')}** → Правильна відповідь: `{m.get('correct_answer', '')}`")
    else:
        lines.append("Усі відповіді правильні — тема засвоєна на відмінно!")
    return coach_mode, "CMS Study Coach (Offline)", "\n".join(lines)


def _serialize_note(note: StudyNote) -> dict:
    return {
        "id": str(note.id),
        "student_id": note.student_id,
        "chat_id": note.chat_id,
        "topic": note.topic,
        "subject": note.subject,
        "score": note.score,
        "total": note.total,
        "percent": note.percent,
        "mistakes_count": note.mistakes_count,
        "coach_mode": note.coach_mode,
        "source": note.source,
        "content_md": note.content_md,
        "created_at": note.created_at.isoformat(),
    }


async def generate_and_save_study_note(
    student_id: int,
    chat_id: Optional[str],
    subject: str,
    topic: str,
    score: int,
    total: int,
    mistakes: list[dict],
) -> dict:
    clean_topic = (topic or subject or "Тест").strip()
    clean_subject = (subject or "").strip()
    percent = round((score / total) * 100) if total > 0 else 0

    n8n_payload = {
        "topic": clean_topic,
        "subject": clean_subject,
        "score": score,
        "total": total,
        "percent": percent,
        "mistakes": mistakes,
        "ollama_model": settings.ai.ollama_model,
    }

    # Prefer n8n orchestration unless Gemini is explicitly forced with API key
    n8n_res = None
    if not (settings.ai.provider.strip().lower() == "gemini" and ai_agent._is_live_gemini_available()):
        n8n_res = await asyncio.to_thread(_call_n8n_study_coach_sync, n8n_payload)

    if n8n_res and n8n_res.get("study_note_md"):
        coach_mode = n8n_res.get("coach_mode") or ("remedial" if percent < 70 else "advanced")
        source = n8n_res.get("source") or "n8n AI Study Coach"
        content_md = n8n_res["study_note_md"].strip()
    else:
        coach_mode, source, content_md = await _generate_coach_fallback(
            clean_topic, score, total, percent, mistakes
        )

    note = StudyNote(
        student_id=int(student_id),
        chat_id=chat_id,
        topic=clean_topic,
        subject=clean_subject,
        score=int(score),
        total=int(total),
        percent=int(percent),
        mistakes_count=len(mistakes),
        coach_mode=coach_mode,
        source=source,
        content_md=content_md,
    )
    await note.insert()
    logger.info(f"Saved StudyNote {note.id} for student_id={student_id} via {source}")
    return _serialize_note(note)


async def get_student_study_notes(student_id: int) -> List[dict]:
    notes = await StudyNote.find(StudyNote.student_id == int(student_id)).sort("-created_at").to_list()
    return [_serialize_note(n) for n in notes]


async def delete_student_study_note(note_id: str, student_id: int) -> dict:
    try:
        oid = PydanticObjectId(note_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = await StudyNote.get(oid)
    if not note:
        raise HTTPException(status_code=404, detail="Study note not found")
    if note.student_id != int(student_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    await note.delete()
    return {"status": "deleted", "id": note_id}
