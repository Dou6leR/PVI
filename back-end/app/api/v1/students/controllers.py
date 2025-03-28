from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from api.v1.students import StudentService

from core.schemas import StudentCreate, StudentUpdate, StudentResponse, StudentsResponse
from core import postgres_helper, settings

router = APIRouter(
    tags=["Students"],
)


@router.get(
    "/",
    response_model=StudentsResponse,
)
async def get_students(
        session: postgres_helper.SessionDep,
        offset: int = 0, limit: int = 100,
        auth: int = Depends(StudentService.login_student),
):
    return await StudentService.get_students_response(
        await StudentService.get_students(session, offset=offset, limit=limit)
    )


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
)
async def get_student(
        student_id: int, session: postgres_helper.SessionDep,
        auth: int = Depends(StudentService.login_student),
):
    return await StudentService.get_student(student_id, session)


@router.post(
    "/",
)
async def create_student(
        student: StudentCreate, session: postgres_helper.SessionDep,
        auth: int = Depends(StudentService.login_student),
):
    await StudentService.create_student(student, session)


@router.patch(
    "/{student_id}",
)
async def update_student(
        student_id: int, student: StudentUpdate,
        session: postgres_helper.SessionDep
):
    await StudentService.update_student(student_id, student, session)


@router.delete(
    "/{student_id}",
)
async def delete_student(
        student_id: int, session: postgres_helper.SessionDep,
        auth: int = Depends(StudentService.login_student),
):
    await StudentService.delete_student(student_id, session)


@router.post(
    "/login",
)
async def get_login(
        auth: int = Depends(StudentService.login_student),
):
    return ORJSONResponse([{"message": "Login successful", "student_id": auth}])


@router.post(
    "/logout",
)
async def get_logout(
        session: postgres_helper.SessionDep,
        auth: int = Depends(StudentService.login_student),
):
    await StudentService.logout_student(auth, session)
    return ORJSONResponse([{"message": "Logout successful", "student_id": auth}])
