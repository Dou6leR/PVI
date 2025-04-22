from beanie import PydanticObjectId
from beanie.operators import In
from fastapi import WebSocket, HTTPException

from core.models import Chat, Messages
from core.schemas import ChatCreate, MessageCreate, ChatsResponse, ChatResponse, WSMessage

from api.v1.students.services import StudentService
from core.schemas.messages import WSMember, WSChat


class WebSocketsService:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, student: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[student] = websocket

    async def disconnect(self, student: int, websocket: WebSocket):
        if student in self.active_connections.keys():
            del self.active_connections[student]

    async def broadcast(self, message: dict, session):
        if message["message_type"] == "message":
            if "room_id" in message:
                if message["room_id"]:
                    chat = await MessagesService.get_chat_by_id(message["room_id"], session)
                    for user in chat.users:
                        if user.id in self.active_connections.keys() and user.id != int(message["user"]):
                            await self.active_connections[user.id].send_json(WSMessage(**message).model_dump_json())
                            await MessagesService.append_message(
                                PydanticObjectId(message["room_id"]),
                                message["message"],
                                int(message["user"])
                            )

        elif message["message_type"] == "member":
            chat = await MessagesService.add_new_member(PydanticObjectId(message["room_id"]), int(message["member_id"]))
            for user in chat.users:
                if user in self.active_connections.keys():
                    await self.active_connections[user].send_json(WSMember(**message).model_dump_json())

        elif message["message_type"] == "chat":
            chat = await MessagesService.create_chat(ChatCreate(**message))
            for user in chat.users:
                if user in self.active_connections.keys():
                    await self.active_connections[user].send_json(
                        WSChat(message_type=message["message_type"], chat_id=chat.id).model_dump_json()
                    )


class MessagesService:
    @classmethod
    async def create_chats_response(cls, chats: list[Chat]):
        result = []
        for chat in chats:
            result.append(ChatResponse(**chat.model_dump()))
        return ChatsResponse(data=result)

    @classmethod
    async def create_chat(cls, chat: ChatCreate):
        chat_dict = chat.model_dump()
        result = Chat(**chat_dict)
        await Chat.insert_one(result)
        return result

    @classmethod
    async def add_new_member(cls, chat_id: PydanticObjectId, user_id: int):
        chat = await Chat.find_one(Chat.id == chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if user_id not in chat.users:
            chat.users.append(user_id)
            await chat.save()
        return chat

    @classmethod
    async def get_all_user_chats(cls, user: int, session):
        chats = await Chat.find(In(Chat.users, [user]), fetch_links=True).to_list()
        if not chats:
            raise HTTPException(status_code=404, detail="Chats not found")
        for chat in chats:
            if chat.users:
                students = [
                    await StudentService.get_student(student_id, session)
                    for student_id in chat.users
                ]
                chat.users = students
        return chats

    @classmethod
    async def get_chat_by_id(cls, chat_id: PydanticObjectId, session):
        chat = await Chat.get(chat_id, fetch_links=True)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if chat.users:
            students = [
                await StudentService.get_student(student_id, session)
                for student_id in chat.users
            ]
            chat.users = students
        return chat

    @classmethod
    async def append_message(cls, chat_id: PydanticObjectId, content: str, sender_id: int):
        chat = await Chat.find_one(Chat.id == chat_id, fetch_links=True)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        message = Messages(message=content, user=sender_id)
        await message.save()
        chat.messages.append(message)
        await chat.save()


web_sockets_service = WebSocketsService()
