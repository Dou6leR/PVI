import asyncio
import json
import random
import re
import urllib.error
import urllib.request
from typing import Optional, List, Dict, Any

from core import settings
from core.logger import logger
from api.v1.ai.rag import rag_store
from api.v1.ai.agent import ai_agent


def _extract_json_payload(raw_text: str) -> Optional[dict]:
    """Extracts a JSON object from LLM text, stripping markdown code fences if present."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            cleaned = brace_match.group(0)
    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"Failed to parse LLM quiz JSON: {e}")
        return None


def _normalize_text_key(text: str) -> str:
    return re.sub(r"\W+", "", (text or "").lower())


def _normalize_questions(
    raw_questions: list,
    previous_questions: Optional[List[str]] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Validates, deduplicates against prior questions, shuffles options, and formats schema."""
    prev_keys = {_normalize_text_key(q) for q in (previous_questions or []) if q}
    seen_keys = set(prev_keys)
    normalized = []

    for q in raw_questions or []:
        if not isinstance(q, dict):
            continue
        question_text = str(q.get("question", "")).strip()
        options = q.get("options") or []
        if not question_text or not isinstance(options, list) or len(options) < 2:
            continue

        q_key = _normalize_text_key(question_text)
        if q_key in seen_keys:
            continue

        options = [str(opt).strip() for opt in options[:4]]
        try:
            correct_idx = int(q.get("correct_index", 0))
        except (TypeError, ValueError):
            correct_idx = 0
        if correct_idx < 0 or correct_idx >= len(options):
            correct_idx = 0

        # Shuffle answer positions while preserving correct_index accuracy
        indexed_opts = list(enumerate(options))
        random.shuffle(indexed_opts)
        shuffled_options = [opt for _, opt in indexed_opts]
        new_correct_idx = next(i for i, (orig_i, _) in enumerate(indexed_opts) if orig_i == correct_idx)

        explanation = str(q.get("explanation", "")).strip() or "Правильна відповідь відповідає наданому матеріалу."
        seen_keys.add(q_key)
        normalized.append({
            "id": len(normalized) + 1,
            "question": question_text,
            "options": shuffled_options,
            "correct_index": new_correct_idx,
            "explanation": explanation,
        })
        if len(normalized) >= limit:
            break

    return normalized


def _call_ollama_json_sync(model: str, system_prompt: str, user_prompt: str) -> str:
    base_url = settings.ai.ollama_url.rstrip("/")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "keep_alive": "5m",
        "options": {
            "temperature": 0.55,
            "top_p": 0.9,
            "seed": random.randint(1, 10**9),
            "num_ctx": 8192,
            "num_predict": 3500,
        },
    }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("message", {}).get("content", "").strip()


async def _generate_via_gemini(system_prompt: str, user_prompt: str) -> tuple[Optional[dict], str]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.ai.api_key.strip())
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.ai.model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.55,
            response_mime_type="application/json",
        ),
    )
    parsed = _extract_json_payload(response.text)
    return parsed, f"Google Gemini ({settings.ai.model})"


async def _generate_via_ollama(system_prompt: str, user_prompt: str) -> tuple[Optional[dict], str]:
    ollama_info = await ai_agent.get_ollama_status()
    model = ai_agent._resolve_ollama_model(ollama_info["models"])
    if not ollama_info["reachable"] or not model:
        return None, ""
    raw = await asyncio.to_thread(_call_ollama_json_sync, model, system_prompt, user_prompt)
    parsed = _extract_json_payload(raw)
    return parsed, f"Ollama ({model})"


