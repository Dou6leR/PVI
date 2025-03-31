from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasicCredentials
from sqlmodel import select
from starlette import status

from core.models import Student
from core.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentsResponse,
    StudentResponse,
)
from core import settings, postgres_helper


class StudentService:
    @classmethod
    async def get_students_response(cls, students: list[Student]) -> StudentsResponse:
        return StudentsResponse(
            data=[
                StudentResponse(
                    id=student.id,
                    group=student.group,
                    first_name=student.first_name,
                    last_name=student.last_name,
                    gender=student.gender,
                    birthday=student.birthday,
                    status=student.status,
                )
                for student in students
            ]
        )

    @classmethod
    async def get_student(cls, student_id, session) -> Student:
        student = session.get(Student, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        return student

    @classmethod
    async def get_students(cls, session, offset: int, limit: int) -> list[Student]:
        students = session.exec(select(Student).order_by(Student.id).offset(offset).limit(limit)).all()
        if not students:
            raise HTTPException(status_code=404, detail="Students not found")
        return students

    @classmethod
    async def create_student(cls, student_create: StudentCreate, session):
        existing_student = session.exec(
            select(Student).where(
                Student.first_name == student_create.first_name,
                Student.last_name == student_create.last_name,
                Student.birthday == student_create.birthday,
            )
        ).first()

        if existing_student:
            raise HTTPException(
                status_code=400,
                detail="Student with this first name, last name and birthday already exists"
            )
        student = Student(**student_create.model_dump(), status=False, password=student_create.birthday.strftime("%d.%m.%Y"))
        session.add(student)
        session.commit()

    @classmethod
    async def update_student(cls, student_id: int, student_update: StudentUpdate, session):
        student = session.get(Student, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        update_data = student_update.model_dump(exclude_unset=True)
        update_data["password"] = student_update.birthday.strftime("%d.%m.%Y")
        new_first_name = update_data.get('first_name', student.first_name)
        new_last_name = update_data.get('last_name', student.last_name)
        new_birthday = update_data.get('birthday', student.birthday)

        if new_first_name != student.first_name or new_last_name != student.last_name:
            existing_student = session.exec(
                select(Student).where(
                    Student.first_name == new_first_name,
                    Student.last_name == new_last_name,
                    Student.birthday == new_birthday,
                    Student.id != student_id,
                )
            ).first()

            if existing_student:
                raise HTTPException(
                    status_code=400,
                    detail="Another student with this first name, last name and birthday already exists"
                )
        for key, value in update_data.items():
            setattr(student, key, value)

        session.add(student)
        session.commit()
        session.refresh(student)

    @classmethod
    async def delete_student(cls, student_id: int, session):
        student = session.get(Student, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        session.delete(student)
        session.commit()

    @classmethod
    async def login_student(
            cls,
            session: postgres_helper.SessionDep,
            credentials: HTTPBasicCredentials = Depends(settings.security),
    ):
        username = credentials.username
        password = credentials.password
        first_name, last_name = username.split(" ")
        print(first_name, last_name, password)
        student = session.exec(
            select(Student).where(
                Student.first_name == first_name,
                Student.last_name == last_name,
                Student.password == password,
            )
        ).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        student.status = True
        session.add(student)
        session.commit()
        session.refresh(student)
        return student.id

    @classmethod
    async def logout_student(
            cls,
            id: int,
            session
    ):
        student = session.get(Student, id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        student.status = False
        session.add(student)
        session.commit()
        session.refresh(student)
