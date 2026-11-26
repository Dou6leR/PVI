from typing import Optional
from beanie import PydanticObjectId
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session

from core import postgres_helper, settings
from api.v1.ai.pdf_parser import extract_text_from_pdf
from api.v1.ai.rag import rag_store
from api.v1.ai.agent import ai_agent
from api.v1.ai.mcp_server import handle_mcp_request
from api.v1.ai.quiz import generate_quiz
from api.v1.ai.coach import (
    generate_and_save_study_note,
    get_student_study_notes,
    delete_student_study_note,
)
from api.v1.messages.services import MessagesService
from core.models import Chat
from core.logger import logger

router = APIRouter(tags=["AI & RAG"])


class AIChatRequest(BaseModel):
    message: str
    subject: Optional[str] = ""
    chat_id: Optional[str] = "default"
    student_id: Optional[int] = None


class RAGQueryRequest(BaseModel):
    query: str
    subject: Optional[str] = None
    student_id: Optional[int] = None
    chat_id: Optional[str] = None
    top_k: int = 3


@router.post("/chat")
async def chat_with_agent(
    payload: AIChatRequest,
    session: Session = Depends(postgres_helper.get_session)
):
    """
    Sends a query to CMS AI Assistant within a specific chat/user scope.
    The agent autonomously uses Tool Calling and RAG vector search scoped to the student & chat.
    """
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    chat_doc = None
    chat_history = []
    if payload.chat_id and payload.student_id is not None:
        try:
            chat_oid = PydanticObjectId(payload.chat_id)
            chat_doc = await Chat.get(chat_oid, fetch_links=True)
            if chat_doc and payload.student_id in chat_doc.users:
                chat_history = [
                    {"user": m.user, "message": m.message}
                    for m in (chat_doc.messages or [])[-6:]
                    if hasattr(m, "user") and hasattr(m, "message")
                ]
        except Exception as e:
            logger.debug(f"Could not preload chat history for chat_id={payload.chat_id}: {e}")

    try:
        result = await ai_agent.execute_agent(
            user_message=payload.message,
            subject=payload.subject or "",
            session=session,
            student_id=payload.student_id,
            chat_id=payload.chat_id,
            chat_history=chat_history,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if chat_doc and payload.student_id in chat_doc.users:
        try:
            await MessagesService.append_message(chat_doc.id, payload.message, payload.student_id)
            await MessagesService.append_message(chat_doc.id, result["response"], 9999)
        except Exception as e:
            logger.debug(f"Skipping chat persistence for chat_id={payload.chat_id}: {e}")

    return result


@router.post("/rag/upload-pdf")
async def upload_pdf_document(
    file: UploadFile = File(...),
    subject: str = Form(""),
    chat_id: str = Form("default"),
    student_id: Optional[int] = Form(None)
):
    """
    Uploads a PDF document (lecture notes, syllabus, lab guide), extracts text with pypdf,
    computes embeddings and indexes into the RAG knowledge store privately for the given student.
    """
    if student_id is None:
        raise HTTPException(status_code=400, detail="student_id is required for private knowledge base")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are supported")

    content_bytes = await file.read()
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        pages_data = extract_text_from_pdf(content_bytes)
        if not pages_data:
            raise HTTPException(status_code=400, detail="No readable text found in PDF")

        chunks_count = await rag_store.add_document_async(
            subject=subject,
            chat_id=chat_id,
            filename=file.filename,
            pages_data=pages_data,
            student_id=student_id
        )

        subj_text = f" для напряму '{subject}'" if subject.strip() else ""
        return {
            "status": "success",
            "filename": file.filename,
            "subject": subject,
            "chat_id": chat_id,
            "student_id": student_id,
            "is_private": True,
            "pages_extracted": len(pages_data),
            "chunks_indexed": chunks_count,
            "message": f"Документ '{file.filename}' успішно збережено у вашій приватній базі знань{subj_text} ({chunks_count} фрагментів)."
        }
    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"Embedding service error for PDF {file.filename}: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error indexing PDF {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/documents")
async def get_rag_documents(
    subject: Optional[str] = None,
    student_id: Optional[int] = None,
    chat_id: Optional[str] = None
):
    """
    Lists indexed documents in the RAG knowledge store strictly scoped to the student & chat.
    """
    docs = rag_store.list_documents(subject=subject, student_id=student_id, chat_id=chat_id)
    return {
        "total_chunks": sum(d["chunks_count"] for d in docs),
        "documents": docs
    }


