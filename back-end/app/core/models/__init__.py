__all__ = [
    "Student",
    "Messages",
    "Chat",
    "all_document_models",
]

from .student import Student
from .messages import Chat, Messages

all_document_models = [
    Chat,
    Messages,
]
