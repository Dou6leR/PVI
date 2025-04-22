from beanie import Document, Link

from core.models import Student


class Messages(Document):
    user: int
    message: str

    class Settings:
        name = "messages"


class Chat(Document):
    users: list[int | Student]
    chat_name: str
    messages: list[Link[Messages]] = []

    class Settings:
        name = "chats"
