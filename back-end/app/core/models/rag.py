from typing import Any
from sqlalchemy import Column, ForeignKey, Text
from sqlmodel import SQLModel, Field
from pgvector.sqlalchemy import Vector

EMBEDDING_DIM = 768


class KnowledgeChunk(SQLModel, table=True):
    __tablename__ = "rag_chunks"

    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(
        sa_column=Column(ForeignKey("student.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    subject: str = Field(default="", index=True)
    display_subject: str = Field(default="")
    chat_id: str = Field(default="default", index=True)
    filename: str
    page: int
    text: str = Field(sa_column=Column(Text, nullable=False))
    embedding: Any = Field(sa_column=Column(Vector(EMBEDDING_DIM), nullable=False))
