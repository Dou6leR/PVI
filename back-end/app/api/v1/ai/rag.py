import asyncio
import json
import urllib.error
import urllib.request
from typing import Optional
import numpy as np
from sqlmodel import Session, select, func

from core import settings, postgres_helper
from core.logger import logger
from core.models.rag import KnowledgeChunk, EMBEDDING_DIM


class RAGKnowledgeStore:
    @staticmethod
    def _fit_embedding_dim(vec: np.ndarray, target_dim: int = EMBEDDING_DIM) -> list[float]:
        """Normalizes and fits any embedding vector to PostgreSQL Vector(EMBEDDING_DIM)."""
        if len(vec) > target_dim:
            vec = vec[:target_dim]
        elif len(vec) < target_dim:
            vec = np.pad(vec, (0, target_dim - len(vec)))
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec.astype(float).tolist()

    @staticmethod
    def _is_gemini_configured() -> bool:
        api_key = settings.ai.api_key.strip()
        return bool(api_key and api_key != "your_gemini_api_key_here")

    @staticmethod
    def _call_ollama_embed_sync(text: str) -> np.ndarray:
        """Generates dense semantic embeddings using the configured Ollama model (e.g. bge-m3)."""
        base_url = settings.ai.ollama_url.rstrip("/")
        model = settings.ai.ollama_embedding_model.strip() or "bge-m3"
        payload = json.dumps({
            "model": model,
            "input": text,
            "keep_alive": "10m",
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/embed",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        embeddings = data.get("embeddings") or []
        if not embeddings or not embeddings[0]:
            raise RuntimeError(f"Ollama returned empty embedding for model '{model}'")
        return np.array(embeddings[0], dtype=np.float32)

    def _embed_via_gemini(self, text: str) -> list[float]:
        from google import genai

        client = genai.Client(api_key=settings.ai.api_key.strip())
        response = client.models.embed_content(
            model=settings.ai.embedding_model,
            contents=text,
        )
        vec = np.array(response.embedding.values, dtype=np.float32)
        return self._fit_embedding_dim(vec, EMBEDDING_DIM)

    def _embed_via_ollama(self, text: str) -> list[float]:
        vec = self._call_ollama_embed_sync(text)
        return self._fit_embedding_dim(vec, EMBEDDING_DIM)

    def _get_embedding(self, text: str) -> list[float]:
        pref = settings.ai.provider.strip().lower()
        has_gemini = self._is_gemini_configured()

        if pref == "gemini":
            if not has_gemini:
                raise RuntimeError("Gemini embedding selected, but APP_CONFIG__AI__API_KEY is not set.")
            return self._embed_via_gemini(text)

        if pref != "ollama" and has_gemini:
            try:
                return self._embed_via_gemini(text)
            except Exception as e:
                logger.warning(f"Gemini embedding failed ({e}), falling back to Ollama ({settings.ai.ollama_embedding_model}).")

        try:
            return self._embed_via_ollama(text)
        except Exception as e:
            raise RuntimeError(
                f"Embedding service unavailable (Ollama model '{settings.ai.ollama_embedding_model}'): {e}"
            ) from e

    @staticmethod
    def _split_text_cleanly(content: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
        """Splits text into overlapping chunks aligned to whitespace boundaries."""
        chunks: list[str] = []
        text_len = len(content)
        start = 0
        while start < text_len:
            end = min(start + chunk_size, text_len)
            if end < text_len:
                space_idx = content.rfind(" ", start + int(chunk_size * 0.6), end)
                newline_idx = content.rfind("\n", start + int(chunk_size * 0.6), end)
                boundary = max(space_idx, newline_idx)
                if boundary > start:
                    end = boundary
            chunk_text = content[start:end].strip()
            if chunk_text:
                chunks.append(chunk_text)
            if end >= text_len:
                break
            next_start = max(end - overlap, start + 1)
            if next_start > 0 and next_start < text_len and not content[next_start - 1].isspace():
                next_space = content.find(" ", next_start, end)
                if next_space != -1:
                    next_start = next_space + 1
            start = next_start
        return chunks

    @staticmethod
    def _build_filters(subject: Optional[str], student_id: Optional[int], chat_id: Optional[str]) -> list:
        if student_id is None:
            return []
        filters = [KnowledgeChunk.student_id == int(student_id)]
        chat_clean = str(chat_id).strip() if chat_id else None
        sub_clean = subject.strip().lower() if subject else None

        if chat_clean and chat_clean not in ["default", ""]:
            filters.append(KnowledgeChunk.chat_id == chat_clean)
        elif sub_clean and sub_clean not in ["all", "any", ""]:
            filters.append(KnowledgeChunk.subject == sub_clean)
        return filters

    def add_chunk(self, subject: str, chat_id: str, filename: str, page: int, text: str, student_id: Optional[int] = None) -> Optional[KnowledgeChunk]:
        if student_id is None:
            return None
        embedding = self._get_embedding(text)
        row = KnowledgeChunk(
            student_id=int(student_id),
            subject=subject.strip().lower(),
            display_subject=subject.strip(),
            chat_id=str(chat_id),
            filename=filename,
            page=page,
            text=text,
            embedding=embedding,
        )
        with Session(postgres_helper.engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
        return row

    async def add_document_async(self, subject: str, chat_id: str, filename: str, pages_data: list[dict], student_id: int, chunk_size: int = 800, overlap: int = 150) -> int:
        """
        Chunks text from pages on word boundaries, computes embeddings, and stores rows
        directly in PostgreSQL (pgvector) strictly scoped to student_id.
        """
        rows: list[KnowledgeChunk] = []
        sub_display = subject.strip()
        sub_lower = sub_display.lower()

        for page_info in pages_data:
            page_num = page_info["page"]
            content = page_info["text"]
            for chunk_text in self._split_text_cleanly(content, chunk_size=chunk_size, overlap=overlap):
                embedding = await asyncio.to_thread(self._get_embedding, chunk_text)
                rows.append(
                    KnowledgeChunk(
                        student_id=int(student_id),
                        subject=sub_lower,
                        display_subject=sub_display,
                        chat_id=str(chat_id),
                        filename=filename,
                        page=page_num,
                        text=chunk_text,
                        embedding=embedding,
                    )
                )

        if rows:
            with Session(postgres_helper.engine) as session:
                session.add_all(rows)
                session.commit()

        logger.info(f"Indexed document '{filename}' in PostgreSQL pgvector for student_id={student_id}, chat_id={chat_id} ({len(rows)} chunks).")
        return len(rows)

    def get_overview_chunks(self, subject: Optional[str] = None, student_id: Optional[int] = None, chat_id: Optional[str] = None, limit: int = 3) -> list[dict]:
        filters = self._build_filters(subject, student_id, chat_id)
        if not filters:
            return []
        with Session(postgres_helper.engine) as session:
            rows = session.exec(
                select(KnowledgeChunk)
                .where(*filters)
                .order_by(KnowledgeChunk.filename, KnowledgeChunk.page, KnowledgeChunk.id)
                .limit(limit)
            ).all()
        return [
            {
                "score": 1.0,
                "subject": r.display_subject,
                "filename": r.filename,
                "page": r.page,
                "text": r.text,
                "is_private": True,
            }
            for r in rows
        ]

    def get_varied_chunks(self, subject: Optional[str] = None, student_id: Optional[int] = None, chat_id: Optional[str] = None, limit: int = 6) -> list[dict]:
        filters = self._build_filters(subject, student_id, chat_id)
        if not filters:
            return []
        with Session(postgres_helper.engine) as session:
            rows = session.exec(
                select(KnowledgeChunk)
                .where(*filters)
                .order_by(func.random())
                .limit(limit)
            ).all()
        return [
            {
                "score": 1.0,
                "subject": r.display_subject,
                "filename": r.filename,
                "page": r.page,
                "text": r.text,
                "is_private": True,
            }
            for r in rows
        ]

    def search(self, query: str, subject: Optional[str] = None, student_id: Optional[int] = None, chat_id: Optional[str] = None, top_k: int = 4) -> list[dict]:
        """Native PostgreSQL pgvector cosine similarity search scoped to student_id and chat_id/subject."""
        filters = self._build_filters(subject, student_id, chat_id)
        if not filters:
            return []

        with Session(postgres_helper.engine) as session:
            has_rows = session.exec(select(KnowledgeChunk.id).where(*filters).limit(1)).first()
            if not has_rows:
                return []

            query_vec = self._get_embedding(query)
            distance_expr = KnowledgeChunk.embedding.cosine_distance(query_vec)
            rows = session.exec(
                select(KnowledgeChunk, (1.0 - distance_expr).label("similarity"))
                .where(*filters)
                .order_by(distance_expr)
                .limit(top_k)
            ).all()

        return [
            {
                "score": float(similarity) if similarity is not None else 0.0,
                "subject": chunk.display_subject,
                "filename": chunk.filename,
                "page": chunk.page,
                "text": chunk.text,
                "is_private": True,
            }
            for chunk, similarity in rows
        ]

    def list_documents(self, subject: Optional[str] = None, student_id: Optional[int] = None, chat_id: Optional[str] = None) -> list[dict]:
        filters = self._build_filters(subject, student_id, chat_id)
        if not filters:
            return []

        with Session(postgres_helper.engine) as session:
            rows = session.exec(
                select(
                    KnowledgeChunk.display_subject,
                    KnowledgeChunk.chat_id,
                    KnowledgeChunk.filename,
                    func.count(KnowledgeChunk.id),
                )
                .where(*filters)
                .group_by(KnowledgeChunk.display_subject, KnowledgeChunk.chat_id, KnowledgeChunk.filename)
            ).all()

        return [
            {
                "subject": disp_sub,
                "chat_id": c_id,
                "filename": fname,
                "chunks_count": int(cnt),
                "is_private": True,
            }
            for disp_sub, c_id, fname, cnt in rows
        ]

    def count_chunks(self) -> int:
        try:
            with Session(postgres_helper.engine) as session:
                return int(session.exec(select(func.count(KnowledgeChunk.id))).one())
        except Exception:
            return 0


rag_store = RAGKnowledgeStore()