def _build_rag_fallback_quiz(topic: str, subject: str, rag_chunks: List[Dict[str, Any]], num_questions: int) -> dict:
    """Offline fallback when no LLM provider is available."""
    questions = []
    for idx, chunk in enumerate(rag_chunks[:num_questions], start=1):
        snippet = chunk.get("text", "")[:160].strip()
        if not snippet:
            continue
        questions.append({
            "id": idx,
            "question": f"Яке з наведених положень відповідає матеріалу з файлу '{chunk.get('filename')}' (стор. {chunk.get('page')})?",
            "options": [
                f"{snippet}...",
                "Це твердження не стосується даної теми та повністю виключене з матеріалу",
                "Дана концепція заборонена до використання в сучасних системах",
                "Жоден із наведених пунктів не описаний у документі"
            ],
            "correct_index": 0,
            "explanation": f"Фрагмент взято безпосередньо зі сторінки {chunk.get('page')} файлу '{chunk.get('filename')}'."
        })

    return {
        "status": "success" if questions else "empty",
        "source": "CMS Offline Fallback",
        "subject": subject,
        "topic": topic or subject or "Тест за матеріалами чату",
        "rag_context_used": len(rag_chunks) > 0,
        "questions": questions,
    }


async def generate_quiz(
    subject: str = "",
    topic: str = "",
    chat_id: Optional[str] = None,
    student_id: Optional[int] = None,
    num_questions: int = 3,
    previous_questions: Optional[List[str]] = None,
) -> dict:
    """
    Generates unique interactive test questions (1..10) scoped strictly to the user's
    selected chat/PDFs or custom topic, avoiding repetition of previous_questions.
    """
    num_questions = max(1, min(int(num_questions or 3), 10))
    clean_subject = (subject or "").strip()
    clean_topic = (topic or "").strip()
    prev_list = [q.strip() for q in (previous_questions or []) if q and q.strip()]

    # 1. Sample diverse RAG chunks across different pages for each generation
    rag_chunks: List[Dict[str, Any]] = []
    if student_id is not None:
        sample_limit = 6 if num_questions <= 5 else 8
        varied = rag_store.get_varied_chunks(
            subject=clean_subject, student_id=student_id, chat_id=chat_id, limit=sample_limit
        )
        semantic = (
            rag_store.search(
                query=clean_topic, subject=clean_subject, student_id=student_id, chat_id=chat_id, top_k=4
            )
            if clean_topic
            else []
        )
        seen = set()
        # Interleave varied page samples and semantic hits so every run explores fresh sections
        for c in varied + semantic:
            key = (c["filename"], c["page"], c["text"][:60])
            if key not in seen:
                seen.add(key)
                rag_chunks.append(c)
        rag_chunks = rag_chunks[:sample_limit]

    if not clean_topic and not rag_chunks:
        return {
            "status": "error",
            "source": "CMS Tests",
            "subject": clean_subject,
            "topic": clean_topic,
            "rag_context_used": False,
            "questions": [],
            "detail": "У вибраному чаті немає завантажених PDF-файлів і не вказано тему тесту."
        }

    effective_topic = clean_topic or (
        f"Матеріали файлу {rag_chunks[0]['filename']}" if rag_chunks else clean_subject
    )

    rag_block = ""
    if rag_chunks:
        rag_block = "\n\n".join(
            [f"[{c['filename']}, стор. {c['page']}]:\n{c['text']}" for c in rag_chunks]
        )

    system_prompt = (
        "Ти — генератор унікальних навчальних тестів для студентів університету.\n"
        "Створюй чіткі, грамотні тестові запитання виключно чистою літературною УКРАЇНСЬКОЮ мовою (без суржику та росіянізмів).\n"
        "Розміщуй правильну відповідь під різними індексами (0, 1, 2 або 3), а не завжди першою.\n"
        "КРИТИЧНЕ ПРАВИЛО ДОВЖИНИ ВАРІАНТІВ: Усі 4 варіанти відповіді (options) мають бути приблизно ОДНАКОВОЇ довжини (по 4–10 слів) і стилю.\n"
        "СУВОРО ЗАБОРОНЕНО робити правильну відповідь найдовшою або детальнішою за хибні — хибні варіанти мають бути такими ж змістовними й розгорнутими, а правильна відповідь має бути стислою.\n"
        "Масив questions ОБОВ'ЯЗКОВО має містити точну запитану кількість елементів.\n"
        "Приклад ідеального формату та балансу довжини варіантів (повертай ВИКЛЮЧНО JSON без зайвого тексту):\n"
        "{\n"
        '  "questions": [\n'
        "    {\n"
        '      "question": "Яке основне призначення індексу B-Tree у PostgreSQL?",\n'
        '      "options": [\n'
        '        "Автоматичне шифрування таблиць на диску сервера",\n'
        '        "Прискорення пошуку та діапазонних вибірок",\n'
        '        "Резервне копіювання даних між кількома вузлами",\n'
        '        "Стиснення бінарних файлів у журналі транзакцій"\n'
        "      ],\n"
        '      "correct_index": 1,\n'
        '      "explanation": "B-Tree оптимізує пошук рівності та діапазонів у таблиці."\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    topic_line = f"Тема / фокус тесту: {effective_topic}\n" if effective_topic else ""
    subject_line = f"Напрям / чат: {clean_subject}\n" if clean_subject else ""

    def _build_user_prompt(target_cnt: int, avoid_qs: List[str]) -> str:
        avoid_part = ""
        if avoid_qs:
            avoid_lines = "\n".join(f"- {q}" for q in avoid_qs[-18:])
            avoid_part = (
                "\n\nСУВОРА ВИМОГА: НЕ повторюй і НЕ перефразовуй ці вже згенеровані запитання — "
                "придумай зовсім інші запитання по інших фактах і деталях:\n"
                f"{avoid_lines}"
            )
        if rag_block:
            return (
                f"{subject_line}{topic_line}"
                f"Згенеруй РІВНО {target_cnt} РІЗНИХ тестових запитань (не менше {target_cnt}) з 4 варіантами відповіді "
                f"на основі наступних фрагментів із PDF-матеріалів (спроба #{random.randint(100, 999)}):"
                f"{avoid_part}\n\nМатеріал:\n{rag_block}"
            )
        return (
            f"{subject_line}{topic_line}"
            f"Згенеруй РІВНО {target_cnt} РІЗНИХ змістовних навчальних тестових запитань (не менше {target_cnt}) "
            f"з 4 варіантами відповіді та поясненнями українською мовою (спроба #{random.randint(100, 999)})."
            f"{avoid_part}"
        )

    pref = settings.ai.provider.strip().lower()
    order = ["ollama", "gemini"] if pref == "ollama" else ["gemini", "ollama"]

    async def _run_provider(candidate_name: str, prompt_text: str) -> tuple[Optional[dict], str]:
        if candidate_name == "gemini" and ai_agent._is_live_gemini_available():
            return await _generate_via_gemini(system_prompt, prompt_text)
        if candidate_name == "ollama":
            return await _generate_via_ollama(system_prompt, prompt_text)
        return None, ""

    for candidate in order:
        if candidate == "gemini" and not ai_agent._is_live_gemini_available():
            continue
        try:
            prompt_text = _build_user_prompt(num_questions, prev_list)
            parsed, src = await _run_provider(candidate, prompt_text)
            questions = _normalize_questions((parsed or {}).get("questions", []), prev_list, num_questions)

            # Top up if the LLM generated slightly fewer than requested
            if 0 < len(questions) < num_questions:
                missing = num_questions - len(questions)
                avoid_all = prev_list + [q["question"] for q in questions]
                extra_parsed, _ = await _run_provider(candidate, _build_user_prompt(missing, avoid_all))
                extra_qs = _normalize_questions((extra_parsed or {}).get("questions", []), avoid_all, missing)
                for eq in extra_qs:
                    eq["id"] = len(questions) + 1
                    questions.append(eq)

            if not questions and parsed:
                questions = _normalize_questions((parsed or {}).get("questions", []), None, num_questions)
            if questions:
                return {
                    "status": "success",
                    "source": src,
                    "subject": clean_subject,
                    "topic": effective_topic,
                    "rag_context_used": len(rag_chunks) > 0,
                    "questions": questions,
                }
        except Exception as e:
            logger.warning(f"{candidate} quiz generation failed: {e}")

    return _build_rag_fallback_quiz(effective_topic, clean_subject, rag_chunks, num_questions)
