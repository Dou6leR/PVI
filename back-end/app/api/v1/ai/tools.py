from sqlmodel import Session, select, func
from core.models import Student
from api.v1.ai.rag import rag_store
from core.logger import logger


def tool_search_students(name_or_query: str, session: Session) -> list[dict]:
    """
    Search students by first name, last name, or partial match in PostgreSQL database.
    """
    try:
        q = f"%{name_or_query.strip()}%"
        statement = select(Student).where(
            (Student.first_name.ilike(q)) | 
            (Student.last_name.ilike(q)) |
            (Student.group.ilike(q))
        ).limit(10)
        results = session.exec(statement).all()
        return [
            {
                "id": s.id,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "group": s.group,
                "status": "Online" if s.status else "Offline",
                "gender": s.gender,
                "birthday": str(s.birthday)
            }
            for s in results
        ]
    except Exception as e:
        logger.error(f"Error in tool_search_students: {e}")
        return [{"error": str(e)}]


def tool_get_group_students(group: str, session: Session) -> list[dict]:
    """
    Get all students belonging to a specific group (e.g., 'PZ-22', 'PZ-21', 'KI-204').
    """
    try:
        statement = select(Student).where(Student.group.ilike(f"%{group.strip()}%")).limit(30)
        results = session.exec(statement).all()
        return [
            {
                "id": s.id,
                "name": f"{s.first_name} {s.last_name}",
                "group": s.group,
                "status": "Online" if s.status else "Offline"
            }
            for s in results
        ]
    except Exception as e:
        logger.error(f"Error in tool_get_group_students: {e}")
        return [{"error": str(e)}]


def tool_get_system_stats(session: Session) -> dict:
    """
    Returns CMS system-level analytics: total students, group distribution, online count.
    """
    try:
        total = session.exec(select(func.count(Student.id))).one()
        online_count = session.exec(select(func.count(Student.id)).where(Student.status == True)).one()
        
        # Get groups
        students = session.exec(select(Student.group)).all()
        groups_distribution = {}
        for g in students:
            groups_distribution[g] = groups_distribution.get(g, 0) + 1

        return {
            "total_students": total,
            "online_students": online_count,
            "groups_count": len(groups_distribution),
            "groups_distribution": groups_distribution
        }
    except Exception as e:
        logger.error(f"Error in tool_get_system_stats: {e}")
        return {"error": str(e)}


def tool_query_subject_knowledge(query: str, subject: str = None, student_id: int = None, chat_id: str = None, top_k: int = 4) -> list[dict]:
    """
    Retrieves relevant knowledge chunks from uploaded PDF materials using RAG vector similarity.
    Respects student privacy (only accesses student's private uploads in the selected chat/subject).
    """
    try:
        results = rag_store.search(query=query, subject=subject, student_id=student_id, chat_id=chat_id, top_k=top_k)
        return results
    except Exception as e:
        logger.error(f"Error in tool_query_subject_knowledge: {e}")
        return [{"error": str(e)}]


def tool_add_knowledge(subject: str, title: str, content: str, student_id: int = None) -> dict:
    """
    Saves a new fact or rule directly into the RAG knowledge base from the conversation.
    """
    try:
        rag_store.add_chunk(
            subject=subject,
            chat_id="chat-memory",
            filename=f"{title}.txt",
            page=1,
            text=content,
            student_id=student_id
        )
        return {"status": "success", "message": f"Saved '{title}' for subject '{subject}' in knowledge base."}
    except Exception as e:
        logger.error(f"Error in tool_add_knowledge: {e}")
        return {"error": str(e)}
