from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


class StudyNote(Document):
    student_id: int
    chat_id: Optional[str] = None
    topic: str
    subject: str = ""
    score: int
    total: int
    percent: int
    mistakes_count: int
    coach_mode: str  # "remedial" or "advanced"
    source: str
    content_md: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "study_notes"
