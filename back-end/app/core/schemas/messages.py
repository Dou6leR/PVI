from beanie import PydanticObjectId
from pydantic import BaseModel
from core.schemas import StudentResponse


class MessageCreate(BaseModel):
    user: int
    message: str


class MessageResponse(BaseModel):
    user: int
    message: str


class WSMessage(BaseModel):
    message_type: str
    user: int
    message: str
    room_id: PydanticObjectId


class WSMember(BaseModel):
    message_type: str
    member_id: int
    room_id: PydanticObjectId


class WSChat(BaseModel):
    message_type: str
    chat_id: PydanticObjectId


class ChatCreate(BaseModel):
    users: list[int]
    chat_name: str


class ChatResponse(BaseModel):
    id: PydanticObjectId
    users: list[StudentResponse]
    chat_name: str
    messages: list[MessageResponse]


class ChatsResponse(BaseModel):
    data: list[ChatResponse]