@router.post("/rag/query")
async def query_rag_knowledge(payload: RAGQueryRequest):
    """
    Direct RAG vector similarity search without LLM synthesis.
    """
    try:
        results = rag_store.search(
            query=payload.query,
            subject=payload.subject,
            student_id=payload.student_id,
            chat_id=payload.chat_id,
            top_k=payload.top_k
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {
        "query": payload.query,
        "subject": payload.subject,
        "results_count": len(results),
        "results": results
    }


@router.get("/status")
async def get_ai_status():
    """
    Returns AI configuration and live provider status (Gemini / Ollama).
    """
    has_gemini = bool(settings.ai.api_key.strip() and settings.ai.api_key.strip() != "your_gemini_api_key_here")
    ollama_info = await ai_agent.get_ollama_status()
    resolved_ollama = ai_agent._resolve_ollama_model(ollama_info["models"])
    resolved_embed = ai_agent._resolve_ollama_model(
        ollama_info["models"],
        preferred_model=settings.ai.ollama_embedding_model,
        fallback_any=False,
    )
    pref = settings.ai.provider.strip().lower()

    if pref == "ollama":
        active = f"Ollama ({resolved_ollama})" if (ollama_info["reachable"] and resolved_ollama) else "Unavailable (Ollama unreachable)"
    elif pref == "gemini":
        active = f"Google Gemini ({settings.ai.model})" if has_gemini else "Unavailable (Gemini API key missing)"
    else:
        if has_gemini:
            active = f"Google Gemini ({settings.ai.model})"
        elif ollama_info["reachable"] and resolved_ollama:
            active = f"Ollama ({resolved_ollama})"
        else:
            active = "Unavailable (Ollama unreachable / no Gemini key)"

    return {
        "provider": active,
        "configured_provider": settings.ai.provider,
        "gemini_model": settings.ai.model,
        "embedding_model": settings.ai.embedding_model if has_gemini and pref != "ollama" else settings.ai.ollama_embedding_model,
        "ollama_embedding_model": resolved_embed or settings.ai.ollama_embedding_model,
        "ollama_embedding_ready": bool(ollama_info["reachable"] and resolved_embed),
        "live_gemini_configured": has_gemini,
        "ollama_reachable": ollama_info["reachable"],
        "ollama_model": resolved_ollama or settings.ai.ollama_model,
        "ollama_models_installed": ollama_info["models"],
        "rag_chunks_count": rag_store.count_chunks(),
        "mcp_enabled": True
    }


@router.post("/mcp")
async def handle_mcp_post(
    request: Request,
    session: Session = Depends(postgres_helper.get_session)
):
    """
    Model Context Protocol (MCP) JSON-RPC 2.0 endpoint.
    """
    body = await request.json()
    return handle_mcp_request(body, session)


class QuizGenerateRequest(BaseModel):
    chat_id: Optional[str] = None
    student_id: Optional[int] = None
    subject: str = ""
    topic: str = ""
    num_questions: int = 3
    previous_questions: list[str] = []


@router.post("/tests/generate-quiz")
@router.post("/tasks/generate-quiz")
async def generate_test_quiz(payload: QuizGenerateRequest):
    """
    Generates interactive multiple-choice test questions scoped to the user's selected chat/PDFs
    or a custom topic using the active AI provider (Ollama / Gemini).
    """
    try:
        result = await generate_quiz(
            subject=payload.subject,
            topic=payload.topic,
            chat_id=payload.chat_id,
            student_id=payload.student_id,
            num_questions=payload.num_questions,
            previous_questions=payload.previous_questions,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if result.get("status") == "error":
        raise HTTPException(
            status_code=int(result.get("http_status", 400)),
            detail=result.get("detail", "Cannot generate test"),
        )
    return result


class StudyCoachRequest(BaseModel):
    student_id: int
    chat_id: Optional[str] = None
    subject: str = ""
    topic: str = ""
    score: int
    total: int
    mistakes: list[dict] = []


@router.post("/tests/study-coach")
async def create_study_coach_note(payload: StudyCoachRequest):
    """
    Runs the n8n AI Study Coach workflow (with seamless fallback) to generate a personalized
    study cheat sheet from test mistakes and persists it in MongoDB for the student.
    """
    return await generate_and_save_study_note(
        student_id=payload.student_id,
        chat_id=payload.chat_id,
        subject=payload.subject,
        topic=payload.topic,
        score=payload.score,
        total=payload.total,
        mistakes=payload.mistakes,
    )


@router.get("/tests/study-notes")
async def list_study_notes(student_id: int):
    """Returns saved study cheat sheets strictly scoped to the given student_id."""
    notes = await get_student_study_notes(student_id=student_id)
    return {"count": len(notes), "notes": notes}


@router.delete("/tests/study-notes/{note_id}")
async def remove_study_note(note_id: str, student_id: int):
    """Deletes a saved study cheat sheet owned by the student."""
    return await delete_student_study_note(note_id=note_id, student_id=student_id)

