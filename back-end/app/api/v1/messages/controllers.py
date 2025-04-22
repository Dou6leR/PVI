import json

from beanie import PydanticObjectId
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from api.v1.messages import web_sockets_service, MessagesService
from api.v1.students import StudentService

from core import postgres_helper, logger
from core.schemas import StudentUpdate, ChatCreate, ChatResponse, ChatsResponse

router = APIRouter(
    tags=["Messages"],
)


@router.post("/chat", status_code=201)
async def create_chat(chat: ChatCreate):
    await MessagesService.create_chat(chat)


@router.post("/new_member/{chat_id}", status_code=201)
async def add_new_member(chat_id: PydanticObjectId, user_id: int):
    pass


@router.get("/chat/{chat_id}", status_code=200, response_model=ChatResponse)
async def get_chat(chat_id: PydanticObjectId, session: postgres_helper.SessionDep, ):
    return await MessagesService.get_chat_by_id(chat_id, session)


@router.get("/user_chats/{user_id}", status_code=200, response_model=ChatsResponse)
async def get_all_user_chats(user_id: int, session: postgres_helper.SessionDep, ):
    chat = await MessagesService.get_all_user_chats(user_id, session)
    result = await MessagesService.create_chats_response(chat)
    return result


@router.get("/ws", status_code=200)
async def get_all_websockets():
    return [k for k in web_sockets_service.active_connections.keys()]


@router.websocket("/{student_id}/ws/{client_id}")
async def websocket_endpoint(
        session: postgres_helper.SessionDep,
        websocket: WebSocket, client_id: int,
        student_id: int,
):
    await web_sockets_service.connect(student_id, websocket)
    try:
        await StudentService.update_student(student_id, StudentUpdate(status=True), session)
        while True:
            data = await websocket.receive_text()
            json_data = json.loads(data)
            print(json_data)
            await web_sockets_service.broadcast(json_data, session)
    except WebSocketDisconnect:
        await web_sockets_service.disconnect(student_id, websocket)
        await StudentService.logout_student(student_id, session)
