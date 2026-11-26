import asyncio
import json
import re
import urllib.error
import urllib.request
from typing import Optional
from sqlmodel import Session

from core import settings
from core.logger import logger
from api.v1.ai.rag import rag_store
from api.v1.ai.tools import (
    tool_search_students,
    tool_get_group_students,
    tool_get_system_stats,
    tool_query_subject_knowledge,
)


OVERVIEW_KEYWORDS = [
    "розкажи", "про що", "опиши", "коротко", "підсумок", "резюме",
    "суть", "зміст", "лаборатор", "файл", "документ", "конспект", "презентац"
]


class CMSAIAgent:
    def _is_live_gemini_available(self) -> bool:
        api_key = settings.ai.api_key.strip()
        return bool(api_key and api_key != "your_gemini_api_key_here")

    @staticmethod
    def _check_ollama_sync() -> dict:
        """Probes Ollama /api/tags to verify availability and installed models."""
        base_url = settings.ai.ollama_url.rstrip("/")
        try:
            req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    return {"reachable": True, "models": models}
        except Exception as e:
            logger.debug(f"Ollama probe failed at {base_url}: {e}")
        return {"reachable": False, "models": []}

    async def get_ollama_status(self) -> dict:
        return await asyncio.to_thread(self._check_ollama_sync)

    @staticmethod
    def _resolve_ollama_model(installed_models: list[str]) -> Optional[str]:
        if not installed_models:
            return None
        target = settings.ai.ollama_model.strip()
        if target in installed_models:
            return target
        # Match tagless name or :latest variant (e.g. 'llama3.2' vs 'llama3.2:latest')
        target_base = target.split(":")[0]
        for model in installed_models:
            if model.split(":")[0] == target_base:
                return model
        return installed_models[0]

    def _gather_context(
        self,
        user_message: str,
        subject: str,
        session: Optional[Session],
        student_id: Optional[int] = None,
        chat_id: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> dict:
        """Collects RAG chunks and PostgreSQL tool results shared across all LLM providers."""
        tools_called = []
        msg_lower = user_message.lower()

        # 1. RAG context (scoped strictly to student_id and chat_id)
        rag_chunks = tool_query_subject_knowledge(
            user_message, subject=subject, student_id=student_id, chat_id=chat_id, top_k=4
        )
        is_overview = any(kw in msg_lower for kw in OVERVIEW_KEYWORDS)
        if is_overview:
            overview_chunks = rag_store.get_overview_chunks(
                subject=subject, student_id=student_id, chat_id=chat_id, limit=3
            )
            seen = set()
            merged = []
            for c in overview_chunks + rag_chunks:
                key = (c["filename"], c["page"], c["text"][:60])
                if key not in seen:
                    seen.add(key)
                    merged.append(c)
            rag_chunks = merged[:5]

        context_str = ""
        if rag_chunks:
            context_str = "\n\n".join(
                [f"[{c['filename']}, стор. {c['page']}]:\n{c['text']}" for c in rag_chunks]
            )
            tools_called.append({
                "tool": "tool_query_subject_knowledge",
                "args": {"query": user_message, "subject": subject},
                "result_count": len(rag_chunks),
                "top_source": f"{rag_chunks[0]['filename']} (стор. {rag_chunks[0]['page']})"
            })

        # 2. PostgreSQL tools
        student_context = ""
        if session is not None:
            if any(w in msg_lower for w in ["студент", "група", "хто", "список", "кількість", "онлайн", "статистик"]):
                stats = tool_get_system_stats(session)
                student_context += (
                    f"\nСтатистика системи: всього студентів {stats.get('total_students')}, "
                    f"онлайн: {stats.get('online_students')}, групи: {stats.get('groups_distribution', {})}."
                )
                tools_called.append({"tool": "tool_get_system_stats", "args": {}, "result": stats})

                group_match = re.search(r"(pz-\d+|ki-\d+|sa-\d+)", msg_lower)
                if group_match:
                    grp = group_match.group(1).upper()
                    grp_students = tool_get_group_students(grp, session)
                    student_context += f"\nСтуденти групи {grp}: " + ", ".join(
                        [f"{s['name']} ({s['status']})" for s in grp_students]
                    )
                    tools_called.append({
                        "tool": "tool_get_group_students",
                        "args": {"group": grp},
                        "result_count": len(grp_students)
                    })

            name_match = re.search(r"(знайди|хто такий|інформація про|пошук)\s+([a-zA-Zа-яА-ЯіїєґІЇЄҐ']+)", msg_lower)
            if name_match:
                query_name = name_match.group(2)
                found = tool_search_students(query_name, session)
                tools_called.append({
                    "tool": "tool_search_students",
                    "args": {"name_or_query": query_name},
                    "result_count": len(found)
                })
                if found and "error" not in found[0]:
                    student_context += "\nЗнайдені студенти: " + "; ".join(
                        [f"{s['first_name']} {s['last_name']} (група {s['group']}, {s['status']}, Д/Н {s['birthday']})" for s in found]
                    )

        course_clause = f" для напряму '{subject}'" if subject else ""
        system_instruction = (
            f"Ти — CMS AI Assistant, розумний помічник університетської платформи CMS{course_clause}.\n"
            f"Завжди відповідай українською мовою, структуровано, зрозуміло та по суті.\n"
            f"Спирайся лише на надані фрагменти з PDF-файлів користувача (RAG) та дані з бази даних PostgreSQL. "
            f"Не вигадуй фактів, яких немає в контексті; якщо контексту недостатньо — чесно скажи про це."
        )

        context_sections = []
        if context_str:
            context_sections.append(f"Фрагменти із завантажених PDF-документів користувача:\n{context_str}")
        if student_context:
            context_sections.append(f"Дані з бази даних CMS (PostgreSQL):{student_context}")

        augmented_prompt = (
            "\n\n".join(context_sections) + f"\n\nЗапитання користувача: {user_message}"
            if context_sections
            else user_message
        )

        history_messages = []
        for msg in (chat_history or [])[-6:]:
            role = "assistant" if msg.get("user") in (9999, "ai") else "user"
            text = (msg.get("message") or "").strip()
            if text:
                history_messages.append({"role": role, "content": text})

        return {
            "tools_called": tools_called,
            "rag_chunks": rag_chunks,
            "system_instruction": system_instruction,
            "augmented_prompt": augmented_prompt,
            "history_messages": history_messages,
        }

    async def execute_agent(
        self,
        user_message: str,
        subject: Optional[str] = "",
        session: Optional[Session] = None,
        student_id: Optional[int] = None,
        chat_id: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> dict:
        """
        Executes the AI Agent using the configured provider order:
        - provider == 'gemini': Gemini -> Ollama -> Offline Fallback
        - provider == 'ollama': Ollama -> Gemini -> Offline Fallback
        - provider == 'auto' (default): Gemini (if API key set) -> Ollama (if running) -> Offline Fallback
        """
        subj = (subject or "").strip()
        ctx = self._gather_context(user_message, subj, session, student_id, chat_id, chat_history)

        pref = settings.ai.provider.strip().lower()
        order = ["ollama", "gemini"] if pref == "ollama" else ["gemini", "ollama"]

        for candidate in order:
            if candidate == "gemini" and self._is_live_gemini_available():
                try:
                    return await self._run_gemini_agent(subj, ctx)
                except Exception as e:
                    logger.warning(f"Gemini execution failed ({e}); trying next provider.")
            elif candidate == "ollama":
                ollama_info = await self.get_ollama_status()
                resolved_model = self._resolve_ollama_model(ollama_info["models"])
                if ollama_info["reachable"] and resolved_model:
                    try:
                        return await self._run_ollama_agent(subj, ctx, resolved_model)
                    except Exception as e:
                        logger.warning(f"Ollama execution failed ({e}); trying next provider.")

        return self._run_smart_agent(user_message, subj, session, ctx)

    async def _run_gemini_agent(self, subject: str, ctx: dict) -> dict:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.ai.api_key.strip())
        history_block = ""
        if ctx["history_messages"]:
            lines = [
                f"{'Користувач' if m['role'] == 'user' else 'Асистент'}: {m['content']}"
                for m in ctx["history_messages"]
            ]
            history_block = "Попередній діалог:\n" + "\n".join(lines) + "\n\n"

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.ai.model,
            contents=history_block + ctx["augmented_prompt"],
            config=types.GenerateContentConfig(
                system_instruction=ctx["system_instruction"],
                temperature=0.3,
            ),
        )

        return {
            "response": response.text,
            "tools_called": ctx["tools_called"],
            "provider": f"Google Gemini ({settings.ai.model})",
            "subject": subject,
        }

    @staticmethod
    def _call_ollama_chat_sync(model: str, messages: list[dict]) -> str:
        base_url = settings.ai.ollama_url.rstrip("/")

        def _post(body_dict: dict) -> str:
            payload = json.dumps(body_dict).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/chat",
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "").strip()

        base_body = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": "10m",
            "options": {"temperature": 0.3},
        }
        try:
            # Disable hidden chain-of-thought on reasoning models (e.g. qwen3.5) for fast chat responses
            return _post({**base_body, "think": False})
        except urllib.error.HTTPError as e:
            if e.code == 400:
                return _post(base_body)
            raise

    async def _run_ollama_agent(self, subject: str, ctx: dict, model: str) -> dict:
        messages = [{"role": "system", "content": ctx["system_instruction"]}]
        messages.extend(ctx["history_messages"])
        messages.append({"role": "user", "content": ctx["augmented_prompt"]})

        reply_text = await asyncio.to_thread(self._call_ollama_chat_sync, model, messages)
        if not reply_text:
            raise ValueError("Empty response from Ollama")

        return {
            "response": reply_text,
            "tools_called": ctx["tools_called"],
            "provider": f"Ollama ({model})",
            "subject": subject,
        }

    def _run_smart_agent(self, user_message: str, subject: str, session: Optional[Session], ctx: dict) -> dict:
        """Offline fallback when neither Gemini API key nor an Ollama model is active."""
        tools_called = ctx["tools_called"]
        msg_lower = user_message.lower()

        # 1. Database Intent: Statistics
        if session is not None and any(w in msg_lower for w in ["статистик", "скільки всього", "скільки студент"]):
            stats = tool_get_system_stats(session)
            resp = "📊 **Статистика системи CMS:**\n\n"
            resp += f"- **Всього зареєстровано студентів:** {stats.get('total_students', 0)}\n"
            resp += f"- **Зараз онлайн:** {stats.get('online_students', 0)}\n"
            resp += f"- **Кількість навчальних груп:** {stats.get('groups_count', 0)}\n"
            resp += "- **Розподіл по групах:**\n"
            for grp, cnt in stats.get("groups_distribution", {}).items():
                resp += f"  - `{grp}`: {cnt} студентів\n"
            return {
                "response": resp,
                "tools_called": tools_called,
                "provider": "CMS Smart Agent Engine (Offline Fallback)",
                "subject": subject,
            }

        # 2. Database Intent: Group Search
        group_match = re.search(r"(pz-\d+|ki-\d+|sa-\d+)", msg_lower)
        if session is not None and group_match:
            grp = group_match.group(1).upper()
            students = tool_get_group_students(grp, session)
            if students:
                resp = f"👥 **Студенти групи {grp} ({len(students)} осіб):**\n\n"
                for idx, s in enumerate(students, 1):
                    status_emoji = "🟢" if s["status"] == "Online" else "⚪"
                    resp += f"{idx}. {s['name']} — {status_emoji} {s['status']}\n"
                return {
                    "response": resp,
                    "tools_called": tools_called,
                    "provider": "CMS Smart Agent Engine (Offline Fallback)",
                    "subject": subject,
                }

        # 3. Database Intent: Student Search by Name
        name_match = re.search(r"(знайди|хто такий|інформація про|пошук)\s+([a-zA-Zа-яА-ЯіїєґІЇЄҐ']+)", msg_lower)
        if session is not None and name_match:
            query_name = name_match.group(2)
            found = tool_search_students(query_name, session)
            if found and "error" not in found[0]:
                resp = f"🔍 **Результати пошуку студента '{query_name}':**\n\n"
                for s in found:
                    resp += f"- **{s['first_name']} {s['last_name']}** (Група: `{s['group']}`, Статус: {s['status']}, Д/Н: {s['birthday']})\n"
                return {
                    "response": resp,
                    "tools_called": tools_called,
                    "provider": "CMS Smart Agent Engine (Offline Fallback)",
                    "subject": subject,
                }

        # 4. RAG fallback
        rag_results = ctx["rag_chunks"]
        if rag_results and rag_results[0]["score"] > 0.05:
            top_chunk = rag_results[0]
            subj_label = f" ({top_chunk['subject']})" if top_chunk.get("subject") else ""
            resp = f"📚 **Фрагмент із вашої бази знань{subj_label} (Офлайн-режим):**\n\n"
            resp += f"{top_chunk['text']}\n\n"
            resp += f"📌 *Джерело: файл `{top_chunk['filename']}`, сторінка {top_chunk['page']}.*"
            return {
                "response": resp,
                "tools_called": tools_called,
                "provider": "CMS Smart Agent Engine (Offline Fallback)",
                "subject": subject,
            }

        subj_phrase = f" для напряму **'{subject}'**" if subject else ""
        return {
            "response": (
                f"Привіт! Я **CMS AI Assistant**{subj_phrase}.\n\n"
                f"Я можу допомогти вам із:\n"
                f"1. 📄 **Вашою базою знань (PDF)**: натисніть 📎 внизу, щоб завантажити файл.\n"
                f"2. 👥 **Даними студентів**: запитайте *'Хто в групі PZ-22?'* або *'Знайди студента'*.\n"
                f"3. 📊 **Статистикою**: запитайте *'Скільки студентів зараз зареєстровано?'*."
            ),
            "tools_called": tools_called,
            "provider": "CMS Smart Agent Engine (Offline Fallback)",
            "subject": subject,
        }


ai_agent = CMSAIAgent()
